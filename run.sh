#!/bin/bash

FLAGS=$1

# go build . ; sudo ./main ;
mv -f *.csv results/
sudo $(which go) run main.go $FLAGS
