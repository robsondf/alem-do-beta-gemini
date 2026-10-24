#!/usr/bin/env python3
import argparse,json,sys,time
from pathlib import Path
from threadpoolctl import threadpool_limits
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from lab03e_common import load
from lab03e_inference import operators,calibration,validation,summaries,observed
if __name__=='__main__':
 p=argparse.ArgumentParser()
 for n in ['output','x-archive','b-archive','d-archive']:p.add_argument('--'+n,required=True,type=Path)
 a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False);started=time.monotonic();d=load(ROOT,a.x_archive,a.b_archive,a.d_archive);dd=operators(d);dd['catalog'].to_csv(a.output/'bank_designs.csv',index=False);d['design'].to_csv(a.output/'design.csv',index=False);d['annual_design'].to_csv(a.output/'annual_design.csv',index=False);d['nuisance'].to_csv(a.output/'asset_nuisance.csv',index=False)
 with threadpool_limits(limits=1):
  bank=calibration(d,dd,a.output);v=validation(d,dd,a.output);tables={**summaries(d,dd,bank,v),**observed(d,dd,bank)}
 for name,table in tables.items():table.to_csv(a.output/(name+'.csv'),index=False)
 record=dict(stage='Lab03E inference',bank_per_mechanism=99999,independent_streams=3,protected_mechanisms=3,validation_mechanisms=6,validation_per_mechanism=1000,out_of_class_stresses_do_not_expand_guarantee=True,original_primary_replaced=False,global_homologated=0,runtime_seconds=time.monotonic()-started);(a.output/'metricas_inferencia.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record,indent=2))
