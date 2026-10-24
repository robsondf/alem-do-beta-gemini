#!/usr/bin/env python3
"""Audit the saved F notebook/export without executing their code or new generators."""
import argparse
import ast
import base64
import hashlib
import io
import json
from pathlib import Path
import re
import zipfile
import numpy as np
import pandas as pd
from PIL import Image
import fitz

ROOT=Path(__file__).resolve().parents[1]


def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def audit(notebook,export,output):
    expected=json.loads((ROOT/'notebooks/Lab03F_pos_parecer.ipynb').read_text())
    nb=json.loads(notebook.read_text());assert len(nb['cells'])==len(expected['cells'])==10
    assert all(c['cell_type']==e['cell_type'] and ''.join(c['source'])==''.join(e['source']) for c,e in zip(nb['cells'],expected['cells']))
    codes=[c for c in nb['cells'] if c['cell_type']=='code'];assert [c.get('execution_count') for c in codes]==list(range(1,7))
    assert not [o for c in codes for o in c.get('outputs',[]) if o.get('output_type')=='error']
    stream=''.join(''.join(o.get('text',[])) if isinstance(o.get('text',[]),list) else o.get('text','') for c in codes for o in c.get('outputs',[]))
    match=re.search(r'Export: (\S+) \| bytes: (\d+) \| SHA256: ([0-9a-f]{64})',stream)
    assert match and export.stat().st_size==int(match[2]) and sha(export)==match[3]
    pins=None
    for node in ast.parse(''.join(nb['cells'][3]['source'])).body:
        if isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='SOURCE_PINS' for t in node.targets):pins=ast.literal_eval(node.value)
    assert pins and len(pins)==15
    output.mkdir(parents=True,exist_ok=False)
    with zipfile.ZipFile(export) as z:
        manifest=json.loads(z.read('manifesto_exports.json'));assert len(z.namelist())==len(set(z.namelist()))
        assert set(z.namelist())==set(manifest)|{'manifesto_exports.json'}
        for n,h in manifest.items():
            assert not Path(n).is_absolute() and '..' not in Path(n).parts
            raw=z.read(n);assert hashlib.sha256(raw).hexdigest()==h
            p=output/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw)
        for n,h in pins.items():assert manifest['runtime/'+n]==h
    actual=output/'outputs';reference=ROOT/'results/tables/lab03f_pos_parecer_20261024'
    report=dict(passed=True,notebook_sha256=sha(notebook),export_sha256=sha(export),export_bytes=export.stat().st_size,
                source_cells_identical=10,sequential_code_cells=6,exceptions=0,source_pins_verified=15,export_members=len(manifest),tables={},arrays={},images={})
    total=0;maximum=0.;decisions=0
    for p in sorted(actual.glob('*.csv*')):
        assert (reference/p.name).is_file(),p.name
        a=pd.read_csv(p,float_precision='round_trip');b=pd.read_csv(reference/p.name,float_precision='round_trip')
        pd.testing.assert_frame_equal(a,b,check_exact=False,atol=1e-10,rtol=1e-9)
        delta=0.
        for col in a.columns:
            if pd.api.types.is_numeric_dtype(a[col]):
                x=a[col].to_numpy(float);y=b[col].to_numpy(float);valid=np.isfinite(x)&np.isfinite(y)
                if valid.any():delta=max(delta,float(abs(x[valid]-y[valid]).max()))
                if 'p_holm' in col:
                    assert np.array_equal(x<.05,y<.05);decisions+=len(x)
        report['tables'][p.name]=dict(rows=len(a),columns=len(a.columns),max_absolute_difference=delta,byte_identical=p.read_bytes()==(reference/p.name).read_bytes())
        total+=a.size;maximum=max(maximum,delta)
    with np.load(actual/'bootstrap_targets.npz') as a,np.load(reference/'bootstrap_targets.npz') as b:
        assert a.files==b.files
        for key in a.files:
            np.testing.assert_allclose(a[key],b[key],atol=1e-10,rtol=1e-9);delta=float(abs(a[key]-b[key]).max())
            report['arrays'][key]=dict(values=a[key].size,max_absolute_difference=delta);total+=a[key].size;maximum=max(maximum,delta)
    embedded=[]
    for c in codes:
        for o in c.get('outputs',[]):
            s=o.get('data',{}).get('image/png')
            if s:embedded.append(base64.b64decode(''.join(s) if isinstance(s,list) else s))
    assert len(embedded)==2
    for i,name in enumerate(['lab03f_agregado','lab03f_criticos']):
        raw=(actual/'figures'/(name+'.png')).read_bytes();assert embedded[i]==raw
        a=np.asarray(Image.open(io.BytesIO(raw)).convert('RGBA'));b=np.asarray(Image.open(ROOT/'paper/figures/lab02'/(name+'.png')).convert('RGBA'))
        with fitz.open(actual/'figures'/(name+'.pdf')) as da,fitz.open(ROOT/'paper/figures/lab02'/(name+'.pdf')) as db:
            pa=da[0].get_pixmap(matrix=fitz.Matrix(2,2));pb=db[0].get_pixmap(matrix=fitz.Matrix(2,2))
        report['images'][name]=dict(embedded_matches_export=True,PNG_pixels_identical_to_paper=bool(np.array_equal(a,b)),PDF_render_identical_to_paper_144dpi=pa.samples==pb.samples)
    report.update(total_values_compared=int(total),max_absolute_difference=maximum,adjusted_threshold_decisions_preserved=decisions,arrays_count=len(report['arrays']),atol=1e-10,rtol=1e-9,
                  scope='Saved-source/output consistency and numerical reproduction; no economic homologation or finite-sample coverage claim')
    (output/'comparison.json').write_text(json.dumps(report,indent=2)+'\n')
    (output/'export_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    return {k:v for k,v in report.items() if k!='arrays'}


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--notebook',type=Path,required=True);p.add_argument('--export',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    print(json.dumps(audit(a.notebook,a.export,a.output),indent=2))
