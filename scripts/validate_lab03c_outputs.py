#!/usr/bin/env python3
"""Independent full-design oracle and complete recalculation of MC summaries.

Does not import lab03c or production inference functions.
"""
import os, argparse, hashlib, json, zipfile, sys
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.stats import norm

ROOT=Path(__file__).resolve().parents[1]

def validate(output, x_archive):
    plan=json.loads((ROOT/'data/lab03c/plano_v1.json').read_text())
    lock=json.loads((ROOT/'data/lab03c/inputs_manifest.json').read_text())
    assert hashlib.sha256(x_archive.read_bytes()).hexdigest()==lock['x_sha256']
    assert hashlib.sha256((ROOT/'data/lab03c/plano_v1.json').read_bytes()).hexdigest()==lock['plan_sha256']
    z=zipfile.ZipFile(x_archive)
    mats={s:pd.read_csv(z.open(f'matrices/referencia_n/{s}/retornos_logaritmicos.csv.gz'),compression='gzip',index_col=0,parse_dates=True,float_precision='round_trip') for s in ['decada','recente']}
    design=pd.read_csv(output/'design.csv'); nuisance=pd.read_csv(output/'asset_nuisance.csv')
    assert len(design)==197 and len(nuisance)==117
    pd.testing.assert_frame_equal(mats['decada'].loc[mats['recente'].index],mats['recente'][mats['decada'].columns],check_exact=True)
    assert [int(mats[s].isna().sum().sum()) for s in ['decada','recente']]==[7,7]
    for row in nuisance.itertuples():
        mat=mats[row.calibration_period];ok=mat[row.ticker].notna() & mat['^BVSP'].notna()
        mm=mat.loc[ok,'^BVSP'].to_numpy();yy=mat.loc[ok,row.ticker].to_numpy()
        Xn=np.column_stack([np.ones(len(mm)),mm]);bn=np.linalg.lstsq(Xn,yy,rcond=None)[0]
        sn=np.sqrt(np.sum((yy-Xn@bn)**2)/(len(mm)-2))
        np.testing.assert_allclose([row.beta_base,row.sigma],[bn[1],sn],rtol=1e-12,atol=1e-14)
    a=np.load(output/'replicates.npz'); err=a['error']; ses=a['se']
    assert err.shape==(3,1000,197) and ses.shape==(3,3,1000,197)
    assert np.isfinite(err).all() and np.isfinite(ses).all() and (ses>0).all()
    m=mats['decada']['^BVSP'].to_numpy(); lag=np.r_[m[0],m[:-1]]
    h=np.sqrt(.5+.5*lag**2/np.mean(m*m));h/=np.sqrt(np.mean(h*h))
    largest_beta=largest_se=0.; fits=0
    for mi in range(3):
        rng=np.random.default_rng(np.random.SeedSequence([20261023,mi,0]));shape=(len(m)+256,118)
        zz=rng.standard_normal(shape) if mi==0 else rng.standard_t(5,shape)*np.sqrt(.6)
        innov=np.sqrt(.3)*zz[:,:1]+np.sqrt(.7)*zz[:,1:]
        phi=0 if mi<2 else .3; u=np.zeros_like(innov); previous=np.zeros(117)
        for t in range(len(u)):
            u[t]=phi*previous+np.sqrt(1-phi**2)*innov[t];previous=u[t]
        noise=u[256:]*(1 if mi==0 else h[:,None])*nuisance.sigma.to_numpy()
        for j,row in enumerate(design.itertuples()):
            mat=mats[row.scenario]; market=mat['^BVSP'].to_numpy(); valid=mat[row.ticker].notna().to_numpy() & np.isfinite(market)
            assert hashlib.sha256(valid.tobytes()).hexdigest()==row.valid_mask_sha256
            assert valid.sum()==row.n_pairs
            on=valid & (market!=0); D=(market>0).astype(float)
            X=np.column_stack([np.ones(len(market)),D,market,D*market])
            ti=mats['decada'].index.get_indexer(mat.index)
            ni=int(row.master_asset_index); base=float(nuisance.iloc[ni].beta_base)
            # Inject an asymmetry and distinct intercepts; these must leave covariance unchanged.
            y=.015-.02*D+base*market+.25*D*market+noise[ti,ni]
            co=np.linalg.lstsq(X[on],y[on],rcond=None)[0]; bread=np.linalg.inv(X[on].T@X[on])
            score=np.zeros_like(X); score[on]=X[on]*(y[on]-X[on]@co)[:,None]
            for li,L in enumerate([0,5,20]):
                meat=score.T@score
                for ell in range(1,L+1):
                    cross=score[ell:].T@score[:-ell];meat+=(1-ell/(L+1))*(cross+cross.T)
                cov=bread@meat@bread*(on.sum()/(on.sum()-4));se=np.sqrt(cov[3,3])
                db=abs(co[3]-(err[mi,0,j]+.25)); ds=abs(se-ses[mi,li,0,j])
                largest_beta=max(largest_beta,db);largest_se=max(largest_se,ds)
                np.testing.assert_allclose(co[3],err[mi,0,j]+.25,rtol=1e-9,atol=1e-11)
                np.testing.assert_allclose(se,ses[mi,li,0,j],rtol=1e-9,atol=1e-12);fits+=1
    cal=pd.read_csv(output/'calibration.csv'); power=pd.read_csv(output/'power.csv'); fam=pd.read_csv(output/'family.csv');pan=pd.read_csv(output/'panel_summary.csv')
    assert list(map(len,[cal,power,fam,pan]))==[1773,15957,81,162]
    Z=norm.ppf(.975);R=1000; comparisons=0
    def same(actual,expected):
        nonlocal comparisons
        np.testing.assert_allclose(actual,expected,rtol=1e-10,atol=1e-12,equal_nan=True);comparisons+=np.size(expected)
    def bern(ev):
        p=ev.mean(axis=0);se=np.sqrt(p*(1-p)/R);den=1+Z*Z/R
        center=(p+Z*Z/(2*R))/den;rad=Z*np.sqrt(p*(1-p)/R+Z*Z/(4*R*R))/den
        return [p,se,np.maximum(0,center-rad),np.minimum(1,center+rad)]
    def panel(ev):
        if ev.shape[1]==0:return [np.nan,np.nan]
        v=ev.mean(axis=1);return [v.mean(),v.std(ddof=1)/np.sqrt(R)]
    pattern_list=[(f'dense_{v:+.2f}',np.full(197,v)) for v in plan['effect_patterns']['dense_delta']]
    selected=set(nuisance.papel_id[:12])
    pattern_list += [(f'sparse_{v:+.2f}',np.where(design.papel_id.isin(selected),v,0)) for v in plan['effect_patterns']['sparse_delta']]
    for mi,spec in enumerate(plan['mechanisms']):
        for li,L in enumerate([0,5,20]):
            method=f'HAC{L}'; E=err[mi];S=ses[mi,li];cover=np.abs(E)<=Z*S
            subset=cal[cal.mechanism.eq(spec['name']) & cal.method.eq(method)]
            for name,values in dict(bias=E.mean(0),bias_mcse=E.std(0,ddof=1)/np.sqrt(R),rmse=np.sqrt((E*E).mean(0)),empirical_se=E.std(0,ddof=1),mean_model_se=S.mean(0)).items():same(subset[name],values)
            for name,values in zip(['coverage','coverage_mcse','coverage_mc_low','coverage_mc_high'],bern(cover)):same(subset[name],values)
            for pat,truth in pattern_list:
                p=2*norm.sf(np.abs((E+truth)/S));raw=p<.05
                # Independent scalar row-wise Holm implementation.
                adjusted=np.empty_like(p)
                for ri in range(R):
                    order=np.argsort(p[ri],kind='stable');last=0.
                    for k,j in enumerate(order):
                        last=max(last,min(1.,(197-k)*p[ri,j]));adjusted[ri,j]=last
                rej=adjusted<.05;null=truth==0
                sel=lambda df:df[df.mechanism.eq(spec['name']) & df.method.eq(method) & df.pattern.eq(pat)]
                rows=sel(power)
                same(rows.true_delta,truth)
                for prefix,ev in [('raw',raw),('holm',rej)]:
                    for name,values in zip([prefix+'_rejection',prefix+'_mcse',prefix+'_mc_low',prefix+'_mc_high'],bern(ev)):same(rows[name],values)
                f=sel(fam).iloc[0];assert f.null_cases==null.sum() and f.nonnull_cases==(~null).sum()
                for prefix,ev in [('fwer_raw',raw),('fwer_holm',rej)]:
                    vals=bern(ev[:,null].any(1)) if null.any() else [np.nan]*4
                    for key,value in zip([prefix,prefix+'_mcse',prefix+'_mc_low',prefix+'_mc_high'],vals):same(f[key],value)
                same([f.power_holm,f.power_holm_mcse],panel(rej[:,~null]))
                for scenario in ['decada','recente']:
                    ix=design.scenario.eq(scenario).to_numpy();q=sel(pan);q=q[q.scenario.eq(scenario)].iloc[0]
                    for key,ev,mask in [('coverage',cover,ix),('power_raw',raw,ix&~null),('power_holm',rej,ix&~null),('type1_raw',raw,ix&null),('type1_holm',rej,ix&null)]:same([q[key],q[key+'_mcse']],panel(ev[:,mask]))
    receipt=dict(status='passed',independent_of_production_imports=True,full_design_oracle_fits=fits,injected_delta=.25,max_coefficient_absolute_difference=largest_beta,max_se_absolute_difference=largest_se,summary_numeric_values_recalculated=int(comparisons),rows=[1773,15957,81,162],missing_cells_decade=7,missing_cells_recent=7,temporal_family_474_calibrated=False,environment=os.environ.get('ALEM_BETA_EXECUTION_ENV','local preparation'))
    (output/'validacao_independente.json').write_text(json.dumps(receipt,indent=2)+'\n'); print(json.dumps(receipt,indent=2));return receipt

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--x-archive',type=Path,required=True);a=p.parse_args();validate(a.output,a.x_archive)
