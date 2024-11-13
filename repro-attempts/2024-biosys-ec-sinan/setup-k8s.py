import logging
import os
from dotenv import load_dotenv
from fabric import Connection, SerialGroup as SGroup, ThreadingGroup as TGroup
from invoke import Responder
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

def setup_access_all_nodes(root_pool: TGroup):
    commands_setup_access = [
        "ufw disable",
        # "systemctl stop firewalld.service",
        "echo \"net.bridge.bridge-nf-call-iptables=1\" | tee -a /etc/sysctl.conf",
        "modprobe br_netfilter",
        "echo '1' > /proc/sys/net/ipv4/ip_forward"
    ]
    for cmd in commands_setup_access:
        res = root_pool.run(cmd, pty=True, watchers=[yes_responder])
        for host, r in res.items():
            print(f'{host}: {r.stdout}')

def disable_swap(root_pool: TGroup):
    commands_disable_swap = [
        "swapoff -a",
        "sed -E \"s|(.*)swap(.*)|#\1swap\2|\" -i /etc/fstab"
    ]
    for cmd in commands_disable_swap:
        res = root_pool.run(cmd, pty=True)
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

def remove_pubkeys(pool: TGroup):
    pool.run('rm -f ~/.ssh/id_rsa.pub', pty=True, watchers=[yes_responder])
    pool.run('sudo rm -f /root/.ssh/id_rsa.pub', pty=True, watchers=[yes_responder])

def reset_authkeys(pool: TGroup):
    pool.run("sudo sed -i '8,$d' ~/.ssh/authorized_keys", watchers=[yes_responder])
    pool.run("sudo sed -i '8,$d' /root/.ssh/authorized_keys", watchers=[yes_responder])
    # When we use ChameleonCloud, the first line has "command" in it. 
    # It prevents us from ssh-ing as root.
    pool.run("sudo sed -E \"command\" -i /root/.ssh/authorized_keys", watchers=[yes_responder])

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

def setup_python_all_nodes(root_pool: TGroup):
    commands_setup_deps = [
        # Python libraries
        "apt-get update",
        "apt-get install -y python3-pip",
        "pip3 install grpcio",
        "pip3 install protobuf",
        "pip3 install numpy",
        "pip3 install pandas",
        "pip3 install requests",
        # In case we need remote development
        "pip3 install fabric",
        "pip3 install python-dotenv",
    ]
    for cmd in commands_setup_deps:
        res = root_pool.run(cmd, pty=True, watchers=[yes_responder])
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

def run_server_all_nodes(root_pool: TGroup):
    commands_run_nodens = [
        "ps aux | grep \"server.py\" | tr -s ' ' | cut -d ' ' -f 2 | xargs -I {} kill -9 {}", # kill running instance
        "tmux kill-session -t nodens",
        "tmux new-session -d -s nodens 'python3 2024-ec-nodens/Nodens/workerServer/server.py'"
    ]
    for cmd in commands_run_nodens:
        res = root_pool.run(cmd, warn=True)
        for host, r in res.items():
            print(f'{host}: {r.stdout}')

def setup_codebase(root_pool: TGroup):
    assert(os.getenv('GIT_TOKEN'))
    assert(os.getenv('GIT_USERNAME'))

    # Auth Github
    with open('git-token', 'w') as f:
        f.write(os.getenv('GIT_TOKEN'))
    root_pool.put('git-token', 'git-token')
    root_pool.run('gh auth login --with-token < git-token ; gh repo clone martinluttap/2024-ec-nodens')

def drain_and_remove_workers(cp_pool: TGroup):
    # Get worker nodes
    worker_nodes = cp_pool[0].run('kubectl get node --selector="!node-role.kubernetes.io/control-plane" | tr -s " " | cut -d " " -f 1 | tail -n +2', pty=True).stdout.strip().split('\n')
    worker_nodes = list(map(lambda x: x.strip(), worker_nodes))
    
    for node in worker_nodes:
        cp_pool.run(f'kubectl drain {node} --ignore-daemonsets --delete-local-data', pty=True)
        cp_pool.run(f'kubectl delete node {node}', pty=True)

def kubeadm_reset_all_nodes(root_pool: TGroup):
    root_pool.run('kubeadm reset', pty=True, watchers=[yes_responder])
    root_pool.run('rm -rf .kube', pty=True)
    root_pool.run('rm -rf /etc/kubernetes', pty=True)

def run_load_generator(cp_connection: TGroup):
    pass

def sync_paths(root_pool: TGroup, paths: List[str]): 
    # How do we get user information from TGroup? 
    # Only works for root_pool for now
    master_host = root_pool[0].host
    master_user = root_pool[0].user
    workers_pool = TGroup.from_connections(root_pool[1:]) 
    for p in paths:
        workers_pool.run(
            f'rsync --exclude="*.git*" -azP root@{master_host}:{p} {p}',
            pty=True, watchers=[yes_responder, y_responder]
        )

def disable_firewall(root_pool: TGroup):
    commands = [
        'ufw disable'
    ]
    for cmd in commands:
        root_pool.run(cmd, pty=True)

if __name__ == "__main__":
    root_pool = TGroup(
        'root@129.114.108.255', # sinan-compute1
        'root@129.114.108.77', # sinan-compute2
        'root@129.114.109.73', # sinan-compute3
        # 'cc@129.114.109.101', # sinan-gpu1

    )
    nonroot_pool = TGroup(
        'cc@129.114.108.255', # sinan-compute1
        'cc@129.114.108.77', # sinan-compute2
        'cc@129.114.109.73', # sinan-compute3
        # 'cc@129.114.109.101', # sinan-gpu1

    )
    CONTROL_PLANE = '129.114.108.255'
    CP_CONNECTION = TGroup(f'root@{CONTROL_PLANE}')

    # We gather keys for both nonroot and root users.
    # For each type of user, we add all keys (nonroot + root)
    remove_pubkeys(nonroot_pool)
    reset_authkeys(nonroot_pool)
    nonroot_pub_keys_d, root_pub_keys_d = gather_keys(nonroot_pool)
    add_authorized_keys(nonroot_pool, nonroot_pub_keys_d, root_pub_keys_d)
    
    print("Keys added!")
    
    # # Get Nodens codebase 
    # setup_codebase(root_pool)

    # # Tear down first, then deploy benchmark. 
    # # Might require pulling docker images
    # manifest_path = f'2024-ec-nodens/hotel-reservation/'
    # CP_CONNECTION.run(f"cat git-token | docker login ghcr.io -u {os.getenv('GIT_USERNAME')} --password-stdin ; kubectl delete -f {manifest_path} ; kubectl apply -f {manifest_path}", pty=True)

    # # Run nodens on all nodes
    # run_server_all_nodes(root_pool)
    # target_sync_paths = [
    #     '/root/2024-ec-nodens/',
    # ]
    # sync_paths(root_pool, target_sync_paths)

    # Run load generator
    # run_load_generator(CP_CONNECTION)

    # Teardown cluster
    # drain_and_remove_workers(CP_CONNECTION)
    # kubeadm_reset_all_nodes(root_pool)