#!/usr/bin/env python3
"""Independent dense OLS and explicit tail reconstruction; no K production imports."""
import argparse,json
from pathlib import Path
import numpy as np
import pandas as pd

def verify(i_output,j_batch,output):
 r=pd.read_csv(i_output/'gaps_preserved/returns_private.csv.gz',index_col=0,parse_dates=True,float_precision='round_trip').loc[:'2020'];m=pd.read_csv(i_output/'market_private.csv.gz',index_col=0,parse_dates=True,float_precision='round_trip').iloc[:,0].reindex(r.index).to_numpy()
 c=pd.read_csv(output/'covariates.csv',index_col=0,float_precision='round_trip').reindex(r.columns);elig=pd.read_csv(output/'eligibility.csv');table=pd.read_csv(output/'joint_tests.csv');coefs=pd.read_csv(output/'coefficients.csv');bank=np.load(output/'draws_private.npz');r15=pd.read_csv(output/'preperiod_returns_private.csv.gz',index_col=0,parse_dates=True,float_precision='round_trip');m15=pd.read_csv(Path(__file__).resolve().parents[1]/'data/lab03i/review_reference/market_returns_2015_2025.csv.gz',index_col=0,parse_dates=True,float_precision='round_trip').iloc[:,0].reindex(r15.index).to_numpy()
 errors=[];fits=0;crossfits=0
 for L in [21,5,63]:
  indices=[]
  for T,seed in [(len(m),20261025+L),(len(m15),20261027+L)]:
   rng=np.random.default_rng(seed);starts=rng.integers(0,T-L+1,size=(4999,(T+L-1)//L));indices.append((starts[:,:,None]+np.arange(L)).reshape(4999,-1)[:,:T])
  for k in [0,1,2,4999]:
   ix=np.arange(len(m)) if k==0 else indices[0][k-1];ix15=np.arange(len(m15)) if k==0 else indices[1][k-1];d=[];beta=[]
   for name in r.columns:
    y=r[name].to_numpy()[ix];market=m[ix];slopes=[]
    for sign in [market>0,market<0]:
     valid=sign&np.isfinite(y);slopes.append(np.linalg.lstsq(np.column_stack([np.ones(valid.sum()),market[valid]]),y[valid],rcond=None)[0][1]);fits+=1
    d.append(slopes[0]-slopes[1]);y=r15[name].to_numpy()[ix15];market=m15[ix15];valid=np.isfinite(y)&np.isfinite(market)
    beta.append(np.linalg.lstsq(np.column_stack([np.ones(valid.sum()),market[valid]]),y[valid],rcond=None)[0][1] if valid.sum()>2 else np.nan);fits+=1
   for row in table[table.block.eq(L)&table.status.eq('estimated')].itertuples():
    names=elig.query('cohort==@row.cohort and model==@row.model and included').papel_id;jj=r.columns.get_indexer(names);cc=c.iloc[jj]
    x=cc.log_amihud_2015.to_numpy() if row.model=='Amihud2015' else cc.log_liquidity_2015.to_numpy();X=[np.ones(len(jj)),x,cc.log_size.to_numpy()];X += [cc.sector.eq(s).to_numpy().astype(float) for s in sorted(cc.sector.unique())[1:]]
    if row.model=='beta2015':X.append(np.array(beta)[jj])
    expected=np.linalg.lstsq(np.column_stack(X),np.array(d)[jj],rcond=None)[0];actual=bank[f'{row.cohort}_{row.model}_{L}'][k];errors.append(float(np.max(abs(expected-actual))));crossfits+=1
  for row in table[table.block.eq(L)&table.status.eq('estimated')].itertuples():
   z=bank[f'{row.cohort}_{row.model}_{L}'][:,1:3];point=z[0];draw=z[1:];cov=np.cov(draw.T);inv=np.linalg.inv(cov);stat=point@inv@point;ee=draw-point;rad=np.array([v@inv@v for v in ee]);p=(1+(rad>=stat).sum())/5000;assert p==row.p
   selected=coefs.query('cohort==@row.cohort and model==@row.model and block==@L')
   for j,label in enumerate(['liquidity','size'],1):
    a=selected[selected.parameter.eq(label)].iloc[0];dd=bank[f'{row.cohort}_{row.model}_{L}'][:,j];q=np.quantile(dd[1:]-dd[0],[.025,.975]);errors+=[abs(a.ci_low-(dd[0]-q[1])),abs(a.ci_high-(dd[0]-q[0]))]
 # Existing reference liquidity estimates are exactly the old J size+sector model.
 old=pd.read_csv(j_batch/'outputs_J/controlled_regressions.csv');new=coefs.query('model=="reference" and parameter=="liquidity"')
 for row in new.itertuples():
  v=old.query('controls=="size+sector" and cohort==@row.cohort and block==@row.block').iloc[0];errors.append(abs(row.estimate-v.estimate))
 assert max(errors)<1e-9
 receipt=dict(passed=True,temporal_dense_fits=fits,cross_sectional_dense_fits=crossfits,joint_tail_checks=24,max_difference=max(errors),scope='numerical oracle, not coverage or economic certification')
 (output/'independent_verification.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--i-output',type=Path,required=True);p.add_argument('--j-batch',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();verify(a.i_output,a.j_batch,a.output)
