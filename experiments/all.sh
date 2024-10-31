#!/bin/bash

POLICIES="autothrottle"
APPS="trimmomatic"
for POLICY in $POLICIES; do
  for APP in $APPS; do
    python3 driver/corr-by_policies.py --app ${APP} --policy ${POLICY}
  done
done
