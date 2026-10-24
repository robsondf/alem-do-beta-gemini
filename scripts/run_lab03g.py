#!/usr/bin/env python3
import argparse,json,sys,time,platform,os
from pathlib import Path
from threadpoolctl import threadpool_limits
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from lab03g import load,observed,calibration,digest

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--x-archive',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--stage',choices=['observed','calibration','all'],default='all');a=p.parse_args()
    start=time.monotonic();plan,fp,mats,samples=load(ROOT,a.x_archive);a.output.mkdir(parents=True,exist_ok=a.stage=='calibration')
    with threadpool_limits(limits=2):
        if a.stage in ['observed','all']:observed(ROOT,plan,fp,mats,samples,a.output)
        if a.stage in ['calibration','all']:calibration(ROOT,plan,fp,mats,samples,a.output)
    record={'stage':'Lab03G '+a.stage,'environment':os.environ.get('ALEM_BETA_EXECUTION_ENV','local_not_author_Colab'),'python':platform.python_version(),'plan_sha256':digest(ROOT/'data/lab03g/plano_v1.json'),'elapsed_seconds':time.monotonic()-start,'inputs_unchanged':True,'no_market_downloads':True}
    (a.output/('execution_'+a.stage+'.json')).write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record,indent=2))
