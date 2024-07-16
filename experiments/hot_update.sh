#!/bin/bash
set -e

./run_bwa.sh &

NEW_NUM_CORES=1.5
DELAY=60

sleep $DELAY; 
LAST_CONTAINER=$(docker ps -a -n 1 | grep bwa | tr -s ' ' | cut -d ' ' -f 1)
docker update --cpus=${NEW_NUM_CORES} ${LAST_CONTAINER}

echo "Updated ${LAST_CONTAINER} to ${NEW_NUM_CORES}!"