#!/usr/bin/env python3
import argparse,hashlib,json,sys,time
from pathlib import Path
import numpy as np
from threadpoolctl import threadpool_limits
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from lab03d_inference import load
from lab03d_rank import designs,equivalence_check,generate,summarize,observed,tail_precision
if __name__=='__main__':
 p=argparse.ArgumentParser()
 for n in ['output','x-archive','b-archive']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();lock=json.loads((ROOT/'data/lab03d/inputs_manifest.json').read_text());ap=ROOT/'data/lab03d/adendo_classes_equivalencia_v1.json';assert hashlib.sha256(ap.read_bytes()).hexdigest()==lock['equivalence_classes_addendum_sha256']
 plan=json.loads((ROOT/'data/lab03d/plano_v1.json').read_text());ad=json.loads(ap.read_text());started=time.monotonic();d=load(ROOT,a.x_archive,a.b_archive);dd=designs(d);diff=equivalence_check(d,dd)
 dd['catalog'].to_csv(a.output/'bank_designs.csv',index=False)
 print('Equivalent design bank:',len(dd['tasks']),'unique designs; maximum invariant difference',diff,flush=True)
 with threadpool_limits(limits=1):bank,values=generate(d,dd,plan,ad)
 np.savez_compressed(a.output/'envelope_replicates.npz',calibration_t=bank,static_map=dd['static'],annual_map=dd['annual'],theta_map=dd['theta'],**values)
 obs=observed(d,dd,bank);obs['observed_envelope_tail_mc']=tail_precision(d,dd,bank,obs)
 for name,t in {**summarize(d,dd,plan,bank,values),**obs}.items():t.to_csv(a.output/(name+'.csv'),index=False)
 receipt=dict(stage='Lab03D rank envelope',unique_bank_designs=len(dd['tasks']),design_counts=dd['catalog'].kind.value_counts().to_dict(),mapped_static=197,mapped_annual=985,mapped_theta=80,equivalence_max_difference=diff,calibration_per_mechanism=9999,validation_per_mechanism=1000,calibration_validation_independent=True,finite_mechanism_class_conditional=True,bank_conditional_mc_intervals=True,original_primary_replaced=False,global_homologated=0,all_limitations_eliminated=False,runtime_seconds=time.monotonic()-started)
 (a.output/'metricas_envelope.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt,indent=2))
