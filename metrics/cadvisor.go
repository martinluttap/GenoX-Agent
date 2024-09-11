package metrics

import (
	"fmt"
	"strings"
	"sync"
	"time"

	"github.com/google/cadvisor/client"
	v1 "github.com/google/cadvisor/info/v1"
)

func BuildCAdvisorCPUStats(containerInfo *v1.ContainerInfo) CAdvisorCpu {
	if len(containerInfo.Stats) != 2 {
		panic("ContainerInfo has too many elements!")
	}
	stats := CAdvisorCpu{
		timeStamp:               containerInfo.Stats[0].Timestamp,
		diffUsageTotalNs:        int64(containerInfo.Stats[1].Cpu.Usage.Total - containerInfo.Stats[0].Cpu.Usage.Total),
		diffUsageUserNs:         int64(containerInfo.Stats[1].Cpu.Usage.User - containerInfo.Stats[0].Cpu.Usage.User),
		diffUsageSystemNs:       int64(containerInfo.Stats[1].Cpu.Usage.System - containerInfo.Stats[0].Cpu.Usage.System),
		cfsQuotaUs:              int64(containerInfo.Spec.Cpu.Quota),
		cfsPeriodUs:             int64(containerInfo.Spec.Cpu.Period),
		cfsNumPeriods:           int64(containerInfo.Stats[0].Cpu.CFS.Periods),
		cfsThrottledPeriods:     int64(containerInfo.Stats[0].Cpu.CFS.ThrottledPeriods),
		cfsThrottledTimeNs:      int64(containerInfo.Stats[0].Cpu.CFS.ThrottledTime),
		schedstatRunTimeNs:      int64(containerInfo.Stats[0].Cpu.Schedstat.RunTime),
		schedstatRunqueueTimeNs: int64(containerInfo.Stats[0].Cpu.Schedstat.RunqueueTime),
		schedstatRunPeriods:     int64(containerInfo.Stats[0].Cpu.Schedstat.RunPeriods),
	}

	return stats
}

func PollCAdvisor(containerDirs []string, pollingIntervalMs int, stopCh chan int, wg *sync.WaitGroup) {

	defer wg.Done()

	client, err := client.NewClient("http://localhost:8080/")
	if err != nil {
		panic(err)
	}
	pollingTicker := time.NewTicker(time.Duration(pollingIntervalMs) * time.Millisecond)
	for {
		select {
		case <-pollingTicker.C:
			request := v1.ContainerInfoRequest{NumStats: 2}
			for _, cidPath := range containerDirs {
				ss := strings.Split(cidPath, "/")
				cid := ss[len(ss)-1]
				sInfo, reqErr := client.ContainerInfo(fmt.Sprintf("/docker/%s", cid), &request)
				if reqErr != nil {
					panic(reqErr)
				}
				currCAdvisorCpu := BuildCAdvisorCPUStats(sInfo)
				usedCpuSeconds := (currCAdvisorCpu.diffUsageSystemNs + currCAdvisorCpu.diffUsageUserNs) / 1000000
				allocatedCpuSeconds := currCAdvisorCpu.cfsQuotaUs / currCAdvisorCpu.cfsPeriodUs

				usage := usedCpuSeconds / allocatedCpuSeconds
				fmt.Printf("Usage %s: %d\n", cidPath, usage)

				// newTimestamp, _ := json.MarshalIndent(sInfo.Stats[0].Timestamp, "", "    ")
				// newCpuStats, _ := json.MarshalIndent(sInfo.Stats[0].Cpu, "", "    ")
			}
		case <-stopCh:
			return
		}
	}
}
