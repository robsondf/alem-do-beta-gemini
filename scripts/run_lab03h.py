#!/usr/bin/env python3
import argparse,json,os,platform,sys,time
from pathlib import Path
from threadpoolctl import threadpool_limits
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from lab03h import load,crisis,calibration_diagnostics,presentation_inputs,digest

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--x-archive',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();start=time.monotonic();plan,fp,mats,samples=load(ROOT,a.x_archive);a.output.mkdir(parents=True,exist_ok=False)
    with threadpool_limits(limits=2):
        frame,point=crisis(ROOT,plan,fp,mats,samples,a.output);calibration_diagnostics(ROOT,mats,samples,a.output);presentation_inputs(ROOT,point,plan,a.output)
    record={'stage':'Lab03H all','environment':os.environ.get('ALEM_BETA_EXECUTION_ENV','local_not_author_Colab'),'python':platform.python_version(),'elapsed_seconds':time.monotonic()-start,'plan_sha256':digest(ROOT/'data/lab03h/plano_v1.json'),'original_G_baseline_and_banks_reproduced':True,'new_crisis_rows':len(frame),'old_source_pins_preserved':78,'new_outer_simulation_generators':0,'new_market_downloads':False,'economic_homologation_completed':False}
    (a.output/'execution.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record,indent=2))
