#!/bin/bash


WORKFLOW="/home/cc/elastic-container/containermod/experiments/nf_scripts/bwa.nf"
INPUT_CONFIG="/home/cc/elastic-container/containermod/experiments/configs/bwa.config"
LABEL="test"
OUT_LOG="${LABEL}.log"

# Kill existing resmon processes
ps aux | grep resmon | tr -s ' ' | cut -d ' ' -f 2 | xargs -I {} kill -9 {}

# Clear PageCache, dentries, indoes, and swap
sudo sync; echo 3 | sudo tee /proc/sys/vm/drop_caches ; sudo swapoff -a && sudo swapon -a

# Backup NF script
cp $WORKFLOW ${LABEL}.nf
cp $INPUT_CONFIG ${LABEL}.config

resmon -o ${OUT_LOG%.log}.csv &
export RESMON_PID=$!
nextflow run ${LABEL}.nf \
    -c $INPUT_CONFIG \
    -with-timeline ${OUT_LOG%.log}-timeline.html \
    -with-trace ${OUT_LOG%.log}-trace.txt \
    -with-report ${OUT_LOG%.log}-report.html \

sleep 5
kill ${RESMON_PID}
