package metrics

import (
	"fmt"
	"os"
	"strings"
	"sync"
	"time"
)

func GetProcSched(activeContainersCh <-chan []string, pollingIntervalMs int, stopCh chan int, wg *sync.WaitGroup) {
	/*
		ksoftirqd/0 (10, #threads: 1)
		-------------------------------------------------------------------
		se.exec_start                                :     522982176.253902
		se.vruntime                                  :      33518562.368233
		se.sum_exec_runtime                          :          1015.129971
		se.nr_migrations                             :                    0
		nr_switches                                  :                53901
		nr_voluntary_switches                        :                53900
		nr_involuntary_switches                      :                    1
		se.load.weight                               :              1048576
		se.runnable_weight                           :              1048576
		se.avg.load_sum                              :                   12
		se.avg.runnable_load_sum                     :                   12
		se.avg.util_sum                              :                12288
		se.avg.load_avg                              :                    0
		se.avg.runnable_load_avg                     :                    0
		se.avg.util_avg                              :                    0
		se.avg.last_update_time                      :      522982176252928
		se.avg.util_est.ewma                         :                    3
		se.avg.util_est.enqueued                     :                   12
		policy                                       :                    0
		prio                                         :                  120
		clock-delta                                  :                   59
		numa_pages_migrated                          :                    0
		numa_preferred_nid                           :                   -1
		total_numa_faults                            :                    0
		current_node=0, numa_group_id=0
		numa_faults node=0 task_private=0 task_shared=0 group_private=0 group_shared=0
		numa_faults node=1 task_private=0 task_shared=0 group_private=0 group_shared=0
		numa_faults node=2 task_private=0 task_shared=0 group_private=0 group_shared=0
		numa_faults node=3 task_private=0 task_shared=0 group_private=0 group_shared=0
	*/
	/*
		Logic: during execution, we sample by interval 1 sec and copy the kernel statistics file into a temp folder. Assume execution of N seconds. We collect N files, then do a post-execution analysis of which fields changes in each file we collect. Finally, we do a correlation analysis of the fields against slowdown. The fields with biggest correlation compose our features.
	*/
	for {
		select {
		case containerDirs := <-activeContainersCh:
			for _, containerDir := range containerDirs {
				procs := GetAllProcs(containerDir)
				fmt.Printf("[%s] PROC SCHED %s: %s", time.Now().Format(time.RFC3339Nano), containerDir, procs)

				/* Create folder for `sched` */
				ss := strings.Split(containerDir, "/")
				cid := ss[len(ss)-1:][0]
				outDir := fmt.Sprintf("out-metrics/%s/sched", cid)
				os.MkdirAll(outDir, os.ModePerm)

				for _, pid := range procs {
					/* 1. Create folder for each target file */
					/* 2. For each pid, create <pid>_<statname>_<HHMMSS> */
					inPath := fmt.Sprintf("/proc/%s/sched", pid)
					infile, openErr := os.Open(inPath)
					if openErr == nil {
						// panic(fmt.Sprintf("Open error: %s", openErr))
						ts := time.Now().Format(time.TimeOnly)
						outPath := fmt.Sprintf("%s/%s_sched_%s", outDir, pid, ts)
						outfile, _ := os.Create(outPath)
						outfile.ReadFrom(infile)
						// schedScanner := bufio.NewScanner(infile)
						// for schedScanner.Scan() {
						// 	fmt.Println(schedScanner.Text())
						// }
					}
				}
			}
		case <-stopCh:
			fmt.Println("Stopped!")
		}
	}
}
func GetProcSchedStat() {
	/* 1015422855 529571569 53916 */
}
func GetProcStat() {
	/* 10 (rcu_sched) I 2 0 0 0 -1 2129984 0 0 0 0 0 54534 0 0 20 0 1 0 143 0 0 18446744073709551615 0 0 0 0 0 0 0 2147483647 0 0 0 0 17 0 0 0 0 0 0 0 0 0 0 0 0 0 0 */
}
func GetProcStatm() {
	/* 0 0 0 0 0 0 0 */
}
func GetProcStatus() {
	/*
		Name:   rcu_sched
		Umask:  0000
		State:  I (idle)
		Tgid:   10
		Ngid:   0
		Pid:    10
		PPid:   2
		TracerPid:      0
		Uid:    0       0       0       0
		Gid:    0       0       0       0
		FDSize: 64
		Groups:
		NStgid: 10
		NSpid:  10
		NSpgid: 0
		NSsid:  0
		Threads:        1
		SigQ:   0/707408
		SigPnd: 0000000000000000
		ShdPnd: 0000000000000000
		SigBlk: 0000000000000000
		SigIgn: ffffffffffffffff
		SigCgt: 0000000000000000
		CapInh: 0000000000000000
		CapPrm: 0000003fffffffff
		CapEff: 0000003fffffffff
		CapBnd: 0000003fffffffff
		CapAmb: 0000000000000000
		NoNewPrivs:     0
		Seccomp:        0
		Speculation_Store_Bypass:       thread vulnerable
		Cpus_allowed:   fffffff,ffffffff,ffffffff
		Cpus_allowed_list:      0-91
		Mems_allowed:   00000000,00000000,00000000,00000000,00000000,00000000,00000000,00000000,00000000,00000000,00000000,00000000,00000000,00000000,00000000,00000000,00000000,00000000,00000000,00000000,00000000,00000000,00000000,00000000,00000000,00000000,00000000,00000000,00000000,00000000,00000000,00000001
		Mems_allowed_list:      0
		voluntary_ctxt_switches:        17763658
		nonvoluntary_ctxt_switches:     1110
	*/
}
func GetProcWaitRes() {
	/* Only for Alibaba's burst kernel
	0 0000000000000000 0 4818086806
	*/
}

func PollBurstStats(activeContainersCh <-chan []string, pollingIntervalMs int, stopCh chan int, wg *sync.WaitGroup) {

}
