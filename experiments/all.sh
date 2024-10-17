#!/bin/bash

POLICIES="base burst elasticcontainer autothrottle"
APPS="fastqc" # samtools_sort samtools_index star trimmomatic gatk_baserecal"
for POLICY in $POLICIES; do
  for APP in $APPS; do
    python3 driver/corr-by_policies.py --app ${APP} --policy ${POLICY}
  done
done
