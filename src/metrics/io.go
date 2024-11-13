package metrics

import (
	"bufio"
	"fmt"
	"log"
	"os"
	"strconv"
	"strings"
)

func GetIOStatData(containerDir string) (int64, int64, int64, int64, int64, int64, int64) {
	// Instead of cgroup/cpu, IO statistics are found in cgroup/blkio.
	// We modify the given path to reflect this.
	ss := strings.Split(containerDir, "/")
	ss[4] = "blkio"
	newContainerDir := strings.Join(ss, "/")
	fmt.Println(newContainerDir)

	// We do not use cgroups' blkio files because there are mismatches between /proc/pid/io files and them. For example, when running BWA, cgroups' files report no write, while /proc/pid/io shows significant amount of writes. We believe /proc/pid/io is right in this case.
	procs := GetAllProcs(containerDir)
	totalRchar := int64(0)
	totalWchar := int64(0)
	totalSyscr := int64(0)
	totalSyscw := int64(0)
	totalReadBytes := int64(0)
	totalWriteBytes := int64(0)
	totalCancelledWriteBytes := int64(0)
	for _, p := range procs {
		ioInfile, openErr := os.OpenFile(fmt.Sprintf("/proc/%s/io", p), os.O_RDWR|os.O_CREATE|os.O_TRUNC, 0644)
		if openErr != nil {
			log.Fatalf("While opening: %s:\n", openErr)
		}
		defer ioInfile.Close()

		s := bufio.NewScanner(ioInfile)
		s.Scan()
		rchar, _ := strconv.ParseInt(strings.Fields(s.Text())[1], 10, 64)
		s.Scan()
		wchar, _ := strconv.ParseInt(strings.Fields(s.Text())[1], 10, 64)
		s.Scan()
		syscr, _ := strconv.ParseInt(strings.Fields(s.Text())[1], 10, 64)
		s.Scan()
		syscw, _ := strconv.ParseInt(strings.Fields(s.Text())[1], 10, 64)
		s.Scan()
		read_bytes, _ := strconv.ParseInt(strings.Fields(s.Text())[1], 10, 64)
		s.Scan()
		write_bytes, _ := strconv.ParseInt(strings.Fields(s.Text())[1], 10, 64)
		s.Scan()
		cancelled_write_bytes, _ := strconv.ParseInt(strings.Fields(s.Text())[1], 10, 64)

		totalRchar += rchar
		totalWchar += wchar
		totalSyscr += syscr
		totalSyscw += syscw
		totalReadBytes += read_bytes
		totalWriteBytes += write_bytes
		totalCancelledWriteBytes += cancelled_write_bytes
	}

	return totalRchar, totalWchar, totalSyscr, totalSyscw, totalReadBytes, totalWriteBytes, totalCancelledWriteBytes
}
