package main

import (
	"bufio"
	"flag"
	"fmt"
	"log"
	"os"
	"path/filepath"
	"strconv"
	"sync"
	"time"
)

func makeHints() map[string]string {
	hints := make(map[string]string)

	hints["cgroupName"] = `Target cgroup (e.g. 'docker')`
	hints["subsystem"] = `Cgroup subsystems.`
	hints["cpu.cfs_period_us"] = `CFS period in us, conforms to Linux's convention.`
	hints["cpu.cfs_quota_us"] = `CFS quota in us, conforms to Linux's convention.`

	return hints
}

func tickWriter(containerDirs []string, intervalMillisecond int, flagMap map[string]string, stopCh chan int, wg *sync.WaitGroup) {
	defer wg.Done()

	tickCh := time.NewTicker(time.Duration(intervalMillisecond) * time.Millisecond)
	for {
		select {
		case t := <-tickCh.C:
			fmt.Printf("Tick at %s\n", t)
			for _, containerDir := range containerDirs {
				// adjustPeriod(containerDir, flagMap)
				adjustQuota(containerDir, flagMap, calculateNewPeriod)
			}

		case <-stopCh:
			fmt.Println("Ticker stopped!")
			return
		}
	}
}

func calculateNewPeriod(oldPeriod string) string {
	old, _ := strconv.ParseFloat(oldPeriod, 64)
	stepMs := int64(100000)
	new := strconv.FormatInt(int64(old)+stepMs, 10)

	return new
}

func adjustPeriod(containerDir string, flagMap map[string]string, modFunction func(x string) string) {
	path := fmt.Sprintf(`%s/cpu.cfs_period_us`, containerDir)
	infile, openErr := os.OpenFile(path, os.O_RDWR|os.O_CREATE|os.O_TRUNC, 0644)
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
	for s.Scan() {
		oldPeriod := s.Text()
		newPeriod := modFunction(oldPeriod)
		fmt.Printf("Old: %s, new: %s\n", oldPeriod, newPeriod)
		infile.WriteString(newPeriod)
	}

}

func resetQuota(containerDir string, flagMap map[string]string) {

	path := fmt.Sprintf(`%s/cpu.cfs_quota_us`, containerDir)
	infile, openErr := os.OpenFile(path, os.O_RDWR|os.O_CREATE|os.O_TRUNC, 0644)
	if openErr != nil {
		log.Fatalf("While opening: %s:\n", openErr)
	}
	defer infile.Close()

	s := bufio.NewScanner(infile)
	for s.Scan() {
		infile.WriteString("-1")
	}
}

func adjustQuota(containerDir string, flagMap map[string]string, modFunction func(x string) string) {

	path := fmt.Sprintf(`%s/cpu.cfs_quota_us`, containerDir)
	infile, openErr := os.OpenFile(path, os.O_RDWR|os.O_CREATE|os.O_TRUNC, 0644)
	if openErr != nil {
		log.Fatalf("While opening: %s:\n", openErr)
	}
	defer infile.Close()

	s := bufio.NewScanner(infile)
	for s.Scan() {
		oldPeriod := s.Text()
		newPeriod := modFunction(oldPeriod)
		infile.WriteString(newPeriod)
	}
}

func stopAt(limit int, stopCh chan int, wg *sync.WaitGroup) {
	defer wg.Done()

	fmt.Printf("Stopper start at %s with limit %d!\n", time.Now(), limit)
	time.Sleep(time.Duration(limit) * time.Second)
	stopCh <- 0
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

func main() {
	// Log filename and timestamp for debugging
	log.SetFlags(log.Lshortfile | log.Ltime)

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

	flagMap := makeFlagMap(cgroup, subsystem, period, quota)
	stopCh := make(chan int)
	var wg sync.WaitGroup

	wg.Add(2)

	dockerRootPath := `/sys/fs/cgroup/cpu/docker/`
	tickIntervalMs := 1000
	modDuration := 6

	containerDirs, _ := getSubDirs(dockerRootPath)
	fmt.Println(containerDirs)
	for _, dir := range containerDirs {
		resetQuota(dir, flagMap)
	}
	go tickWriter(containerDirs, tickIntervalMs, flagMap, stopCh, &wg)
	go stopAt(modDuration, stopCh, &wg)
	wg.Wait()
}
