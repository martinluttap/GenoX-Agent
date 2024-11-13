package metrics

import "time"

type CpuUsage struct {
	WorkingTime float64
	IdleTime    float64
}

type CAdvisorCpu struct {
	/*
		Docs:
		https://docs.kernel.org/scheduler/sched-bwc.html
		https://docs.kernel.org/scheduler/sched-stats.html
	*/
	timeStamp time.Time //
	// CPU Usage
	diffUsageTotalNs  int64 //
	diffUsageUserNs   int64 //
	diffUsageSystemNs int64 //

	// CFS Management
	cfsQuotaUs    int64 // run-time replenished within a period (in microseconds)
	cfsPeriodUs   int64 // the length of a period (in microseconds)
	cfsNumPeriods int64 // Number of enforcement intervals that have elapsed.

	// CFS Statistics
	cfsThrottledPeriods int64 // Number of times the group has been throttled/limited.
	cfsThrottledTimeNs  int64 // The total time duration (in nanoseconds) for which entities of the group have been throttled.

	// Schedstat Statistics
	schedstatRunTimeNs      int64 // Time spent on the CPU (nanoseconds)
	schedstatRunqueueTimeNs int64 // Time spent waiting on the runqueue (nanoseconds)
	schedstatRunPeriods     int64 // # timeslices run on CPU
}

type CfsStats struct {
	NrPeriods       int64
	NrThrottled     int64
	ThrottledTimeNs int64
}

type CtrStat struct {
	procStatCpuMap map[string]ProcStatCpu
	timestampTick  int64
	cpuUsage       float64
}

type DockerStats struct {
	containerId   string
	containerName string
	cpuUsage      float64
}

type KernelStats struct {
	// CFS Management
	cfsQuotaUs  int64 // run-time replenished within a period (in microseconds)
	cfsPeriodUs int64 // the length of a period (in microseconds)

	// CFS Statistics
	cfsNumPeriods       int64 // Number of enforcement intervals that have elapsed.
	cfsThrottledPeriods int64 // Number of times the group has been throttled/limited.
	cfsThrottledTimeNs  int64 // The total time duration (in nanoseconds) for which entities of the group have been throttled.

	// CpuAcct
	cpuacctUsage int64 // The total CPU time (in nanoseconds) consumed by all tasks in this cgroup (including tasks lower in the hierarchy)

	// PidStats Statistics Per Process
	procsPidStats map[string]PidStats

	// IO Statistics.
	// Total of all procs within the container.
	totalRchar               int64
	totalWchar               int64
	totalSyscr               int64
	totalSyscw               int64
	totalReadBytes           int64
	totalWriteBytes          int64
	totalCancelledWriteBytes int64
}

type PidStats struct {
	// Schedstat Statistics
	schedstatRunTimeNs      int64 // Time spent on the CPU (nanoseconds)
	schedstatRunqueueTimeNs int64 // Time spent waiting on the runqueue (nanoseconds)
	schedstatRunPeriods     int64 // # timeslices run on CPU

	// I/O Statistics
	rchar                 int64 // The number of bytes which this task has caused / attempted to be read from storage. This is simply the sum of bytes which this process passed to read() and pread().
	wchar                 int64 // Same as rchar, but for write.
	syscr                 int64 // num. syscalls for read.
	syscw                 int64 // num. syscalls for write.
	read_bytes            int64 // Actual amount of bytes read from storage.
	write_bytes           int64 // Same as read_bytes, but for write.
	cancelled_write_bytes int64 //
}

type ProcStatCpu struct {
	userTimeTick int64
	sysTimeTick  int64
	uptimeSec    float64
}
