package main

import (
	"flag"
	"fmt"
	"log"
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

func ticker(intervalSec int, stopCh chan int, wg *sync.WaitGroup) {
	defer wg.Done()

	tickCh := time.NewTicker(time.Duration(intervalSec) * time.Second)
	for {
		select {
		case t := <-tickCh.C:
			fmt.Printf("Tick at %s\n", t)

		case <-stopCh:
			fmt.Println("Ticker stopped!")
			return
		}
	}
}

func stopAt(limit int, stopCh chan int, wg *sync.WaitGroup) {
	defer wg.Done()

	fmt.Printf("Stopper start at %s with limit %d!\n", time.Now(), limit)
	time.Sleep(time.Duration(limit) * time.Second)
	stopCh <- 0
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

	flag.String("cgroup", "docker", hints["cgroupName"])
	flag.String("subsystem", "cpu", hints["subsystem"])
	flag.String("cpu.cfs_period_us", "100000", hints["cpu.cfs_period_us"])
	flag.String("cpu.cfs_quota_us", "-1", hints["cpu.cfs_quota_us"])

	flag.Parse()

	fmt.Printf("Arguments: %v!\n", flag.Args())

	stopCh := make(chan int)
	var wg sync.WaitGroup

	wg.Add(2)
	go ticker(1, stopCh, &wg)
	go stopAt(5, stopCh, &wg)
	wg.Wait()

}
