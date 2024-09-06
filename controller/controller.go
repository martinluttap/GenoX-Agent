package controller

import (
	"bufio"
	"errors"
	"fmt"
	"log"
	"os"
	"strconv"
	"strings"
	"sync"
	"time"

	"github.com/martinluttap/containermod/functions"
)

func TickWriter(activeContainersCh <-chan []string, intervalMillisecond int, stopCh chan int, wg *sync.WaitGroup) {
	defer wg.Done()

	tickCh := time.NewTicker(time.Duration(intervalMillisecond) * time.Millisecond)
	startTime := time.Now()
	for {
		select {
		// We guarantee in main that containerDirs is produced at the same rate, or faster, than tick
		case containerDirs := <-activeContainersCh:
			<-tickCh.C
			if len(containerDirs) > 0 {
				fmt.Println("Tick writing at ", time.Now().String())
				elapsedTime := time.Since(startTime).Seconds()

				numTargets := 1
				targetContainers := containerDirs[:numTargets]
				controlVariableContainers := containerDirs[numTargets:]
				for _, containerDir := range targetContainers {
					ss := strings.Split(containerDir, "/")
					cid := ss[len(ss)-1]
					fmt.Println("Adjusting quota for ", cid)
					adjustQuota(containerDir, elapsedTime, "numThreads")
				}
				for _, containerDir := range controlVariableContainers {
					ss := strings.Split(containerDir, "/")
					cid := ss[len(ss)-1]
					fmt.Println("Adjusting quota for ", cid)
					adjustQuota(containerDir, elapsedTime, "constant")
				}
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

func adjustQuota(containerDir string, elapsedTime float64, functionName string) {

	path := fmt.Sprintf(`%s/cpu.cfs_quota_us`, containerDir)
	if _, err := os.Stat(path); errors.Is(err, os.ErrNotExist) {
		// path/to/whatever does not exist
		return
	}
	infile, openErr := os.OpenFile(path, os.O_RDWR|os.O_CREATE|os.O_TRUNC, 0644)
	if openErr != nil {
		log.Fatalf("While opening: %s:\n", openErr)
	}
	defer infile.Close()

	// buckets := functions.GenerateBuckets()
	s := bufio.NewScanner(infile)
	var newPeriod string
	allowedFunctions := map[string]bool{"constant": true, "continuousIncrease": true, "continuousDecrease": true, "numThreads": true, "sineWave": true, "randomStep": true}
	for s.Scan() {
		oldPeriod := s.Text()
		// f(x): constant
		if functionName == "constant" {
			allocatedCores := int64(1)
			newPeriod = strconv.FormatInt(allocatedCores*100000, 10)
		} else if functionName == "continuousIncrease" {
			// f(x): continuousIncrease
			newPeriod = functions.ContinuousIncrease(elapsedTime)
		} else if functionName == "continuousDecrese" {
			// f(x): continousDecrease
			fromCore := int64(16)
			toCore := int64(1)
			newPeriod = functions.ContinousDecrease(elapsedTime, fromCore, toCore)
		} else if functionName == "numThreads" {
			// f(x): by task
			newPeriod = functions.NumThreads(containerDir)
		} else if functionName == "sineWave" {
			// f(x): sineWave
			newPeriod = functions.SineWave(elapsedTime)
		} else if functionName == "randomStep" {
			// f(x): randomStep
			// buckets :=
			// newPeriod = functions.RandomStep(elapsedTime, buckets)
			newPeriod = oldPeriod
		} else if functionName == "cappedNumThreads" {
			newPeriod = functions.CappedNumThreads(containerDir, 64)
		}
		if val, ok := allowedFunctions[functionName]; !ok {
			fmt.Println("Function ", val, " not allowed!")
		} else {
			fmt.Println("Adjusted for ", functionName)
		}
		if newPeriod == "" {
			panic("Empty new period!!")
		}
		fmt.Printf("Old: %s, new: %s\n", oldPeriod, newPeriod)
		infile.WriteString(newPeriod)
	}
}
