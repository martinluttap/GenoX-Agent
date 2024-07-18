package metrics

import (
	"bufio"
	"fmt"
	"log"
	"os"
	"strconv"
	"strings"
	"sync"
	"time"

	"github.com/google/cadvisor/client"
	v1 "github.com/google/cadvisor/info/v1"
	"github.com/prometheus/procfs"
)

type CpuUsage struct {
	WorkingTime float64
	IdleTime    float64
}

type CAdvisorCpu struct {
	/*
		Docs:
		https://docs.kernel.org/scheduler/sched-bwc.html
		https://docs.kernel.org/scheduler/sched-stats.html
	*/
	timeStamp time.Time //
	// CPU Usage
	usageTotalNs  int64 //
	usageUserNs   int64 //
	usageSystemNs int64 //

	// CFS Management
	cfsQuotaUs    int64 // run-time replenished within a period (in microseconds)
	cfsPeriodUs   int64 // the length of a period (in microseconds)
	cfsNumPeriods int64 // Number of enforcement intervals that have elapsed.

	// CFS Statistics
	cfsThrottledPeriods int64 // Number of times the group has been throttled/limited.
	cfsThrottledTimeNs  int64 // The total time duration (in nanoseconds) for which entities of the group have been throttled.

	// Schedstat Statistics
	schedstatRunTimeNs      int64 // Time spent on the CPU (nanoseconds)
	schedstatRunqueueTimeNs int64 // Time spent waiting on the runqueue (nanoseconds)
	schedstatRunPeriods     int64 // # timeslices run on CPU
}

type CfsStats struct {
	NrPeriods       int
	NrThrottled     int
	ThrottledTimeNs int
}

func BuildCAdvisorCPUStats(containerInfo *v1.ContainerInfo) CAdvisorCpu {
	if len(containerInfo.Stats) != 1 {
		panic("ContainerInfo has too many elements!")
	}
	stats := CAdvisorCpu{
		timeStamp:               containerInfo.Stats[0].Timestamp,
		usageTotalNs:            int64(containerInfo.Stats[0].Cpu.Usage.Total),
		usageUserNs:             int64(containerInfo.Stats[0].Cpu.Usage.User),
		usageSystemNs:           int64(containerInfo.Stats[0].Cpu.Usage.System),
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

func BuildCpuUsage(stat procfs.Stat) CpuUsage {
	workingTime := stat.CPUTotal.User + stat.CPUTotal.System + stat.CPUTotal.Nice + stat.CPUTotal.IRQ + stat.CPUTotal.SoftIRQ
	idleTime := stat.CPUTotal.Idle + stat.CPUTotal.Iowait
	usage := CpuUsage{
		WorkingTime: workingTime,
		IdleTime:    idleTime,
	}

	return usage
}

func BuildCpuUsageFromFile(containerDirs []string) map[string]int {
	cpuUsageMap := map[string]int{}
	for _, cid := range containerDirs {
		path := fmt.Sprintf(`%s/cpuacct.usage`, cid)
		infile, openErr := os.OpenFile(path, os.O_RDWR|os.O_CREATE|os.O_TRUNC, 0644)
		if openErr != nil {
			log.Fatalf("While opening: %s:\n", openErr)
		}
		defer infile.Close()
		/*
			-- cpuacct.usage
			108592018866225
		*/
		s := bufio.NewScanner(infile)
		s.Scan()
		usageNs, _ := strconv.Atoi(s.Text())
		cpuUsageMap[cid] = usageNs
	}

	return cpuUsageMap
}

func MetricsCollection(containerDirs []string, metricsIntervalMs int, stopCh chan int, wg *sync.WaitGroup) {
	defer wg.Done()

	metricsTicker := time.NewTicker(time.Duration(metricsIntervalMs) * time.Millisecond)
	prevFS, _ := procfs.NewFS("/proc")
	prevStats, _ := prevFS.Stat()
	prevUsage := BuildCpuUsage(prevStats)

	for {
		select {
		case t := <-metricsTicker.C:
			fmt.Printf("Metrics collection at %s\n", t)

			currentFS, _ := procfs.NewFS("/proc")
			currentStats, _ := currentFS.Stat()
			currentUsage := BuildCpuUsage(currentStats)

			workingTime := currentUsage.WorkingTime - prevUsage.WorkingTime
			allTime := workingTime + (currentUsage.IdleTime - prevUsage.IdleTime)
			perc := workingTime / allTime * 100

			fmt.Printf("Perc: %s\n",
				strconv.FormatFloat(perc, 'f', 2, 64),
			)

			prevUsage = currentUsage

		case <-stopCh:
			fmt.Println("Metrics collection stopped!")
			return
		}
	}
}

func BuildCfsStats(containerDirs []string) map[string]CfsStats {
	// Inits for each container
	containerPathDict := map[string]string{}
	for _, containerDir := range containerDirs {
		// Metrics Filepath
		containerPathDict[containerDir] = fmt.Sprintf(`%s/cpu.stat`, containerDir)
	}

	cfsDict := map[string]CfsStats{}
	for containerDir, statsPath := range containerPathDict {
		infile, openErr := os.OpenFile(statsPath, os.O_RDWR|os.O_CREATE|os.O_TRUNC, 0644)
		/*
			1. Open file
			2. Get old period
			3. Calculate new period
			4. Write new period
		*/
		if openErr != nil {
			log.Fatalf("While opening: %s:\n", openErr)
		}
		defer infile.Close()

		s := bufio.NewScanner(infile)
		s.Scan()
		nrPeriod, _ := strconv.Atoi(strings.Fields(s.Text())[1])
		s.Scan()
		nrThrottled, _ := strconv.Atoi(strings.Fields(s.Text())[1])
		s.Scan()
		throttledTime, _ := strconv.Atoi(strings.Fields(s.Text())[1])

		cfsDict[containerDir] = CfsStats{
			NrPeriods:       nrPeriod,
			NrThrottled:     nrThrottled,
			ThrottledTimeNs: throttledTime,
		}
	}

	return cfsDict
}

func ProcFsMetricsCollection(containerDirs []string, metricsIntervalMs int, stopCh chan int, wg *sync.WaitGroup) {
	defer wg.Done()

	metricsTicker := time.NewTicker(time.Duration(metricsIntervalMs) * time.Millisecond)
	prevUsage := BuildCpuUsageFromFile(containerDirs)
	startTime := time.Now()
	for {
		select {
		case <-metricsTicker.C:
			elapsedNs := time.Since(startTime).Nanoseconds()
			//  CPU Usage
			currentUsage := BuildCpuUsageFromFile(containerDirs)
			percentageMap := map[string]float64{}
			for cidPath, usageNs := range currentUsage {
				perc := (float64(usageNs-prevUsage[cidPath]) / float64(elapsedNs)) * 100
				percentageMap[cidPath] = perc

				ss := strings.Split(cidPath, "/")
				cidPathShort := ss[len(ss)-1][:5]
				fmt.Printf("%s: %f at %s\n", cidPathShort, perc, time.Since(startTime))
			}

			// Throttling Information
			cfsDict := BuildCfsStats(containerDirs)
			fmt.Println(cfsDict)
			for cid, stats := range cfsDict {
				fmt.Printf("CfsDict %s: NrPeriod %d, NrThrottled %d, TotalThrottled %d\n", cid, stats.NrPeriods, stats.NrThrottled, stats.ThrottledTimeNs)

			}
			prevUsage = currentUsage

		case <-stopCh:
			fmt.Println("Metrics collection stopped!")
			return
		}
	}
}

func PollCAdvisor(containerDirs []string, pollingIntervalMs int, stopCh chan int, wg *sync.WaitGroup) {

	defer wg.Done()

	client, err := client.NewClient("http://localhost:8080/")
	if err != nil {
		panic(err)
	}
	pollingTicker := time.NewTicker(time.Duration(pollingIntervalMs) * time.Millisecond)

	prevCadvisorCpu := CAdvisorCpu{}
	for {
		select {
		case <-pollingTicker.C:
			request := v1.ContainerInfoRequest{NumStats: 1}
			for _, cidPath := range containerDirs {
				ss := strings.Split(cidPath, "/")
				cid := ss[len(ss)-1]
				sInfo, reqErr := client.ContainerInfo(fmt.Sprintf("/docker/%s", cid), &request)
				if reqErr != nil {
					panic(reqErr)
				}
				currCAdvisorCpu := BuildCAdvisorCPUStats(sInfo)
				if prevCadvisorCpu != (CAdvisorCpu{}) {
					diffTimeNs := currCAdvisorCpu.timeStamp.Nanosecond() - prevCadvisorCpu.timeStamp.Nanosecond()
					if diffTimeNs > 0 {
						diffTotalCpuNs := currCAdvisorCpu.usageTotalNs - prevCadvisorCpu.usageTotalNs

						usage := (diffTotalCpuNs / int64(pollingIntervalMs*1000000)) * 100
						fmt.Printf("Usage %s: %d\n", cidPath, usage)
					}
				}

				// newTimestamp, _ := json.MarshalIndent(sInfo.Stats[0].Timestamp, "", "    ")
				// newCpuStats, _ := json.MarshalIndent(sInfo.Stats[0].Cpu, "", "    ")
				prevCadvisorCpu = currCAdvisorCpu
			}
		case <-stopCh:
			return
		}
	}
}
