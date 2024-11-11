#!/bin/bash

set -e 

# Assume a range of {1..8} cores allocation
# For cpu.cfs_quota_us, this corresponds to {100000..800000} at 100000 interval.
# We collect 35 data points by traversing with a step of 10000.
APP="bwa"
PATH_RUNSCRIPT=$(pwd)/run_${APP}.sh
PATH_CONTROLLER=$(pwd)/../controller/controller.go

mkdir -p correlation/

for STEP in $(seq 80 40 80); do 
    echo $STEP
    # Modify two things: 
    # 1. LABEL in run_<app>.sh
    # 2. allocatedCores := int64(...) in controller/controller/go

    echo "STEP $STEP"
    sed -E "s|LABEL=.*|LABEL=\"base-$APP\_corrstep$STEP\"|" -i $PATH_RUNSCRIPT
    sed -E "s|allocatedCores :=.*|allocatedCores := int64($STEP)|" -i $PATH_CONTROLLER

    echo
    grep -E "LABEL=" -A2 -B2 $PATH_RUNSCRIPT

    echo
    grep -E "allocatedCores :=" -A2 -B2 $PATH_CONTROLLER

    pushd ../
    # ./agent.sh &
    sudo $(which go) run main.go &
    export AGENT_PID=$!
    popd
    
    $(pwd)/run_$APP.sh
    sleep 3
    sudo kill ${AGENT_PID}
    
    mkdir -p correlation/${STEP}/
    mv *corrstep$STEP* correlaton/${STEP}/
    mv ../*.csv correlation/${STEP}
done