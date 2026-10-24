#!/usr/bin/env python3
from pathlib import Path
import argparse
import hashlib
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from lab03 import run


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--x-archive', type=Path, required=True)
    parser.add_argument('--y-archive', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError('Preserve earlier runs; choose a new output folder')
    result = run(ROOT, args.x_archive, args.y_archive)
    args.output.mkdir(parents=True)
    for name in ['annual', 'halves', 'temporal_family', 'common_directions', 'rolling', 'summary']:
        result[name].to_csv(args.output/(name+'.csv'), index=False)
    (args.output/'metricas.json').write_text(json.dumps(result['metrics'], indent=2)+'\n')
    (args.output/'manifesto_exports.json').write_text(json.dumps({p.name:hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(args.output.iterdir()) if p.is_file()}, indent=2)+'\n')
    print(json.dumps(result['metrics'], indent=2))
