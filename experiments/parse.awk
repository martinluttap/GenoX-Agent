#!/bin/awk

BEGIN {
    FS=","
}

{ 
    if (NR==1) 
        { printf ("timestamp,total_cpu_perc\n") } 
    else 
        { printf ("%s,%f,%f\n",$1,$2) }  
}

END {}