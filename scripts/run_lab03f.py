#!/usr/bin/env python3
"""Run the complete post-review batch with the authenticated existing X archive."""
import argparse
import json
import sys
from pathlib import Path
from threadpoolctl import threadpool_limits
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from lab03f import run

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--x-archive',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    with threadpool_limits(limits=1):result=run(ROOT,a.x_archive,a.output)
    print(json.dumps(result,indent=2))
