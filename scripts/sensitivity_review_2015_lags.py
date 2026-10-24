#!/usr/bin/env python3
"""Descriptive cumulative projections with predeclared lag lengths; no tests."""
import argparse,json
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.stats import spearmanr
ROOT=Path(__file__).resolve().parents[1]


def build(out):
    r=pd.read_csv(out/'gaps_preserved/returns_private.csv.gz',index_col=0,parse_dates=True,float_precision='round_trip');m=pd.read_csv(ROOT/'data/lab03i/review_reference/market_returns_2015_2025.csv.gz',index_col=0,parse_dates=True,float_precision='round_trip')['market'];li=pd.read_csv(out/'asset_liquidity.csv',index_col=0);names=list(r);records=[];max0=0.
    old=pd.read_csv(out/'gaps_preserved/assets_originais_COTAHIST.csv').set_index('papel_id');new=pd.read_csv(out/'gaps_preserved/assets_universo_2015.csv').set_index('papel_id');ref=pd.concat([old,new.loc[new.index.difference(old.index)]])
    for K in [0,1,5,10]:
        lag=pd.concat([m.shift(j).rename(j) for j in range(K+1)],axis=1).reindex(r.index);D=lag[0].gt(0).to_numpy();X=np.column_stack([np.ones(len(r)),D,lag.to_numpy(),D[:,None]*lag.to_numpy()]);market_ok=np.isfinite(X).all(axis=1)&lag[0].ne(0).to_numpy();periods={'early':r.index.year<=2020,'late':r.index.year>=2021,'decada':np.ones(len(r),bool)}
        for period,window in periods.items():
            eligible=market_ok&window;total=int(eligible.sum())
            for isin in names:
                v=eligible&np.isfinite(r[isin].to_numpy());n=int(v.sum());up=int((v&D).sum());dn=int((v&~D).sum());status='insufficient';delta=np.nan;beta_up=np.nan;beta_down=np.nan;rank=0
                if n>=200 and min(up,dn)>=60 and n/total>=.95:
                    coef,_,rank,_=np.linalg.lstsq(X[v],r[isin].to_numpy()[v],rcond=None)
                    if rank==X.shape[1]:beta_down=coef[2:3+K].sum();delta=coef[3+K:].sum();beta_up=beta_down+delta;status='ok'
                if K==0 and status=='ok':
                    expected=ref.loc[isin,'d_'+period];assert abs(delta-expected)<1e-10;max0=max(max0,abs(delta-expected))
                records.append(dict(papel_id=isin,K=K,period=period,n_pairs=n,n_plus=up,n_minus=dn,eligible_sessions=total,rank=rank,parameters=X.shape[1],status=status,beta_plus=beta_up,beta_minus=beta_down,delta=delta))
    frame=pd.DataFrame(records);frame.to_csv(out/'lag_asset_points.csv',index=False);rows=[]
    cohorts={'original80':old.index,'selected2015':new.index,'union118':r.columns}
    for K in [0,1,5,10]:
        f=frame[frame.K.eq(K)];early=f[f.period.eq('early')].set_index('papel_id');late=f[f.period.eq('late')].set_index('papel_id');dec=f[f.period.eq('decada')].set_index('papel_id');theta=late.delta-early.delta
        for cohort,ids in cohorts.items():
            for target,values,status in [('early',early.delta,early.status.eq('ok')),('theta',theta,early.status.eq('ok')&late.status.eq('ok')),('decada',dec.delta,dec.status.eq('ok'))]:
                keep=ids.intersection(status.index[status]);y=values.reindex(keep);x=li.adtv_2015.reindex(keep);rho=spearmanr(x,y).statistic if len(keep)>2 else np.nan;rows.append(dict(cohort=cohort,K=K,target=target,N=len(keep),mean=y.mean(),median=y.median(),liquidity_spearman=rho))
    summary=pd.DataFrame(rows);summary.to_csv(out/'lag_summary.csv',index=False);(out/'lag_verification.json').write_text(json.dumps({'K0_matches_independent_regime_points':True,'max_difference':max0,'per_asset_fits':len(frame),'summary_rows':len(summary),'new_pvalues':0,'estimand':'cumulative projection;not validated bias correction'},indent=2)+'\n');print(summary[summary.cohort.eq('original80')].to_string(index=False))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);build(p.parse_args().output)
