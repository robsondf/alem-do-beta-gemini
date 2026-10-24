#!/usr/bin/env python3
import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from lab02_robustness_suite import run


def execute(archive, output):
    if output.exists():
        raise FileExistsError('Choose a new output directory; preserve earlier executions')
    lock = json.loads((ROOT / 'data/lab02/lab02y_inputs_manifest.json').read_text())
    for rel, digest in lock['repo_files'].items():
        if hashlib.sha256((ROOT / rel).read_bytes()).hexdigest() != digest:
            raise ValueError('Repository input hash mismatch: ' + rel)
    result = run(archive, lock)
    output.mkdir(parents=True)
    for key in ['hac', 'simple', 'events', 'bootstrap', 'exclusions', 'summary']:
        result[key].to_csv(output / (key + '.csv'), index=False)
    (output / 'metricas.json').write_text(json.dumps(result['metrics'], indent=2) + '\n')
    (output / 'manifesto_exports.json').write_text(json.dumps({p.name: hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(output.iterdir()) if p.is_file()}, indent=2) + '\n')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--archive', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(execute(args.archive, args.output)['metrics'], indent=2))
