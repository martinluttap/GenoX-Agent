import glob
import logging
import numpy
import os
import subprocess as sp

from dotenv import load_dotenv
from fabric import (
    Connection, SerialGroup as SGroup, 
    ThreadingGroup as TGroup,
)
from invoke import Responder
from pathlib import Path
from typing import Any, Callable, Dict, List, Set, Tuple

load_dotenv()

logger = logging.basicConfig(
    level=logging.WARNING,
    format='%(asctime)s %(name)s %(levelname)s %(module)s - %(funcName)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
)

y_responder = Responder(
    pattern=r'.*\?.*',
    response='y\n',
)

yes_responder = Responder(
    pattern=r'.*\?.*',
    response='yes\n',
)

def show_hostname(pool: TGroup):
    commands = [
        'whoami ; hostname ; curl ifconfig.me'
    ]
    for c in commands:
        pool.run(c, pty=True)

def add_ssh_config(pool: TGroup):
    pool.run('rm -f ~/.ssh/config', pty=True, warn=True)
    pool.run('rm -f /root/.ssh/config', pty=True, warn=True)

    res = pool.run('hostname')
    ip_host_d = {}
    for c, r in res.items():
        print(f'{c.host}: {r.stdout}')
        ip_host_d[c.host] = r.stdout.strip()

    res = pool.run('whoami')
    ip_user_d = {}
    for c, r in res.items():
        print(f'{c.host}: {r.stdout}')
        ip_user_d[c.host] = r.stdout.strip()

    # Construct ~/.ssh/.config file
    content = ""
    for ip, _ in ip_host_d.items():
        user = ip_user_d[ip]
        host = ip_host_d[ip]
        print(ip, user, host)
        entry = f'Host {host}\n\tHostName {ip}\n\tUser {user}\n'
        content += entry
    
    pool.run(f"echo \"{content}\" > ~/.ssh/config")
    pool.run(f"echo \"{content}\" | sudo tee /root/.ssh/config")

def setup_internode_access(nonroot_pool: TGroup):
    # We gather keys for both nonroot and root users.
    # For each type of user, we add all keys (nonroot + root)
    remove_pubkeys(nonroot_pool)
    reset_authkeys(nonroot_pool)
    nonroot_pub_keys_d, root_pub_keys_d = gather_keys(nonroot_pool)
    add_authorized_keys(nonroot_pool, nonroot_pub_keys_d, root_pub_keys_d)
    add_ssh_config(nonroot_pool)

    # We need to ensure firewewall is off. 
    commands = [
        'sudo ufw disable'
    ]
    for cmd in commands:
        nonroot_pool.run(cmd, pty=True)

def remove_pubkeys(pool: TGroup):
    pool.run('rm -f ~/.ssh/id_rsa.pub', pty=True, watchers=[yes_responder])
    pool.run('sudo rm -f /root/.ssh/id_rsa.pub', pty=True, watchers=[yes_responder])

def reset_authkeys(pool: TGroup):
    pool.run("sudo sed -i '8,$d' ~/.ssh/authorized_keys", watchers=[yes_responder])
    pool.run("sudo sed -i '8,$d' /root/.ssh/authorized_keys", watchers=[yes_responder])

def gather_keys(pool: TGroup) -> Tuple[Dict[str, str], Dict[str, str]]:
    nonroot_pub_keys_d: Dict[str, str] = {}
    root_pub_keys_d: Dict[str, str] = {}

    # Non-root
    try:
        pool.run(f'test -f ~/.ssh/id_rsa.pub', watchers=[yes_responder])
    except Exception as e:
        for c in pool:
            res = c.run('ssh-keygen -q -t rsa -N "" -f ~/.ssh/id_rsa <<<y >/dev/null 2>&1')
    print('Generated non-root keys.')
    # Root
    try:
        pool.run(f'sudo test -f /root/.ssh/id_rsa.pub', watchers=[yes_responder])
    except Exception as e:
        for c in pool:
            res = c.run('sudo ssh-keygen -q -t rsa -N "" -f /root/.ssh/id_rsa <<<y >/dev/null 2>&1')
    print('Generated root keys.')

    # Non-root
    res = pool.run('cat ~/.ssh/id_rsa.pub', hide=True, watchers=[yes_responder])
    for h, r in res.items():
        nonroot_pub_keys_d[h.host] = r.stdout.strip()
    print('Collected non-root keys.')

    # Root
    res = pool.run('sudo cat /root/.ssh/id_rsa.pub', hide=True, watchers=[yes_responder])
    for h, r in res.items():
        root_pub_keys_d[h.host] = r.stdout.strip()
    print('Collected root keys.')

    print(nonroot_pub_keys_d)
    print('---------------------')
    print(root_pub_keys_d)
    print('---------------------')

    return nonroot_pub_keys_d, root_pub_keys_d

def add_authorized_keys(pool: TGroup, 
                        nonroot_pub_keys_d: Dict[str, str],
                        root_pub_keys_d: Dict[str, str]
                        ):
    new_keys = ''
    for host, key in nonroot_pub_keys_d.items():
        new_keys += f'{key}\n'
    for host, key in root_pub_keys_d.items():
        new_keys += f'{key}\n'

    # Remove duplicate lines in nonroot keys first
    pool.run(f'awk -i inplace \'!seen[$0]++\' ~/.ssh/authorized_keys', hide=True, watchers=[yes_responder])

    # Collect everything, then put in both nonroot and root authkeys
    pool.run(f'echo "{new_keys}" | tee -a ~/.ssh/authorized_keys', hide=True, watchers=[yes_responder])
    pool.run(
        f'EXISTING_KEYS=$(cat ~/.ssh/authorized_keys); echo "\n$EXISTING_KEYS" | sudo tee -a /root/.ssh/authorized_keys; echo "{new_keys}" | sudo tee -a /root/.ssh/authorized_keys',
        hide=True, watchers=[yes_responder])

    # Just in case root keys still have duplicates
    pool.run(f'sudo awk -i inplace \'!seen[$0]++\' /root/.ssh/authorized_keys', hide=True, watchers=[yes_responder])

def install_gh(nonroot_pool: TGroup):
    commands_inst_gh = [
        "(type -p wget >/dev/null || (sudo apt update && sudo apt-get install wget -y))",
        "sudo mkdir -p -m 755 /etc/apt/keyrings",
        "wget -qO- https://cli.github.com/packages/githubcli-archive-keyring.gpg | sudo tee /etc/apt/keyrings/githubcli-archive-keyring.gpg > /dev/null",
        "sudo chmod go+r /etc/apt/keyrings/githubcli-archive-keyring.gpg",
        "echo \"deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main\" | sudo tee /etc/apt/sources.list.d/github-cli.list > /dev/null",
        "sudo apt update",
        "sudo apt install gh -y"
    ]
    for cmd in commands_inst_gh:
        res = nonroot_pool.run(cmd, pty=True, watchers=[yes_responder])
        for host, r in res.items():
            print(f'{host}: {r.stdout}')

def setup_codebase(pool: TGroup):
    assert(os.getenv('GIT_TOKEN'))
    assert(os.getenv('GIT_USERNAME'))

    pool.run('rm -rf 2024-ec-sinan', pty=True, warn=True)

    # Auth Github
    with open('git-token', 'w') as f:
        f.write(os.getenv('GIT_TOKEN'))
    pool.put('git-token', 'git-token')
    pool.run('gh auth login --with-token < git-token ; gh repo clone martinluttap/2024-ec-sinan')

def setup_python_all_nodes(pool: TGroup):

    commands_setup_deps = [
            # Python libraries
            "pip3 install fabric",
            "pip3 install python-dotenv",
            "pip3 install docker",
            "pip3 install numpy"
        ]
    for cmd in commands_setup_deps:
        res = pool.run(cmd, watchers=[yes_responder])
        for host, r in res.items():
            print(f'{host}: {r.stdout}')

def generate_cluster_config(nonroot_pool: TGroup):
    # manager_config
    commands = [
        'python3 make_cluster_config.py --nodes ath-8 ath-9 --cluster-config test_cluster.json --replica-cpus 4'
    ]

def reset_sinan(pool: TGroup):
    commands = [
        # "cat /home/cc/2024-ec-sinan/docker_swarm/slave_data_collect_social.txt",
        # "ps aux | grep -E \"python3.*sinan.*\"",
        "ps aux | grep -E \"python3.*sinan.*\"  | tr -s ' ' | cut -d ' ' -f 2 | xargs -I {} kill -9 {}"
    ]
    for cmd in commands:
        res = pool.run(cmd, pty=True, warn=True)
        for host, r in res.items():
            print(f'{host}: {r.stdout}')

def setup_dirs(root_pool: TGroup, nonroot_pool: TGroup):
    root_pool.run('rm -rf ~/sinan_locust_log/', pty=True)
    # Docker for locust requires nonroot access, but we put the output dir in /root/. 
    # We need to change its permissions. 
    nonroot_user = nonroot_pool[0].user
    assert nonroot_user != 'root'
    commands = [
        f"mkdir -p ~/sinan_locust_log/",
        f"chown -R {nonroot_user}:{nonroot_user} ~/sinan_locust_log/",
    ]
    for cmd in commands:
        res = root_pool.run(cmd, pty=True, warn=True)
        for host, r in res.items():
            print(f'{host}: {r.stdout}')

def teardown_swarm(pool: TGroup):
    manager_cp = pool[0]
    manager_cp.run('docker service rm $(docker service ls -q)', warn=True)
    manager_cp.run('docker system prune -a -f', warn=True)

    commands = [
        'docker swarm leave --force'
    ]
    for cmd in commands:
        pool.run(cmd, pty=True)

def run_data_collect_social(pool: TGroup):
    random_port = numpy.random.randint(1024, 65336)
    dirpath = f'2024-ec-sinan/Sinan/docker_swarm/'
    cp_conn = pool[0]
    worker_conns = TGroup.from_connections(pool[1:])

    # Run worker client
    worker_conns.run(
        f'cd {dirpath} ; python3 {dirpath}/slave_data_collect_social.py --stack-name sinan-socialnet --cpus 96 --server-port 40111 --service-config /root/2024-ec-sinan/Sinan/docker_swarm/config/slave_config.json 2>&1 | tee $(date \'+%d-%m-%Y_%H-%M-%S\')-slave_social.txt'   
    )

    # Then run master
    commands = [
         f'cd {dirpath} ; ls ; python3 master_data_collect_ath_social.py --user-name $(whoami) \
            --stack-name sinan-socialnet \
            --min-users 4 --max-users 24 --users-step 2 \
            --exp-time 60 --measure-interval 1 --slave-port 40111 --deploy-config test_cluster.json \
        	--mab-config social_mab.json --deploy'
     ]
    for cmd in commands:
        res = cp_conn.run(cmd, pty=True)
        for host, r in res.items():
            print(f'{host}: {r.stdout}')
     
def login_docker(pool: TGroup):
    # Auth Github
    with open('git-token', 'w') as f:
        f.write(os.getenv('GIT_TOKEN'))
    with open('git-username', 'w') as f:
        f.write(os.getenv('GIT_USERNAME'))
    pool.put('git-token', 'git-token')
    pool.put('git-username', 'git-username')
    commands = [
        "GIT_USERNAME=$(cat git-username) ; cat git-token | docker login ghcr.io -u $GIT_USERNAME --password-stdin"
    ]
    for cmd in commands:
        pool.run(cmd, pty=True)

def install_containerd(root_pool: TGroup):
    commands_inst_containerd = [
        "wget https://github.com/containerd/containerd/releases/download/v1.6.14/containerd-1.6.14-linux-amd64.tar.gz",
        "tar Cxzvf /usr/local containerd-1.6.14-linux-amd64.tar.gz",
        "wget https://github.com/opencontainers/runc/releases/download/v1.1.3/runc.amd64",
        "install -m 755 runc.amd64 /usr/local/sbin/runc",
        "mkdir -p /etc/containerd",
        "containerd config default | tee /etc/containerd/config.toml",
        "sed -i 's/SystemdCgroup \= false/SystemdCgroup \= true/g' /etc/containerd/config.toml",
        "curl -L https://raw.githubusercontent.com/containerd/containerd/main/containerd.service -o /etc/systemd/system/containerd.service",
        "systemctl daemon-reload",
        "systemctl enable --now containerd",
        "systemctl restart containerd"
    ]
    for cmd in commands_inst_containerd:
        res = root_pool.run(cmd, pty=True, watchers=[yes_responder])
        for host, r in res.items():
            print(f'{host}: {r.stdout}')

def test_containerd(root_pool: TGroup):
    commands_test_containerd = [
        "systemctl --no-pager status containerd"
    ]
    for cmd in commands_test_containerd:
        res = root_pool.run(cmd, pty=True, watchers=[yes_responder])
        for host, r in res.items():
            print(f'{host}: {r.stdout}')

def install_k8s(root_pool: TGroup):
    # Install k8s
    commands_inst_k8s = [
        "apt-get update",
        "apt-get install -y apt-transport-https ca-certificates curl gpg",
        "mkdir -p /etc/apt/keyrings/",
        "curl -fsSL https://pkgs.k8s.io/core:/stable:/v1.28/deb/Release.key | gpg --yes --dearmor -o /etc/apt/keyrings/kubernetes-apt-keyring.gpg",
        "echo 'deb [signed-by=/etc/apt/keyrings/kubernetes-apt-keyring.gpg] https://pkgs.k8s.io/core:/stable:/v1.28/deb/ /' | tee /etc/apt/sources.list.d/kubernetes.list",
        "apt-get update",
        "apt-get install -y socat",
        "apt-get install -y kubelet kubeadm kubectl"
    ]
    for command in commands_inst_k8s:
        res = root_pool.run(command, pty=True, watchers=[yes_responder])
        print(res)

def install_docker(nonroot_pool: TGroup):
    commands_inst_docker = [
        "sudo apt-get update && sudo apt-get install -y ca-certificates curl",
        "sudo install -m 0755 -d /etc/apt/keyrings",
        "sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc",
        "sudo chmod a+r /etc/apt/keyrings/docker.asc",
        "echo \
        \"deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu \
        $(. /etc/os-release && echo $VERSION_CODENAME) stable\" | \
        sudo tee /etc/apt/sources.list.d/docker.list > /dev/null",
        "sudo apt-get update && sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin",
        "sudo groupadd docker",
        "sudo usermod -aG docker $USER",
    ]
    failed_runs = []
    for cmd in commands_inst_docker:
        res = nonroot_pool.run(cmd, watchers=[yes_responder], warn=True)
        if res.failed:
            failed_runs.append(res)
        print(res)

    return failed_runs

def test_docker(nonroot_pool: TGroup):
    commands_test_docker = [
        "docker --version",
        "docker run hello-world"
    ]
    for cmd in commands_test_docker:
        res = nonroot_pool.run(cmd, pty=True, watchers=[yes_responder])
        for c, r in res.items():
            print(f'{c.host}: {r.stdout}')

def disable_swap(root_pool: TGroup):
    commands_disable_swap = [
        "swapoff -a",
        "sed -E \"s|(.*)swap(.*)|#\1swap\2|\" -i /etc/fstab"
    ]
    for cmd in commands_disable_swap:
        res = root_pool.run(cmd, pty=True)
        for host, r in res.items():
            print(f'{host}: {r.stdout}')

def setup_js_all_nodes(root_pool: TGroup):
    commands_setup_js = [
        # Node.js
        'curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.7/install.sh | bash',
        'export NVM_DIR="$HOME/.nvm" ; [ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh" ; [ -s "$NVM_DIR/bash_completion" ] && \. "$NVM_DIR/bash_completion" ; nvm install 20.12.0',
    ]
    for cmd in commands_setup_js:
        res = root_pool.run(cmd)
        for host, r in res.items():
            print(f'{host}: {r.stdout}')

def setup_control_plane(root_pool: TGroup):
    # Init cluster
    root_pool.run("kubeadm reset; kubeadm init --pod-network-cidr=10.244.0.0/16", pty=True, watchers=[yes_responder])

    commands = [
        # Setup kubeconfig
        'mkdir -p .kube',
        'cp /etc/kubernetes/admin.conf .kube/config',
        # flannel networking
        'kubectl apply -f https://github.com/flannel-io/flannel/releases/latest/download/kube-flannel.yml',
        # save join command and credentials
        'kubeadm token create --print-join-command >join-command',
        'cp .kube/config kube-config'
    ]
    for cmd in commands:
        res = root_pool.run(cmd, pty=True)

    conveniences_cmds = [
        # Conveniences: zsh, ...
        'apt-get install -y zsh',
        'rm -rf ~/.oh-my-zsh',
        'sh -c "$(curl -fsSL https://raw.githubusercontent.com/ohmyzsh/ohmyzsh/master/tools/install.sh)"'
    ]
    for cmd in conveniences_cmds:
        res = root_pool.run(cmd)

def drain_and_remove_workers(cp_pool: TGroup):
    # Get worker nodes
    res = cp_pool[0].run('kubectl get node --selector="!node-role.kubernetes.io/control-plane" | tr -s " " | cut -d " " -f 1 | tail -n +2', pty=True).stdout.strip().split('\n')
    worker_nodes = list(map(lambda x: x.strip(), res))
    
    for node in worker_nodes:
        cp_pool.run(f'kubectl drain {node} --ignore-daemonsets --delete-local-data', pty=True, warn=True)
        cp_pool.run(f'kubectl delete node {node}', pty=True, warn=True)

def kubeadm_reset_all_nodes(root_pool: TGroup):
    root_pool.run('kubeadm reset', pty=True, watchers=[yes_responder])
    root_pool.run('rm -rf .kube', pty=True)
    root_pool.run('rm -rf /etc/kubernetes', pty=True)

def setup_k8s_cluster(root_pool: TGroup):
    CP_CONNECTION = TGroup.from_connections(root_pool[:1])

    # Kubernetes installation
    install_containerd(root_pool)
    test_containerd(root_pool)
    install_k8s(root_pool)
    install_docker(root_pool)
    test_docker(root_pool)

    disable_swap(root_pool)

    # Tear down cluster, if exists
    drain_and_remove_workers(CP_CONNECTION)
    kubeadm_reset_all_nodes(root_pool)

    # Get join command and credentials 
    setup_control_plane(CP_CONNECTION)
    CP_CONNECTION.get('kube-config', 'kube-config')
    CP_CONNECTION.get('join-command', 'join-command')

    # Copy join command and credentials to all other nodes,
    # then execute
    root_pool.put('kube-config', 'kube-config')
    root_pool.put('join-command', 'join-command')
    try:
        root_pool.run('chmod +x join-command; bash join-command', pty=True)
    except:
        pass
    try:
        root_pool.run('mkdir -p .kube ; cp kube-config .kube/config', pty=True)
    except:
        pass

    # Check cluster
    CP_CONNECTION.run('kubectl get nodes', pty=True)

def run_social_network(root_pool: TGroup,
                       manifest_path: str = ''
                        ):
    cp_conn = root_pool[0]
    commands = [
        'kubectl delete -f {manifest_path} ; kubectl apply -f {manifest_path}'
    ]
    for cmd in commands:
        cp_conn.run(cmd, pty=True)

def sync_dir(root_pool: TGroup, dir_path: str):
    # We do two hops to reduce traffic from local machine.
    ## First sync to manager / control plane
    cmds = f"rsync --exclude *.git/* --exclude *__pycache__/* -azP -e 'ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null' {dir_path}/ root@{root_pool[0].host}:/root/{dir_path.split('/')[-1]}/"
    sp.run(cmds, shell=True)

    ## Then ask workers to pull from manager / control plane
    workers = TGroup.from_connections(root_pool[1:])
    workers.run(f"rsync --exclude *.git/* --exclude *__pycache__/* -azP -e 'ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null' root@{root_pool[0].host}:/root/{dir_path.split('/')[-1]}/ /root/{dir_path.split('/')[-1]}/")

if __name__ == "__main__":
    nonroot_pool = TGroup(
        'cc@129.114.108.255', # sinan-compute1
        'cc@129.114.108.77', # sinan-compute2
        'cc@129.114.109.73', # sinan-compute3
        # 'cc@129.114.109.101', # sinan-gpu1
    )

    root_pool = TGroup(
        'root@129.114.108.255', # sinan-compute1
        'root@129.114.108.77', # sinan-compute2
        'root@129.114.109.73', # sinan-compute3
        # 'cc@129.114.109.101', # sinan-gpu1
    )

    # # Setup networking and access
    # setup_internode_access(nonroot_pool)

    # Development tools
    # install_gh(nonroot_pool)
    # setup_python_all_nodes(nonroot_pool)
    # setup_js_all_nodes(nonroot_pool)

    # Tear down cluster, if exists
    # CP_CONNECTION = TGroup.from_connections(root_pool[:1])
    # drain_and_remove_workers(CP_CONNECTION)
    # kubeadm_reset_all_nodes(root_pool)
    # setup_k8s_cluster(root_pool)

    # Get images and codebase
    # login_docker(root_pool)
    # setup_codebase(root_pool)

    # Check cluster
    CP_CONNECTION = TGroup.from_connections(root_pool[:1])
    # CP_CONNECTION.run('kubectl get pods --all-namespaces -o wide', pty=True)

    # Setup benchmark
    ## Social Network
    reset_sinan(root_pool)
    # CP_CONNECTION.run(
    #     'kubectl delete -f 2024-ec-sinan/social-network ; kubectl apply -f 2024-ec-sinan/social-network', 
    #     pty=True
    # )
    # CP_CONNECTION.run('kubectl get pods --all-namespaces -o wide', pty=True)


    dir_path = os.path.dirname(os.path.realpath(__file__))
    sync_dir(root_pool, dir_path)
    
    # run_data_collect_social(root_pool)

    # setup_dirs(root_pool, nonroot_pool)
    # reset_sinan(root_pool)
    # # teardown_swarm(nonroot_pool)
    # # run_data_collect_social(nonroot_pool)
    # print('All done!')