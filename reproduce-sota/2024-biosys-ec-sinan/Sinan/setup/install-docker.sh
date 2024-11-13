#!/bin/bash
set -e

install_docker_for_centos () {
    echo "Installing for CentOs"

    # install required dependencies
    echo 'installing dependencies...'
    sudo yum install -y yum-utils device-mapper-persistent-data lvm2 yum-versionlock &>/dev/null

    # add docker stable repo to our system
    echo 'installing docker...'
    sudo yum-config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo &>/dev/null

    # install docker
    #sudo yum install -y docker-ce
    sudo yum install -y docker-ce-19.03.12-3.el7 

    # hold the docker version
    sudo yum versionlock add docker-ce 

    echo 'configuring docker service...'
    # enable docker service to start on boot
    sudo systemctl enable docker 

    # start docker service
    sudo systemctl start docker 

    # print docker service status
    echo 'showing docker service status...'
    systemctl list-units --type service | grep docker

    # print docker version
    echo -e "\n\nfinished installing docker-ce\n$(docker -v)"

    sudo groupadd docker

    sudo usermod -aG docker $USER

    newgrp docker


}

install_docker_for_ubuntu () {
    echo "Installing for Ubuntu"

    # update list of available packages
    sudo apt update
    sudo apt install -y apt-transport-https ca-certificates curl software-properties-common
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo apt-key add -
    sudo add-apt-repository "deb [arch=amd64] https://download.docker.com/linux/ubuntu bionic stable"
    sudo apt update
    
    echo 'installing docker...'
    sudo apt install -y docker-ce=5:19.03.12~3-0~ubuntu-bionic 
    
    # hold the docker version
    sudo apt-mark hold docker-ce 
    
    # print docker service status
    echo 'showing docker service status...'
    sudo service --status-all | grep docker
    
    sudo groupadd docker
    
    sudo usermod -aG docker $USER
    
    newgrp docker

}

if grep -i ubuntu /etc/os-release >/dev/null; then
    install_docker_for_ubuntu
else
    install_docker_for_centos
fi

# for testing
docker container run hello-world
