#!/bin/bash
# Change the path of the image as desired
OS_IMAGE=./ubuntu-20.qcow2
USER_IMAGE=./user-data.img
REF_FILES_IMAGE=./genomics_references.img

# Here we use QEMU to run the virtual machine
sudo qemu-system-x86_64 \
    -name "Ubuntu 29" \
    -cpu host \
    -smp 92,maxcpus=92\
    -m 128G \
    -enable-kvm \
    -drive file=${OS_IMAGE},if=ide,cache=none,aio=native,format=qcow2 \
    -drive file=${REF_FILES_IMAGE},if=ide,cache=none,aio=native,format=raw \
    -netdev user,id=user0,hostfwd=tcp::10101-:22 \
    -device virtio-net-pci,netdev=user0 \
    -drive file=${USER_IMAGE},format=raw \
    -nographic
