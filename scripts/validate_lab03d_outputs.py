#!/usr/bin/env python3
"""Independent full-design, temporal and rolling-forecast verification.

No imports from lab03d implementation modules. Raw cached matrices are authenticated.
"""
import argparse,hashlib,json,zipfile,sys,time
from pathlib import Path
import numpy as np,pandas as pd
from scipy.linalg import toeplitz
from scipy.stats import norm
from threadpoolctl import threadpool_limits
ROOT=Path(__file__).resolve().parents[1]

def validate(output,x_archive,b_archive):
 started=time.monotonic();plan=json.loads((ROOT/'data/lab03d/plano_v1.json').read_text());lock=json.loads((ROOT/'data/lab03d/inputs_manifest.json').read_text())
 assert hashlib.sha256(x_archive.read_bytes()).hexdigest()==lock['x_sha256'];assert hashlib.sha256(b_archive.read_bytes()).hexdigest()==lock['b_sha256']
 assert hashlib.sha256((ROOT/'data/lab03d/plano_v1.json').read_bytes()).hexdigest()==lock['plan_sha256']
 z=zipfile.ZipFile(x_archive);manifest=json.loads(z.read('manifesto_exports.json'))
 assert set(z.namelist())==set(manifest)|{'manifesto_exports.json'}
 for n,h in manifest.items():assert hashlib.sha256(z.read(n)).hexdigest()==h
 variants=['referencia_n','jcp_duas_celulas_documentadas','jcp_condicional','jcp_rendimento_caixa_baixo','jcp_rendimento_caixa_alto']
 mats={v:{s:pd.read_csv(z.open(f'matrices/{v}/{s}/retornos_logaritmicos.csv.gz'),compression='gzip',index_col=0,parse_dates=True,float_precision='round_trip') for s in ['decada','recente']} for v in variants}
 z.close();design=pd.read_csv(output/'design.csv');annual=pd.read_csv(output/'annual_design.csv');nu=pd.read_csv(output/'asset_nuisance.csv')
 assert len(design)==197 and len(annual)==985 and len(nu)==117
 with zipfile.ZipFile(b_archive) as b:old=pd.read_csv(b.open('asset_betas.csv'))
 saved_arrays=np.load(output/'replicates.npz');arrays={name:saved_arrays[name] for name in saved_arrays.files};master=mats['referencia_n']['decada'];market=master['^BVSP'].to_numpy();N=len(market)
 assert arrays['error'].shape==(3,1000,197) and arrays['annual_error'].shape==(3,1000,985)
 assert arrays['theta_error'].shape==(3,1000,80) and arrays['critical'].shape==(3,1000)
 maxcoef=maxse=maxcov=maxcrit=0.;fits=0;sandwiches=0
 annual_idx={(row.papel_id,row.year):j for j,row in enumerate(annual.itertuples())}
 maps=[[annual_idx[(row.papel_id,y)] for y in range(2016 if row.scenario=='decada' else 2021,2026)] for row in design.itertuples()]
 def oracle(y,m,ok,eight=False,dates=None):
  nonlocal fits,sandwiches
  D=(m>0).astype(float);X=np.column_stack([np.ones(len(m)),D,m,D*m]);on=ok&(m!=0);j=3
  if eight:
   Q=(dates.year>=2021).astype(float);X=np.column_stack([X,X*Q[:,None]]);j=7
  xx=X[on];coef=np.linalg.lstsq(xx,y[on],rcond=None)[0];bread=np.linalg.inv(xx.T@xx);e=y[on]-xx@coef;h=np.einsum('ij,jk,ik->i',xx,bread,xx);ses=[];contrast=[]
  for mode in [0,1]:
   ee=e if mode==0 else e/(1-h);score=np.zeros_like(X);score[on]=xx*ee[:,None];meat=score.T@score
   for lag in range(1,6):
    cross=score[lag:].T@score[:-lag];meat+=(1-lag/6)*(cross+cross.T)
   correction=on.sum()/(on.sum()-X.shape[1]);cov=bread@meat@bread*correction;ses.append(np.sqrt(cov[j,j]));contrast.append(score@bread[:,j]*np.sqrt(correction));sandwiches+=1
  fits+=1;return coef[j],np.array(ses),contrast[1]
 def holm(p):
  p=np.asarray(p);out=np.empty_like(p);order=np.argsort(p,axis=-1,kind='stable');v=np.take_along_axis(p,order,axis=-1);adjusted=np.minimum(1,np.maximum.accumulate(v*np.arange(p.shape[-1],0,-1),axis=-1));np.put_along_axis(out,order,adjusted,axis=-1);return out
 # Independent RNG/AR recursion and full four/eight-column fits for first replication of each mechanism.
 actual_annual=np.empty(985);actual_ase=np.empty((2,985));actual_theta=np.empty(80);actual_tse=np.empty((2,80));actual_static=np.empty(197);actual_sse=np.empty((2,197))
 with threadpool_limits(limits=1):
  for mi in range(4):
   if mi<3:
    rng=np.random.default_rng(np.random.SeedSequence([plan['seed_entropy'],mi,0]));shape=(N+256,118)
    zz=rng.standard_normal(shape) if mi==0 else rng.standard_t(5,shape)*np.sqrt(.6);innov=np.sqrt(.3)*zz[:,:1]+np.sqrt(.7)*zz[:,1:];phi=0 if mi<2 else .3;previous=np.zeros(117);noise=np.empty_like(innov)
    for ti in range(len(noise)):noise[ti]=phi*previous+np.sqrt(1-phi*phi)*innov[ti];previous=noise[ti]
    h=np.sqrt(.5+.5*np.r_[market[0],market[:-1]]**2/np.mean(market**2));h/=np.sqrt(np.mean(h*h));noise=noise[256:]*(1 if mi==0 else h[:,None])*nu.sigma.to_numpy()
   joint=np.zeros((N,197))
   for j,row in enumerate(design.itertuples()):
    mat=mats['referencia_n'][row.scenario];m=mat['^BVSP'].to_numpy();ok=mat[row.ticker].notna().to_numpy();ti=master.index.get_indexer(mat.index)
    if mi<3:y=noise[ti,row.master_asset_index]+.015-.02*(m>0)+nu.iloc[row.master_asset_index].beta_base*m+.25*m*(m>0)
    else:y=mat[row.ticker].to_numpy()
    beta,se,score=oracle(y,m,ok);joint[ti,j]=score
    if mi<3:
     maxcoef=max(maxcoef,abs(beta-(arrays['error'][mi,0,j]+.25)));maxse=max(maxse,float(np.max(np.abs(se-arrays['se'][mi,:,0,j]))));np.testing.assert_allclose(beta,arrays['error'][mi,0,j]+.25,atol=1e-11,rtol=1e-9);np.testing.assert_allclose(se,arrays['se'][mi,:,0,j],atol=1e-12,rtol=1e-9)
    else:actual_static[j]=beta;actual_sse[:,j]=se
   # Direct Toeplitz construction is independent of the production moving-sum factor.
   K=toeplitz(np.maximum(0,1-np.arange(N)/6));cov=joint.T@K@joint;sd=np.sqrt(np.diag(cov));corr=cov/sd[:,None]/sd[None,:];corr=(corr+corr.T)/2
   val,vec=np.linalg.eigh(corr)
   try:L=np.linalg.cholesky(corr)
   except np.linalg.LinAlgError:
    assert val.min()>-1e-10;L=vec*np.sqrt(np.maximum(val,0))[None,:]
   rng=np.random.default_rng(np.random.SeedSequence([plan['seed_entropy'],mi if mi<3 else 9,0,991]));maxima=np.max(np.abs(rng.standard_normal((999,197))@L.T),axis=1);critical=np.sort(maxima)[950]
   if mi<3:maxcrit=max(maxcrit,abs(critical-arrays['critical'][mi,0]));np.testing.assert_allclose(critical,arrays['critical'][mi,0],rtol=1e-9,atol=1e-11)
   else:
    got=np.load(output/'observed_multiplier_covariance.npy');maxcov=float(np.max(np.abs(cov-got)));np.testing.assert_allclose(cov,got,rtol=1e-9,atol=1e-12)
    np.testing.assert_allclose(maxima,pd.read_csv(output/'multiplier_maxima.csv').maximum,rtol=1e-9,atol=1e-11)
   for j,row in enumerate(annual.itertuples()):
    scenario='decada' if row.year<2021 else 'recente';mat=mats['referencia_n'][scenario];mat=mat[mat.index.year==row.year];m=mat['^BVSP'].to_numpy();ok=mat[row.ticker].notna().to_numpy();ti=master.index.get_indexer(mat.index);ni=int(nu.index[nu.papel_id.eq(row.papel_id)][0])
    y=mat[row.ticker].to_numpy() if mi==3 else noise[ti,ni]+.25*m*(m>0)+.015-.02*(m>0)
    beta,se,_=oracle(y,m,ok)
    if mi<3:
     maxcoef=max(maxcoef,abs(beta-(arrays['annual_error'][mi,0,j]+.25)));maxse=max(maxse,float(np.max(np.abs(se-arrays['annual_se'][mi,:,0,j]))));np.testing.assert_allclose(beta,arrays['annual_error'][mi,0,j]+.25,atol=1e-11,rtol=1e-9);np.testing.assert_allclose(se,arrays['annual_se'][mi,:,0,j],atol=1e-12,rtol=1e-9)
    else:actual_annual[j]=beta;actual_ase[:,j]=se
   for j,row in enumerate(design.iloc[:80].itertuples()):
    m=market;ok=master[row.ticker].notna().to_numpy();Q=(master.index.year>=2021).astype(float)
    y=master[row.ticker].to_numpy() if mi==3 else noise[:,row.master_asset_index]+.015-.02*(m>0)+.25*Q*m*(m>0)
    beta,se,_=oracle(y,m,ok,eight=True,dates=master.index)
    if mi<3:
     maxcoef=max(maxcoef,abs(beta-(arrays['theta_error'][mi,0,j]+.25)));maxse=max(maxse,float(np.max(np.abs(se-arrays['theta_se'][mi,:,0,j]))));np.testing.assert_allclose(beta,arrays['theta_error'][mi,0,j]+.25,atol=1e-11,rtol=1e-9);np.testing.assert_allclose(se,arrays['theta_se'][mi,:,0,j],atol=1e-12,rtol=1e-9)
    else:actual_theta[j]=beta;actual_tse[:,j]=se
 print('Independent OLS/sandwich oracle passed:',fits,sandwiches,flush=True)
 comparisons=0
 def same(a,b):
  nonlocal comparisons
  np.testing.assert_allclose(a,b,rtol=1e-9,atol=1e-11,equal_nan=True);comparisons+=np.size(b)
 Z=norm.ppf(.975);R=1000
 def rates(ev):
  p=ev.mean(0);se=np.sqrt(p*(1-p)/R);den=1+Z*Z/R;center=(p+Z*Z/(2*R))/den;radius=Z*np.sqrt(p*(1-p)/R+Z*Z/(4*R*R))/den;return p,se,np.maximum(0,center-radius),np.minimum(1,center+radius)
 def check_family(row,raw,reject,null):
  assert row.null_cases==null.sum() and row.nonnull_cases==(~null).sum()
  for name,ev in [('fwer_raw',raw),('fwer_adjusted',reject)]:
   values=rates(ev[:,null].any(1)) if null.any() else [np.nan]*4
   same(row[[name,name+'_mcse',name+'_mc_low',name+'_mc_high']].to_numpy(float),values)
  for name,ev in [('power_raw',raw),('power_adjusted',reject)]:
   values=ev[:,~null].mean(1) if (~null).any() else None;same(row[[name,name+'_mcse']].to_numpy(float),[values.mean(),values.std(ddof=1)/np.sqrt(R)] if values is not None else [np.nan,np.nan])
 sc=pd.read_csv(output/'static_calibration.csv');sf=pd.read_csv(output/'static_family.csv');sr=pd.read_csv(output/'static_rejection.csv');sp=pd.read_csv(output/'static_panels.csv');tc=pd.read_csv(output/'temporal_calibration.csv');tf=pd.read_csv(output/'temporal_family.csv');th=pd.read_csv(output/'temporal_hypotheses.csv')
 assert [len(x) for x in [sc,sf,sr,sp,tc,tf,th]]==[1773,81,15957,162,6390,30,14220]
 selected=set(nu.papel_id[:12]);static_patterns=[(f'dense_{v:+.2f}',np.full(197,v)) for v in [-.5,-.25,-.1,0,.1,.25,.5]]+[(f'sparse_{v:+.2f}',np.where(design.papel_id.isin(selected),v,0.)) for v in [-.25,.25]]
 methods=['HAC5_Holm','HC3_HAC5_Holm','HC3_HAC5_maxT']
 for mi,spec in enumerate(plan['mechanisms']):
  mechanism=spec['name'];E=arrays['error'][mi]
  for method in methods:
   li=0 if method==methods[0] else 1;S=arrays['se'][mi,li];critical=Z if method!=methods[2] else arrays['critical'][mi,:,None];covered=np.abs(E)<=critical*S
   q=sc[sc.mechanism.eq(mechanism)&sc.method.eq(method)]
   for name,values in dict(bias=E.mean(0),bias_mcse=E.std(0,ddof=1)/np.sqrt(R),rmse=np.sqrt((E**2).mean(0)),empirical_se=E.std(0,ddof=1),mean_model_se=S.mean(0)).items():same(q[name],values)
   for name,values in zip(['coverage','coverage_mcse','coverage_mc_low','coverage_mc_high'],rates(covered)):same(q[name],values)
   for pattern,truth in static_patterns:
    p=2*norm.sf(np.abs((E+truth)/S));raw=p<.05;reject=holm(p)<.05 if method!=methods[2] else np.abs((E+truth)/S)>critical;null=truth==0
    select=lambda t:t[t.mechanism.eq(mechanism)&t.method.eq(method)&t.pattern.eq(pattern)]
    check_family(select(sf).iloc[0],raw,reject,null);q=select(sr)
    for name,values in zip(['adjusted_rejection','adjusted_mcse','adjusted_mc_low','adjusted_mc_high'],rates(reject)):same(q[name],values)
    same(q.raw_rejection,raw.mean(0));same(q.true_delta,truth)
    for scenario in ['decada','recente']:
     row=select(sp);row=row[row.scenario.eq(scenario)].iloc[0];ix=design.scenario.eq(scenario).to_numpy()
     for key,ev,mask in [('coverage',covered,ix),('power_adjusted',reject,ix&~null),('type1_raw',raw,ix&null)]:
      v=ev[:,mask].mean(1) if mask.any() else None;same(row[[key,key+'_mcse']].to_numpy(float),[v.mean(),v.std(ddof=1)/np.sqrt(R)] if v is not None else [np.nan,np.nan])
  for li,method in enumerate(methods[:2]):
   AE=arrays['annual_error'][mi];AS=arrays['annual_se'][mi,li];TE=arrays['theta_error'][mi];TS=arrays['theta_se'][mi,li]
   for kind,E,S in [('annual',AE,AS),('theta',TE,TS)]:
    q=tc[tc.mechanism.eq(mechanism)&tc.method.eq(method)&tc.kind.eq(kind)];cv=np.abs(E)<=Z*S;same(q.bias,E.mean(0));same(q.mean_model_se,S.mean(0));same(q.empirical_se,E.std(0,ddof=1))
    for name,values in zip(['coverage','coverage_mcse','coverage_mc_low','coverage_mc_high'],rates(cv)):same(q[name],values)
   for pattern in plan['temporal']['patterns']:
    truth=np.zeros(985)
    if pattern=='constant_positive_.25':truth[:]=.25
    elif pattern=='constant_negative_.25':truth[:]=-.25
    elif pattern=='early_negative_late_positive_.25':truth=np.where(annual.year<=2020,-.25,.25)
    elif pattern=='sparse_positive_.25':truth=np.where(annual.papel_id.isin(selected),.25,0)
    tt=np.full(80,.5 if pattern=='early_negative_late_positive_.25' else 0.)
    positive=np.array([np.all(truth[ix]>0) for ix in maps]);negative=np.array([np.all(truth[ix]<0) for ix in maps]);null=np.r_[tt==0,~positive,~negative]
    pp=np.column_stack([norm.sf((AE[:,ix]+truth[ix])/AS[:,ix]).max(1) for ix in maps]);pn=np.column_stack([norm.cdf((AE[:,ix]+truth[ix])/AS[:,ix]).max(1) for ix in maps]);p=np.column_stack([2*norm.sf(np.abs((TE+tt)/TS)),pp,pn]);raw=p<.05;reject=holm(p)<.05
    select=lambda t:t[t.mechanism.eq(mechanism)&t.method.eq(method)&t.pattern.eq(pattern)]
    check_family(select(tf).iloc[0],raw,reject,null);q=select(th);np.testing.assert_array_equal(q.is_true_null,null)
    for name,values in zip(['adjusted_rejection','adjusted_mcse','adjusted_mc_low','adjusted_mc_high'],rates(reject)):same(q[name],values)
 # Actual outputs: all point estimates/p-values, preserving original primary family.
 obs=pd.read_csv(output/'observed_static.csv');ot=pd.read_csv(output/'observed_temporal.csv')
 for li,method in enumerate(methods):
  k=0 if li==0 else 1;q=obs[obs.method.eq(method)];same(q.delta,actual_static);same(q.se_delta,actual_sse[k]);p=2*norm.sf(np.abs(actual_static/actual_sse[k]));same(q.p_raw,p)
  if li<2:same(q.p_adjusted,holm(p))
  else:same(q.p_adjusted,(1+(maxima[:,None]>=np.abs(actual_static/actual_sse[k])[None,:]).sum(0))/1000)
  if li==0:
   prior=q.merge(old,on=['scenario','papel_id'],suffixes=('_new','_old'));assert len(prior)==197;same(prior.delta_new,prior.delta_old);same(prior.se_delta,prior.delta_se);same(prior.p_adjusted,prior.delta_p_holm_197)
 for k,method in enumerate(methods[:2]):
  pp=np.array([norm.sf(actual_annual[ix]/actual_ase[k,ix]).max() for ix in maps]);pn=np.array([norm.cdf(actual_annual[ix]/actual_ase[k,ix]).max() for ix in maps]);p=np.r_[2*norm.sf(np.abs(actual_theta/actual_tse[k])),pp,pn];q=ot[ot.method.eq(method)];same(q.p_raw,p);same(q.p_adjusted,holm(p))
 print('Independent inference summaries passed:',comparisons,'values',flush=True)
 prediction_receipt=validate_prediction(output,mats,design,plan)
 receipt=dict(status='passed',independent_of_lab03d_imports=True,full_ols_oracle_fits=fits,sandwich_oracle_evaluations=sandwiches,max_coefficient_absolute_difference=maxcoef,max_se_absolute_difference=maxse,max_joint_covariance_absolute_difference=maxcov,max_multiplier_critical_absolute_difference=maxcrit,inference_summary_values_recalculated=int(comparisons),prediction=prediction_receipt,runtime_seconds=time.monotonic()-started,all_limitations_eliminated=False,global_homologated=0)
 (output/'validacao_independente.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt,indent=2));return receipt


def validate_prediction(output,mats,design,plan):
 """Full-fold independent lstsq + brute-force integration and score recomputation."""
 metrics=pd.read_csv(output/'prediction_metrics.csv');gains=pd.read_csv(output/'prediction_gains.csv');folds=pd.read_csv(output/'prediction_folds.csv');daily=pd.read_csv(output/'prediction_daily.csv.gz',float_precision='round_trip');intervals=pd.read_csv(output/'prediction_intervals.csv')
 assert folds.origin.lt(folds.target_start).all() and folds.max_train_date.le(folds.origin).all()
 assert daily.training_origin.lt(daily.date).all() and daily.previous_market_date.lt(daily.date).all()
 assert len(intervals)==1662 and intervals.interval_scope.str.startswith('exploratory marginal').all()
 configs=[('N252','referencia_n',252,None),('N504','referencia_n',504,None),('gap_guard252','referencia_n',252,'gap'),('LightQ4252','referencia_n',252,'light')]+[(v+'252',v,252,None) for v in ['jcp_duas_celulas_documentadas','jcp_condicional','jcp_rendimento_caixa_baixo','jcp_rendimento_caixa_alto']]
 models=['zero','historical_mean','traditional_market','conditional_market'];count=0;forecast_values=0;maxdiff=0.;allmetrics=[];allgains=[];maxsummary=0.
 long_ids=set(design[design.scenario.eq('decada')].papel_id)
 with threadpool_limits(limits=1):
  for config,variant,W,mode in configs:
   results=[]
   for scenario,start_year in [('decada',2019),('recente',2024)]:
    sample=design[design.scenario.eq(scenario)].reset_index(drop=True);a=mats[variant][scenario].copy()
    if mode=='light':a.loc[(a.index>='2024-10-01')&(a.index<='2024-12-31'),'LIGT3.SA']=np.nan
    targets=np.flatnonzero((a.index.year>=start_year)&(a.index.year<=2025));dates=a.index[targets];periods=dates.to_period('M');pred=np.empty((len(targets),len(sample),4));m=a['^BVSP'].to_numpy()
    saved_fold=folds[folds.configuration.eq(config)&folds.scenario.eq(scenario)].set_index(['papel_id','origin'],verify_integrity=True)
    for period in periods.unique():
     loc=np.flatnonzero(periods==period);idx=targets[loc];origin=int(idx[0]-1);train=np.arange(origin-W+1,origin+1);mt=m[train];Y=a[sample.ticker].to_numpy()[train].copy()
     if mode=='gap':
      for j,col in enumerate(sample.ticker):
       known=np.flatnonzero(a[col].iloc[:origin+1].isna().to_numpy());near={k for v in known for k in [v-1,v,v+1] if train[0]<=k<=origin}
       for k in near:Y[k-train[0],j]=np.nan
     valid=np.isfinite(Y)&(mt[:,None]!=0)
     arX=np.column_stack([np.ones(W-1),mt[:-1]]);ar=np.linalg.lstsq(arX,mt[1:],rcond=None)[0];eps=mt[1:]-arX@ar;eps-=eps.mean();ms=ar[0]+ar[1]*m[idx-1,None]+eps[None,:]
     X=np.column_stack([np.ones(W),mt>0,mt,mt*(mt>0)]);F=np.column_stack([np.ones(len(idx)),(ms>0).mean(1),ms.mean(1),(ms*(ms>0)).mean(1)])
     # Group by identical masks to solve all assets with the same full design together.
     groups={}
     for j in range(len(sample)):groups.setdefault(valid[:,j].tobytes(),[]).append(j)
     for positions in groups.values():
      on=valid[:,positions[0]];n=on.sum();np_=np.sum(on&(mt>0));nm_=np.sum(on&(mt<0));vv=[np.var(mt[on],ddof=1),np.var(mt[on&(mt>0)],ddof=1),np.var(mt[on&(mt<0)],ddof=1)]
      eligible=n>=200 and n/W>=.95 and np_>=60 and nm_>=60 and min(vv)>=1e-12
      mean=Y[on][:,positions].mean(0);pred[np.ix_(loc,positions,[0])]=0;pred[np.ix_(loc,positions,[1])]=mean[None,:,None]
      if eligible:
       beta=np.linalg.lstsq(X[on],Y[on][:,positions],rcond=None)[0];bt=np.linalg.lstsq(X[on][:,[0,2]],Y[on][:,positions],rcond=None)[0]
       ft=np.column_stack([np.ones(len(idx)),ms.mean(1)])@bt;fc=F@beta
       zero=(ms==0).mean(1)
       if zero.any():fc+=zero[:,None]*(bt[0]-beta[0])
       pred[np.ix_(loc,positions,[2])]=ft[:,:,None];pred[np.ix_(loc,positions,[3])]=fc[:,:,None];count+=2
      else:
       pred[np.ix_(loc,positions,[2])]=mean[None,:,None];pred[np.ix_(loc,positions,[3])]=mean[None,:,None]
      for j in positions:
       row=saved_fold.loc[(sample.iloc[j].papel_id,a.index[origin].date().isoformat())]
       assert [row.n_pairs,row.n_plus,row.n_minus]==[n,np_,nm_];assert row.status==('estimated' if eligible else 'historical_mean_fallback');assert row.max_train_date==a.index[train[on][-1]].date().isoformat()
    actual=a[sample.ticker].to_numpy()[targets].copy()
    if mode=='gap':actual[np.isnan(a[sample.ticker].to_numpy()[targets-1])]=np.nan
    result=dict(sample=sample,dates=dates,pred=pred,actual=actual,market=m[targets]);results.append(result)
    if config in ['N252','N504']:
     saved=daily[daily.configuration.eq(config)&daily.scenario.eq(scenario)]
     assert len(saved)==pred.shape[0]*pred.shape[1]
     np.testing.assert_array_equal(saved.papel_id.to_numpy(),np.tile(sample.papel_id,len(dates)))
     values=saved[models].to_numpy().reshape(pred.shape);diff=float(np.max(np.abs(values-pred)));maxdiff=max(maxdiff,diff);np.testing.assert_allclose(values,pred,atol=1e-12,rtol=1e-9);forecast_values+=pred.size
     np.testing.assert_allclose(saved.actual.to_numpy().reshape(actual.shape),actual,atol=0,rtol=0,equal_nan=True);np.testing.assert_array_equal(saved.valid_target,np.isfinite(actual).ravel())
    # Every aggregate/annual/regime row independently reconstructed.
    def collect(result,scenario2,ids):
     nonlocal maxsummary
     ss=result['sample'].iloc[ids];yy=result['actual'][:,ids];ff=result['pred'][:,ids];mm=result['market'];dt=result['dates']
     periods2=[('full','all',np.ones(len(dt),bool)),('full','positive',mm>0),('full','negative',mm<0)]+[(str(y),'all',dt.year==y) for y in sorted(set(dt.year))]
     for period2,regime,time in periods2:
      valid=np.isfinite(yy)&time[:,None];n=valid.sum(0);e=np.where(valid[:,:,None],yy[:,:,None]-ff,0);mse=(e*e).sum(0)/np.maximum(1,n)[:,None];mae=np.abs(e).sum(0)/np.maximum(1,n)[:,None];mse[n==0]=np.nan;mae[n==0]=np.nan
      for j,row in enumerate(ss.itertuples()):
       for k,model in enumerate(models):allmetrics.append((config,scenario2,row.papel_id,period2,regime,model,int(n[j]),mse[j,k],mae[j,k],1-mse[j,k]/mse[j,0],1-mse[j,k]/mse[j,1]))
       allgains.append((config,scenario2,row.papel_id,period2,regime,int(n[j]),mse[j,2]-mse[j,3],1-mse[j,3]/mse[j,2]))
    collect(result,scenario,np.arange(len(sample)))
   recent=results[1];ix=np.flatnonzero(recent['sample'].papel_id.isin(long_ids));collect(recent,'decada_periodo_comum',ix)
   long=results[0];ti=long['dates'].get_indexer(recent['dates']);ix2=[int(recent['sample'].index[recent['sample'].papel_id.eq(pid)][0]) for pid in long['sample'].papel_id];np.testing.assert_allclose(long['pred'][ti],recent['pred'][:,ix2],atol=1e-12,rtol=1e-9)
   print('Independent forecast configuration verified:',config,flush=True)
 ref=pd.DataFrame(allmetrics,columns=['configuration','scenario','papel_id','period','regime','model','n','mse','mae','r2_vs_zero','r2_vs_mean']);refg=pd.DataFrame(allgains,columns=['configuration','scenario','papel_id','period','regime','n','loss_gain','relative_mse_gain']);assert len(ref)==len(metrics) and len(refg)==len(gains)
 keys=['configuration','scenario','papel_id','period','regime','model'];actual=metrics.copy();actual['period']=actual.period.astype(str)
 joined=actual.merge(ref,on=keys,suffixes=('_actual','_ref'),validate='one_to_one');assert len(joined)==len(metrics)
 for key in ['n','mse','mae','r2_vs_zero','r2_vs_mean']:
  av=joined[key+'_actual'].to_numpy();bv=joined[key+'_ref'].to_numpy();np.testing.assert_allclose(av,bv,atol=1e-11,rtol=1e-9,equal_nan=True);maxsummary=max(maxsummary,float(np.nanmax(np.abs(av-bv))))
 actual=gains.copy();actual['period']=actual.period.astype(str);joined=actual.merge(refg,on=keys[:-1],suffixes=('_actual','_ref'),validate='one_to_one');assert len(joined)==len(gains)
 for key in ['n','loss_gain','relative_mse_gain']:np.testing.assert_allclose(joined[key+'_actual'],joined[key+'_ref'],atol=1e-11,rtol=1e-9,equal_nan=True)
 # Direct resampled-index means independently check all marginal interval endpoints.
 bootstrap_values=0
 for configuration,W in [('N252',252),('N504',504)]:
  for pi,scenario in enumerate(['decada','recente']):
   q=daily[daily.configuration.eq(configuration)&daily.scenario.eq(scenario)]
   A=80 if pi==0 else 117;T=len(q)//A;yy=q.actual.to_numpy().reshape(T,A);ft=q.traditional_market.to_numpy().reshape(T,A);fc=q.conditional_market.to_numpy().reshape(T,A);valid=np.isfinite(yy);diff=np.where(valid,(yy-ft)**2-(yy-fc)**2,0);pids=q.papel_id.to_numpy()[:A]
   for block in [21,42,63]:
    rng=np.random.default_rng(np.random.SeedSequence([plan['seed_entropy'],701,W,pi,block]));boot=np.empty((1999,A));blocks=int(np.ceil(T/block))
    for b in range(1999):
     starts=rng.integers(0,T-block+1,size=blocks);indices=np.concatenate([np.arange(v,v+block) for v in starts])[:T];boot[b]=diff[indices].sum(0)/valid[indices].sum(0)
    print('Independent bootstrap verified:',configuration,scenario,block,flush=True)
    lo,hi=np.quantile(boot,[.025,.975],axis=0);saved=intervals[intervals.configuration.eq(configuration)&intervals.scenario.eq(scenario)&intervals.block_length.eq(block)]
    np.testing.assert_array_equal(saved.papel_id,pids);np.testing.assert_allclose(saved.ci_low,lo,atol=1e-12,rtol=1e-9);np.testing.assert_allclose(saved.ci_high,hi,atol=1e-12,rtol=1e-9);bootstrap_values+=1999*A
    common=intervals[intervals.configuration.eq(configuration)&intervals.scenario.eq('decada_periodo_comum')&intervals.block_length.eq(block)]
    if scenario=='recente':
     matched=common.merge(saved,on='papel_id',suffixes=('_common','_recent'));assert len(matched)==80;np.testing.assert_array_equal(matched.ci_low_common,matched.ci_low_recent);np.testing.assert_array_equal(matched.ci_high_common,matched.ci_high_recent)
 return dict(bootstrap_draw_asset_values_recalculated=bootstrap_values,full_design_ols_groups=count,forecast_numeric_values_recalculated=forecast_values,max_daily_forecast_absolute_difference=maxdiff,metrics_rows_recalculated=len(metrics),gain_rows_recalculated=len(gains),all_fold_rows_checked=len(folds),max_metric_absolute_difference=maxsummary,strict_temporal_cutoffs=True,common80_reuse_verified_all8configs=True,bootstrap_intervals_scope='exploratory marginal, not independently recalibrated for predictive nominal coverage',retrospective_selection_and_data_vintage_limits_remain=True)

if __name__=='__main__':
 p=argparse.ArgumentParser()
 for n in ['output','x-archive','b-archive']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();validate(a.output,a.x_archive,a.b_archive)
