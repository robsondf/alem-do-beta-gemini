#!/usr/bin/env python3
import argparse,hashlib,json,sys,time
from pathlib import Path
import numpy as np,pandas as pd
from threadpoolctl import threadpool_limits
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from lab03d_inference import load
from lab03d_envelope import generate,summarize,observed_table
if __name__=='__main__':
 p=argparse.ArgumentParser()
 for n in ['output','x-archive','b-archive']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();lock=json.loads((ROOT/'data/lab03d/inputs_manifest.json').read_text());addp=ROOT/'data/lab03d/adendo_envelope_v1.json';assert hashlib.sha256(addp.read_bytes()).hexdigest()==lock['envelope_addendum_sha256']
 plan=json.loads((ROOT/'data/lab03d/plano_v1.json').read_text());ad=json.loads(addp.read_text());d=load(ROOT,a.x_archive,a.b_archive,);started=time.monotonic()
 with threadpool_limits(limits=1):bank,e,se=generate(d,plan,ad)
 np.savez_compressed(a.output/'envelope_replicates.npz',calibration_t=bank,validation_error=e,validation_se=se)
 for name,t in summarize(d,plan,bank,e,se).items():t.to_csv(a.output/(name+'.csv'),index=False)
 observed_table(d,bank,pd.read_csv(a.output/'observed_static.csv',float_precision='round_trip')).to_csv(a.output/'observed_envelope.csv',index=False)
 receipt=dict(stage='Lab03D Monte Carlo envelope',calibration_per_mechanism=9999,validation_per_mechanism=1000,independent_calibration_validation_streams=True,conditional_on_finite_three_mechanism_class=True,validation_mc_intervals_conditioned_on_bank=True,original_primary_replaced=False,all_limitations_eliminated=False,global_homologated=0,runtime_seconds=time.monotonic()-started)
 (a.output/'metricas_envelope.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt,indent=2))
