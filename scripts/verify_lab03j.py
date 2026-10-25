#!/usr/bin/env python3
"""Independent dense-OLS audit of J;never imports production model functions."""
import argparse,json
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.stats import rankdata
ROOT=Path(__file__).resolve().parents[1]
def holm(p):
 p=np.array(p);o=np.argsort(p);v=np.empty(len(p));v[o]=np.minimum(1,np.maximum.accumulate(p[o]*np.arange(len(p),0,-1)));return v
def audit(i_output,turnover,output):
 r=pd.read_csv(i_output/'gaps_preserved/returns_private.csv.gz',index_col=0,parse_dates=True,float_precision='round_trip');m=pd.read_csv(i_output/'market_private.csv.gz',index_col=0,parse_dates=True).iloc[:,0].reindex(r.index);c=pd.read_csv(output/'covariates_used.csv').set_index('papel_id').reindex(r.columns);table=pd.read_csv(output/'controlled_regressions.csv');association=pd.read_csv(output/'liquidity_change.csv');exclusion=pd.read_csv(output/'complete_case_audit.csv');v=pd.read_csv(turnover);v['date']=pd.to_datetime(v.date.astype(str),format='%Y%m%d');volume=v.pivot(index='date',columns='papel_id',values='volume').reindex(index=r.index,columns=r.columns).fillna(0.)
 bank=np.load(output/'bootstrap_draws.npz');maximum=0.;fits=0;regressions=0;corrs=0
 def fit(y,x):
  ok=np.isfinite(y)&np.isfinite(x);return np.linalg.lstsq(np.column_stack([np.ones(ok.sum()),x[ok]]),y[ok],rcond=None)[0][1]
 def quantities(ii,j):
  nonlocal fits
  x=m.iloc[ii].to_numpy();y=r.iloc[ii,j].to_numpy();bet=fit(y,x);neg=fit(y[x<0],x[x<0]);pos=fit(y[x>0],x[x>0]);fits+=3;return pos-neg,bet
 def coefficient(ys,bs,names,controls):
  ids=r.columns.get_indexer(names);part=c.reindex(names);X=[np.ones(len(names)),part.log_liquidity_2015.to_numpy()]
  if 'size' in controls:X.append(part.log_size.to_numpy())
  if 'sector' in controls:X.extend([(part.sector.to_numpy()==s).astype(float) for s in sorted(part.sector.unique())[1:]])
  if 'beta' in controls:X.append(bs[ids])
  X=np.column_stack(X);assert np.linalg.matrix_rank(X)==X.shape[1];return np.linalg.lstsq(X,ys[ids],rcond=None)[0][1]
 def corr(x,y):return np.corrcoef(rankdata(x),rankdata(y))[0,1]
 early=np.flatnonzero(r.index.year<=2020);late=np.flatnonzero(r.index.year>=2021);points=[]
 for ii in [early,late]:points.append(np.array([quantities(ii,j) for j in range(118)]))
 names={cohort:exclusion.query('cohort==@cohort and included').papel_id.tolist() for cohort in ['original80','union118']}
 for cohort,ids in names.items():
  part=c.reindex(ids);assert part.log_size.notna().all() and part.sector.notna().all();assert part.capital_filing_date.le('2015-12-31').all();assert part.capital_effective_date.le('2015-12-31').all();assert part['count_kind'].isin(['Capital Emitido','Capital Integralizado']).all()
 for row in table.itertuples():
  controls=[] if row.controls=='none' else row.controls.split('+');point=coefficient(points[0][:,0],points[0][:,1],names[row.cohort],controls);assert abs(point-row.estimate)<1e-10;maximum=max(maximum,abs(point-row.estimate));b=bank[f'{row.cohort}_{row.controls}_{row.block}'];q=np.quantile(b-row.estimate,[.025,.975]);pv=(1+np.sum(abs(b-row.estimate)>=abs(row.estimate)))/5000;np.testing.assert_allclose([pv,row.estimate-q[1],row.estimate-q[0]],[row.p,row.ci_low,row.ci_high],atol=1e-10);regressions+=1
 for L,g in table.groupby('block'):assert len(g)==16;np.testing.assert_allclose(holm(g.p),g.p_holm16,atol=1e-12)
 for L in [21,5,63]:
  rng=np.random.default_rng(20261025+L);draws=[]
  for ii in [early,late]:
   T=len(ii);starts=rng.integers(0,T-L+1,size=(4999,(T+L-1)//L));ix=ii[(starts[:3,:,None]+np.arange(L)).reshape(3,-1)[:,:T]];draws.append(ix)
  for b in range(3):
   qearly=np.array([quantities(draws[0][b],j) for j in range(118)]);qlate=np.array([quantities(draws[1][b],j) for j in range(118)])
   for row in table[table.block.eq(L)].itertuples():
    controls=[] if row.controls=='none' else row.controls.split('+');value=coefficient(qearly[:,0],qearly[:,1],names[row.cohort],controls);expected=bank[f'{row.cohort}_{row.controls}_{L}'][b];assert abs(value-expected)<1e-10;maximum=max(maximum,abs(value-expected));regressions+=1
   with np.errstate(divide='ignore',invalid='ignore'):change=np.log(volume.iloc[draws[1][b]].mean().to_numpy())-np.log(volume.iloc[draws[0][b]].mean().to_numpy())
   for row in association[association.block.eq(L)].itertuples():
    fixed=np.isfinite(r.iloc[early]).mean().to_numpy()>=.95;fixed&=np.isfinite(r.iloc[late]).mean().to_numpy()>=.95
    if row.cohort=='original80':fixed&=c.original80.to_numpy()
    jj=np.flatnonzero(fixed);x=c.log_liquidity_2015.to_numpy()[jj] if row.liquidity_target=='initial_level' else change[jj];value=corr(x,qlate[jj,0]-qearly[jj,0]);expected=bank[f'change_{row.cohort}_{row.liquidity_target}_{L}'][b];assert abs(value-expected)<1e-10;maximum=max(maximum,abs(value-expected));corrs+=1
 for L,g in association.groupby('block'):np.testing.assert_allclose(holm(g.p),g.p_holm4,atol=1e-12)
 gaps=pd.read_csv(i_output/'documented_gaps.csv');assert len(gaps)==7
 for row in gaps.itertuples():assert pd.isna(r.loc[row.date,row.papel_id])
 report=dict(passed=True,production_imported=False,dense_time_series_regressions=fits,dense_control_regressions_and_CI_p=regressions,explicit_change_rank_statistics=corrs,max_difference=maximum,documented_gaps_protected=7,source_dates_checked=True,scope='Independent numerical verification;not calibrated test size/coverage,exact yearend/free-float share certification or causal identification')
 (output/'independent_verification.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2));return report
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--i-output',type=Path,required=True);p.add_argument('--turnover',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();audit(a.i_output,a.turnover,a.output)
