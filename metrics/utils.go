package metrics

import (
	"bufio"
	"errors"
	"fmt"
	"log"
	"os"
	"strconv"
	"strings"
	"syscall"
)

type ProcParser struct {
	pid           int64
	pathDir       string
	pathSched     string
	pathSchedStat string
	pathStat      string
	pathStatM     string
	pathStatus    string
	pathWaitRes   string
}

type ProcSched struct {
	/* /proc/<pid>/sched */
	pid                   int64
	name                  string
	numThreads            int32
	execStart             float32
	vruntime              float32
	sumExecRuntime        float32
	nrMigrations          int32
	nrSwitches            int32
	nrVoluntarySwitches   int32
	nrInvoluntarySwitches int32
	loadWeight            int32
	runnableWeight        int32
	avgLoadSum            int32
	avgRunnableLoadSum    int32
	avgUtilSum            int32
	avgLoadAvg            int32
	avgRunnableLoadAvg    int32
	avgUtilAvg            int32
	avgLastUpdateTime     int32
	avgUtilEstEWMA        int32
	avgUtilEstEnqueued    int32
	policy                int32
	prio                  int32
	clockDelta            int32
	mmNumaScanSeq         int32
	numaPagesMigrated     int32
	numaPreferredNid      int32
	totalNumaFaults       int32
	currentNode           int32
	numaGroupId           int32
}

func (parser *ProcParser) NewProcParser(pid string) {
	parser.pathDir = fmt.Sprintf("/proc/%s/", pid)
	parser.pathSched = fmt.Sprintf("/proc/%s/sched", pid)
	parser.pathSchedStat = fmt.Sprintf("/proc/%s/schedstat", pid)
	parser.pathStat = fmt.Sprintf("/proc/%s/stat", pid)
	parser.pathStatM = fmt.Sprintf("/proc/%s/statm", pid)
	parser.pathStatus = fmt.Sprintf("/proc/%s/status", pid)
	parser.pathWaitRes = fmt.Sprintf("/proc/%s/wait_res", pid)

}

// func (parser *ProcParser) ParseProcSched(pid string) map[string]float64 {
// if parser.pathSched == "" {
// 	panic(fmt.Sprintf("Parser %d pathSched empty!", pid))
// }
// infile, openErr := os.Open(parser.pathSched)
// if openErr == nil {
// s := bufio.NewScanner(infile)
// for s.Scan() {
// 	return
// }
// }
// }

// A utility to convert the values to proper strings.
func int8ToStr(arr []int8) string {
	b := make([]byte, 0, len(arr))
	for _, v := range arr {
		if v == 0x00 {
			break
		}
		b = append(b, byte(v))
	}
	return string(b)
}

func GetSystemHz() (int64, error) {
	var uname syscall.Utsname
	if err := syscall.Uname(&uname); err == nil {
		// extract members:
		// type Utsname struct {
		//  Sysname    [65]int8
		//  Nodename   [65]int8
		//  Release    [65]int8
		//  Version    [65]int8
		//  Machine    [65]int8
		//  Domainname [65]int8
		// }
		fmt.Println(
			int8ToStr(uname.Release[:]),
		)
	}
	kernelRelease := int8ToStr(uname.Release[:])
	fmt.Println("GetSystemHz()", kernelRelease)
	bootConfigFile, openErr := os.OpenFile(fmt.Sprintf("/boot/config-%s", kernelRelease), os.O_RDONLY, 0444)
	if openErr != nil {
		log.Fatalf("While opening: %s:\n", openErr)
	}
	defer bootConfigFile.Close()

	// Get all procs associated with container
	s := bufio.NewScanner(bootConfigFile)
	s.Scan()
	fmt.Println("Test", s.Text())
	var hertz string
	for s.Scan() {
		fmt.Println(s.Text())
		if strings.Contains(s.Text(), "CONFIG_HZ=") {
			hertz = strings.Split(s.Text(), "=")[1]
			fmt.Println(hertz)
			break
		}
	}
	if hertz != "" {
		hzValue, _ := strconv.ParseInt(hertz, 10, 64)
		return hzValue, nil
	} else {
		return 0, errors.New("Failed to read system hertz!")
	}
}

func GetAllProcs(containerDir string) []string {
	var procs []string
	if _, err := os.Stat("/path/to/whatever"); err == nil {
		procsInfile, openErr := os.Open(fmt.Sprintf("%s/cgroup.procs", containerDir))
		if openErr != nil {
			log.Fatalf("While opening: %s:\n", openErr)
		}
		defer procsInfile.Close()
		// Get all procs associated with container
		s := bufio.NewScanner(procsInfile)
		for s.Scan() {
			procs = append(procs, strings.TrimSpace(s.Text()))
		}
	}
	return procs
}
