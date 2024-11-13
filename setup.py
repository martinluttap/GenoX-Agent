import logging
import os
import subprocess as sp

from dotenv import load_dotenv
from fabric import (
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

def parameterized(dec):
    def layer(*args, **kwargs):
        def repl(f):
            return dec(f, *args, **kwargs)
        return repl
    return layer

@parameterized
def check_installed(f, binary: str):
    def checker(*xs, **kws):
        assert isinstance(xs[0] , TGroup)
        pool = xs[0]
        ret = pool[0].run(f'{binary}', hide=True, warn=True)
        if ret.exited == 127:
            return f(*xs, **kws)
        else:
            print(f'{binary} installed!')
    return checker

@check_installed('gh')
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
        res = nonroot_pool.run(cmd, watchers=[yes_responder])

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

@check_installed('docker')
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

def pull_docker_images(nonroot_pool: TGroup):
    login_docker(nonroot_pool)
    images = [
        'ghcr.io/martinluttap/bwa:0.7.15-554c2eb',
        'ghcr.io/martinluttap/fastqc:0.12.1',
        'ghcr.io/martinluttap/gatk:4.2.4.1-no-entrypoint',
        'ghcr.io/martinluttap/picard:2.26.10',
        'ghcr.io/martinluttap/samtools:1.9',
        'ghcr.io/martinluttap/star2:2.7.10b',
        'ghcr.io/martinluttap/trimmomatic:0.38',
    ]
    for image in images:
        nonroot_pool.run(f'docker pull {image}', pty=True)        

def sync_dir(root_pool: TGroup, dir_path: str):
    # We do two hops to reduce traffic from local machine.
    ## First sync to manager / control plane
    cmds = f"rsync --exclude *.git/* --exclude *__pycache__/* -azP -e 'ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null' {dir_path}/ root@{root_pool[0].host}:/root/{dir_path.split('/')[-1]}/"
    sp.run(cmds, shell=True)

    ## Then ask workers to pull from manager / control plane
    workers = TGroup.from_connections(root_pool[1:])
    workers.run(f"rsync --exclude *.git/* --exclude *__pycache__/* -azP -e 'ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null' root@{root_pool[0].host}:/root/{dir_path.split('/')[-1]}/ /root/{dir_path.split('/')[-1]}/")

@check_installed('java')
def install_java(nonroot_pool: TGroup): 
    user = nonroot_pool[0].user
    commands = [
        'sudo apt-get install -y zip unzip',
        'curl -s "https://get.sdkman.io" | bash',
        f'source "/home/{user}/.sdkman/bin/sdkman-init.sh" ; sdk install java 17.0.10-tem',
        'java -version'
    ]
    for cmd in commands:
        nonroot_pool.run(cmd, pty=True)

@check_installed('nextflow')
def install_nextflow(nonroot_pool: TGroup):
    commands = [
        'curl -s https://get.nextflow.io | bash',
        'sudo mv nextflow /usr/bin/',
        # 'mkdir bin',
        # 'echo "export PATH=$PATH:$HOME/bin" >> ~/.bashrc',
        # 'source ~/.bashrc'
    ]
    for cmd in commands:
        nonroot_pool.run(cmd, pty=True, watchers=[y_responder, yes_responder])

@check_installed('go')
def install_golang(nonroot_pool: TGroup):
    # How to know the latest golang version? 
    go_version = 'go1.23.3'
    commands = [
        'sudo rm -rf /usr/local/go /usr/bin/go',
        # f'wget https://go.dev/dl/{go_version}.linux-amd64.tar.gz',
        f'sudo tar -C /usr/local -xzf {go_version}.linux-amd64.tar.gz',
        f'sudo ln -s /usr/local/go/bin/go /usr/bin/go ',
        f'sudo ln -s /usr/local/go/bin/gofmt /usr/bin/gofmt',
        # 'export PATH=$PATH:/usr/local/go/bin',
        'go version'
    ]
    for cmd in commands:
        nonroot_pool.run(cmd, watchers=[y_responder, yes_responder])

@check_installed('pyenv')
def install_pyenv(nonroot_pool: TGroup):
    # Install pyenv
    nonroot_pool.run('rm -rf ~/.pyenv', pty=True, warn=True)
    commands = [
        'sudo apt-get update', 
        'sudo apt-get install -y build-essential libssl-dev libffi-dev libncurses5-dev zlib1g zlib1g-dev libreadline-dev libbz2-dev libsqlite3-dev make gcc liblzma-dev',
        'curl https://pyenv.run | bash',
    ]
    for cmd in commands:
        nonroot_pool.run(cmd, pty=True, watchers=[y_responder, yes_responder])
    
    # Add pyenv to bashrc config
    with open('bashrc-pyenv', 'w') as outfile:
        lines = [
            '# bashrc-pyenv'
            'export PYENV_ROOT="$HOME/.pyenv"', 
            '[[ -d $PYENV_ROOT/bin ]] && export PATH="$PYENV_ROOT/bin:$PATH"',
            'eval "$(pyenv init -)"',
            'eval "$(pyenv virtualenv-init -)"'
        ]
        content = '\n'.join(lines)
        outfile.write(f'{content}\n')

    nonroot_pool.put('bashrc-pyenv', 'bashrc-pyenv')
    commands = [
        # pyenv post-install
        'cat bashrc-pyenv >> ~/.bashrc',
        'rm -f bashrc-pyenv',
        'source ~/.bashrc',
        'pyenv doctor',
        
        # Install specific version -- 3.10.10? 
        'pyenv doctor',
        'pyenv install 3.10.10',
        'pyenv virtualenv 3.10.10 ec',
        'pyenv local ec ; pyenv global ec ; pyenv activate ec',
        
        # Libraries
        'python3 -m pip install --upgrade pip'
        'pip install git+ssh://git@github.com/xybu/python-resmon.git',
    ]
    
@check_installed('rclone')
def install_rclone(nonroot_pool: TGroup):
    user = nonroot_pool[0].user
    commands = [
        'sudo curl https://rclone.org/install.sh | sudo bash',
        'mkdir -p ~/.config/rclone/'
    ]
    for cmd in commands:
        nonroot_pool.run(cmd, pty=True)
    
    # Copy & test config
    lines = [
        '[remote]',
        'type = drive',
        'scope = drive',
        f'token = {os.environ.get("RCLONE_TOKEN")}',
        'team_drive = ', 
    ]
    content = '\n'.join(lines)
    with open('./conf-rclone', 'w') as outfile:
        outfile.write(content)
    nonroot_pool.put('./conf-rclone', 'conf-rclone')
    
    conf_path = "~/.config/rclone/rclone.conf"
    nonroot_pool.run(f'cat conf-rclone > {conf_path} && rm conf-rclone ; sudo chmod 600 {conf_path}')
    nonroot_pool.run('rclone lsd remote:/elastic-container')

def install_apt_deps(nonroot_pool: TGroup):
    commands = [
        'sudo apt-get update',
        # For python & pyenv
        'sudo apt-get install python3-pip',
        'sudo apt-get install -y build-essential libssl-dev libffi-dev libncurses5-dev zlib1g zlib1g-dev libreadline-dev libbz2-dev libsqlite3-dev make gcc liblzma-dev',
        # For QEMU
        'sudo apt-get install -y qemu-kvm virt-manager virtinst libvirt-clients bridge-utils libvirt-daemon-system dnsmasq cloud-utils dmidecode',
        'sudo systemctl enable --now libvirtd',
        'sudo systemctl start libvirtd',
        'sudo systemctl status libvirtd',
        'sudo usermod -aG kvm $USER',
        'sudo usermod -aG libvirt $USER',
    ]
    for cmd in commands:
        nonroot_pool.run(cmd, watchers=[y_responder, yes_responder])

if __name__ == "__main__":
    nonroot_pool = TGroup(
        'cc@129.114.109.74', # ectr-instance1
    )
    install_apt_deps(nonroot_pool)
    install_gh(nonroot_pool)
    install_docker(nonroot_pool)
    install_java(nonroot_pool)
    install_nextflow(nonroot_pool)
    install_golang(nonroot_pool)
    install_rclone(nonroot_pool)

    pull_docker_images(nonroot_pool)

    # Install pyresmon
    # Download dataset