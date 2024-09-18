#!/bin/bash

# set -e 

TOPDIR="/home/cc/elastic-container/containermod/"


getMode() {
    FLAGS=$1 
    case "${FLAGS}" in 
        "-enable-burst")
            echo "burst" ;;
        "-elastic")
            echo "ectr" ;;
        *)
            echo "noburst" ;;
    esac
}

# We give runtime flags for our go command line parser here.
# Currently supported;
# * -enable-burst # (need Alibaba's Cloud Linux 2)
FLAGS=$1

# This script run both the workload and agent. 
# "Mode" refers to the policy we use to control cfs.quota
# We currently support the following mode: 
# 1. Base / No controller
# 2. ECTR
# 3. Ali-BurstKernel (need Alibaba's Cloud Linux 2)
# 4. Ali-BurstKernel + TCP (need Alibaba's Cloud Linux 2)
MODE=$(getMode $FLAGS)

# Applications refer to the set of experiments in TOPDIR/experiments.
# We currently support:
# - bwa
# - fastqc
# - gatk_baserecal
# - samtools_index
# - samtools_sort
# - star
# - trimmomatic
APPS="bwa"
NUM_RUNS=$((6))

for i in $(seq 4 $NUM_RUNS); do
    for APP in $APPS; do 
        START_TIME=$(date +%H-%M-%S)
        LABEL=$MODE-$APP-$i
        echo "============================="
        echo "Starting $LABEL at $START_TIME ..."
        echo "============================="
        mv -f *.csv ${TOPDIR}/results/
        
        sudo $(which go) run ${TOPDIR}/main.go $FLAGS | sudo tee ${LABEL}-controller.log &
        CTR_PID=$!

        ${TOPDIR}/experiments/run_${APP}.sh | sudo tee ${LABEL}-nf.log

        END_TIME=$(date +%H%M%S)
        echo "$LABEL done at $END_TIME!"
        sudo kill -9 ${CTR_PID}
        mkdir -p results/$LABEL-${END_TIME}

        sudo chown cc:cc *.log
        mv *.log results/$LABEL-${END_TIME}
        mv *cpu.csv results/$LABEL-${END_TIME}

        rm -rf ${TOPDIR}/work/
    done
done

