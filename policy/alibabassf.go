package policy

import (
	"bufio"
	"errors"
	"fmt"
	"log"
	"os"
	"strconv"
	"strings"
	"time"

	"github.com/containerd/cgroups/v3/cgroup1"
	"github.com/martinluttap/containermod/metrics"
)

func AIMD(activeContainersCh chan []string) {
	/*
		We implement the userspace policy used by AlibabaSSF to do AIMD similar to TCP quick drop but slow rebound. There are a couple factors we need to consider:
		1. There is a constant for average and maximum CPU utilization for each app which will be used to decide whther the application is throttle.d
		2. We consider the interference of hyperthreading when we share workload on different set of physical cores.

		N_CORES ← number of physical cores in the machine
		Split N_CORES into two sets: EXCLUSIVE and SHARED.
		Classify applications into Sensitive (S), Bursty (B), and Insensitive (I).
		U_thres ← determine threshold s.t. hyperthread interference is negligible for all  cores.
		e ← constant for additive increase
		r ← constant for multiplicative decrease
		for app in (B + I):
		U ← determine threshold s.t. hyperthread interference is negligible only for SHARED cores.
		P_avg ← average CPU utilization of app.
		P_lim ← max. allowed CPU utilization for app.
		if (U < U_thres) and (P_avg < P_lim):
			if app is throttled:
					app_quota += e
		else:
			app_quota = (app_quota / r)
	*/
	ADD_CONST := 50000 // Addition value for increasing quota in step-wise manner.
	MULT_CONST := 4    // (De)multiplication value for rapidly decrease quota.
	prevCidTTMap := map[string]int64{}
	for {
		select {
		case containerDirs := <-activeContainersCh:
			prevWallTime := time.Now()
			for _, containerDir := range containerDirs {
				/*
					For each active container, we maintain a map of previous throttled time. We then compare the value on each polling period -- if there are delta, the application is being throttled, and we may do additive increase. Else we multiplicatively decrease.

					We need to make sure that, if possible, everything we do is faster than a single period. 100ms is too coarse for the rapid response needed in our case.
				*/
				cid := strings.TrimPrefix(containerDir, "/sys/fs/cgroup/cpu/docker")
				control, _ := cgroup1.Load(cgroup1.StaticPath(cid))
				stats, _ := control.Stat()
				cidThrotTimeNs := stats.GetCPU().GetThrottling().GetThrottledTime()

				prevThrotTimens := prevCidTTMap[cid]
				deltaThrotTimeNs := cidThrotTimeNs - uint64(prevThrotTimens)

				if deltaThrotTimeNs > 0 {
					deltaTimeNs := time.Since(prevWallTime).Nanoseconds()
					fmt.Printf("[%s] %s has delta %d in %d\n", time.Now().Format(time.RFC3339Nano), cid, deltaThrotTimeNs, deltaTimeNs)

					/* Increase quota here */
					infile
				}
				prevCidTTMap[cid] = int64(cidThrotTimeNs)

				fmt.Printf("[%s] ACTIVE %s\n", time.Now().Format(time.RFC3339Nano), containerDir)
			}

		}
	}

}

func WatchAccruedBurstTime(containerDir string) {
	prevCpuNs := 0
	prevWall := time.Now()
	prevNrPeriod := 0
	// bucketBurstNs := 0
	bucketCpuNs := 0
	// prevNrPeriod :
	burstWatcher := NewBurstWatcher()
	for shouldWatch := true; shouldWatch; {
		control, _ := cgroup1.Load(cgroup1.StaticPath(strings.TrimPrefix(containerDir, "/sys/fs/cgroup/cpu")))
		stats, _ := control.Stat(cgroup1.IgnoreNotExist)
		cpuNs := stats.GetCPU().GetUsage().Total
		nrPeriod := stats.GetCPU().GetThrottling().GetPeriods()
		nrThrottled := stats.GetCPU().GetThrottling().GetThrottledPeriods()
		nrThrottledTimeNs := stats.GetCPU().GetThrottling().GetThrottledTime()

		quotaUs, periodUs := metrics.GetCFSData(containerDir)
		periodNs := periodUs * nsPerSecond / usPerSecond
		quotaNs := quotaUs * nsPerSecond / usPerSecond
		burstWatcher.updatePeriodNs(periodNs)
		burstWatcher.updateQuotaNs(quotaNs)
		if burstWatcher.originalQuotaUs == 0 {
			burstWatcher.setOriginalQuotaUs(quotaUs)
		}

		deltaCpuNs := (cpuNs - uint64(prevCpuNs))
		// deltaNrPeriod := (nrPeriod - uint64(prevNrPeriod))
		deltaWallNs := time.Since(prevWall).Nanoseconds()
		moment := (float64(deltaCpuNs) / float64(deltaWallNs))

		/*
			Here we accrue burst credits. Our considerations & algorithm are as follows:

			Within a certain CFS period, a cgroup (usually a single container) may or may not uses up all its allocated cpu time units. Allocated cpu time is simply cfs.quota, which can be used within the duration of cfs.period by jiffies (CFS timeslice, usually 5ms). If a cgroup requires more than cfs.quota within cfs.period, the cgroup will be throttled by kernel, and we can observe this in cpu.stat.
		*/
		burstWatcher.addJiffyNs(deltaWallNs)
		burstWatcher.addPeriodWatchNs(deltaWallNs)
		if deltaCpuNs > 0 {
			fmt.Printf("[%s] DELTA %d\n", time.Now().Format(time.RFC3339Nano), deltaCpuNs)
		}

		if deltaCpuNs > uint64(deltaWallNs) {
			burst := int64(deltaCpuNs) - deltaWallNs
			burstWatcher.addUsage(burst)
			fmt.Printf("[%s] Wall:%d, Cpu:%d, Burst:%d\n", time.Now().Format(time.RFC3339Nano), deltaWallNs, deltaCpuNs, burstWatcher.availBurstNs)
		}

		fmt.Printf("[%s] Burst period %d quota %d deltaJiffy %d deltaPeriodWatchNs %d bucketUsage %d, availBurst %d\n", time.Now().Format(time.RFC3339Nano), burstWatcher.periodNs, burstWatcher.quotaNs, burstWatcher.deltaJiffyNs, burstWatcher.deltaPeriodWatchNs, burstWatcher.bucketUsageNs, burstWatcher.availBurstNs)

		if burstWatcher.hasJiffyElapsed() {
			fmt.Printf("[%s] ELAPSED JIFFY %s nrPeriod:%d, bucketCpuNs:%d, quotaNs:%d, periodNs:%d\n", time.Now().Format(time.RFC3339Nano), containerDir, nrPeriod, bucketCpuNs, quotaNs, periodNs)

			burstWatcher.resetJiffy()
		}
		if burstWatcher.hasPeriodElapsed() {
			fmt.Printf("[%s] ELAPSED PERIOD %s nrPeriod:%d prev:%d, bucketCpuNs:%d, quotaNs:%d, periodNs:%d\n", time.Now().Format(time.RFC3339Nano), containerDir, nrPeriod, prevNrPeriod, bucketCpuNs, quotaNs, periodNs)

			burstWatcher.resetToOriginalQuota(containerDir)
			burstWatcher.applyBurst(containerDir)
			burstWatcher.resetPeriodWatch()

			path := fmt.Sprintf(`%s/cpu.cfs_quota_us`, containerDir)
			if _, err := os.Stat(path); errors.Is(err, os.ErrNotExist) {
				// path/to/whatever does not exist
			}
			infile, openErr := os.OpenFile(path, os.O_RDWR|os.O_CREATE|os.O_TRUNC, 0644)
			if openErr != nil {
				log.Fatalf("While opening: %s:\n", openErr)
			}
			defer infile.Close()

			s := bufio.NewScanner(infile)
			for s.Scan() {
				oldQuotaUs, _ := (strconv.ParseInt(s.Text(), 10, 64))
				fmt.Printf("NOWQUOTA %d\n", oldQuotaUs)
			}

		}

		fmt.Printf("[%s] %s deltaCpuNs:%d,dc/dw:%f,nr_period:%d,nr_throttled:%d,throttled_time:%d\n", time.Now().Format(time.RFC3339Nano), containerDir, deltaCpuNs, moment, nrPeriod, nrThrottled, nrThrottledTimeNs)

		prevCpuNs = int(cpuNs)
		prevNrPeriod = int(nrPeriod)
		prevWall = time.Now()
	}

}
