import glob
import logging
import pathlib
import os

from collections import deque
from concurrent.futures import ThreadPoolExecutor
from functools import partial
from subprocess import PIPE, CalledProcessError, CompletedProcess, Popen
from typing import Any, Dict, List, Set

TARGET_BPS: List[int] = [1.0, 8035.0, 15179.0, 20993.0, 26837.0, 33526.0, 41225.0, 48438.0, 55049.0, 61332.0, 67777.0, 74482.0, 83374.0, 93677.0, 105927.0, 121690.0, 140897.0, 164547.0, 187551.0, 208687.0, 234471.0, 262667.0, 294752.0, 317710.0, 337975.0, 356234.0, 375405.0, 393980.0, 414493.0, 437127.0, 464087.0, 490041.0, 518136.0, 541473.0, 563473.0, 584447.0, 602149.0, 622378.0, 643827.0, 667040.0, 693457.0, 731165.0, 789923.0, 903460.0, 1144248.0, 1457447.0, 1697954.0, 1905781.0, 2100907.0, 2289859.0, 2485987.0, 2666523.0, 2839796.0, 3013351.0, 3201376.0, 3410971.0, 3619466.0, 3837896.0, 4067867.0, 4340680.0, 4704751.0, 5090657.0, 5424893.0, 5709911.0, 5938427.0, 6142344.0, 6335658.0, 6516425.0, 6688536.0, 6863293.0, 7033424.0, 7218506.0, 7410085.0, 7642426.0, 7889795.0, 8228551.0, 8659302.0, 9275858.0, 10185860.0, 11173175.0, 12209735.0, 13510437.0, 15298048.0, 17101768.0, 19154562.0, 24213813.0, 29068954.0, 32507148.0, 38080054.0, 52841121.0, 133108397.0, 135308103.0, 139028521.0, 142322182.0, 146416747.0, 150942581.0, 153926030.0, 157264723.0, 160979596.0, 164764518.0, 183811691.0]

def stream_command(
    args,
    *,
    stdout_handler=logging.info,
    stderr_handler=logging.error,
    check=True,
    text=True,
    stdout=PIPE,
    stderr=PIPE,
    **kwargs,
):
    """Mimic subprocess.run, while processing the command output in real time."""
    with Popen(args, text=text, stdout=stdout, stderr=stderr, **kwargs) as process:
        with ThreadPoolExecutor(2) as pool:  # two threads to handle the streams
            exhaust = partial(pool.submit, partial(deque, maxlen=0))
            exhaust(stdout_handler(line[:-1]) for line in process.stdout)
            exhaust(stderr_handler(line[:-1]) for line in process.stderr)
    retcode = process.poll()
    if check and retcode:
        raise CalledProcessError(retcode, process.args)
    return CompletedProcess(process.args, retcode)

if __name__ == "__main__":
    count: int = 0
    for bp in TARGET_BPS[50:]:
        # First, delete work folder
        cwd: str = pathlib.Path(__file__).parent.resolve()
        stream_command(['rm', '-rf', 'work/'], cwd=cwd)

        # Then run the generation once
        nextflow_cmd: List[str] = f"nextflow nf_scripts/input_generation.nf --NUM_BP {int(bp)}".split(' ')
        stream_command(nextflow_cmd, cwd=cwd, stdout_handler=print, stderr_handler=print)

        # Get *.fastq files and store.
        for filepath in glob.iglob(str(cwd) + '/work/**/*.fastq', recursive=True):
            if not os.path.islink(filepath):
                print(filepath)
                mod_name: str = f'{round(bp * 360 / 1e6)}mb-{filepath.split("/")[-1]}'
                copy_cmd: List[str] = ['mv', filepath, f'./generated-read-files/{mod_name}']
                stream_command(copy_cmd, cwd=cwd, stderr_handler=print, stdout_handler=print)
                count += 1
                print(f"[{count}/{len(TARGET_BPS)}] Finished {mod_name} ...")