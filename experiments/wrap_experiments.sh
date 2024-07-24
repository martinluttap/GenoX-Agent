#!/bin/bash

TARGET="/home/cc/research-code/2024/07-week3/experiments/"
WORKDIR="/home/cc/elastic-container/containermod/experiments/"

# Backup
rsync -azP ${WORKDIR}/nf_scripts $TARGET
rsync -azP ${WORKDIR}/configs $TARGET
rsync -azP ${WORKDIR}/*.sh $TARGET
rsync -azP ${WORKDIR}/*.py $TARGET
rsync -azP ${WORKDIR}/$0 $TARGET

# Remove artefact files
sudo rm -rf ${WORKDDIR}/work
