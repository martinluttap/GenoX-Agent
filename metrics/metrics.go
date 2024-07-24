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

	// IO Statistics.
	// Total of all procs within the container.
	totalRchar               int64
	totalWchar               int64
	totalSyscr               int64
	totalSyscw               int64
	totalReadBytes           int64
	totalWriteBytes          int64
	totalCancelledWriteBytes int64
}

type PidStats struct {
	// Schedstat Statistics
	schedstatRunTimeNs      int64 // Time spent on the CPU (nanoseconds)
	schedstatRunqueueTimeNs int64 // Time spent waiting on the runqueue (nanoseconds)
	schedstatRunPeriods     int64 // # timeslices run on CPU

	// I/O Statistics
	rchar                 int64 // The number of bytes which this task has caused / attempted to be read from storage. This is simply the sum of bytes which this process passed to read() and pread().
	wchar                 int64 // Same as rchar, but for write.
	syscr                 int64 // num. syscalls for read.
	syscw                 int64 // num. syscalls for write.
	read_bytes            int64 // Actual amount of bytes read from storage.
	write_bytes           int64 // Same as read_bytes, but for write.
	cancelled_write_bytes int64 //
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

func executeCgtop(cgroup string) string {
	/*	Execute:
		systemd-cgtop -b -n 2 -d 25ms docker/6629b5c0395314ab47fd4dec05d71bea3657c0bfb8f6087feecbda6c225702ca
		---
		Output:
		ControlGroup 		 Tasks   %CPU   Memory  Input/s Output/s
		docker/6629b5...      99   25.7   257.3M        -        -
	*/
	cmd := exec.Command("systemd-cgtop", "-b", "-n", "2", "-d", "25ms", cgroup)
	var out strings.Builder
	cmd.Stdout = &out
	err := cmd.Run()
	if err != nil {
		log.Fatal(err)
	}
	return out.String()
}

func GetCpuUsageCgtop(containerDirs []string) map[string]float64 {
	/*	Execute:
		systemd-cgtop -b -n 2 -d 25ms docker/6629b5c0395314ab47fd4dec05d71bea3657c0bfb8f6087feecbda6c225702ca
		---
		Output:
		ControlGroup 		 Tasks   %CPU   Memory  Input/s Output/s
		docker/6629b5...      99   25.7   257.3M        -        -

		Return map {"docker/66...": 25.7}
	*/
	cgtopMap := map[string]float64{}
	for _, containerDir := range containerDirs {
		ss := strings.Split(containerDir, "/")
		cgroup := strings.Join(ss[len(ss)-2:], `/`)
		// We take 10 iterations with rate 0.1 ms, but it's possible that not all has cpu usage (or even any).
		// Thus, we either take the last value, or if there's no value at all, we repeat the process.
		cpuUsages := []string{}
		for len(cpuUsages) == 0 {
			out := executeCgtop(cgroup)
			allLines := strings.Fields(out)
			lineLen := 6
			for i := 0; i < len(allLines); i = i + lineLen {
				singleLine := allLines[i : i+lineLen]
				if singleLine[2] != `-` {
					cpuUsages = append(cpuUsages, singleLine[2])
				}
			}
		}
		val, _ := strconv.ParseFloat(cpuUsages[len(cpuUsages)-1], 64)
		cgtopMap[containerDir] = val
	}
	return cgtopMap
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

func GetIOStatData(containerDir string) (int64, int64, int64, int64, int64, int64, int64) {
	// Instead of cgroup/cpu, IO statistics are found in cgroup/blkio.
	// We modify the given path to reflect this.
	ss := strings.Split(containerDir, "/")
	ss[4] = "blkio"
	newContainerDir := strings.Join(ss, "/")
	fmt.Println(newContainerDir)

	// We do not use cgroups' blkio files because there are mismatches between /proc/pid/io files and them. For example, when running BWA, cgroups' files report no write, while /proc/pid/io shows significant amount of writes. We believe /proc/pid/io is right in this case.
	procs := GetAllProcs(containerDir)
	totalRchar := int64(0)
	totalWchar := int64(0)
	totalSyscr := int64(0)
	totalSyscw := int64(0)
	totalReadBytes := int64(0)
	totalWriteBytes := int64(0)
	totalCancelledWriteBytes := int64(0)
	for _, p := range procs {
		ioInfile, openErr := os.OpenFile(fmt.Sprintf("/proc/%s/io", p), os.O_RDWR|os.O_CREATE|os.O_TRUNC, 0644)
		if openErr != nil {
			log.Fatalf("While opening: %s:\n", openErr)
		}
		defer ioInfile.Close()

		s := bufio.NewScanner(ioInfile)
		s.Scan()
		rchar, _ := strconv.ParseInt(strings.Fields(s.Text())[1], 10, 64)
		s.Scan()
		wchar, _ := strconv.ParseInt(strings.Fields(s.Text())[1], 10, 64)
		s.Scan()
		syscr, _ := strconv.ParseInt(strings.Fields(s.Text())[1], 10, 64)
		s.Scan()
		syscw, _ := strconv.ParseInt(strings.Fields(s.Text())[1], 10, 64)
		s.Scan()
		read_bytes, _ := strconv.ParseInt(strings.Fields(s.Text())[1], 10, 64)
		s.Scan()
		write_bytes, _ := strconv.ParseInt(strings.Fields(s.Text())[1], 10, 64)
		s.Scan()
		cancelled_write_bytes, _ := strconv.ParseInt(strings.Fields(s.Text())[1], 10, 64)

		totalRchar += rchar
		totalWchar += wchar
		totalSyscr += syscr
		totalSyscw += syscw
		totalReadBytes += read_bytes
		totalWriteBytes += write_bytes
		totalCancelledWriteBytes += cancelled_write_bytes
	}

	return totalRchar, totalWchar, totalSyscr, totalSyscw, totalReadBytes, totalWriteBytes, totalCancelledWriteBytes
}

func GetAllProcs(containerDir string) []string {
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

	return procs
}

func GetProcsPidStats(containerDir string) map[string]PidStats {
	var procs []string
	procs = GetAllProcs(containerDir)

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
		// totalRchar, totalWchar, totalSyscr, totalSyscw, totalReadBytes, totalWriteBytes, totalCancelledWriteBytes := GetIOStatData(containerDir)

		kernelStatsD[containerDir] = KernelStats{
			cfsQuotaUs:          cfsQuota,
			cfsPeriodUs:         cfsPeriod,
			cfsNumPeriods:       nrPeriod,
			cfsThrottledPeriods: nrThrottled,
			cfsThrottledTimeNs:  throttledTime,
			// procsPidStats:       procsPidStats,
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
		headers := []string{"timestampNs", "cid", "totalCpu", "quotaUs", "periodUs", "numPeriods", "trPeriods", "trTimeNs"}
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
	timeStart := time.Now()
	fmt.Println("Polling start at ", timeStart.String())
	for {
		select {
		case tick := <-pollingTicker.C:
			fmt.Println("Active contianers", containerDirs)
			fmt.Println("Polling tick at ", tick.String())

			cgtopMap := GetCpuUsageCgtop(containerDirs)
			kernelStatsMap := BuildKernelStats(containerDirs)

			ts := strconv.FormatInt((time.Since(timeStart) * time.Millisecond).Milliseconds(), 10)
			for containerDir, writer := range outWriterDict {
				ss := strings.Split(containerDir, "/")
				cid := ss[len(ss)-1][:12]
				totalCpu := fmt.Sprintf("%.2f", cgtopMap[containerDir])
				quotaUs := fmt.Sprintf("%d", kernelStatsMap[containerDir].cfsQuotaUs)
				periodUs := fmt.Sprintf("%d", kernelStatsMap[containerDir].cfsPeriodUs)
				numPeriods := fmt.Sprintf("%d", kernelStatsMap[containerDir].cfsNumPeriods)
				trPeriods := fmt.Sprintf("%d", kernelStatsMap[containerDir].cfsThrottledPeriods)
				trTimeNs := fmt.Sprintf("%d", kernelStatsMap[containerDir].cfsThrottledTimeNs)

				row := []string{
					ts, cid, totalCpu, quotaUs, periodUs, numPeriods, trPeriods, trTimeNs,
				}
				writer.Write(row)
				writer.Flush()
			}
		case <-stopCh:
			return
		}
	}
}
