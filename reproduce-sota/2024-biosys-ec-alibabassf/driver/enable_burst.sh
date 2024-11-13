#!/bin/bash

BURST_TIME=$1

echo 1 > /proc/sys/kernel/sched_cfs_bw_burst_enabled
echo ${BURST_TIME} > /sys/fs/cgroup/cpu/test/cpu.cfs_burst_us
