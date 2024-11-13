# assume docker version >= 1.13
import sys
import os
import time
import json
import argparse
import logging
from pathlib import Path
import copy

from pathlib import Path
sys.path.append(str(Path.cwd() / 'src'))
from docker_swarm_util import (
	setup_swarm, update_node_label, docker_stack_rm, docker_stack_deploy, docker_check_replica, docker_service_scale
)

# -----------------------------------------------------------------------
# miscs
# -----------------------------------------------------------------------
logging.basicConfig(level=logging.DEBUG,filename=f'{__file__}.log',
                    format='%(asctime)s %(levelname)s: %(message)s', datefmt='%Y-%m-%d %H:%M:%S')

# -----------------------------------------------------------------------
# parser args definition
# -----------------------------------------------------------------------
parser = argparse.ArgumentParser()
# parser.add_argument('--cpus', dest='cpus', type=int, required=True)
# parser.add_argument('--stack-name', dest='stack_name', type=str, required=True)
parser.add_argument('--user-name', dest='user_name', type=str, default='cc')
parser.add_argument('--deploy-config', dest='deploy_config', type=str, required=True)

# -----------------------------------------------------------------------
# parse args
# -----------------------------------------------------------------------
args = parser.parse_args()
# todo: currently assumes all vm instances have the same #cpus
# MaxCpus = args.cpus
print(f'Executing with args: {args}')

Username = args.user_name
DeployConfig = Path.cwd() / 'config' / args.deploy_config.strip()

# -----------------------------------------------------------------------
# server configuration
# -----------------------------------------------------------------------
Servers = {}
HostServer = ''
with open('/proc/sys/kernel/hostname', 'r') as f:
	HostServer = f.read().replace('\n', '')

print(f'HostServer now: {HostServer}')

with open(str(DeployConfig), 'r') as f:
	config_info = json.load(f)
	Servers = config_info['nodes']

print(f'DeployConfig now: {DeployConfig}')



# establish docker swarm
worker_nodes = list(Servers.keys())
print(f'Worker nodes: {worker_nodes}')
worker_nodes.remove(HostServer)

assert HostServer not in worker_nodes
setup_swarm(username=Username, worker_nodes=worker_nodes)
# label nodes
for server in Servers:
	if 'label' in Servers[server]:
		update_node_label(server, Servers[server]['label'])