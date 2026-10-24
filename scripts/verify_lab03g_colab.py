#!/usr/bin/env python3
"""Audit saved G sources/exports against the frozen local reference.

Does not execute notebook cells or imported export code. The separate
trusted G oracle can subsequently be run on a copy of authenticated outputs.
"""
import argparse,ast,base64,hashlib,io,json,re,zipfile
from pathlib import Path
import numpy as np
import pandas as pd
from PIL import Image
import fitz

ROOT=Path(__file__).resolve().parents[1]


def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def audit(notebook,export,output,reference_figures=None):
    expected=json.loads((ROOT/'notebooks/Lab03G_mudanca_calibracao.ipynb').read_text());nb=json.loads(notebook.read_text())
    assert len(nb['cells'])==len(expected['cells'])==10
    assert all(c['cell_type']==e['cell_type'] and ''.join(c['source'])==''.join(e['source']) for c,e in zip(nb['cells'],expected['cells']))
    codes=[c for c in nb['cells'] if c['cell_type']=='code'];assert [c.get('execution_count') for c in codes]==list(range(1,7))
    assert not any(o.get('output_type')=='error' for c in codes for o in c.get('outputs',[]))
    stream=''.join(''.join(o.get('text',[])) if isinstance(o.get('text',[]),list) else o.get('text','') for c in codes for o in c.get('outputs',[]))
    match=re.search(r'Export: (\S+) \| bytes: (\d+) \| SHA256: ([0-9a-f]{64})',stream)
    assert match and export.name==match[1] and export.stat().st_size==int(match[2]) and sha(export)==match[3]
    constants={}
    for node in ast.parse(''.join(nb['cells'][3]['source'])).body:
        if isinstance(node,ast.Assign):
            for t in node.targets:
                if isinstance(t,ast.Name) and t.id in ['SOURCE_PINS','SOURCE_COMMIT']:constants[t.id]=ast.literal_eval(node.value)
    pins=constants['SOURCE_PINS'];assert len(pins)==70 and constants['SOURCE_COMMIT']=='880de4fa25a6ced45b137bd9d5f5126abf869f25'
    output.mkdir(parents=True,exist_ok=False)
    with zipfile.ZipFile(export) as z:
        manifest=json.loads(z.read('manifesto_exports.json'));assert len(z.namelist())==len(set(z.namelist()))
        assert set(z.namelist())==set(manifest)|{'manifesto_exports.json'} and len(manifest)==88
        for n,h in manifest.items():
            assert not Path(n).is_absolute() and '..' not in Path(n).parts
            raw=z.read(n);assert hashlib.sha256(raw).hexdigest()==h,n
            p=output/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw)
        for n,h in pins.items():
            assert manifest['runtime/'+n]==h,n
            assert sha(ROOT/n)==h,n
    actual=output/'outputs';reference=ROOT/'results/tables/lab03g_pos_parecer_v3_20261024'
    execution=json.loads((actual/'execution_all.json').read_text());comparison=json.loads((actual/'notebook_comparison.json').read_text())
    assert execution['stage']=='Lab03G all' and execution['environment']=='Colab' and execution['inputs_unchanged'] and execution['no_market_downloads']
    assert comparison['environment']=='Colab' and comparison['passed'] and comparison['compared_values']==1594818
    assert execution['plan_sha256']==pins['data/lab03g/plano_v1.json']
    report=dict(passed=True,notebook_sha256=sha(notebook),notebook_bytes=notebook.stat().st_size,export_sha256=sha(export),export_bytes=export.stat().st_size,
        source_cells_identical=10,sequential_code_cells=6,exceptions=0,source_pins_verified=70,export_members=88,source_commit=constants['SOURCE_COMMIT'],
        full_Colab_execution=execution,notebook_internal_comparison=comparison,tables={},arrays={},images={},tables_LaTeX={})
    total=0;maximum=0.;adjusted_decisions=0;raw_decisions=0
    for p in sorted(actual.glob('*.csv*')):
        assert (reference/p.name).is_file(),p.name
        a=pd.read_csv(p,float_precision='round_trip');b=pd.read_csv(reference/p.name,float_precision='round_trip')
        pd.testing.assert_frame_equal(a,b,check_exact=False,atol=1e-10,rtol=1e-9)
        delta=0.
        for col in a.columns:
            if pd.api.types.is_numeric_dtype(a[col]):
                x=a[col].to_numpy(float);y=b[col].to_numpy(float);valid=np.isfinite(x)&np.isfinite(y)
                if valid.any():delta=max(delta,float(abs(x[valid]-y[valid]).max()))
                if col in ['p_adjusted','p_centered']:
                    assert np.array_equal(x<.05,y<.05)
                    if col=='p_adjusted':adjusted_decisions+=len(x)
                    else:raw_decisions+=len(x)
        report['tables'][p.name]=dict(rows=len(a),columns=len(a.columns),max_absolute_difference=delta,byte_identical=p.read_bytes()==(reference/p.name).read_bytes());total+=a.size;maximum=max(maximum,delta)
    assert len(report['tables'])==6
    with np.load(actual/'observed_draws.npz') as a,np.load(reference/'observed_draws.npz') as b:
        assert a.files==b.files and len(a.files)==66
        for key in a.files:
            np.testing.assert_allclose(a[key],b[key],atol=1e-10,rtol=1e-9);delta=float(abs(a[key]-b[key]).max())
            report['arrays'][key]=dict(values=a[key].size,max_absolute_difference=delta);total+=a[key].size;maximum=max(maximum,delta)
    for name in ['temporal.tex','microstructure.tex','calibration.tex']:
        assert (actual/name).read_bytes()==(reference/name).read_bytes();report['tables_LaTeX'][name]='byte_identical'
    embedded=[]
    for c in codes:
        for o in c.get('outputs',[]):
            s=o.get('data',{}).get('image/png')
            if s:embedded.append(base64.b64decode(''.join(s) if isinstance(s,list) else s))
    assert len(embedded)==2
    for i,name in enumerate(['lab03g_temporal','lab03g_calibracao']):
        raw=(actual/'figures'/(name+'.png')).read_bytes();assert embedded[i]==raw
        with fitz.open(actual/'figures'/(name+'.pdf')) as da,fitz.open(ROOT/'paper/figures/lab02'/(name+'.pdf')) as db:
            pa=da[0].get_pixmap(matrix=fitz.Matrix(2,2),alpha=False);pb=db[0].get_pixmap(matrix=fitz.Matrix(2,2),alpha=False)
        q=dict(embedded_matches_export=True,PDF_render_identical_to_paper_144dpi=(pa.width,pa.height,pa.samples)==(pb.width,pb.height,pb.samples),PDF_byte_identical=(actual/'figures'/(name+'.pdf')).read_bytes()==(ROOT/'paper/figures/lab02'/(name+'.pdf')).read_bytes())
        if reference_figures:
            a=np.asarray(Image.open(io.BytesIO(raw)).convert('RGBA'));b=np.asarray(Image.open(reference_figures/(name+'.png')).convert('RGBA'));q['PNG_pixels_identical_to_local']=bool(np.array_equal(a,b))
        report['images'][name]=q
    report.update(total_values_compared=int(total),max_absolute_difference=maximum,adjusted_threshold_positions_preserved=adjusted_decisions,raw_threshold_positions_preserved=raw_decisions,
        arrays_count=len(report['arrays']),bootstrap_array_byte_identical=(actual/'observed_draws.npz').read_bytes()==(reference/'observed_draws.npz').read_bytes(),atol=1e-10,rtol=1e-9,
        scope='Saved-source/export consistency and numerical reproduction; no general size/coverage theorem, economic homologation, or KRR validation')
    (output/'comparison.json').write_text(json.dumps(report,indent=2)+'\n');(output/'export_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    return {k:v for k,v in report.items() if k!='arrays'}


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--notebook',required=True,type=Path);p.add_argument('--export',required=True,type=Path);p.add_argument('--output',required=True,type=Path);p.add_argument('--reference-figures',type=Path);a=p.parse_args()
    print(json.dumps(audit(a.notebook,a.export,a.output,a.reference_figures),indent=2))
