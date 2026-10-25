#!/usr/bin/env python3
"""External verification of saved K notebook/export; no production imports.

The caller supplies an immutable delivered notebook, runtime manifest and
separately reconstructed observed bank. No quotation downloads or simulations.
"""
import argparse,base64,hashlib,json,zipfile
from pathlib import Path
import numpy as np
import pandas as pd
from PIL import Image

def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def verify(notebook,delivered,export,frozen_manifest,rebuilt,rebuilt_paper,output):
    output.mkdir(parents=True,exist_ok=False)
    nb=json.loads(notebook.read_text());expected=json.loads(delivered.read_text())
    assert len(nb['cells'])==len(expected['cells'])==9
    sources=[];counts=[];errors=[];streams=[];embedded=[]
    for i,(actual,reference) in enumerate(zip(nb['cells'],expected['cells'])):
        assert actual['cell_type']==reference['cell_type']
        a=''.join(actual['source']);r=''.join(reference['source']);assert a==r,('modified cell source',i)
        sources.append(dict(cell=i,kind=actual['cell_type'],sha256=hashlib.sha256(a.encode()).hexdigest()))
        if actual['cell_type']=='code':
            counts.append(actual.get('execution_count'))
            for item in actual.get('outputs',[]):
                if item.get('output_type')=='error':errors.append(item)
                if item.get('output_type')=='stream':streams.append(''.join(item.get('text',[])))
                data=item.get('data',{})
                if 'image/png' in data:embedded.append(base64.b64decode(''.join(data['image/png'])))
    assert counts==[1,2,3,4,5] and not errors
    text='\n'.join(streams);assert 'environment": "author_Colab"' in text
    extracted=output/'extracted'
    with zipfile.ZipFile(export) as z:
        assert z.testzip() is None
        inventory=json.loads(z.read('manifesto_exports.json'))
        assert set(inventory)==set(z.namelist())-{'manifesto_exports.json'}
        for name,sha in inventory.items():
            assert not name.startswith('/') and '..' not in Path(name).parts
            assert hashlib.sha256(z.read(name)).hexdigest()==sha,name
        z.extractall(extracted)
    pins=json.loads(frozen_manifest.read_text())['source_pins'];pins=dict(pins)
    pins['data/lab03k/inputs_manifest.json']=digest(frozen_manifest)
    for name,sha in pins.items():assert digest(extracted/'runtime'/name)==sha,name
    assert digest(export) in text,'notebook/export digest linkage missing'
    source=extracted/'outputs_K';reference=extracted/'runtime/results/tables/lab03k_20261025'
    comparison=json.loads((source/'notebook_comparison.json').read_text())
    assert comparison['passed'] and comparison['environment']=='author_Colab'
    assert comparison['source_commit']=='276ebc08414f01b2363a5c4e554fb79b2a6a2dca'
    assert comparison['I_sha256']=='ff67a56f9b9cc8b91f11bcbcad311d6253fcfe95aef3f9e02303bad677b41e0e'
    assert comparison['J_sha256']=='96b56d0a9e3d8ace52f1f4a6b0307c769547e2bfe355a6f6318e6656ab5f8dce'
    rows=[];cells=0;thresholds=0;numeric=0;maxdiff=0.
    for f in sorted(reference.glob('*.csv*')):
        a=pd.read_csv(source/f.name,float_precision='round_trip');r=pd.read_csv(f,float_precision='round_trip')
        pd.testing.assert_frame_equal(a,r,check_exact=False,atol=1e-10,rtol=1e-9)
        error=0.
        for col in a.select_dtypes(include='number'):
            av=a[col].to_numpy();rv=r[col].to_numpy();assert np.array_equal(np.isnan(av),np.isnan(rv));valid=np.isfinite(av)&np.isfinite(rv)
            numeric+=int(valid.sum());delta=float(np.max(abs(av[valid]-rv[valid]),initial=0));error=max(error,delta)
            if col=='p' or col.startswith('p_'):
                np.testing.assert_array_equal(a[col].le(.05),r[col].le(.05));thresholds+=len(a)
        rows.append(dict(file=f.name,rows=len(a),columns=len(a.columns),cells=a.size,max_absolute_difference=error));cells+=a.size;maxdiff=max(maxdiff,error)
    assert cells==comparison['compared_values']==72724
    assert thresholds==comparison['p_threshold_positions']==12381
    pd.DataFrame(rows).to_csv(output/'table_comparisons.csv',index=False)
    bank=np.load(source/'draws_private.npz');other=np.load(rebuilt/'draws_private.npz');assert set(bank.files)==set(other.files)
    bank_values=0;bankdiff=0.;bank_rows=[]
    for name in bank.files:
        a=bank[name];r=other[name];assert a.shape==r.shape;np.testing.assert_allclose(a,r,atol=1e-10,rtol=1e-9,equal_nan=True)
        difference=float(np.nanmax(abs(a-r)));bank_values+=a.size;bankdiff=max(bankdiff,difference);bank_rows.append(dict(key=name,rows=a.shape[0],columns=a.shape[1],values=a.size,max_absolute_difference=difference))
    pd.DataFrame(bank_rows).to_csv(output/'bank_comparisons.csv',index=False)
    actual=pd.read_csv(source/'preperiod_returns_private.csv.gz',index_col=0);ref=pd.read_csv(rebuilt/'preperiod_returns_private.csv.gz',index_col=0)
    np.testing.assert_array_equal(actual.isna(),ref.isna());pd.testing.assert_frame_equal(actual,ref,check_exact=False,atol=1e-10,rtol=1e-9)
    original_png=extracted/'paper/figures/lab02/lab03k_controls.png'
    assert len(embedded)==1 and hashlib.sha256(embedded[0]).hexdigest()==digest(original_png)
    aa=np.asarray(Image.open(original_png));rr=np.asarray(Image.open(rebuilt_paper/'figures/lab02/lab03k_controls.png'))
    image_check=dict(same_shape=aa.shape==rr.shape,pixels_equal=aa.shape==rr.shape and np.array_equal(aa,rr))
    for file in (extracted/'paper/tables').glob('*.tex'):
        assert file.read_bytes()==(rebuilt_paper/'tables'/file.name).read_bytes(),file.name
    receipt=dict(passed=True,notebook_sha256=digest(notebook),export_sha256=digest(export),export_bytes=export.stat().st_size,
        source_commit=comparison['source_commit'],cell_sources=sources,code_cells=5,execution_counts=counts,errors=0,
        authenticated_export_members=len(inventory),source_files=len(pins),table_cells=cells,finite_numeric_table_values=numeric,
        threshold_positions=thresholds,max_table_difference=maxdiff,observed_bank_arrays=len(bank.files),observed_bank_values=bank_values,
        max_bank_difference=bankdiff,preperiod_missing_mask_identical=True,embedded_plot_matches_export=True,plot_reconstruction=image_check,
        calibration_rows=6000,calibration_not_rerun=True,atol=1e-10,rtol=1e-9,
        scope='external numerical reproduction; no economic or universal inferential certification')
    (output/'audit.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt,indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser()
    for name in ['notebook','delivered','export','frozen_manifest','rebuilt','rebuilt_paper','output']:p.add_argument('--'+name.replace('_','-'),type=Path,required=True)
    a=p.parse_args();verify(**vars(a))
