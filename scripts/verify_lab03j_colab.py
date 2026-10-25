#!/usr/bin/env python3
"""Author J notebook/export audit;never executes downloaded notebook/runtime code.
Reuses the dense independent continuity oracle with the previously declared
1e-10/1e-9 cross-environment tolerances on independently serialized references.
The original verifier remains frozen and requires exact within-run identity.
"""
import argparse,json
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.stats import rankdata
ROOT=Path(__file__).resolve().parents[1]
def audit_successions(i_output,turnover,output):
 r=pd.read_csv(output/'succession_returns_private.csv.gz',index_col=0,parse_dates=True,float_precision='round_trip');old=pd.read_csv(i_output/'gaps_preserved/returns_private.csv.gz',index_col=0,parse_dates=True,float_precision='round_trip');m=pd.read_csv(i_output/'market_private.csv.gz',index_col=0,parse_dates=True).iloc[:,0].reindex(r.index);plan=json.loads((ROOT/'data/lab03j/adendo_sucessoes_v1.json').read_text());changed=[x['old_ISIN'] for x in plan['pairs']];np.testing.assert_array_equal(r.drop(columns=changed).isna(),old.drop(columns=changed).isna());reference_roundoff=float(np.nanmax(abs(r.drop(columns=changed).to_numpy()-old.drop(columns=changed).to_numpy())));np.testing.assert_allclose(r.drop(columns=changed),old.drop(columns=changed),equal_nan=True,atol=1e-10,rtol=1e-9)
 transition=pd.read_csv(output/'succession_transitions.csv');assert len(transition)==3 and transition.adjacent_sessions.all() and transition.factor.eq(1).all()
 for t in transition.itertuples():
  pair=next(x for x in plan['pairs'] if x['old']==t.old);j=r.index.get_loc(pd.Timestamp(t.date));assert r.index[j-1]<pd.Timestamp(t.date);assert abs(r.iloc[j][pair['old_ISIN']]-t.transition_return)<1e-12
 gaps=pd.read_csv(i_output/'documented_gaps.csv')
 for t in gaps.itertuples():assert pd.isna(r.loc[t.date,t.papel_id])
 early=r.index.year<=2020;R=r.loc[early].to_numpy();M=m.loc[early].to_numpy();valid=np.isfinite(R);eligible=(valid.sum(0)>=200)&((valid&(M>0)[:,None]).sum(0)>=60)&((valid&(M<0)[:,None]).sum(0)>=60)&(valid.mean(0)>=.95);universe=pd.read_csv(ROOT/'data/lab03i/review_reference/universo_2015.csv').papel_id;vol=pd.read_csv(turnover);liq=vol[vol.date.astype(str).str[:4].eq('2015')].groupby('papel_id').volume.sum()/246;tab=pd.read_csv(output/'succession_sensitivity.csv');bank=np.load(output/'succession_draws.npz');errors=[];fits=0
 def contrasts(ii):
  nonlocal fits
  out=[]
  for j in range(R.shape[1]):
   y=R[ii,j];x=M[ii];sl=[]
   for sign in [1,-1]:
    ok=np.isfinite(y)&(sign*x>0);sl.append(np.linalg.lstsq(np.column_stack([np.ones(ok.sum()),x[ok]]),y[ok],rcond=None)[0][1]);fits+=1
   out.append(sl[0]-sl[1])
  return np.array(out)
 def stat(y,jj,target):
  if target=='early_mean':return y[jj].mean()
  return np.corrcoef(rankdata(np.log(liq.reindex(r.columns[jj]).to_numpy())),rankdata(y[jj]))[0,1]
 point=contrasts(np.arange(len(M)))
 for L in [21,5,63]:
  rng=np.random.default_rng(20261026+L);starts=rng.integers(0,len(M)-L+1,size=(4999,(len(M)+L-1)//L));indices=(starts[:3,:,None]+np.arange(L)).reshape(3,-1)[:,:len(M)];draws=[contrasts(ii) for ii in indices]
  g=tab[tab.block.eq(L)];order=np.argsort(g.p.to_numpy());adjusted=np.empty(4);adjusted[order]=np.minimum(1,np.maximum.accumulate(g.p.to_numpy()[order]*np.arange(4,0,-1)));np.testing.assert_allclose(adjusted,g.p_holm4,atol=1e-12)
  for row in g.itertuples():
   jj=np.flatnonzero(eligible&(r.columns.isin(universe) if row.cohort=='universe2015' else True));assert len(jj)==row.N;errors.append(abs(stat(point,jj,row.target)-row.estimate));b=bank[f'{row.cohort}_{row.target}_{L}'];errors.extend(abs(stat(y,jj,row.target)-b[k]) for k,y in enumerate(draws));q=np.quantile(b-row.estimate,[.025,.975]);np.testing.assert_allclose([row.estimate-q[1],row.estimate-q[0],(1+sum(abs(b-row.estimate)>=abs(row.estimate)))/5000],[row.ci_low,row.ci_high,row.p],atol=1e-10)
 assert max(errors)<1e-10;report=dict(passed=True,production_imported=False,dense_regime_fits=fits,max_difference=max(errors),documented_transitions=3,gaps_protected=7,primary_other_ISINs_unchanged=True,reference_roundoff=reference_roundoff,reference_atol=1e-10,reference_rtol=1e-9,scope='Cross-export numerical audit;bit identity is not assumed between independently serialized I references. Missing masks exact;not economic certification');(output/'succession_cross_export_verification.json').write_text(json.dumps(report,indent=2)+'\n');print(report);return report

import hashlib,zipfile,ast,base64,io,subprocess,sys
from PIL import Image

def main():
 p=argparse.ArgumentParser();p.add_argument('--notebook',type=Path,required=True);p.add_argument('--archive',type=Path,required=True);p.add_argument('--i-output',type=Path,required=True);p.add_argument('--local-output',type=Path,required=True);p.add_argument('--work-dir',type=Path,required=True);opts=p.parse_args()
 R=ROOT;D=opts.work_dir;D.mkdir(parents=True,exist_ok=False);Z=opts.archive;i_output=opts.i_output;nb=json.loads(opts.notebook.read_text());delivered=json.loads((R/'notebooks/Lab03J_liquidez_controles.ipynb').read_text());assert len(nb['cells'])==9 and all(c['source']==d['source'] for c,d in zip(nb['cells'],delivered['cells']));code=[c for c in nb['cells'] if c['cell_type']=='code'];assert [c['execution_count'] for c in code]==[1,2,3,4,5];assert not any(o.get('output_type')=='error' for c in code for o in c.get('outputs',[]))
 tree=ast.parse(''.join(delivered['cells'][3]['source']));pins=next(ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='SOURCE_PINS' for t in n.targets))
 with zipfile.ZipFile(Z) as z:
  assert z.testzip() is None;manifest=json.loads(z.read('manifesto_exports.json'));assert set(manifest)==set(z.namelist())-{'manifesto_exports.json'}
  for name,expected in manifest.items():assert hashlib.sha256(z.read(name)).hexdigest()==expected,name
  for name,expected in pins.items():assert hashlib.sha256(z.read('runtime/'+name)).hexdigest()==expected,name
  target=D/'extracted';target.mkdir(exist_ok=True)
  for name in z.namelist():
   if name=='manifesto_exports.json':continue
   p=target/name;assert p.resolve().is_relative_to(target.resolve());p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(z.read(name))
 output=target/'batch_J/outputs_J';reference=R/'results/tables/lab03j_pareceres_20261024';compared=0;thresholds=0;maxdiff=0.
 for p in sorted(reference.glob('*.csv')):
  a=pd.read_csv(output/p.name,float_precision='round_trip');e=pd.read_csv(p,float_precision='round_trip');pd.testing.assert_frame_equal(a,e,check_exact=False,atol=1e-10,rtol=1e-9);compared+=a.size
  for col in a.select_dtypes(include='number'):
   aa=a[col].to_numpy();ee=e[col].to_numpy();valid=np.isfinite(aa)&np.isfinite(ee)
   if valid.any():maxdiff=max(maxdiff,float(np.max(abs(aa[valid]-ee[valid]))))
   if col=='p' or col.startswith('p_'):np.testing.assert_array_equal(a[col].le(.05),e[col].le(.05));thresholds+=len(a)
 local=opts.local_output;banks=0;vectors=0
 for name in ['bootstrap_draws.npz','succession_draws.npz']:
  with np.load(output/name) as a,np.load(local/name) as e:
   assert a.files==e.files
   for key in a.files:
    np.testing.assert_allclose(a[key],e[key],atol=1e-10,rtol=1e-9);banks+=a[key].size;vectors+=1;maxdiff=max(maxdiff,float(np.max(abs(a[key]-e[key]))))
 figures=[]
 for name in ['lab03j_assimetria_anual','lab03j_liquidez_inicial']:
  file=target/'batch_J/paper/figures/lab02'/(name+'.png');original=R/'paper/figures/lab02'/(name+'.png');a=Image.open(file).convert('RGBA');e=Image.open(original).convert('RGBA');equal=a.size==e.size and np.array_equal(np.asarray(a),np.asarray(e));figures.append(dict(name=name,size=a.size,pixels_equal_local=equal))
  embedded=[o['data']['image/png'] for c in code for o in c.get('outputs',[]) if 'image/png' in o.get('data',{})];assert len(embedded)==2
 for v,info in zip(embedded,figures):
  im=Image.open(io.BytesIO(base64.b64decode(''.join(v)))).convert('RGBA');exp=Image.open(target/'batch_J/paper/figures/lab02'/(info['name']+'.png')).convert('RGBA');assert im.size==exp.size and np.array_equal(np.asarray(im),np.asarray(exp))
 subprocess.run([sys.executable,str(R/'scripts/verify_lab03j.py'),'--i-output',str(i_output),'--turnover',str(target/'batch_J/private_inputs/turnover_private.csv.gz'),'--output',str(output)],check=True)
 linked=audit_successions(i_output,target/'batch_J/private_inputs/turnover_private.csv.gz',output)
 record=dict(passed=True,author_notebook_id='1alqzGsbG4-cwQlTyeF2JSoZRQIZQEfsR',author_export_id='17DxLLmCd-UD0NXlFXDQNANbk1fxmqZ2q',source_cells_equal=9,code_cells=5,execution_counts=[1,2,3,4,5],exceptions=0,notebook_sha256=hashlib.sha256(opts.notebook.read_bytes()).hexdigest(),export_sha256=hashlib.sha256(Z.read_bytes()).hexdigest(),export_bytes=Z.stat().st_size,members=len(manifest)+1,manifest_checked_members=len(manifest),source_pins_checked=len(pins),table_values_compared=compared,bootstrap_values_compared=banks,bootstrap_vectors_compared=vectors,p_threshold_positions=thresholds,max_absolute_difference=maxdiff,atol=1e-10,rtol=1e-9,figures=figures,independent_oracles_rerun=True,cross_export_reference_roundoff=linked["reference_roundoff"],comparison=json.loads((output/'notebook_comparison.json').read_text()),scope='Author Colab execution and external computational audit;does not certify economic returns,exact share inventory,causality or new test coverage')
 (D/'audit.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record,indent=2))

if __name__=='__main__':main()
