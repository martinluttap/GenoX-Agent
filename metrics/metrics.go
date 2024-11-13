package metrics

import (
	"bufio"
	"encoding/csv"
	"errors"
	"fmt"
	"log"
	"os"
	"strconv"
	"strings"
	"sync"
	"time"

	"github.com/containerd/cgroups/v3/cgroup1"
	"github.com/prometheus/procfs"
)

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

func GetCpuStatData(containerDir string) (int64, int64, int64) {
	if _, statErr := os.Stat(fmt.Sprintf("%s/cpu.stat", containerDir)); statErr == nil {
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
	} else {
		return -1, -1, -1
	}
}

func GetCpuacctUsageData(containerDir string) int64 {
	infile, openErr := os.OpenFile(fmt.Sprintf("%s/cpuacct.usage", containerDir), os.O_RDWR|os.O_CREATE|os.O_TRUNC, 0644)
	if openErr != nil {
		log.Fatalf("While opening: %s:\n", openErr)
	}
	defer infile.Close()

	s := bufio.NewScanner(infile)
	s.Scan()
	cpuUsage, _ := strconv.Atoi(s.Text())

	return int64(cpuUsage)
}

func GetCFSData(containerDir string) (int64, int64) {
	// CFS Quota
	quotaInfilePath := fmt.Sprintf("%s/cpu.cfs_quota_us", containerDir)
	if _, err := os.Stat(quotaInfilePath); errors.Is(err, os.ErrNotExist) {
		return int64(-1), int64(-1)
	}
	quotaInfile, openErr := os.OpenFile(quotaInfilePath, os.O_RDWR|os.O_CREATE|os.O_TRUNC, 0644)
	if openErr != nil {
		log.Fatalf("While opening: %s:\n", openErr)
	}
	defer quotaInfile.Close()

	quotaScanner := bufio.NewScanner(quotaInfile)
	quotaScanner.Scan()
	cfsQuota, _ := strconv.Atoi(quotaScanner.Text())

	// CFS Period
	periodInfilePath := fmt.Sprintf("%s/cpu.cfs_period_us", containerDir)
	if _, err := os.Stat(periodInfilePath); errors.Is(err, os.ErrNotExist) {
		return int64(-1), int64(-1)
	}
	periodInfile, openErr := os.OpenFile(periodInfilePath, os.O_RDWR|os.O_CREATE|os.O_TRUNC, 0644)
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
	procs := GetAllProcs(containerDir)

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
		cpuUsage := GetCpuacctUsageData(containerDir)
		// totalRchar, totalWchar, totalSyscr, totalSyscw, totalReadBytes, totalWriteBytes, totalCancelledWriteBytes := GetIOStatData(containerDir)

		kernelStatsD[containerDir] = KernelStats{
			cfsQuotaUs:          cfsQuota,
			cfsPeriodUs:         cfsPeriod,
			cfsNumPeriods:       nrPeriod,
			cfsThrottledPeriods: nrThrottled,
			cfsThrottledTimeNs:  throttledTime,
			cpuacctUsage:        cpuUsage,
			// procsPidStats:       procsPidStats,
		}
	}

	return kernelStatsD
}

func PollAllStats(activeContainersCh <-chan []string, pollingIntervalMs int, stopCh chan int, wg *sync.WaitGroup) {

	defer wg.Done()

	// containerDirs := <-activeContainersCh
	outWriterDict := map[string]*csv.Writer{}
	// csvFds := prepPollingAllStats(containerDirs, outWriterDict)
	csvFds := []*os.File{}
	// hertz, _ := GetSystemHz()
	// hertz := int64(250)
	timeStart := time.Now()
	for {
		select {
		case containerDirs := <-activeContainersCh:
			fmt.Println(time.Now().String(), "Active contianers", containerDirs)
			newFds := prepPollingAllStats(containerDirs, outWriterDict)
			csvFds = append(csvFds, newFds...)

			profileStart := time.Now()
			// cgtopMap := GetProcStatCpuCgtop(containerDirs)
			kernelStatsMap := BuildKernelStats(containerDirs)
			profileEnd := time.Now()

			ts := strconv.FormatInt((time.Since(timeStart) * time.Millisecond).Milliseconds(), 10)
			fmt.Println(outWriterDict)
			for containerDir, writer := range outWriterDict {
				ss := strings.Split(containerDir, "/")
				cid := ss[len(ss)-1][:12]
				// totalCpu := fmt.Sprintf("%.2f", cgtopMap[containerDir])
				quotaUs := fmt.Sprintf("%d", kernelStatsMap[containerDir].cfsQuotaUs)
				periodUs := fmt.Sprintf("%d", kernelStatsMap[containerDir].cfsPeriodUs)
				numPeriods := fmt.Sprintf("%d", kernelStatsMap[containerDir].cfsNumPeriods)
				trPeriods := fmt.Sprintf("%d", kernelStatsMap[containerDir].cfsThrottledPeriods)
				trTimeNs := fmt.Sprintf("%d", kernelStatsMap[containerDir].cfsThrottledTimeNs)
				cpuacctUsage := fmt.Sprintf("%d", kernelStatsMap[containerDir].cpuacctUsage)

				row := []string{
					ts, cid, quotaUs, periodUs, numPeriods, trPeriods, trTimeNs, cpuacctUsage,
				}
				fmt.Println("Wrote ", row, "to ", containerDir)
				writer.Write(row)
				writer.Flush()
				fmt.Println(writer.Error())
			}
			fmt.Printf("Writing for %d containers took %d us, start %s, end %s\n", len(containerDirs), profileEnd.Sub(profileStart).Microseconds(), timeStart.String(), profileEnd.String())
		case <-stopCh:
			for idx, fd := range csvFds {
				fmt.Printf("Closing fd for container %d: %p\n", idx, fd)
			}
			fmt.Println()
			return
		}
	}
}

func GetProcStatCpu(containerDir string, proc string, hertz int64) ProcStatCpu {
	/*
		We calculate CPU usage per container.
		The components we need:
		1. Elapsed wallclock time.
		2. CPU time per process:
			- user code, in clock ticks
			- kernel code, in clock ticks
			- (optional) children process
		3. Hertz (clock ticks per second)
		We assume grep 'CONFIG_HZ=' /boot/config-$(uname -r) is the Hertz of running kernel.

		Our pseudocode is as follow:
		- Get Hertz
		- Mark starttime of calculation
		- Given a list of containers,
		- For each container, get all procs
		- For each proc, get proc_total = (user + kernel) clock ticks
		- ctr_total = sum(proc_total / Hertz)
		- Mark endtime of calculation
		- ctr_cpu_usage = ctr_total / (endtime - starttime)
	*/
	procsInfile, openErr := os.OpenFile(fmt.Sprintf("/proc/%s/stat", proc), os.O_RDONLY, 0444)
	if openErr != nil {
		// Most probably process has finished. No need to throw error.
		// log.Fatalf("While opening: %s:\n", openErr)
	} else {
		defer procsInfile.Close()
		statScanner := bufio.NewScanner(procsInfile)
		statScanner.Scan()
		fields := strings.Fields(statScanner.Text())
		utime, _ := strconv.ParseInt(fields[13], 10, 64)
		stime, _ := strconv.ParseInt(fields[14], 10, 64)
		start, _ := strconv.ParseInt(fields[21], 10, 64)
		procTicks := utime + stime

		uptimeFile, _ := os.OpenFile("/proc/uptime", os.O_RDONLY, 0444)
		uptimeScanner := bufio.NewScanner(uptimeFile)
		uptimeScanner.Scan()
		uptime, _ := strconv.ParseFloat(strings.Fields(uptimeScanner.Text())[0], 64)

		elapsedSeconds := uptime - float64(start/hertz)
		procUsage := 100 * (float64(procTicks/hertz) / elapsedSeconds)

		fmt.Printf("ctr-%s proc-%s: utime=%d,stime=%d,time=%d,uptime=%f,elasped=%f,usage=%f\n", containerDir, proc, utime, stime, (procTicks / hertz), uptime, elapsedSeconds, procUsage)
	}

	return ProcStatCpu{}
}

func sumWorkingTime(cpuTotal procfs.CPUStat) float64 {
	// https://github.com/moby/moby/blob/master/daemon/stats_unix.go#L321
	// man 5 proc
	return (cpuTotal.User + cpuTotal.Nice + cpuTotal.System + cpuTotal.Iowait + cpuTotal.IRQ + cpuTotal.SoftIRQ + cpuTotal.Steal)
}

func PollCpuStats(activeContainersCh <-chan []string, pollingIntervalMs int, stopCh chan int, wg *sync.WaitGroup) {

	defer wg.Done()

	outWriterDict := map[string]*csv.Writer{}
	csvFds := []*os.File{}
	lastCpuMap := map[string]int64{}
	prevWall := time.Now()
	timeStart := time.Now()
	USER_HZ := 100 // getconf CLK_TCK 100
	fs, _ := procfs.NewFS("/proc")
	prevStat, _ := fs.Stat()
	prevSysCpuTotal := sumWorkingTime(prevStat.CPUTotal)

	for {
		select {
		case containerDirs := <-activeContainersCh:
			headers := []string{"timestampNs", "cid", "cidCpuPercent", "machineCpuPercent"}
			metricName := "cpu"
			newFds := PrepPollingCpuStats(containerDirs, metricName, headers, outWriterDict)
			csvFds = append(csvFds, newFds...)

			ts := strconv.FormatInt((time.Since(timeStart) * time.Nanosecond).Nanoseconds(), 10)

			deltaWall := time.Since(prevWall).Nanoseconds()
			stat, _ := fs.Stat()
			sysCpuTotal := sumWorkingTime(stat.CPUTotal)
			deltaSys := (sysCpuTotal - prevSysCpuTotal) / float64(USER_HZ) * 1e9

			for containerDir, writer := range outWriterDict {
				control, loadErr := cgroup1.Load(cgroup1.StaticPath(strings.TrimPrefix(containerDir, "/sys/fs/cgroup/cpu")))
				if loadErr != nil {
					continue
				}
				stats, statErr := control.Stat(cgroup1.IgnoreNotExist)
				if statErr != nil {
					continue
				}
				ctrCpuNs := stats.GetCPU().GetUsage().Total
				prevctrCpuNs := lastCpuMap[containerDir]
				deltaCtrCpuNs := int64(ctrCpuNs) - prevctrCpuNs

				ctrCpuUsage := strconv.FormatFloat(float64(deltaCtrCpuNs)/float64(deltaWall)/92, 'f', 2, 64)
				machineUsage := strconv.FormatFloat(deltaSys/float64(deltaWall)*100, 'f', 2, 64)

				ss := strings.Split(containerDir, "/")
				cid := ss[len(ss)-1]
				row := []string{
					ts, cid, ctrCpuUsage, machineUsage,
				}
				fmt.Printf("[%s] %s: %s (CTR), %s (MACHINE)\n", time.Now().Format(time.RFC3339Nano), cid, ctrCpuUsage, machineUsage)
				writer.Write(row)
				writer.Flush()
				fmt.Println(writer.Error())
			}
			prevSysCpuTotal = sysCpuTotal
			prevWall = time.Now()

		case <-stopCh:
			for idx, fd := range csvFds {
				fmt.Printf("Closing fd for container %d: %p\n", idx, fd)
			}
			fmt.Println()
			return
		}
	}
}

func MonitorCpuUsage(activeContainersCh <-chan []string, MonitorIntervalMs int, stopCh chan int, wg *sync.WaitGroup) {

	defer wg.Done()
	/*
		key: containerdir, val: cpu
	*/
	lastCpuMap := map[string]int64{}
	USER_HZ := 100 // getconf CLK_TCK 100
	fs, _ := procfs.NewFS("/proc")
	prevStat, _ := fs.Stat()
	prevSysCpuTotal := sumWorkingTime(prevStat.CPUTotal)
	prevWall := time.Now()
	for {
		select {
		case containerDirs := <-activeContainersCh:
			stat, _ := fs.Stat()
			sysCpuTotal := sumWorkingTime(stat.CPUTotal)
			deltaSys := (sysCpuTotal - prevSysCpuTotal) / float64(USER_HZ) * 1e9
			for _, containerDir := range containerDirs {

				control, loadErr := cgroup1.Load(cgroup1.StaticPath(strings.TrimPrefix(containerDir, "/sys/fs/cgroup/cpu")))
				if loadErr != nil {
					continue
				}
				stats, statErr := control.Stat(cgroup1.IgnoreNotExist)
				if statErr != nil {
					continue
				}
				cpuNs := stats.GetCPU().GetUsage().Total
				prevCpuNs := lastCpuMap[containerDir]

				deltaWall := time.Since(prevWall).Nanoseconds()
				deltaCpuNs := int64(cpuNs) - prevCpuNs

				fmt.Println(stat.CPUTotal, stat.CPUTotal.User, stat.CPUTotal.System, prevStat.CPUTotal)
				// numCpus := len(stat.CPU) // Assume num. CPU == online CPUs
				cpuUsage := (float64(deltaCpuNs) / float64(deltaWall) * 100)
				machineUsage := (deltaSys / float64(deltaWall) * 100)

				fmt.Printf("[%s] %s, deltaCpuNs:%d, deltaSys:%f, deltaWall: %f, CPU Util.: %f, Sys. Util.: %f\n", time.Now(), containerDir, deltaCpuNs, deltaSys, float64(deltaWall), cpuUsage, machineUsage)

				lastCpuMap[containerDir] = int64(cpuNs)
			}
			prevSysCpuTotal = sysCpuTotal
			prevWall = time.Now()
		case <-stopCh:
			fmt.Println()
			return
		}
	}
}

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

			fmt.Println("Container Dirs: ", containerDirs)
			for _, containerDir := range containerDirs {
				cgroupSlice := NewCGroupSlice(containerDir)
				fmt.Println(cgroupSlice)
			}

			// fmt.Println(cgroupSlice.resourceStat.cpu)

		case <-stopCh:
			for idx, fd := range csvFds {
				fmt.Printf("Closing fd for container %d: %p\n", idx, fd)
			}
			fmt.Println()
			return
		}
	}
}
