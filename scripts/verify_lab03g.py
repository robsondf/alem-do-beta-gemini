#!/usr/bin/env python3
"""Independent direct-row OLS oracle and complete exported-statistic checks.

No production G imports. Calibration summaries are recomputed, not taken on trust.
This checks numerical implementation, not unrestricted bootstrap validity.
"""
import argparse,hashlib,json,zipfile
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.stats import norm
from threadpoolctl import threadpool_limits


def adjust(p):
    p=np.asarray(p);order=np.argsort(p);out=np.empty(len(p));out[order]=np.minimum(1,np.maximum.accumulate(p[order]*np.arange(len(p),0,-1)));return out


def verify(root,archive,out):
    lock=json.loads((root/'data/lab03g/inputs_manifest.json').read_text());assert hashlib.sha256(archive.read_bytes()).hexdigest()==lock['x_sha256']
    plan=json.loads((root/'data/lab03g/plano_v1.json').read_text());fp=json.loads((root/'data/lab03f/plano_pos_parecer_v1.json').read_text())
    with zipfile.ZipFile(archive) as z:
        mats={s:pd.read_csv(z.open(f'matrices/referencia_n/{s}/retornos_logaritmicos.csv.gz'),compression='gzip',index_col=0,parse_dates=True,float_precision='round_trip') for s in ['decada','recente']}
    meta=pd.read_csv(root/fp['metadata_path']);names={s:list(meta[meta.scenario.eq(s)].sort_values('papel_id').ticker) for s in mats};common=[names['recente'].index(t) for t in names['decada']]
    actual=pd.read_csv(out/'observed_aggregate.csv.gz',float_precision='round_trip');bank=np.load(out/'observed_draws.npz');B=4999;R=3;checked=0;maxdiff=0.

    def ids(N,L,rng):
        starts=rng.integers(0,N-L+1,size=(B,(N+L-1)//L));return (starts[:R,:,None]+np.arange(L)).reshape(R,-1)[:,:N]

    def slopes(frame,tickers,offsets,ix):
        m=frame['^BVSP'];M=np.column_stack([m.shift(k) for k in offsets]);D=(m.to_numpy()>0);X=np.column_stack([np.ones(len(m)),D,M,M*D[:,None]])[ix];ans=[]
        for t in tickers:
            y=frame[t].to_numpy()[ix];valid=np.isfinite(X).all(1)&np.isfinite(y)&m.to_numpy()[ix].astype(bool)
            coef=np.linalg.lstsq(X[valid],y[valid],rcond=None)[0];ans.append(coef[2+len(offsets):].sum())
        return np.array(ans)

    def compare(profile,scenario,L,b,values):
        nonlocal checked,maxdiff
        for stat,fn in [('mean',np.mean),('median',np.median)]:
            v=bank[f'{profile}_{scenario}_{stat}_L{L}'][b];expected=fn(values)
            np.testing.assert_allclose(v,expected,atol=1e-10,rtol=1e-9);maxdiff=max(maxdiff,abs(v-expected));checked+=1

    before=mats['decada'].loc[:'2020-12-31'];recent=mats['recente']
    for L in [21,5,63]:
        earlyids=ids(len(before),L,np.random.default_rng(np.random.SeedSequence([fp['bootstrap']['seed'],L,2,0])));lateids=ids(len(recent),L,np.random.default_rng(np.random.SeedSequence([fp['bootstrap']['seed'],L,1])))
        for b in range(R):
            ep=slopes(before,names['decada'],[0],earlyids[b]);lp=slopes(recent,names['recente'],[0],lateids[b])[common]
            compare('early','decada',L,b,ep);compare('theta','decada',L,b,lp-ep)
    for pi,profile in enumerate(['lag1','leadlag1','weekly']):
        for L in ([4,1,13] if profile=='weekly' else [21,5,63]):
            for si,s in enumerate(['decada','recente']):
                f=mats[s]
                if profile=='weekly':f=f.groupby(f.index.to_period('W-FRI')).agg(lambda q:q.sum() if q.notna().all() else np.nan).iloc[1:-1];f.index=f.index.to_timestamp(how='end').normalize()
                rng=np.random.default_rng(np.random.SeedSequence([plan['observed_bootstrap']['seed'],700,pi,si,L]));ixs=[]
                for seg in [np.flatnonzero(f.index.year<2021),np.flatnonzero(f.index.year>=2021)]:
                    if len(seg):ixs.append(seg[ids(len(seg),L,rng)])
                ix=np.column_stack(ixs);offsets=[0,1] if profile=='lag1' else ([-1,0,1] if profile=='leadlag1' else [0])
                for b in range(R):
                    val=slopes(f,names[s],offsets,ix[b]);compare(profile,s,L,b,val)
                    if s=='recente':compare(profile,'decada_periodo_comum',L,b,val[common])
    for row in actual.itertuples():
        b=bank[f'{row.profile}_{row.scenario}_{row.statistic}_L{int(row.block)}'];err=b-row.estimate;lo,hi=np.quantile(err,[.025,.975]);p=(1+(abs(err)>=abs(row.estimate)).sum())/5000
        assert row.invalid_draws==0
        np.testing.assert_allclose([row.ci_low,row.ci_high,row.p_centered,row.bootstrap_mean,row.bootstrap_bias,row.bootstrap_se],[row.estimate-hi,row.estimate-lo,p,b.mean(),b.mean()-row.estimate,b.std(ddof=1)],atol=1e-11,rtol=1e-9)
    for _,g in actual[actual.family.eq('temporal4')].groupby('block'):np.testing.assert_allclose(g.p_adjusted,adjust(g.p_centered),atol=1e-12)
    for _,g in actual[actual.family.eq('micro18')].groupby('block_choice'):np.testing.assert_allclose(g.p_adjusted,adjust(g.p_centered),atol=1e-12)
    mc=pd.read_csv(out/'calibration_replications.csv.gz',float_precision='round_trip');cases=pd.read_csv(out/'calibration_cases.csv');families=pd.read_csv(out/'calibration_families.csv')
    assert len(mc)==84000 and len(cases)==252 and len(families)==24
    assert set(mc.mechanism)==set(plan['calibration']['mechanisms']) and mc.invalid_draws.eq(0).all()
    for _,g in mc.groupby(['mechanism','replication','family']):np.testing.assert_allclose(g.p_adjusted,adjust(g.p_centered),atol=1e-12)
    def check_rate(events,row):
        n=len(events);p=np.mean(events);z=norm.ppf(.975);den=1+z*z/n;c=(p+z*z/(2*n))/den;r=z*np.sqrt(p*(1-p)/n+z*z/(4*n*n))/den
        np.testing.assert_allclose([row.rate,row.mcse,row.wilson_low,row.wilson_high],[p,np.sqrt(p*(1-p)/n),max(0,c-r),min(1,c+r)],atol=1e-12)
    for row in cases.itertuples():
        g=mc[(mc.mechanism==row.mechanism)&(mc.family==row.family)&(mc.profile==row.profile)&(mc.scenario==row.scenario)&(mc.statistic==row.statistic)];assert len(g)==1000
        event=(g.ci_low<=0)&(g.ci_high>=0) if row.event=='coverage' else g['p_adjusted' if row.event=='adjusted_rejection' else 'p_centered']<.05;check_rate(event,row)
    for row in families.itertuples():
        g=mc[(mc.mechanism==row.mechanism)&(mc.family==row.family)];check_rate(g.assign(reject=g['p_adjusted' if row.adjusted else 'p_centered']<.05).groupby('replication').reject.any(),row)
    counts=[]
    for s,f in [('early',before),('late',recent)]:
        for t in names['decada']:
            m=f['^BVSP'];on=f[t].notna()&m.ne(0);counts.append(dict(period=s,ticker=t,n_pairs=int(on.sum()),n_plus=int((on&m.gt(0)).sum()),n_minus=int((on&m.lt(0)).sum()),n_missing=int(f[t].isna().sum())))
    pd.DataFrame(counts).to_csv(out/'temporal_observations.csv',index=False)
    result=dict(passed=True,production_G_imports=False,explicit_bootstrap_statistics=checked,max_explicit_difference=maxdiff,complete_draw_rows=len(actual),calibration_replication_rows=len(mc),independently_recomputed_rate_rows=len(cases)+len(families),scope='numerical consistency and summary audit; not a general size or coverage theorem')
    (out/'independent_verification.json').write_text(json.dumps(result,indent=2)+'\n');return result


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--x-archive',required=True,type=Path);p.add_argument('--output',required=True,type=Path);a=p.parse_args()
    with threadpool_limits(limits=1):print(json.dumps(verify(Path(__file__).resolve().parents[1],a.x_archive,a.output),indent=2))
