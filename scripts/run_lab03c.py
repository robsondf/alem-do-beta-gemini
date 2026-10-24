#!/usr/bin/env python3
"""Execute the frozen1000-replication static-inference calibration."""
import argparse, hashlib, json, sys, time
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
from lab03c import prepare, simulate, analyze, sha

if __name__ == '__main__':
    p = argparse.ArgumentParser()
    for name in ['x-archive', 'b-archive', 'output']:
        p.add_argument('--'+name, type=Path, required=True)
    a = p.parse_args(); a.output.mkdir(parents=True, exist_ok=False)
    lock = json.loads((ROOT/'data/lab03c/inputs_manifest.json').read_text())
    plan_path = ROOT/'data/lab03c/plano_v1.json'
    assert sha(plan_path) == lock['plan_sha256']
    plan = json.loads(plan_path.read_text()); started = time.monotonic()
    d = prepare(a.x_archive, a.b_archive, lock)
    d['design'].to_csv(a.output/'design.csv', index=False)
    d['nuisance'].to_csv(a.output/'asset_nuisance.csv', index=False)
    error, se = simulate(d, plan)
    np.savez_compressed(a.output/'replicates.npz', error=error, se=se)
    for name, table in analyze(d, plan, error, se).items():
        table.to_csv(a.output/(name+'.csv'), index=False)
    metrics = dict(stage='Lab03C', replications_per_mechanism=1000, mechanisms=3, primary_cases=197,
        unique_synthetic_paths_per_replication=117, lag_configurations=3, effect_patterns=9,
        optimized_contrast_evaluations=3*1000*197, grid_inference_evaluations=3*1000*197*3*9,
        calibration_rows=1773, power_rows=15957, family_rows=81, panel_rows=162,
        runtime_seconds=time.monotonic()-started, temporal_family_474_calibrated=False,
        empirical_return_matrices_modified=False, independent_preregistration=False,
        real_data_global_homologated=0, out_of_sample_prediction_tested=False, equivalence_tested=False)
    (a.output/'metricas.json').write_text(json.dumps(metrics, indent=2)+'\n')
    print(json.dumps(metrics, indent=2))
