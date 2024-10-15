#!/usr/bin/env python3 

import os
from pathlib import Path
from typing import Any, Dict, Set, Tuple, List


if __name__ == "__main__":
    for dirpath, dnames, fnames in os.walk("./"):
        for f in fnames:
            if (f.startswith("1") or f.startswith("2") or f.startswith("3")):
                split_f: List[str] = f.split("-")
                app = split_f[2]
                if app == "gatk_basereca":
                    split_f[2] = "gatk_baserecal"
                    new_name = '-'.join(split_f)
                    p = Path(f)
                    p.rename(new_name)