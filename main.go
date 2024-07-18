package main

import (
	"flag"
	"fmt"
	"log"
	"os"
	"path/filepath"
	"sync"

	"github.com/martinluttap/containermod/controller"
	"github.com/martinluttap/containermod/metrics"
)

func makeHints() map[string]string {
	hints := make(map[string]string)

	hints["cgroupName"] = `Target cgroup (e.g. 'docker')`
	hints["subsystem"] = `Cgroup subsystems.`
	hints["cpu.cfs_period_us"] = `CFS period in us, conforms to Linux's convention.`
	hints["cpu.cfs_quota_us"] = `CFS quota in us, conforms to Linux's convention.`

	return hints
}

func makeFlagMap(cgroup *string, subsystem *string, period *string, quota *string) map[string]string {
	flagMaps := make(map[string]string)

	flagMaps["cgroup"] = *cgroup
	flagMaps["subsystem"] = *subsystem
	flagMaps["period"] = *period
	flagMaps["quota"] = *quota

	return flagMaps
}

func getSubDirs(root string) ([]string, error) {
	var dirs []string
	err := filepath.WalkDir(root, func(path string, info os.DirEntry, err error) error {
		if info.IsDir() &&
			info.Name() != "buildkit" &&
			info.Name() != root {
			dirs = append(dirs, path)
		}
		return nil
	})
	// dirs[0] == root. We skip it
	return dirs[1:], err
}

func prepareResultsFolder() {
	ex, _ := os.Executable()
	exPath := filepath.Dir(ex)
	resultsPath := fmt.Sprintf("%s/results/", exPath)
	os.MkdirAll(resultsPath, os.ModePerm)
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

	cgroup := flag.String("cgroup", "docker", hints["cgroupName"])
	subsystem := flag.String("subsystem", "cpu", hints["subsystem"])
	period := flag.String("cpu.cfs_period_us", "100000", hints["cpu.cfs_period_us"])
	quota := flag.String("cpu.cfs_quota_us", "-1", hints["cpu.cfs_quota_us"])
	flag.Parse()
	_ = makeFlagMap(cgroup, subsystem, period, quota)

	// Prepare results folder
	prepareResultsFolder()

	// Spawn elasticcontainer processes
	stopCh := make(chan int)
	var wg sync.WaitGroup

	wg.Add(5)

	dockerRootPath := `/sys/fs/cgroup/cpu/docker/`
	tickIntervalMs := 1000
	// metricsIntervalMs := 1000
	pollingIntervalMs := 1000
	modDuration := 180

	containerDirs, _ := getSubDirs(dockerRootPath)
	fmt.Println(containerDirs)
	for _, dir := range containerDirs {
		controller.ResetQuota(dir)
	}
	go controller.TickWriter(containerDirs, tickIntervalMs, stopCh, &wg)
	// go metrics.MetricsCollection(containerDirs, metricsIntervalMs, stopCh, &wg)
	// go metrics.ProcFsMetricsCollection(containerDirs, metricsIntervalMs, stopCh, &wg)
	go metrics.PollCAdvisor(containerDirs, pollingIntervalMs, stopCh, &wg)
	go controller.StopAt(modDuration, stopCh, &wg)

	wg.Wait()
}
