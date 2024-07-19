#!/bin/bash

# go build . ; sudo ./main ;
mv -f *.csv results/
sudo $(which go) run main.go
