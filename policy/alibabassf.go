package policy

import (
	"fmt"
	"strings"
	"time"

	"github.com/containerd/cgroups/v3/cgroup1"
	"github.com/martinluttap/containermod/metrics"
)

func WatchAccruedBurstTime(containerDir string) {

	// prevWall := time.Now()
	// loopPeriod := time.Duration(5 * time.Millisecond).Milliseconds()
	prevCpuNs := 0
	prevWall := time.Now()
	// bucketBurstNs := 0
	bucketCpuNs := 0
	// prevNrPeriod := 0
	for shouldWatch := true; shouldWatch; {
		control, _ := cgroup1.Load(cgroup1.StaticPath(strings.TrimPrefix(containerDir, "/sys/fs/cgroup/cpu")))
		stats, _ := control.Stat(cgroup1.IgnoreNotExist)
		cpuNs := stats.GetCPU().GetUsage().Total
		nrPeriod := stats.GetCPU().GetThrottling().GetPeriods()
		nrThrottled := stats.GetCPU().GetThrottling().GetThrottledPeriods()
		nrThrottledTimeNs := stats.GetCPU().GetThrottling().GetThrottledTime()

		quotaNs, periodNs := metrics.GetCFSData(containerDir)
		if cpuNs != uint64(prevCpuNs) && prevCpuNs != 0 {
			if cpuNs <= uint64(prevCpuNs) { // Will this ever happen?
				panic(fmt.Sprintf("[%s] %s prev: %d <= now: %d\n", time.Now(), containerDir, prevCpuNs, cpuNs))
			} else {
				deltaCpuNs := (cpuNs - uint64(prevCpuNs))
				deltaWallNs := time.Since(prevWall).Nanoseconds()
				moment := (float64(deltaCpuNs) / float64(deltaWallNs))

				// Here we accrue burst credits
				bucketCpuNs += int(deltaCpuNs)
				fmt.Printf("[%s] %s nrPeriod:%d, bucketCpuNs:%d, quotaNs:%d, periodNs:%d\n", time.Now().Format(time.RFC3339Nano), containerDir, nrPeriod, bucketCpuNs, quotaNs, periodNs)

				fmt.Printf("[%s] %s deltaCpuNs:%d,deltaWallNs:%d,dc/dw:%f,nr_period:%d,nr_throttled:%d,throttled_time:%d\n", time.Now().Format(time.RFC3339Nano), containerDir, deltaCpuNs, deltaWallNs, moment, nrPeriod, nrThrottled, nrThrottledTimeNs)
			}
		}
		prevCpuNs = int(cpuNs)
		// prevNrPeriod = int(nrPeriod)
		prevWall = time.Now()
		// fmt.Println(stat.CPUTotal, stat.CPUTotal.User, stat.CPUTotal.System, prevStat.CPUTotal)
		// fmt.Printf("[%s] %s, deltaCpuNs:%d, deltaSys:%f, deltaWall: %f, CPU Util.: %f, Sys. Util.: %f\n", time.Now(), containerDir, deltaCpuNs, deltaSys, float64(deltaWall), cpuUsage, machineUsage)
	}

}
