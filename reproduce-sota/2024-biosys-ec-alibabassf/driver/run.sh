#!/bin/bash

echo "Clear PageCache, dentries, indoes, and swap."
# Clear PageCache, dentries, indoes, and swap
sudo sync; echo 3 | sudo tee /proc/sys/vm/drop_caches ; sudo swapoff -a && sudo swapon -a

# Setup period, quota, etc
echo $$ > /sys/fs/cgroup/cpu/test/cgroup.procs
echo 100000 > /sys/fs/cgroup/cpu/test/cpu.cfs_period_us

# Sanity check
echo "Run at $(date) ..." 
echo -n "Period: " ; cat /sys/fs/cgroup/cpu/test/cpu.cfs_period_us
echo -n "Quota: " ; cat /sys/fs/cgroup/cpu/test/cpu.cfs_quota_us
echo -n "Burst Enabled: " ; cat /proc/sys/kernel/sched_cfs_bw_burst_enabled
echo -n "Burst: " ; cat /sys/fs/cgroup/cpu/test/cpu.cfs_burst_us
echo ""
echo ""

RUN=3
BURST=$(cat /sys/fs/cgroup/cpu/test/cpu.cfs_burst_us)

echo "Snapshot cpu.stat before test ..."
cat /sys/fs/cgroup/cpu/test/cpu.stat > before_cpu-b${BURST}-${RUN}.stat

# Actual test
./schbench/schbench -m 1 -t 30 -r 10 -c 10000 -R 300 2>&1 3>&1 | tee schbench_results-b${BURST}-${RUN}.txt

echo "Snapshot cpu.stat after test ..."
cat /sys/fs/cgroup/cpu/test/cpu.stat > after_cpu-b${BURST}-${RUN}.stat


echo "All done! Diff: "
diff before_cpu-b${BURST}-${RUN}.stat after_cpu-b${BURST}-${RUN}.stat
