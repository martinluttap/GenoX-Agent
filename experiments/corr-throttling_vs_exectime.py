#!/usr/bin/env python3

from typing import Any, Callable, Dict, List, Set, Tuple

import argparse
import datetime
import os
import subprocess
import time

"""
Script for throttling vs exec. time correlation experiment.
"""

TOP_DIR = os.path.dirname(os.path.realpath(__file__))
AGENT_DIR = os.path.join(TOP_DIR, "../")

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
    agent_outfile = open(f"agent-{timestamp}.log", "w")
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

if __name__ == "__main__":
    print(f"{TOP_DIR}, running program: {args.app}")
    try:
        assert args.app, "Application not provided"

        timestamp: str = datetime.datetime.now().isoformat()

        # Run Agent
        agent_ps = run_agent()
        pass
    except Exception as e:
        print(f"Error: {e}")
        parser.print_help()
