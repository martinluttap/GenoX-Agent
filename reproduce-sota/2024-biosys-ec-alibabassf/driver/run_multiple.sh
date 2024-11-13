#!/bin/bash

for i in {1..3}; do 
    # for BURST in 100000 400000 600000 1200000 1800000; do 
        echo ; 
        echo "Run ${i} Burst ${BURST}" ; 
        echo ; 
        sed -e "s|RUN=.*|RUN=${i}|" -i run.sh ; 
        sed -e "s|BURST_TIME=.*|BURST_TIME=${BURST}|" -i enable_burst.sh ; 
        # ./enable_burst.sh; ./run.sh; 
	./disable_burst.sh ; ./run.sh
    # done ; 
done
