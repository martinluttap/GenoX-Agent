#!/bin/bash

EXP_DIR="/home/cc/elastic-container/containermod/experiments/"
WORKFLOW="${EXP_DIR}/nf_scripts/dnaseq.nf"
INPUT_CONFIG="${EXP_DIR}/configs/dnaseq.config"
LABEL="dnaseq_test"
OUT_LOG="${LABEL}.log"

# Kill existing resmon processes
ps aux | grep resmon | tr -s ' ' | cut -d ' ' -f 2 | xargs -I {} kill -9 {}

# Kill existing glances processes
# ps aux | grep glances | tr -s ' ' | cut -d ' ' -f 2 | xargs -I {} kill -9 {}

# Clear PageCache, dentries, indoes, and swap
sudo sync; echo 3 | sudo tee /proc/sys/vm/drop_caches ; sudo swapoff -a && sudo swapon -a

# Clear artefacts from previous runs
rm LoadDuration.txt

# Backup NF script
cp $WORKFLOW ${LABEL}.nf
cp $INPUT_CONFIG ${LABEL}.config

resmon -o ${EXP_DIR}/${OUT_LOG%.log}.csv &
export RESMON_PID=$!

nextflow run ${LABEL}.nf \
    -c $INPUT_CONFIG \
    -with-timeline ${OUT_LOG%.log}-timeline.html \
    -with-trace ${OUT_LOG%.log}-trace.txt \
    -with-report ${OUT_LOG%.log}-report.html \

sleep 5
kill ${RESMON_PID}
# kill ${GLANCES_PID}

rm -rf ${EXP_DIR}/results/${LABEL}
mkdir -p ${EXP_DIR}/results/${LABEL}
mv ${EXP_DIR}/${OUT_LOG%.log}.csv ${EXP_DIR}/results/${LABEL}/${OUT_LOG%.log}.csv

# awk -f ${EXP_DIR}/parse.awk ${EXP_DIR}/${OUT_LOG%.log}.csv \
#     > ${EXP_DIR}/results/${LABEL}/${OUT_LOG%.log}.csv

echo "All gatk_applybqsr done!"