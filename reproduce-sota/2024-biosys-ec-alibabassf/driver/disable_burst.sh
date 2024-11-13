#!/bin/bash

echo 0 > /proc/sys/kernel/sched_cfs_bw_burst_enabled
echo 0 > /sys/fs/cgroup/cpu/test/cpu.cfs_burst_us
