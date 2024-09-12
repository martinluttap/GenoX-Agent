package main

import (
	"flag"
	"fmt"
	"log"
	"os"
	"path/filepath"
	"slices"
	"sync"
	"time"

	"github.com/martinluttap/containermod/controller"
	"github.com/martinluttap/containermod/metrics"
	"github.com/martinluttap/containermod/policy"
)

func makeHints() map[string]string {
	hints := make(map[string]string)

	hints["cgroupName"] = `Target cgroup (e.g. 'docker')`
	hints["subsystem"] = `Cgroup subsystems.`
	hints["cpu.cfs_period_us"] = `CFS period in us, conforms to Linux's convention.`
	hints["cpu.cfs_quota_us"] = `CFS quota in us, conforms to Linux's convention.`
	hints["enableBurst"] = `Enable burstable CFS by putting 1 in /proc/sys/kernel/sched_cfs_bw_burst_enabled.`

	return hints
}

func makeFlagMap(enableBurst *string) map[string]string {
	flagMaps := make(map[string]string)

	return flagMaps
}

func watchActiveContainers(root string, intervalMs int64, activeDirsCh chan<- []string, stopCh <-chan int, wg *sync.WaitGroup) {
	defer wg.Done()

	/*
		This watcher routine do the following:
		1. Receive tick interval and a result channel. Results channel will be used by other routines
		2. Create a channel for self-use which produces a signal on each interval
		3. At each tick:
			- Poll the operating systems for active containers
			- Create list of directories for the active containers
			- Push the list to result channel
	*/

	tickCh := time.NewTicker(time.Duration(intervalMs) * time.Millisecond)
	for {
		select {
		case <-tickCh.C:
			var dirs []string
			err := filepath.WalkDir(root, func(path string, info os.DirEntry, err error) error {
				if info.IsDir() &&
					info.Name() != "buildkit" &&
					info.Name() != root {
					dirs = append(dirs, path)
				}
				return nil
			})
			if err == nil {
				// dirs[0] == root. We skip it
				activeDirsCh <- dirs[1:]
				fmt.Println("At ", time.Now().String(), " sent ", dirs[1:])
			} else {
				panic("Error when polling active containers!")
			}
		case <-stopCh:
			fmt.Println("Active container watcher stopped!")
			return
		}

	}

}

func prepareResultsFolder() {
	ex, _ := os.Executable()
	exPath := filepath.Dir(ex)
	resultsPath := fmt.Sprintf("%s/results/", exPath)
	os.MkdirAll(resultsPath, os.ModePerm)
	fmt.Println("Made folder in ", resultsPath)
}

func blockUntilNextflowSignal(dir string) {
	signalPath := fmt.Sprintf("%s/experiments/LoadDuration.txt", dir)
	_, err := os.Stat(signalPath)
	signalNotExist := os.IsNotExist(err)
	for signalNotExist {
		// Signal not exist yet
		sleepTimeMs := 500
		fmt.Printf("Signal path %s not exist yet at %s! Sleeping for %d ms\n", signalPath, time.Now().String(), sleepTimeMs)
		time.Sleep(time.Duration(sleepTimeMs) * time.Millisecond)
		_, err := os.Stat(signalPath)
		signalNotExist = os.IsNotExist(err)
	}
}

func blockUntilContainerStarts() {
	dockerRootDir := `/sys/fs/cgroup/cpu/docker/`
	var dirs []string
	noContainerExists := (len(dirs) <= 1)
	for noContainerExists {
		filepath.WalkDir(dockerRootDir, func(path string, info os.DirEntry, err error) error {
			if info.IsDir() &&
				info.Name() != "buildkit" &&
				info.Name() != "docker" {
				dirs = append(dirs, path)
			}
			return nil
		})
		noContainerExists = (len(dirs) <= 1)
		// dirs[0] == dockerRootDir. We skip it
	}
}

func StopAt(limit int, stopCh chan int, wg *sync.WaitGroup) {
	defer wg.Done()

	fmt.Printf("Stopper start at %s with limit %d!\n", time.Now(), limit)
	time.Sleep(time.Duration(limit) * time.Second)
	stopCh <- 0
}

func enableBurst() error {
	path := "/proc/sys/kernel/sched_cfs_bw_burst_enabled"
	infile, openErr := os.OpenFile(path, os.O_RDWR, 0644)
	if openErr != nil {
		panic("Error opening burst file!")
	}
	defer infile.Close()

	enabled := "1"
	_, writeErr := infile.WriteString(enabled)

	return writeErr
}

func disableBurst() error {
	path := "/proc/sys/kernel/sched_cfs_bw_burst_enabled"
	infile, openErr := os.OpenFile(path, os.O_RDWR, 0644)
	if openErr != nil {
		panic("Error opening burst file!")
	}
	defer infile.Close()

	enabled := "0"
	_, writeErr := infile.WriteString(enabled)

	return writeErr
}

func main() {
	// Log filename and timestamp for debugging
	log.SetFlags(log.Lshortfile | log.Ltime)

	// Parse commandline flags
	/*
		cgroupName 			:= Target cgroup (e.g. 'docker')
		path 				:= Absolute path. Default: "/sys/fs/cgroup/<cgroupName>"
		subsystem			:= Cgroup subsystems. Default: 'cpu'
		cpu.cfs_period_us	:= CFS period in us, conforms to Linux's convention. Default: 100000.
		cpu.cfs_quota_us	:= CFS quota in us, conforms to Linux's convention. Default: -1.
	*/
	hints := makeHints()

	// cgroup := flag.String("cgroup", "docker", hints["cgroupName"])
	// subsystem := flag.String("subsystem", "cpu", hints["subsystem"])
	// period := flag.String("cpu.cfs_period_us", "100000", hints["cpu.cfs_period_us"])
	// quota := flag.String("cpu.cfs_quota_us", "-1", hints["cpu.cfs_quota_us"])
	var (
		flagBurst      bool
		flagCfsBurstUs int64
	)
	flag.BoolVar(&flagBurst, "enable-burst", false, hints["enableBurst"])
	flag.Int64Var(&flagCfsBurstUs, "cpu.cfs_burst_us", 0, hints["cpu.cfs_burst_us"])
	flag.Parse()

	if flagBurst {
		enableBurst()
		fmt.Printf("[%s] Burst enabled!", time.Now().Format(time.RFC3339Nano))
	} else {
		disableBurst()
		fmt.Printf("[%s] Burst disabled!", time.Now().Format(time.RFC3339Nano))
	}

	/*
		Our algorithm is a follows. For each execution, we received from the user a flag indicating whether burst disabled or enabled. Following that, we decide on the amount of burst we need to allocate for each contianer. This should happen using 'monitor' pattern, since we do not have any information about active containers at this point.
	*/

	// Prepare results folder
	prepareResultsFolder()

	// Check whether Nextflow has finished loading data
	// We use the existence of file 'LoadDuration.txt' generated by Nextflow.
	dir := "/home/cc/elastic-container/containermod/"
	blockUntilNextflowSignal(dir)
	fmt.Println("Waiting until container starts ...")
	blockUntilContainerStarts()
	// sleepTime := 10
	// time.Sleep(time.Duration(sleepTime) * time.Second)

	// Spawn elasticcontainer processes
	stopCh := make(chan int)
	activeContainersCh := make(chan []string)
	var wg sync.WaitGroup

	dockerRootPath := `/sys/fs/cgroup/cpu/docker/`
	tickIntervalMs := 10
	// metricsIntervalMs := 1000
	pollingIntervalMs := 10
	monitorCpuIntervalMs := 5
	modDuration := 3600
	nonWatchIntervals := []int64{
		int64(tickIntervalMs),
		int64(pollingIntervalMs),
		int64(monitorCpuIntervalMs),
		// int64(metricsIntervalMs),
	}

	/*
		We have several go-routines with different 'tick intervals'.
		Our active container watcher becomes the starting point for all other routines' activities. Thus, its interval should be the smallest among other intervals to avoid being bottleneck.
	*/
	containerWatchIntervalMs := slices.Min(nonWatchIntervals)

	wg.Add(5)
	go StopAt(modDuration, stopCh, &wg)
	go watchActiveContainers(dockerRootPath, containerWatchIntervalMs, activeContainersCh, stopCh, &wg)
	go controller.TickWriter(activeContainersCh, tickIntervalMs, stopCh, &wg)
	// go metrics.MetricsCollection(activeContainersCh, metricsIntervalMs, stopCh, &wg)
	// go metrics.ProcFsMetricsCollection(activeContainersCh, metricsIntervalMs, stopCh, &wg)
	// go metrics.PollCAdvisor(activeContainersCh, pollingIntervalMs, stopCh, &wg)
	// go metrics.MonitorCpuUsage(activeContainersCh, monitorCpuIntervalMs, stopCh, &wg)
	// go metrics.PollAllStats(activeContainersCh, pollingIntervalMs, stopCh, &wg)
	go metrics.PollCpuStats(activeContainersCh, monitorCpuIntervalMs, stopCh, &wg)

	if flagBurst {
		go policy.DefaultBurstController(activeContainersCh, monitorCpuIntervalMs, stopCh, &wg)
	}
	// go policy.WatchAccruedBurstTime("/sys/fs/cgroup/cpu/docker/schbench")
	wg.Wait()
}
