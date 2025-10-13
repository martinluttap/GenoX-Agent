#!/bin/bash
# Dynamically set thread env vars to use all available CPU cores
NUM_CORES=$(nproc)
export OMP_NUM_THREADS=$NUM_CORES
export MKL_NUM_THREADS=$NUM_CORES
export OPENBLAS_NUM_THREADS=$NUM_CORES
export VECLIB_MAXIMUM_THREADS=$NUM_CORES
export NUMEXPR_NUM_THREADS=$NUM_CORES

exec "$@"
