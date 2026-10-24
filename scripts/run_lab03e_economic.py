#!/usr/bin/env python3
import argparse,json,sys
from pathlib import Path
from threadpoolctl import threadpool_limits
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from lab03e_common import load
from lab03e_economic import run
if __name__=='__main__':
 p=argparse.ArgumentParser()
 for n in ['output','x-archive','b-archive','d-archive']:p.add_argument('--'+n,required=True,type=Path)
 a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False);d=load(ROOT,a.x_archive,a.b_archive,a.d_archive)
 with threadpool_limits(limits=1):tables=run(d)
 for name,t in tables.items():t.to_csv(a.output/(name+'.csv'),index=False)
 record=dict(stage='Lab03E economic impact',cases=len(tables['economic_ledger']),sensitivity_rows=len(tables['economic_sensitivities']),global_homologated=0,primary_matrix_modified=False,diagnostic_mask_not_correction=True,insufficient=int(tables['economic_sensitivities'].status.eq('insufficient').sum()))
 (a.output/'metricas_economia.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record,indent=2))
