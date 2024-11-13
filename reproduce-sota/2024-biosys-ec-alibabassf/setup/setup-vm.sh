#!/bin/bash

# Various packages
sudo yum install -y dnf tmux

# Docker
sudo yum remove -y docker \
                  docker-client \
                  docker-client-latest \
                  docker-common \
                  docker-latest \
                  docker-latest-logrotate \
                  docker-logrotate \
                  docker-engine

sudo yum install -y yum-utils
sudo yum-config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo

sudo yum install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

sudo systemctl start docker

sudo groupadd docker
sudo usermod -aG docker $USER
newgrp docker

docker run hello-world

# Pyenv
sudo yum -y install epel-release
sudo yum -y install git gcc xz-devel libffi-devel zlib-devel bzip2-devel readline-devel sqlite-devel openssl-devel
curl https://pyenv.run | bash
cat <<EOF >> ~/.bashrc
export PYENV_ROOT="$HOME/.pyenv"
[[ -d $PYENV_ROOT/bin ]] && export PATH="$PYENV_ROOT/bin:$PATH"
eval \"$(pyenv init -)\"
eval \"$(pyenv virtualenv-init -)\"
EOF
source ~/.bashrc


# Golang 
wget https://go.dev/dl/go1.23.0.linux-amd64.tar.gz

sudo rm -rf /usr/local/go && sudo tar -C /usr/local -xzf go1.23.0.linux-amd64.tar.gz

export PATH=$PATH:/usr/local/go/bin
echo "export PATH=$PATH:/usr/local/go/bin" >> ~/.bashrc

# Resmon
sudo yum install gcc python3-devel
pyenv install 3.9
python3 -m pip install git+ssh://git@github.com/xybu/python-resmon.git

# Java
sudo yum install -y zip unzip
curl -s "https://get.sdkman.io" | bash
sdk install java 17.0.10-tem

# Nextflow
curl -s https://get.nextflow.io | bash
mkdir bin
mv nextflow bin
echo "export PATH=$PATH:$HOME/bin" >> ~/.bashrc
source  ~/.bashrc

# Rclone 
sudo -v ; curl https://rclone.org/install.sh | sudo bash

# Misc. setup (ssh for login, git, etc)
## Git 
sudo vi /etc/ssh/ssh_config # Comment line 61

# Exp. AlibabaSSF
gh repo clone martinluttap/2024-exp-alibabassf
## schbench
git clone https://git.kernel.org/pub/scm/linux/kernel/git/mason/schbench.git
pushd schbench
git checkout 5d65fcd09f7026b2af2cacf3204b26a0b0006b9e
sed -E "s|^CFLAGS(.*)|CFLAGS\1 -lm|" -i Makefile
make
popd

# Files
## Run on tmux!
rclone copy --progress remote:/genomics-files/reference-files/ reference-files/ 
rclone copy --progress remote:/genomics-files/read-files/SRR24039108_1.fastq.split/ read-files/SRR24039108/SRR24039108_1.fastq.split/
rclone copy --progress remote:/genomics-files/read-files/SRR24039108/ .
mv SRR24039108_150MB_*.fastq read-files/SRR24039108

# Minor changes on utils.py
# Need to make sure 'sudo python3' runs the correct python version
# sudo /home/cc/.pyenv/shims/python3 agent.py

# Setup all policies
mkdir -p elastic-container
cd elastic-container
git clone git@github.com:martinluttap/containermod.git
mv containermod autothrottle-py
cd authrottle-py
git checkout autothrottle-py
