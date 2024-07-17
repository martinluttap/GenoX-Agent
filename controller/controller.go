package controller

import (
	"bufio"
	"fmt"
	"log"
	"os"
	"strconv"
	"sync"
	"time"

	"github.com/martinluttap/containermod/functions"
)

func TickWriter(containerDirs []string, intervalMillisecond int, stopCh chan int, wg *sync.WaitGroup) {
	defer wg.Done()

	tickCh := time.NewTicker(time.Duration(intervalMillisecond) * time.Millisecond)
	startTime := time.Now()
	for {
		select {
		case t := <-tickCh.C:
			elapsedTime := time.Since(startTime).Seconds()
			fmt.Printf("Tick at %s, elapsed: %s seconds\n", t, strconv.FormatFloat(elapsedTime, 'f', 2, 64))
			for _, containerDir := range containerDirs {
				adjustQuota(containerDir, elapsedTime)
			}

		case <-stopCh:
			fmt.Println("Ticker stopped!")
			return
		}
	}
}

func AdjustPeriod(containerDir string, modFunction func(x string) string) {
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
		infile.WriteString(newPeriod)
	}

}

func ResetQuota(containerDir string) {

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

func adjustQuota(containerDir string, elapsedTime float64) {

	path := fmt.Sprintf(`%s/cpu.cfs_quota_us`, containerDir)
	infile, openErr := os.OpenFile(path, os.O_RDWR|os.O_CREATE|os.O_TRUNC, 0644)
	if openErr != nil {
		log.Fatalf("While opening: %s:\n", openErr)
	}
	defer infile.Close()

	buckets := functions.GenerateBuckets()
	s := bufio.NewScanner(infile)
	for s.Scan() {
		oldPeriod := s.Text()
		// f(x): continuousIncrease
		// newPeriod := functions.ContinuousIncrease(elapsedTime)

		// f(x): sineWave
		// newPeriod := functions.SineWave(elapsedTime)

		// f(x): randomStep
		newPeriod := functions.RandomStep(elapsedTime, buckets)
		fmt.Printf("Old: %s, new: %s\n", oldPeriod, newPeriod)
		infile.WriteString(newPeriod)
	}
}

func StopAt(limit int, stopCh chan int, wg *sync.WaitGroup) {
	defer wg.Done()

	fmt.Printf("Stopper start at %s with limit %d!\n", time.Now(), limit)
	time.Sleep(time.Duration(limit) * time.Second)
	stopCh <- 0
}
