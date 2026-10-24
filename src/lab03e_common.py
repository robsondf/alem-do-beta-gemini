"""Frozen Lab03E inputs. No earlier protocol/source is modified."""
import hashlib,json
from pathlib import Path
import numpy as np,pandas as pd
from lab03c import archive
from lab03d_inference import load as load_d

def digest(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def load(root,x,b,previous):
    lock=json.loads((root/'data/lab03e/inputs_manifest.json').read_text());plan=json.loads((root/'data/lab03e/plano_v1.json').read_text())
    assert digest(root/'data/lab03e/plano_v1.json')==lock['plan_sha256']
    assert digest(root/'data/lab03d/validacao_colab_20261023.json')==lock['reference_d_receipt_sha256']
    for n,h in lock['original_d_source_pins'].items():assert digest(root/n)==h,n
    assert digest(x)==lock['x_sha256'] and digest(b)==lock['b_sha256']
    d=load_d(root,x,b)
    with archive(previous,lock['d_sha256']) as z:
        d['previous']={name:pd.read_csv(z.open(name+'.csv'),float_precision='round_trip') for name in ['observed_static','observed_envelope','observed_envelope_intervals','observed_envelope_temporal','prediction_gains','prediction_metrics','prediction_intervals']}
        assert json.loads(z.read('registro_execucao.json'))['environment']=='Colab'
    d['plan_e']=plan;return d
