#!/bin/bash

set -o errexit

INTERVAL=1
OUTNAME=docker_stats.raw

update_file() {
  docker stats --no-stream --format "table {{.Container}},{{.Name}},{{.CPUPerc}},{{.MemUsage}},{{.NetIO}},{{.BlockIO}},{{.PIDs}}" | tee --append $OUTNAME;
  TIMESTAMP=$(date +'%s.%N')
  echo "timestamp=${TIMESTAMP}" | tee --append $OUTNAME;
}

run_containermod() {
  go build . && sudo ./main | tee --append go.out 
}

run_nextflow() {
  /home/cc/nextflow/harvestsim/run_bwa.sh | tee --append nextflow.out
}

# run_nextflow &
# sleep 2
run_containermod &

while true;
do
  update_file &
  sleep $INTERVAL;
done
