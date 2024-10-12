from typing import Any, Callable, Dict, List, Set, Tuple

import argparse
import datetime
import os
from pathlib import Path
import subprocess
import time

TOP_DIR = Path(os.path.dirname(os.path.realpath(__file__))).resolve()
AGENT_DIR = Path(os.path.join(TOP_DIR, "../")).resolve()

APPS: List[str] = [
    "bwa",
    "fastqc",
    "gatk_applybqsr",
    "gatk_baserecal",
    "samtools_index",
    "samtools_sort",
    "star",
    "trimmomatic"
]

POLICIES: List[str] = [
    "base",
    "burst",
    "autothrottle"
]

START_RUN: int = 1
END_RUN: int =  2

def run_agent(LABEL: str, policy: str) -> subprocess.Popen:

    policy_flags: Dict[str, str] = {
        'base': '',
        'burst': '--enable-burst',
        'autothrottle': '--enable-autothrottle',
    }
    assert(policy in policy_flags.keys()), f"Policy {policy} not found!"

    agent_outfile = open(f"{LABEL}-agent.log", "w")
    agent_command: str = f"sudo /usr/local/go/bin/go run main.go {policy_flags[policy]}".split()
    agent_ps = subprocess.Popen(
        agent_command,
        cwd=AGENT_DIR,
        stdin=subprocess.DEVNULL,
        stderr=agent_outfile,
        stdout=agent_outfile,
        close_fds=True,
    )
    outpath = Path(f"{AGENT_DIR}/agent-{LABEL}.log").resolve()
    print(f"Agent started with PID: {agent_ps.pid}, outfile: {outpath}")

    return agent_ps

def run_nextflow(INPUT_CONFIG: str, LABEL: str, OUT_LOG: str) -> subprocess.Popen:
    DIR: str = f'{TOP_DIR}/../'

    nextflow_command: str = f"nextflow run {DIR}/{LABEL}.nf -c {INPUT_CONFIG} -with-timeline {DIR}/{OUT_LOG.rstrip('.log')}-timeline.html -with-trace {DIR}/{OUT_LOG.rstrip('.log')}-trace.txt -with-report {DIR}/{OUT_LOG.rstrip('.log')}-report.html".split()

    nextflow_ps = subprocess.Popen(
        nextflow_command,
        cwd=TOP_DIR,
        stdin=subprocess.DEVNULL,
        stderr=subprocess.STDOUT,
        stdout=subprocess.PIPE,
        close_fds=True
    )

    return nextflow_ps


def run_resmon(LABEL: str) -> subprocess.Popen:
    resmon_command: str = f"resmon -o {LABEL}-resmon.csv".split()
    resmon_ps = subprocess.Popen(
        resmon_command,
        cwd=AGENT_DIR,
    )
    outpath = Path(f"{AGENT_DIR}/{LABEL}-resmon.csv").resolve()
    print(f"Resmon started with PID: {resmon_ps.pid}, outfile: {outpath}")

    return resmon_ps

def run_cmd(cmd: str) -> None:
    ps = subprocess.Popen(cmd,shell=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    output = ps.communicate()[0].decode('utf-8')
    print(output)
    
    return

def run_exp_prep(INPUT_CONFIG: str, LABEL: str, WORKFLOW: str) -> None:
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

    # Removed -cpu and -all csv files
    for (root, dirs, files) in os.walk(f'{AGENT_DIR}', topdown=True):
        for f in files:
            if LABEL not in f and f.endswith('.csv'):
                path = Path(f'{AGENT_DIR}/{f}').resolve()
                run_cmd(f"sudo rm -f {path}")
                print(f'Removed {path} ...')
        break # Check only the first level


    return

def run_exp_cleanup(LABEL: str) -> None:
    run_cmd(f"mkdir -p results/{LABEL}")

    # Gather NF report, timeline, trace, config, and script
    suffixes: List[str] = ["-report.html", "-timeline.html", 
                           "-trace.txt", "-resmon.csv", "-agent.log", 
                           ".config", ".nf"]
    for suffix in suffixes:
        run_cmd(f"sudo mv -f {LABEL}{suffix} results/{LABEL}")
        print(f'Moved {LABEL}{suffix} to results/{LABEL} ...')

    # Get <cid>-all and <cid>-cpu csv files.
    for (root, dirs, files) in os.walk(f'{AGENT_DIR}', topdown=True):
        for f in files:
            if LABEL not in f and f.endswith('.csv'):
                new_name: str = f"{LABEL}-{f.rstrip('.csv').split('-')[-1]}.csv"
                path = Path(f'{AGENT_DIR}/{f}').resolve()
                run_cmd(f"sudo mv -f {path} results/{LABEL}/{new_name}")
                print(f'Moved {path} to results/{LABEL}/{new_name} ...')
        break # Check only the first level
    
    # Change ownership of results
    run_cmd(f"sudo chown -R cc:cc results/{LABEL}")

    return