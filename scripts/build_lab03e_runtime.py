#!/usr/bin/env python3
"""Build the pinned minimal runtime; no market data or historical outputs."""
import argparse,hashlib,json,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def build(destination):
    lock=json.loads((ROOT/'data/lab03e/inputs_manifest.json').read_text());names=set(lock['original_d_source_pins'])
    for pattern in ['src/lab03e*.py','scripts/*lab03e*.py','tests/test_lab03e.py','data/lab03e/primary/*']:
        names.update(str(p.relative_to(ROOT)) for p in ROOT.glob(pattern) if p.is_file())
    names.update(['data/lab03e/plano_v1.json','data/lab03e/inputs_manifest.json','data/lab03e/primary_sources_manifest.json','data/lab03d/validacao_colab_20261023.json','data/lab02/semantica_caixa_v1/recuperacao_fras_visivel_2024_2025.csv','notebooks/Lab03D_inferencia_previsao.ipynb'])
    manifest={name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in sorted(names)}
    for name,h in lock['original_d_source_pins'].items():assert manifest[name]==h,name
    target=ROOT/'data/lab03e/runtime_manifest.json';target.write_text(json.dumps(manifest,indent=2)+'\n')
    with zipfile.ZipFile(destination,'w',zipfile.ZIP_DEFLATED) as z:
        for name in sorted(names|{'data/lab03e/runtime_manifest.json'}):z.write(ROOT/name,name)
    print(json.dumps(dict(files=len(manifest),bytes=destination.stat().st_size,sha256=hashlib.sha256(destination.read_bytes()).hexdigest()),indent=2))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--destination',required=True,type=Path);build(p.parse_args().destination)
