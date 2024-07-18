package metrics

import (
	"bufio"
	"encoding/csv"
	"fmt"
	"log"
	"os"
	"os/exec"
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
	diffUsageTotalNs  int64 //
	diffUsageUserNs   int64 //
	diffUsageSystemNs int64 //

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
	NrPeriods       int64
	NrThrottled     int64
	ThrottledTimeNs int64
}

type KernelStats struct {
	// CFS Management
	cfsQuotaUs  int64 // run-time replenished within a period (in microseconds)
	cfsPeriodUs int64 // the length of a period (in microseconds)

	// CFS Statistics
	cfsNumPeriods       int64 // Number of enforcement intervals that have elapsed.
	cfsThrottledPeriods int64 // Number of times the group has been throttled/limited.
	cfsThrottledTimeNs  int64 // The total time duration (in nanoseconds) for which entities of the group have been throttled.

	// PidStats Statistics Per Process
	procsPidStats map[string]PidStats
}

type PidStats struct {
	// Schedstat Statistics
	schedstatRunTimeNs      int64 // Time spent on the CPU (nanoseconds)
	schedstatRunqueueTimeNs int64 // Time spent waiting on the runqueue (nanoseconds)
	schedstatRunPeriods     int64 // # timeslices run on CPU
}

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
			NrPeriods:       int64(nrPeriod),
			NrThrottled:     int64(nrThrottled),
			ThrottledTimeNs: int64(throttledTime),
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

type DockerStats struct {
	containerId   string
	containerName string
	cpuUsage      float64
}

func BuildDockerStats(cidToDirMap map[string]string) map[string]DockerStats {
	/*
			CONTAINER ID   NAME                           CPU %     MEM USAGE / LIMIT     MEM %     NET I/O          BLOCK I/O     PIDS
		c1105f0ff4b6   nxf-ApNjNbCU6j9F7z3k015mW07X   375.73%   11.53GiB / 187.4GiB   6.15%     2.45kB / 0B      5.45GB / 0B   103
		678500ab3f33   cadvisor                       28.72%    270MiB / 187.4GiB     0.14%     5.13MB / 428MB   3.73MB / 0B   96
	*/
	// Execute command
	cmd := exec.Command("docker", "stats", "--no-stream")
	var out strings.Builder
	cmd.Stdout = &out
	err := cmd.Run()
	if err != nil {
		log.Fatal(err)
	}
	// Capture and process output
	lines := strings.Split(strings.TrimSpace(out.String()), "\n")
	_, data := lines[0], lines[1:]
	statsMap := map[string]DockerStats{}
	for _, d := range data {
		fields := strings.Fields(d)
		cid, name := fields[0], fields[1]
		cpuUsage, _ := strconv.ParseFloat(strings.TrimRight(fields[2], `%`), 64)
		containerDir := cidToDirMap[cid]
		statsMap[containerDir] = DockerStats{
			containerId:   cid,
			containerName: name,
			cpuUsage:      cpuUsage,
		}
	}

	return statsMap
}

func GetCpuStatData(containerDir string) (int64, int64, int64) {
	infile, openErr := os.OpenFile(fmt.Sprintf("%s/cpu.stat", containerDir), os.O_RDWR|os.O_CREATE|os.O_TRUNC, 0644)
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

	return int64(nrPeriod), int64(nrThrottled), int64(throttledTime)
}

func GetCFSData(containerDir string) (int64, int64) {
	// CFS Quota
	quotaInfile, openErr := os.OpenFile(fmt.Sprintf("%s/cpu.cfs_quota_us", containerDir), os.O_RDWR|os.O_CREATE|os.O_TRUNC, 0644)
	if openErr != nil {
		log.Fatalf("While opening: %s:\n", openErr)
	}
	defer quotaInfile.Close()

	quotaScanner := bufio.NewScanner(quotaInfile)
	quotaScanner.Scan()
	cfsQuota, _ := strconv.Atoi(quotaScanner.Text())

	// CFS Period
	periodInfile, openErr := os.OpenFile(fmt.Sprintf("%s/cpu.cfs_period_us", containerDir), os.O_RDWR|os.O_CREATE|os.O_TRUNC, 0644)
	if openErr != nil {
		log.Fatalf("While opening: %s:\n", openErr)
	}
	defer periodInfile.Close()

	periodScanner := bufio.NewScanner(periodInfile)
	periodScanner.Scan()
	cfsPeriod, _ := strconv.Atoi(periodScanner.Text())

	return int64(cfsQuota), int64(cfsPeriod)
}

func GetProcsPidStats(containerDir string) map[string]PidStats {
	procsInfile, openErr := os.OpenFile(fmt.Sprintf("%s/cgroup.procs", containerDir), os.O_RDWR|os.O_CREATE|os.O_TRUNC, 0644)
	if openErr != nil {
		log.Fatalf("While opening: %s:\n", openErr)
	}
	defer procsInfile.Close()

	// Get all procs associated with container
	var procs []string
	s := bufio.NewScanner(procsInfile)
	for s.Scan() {
		procs = append(procs, strings.TrimSpace(s.Text()))
	}

	// For each proc, gather its schedstats
	procsPidStats := map[string]PidStats{}
	for _, p := range procs {
		schedStatInfile, openErr := os.OpenFile(fmt.Sprintf("/proc/%s/schedstat", p), os.O_RDWR|os.O_CREATE|os.O_TRUNC, 0644)
		if openErr != nil {
			log.Fatalf("While opening: %s:\n", openErr)
		}
		defer schedStatInfile.Close()

		s := bufio.NewScanner(schedStatInfile)
		s.Scan()
		fields := strings.Fields(strings.TrimSpace(s.Text()))
		schedstatRunTimeNs, _ := strconv.ParseInt(fields[0], 10, 64)
		schedstatRunqueueTimeNs, _ := strconv.ParseInt(fields[1], 10, 64)
		schedstatRunPeriods, _ := strconv.ParseInt(fields[2], 10, 64)

		pidStats := PidStats{
			schedstatRunTimeNs:      schedstatRunTimeNs,
			schedstatRunqueueTimeNs: schedstatRunqueueTimeNs,
			schedstatRunPeriods:     schedstatRunPeriods,
		}
		procsPidStats[p] = pidStats
	}

	return procsPidStats
}

func BuildKernelStats(containerDirs []string) map[string]KernelStats {
	/*
		We collect the stats from the following folders:
		- /sys/fs/cgroup/cpu/docker/<containerId>/ for each containerId in containerDirs
		- /proc/<pid> for each pid in cgroup.procs
	*/
	kernelStatsD := map[string]KernelStats{}
	for _, containerDir := range containerDirs {
		cfsQuota, cfsPeriod := GetCFSData(containerDir)
		nrPeriod, nrThrottled, throttledTime := GetCpuStatData(containerDir)
		procsPidStats := GetProcsPidStats(containerDir)
		kernelStatsD[containerDir] = KernelStats{
			cfsQuotaUs:          cfsQuota,
			cfsPeriodUs:         cfsPeriod,
			cfsNumPeriods:       nrPeriod,
			cfsThrottledPeriods: nrThrottled,
			cfsThrottledTimeNs:  throttledTime,
			procsPidStats:       procsPidStats,
		}
	}

	return kernelStatsD
}

func PollAllStats(containerDirs []string, pollingIntervalMs int, stopCh chan int, wg *sync.WaitGroup) {

	defer wg.Done()

	pollingTicker := time.NewTicker(time.Duration(pollingIntervalMs) * time.Millisecond)

	outWriterDict := map[string]*csv.Writer{}
	for _, containerDir := range containerDirs {
		ss := strings.Split(containerDir, "/")
		cid := ss[len(ss)-1][:13] // Use first 12 chars as containerId to match Docker's stats
		outFile, err := os.Create(fmt.Sprintf("%s.csv", cid))
		if err != nil {
			panic(err)
		}
		defer outFile.Close()
		writer := csv.NewWriter(outFile)
		defer writer.Flush()
		// this defines the header value and data values for the new csv file
		headers := []string{"timestampNs", "cid", "name", "totalCpu", "quotaUs", "periodUs", "numPeriods", "trPeriods", "trTimeNs"}
		writer.Write(headers)
		outWriterDict[containerDir] = writer
	}

	// Build cid -> containerDir map to join DockerStats and KernelStats
	cidToDirMap := map[string]string{}
	for _, containerDir := range containerDirs {
		ss := strings.Split(containerDir, "/")
		cid := ss[len(ss)-1][:12]
		cidToDirMap[cid] = containerDir
	}
	for {
		select {
		case <-pollingTicker.C:
			dockerStatsMap := BuildDockerStats(cidToDirMap)
			kernelStatsMap := BuildKernelStats(containerDirs)

			ts := strconv.FormatInt(int64(time.Now().Nanosecond()), 10)
			for containerDir, writer := range outWriterDict {
				cid := dockerStatsMap[containerDir].containerId
				name := dockerStatsMap[containerDir].containerName
				totalCpu := fmt.Sprintf("%.2f", dockerStatsMap[containerDir].cpuUsage)
				quotaUs := fmt.Sprintf("%d", kernelStatsMap[containerDir].cfsQuotaUs)
				periodUs := fmt.Sprintf("%d", kernelStatsMap[containerDir].cfsPeriodUs)
				numPeriods := fmt.Sprintf("%d", kernelStatsMap[containerDir].cfsNumPeriods)
				trPeriods := fmt.Sprintf("%d", kernelStatsMap[containerDir].cfsThrottledPeriods)
				trTimeNs := fmt.Sprintf("%d", kernelStatsMap[containerDir].cfsThrottledTimeNs)

				row := []string{
					ts, cid, name, totalCpu, quotaUs, periodUs, numPeriods, trPeriods, trTimeNs,
				}
				writer.Write(row)
				writer.Flush()
			}
		case <-stopCh:
			return
		}
	}
}
