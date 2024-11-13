#!/bin/bash

# Ensure connectivity between all nodes.
# We do this by ensuring each machine has each other's public key in their authorized keys

ssh-keygen -q -t rsa -N '' -f ~/.ssh/id_rsa <<<y >/dev/null 2>&1
cat ~/.ssh/id_rsa.pub

# Install prerequisites
./install-docker.sh
./install-gh.sh
## Install pyenv
curl https://pyenv.run | bash
## Assume pyenv's post-installation steps are done 
pyenv install 3.10.10
pyenv virtualenv 3.10.10 sinan 
pyenv local sinan
pyenv global sinan

## Install mxnet -- must make sure numpy version is compatible
pip3 install mxnet-mkl==1.6.0 numpy==1.23.1 xgboost==1.6.0

# Generate docker swarm config file
python3 make_cluster_config.py --nodes sinan-1 sinan-2 --cluster-config test_cluster.json --replica-cpus 2

