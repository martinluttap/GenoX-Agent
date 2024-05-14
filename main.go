package main

import (
	"bufio"
	"flag"
	"fmt"
	"log"
	"math"
	"math/rand/v2"
	"os"
	"path/filepath"
	"strconv"
	"sync"
	"time"
)

/****************** FUNCTIONS ******************/

func calculateNewPeriod(oldPeriod string) string {
	old, _ := strconv.ParseFloat(oldPeriod, 64)
	stepMs := int64(100000)
	new := strconv.FormatInt(int64(old)+stepMs, 10)

	return new
}

func continuousIncrease(x float64) string {
	fmt.Printf("Function called for %f\n", x)

	TARGET_CORE := 16
	INIT_CORE := 1
	START_DUR := 1
	END_DUR := 180 // 3 minutes

	// m = (y2 - y1) / (x2 - x1)
	m := float64(TARGET_CORE-INIT_CORE) / float64(END_DUR-START_DUR)

	// y = mx + c
	c := float64(0)
	y := int64(((m * x) + c) * 100000) // match cpu.cfs_quota_us, default=100000

	// newPeriod := strconv.FormatFloat(y, 'f', 2, 64)
	fmt.Printf("m:%f, x:%f, c:%f, y:%d\n", m, x, c, y)

	return strconv.FormatInt(y, 10)
}

func sineWave(x float64) string {
	// Sine wav: (A * sin(2 * Pi * f + phase)) + yOffset
	MIN_CORE := 1
	INIT_CORE := 8
	// START_DUR := 1
	// END_DUR := 180 // 3 minutes
	QUOTA_ONE_CORE := 100000

	yOffset := float64(INIT_CORE)
	amplitude := math.Max(float64(INIT_CORE-MIN_CORE), float64(1)) // Don't hit < 1
	frequency := float64(0.05)
	phase := float64(0)

	y := (amplitude * math.Sin((2*math.Pi*frequency*x)+phase)) + yOffset
	return strconv.FormatInt(int64(y*float64(QUOTA_ONE_CORE)), 10)
}

/*********************************************************/

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
	startTime := time.Now()
	for {
		select {
		case t := <-tickCh.C:
			elapsedTime := time.Since(startTime).Seconds()
			fmt.Printf("Tick at %s, elapsed: %s seconds\n", t, strconv.FormatFloat(elapsedTime, 'f', 2, 64))
			for _, containerDir := range containerDirs {

				// f(x): continuousIncrease
				// adjustQuota(containerDir, elapsedTime, continuousIncrease)

				// f(x): sineWave
				adjustQuota(containerDir, elapsedTime, sineWave)
			}

		case <-stopCh:
			fmt.Println("Ticker stopped!")
			return
		}
	}
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

func adjustQuota(containerDir string, elapsedTime float64, modFunction func(x float64) string) {

	path := fmt.Sprintf(`%s/cpu.cfs_quota_us`, containerDir)
	infile, openErr := os.OpenFile(path, os.O_RDWR|os.O_CREATE|os.O_TRUNC, 0644)
	if openErr != nil {
		log.Fatalf("While opening: %s:\n", openErr)
	}
	defer infile.Close()

	s := bufio.NewScanner(infile)
	for s.Scan() {
		oldPeriod := s.Text()
		newPeriod := modFunction(elapsedTime)
		// newPeriod := strconv.FormatFloat(elapsedTime, 'f', 1, 64)
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

func main2() {
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
	modDuration := 180

	containerDirs, _ := getSubDirs(dockerRootPath)
	fmt.Println(containerDirs)
	for _, dir := range containerDirs {
		resetQuota(dir, flagMap)
	}
	go tickWriter(containerDirs, tickIntervalMs, flagMap, stopCh, &wg)
	go stopAt(modDuration, stopCh, &wg)
	wg.Wait()
	// for _, dir := range containerDirs {
	// 	resetQuota(dir, flagMap)
	// }
}

type BucketRange[T, U any] struct {
	Begin T
	End   U
}

type StepBucket struct {
	bucket BucketRange[float64, float64]
	value  float64
}

func randRange(min, max int) int {
	return rand.IntN(max-min) + min
}

func generate_buckets() []StepBucket {
	END_DUR := 180
	V_MIN := 1
	V_MAX := 16
	H_MIN := 4
	H_MAX := 18

	totalSecs := 0
	buckets := make([]StepBucket, 0, END_DUR/H_MIN)

	for totalSecs <= END_DUR {
		nextVStep := randRange(V_MIN, V_MAX)
		nextHStep := randRange(H_MIN, H_MAX)
		if totalSecs+nextHStep >= END_DUR {
			break
		} else {
			totalSecs += nextHStep
			if len(buckets) == 0 {
				bucketRange := BucketRange[float64, float64]{Begin: 0, End: float64(nextHStep)}
				stepBucket := StepBucket{bucket: bucketRange, value: float64(nextVStep)}
				buckets = append(buckets, stepBucket)
			} else {
				lastEnd := buckets[len(buckets)-1].bucket.End
				bucketRange := BucketRange[float64, float64]{Begin: lastEnd, End: lastEnd + float64(nextHStep)}
				stepBucket := StepBucket{bucket: bucketRange, value: float64(nextVStep)}
				buckets = append(buckets, stepBucket)
			}
		}
	}
	return buckets
}

func main() {
	// for i := range 180 {
	// 	fmt.Println(sineWave(float64(i), float64(yOffset), float64(amplitude), frequency, float64(phase)))
	// }
	generate_buckets()
}
