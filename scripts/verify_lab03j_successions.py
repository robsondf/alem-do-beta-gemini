#!/usr/bin/env python3
"""Dense OLS/rank and explicit-index audit for documented-lineage sensitivity."""
import argparse,json
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.stats import rankdata
ROOT=Path(__file__).resolve().parents[1]
def run(i_output,turnover,output):
 r=pd.read_csv(output/'succession_returns_private.csv.gz',index_col=0,parse_dates=True,float_precision='round_trip');old=pd.read_csv(i_output/'gaps_preserved/returns_private.csv.gz',index_col=0,parse_dates=True,float_precision='round_trip');m=pd.read_csv(i_output/'market_private.csv.gz',index_col=0,parse_dates=True).iloc[:,0].reindex(r.index);plan=json.loads((ROOT/'data/lab03j/adendo_sucessoes_v1.json').read_text());changed=[x['old_ISIN'] for x in plan['pairs']];np.testing.assert_allclose(r.drop(columns=changed),old.drop(columns=changed),equal_nan=True,atol=0,rtol=0)
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
 assert max(errors)<1e-10;report=dict(passed=True,production_imported=False,dense_regime_fits=fits,max_difference=max(errors),documented_transitions=3,gaps_protected=7,primary_other_ISINs_unchanged=True,scope='Numerical/continuity sensitivity audit;not exhaustive succession or economic-return certification');(output/'succession_verification.json').write_text(json.dumps(report,indent=2)+'\n');print(report)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--i-output',type=Path,required=True);p.add_argument('--turnover',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();run(a.i_output,a.turnover,a.output)
