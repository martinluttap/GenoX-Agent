package policy

import (
	"bufio"
	"fmt"
	"os"
	"strconv"
	"sync"
	"time"
)

func getBurstValue(containerDir string) int64 {
	burstPath := fmt.Sprintf("%s/cpu.cfs_burst_us", containerDir)
	infile, openErr := os.OpenFile(burstPath, os.O_RDWR, 06444)

	if openErr != nil {
		panic(fmt.Sprintf("[%s] Unable to open burst file for %s", time.Now().Format(time.RFC3339Nano), containerDir))
	}

	scanner := bufio.NewScanner(infile)
	scanner.Scan()
	burstValueUs, _ := strconv.ParseInt(scanner.Text(), 10, 64)
	return burstValueUs
}

func setBurstValue(containerDir string, newValue int64) {
	burstPath := fmt.Sprintf("%s/cpu.cfs_burst_us", containerDir)
	infile, openErr := os.OpenFile(burstPath, os.O_RDWR, 06444)

	if openErr != nil {
		panic(fmt.Sprintf("[%s] Unable to open burst file for %s", time.Now().Format(time.RFC3339Nano), containerDir))
	}
	defer infile.Close()

	infile.WriteString(strconv.FormatInt(newValue, 10))
	fmt.Printf("[%s] %s WRITING :%d\n", time.Now().Format(time.RFC3339Nano), containerDir, newValue)
	// scanner := bufio.NewScanner(infile)
	// for scanner.Scan() {
	// oldBurstUs, _ := (strconv.ParseInt(scanner.Text(), 10, 64))
	// }
}

func DefaultBurstController(activeContainersCh <-chan []string, intervalMillisecond int, stopCh chan int, wg *sync.WaitGroup) {

	/*
		When kernel burst is enabled, for each of active container,
		we set the burst value to an integer N multiple of current quota value.
	*/
	for {
		select {
		case containerDirs := <-activeContainersCh:
			for _, containerDir := range containerDirs {
				/*
					Third-party packages do not support burstable CFS, so we need to build our own cfs_burst_us control utilities here.
				*/
				// burstValueUs := getBurstValue(containerDir)
				setBurstValue(containerDir, 400000)
				// if burstValueUs == 0 {
				// 	fmt.Printf("[%s] %s SET TO 100000 current burst: %d\n", time.Now().Format(time.RFC3339Nano), containerDir, burstValueUs)
				// 	setBurstValue(containerDir, 100000)
				// } else {
				// 	fmt.Printf("[%s] %s SET TO 0 current burst: %d\n", time.Now().Format(time.RFC3339Nano), containerDir, burstValueUs)
				// 	setBurstValue(containerDir, 0)
			}
		}
	}
}
