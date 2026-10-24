#!/usr/bin/env python3
"""Independent full-design OLS and direct-index bootstrap checks; no lab03f imports."""
import argparse
import hashlib
import json
from pathlib import Path
import zipfile
import numpy as np
import pandas as pd
from scipy.stats import norm
from threadpoolctl import threadpool_limits


def verify(root,archive,output):
    plan=json.loads((root/'data/lab03f/plano_pos_parecer_v1.json').read_text())
    assert hashlib.sha256(archive.read_bytes()).hexdigest()==plan['x_sha256']
    with zipfile.ZipFile(archive) as z:
        matrices={s:pd.read_csv(z.open(f'matrices/referencia_n/{s}/retornos_logaritmicos.csv.gz'),compression='gzip',index_col=0,parse_dates=True,float_precision='round_trip') for s in plan['samples']}
    meta=pd.read_csv(root/plan['metadata_path']);actual=pd.read_csv(output/'individual.csv.gz',float_precision='round_trip')
    maxdiff=0.;count=0
    weekly={s:q.groupby(q.index.to_period('W-FRI')).agg(lambda x:x.sum() if x.notna().all() else np.nan).iloc[1:-1] for s,q in matrices.items()}
    for row in actual.itertuples():
        a=matrices[row.scenario].copy();N=len(a);keep=np.ones(N,bool);idx=a.index
        if row.profile=='exclude_2020_03':keep=~((idx.year==2020)&(idx.month==3))
        if row.profile=='exclude_2020_H1':keep=~((idx.year==2020)&(idx.month<=6))
        if row.profile=='weekly':
            a=weekly[row.scenario]
            keep=np.ones(len(a),bool)
        m=a['^BVSP'];y=a[row.ticker];offsets=[-1,0,1] if row.profile=='leadlag1' else ([0,1] if row.profile=='lag1' else [0])
        MM=np.column_stack([m.shift(k) for k in offsets]);D=(m.to_numpy()>0).astype(float);continuous=row.profile=='continuous'
        X=np.column_stack(([np.ones(len(a))] if continuous else [np.ones(len(a)),D])+[MM,MM*D[:,None]])
        on=keep&np.isfinite(y)&np.isfinite(X).all(1)&m.ne(0)
        xx=X[on];yy=y.to_numpy()[on];b=np.linalg.lstsq(xx,yy,rcond=None)[0];bread=np.linalg.inv(xx.T@xx)
        start=1 if continuous else 2;K=len(offsets);C=np.zeros((2,len(b)));C[0,start+K:]=1
        if not continuous:C[1,1]=1
        score=np.zeros((len(a),len(b)));score[on]=xx*(yy-xx@b)[:,None]
        meat=score.T@score
        for h in range(1,6):
            cross=score[h:].T@score[:-h];meat+=(1-h/6)*(cross+cross.T)
        V=C@bread@meat@bread@C.T*on.sum()/(on.sum()-len(b))
        expected=np.r_[C@b,np.sqrt(np.maximum(0,np.diag(V)))]
        observed=np.array([row.delta,row.intercept_jump,row.delta_se_hac5,row.intercept_jump_se_hac5])
        np.testing.assert_allclose(observed,expected,atol=1e-10,rtol=1e-9)
        maxdiff=max(maxdiff,float(abs(observed-expected).max()));count+=1
    print(f'Independent OLS/sandwich: {count} fits checked',flush=True)
    cfg=plan['bootstrap'];B=cfg['replications'];R=5;J=117;seed=cfg['seed']
    sm={s:meta[meta.scenario.eq(s)].sort_values('papel_id') for s in matrices}
    tickers={s:list(sm[s].ticker) for s in sm};recent=matrices['recente'];before=matrices['decada'].loc[:'2020-12-31']
    common=[tickers['recente'].index(t) for t in tickers['decada']]
    bank=np.load(output/'bootstrap_targets.npz');checked=0;max_boot=0.

    def explicit_indices(N,L,rng):
        blocks=(N+L-1)//L;starts=rng.integers(0,N-L+1,size=(B,blocks))
        return [np.concatenate([np.arange(v,v+L) for v in row])[:N] for row in starts[:R]]

    def slopes(a,names):
        m=a['^BVSP'].to_numpy();out=[]
        for t in names:
            y=a[t].to_numpy();betas=[]
            for mask in [m>0,m<0]:
                on=mask&np.isfinite(y);X=np.column_stack([np.ones(on.sum()),m[on]])
                betas.append(np.linalg.lstsq(X,y[on],rcond=None)[0][1])
            out.append(betas[0]-betas[1])
        return np.array(out)

    for L in [21,5,63]:
        rid=explicit_indices(len(recent),L,np.random.default_rng(np.random.SeedSequence([seed,L,1])))
        for pi,profile in enumerate(['daily','exclude_2020_03','exclude_2020_H1']):
            keep=np.ones(len(before),bool)
            if profile=='exclude_2020_03':keep=~((before.index.year==2020)&(before.index.month==3))
            if profile=='exclude_2020_H1':keep=~((before.index.year==2020)&(before.index.month<=6))
            ids=np.flatnonzero(keep);segments=np.split(ids,np.flatnonzero(np.diff(ids)>1)+1)
            rng=np.random.default_rng(np.random.SeedSequence([seed,L,2,pi]))
            did=[explicit_indices(len(ix),L,rng) for ix in segments]
            for b in range(R):
                dec=pd.concat([*[before.iloc[ix[draw[b]]] for ix,draw in zip(segments,did)],recent.iloc[rid[b]][matrices['decada'].columns]])
                vals={'decada':slopes(dec,tickers['decada'])}
                if profile=='daily':
                    r=slopes(recent.iloc[rid[b]],tickers['recente']);vals.update(recente=r,decada_periodo_comum=r[common])
                for scenario,x in vals.items():
                    for statistic,fn in [('mean',np.mean),('median',np.median)]:
                        expected=fn(x);observed=bank[f'{profile}_{scenario}_{statistic}_L{L}'][b]
                        np.testing.assert_allclose(observed,expected,atol=1e-10,rtol=1e-9)
                        max_boot=max(max_boot,abs(observed-expected));checked+=1
    # Reconstruct every statistic/p-value/interval from the complete exported draws.
    aggregate=pd.read_csv(output/'aggregate.csv.gz',float_precision='round_trip')
    for row in aggregate.itertuples():
        draws=bank[f'{row.profile}_{row.scenario}_{row.statistic}_L{row.block}'];error=draws-row.estimate
        low,high=np.quantile(error,[.025,.975]);p=(1+(abs(error)>=abs(row.estimate)).sum())/(B+1)
        np.testing.assert_allclose([row.ci_low,row.ci_high,row.p_centered],[row.estimate-high,row.estimate-low,p],atol=1e-12)
    for L,g in aggregate.groupby('block'):
        order=g.p_centered.sort_values().index;expected=(aggregate.loc[order,'p_centered']*np.arange(10,0,-1)).cummax().clip(upper=1)
        np.testing.assert_allclose(aggregate.loc[order,'p_holm10'],expected,atol=1e-12)
    result=dict(passed=True,full_OLS_sandwich_fits=count,max_OLS_difference=maxdiff,
        explicit_bootstrap_statistics=checked,max_explicit_bootstrap_difference=max_boot,
        all_bootstrap_interval_and_pvalue_rows=len(aggregate),production_imports=False,
        scope='numerical consistency, not finite-sample coverage certification')
    (output/'independent_verification.json').write_text(json.dumps(result,indent=2)+'\n')
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--x-archive',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    with threadpool_limits(limits=1):print(json.dumps(verify(Path(__file__).resolve().parents[1],a.x_archive,a.output),indent=2))
