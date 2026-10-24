#!/usr/bin/env python3
"""Independent rank-bank, full-design and model-envelope verification."""
import argparse,hashlib,json,sys,time,zipfile
from pathlib import Path
import numpy as np,pandas as pd
from scipy.stats import norm
from threadpoolctl import threadpool_limits
ROOT=Path(__file__).resolve().parents[1]

def validate(output,x_archive):
 started=time.monotonic();plan=json.loads((ROOT/'data/lab03d/plano_v1.json').read_text());ad=json.loads((ROOT/'data/lab03d/adendo_classes_equivalencia_v1.json').read_text());lock=json.loads((ROOT/'data/lab03d/inputs_manifest.json').read_text());assert hashlib.sha256(x_archive.read_bytes()).hexdigest()==lock['x_sha256']
 z=zipfile.ZipFile(x_archive);mats={s:pd.read_csv(z.open(f'matrices/referencia_n/{s}/retornos_logaritmicos.csv.gz'),compression='gzip',index_col=0,parse_dates=True,float_precision='round_trip') for s in ['decada','recente']};z.close();master=mats['decada'];market=master['^BVSP'].to_numpy();N=len(market)
 d=pd.read_csv(output/'design.csv');annual=pd.read_csv(output/'annual_design.csv');nu=pd.read_csv(output/'asset_nuisance.csv');catalog=pd.read_csv(output/'bank_designs.csv');saved=np.load(output/'envelope_replicates.npz');a={k:saved[k] for k in saved.files};bank=a['calibration_t'];G=len(catalog)
 assert bank.shape==(3,9999,G)
 for kind,size in [('static',197),('annual',985),('theta',80)]:assert a[kind+'_error'].shape==(3,1000,size) and a[kind+'_se'].shape==(3,1000,size)
 signatures={};description={};annual_index={(r.papel_id,r.year):j for j,r in enumerate(annual.itertuples())}
 for kind,rows in [('static',d),('annual',annual),('theta',d.iloc[:80])]:
  for j,row in enumerate(rows.itertuples()):
   s=row.scenario if kind=='static' else ('decada' if kind=='theta' or row.year<2021 else 'recente');mat=mats[s]
   if kind=='annual':mat=mat[mat.index.year==row.year]
   m=mat['^BVSP'].to_numpy();valid=np.isfinite(mat[row.ticker].to_numpy())&(m!=0);signature=(kind,mat.index.to_numpy().tobytes(),valid.tobytes());g=int(a[kind+'_map'][j])
   if g in signatures:assert signatures[g]==signature
   else:signatures[g]=signature;description[g]=(kind,j,s,mat,valid)
 assert len(signatures)==G and len(set(signatures.values()))==G
 # Full-design HC3-HAC5 oracle, no production imports.
 fits=0;maximum=0.
 def oracle(y,m,valid,kind,dates):
  nonlocal fits
  D=(m>0).astype(float);X=np.column_stack([np.ones(len(m)),D,m,D*m]);j=3
  if kind=='theta':Q=(dates.year>=2021).astype(float);X=np.column_stack([X,X*Q[:,None]]);j=7
  xx=X[valid];beta=np.linalg.lstsq(xx,y[valid],rcond=None)[0];bread=np.linalg.inv(xx.T@xx);h=np.einsum('ij,jk,ik->i',xx,bread,xx);res=(y[valid]-xx@beta)/(1-h);score=np.zeros_like(X);score[valid]=xx*res[:,None];meat=score.T@score
  for lag in range(1,6):cross=score[lag:].T@score[:-lag];meat+=(1-lag/6)*(cross+cross.T)
  se=np.sqrt((bread@meat@bread)[j,j]*valid.sum()/(valid.sum()-X.shape[1]));fits+=1;return beta[j],se
 def generated(mi,entropy,columns):
  rng=np.random.default_rng(np.random.SeedSequence([entropy,mi,0]));shape=(N+256,columns);zz=rng.standard_normal(shape) if mi==0 else rng.standard_t(5,shape)*np.sqrt(.6);phi=0 if mi<2 else .3
  if columns==2:v=np.sqrt(.3)*zz[:,0]+np.sqrt(.7)*zz[:,1];previous=0.;u=np.empty(len(v))
  else:v=np.sqrt(.3)*zz[:,:1]+np.sqrt(.7)*zz[:,1:];previous=np.zeros(117);u=np.empty_like(v)
  for t in range(len(v)):u[t]=phi*previous+np.sqrt(1-phi*phi)*v[t];previous=u[t]
  h=np.sqrt(.5+.5*np.r_[market[0],market[:-1]]**2/np.mean(market**2));h/=np.sqrt(np.mean(h*h));u=u[256:]
  return u if mi==0 else u*(h if columns==2 else h[:,None])
 with threadpool_limits(limits=1):
  for mi in range(3):
   u=generated(mi,ad['calibration_seed_entropy'],2)
   for g,(kind,j,s,mat,valid) in description.items():
    ti=master.index.get_indexer(mat.index);b,se=oracle(u[ti],mat['^BVSP'].to_numpy(),valid,kind,mat.index);np.testing.assert_allclose(b/se,bank[mi,0,g],rtol=1e-9,atol=1e-11);maximum=max(maximum,abs(b/se-bank[mi,0,g]))
   noise=generated(mi,ad['validation_seed_entropy'],118)*nu.sigma.to_numpy()
   for kind,rows in [('static',d),('annual',annual),('theta',d.iloc[:80])]:
    for j,row in enumerate(rows.itertuples()):
     s=row.scenario if kind=='static' else ('decada' if kind=='theta' or row.year<2021 else 'recente');mat=mats[s]
     if kind=='annual':mat=mat[mat.index.year==row.year]
     m=mat['^BVSP'].to_numpy();valid=mat[row.ticker].notna().to_numpy()&(m!=0);ti=master.index.get_indexer(mat.index);ni=int(nu.index[nu.papel_id.eq(row.papel_id)][0]);b,se=oracle(noise[ti,ni],m,valid,kind,mat.index)
     np.testing.assert_allclose([b,se],[a[kind+'_error'][mi,0,j],a[kind+'_se'][mi,0,j]],rtol=1e-9,atol=1e-11)
 print('Independent rank bank/validation full-design fits:',fits,flush=True)
 signed=np.sort(bank,axis=1);ab=np.sort(np.abs(bank),axis=1);comparisons=0
 def pvalue(t,mapping,tail):
  t=np.atleast_2d(t);result=np.zeros_like(t)
  for j,g in enumerate(mapping):
   for mechanism in range(3):
    if tail=='two':counts=9999-np.searchsorted(ab[mechanism,:,g],np.abs(t[:,j]),side='left')
    elif tail=='positive':counts=9999-np.searchsorted(signed[mechanism,:,g],t[:,j],side='left')
    else:counts=np.searchsorted(signed[mechanism,:,g],t[:,j],side='right')
    result[:,j]=np.maximum(result[:,j],(counts+1)/10000)
  return result
 # Explicit counts additionally verify all three tail conventions and tie handling.
 for tail in ['two','positive','negative']:
  values=np.linspace(-3,3,197)[None,:];got=pvalue(values,a['static_map'],tail)
  for j,g in enumerate(a['static_map']):
   probabilities=[]
   for m in range(3):
    ev=np.abs(bank[m,:,g])>=abs(values[0,j]) if tail=='two' else (bank[m,:,g]>=values[0,j] if tail=='positive' else bank[m,:,g]<=values[0,j]);probabilities.append((1+ev.sum())/10000)
   assert got[0,j]==max(probabilities)
 def holm(p):
  order=np.argsort(p,axis=-1,kind='stable');values=np.take_along_axis(p,order,axis=-1);v=np.minimum(1,np.maximum.accumulate(values*np.arange(p.shape[-1],0,-1),axis=-1));out=np.empty_like(p);np.put_along_axis(out,order,v,axis=-1);return out
 Z=norm.ppf(.975)
 def rates(ev):
  pp=ev.mean(0);se=np.sqrt(pp*(1-pp)/1000);den=1+Z*Z/1000;c=(pp+Z*Z/2000)/den;r=Z*np.sqrt(pp*(1-pp)/1000+Z*Z/4000000)/den;return pp,se,np.maximum(0,c-r),np.minimum(1,c+r)
 def same(x,y):
  nonlocal comparisons
  np.testing.assert_allclose(x,y,atol=1e-11,rtol=1e-9,equal_nan=True);comparisons+=np.size(y)
 def family(row,raw,rej,null):
  assert row.null_cases==null.sum() and row.nonnull_cases==(~null).sum()
  for name,ev in [('fwer_raw',raw),('fwer_adjusted',rej)]:same(row[[name,name+'_mcse',name+'_mc_low',name+'_mc_high']].to_numpy(float),rates(ev[:,null].any(1)) if null.any() else [np.nan]*4)
  for name,ev in [('power_raw',raw),('power_adjusted',rej)]:
   v=ev[:,~null].mean(1) if (~null).any() else None;same(row[[name,name+'_mcse']].to_numpy(float),[v.mean(),v.std(ddof=1)/np.sqrt(1000)] if v is not None else [np.nan]*2)
 sf=pd.read_csv(output/'envelope_family.csv');sr=pd.read_csv(output/'envelope_rejection.csv');sc=pd.read_csv(output/'envelope_calibration.csv');sp=pd.read_csv(output/'envelope_panels.csv');tf=pd.read_csv(output/'envelope_temporal_family.csv');th=pd.read_csv(output/'envelope_temporal_hypotheses.csv');tc=pd.read_csv(output/'envelope_temporal_calibration.csv')
 assert [len(q) for q in [sf,sr,sc,sp,tf,th,tc]]==[27,5319,591,54,15,7110,3195]
 selected=set(nu.papel_id[:12]);patterns=[(f'dense_{v:+.2f}',np.full(197,v)) for v in [-.5,-.25,-.1,0,.1,.25,.5]]+[(f'sparse_{v:+.2f}',np.where(d.papel_id.isin(selected),v,0)) for v in [-.25,.25]]
 amap=[[annual_index[(r.papel_id,y)] for y in range(2016 if r.scenario=='decada' else 2021,2026)] for r in d.itertuples()]
 critical=np.max(ab[:,9500,:],axis=0);bonf=np.max(ab[:,9997,:],axis=0)
 for mi,spec in enumerate(plan['mechanisms']):
  name=spec['name'];E=a['static_error'][mi];S=a['static_se'][mi];cover=np.abs(E)<=critical[a['static_map']]*S;q=sc[sc.mechanism.eq(name)]
  for key,value in zip(['coverage','coverage_mcse','coverage_mc_low','coverage_mc_high'],rates(cover)):same(q[key],value)
  for pat,truth in patterns:
   pp=pvalue((E+truth)/S,a['static_map'],'two');rej=holm(pp)<.05;null=truth==0;row=sf[sf.mechanism.eq(name)&sf.pattern.eq(pat)].iloc[0];family(row,pp<.05,rej,null);q=sr[sr.mechanism.eq(name)&sr.pattern.eq(pat)]
   for key,value in zip(['adjusted_rejection','adjusted_mcse','adjusted_mc_low','adjusted_mc_high'],rates(rej)):same(q[key],value)
  AE=a['annual_error'][mi];AS=a['annual_se'][mi];TE=a['theta_error'][mi];TS=a['theta_se'][mi]
  for kind,err,se in [('annual',AE,AS),('theta',TE,TS)]:
   cover=np.abs(err)<=critical[a[kind+'_map']]*se;q=tc[tc.mechanism.eq(name)&tc.kind.eq(kind)]
   for key,value in zip(['coverage','coverage_mcse','coverage_mc_low','coverage_mc_high'],rates(cover)):same(q[key],value)
  for pat in plan['temporal']['patterns']:
   truth=np.zeros(985)
   if pat=='constant_positive_.25':truth[:]=.25
   elif pat=='constant_negative_.25':truth[:]=-.25
   elif pat=='early_negative_late_positive_.25':truth=np.where(annual.year<=2020,-.25,.25)
   elif pat=='sparse_positive_.25':truth=np.where(annual.papel_id.isin(selected),.25,0)
   tt=np.full(80,.5 if pat=='early_negative_late_positive_.25' else 0.);positive=np.array([np.all(truth[ix]>0) for ix in amap]);negative=np.array([np.all(truth[ix]<0) for ix in amap]);null=np.r_[tt==0,~positive,~negative]
   py=pvalue((AE+truth)/AS,a['annual_map'],'positive');ny=pvalue((AE+truth)/AS,a['annual_map'],'negative');tp=pvalue((TE+tt)/TS,a['theta_map'],'two');pp=np.column_stack([tp,np.column_stack([py[:,ix].max(1) for ix in amap]),np.column_stack([ny[:,ix].max(1) for ix in amap])]);rej=holm(pp)<.05;q=tf[tf.mechanism.eq(name)&tf.pattern.eq(pat)].iloc[0];family(q,pp<.05,rej,null);q=th[th.mechanism.eq(name)&th.pattern.eq(pat)];np.testing.assert_array_equal(q.is_true_null,null)
   for key,value in zip(['adjusted_rejection','adjusted_mcse','adjusted_mc_low','adjusted_mc_high'],rates(rej)):same(q[key],value)
 # Actual rank p-values/interval inversion using independently validated observed scores.
 obs=pd.read_csv(output/'observed_static.csv');obs=obs[obs.method.eq('HC3_HAC5_Holm')].reset_index(drop=True);new=pd.read_csv(output/'observed_envelope.csv');p=pvalue((obs.delta/obs.se_delta).to_numpy()[None,:],a['static_map'],'two')[0]
 same(new.delta,obs.delta);same(new.se_delta,obs.se_delta);same(new.p_envelope,p);same(new.p_envelope_holm_197,holm(p[None,:])[0])
 same(new.ci_marginal_low,obs.delta-critical[a['static_map']]*obs.se_delta);same(new.ci_marginal_high,obs.delta+critical[a['static_map']]*obs.se_delta);same(new.ci_bonferroni_low,obs.delta-bonf[a['static_map']]*obs.se_delta);same(new.ci_bonferroni_high,obs.delta+bonf[a['static_map']]*obs.se_delta)
 # Annual/theta estimates are checked against full-design data oracle here as well.
 annual_observed=[];theta_observed=[]
 with threadpool_limits(limits=1):
  for kind,rows,target in [('annual',annual,annual_observed),('theta',d.iloc[:80],theta_observed)]:
   for row in rows.itertuples():
    s='decada' if kind=='theta' or row.year<2021 else 'recente';mat=mats[s]
    if kind=='annual':mat=mat[mat.index.year==row.year]
    m=mat['^BVSP'].to_numpy();ok=mat[row.ticker].notna().to_numpy()&(m!=0);target.append(oracle(mat[row.ticker].to_numpy(),m,ok,kind,mat.index))
 av=np.array(annual_observed);tv=np.array(theta_observed);py=pvalue((av[:,0]/av[:,1])[None,:],a['annual_map'],'positive');ny=pvalue((av[:,0]/av[:,1])[None,:],a['annual_map'],'negative');tp=pvalue((tv[:,0]/tv[:,1])[None,:],a['theta_map'],'two');p=np.r_[tp[0],[py[:,ix].max() for ix in amap],[ny[:,ix].max() for ix in amap]];new=pd.read_csv(output/'observed_envelope_temporal.csv');same(new.p_envelope,p);same(new.p_envelope_holm_474,holm(p[None,:])[0])
 receipt=dict(status='passed',independent_of_production_rank_imports=True,bank_unique_designs=G,all_case_mapping_signatures_verified=197+985+80,full_design_oracle_fits=fits,max_first_calibration_statistic_difference=maximum,summary_numeric_values_recalculated=int(comparisons),bank_and_validation_streams_independent=True,finite_model_class_scope_only=True,global_homologated=0,runtime_seconds=time.monotonic()-started)
 (output/'validacao_envelope_independente.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt,indent=2));return receipt
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--x-archive',type=Path,required=True);a=p.parse_args();validate(a.output,a.x_archive)
