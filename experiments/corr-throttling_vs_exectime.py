#!/usr/bin/env python3

from typing import Any, Callable, Dict, List, Set, Tuple

import argparse
import datetime
import os
from pathlib import Path
import subprocess
import time

"""
Script for throttling vs exec. time correlation experiment.
"""

TOP_DIR = Path(os.path.dirname(os.path.realpath(__file__))).resolve()
AGENT_DIR = Path(os.path.join(TOP_DIR, "../")).resolve()

APPS: List[str] = [
    "bwa",
]

parser = argparse.ArgumentParser(
    prog="corr-throttling_vs_exectime",
    description=f"Experiment for correlation between throttling and execution time.",
    # epilog='Text at the bottom of help'
)

parser.add_argument("--app", type=str, choices=APPS, help="Application to run")

args = parser.parse_args()

def run_agent() -> subprocess.Popen:
    timestamp: str = datetime.datetime.now().isoformat()
    agent_outfile = open(f"agent-{LABEL}.log", "w")
    agent_command: str = f"sudo /usr/local/go/bin/go run main.go".split()
    agent_ps = subprocess.Popen(
        agent_command,
        cwd=AGENT_DIR,
        stdin=subprocess.DEVNULL,
        stderr=agent_outfile,
        stdout=agent_outfile,
        close_fds=True,
    )
    print(f"Agent started with PID: {agent_ps.pid}")

    return agent_ps

def run_nextflow(exp_dir: str = '') -> subprocess.Popen:
    nextflow_command: str = f"nextflow run {LABEL}.nf -c {INPUT_CONFIG} -with-timeline {OUT_LOG.rstrip('.log')}-timeline.html -with-trace {OUT_LOG.rstrip('.log')}-trace.txt -with-report {OUT_LOG.rstrip('.log')}-report.html".split()

    nextflow_ps = subprocess.Popen(
        nextflow_command,
        cwd=TOP_DIR,
        stdin=subprocess.DEVNULL,
        stderr=subprocess.STDOUT,
        stdout=subprocess.PIPE,
        close_fds=True
    )

    return nextflow_ps


def run_resmon(exp_dir: str = '') -> subprocess.Popen:
    resmon_command: str = f"resmon -o resmon-{LABEL}.csv".split()
    resmon_ps = subprocess.Popen(
        resmon_command,
        cwd=AGENT_DIR,
    )
    print(f"Resmon started with PID: {resmon_ps.pid}")

    return resmon_ps

def run_cmd(cmd: str) -> None:
    ps = subprocess.Popen(cmd,shell=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    output = ps.communicate()[0].decode('utf-8')
    print(output)
    
    return

def run_exp_prep(exp_dir: str = '') -> None:
    # Kill previous resmon and agent process
    print(f'Killing previous resmon and agent process ...')
    cmd: str = "ps aux | grep resmon | tr -s ' ' | cut -d ' ' -f 2 | xargs -I {} sudo kill -9 {}"
    run_cmd(cmd)
    cmd: str = "ps aux | grep \"main.go\" | tr -s ' ' | cut -d ' ' -f 2 | xargs -I {} sudo kill -9 {}"
    run_cmd(cmd)
    cmd: str = "ps aux | grep \"go-build\" | tr -s ' ' | cut -d ' ' -f 2 | xargs -I {} sudo kill -9 {}"
    run_cmd(cmd)

    # Clear PageCache, dentries, indoes, and swap
    cmd: str = "sudo sync; echo 3 | sudo tee /proc/sys/vm/drop_caches ; sudo swapoff -a && sudo swapon -a"
    print(f'Clearing PageCache, dentries, indoes, and swap ...')
    run_cmd(cmd)

    # Clear artefacts from previous runs
    cmd: str = 'rm LoadDuration.txt'
    print(f'Removing artefacts from previous runs ...')
    run_cmd(cmd)

    # Backup NF script
    print(f'Backing up NF script & config ...')
    run_cmd(f'cp {WORKFLOW} {LABEL}.nf')
    run_cmd(f'cp {INPUT_CONFIG} {LABEL}.config')

    # Modify allocatedCores
    run_cmd(f'sed -E "s|allocatedCores :=.*|allocatedCores := int64({STEP})|" -i {PATH_CONTROLLER}')

    return

def run_exp_cleanup(exp_dir: str = '') -> None:
    run_cmd(f"mkdir -p results/{LABEL}")

    # Gather NF report, timeline, trace, config, and script
    suffixes: List[str] = ["-report.html", "-timeline.html", "-trace.txt", ".config", ".nf"]
    for suffix in suffixes:
        run_cmd(f"cp {LABEL}{suffix} results/{LABEL}")

    run_cmd(f"cp ../*-all.csv results/{LABEL}")
    run_cmd(f"cp ../*-cpu.csv results/{LABEL}")

    return

if __name__ == "__main__":
    print(f"{TOP_DIR}, running program: {args.app}")
    
    global WORKFLOW, INPUT_CONFIG, LABEL, STEP, OUT_LOG, PATH_CONTROLLER
    WORKFLOW=f"/home/cc//elastic-container/containermod/experiments/nf_scripts/bwa.nf"
    INPUT_CONFIG=f"/home/cc//elastic-container/containermod/experiments/configs/bwa.config"
    PATH_CONTROLLER=f"/home/cc//elastic-container/containermod/controller/controller.go"
    STEP=10
    LABEL=f"base-bwa_corrstep{STEP}"
    OUT_LOG=f"{LABEL}.log"

    try:
        assert args.app, "Application not provided"

        # Run prep
        run_exp_prep(exp_dir=TOP_DIR)

        # Run Agent
        agent_ps = run_agent()
        # Run Resmon
        resmon_ps = run_resmon()
        # Run Nextflow
        nextflow_ps = run_nextflow()

        while nextflow_ps.poll() is None:
            for line in nextflow_ps.stdout:
                print(line.decode('utf-8'))
            time.sleep(1)

        print('Nextflow process finished!')
        # while agent_ps.poll() is None:
        subprocess.check_output(f"sudo kill -9 {agent_ps.pid}".split())
        print('Agent killed!')
        # while resmon_ps.poll() is None:
        subprocess.check_output(f"sudo kill -9 {resmon_ps.pid}".split())
        print('Resmon killed!')

        # Cleanup
        run_exp_cleanup(exp_dir=TOP_DIR)

        pass
    except Exception as e:
        print(f"Error: {e}")
        # parser.print_help()
