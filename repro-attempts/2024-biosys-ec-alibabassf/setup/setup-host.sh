#!/bin/bash

# Install rclone
sudo -v ; curl https://rclone.org/install.sh | sudo bash

# Burst Kernel VM
rclone copy --progress remote:/elastic-container/alibaba_linux2.qcow2 ./
# Disk images
rclone copy --progress remote:/genomics-files/ec-disk-images/ec_genomics_readfiles.img
rclone copy --progress remote:/genomics-files/ec-disk-images/genomics_references.img

# User-data
rclone copy --progress remote:/elastic-container/cpu_hotplug/user-data ./
rclone copy --progress remote:/elastic-container/cpu_hotplug/user-data.img ./

# Utilities
## Pigz
sudo apt-get install -y pigz

## Seqkit 
wget https://github.com/shenwei356/seqkit/releases/download/v2.8.2/seqkit_linux_amd64.tar.gz
gunzip seqkit_linux_amd64.tar.gz && tar -xf seqkit_linux_amd64.tar

# Accounts are: 
# admin:admin
# cc:????

# Permission for passwordless SSH
# sudo chmod 600 ~/.ssh/authorized_keys
