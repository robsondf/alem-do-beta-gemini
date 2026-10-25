#!/usr/bin/env python3
"""Export every regression coefficient and nominal uncertainty;Holm16 applies to liquidity only."""
import argparse,sys
from pathlib import Path
import numpy as np
import pandas as pd
from threadpoolctl import threadpool_limits
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from lab03j import estimates,block_weights,summarize

def run(i_output,output):
 r=pd.read_csv(i_output/'gaps_preserved/returns_private.csv.gz',index_col=0,parse_dates=True,float_precision='round_trip');r=r.loc[r.index.year<=2020];m=pd.read_csv(i_output/'market_private.csv.gz',index_col=0,parse_dates=True).iloc[:,0].reindex(r.index).to_numpy();cov=pd.read_csv(output/'covariates_used.csv').set_index('papel_id').reindex(r.columns);audit=pd.read_csv(output/'complete_case_audit.csv');models=pd.read_csv(output/'controlled_regressions.csv');point=estimates(r.to_numpy(),m,np.ones((1,len(m))));rows=[];maxerr=0.;dense_checks=0
 for L in [21,5,63]:
  w,_=block_weights(len(m),L,np.random.default_rng(20261025+L),4999);d,b=estimates(r.to_numpy(),m,w);Y=np.vstack([point[0],d]);B=np.vstack([point[1],b])
  for row in models[models.block.eq(L)].itertuples():
   names=audit.query('cohort==@row.cohort and included').papel_id;jj=r.columns.get_indexer(names);c=cov.iloc[jj];labels=['intercept','log_liquidity_2015'];X=[np.ones(len(c)),c.log_liquidity_2015.to_numpy()];controls=row.controls.split('+')
   if 'size' in controls:labels.append('log_size_proxy');X.append(c.log_size.to_numpy())
   if 'sector' in controls:
    for s in sorted(c.sector.unique())[1:]:labels.append('sector:'+s);X.append(c.sector.eq(s).to_numpy().astype(float))
   X=np.column_stack(X);pinv=np.linalg.pinv(X);yy=Y[:,jj];bb=B[:,jj];coef=yy@pinv.T
   if 'beta' in controls:
    proj=bb@pinv.T;br=bb-proj@X.T;yr=yy-coef@X.T;eta=np.sum(br*yr,axis=1)/np.sum(br*br,axis=1);coef=np.column_stack([coef-eta[:,None]*proj,eta]);labels.append('traditional_beta')
   for k in range(4):
    design=np.column_stack([X,bb[k]]) if 'beta' in controls else X;oracle=np.linalg.lstsq(design,yy[k],rcond=None)[0];maxerr=max(maxerr,float(np.max(abs(oracle-coef[k]))));dense_checks+=1
   assert abs(coef[0,1]-row.estimate)<1e-10
   for j,label in enumerate(labels):
    s=summarize(coef[0,j],coef[1:,j]);s['p_holm16']=row.p_holm16 if label=='log_liquidity_2015' else np.nan
    rows.append(dict(cohort=row.cohort,controls=row.controls,block=L,N=row.N,parameter=label,sector_reference=sorted(c.sector.unique())[0] if 'sector' in controls else '',inferential_role='Holm16_target' if label=='log_liquidity_2015' else 'descriptive_control_unadjusted',**s))
 assert maxerr<1e-10;pd.DataFrame(rows).to_csv(output/'all_control_coefficients.csv',index=False);return dict(passed=True,dense_checks=dense_checks,max_difference=maxerr,coefficient_rows=len(rows))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--i-output',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
 with threadpool_limits(limits=2):print(run(a.i_output,a.output))
