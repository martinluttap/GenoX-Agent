package metrics

import (
	"bufio"
	"fmt"
	"log"
	"math"
	"os"
	"regexp"
	"strconv"
	"strings"
	"time"
)

/*
	Documentation: https://www.kernel.org/doc/Documentation/cgroup-v2.txt
*/

const (
	subtreeControl = "cgroup.subtree_control"
	controller     = "cgroup.controllers"
)

type CPUPressure struct {
	someAvgPerc10s  float64
	someAvgPerc60s  float64
	someAvgPerc300s float64
	someTotalUs     int64
	fullAvgPerc10s  float64
	fullAvgPerc60s  float64
	fullAvgPerc300s float64
	fullTotalUs     int64
}

type CPUStat struct {
	usageUs       int64
	userUs        int64
	systemUs      int64
	nrPeriods     int64
	nrThrottled   int64
	throttledUsec int64
}

type IOStat struct {
	major               int64
	minor               int64
	totalReadBytes      int64
	totalWriteBytes     int64
	totalDiscardedBytes int64
	totalReadIOs        int64
	totalWriteIOs       int64
	totalDiscardedIOs   int64
}

type IOPressure struct {
	someAvgPerc10s  float64
	someAvgPerc60s  float64
	someAvgPerc300s float64
	someTotalUs     int64
	fullAvgPerc10s  float64
	fullAvgPerc60s  float64
	fullAvgPerc300s float64
	fullTotalUs     int64
}

type CPU struct {
	idle       int64
	quotaUs    int64 // We assign 0 for 'max'
	periodUs   int64
	burstUs    int64
	pressure   *CPUPressure
	stat       *CPUStat
	uclampMin  float64
	uclampMax  float64 // We assign 0 for 'max'
	weight     int64
	weightNice int64
}

type IO struct {
	max       int64
	pressure  *IOPressure
	prioClass string
	stat      *IOStat
	weight    int64 // The weights are in the range [1, 10000] and specifies the relative amount IO time the cgroup can use in relation to its siblings.
}

type ResourceStat struct {
	// cpuset cpu io memory hugetlb pids rdma misc
	cpu *CPU
	// CPUSet  *CPUSet
	io *IO
	// Memory  *Memory
	// HugeTLB *HugeTLB
	// PIDs    *PIDs
	// RDMA    *RDMA
	// Misc    *Misc
	timestampUs int64
}

const (
	rootPath          = "/sys/fs/cgroup"
	cpuIdleFile       = "cpu.idle"
	cpuMaxFile        = "cpu.max"
	cpuMaxBurstFile   = "cpu.max.burst"
	cpuPressureFile   = "cpu.pressure"
	cpuStatFile       = "cpu.stat"
	cpuUclampMinFile  = "cpu.uclamp.min"
	cpuUclampMaxFile  = "cpu.uclamp.max"
	cpuWeightFile     = "cpu.weight"
	cpuWeightNiceFile = "cpu.weight.nice"

	ioMaxFile       = "io.max"
	ioPressureFile  = "io.pressure"
	ioPrioClassFile = "io.prio_class"
	ioStatFile      = "io.stat"
	ioWeightFile    = "io.weight"
)

type CGroupSlice struct {
	slicePath    string
	resourceStat *ResourceStat
	cpuUtil      float64
}

func NewCGroupSlice(slicePath string) *CGroupSlice {
	rs := GetResourceStat(slicePath)
	return &CGroupSlice{
		slicePath:    slicePath,
		resourceStat: rs,
		cpuUtil:      -1,
	}
}

func (c *CGroupSlice) GetTimestamp() int64 {
	return c.resourceStat.timestampUs
}

func (c *CGroupSlice) GetCpuUtil(newStat *ResourceStat, oldStat *ResourceStat) float64 {
	deltaCpuUsage := math.Abs(float64(newStat.cpu.stat.usageUs - oldStat.cpu.stat.usageUs))
	deltaWallUs := math.Abs(float64(newStat.timestampUs - oldStat.timestampUs))

	fmt.Printf("deltaCpuUsage=%f, deltaWallUs=%f\n", deltaCpuUsage, deltaWallUs)

	return float64(deltaCpuUsage / deltaWallUs * 100)
}

func (c *CGroupSlice) UpdateResourceStat() {
	oldStat := c.resourceStat
	c.resourceStat = GetResourceStat(c.slicePath)
	c.cpuUtil = c.GetCpuUtil(c.resourceStat, oldStat)
}

func (c *CGroupSlice) updateResourceStat() {
	c.resourceStat = GetResourceStat(c.slicePath)
}

// func GetDeltaResourceStat(slicePath string) *ResourceStat {

// }

func GetResourceStat(slicePath string) *ResourceStat {
	rs := &ResourceStat{
		cpu: &CPU{},
		io:  &IO{},
	}

	rs.cpu = GetCPUStat(slicePath)
	rs.io = GetIOStat(slicePath)

	// Read CPU stat

	// Read IO stat

	rs.timestampUs = time.Now().UnixMicro()

	return rs
}

func GetIOStat(slicePath string) *IO {
	io := &IO{}
	// io.max = ParseIOMaxFile(slicePath)
	io.pressure = ParseIOPressureFile(slicePath)
	// io.prioClass = ParseIOPrioClassFile(slicePath)
	io.stat = ParseIOStatFile(slicePath)
	// io.weight = ParseIOWeightFile(slicePath)

	return io
}

func ParseIOStatFile(slicePath string) *IOStat {
	filePath := fmt.Sprintf("%s/%s", slicePath, ioStatFile)
	procsInfile, openErr := os.OpenFile(filePath, os.O_RDONLY, 0644)
	if openErr != nil {
		log.Fatalf("While opening: %s:\n", openErr)
	}
	defer procsInfile.Close()

	scanner := bufio.NewScanner(procsInfile)
	ioStat := &IOStat{}
	for scanner.Scan() {
		line := scanner.Text()
		fields := strings.Fields(line)
		if len(fields) < 2 {
			log.Fatalf("Invalid line: %s\n", line)
		}
		rePattern := regexp.MustCompile(`(\d+):(\d+) rbytes=(\d+) wbytes=(\d+) rios=(\d+) wios=(\d+) dbytes=(\d+) dios=(\d+)`)
		matches := rePattern.FindAllStringSubmatch(line, -1)
		ioStat.major, _ = strconv.ParseInt(matches[0][1], 10, 64)
		ioStat.minor, _ = strconv.ParseInt(matches[0][2], 10, 64)
		ioStat.totalReadBytes, _ = strconv.ParseInt(matches[0][3], 10, 64)
		ioStat.totalWriteBytes, _ = strconv.ParseInt(matches[0][4], 10, 64)
		ioStat.totalReadIOs, _ = strconv.ParseInt(matches[0][5], 10, 64)
		ioStat.totalWriteIOs, _ = strconv.ParseInt(matches[0][6], 10, 64)
		ioStat.totalDiscardedBytes, _ = strconv.ParseInt(matches[0][7], 10, 64)
		ioStat.totalDiscardedIOs, _ = strconv.ParseInt(matches[0][8], 10, 64)
	}
	return ioStat
}

func ParseIOPressureFile(slicePath string) *IOPressure {
	filePath := fmt.Sprintf("%s/%s", slicePath, ioPressureFile)
	procsInfile, openErr := os.OpenFile(filePath, os.O_RDONLY, 0644)
	if openErr != nil {
		log.Fatalf("While opening: %s:\n", openErr)
	}
	defer procsInfile.Close()

	scanner := bufio.NewScanner(procsInfile)
	ioPressure := &IOPressure{}
	rePattern := regexp.MustCompile(`(\w+) avg10=([0-9]*[.]?[0-9]+) avg60=([0-9]*[.]?[0-9]+) avg300=([0-9]*[.]?[0-9]+) total=(\d+)`)
	for scanner.Scan() {
		line := scanner.Text()
		matches := rePattern.FindAllStringSubmatch(line, -1)
		if len(matches) > 1 {
			panic("Pressure line matches more than one")
		}
		pressureType := matches[0][1]
		vals := matches[0][2:]
		if pressureType == "some" {
			ioPressure.someAvgPerc10s, _ = strconv.ParseFloat(vals[0], 64)
			ioPressure.someAvgPerc60s, _ = strconv.ParseFloat(vals[1], 64)
			ioPressure.someAvgPerc300s, _ = strconv.ParseFloat(vals[2], 64)
			ioPressure.someTotalUs, _ = strconv.ParseInt(vals[3], 10, 64)
		} else if pressureType == "full" {
			ioPressure.fullAvgPerc10s, _ = strconv.ParseFloat(vals[0], 64)
			ioPressure.fullAvgPerc60s, _ = strconv.ParseFloat(vals[1], 64)
			ioPressure.fullAvgPerc300s, _ = strconv.ParseFloat(vals[2], 64)
			ioPressure.fullTotalUs, _ = strconv.ParseInt(vals[3], 10, 64)
		} else {
			log.Fatalf("Invalid line: %s\n", line)
		}
	}

	return ioPressure
}

func GetCPUStat(slicePath string) *CPU {
	cpu := &CPU{}
	cpu.idle = ParseCPUIdleFile(slicePath)
	cpu.quotaUs, cpu.periodUs = ParseCPUMaxFile(slicePath)
	cpu.burstUs = ParseCPUMaxBurstFile(slicePath)
	cpu.pressure = ParseCPUPressureFile(slicePath)
	cpu.stat = ParseCPUStatFile(slicePath)
	cpu.uclampMin = ParseCPUUclampMinFile(slicePath)
	cpu.uclampMax = ParseCPUUclampMaxFile(slicePath)
	cpu.weight = ParseCPUWeightFile(slicePath)
	cpu.weightNice = ParseCPUWeightNiceFile(slicePath)

	return cpu
}

func ParseCPUPressureFile(slicePath string) *CPUPressure {
	filePath := fmt.Sprintf("%s/%s", slicePath, cpuPressureFile)
	procsInfile, openErr := os.OpenFile(filePath, os.O_RDONLY, 0644)
	if openErr != nil {
		log.Fatalf("While opening: %s:\n", openErr)
	}
	defer procsInfile.Close()

	scanner := bufio.NewScanner(procsInfile)
	cpuPressure := &CPUPressure{}
	rePattern := regexp.MustCompile(`(\w+) avg10=([0-9]*[.]?[0-9]+) avg60=([0-9]*[.]?[0-9]+) avg300=([0-9]*[.]?[0-9]+) total=(\d+)`)
	for scanner.Scan() {
		line := scanner.Text()
		matches := rePattern.FindAllStringSubmatch(line, -1)
		if len(matches) > 1 {
			panic("Pressure line matches more than one")
		}
		pressureType := matches[0][1]
		vals := matches[0][2:]
		if pressureType == "some" {
			cpuPressure.someAvgPerc10s, _ = strconv.ParseFloat(vals[0], 64)
			cpuPressure.someAvgPerc60s, _ = strconv.ParseFloat(vals[1], 64)
			cpuPressure.someAvgPerc300s, _ = strconv.ParseFloat(vals[2], 64)
			cpuPressure.someTotalUs, _ = strconv.ParseInt(vals[3], 10, 64)
		} else if pressureType == "full" {
			cpuPressure.fullAvgPerc10s, _ = strconv.ParseFloat(vals[0], 64)
			cpuPressure.fullAvgPerc60s, _ = strconv.ParseFloat(vals[1], 64)
			cpuPressure.fullAvgPerc300s, _ = strconv.ParseFloat(vals[2], 64)
			cpuPressure.fullTotalUs, _ = strconv.ParseInt(vals[3], 10, 64)
		} else {
			log.Fatalf("Invalid line: %s\n", line)
		}
	}

	return cpuPressure
}

func ParseCPUStatFile(slicePath string) *CPUStat {
	filePath := fmt.Sprintf("%s/%s", slicePath, cpuStatFile)
	procsInfile, openErr := os.OpenFile(filePath, os.O_RDONLY, 0644)
	if openErr != nil {
		log.Fatalf("While opening: %s:\n", openErr)
	}
	defer procsInfile.Close()

	scanner := bufio.NewScanner(procsInfile)
	cpuStat := &CPUStat{}
	for scanner.Scan() {
		line := scanner.Text()
		fields := strings.Fields(line)
		if len(fields) < 2 {
			log.Fatalf("Invalid line: %s\n", line)
		}
		key, val := fields[0], fields[1]
		valInt, _ := strconv.ParseInt(val, 10, 64)
		switch key {
		case "usage_usec":
			cpuStat.usageUs = valInt
		case "user_usec":
			cpuStat.userUs = valInt
		case "system_usec":
			cpuStat.systemUs = valInt
		case "nr_periods":
			cpuStat.nrPeriods = valInt
		case "nr_throttled":
			cpuStat.nrThrottled = valInt
		case "throttled_usec":
			cpuStat.throttledUsec = valInt
		}
	}
	return cpuStat
}

func ParseCPUUclampMinFile(slicePath string) float64 {
	filePath := fmt.Sprintf("%s/%s", slicePath, cpuUclampMinFile)
	return ReadFloat64FromFile(filePath)
}

func ParseCPUUclampMaxFile(slicePath string) float64 {
	filePath := fmt.Sprintf("%s/%s", slicePath, cpuUclampMaxFile)
	procsInfile, openErr := os.OpenFile(filePath, os.O_RDONLY, 0644)
	if openErr != nil {
		log.Fatalf("While opening: %s:\n", openErr)
	}
	defer procsInfile.Close()

	scanner := bufio.NewScanner(procsInfile)
	ret := float64(-1)
	for scanner.Scan() {
		line := scanner.Text()
		if line == "max" {
			ret = 0
		} else {
			val, err := strconv.ParseFloat(line, 64)
			if err != nil {
				log.Fatalf("While parsing: %s:\n", err)
			}
			ret = val
		}
	}
	return ret
}

func ParseBurstUs(slicePath string) int64 {
	filePath := fmt.Sprintf("%s/%s", slicePath, cpuMaxBurstFile)
	return ReadInt64FromFile(filePath)
}

func ParseCPUMaxFile(slicePath string) (int64, int64) {
	filePath := fmt.Sprintf("%s/%s", slicePath, cpuMaxFile)
	procsInfile, openErr := os.OpenFile(filePath, os.O_RDONLY, 0644)
	if openErr != nil {
		log.Fatalf("While opening: %s:\n", openErr)
	}
	defer procsInfile.Close()

	scanner := bufio.NewScanner(procsInfile)
	for scanner.Scan() {
		line := scanner.Text()
		fields := strings.Fields(line)
		quotaUsStr, periodUsStr := fields[0], fields[1]
		periodUs, _ := strconv.ParseInt(periodUsStr, 10, 64)
		if quotaUsStr == "max" {
			return 0, periodUs
		} else {
			quotaUs, _ := strconv.ParseInt(quotaUsStr, 10, 64)
			return quotaUs, periodUs
		}
	}
	return -1, -1
}

func ParseCPUIdleFile(slicePath string) int64 {
	filePath := fmt.Sprintf("%s/%s", slicePath, cpuIdleFile)
	return ReadInt64FromFile(filePath)
}

func ParseCPUWeightFile(slicePath string) int64 {
	filePath := fmt.Sprintf("%s/%s", slicePath, cpuWeightFile)
	return ReadInt64FromFile(filePath)
}

func ParseCPUWeightNiceFile(slicePath string) int64 {
	filePath := fmt.Sprintf("%s/%s", slicePath, cpuWeightNiceFile)
	return ReadInt64FromFile(filePath)
}

func ParseCPUMaxBurstFile(slicePath string) int64 {
	filePath := fmt.Sprintf("%s/%s", slicePath, cpuMaxBurstFile)
	return ReadInt64FromFile(filePath)
}

func ReadFloat64FromFile(filePath string) float64 {
	procsInfile, openErr := os.OpenFile(filePath, os.O_RDONLY, 0644)
	if openErr != nil {
		log.Fatalf("While opening: %s:\n", openErr)
	}
	defer procsInfile.Close()

	scanner := bufio.NewScanner(procsInfile)
	for scanner.Scan() {
		val, err := strconv.ParseFloat(scanner.Text(), 64)
		if err == nil {
			return val
		} else {
			log.Fatalf("While parsing: %s:\n", err)
		}
	}
	return -1
}

func ReadInt64FromFile(filePath string) int64 {
	procsInfile, openErr := os.OpenFile(filePath, os.O_RDONLY, 0644)
	if openErr != nil {
		log.Fatalf("While opening: %s:\n", openErr)
	}
	defer procsInfile.Close()

	scanner := bufio.NewScanner(procsInfile)
	for scanner.Scan() {
		val, err := strconv.ParseInt(scanner.Text(), 10, 64)
		if err == nil {
			return val
		} else {
			log.Fatalf("While parsing: %s:\n", err)
		}
	}
	return -1
}
