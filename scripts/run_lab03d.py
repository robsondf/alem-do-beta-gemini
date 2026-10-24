#!/usr/bin/env python3
"""Complementary inference validation and historical next-return forecasts."""
import argparse,hashlib,json,sys,time
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from lab03d_inference import load,simulate,analyze_static,analyze_temporal,observed
from lab03d_prediction import run as predict
if __name__=='__main__':
 p=argparse.ArgumentParser()
 for name in ['x-archive','b-archive','output']:p.add_argument('--'+name,type=Path,required=True)
 a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False);started=time.monotonic()
 lock=json.loads((ROOT/'data/lab03d/inputs_manifest.json').read_text());pp=ROOT/'data/lab03d/plano_v1.json'
 assert hashlib.sha256(pp.read_bytes()).hexdigest()==lock['plan_sha256']
 assert hashlib.sha256((ROOT/'data/lab03c/validacao_colab_20261023.json').read_bytes()).hexdigest()==lock['reference_c_colab_record_sha256']
 plan=json.loads(pp.read_text());d=load(ROOT,a.x_archive,a.b_archive)
 d['design'].to_csv(a.output/'design.csv',index=False);d['nuisance'].to_csv(a.output/'asset_nuisance.csv',index=False);d['annual_design'].to_csv(a.output/'annual_design.csv',index=False)
 arrays=simulate(d,plan);np.savez_compressed(a.output/'replicates.npz',**arrays)
 print('Full1000rep calibration complete; exporting all methods',flush=True)
 tables=analyze_static(d,plan,arrays);tables.update(analyze_temporal(d,plan,arrays));obs,cov=observed(d,plan);tables.update(obs)
 for name,t in tables.items():t.to_csv(a.output/(name+'.csv'),index=False)
 np.save(a.output/'observed_multiplier_covariance.npy',cov)
 prediction=predict(d,plan,a.output)
 metrics=dict(stage='Lab03D',replications_per_mechanism=1000,mechanisms=3,static_cases=197,temporal_family=474,unique_annual_cases=985,theta_cases=80,multiplier_draws_per_replication=999,static_methods=3,temporal_methods=2,prediction_configs=8,prediction_models=4,prediction_target='next-session observed log return',prediction_metrics_rows=len(prediction['prediction_metrics']),prediction_gains_rows=len(prediction['prediction_gains']),prediction_folds_rows=len(prediction['prediction_folds']),prediction_intervals_rows=len(prediction['prediction_intervals']),original_primary_replaced=False,prospective_untouched_holdout=False,retrospective_universe_bias_eliminated=False,provider_vintages_point_in_time=False,global_homologated=0,all_limitations_eliminated=False,runtime_seconds=time.monotonic()-started)
 (a.output/'metricas.json').write_text(json.dumps(metrics,indent=2)+'\n');print(json.dumps(metrics,indent=2))
