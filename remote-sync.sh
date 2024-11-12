#!/bin/bash

rsync -azP -e 'ssh -p10101' --exclude *results* --exclude **out-metric** /home/cc/elastic-container/remote-staging/ cc@localhost:/home/cc/elastic-container/containermod/
