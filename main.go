package main

import (
	"bufio"
	"flag"
	"fmt"
	"log"
	"os"
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

func tickWriter(intervalSec int, flagMap map[string]string, stopCh chan int, wg *sync.WaitGroup) {
	defer wg.Done()

	tickCh := time.NewTicker(time.Duration(intervalSec) * time.Second)
	for {
		select {
		case t := <-tickCh.C:
			fmt.Printf("Tick at %s\n", t)
			dynamicWrite(flagMap)

		case <-stopCh:
			fmt.Println("Ticker stopped!")
			return
		}
	}
}

func calculateNewPeriod(oldPeriod string) string {
	old, _ := strconv.ParseFloat(oldPeriod, 64)
	fmt.Println("Old", old)
	interval := int64(10000)
	new := strconv.FormatInt(int64(old)+interval, 10)
	fmt.Println("New", new)

	return new
}

func dynamicWrite(flagMap map[string]string) {

	fmt.Printf("Arguments: %v!\n", flagMap)
	path := `/sys/fs/cgroup/cpu/docker/cpu.cfs_period_us`
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
		newPeriod := calculateNewPeriod(oldPeriod)
		fmt.Printf("Old: %s, new: %s\n", oldPeriod, newPeriod)
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
	go tickWriter(1, flagMap, stopCh, &wg)
	go stopAt(5, stopCh, &wg)
	wg.Wait()

}
