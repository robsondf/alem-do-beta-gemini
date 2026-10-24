#!/usr/bin/env python3
import argparse,json,sys,time
from pathlib import Path
from threadpoolctl import threadpool_limits
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from lab03e_common import load
from lab03e_prediction import run
if __name__=='__main__':
 p=argparse.ArgumentParser()
 for n in ['output','x-archive','b-archive','d-archive']:p.add_argument('--'+n,required=True,type=Path)
 a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False);started=time.monotonic();d=load(ROOT,a.x_archive,a.b_archive,a.d_archive);d['previous_plan_seed']=json.loads((ROOT/'data/lab03d/plano_v1.json').read_text())['seed_entropy']
 with threadpool_limits(limits=1):tables=run(d,a.output)
 for name,table in tables.items():table.to_csv(a.output/(name+'.csv'),index=False)
 record=dict(stage='Lab03E predictive risk',validation_scenarios=6,replications_per_scenario=1000,unique_cases=394,blocks=[21,42,63],bootstrap_replications=1999,conditional_on_observed_market=True,joint_future_market_uncertainty_validated=False,bootstrap_banks_fixed_independent_of_simulated_errors=True,coverage_evaluated_not_assumed=True,global_homologated=0,runtime_seconds=time.monotonic()-started);(a.output/'metricas_previsao.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record,indent=2))
