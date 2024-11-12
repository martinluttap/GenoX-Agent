package metrics

import (
	"encoding/csv"
	"fmt"
	"os"
	"sync"
)

func PollCpuStatsV2(activeContainersCh <-chan []string, pollingIntervalMs int, stopCh chan int, wg *sync.WaitGroup) {

	defer wg.Done()

	outWriterDict := map[string]*csv.Writer{}
	csvFds := []*os.File{}
	// lastCpuMap := map[string]int64{}
	// prevWall := time.Now()
	// timeStart := time.Now()
	// USER_HZ := 100 // getconf CLK_TCK 100
	// fs, _ := procfs.NewFS("/proc")
	// prevStat, _ := fs.Stat()
	// prevSysCpuTotal := sumWorkingTime(prevStat.CPUTotal)

	for {
		select {
		case containerDirs := <-activeContainersCh:
			headers := []string{"timestampNs", "cid", "cidCpuPercent", "machineCpuPercent"}
			metricName := "cpu"
			newFds := PrepPollingCpuStats(containerDirs, metricName, headers, outWriterDict)
			csvFds = append(csvFds, newFds...)

			// ts := strconv.FormatInt((time.Since(timeStart) * time.Nanosecond).Nanoseconds(), 10)

			cgroupSlice := metrics.NewCGroupSlice("/sys/fs/cgroup/system.slice/docker-4b86025e00fca7570fb6c064b9b38f27dd0c85ce58c984dae958e9dae5044e7d.scope")
			fmt.Println(cgroupSlice.resourceStat.cpu)

		case <-stopCh:
			for idx, fd := range csvFds {
				fmt.Printf("Closing fd for container %d: %p\n", idx, fd)
			}
			fmt.Println()
			return
		}
	}
}
