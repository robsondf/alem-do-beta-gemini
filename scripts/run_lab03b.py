#!/usr/bin/env python3
from pathlib import Path
import argparse,json,hashlib,sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from lab03b import run
if __name__=='__main__':
    p=argparse.ArgumentParser()
    for name in ['x-archive','y-archive','lab03-archive','output']:p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args()
    if a.output.exists():raise FileExistsError('Choose a new output directory')
    out=run(ROOT,a.x_archive,a.y_archive,a.lab03_archive);a.output.mkdir(parents=True)
    for name,table in out.items():
        if name!='metrics':table.to_csv(a.output/(name+'.csv'),index=False)
    (a.output/'metricas.json').write_text(json.dumps(out['metrics'],indent=2)+'\n')
    hashes={str(q.relative_to(a.output)):hashlib.sha256(q.read_bytes()).hexdigest() for q in sorted(a.output.rglob('*')) if q.is_file()}
    (a.output/'manifesto_exports.json').write_text(json.dumps(hashes,indent=2)+'\n');print(json.dumps(out['metrics'],indent=2))
