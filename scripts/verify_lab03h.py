#!/usr/bin/env python3
"""Independent explicit-row OLS/bootstrap and diagnostics; no H/G/F imports."""
import argparse,hashlib,json,zipfile
from pathlib import Path
import numpy as np
import pandas as pd
from threadpoolctl import threadpool_limits

ROOT=Path(__file__).resolve().parents[1]


def adjusted(p):
    p=np.array(p);ix=np.argsort(p);ans=np.empty(len(p));ans[ix]=np.minimum(1,np.maximum.accumulate(p[ix]*np.arange(len(p),0,-1)));return ans


def verify(x,out):
    lock=json.loads((ROOT/'data/lab03h/inputs_manifest.json').read_text());assert hashlib.sha256(x.read_bytes()).hexdigest()==lock['x_sha256']
    for n,h in lock['source_pins'].items():assert hashlib.sha256((ROOT/n).read_bytes()).hexdigest()==h,n
    with zipfile.ZipFile(x) as z:
        mats={s:pd.read_csv(z.open(f'matrices/referencia_n/{s}/retornos_logaritmicos.csv.gz'),compression='gzip',index_col=0,parse_dates=True,float_precision='round_trip') for s in ['decada','recente']}
    before=mats['decada'].loc[:'2020-12-31'];late=mats['recente'];fp=json.loads((ROOT/'data/lab03f/plano_pos_parecer_v1.json').read_text());meta=pd.read_csv(ROOT/fp['metadata_path']);names=list(meta[meta.scenario.eq('decada')].sort_values('papel_id').ticker);B=4999;R=3
    records=pd.read_csv(out/'period_observations.csv',float_precision='round_trip');maximum=0.
    def full_OLS(frame,ticker,ix):
        m=frame['^BVSP'].to_numpy()[ix];y=frame[ticker].to_numpy()[ix];on=np.isfinite(y)&np.isfinite(m)&(m!=0);D=m>0;X=np.column_stack([np.ones(len(m)),D,m,D*m]);b=np.linalg.lstsq(X[on],y[on],rcond=None)[0];return np.array([b[2]+b[3],b[2],b[0]+b[1],b[0],b[3],b[1]])
    def mask(frame,profile):
        keep=np.ones(len(frame),bool)
        if profile=='exclude_2020_03':keep=~((frame.index.year==2020)&(frame.index.month==3))
        if profile=='exclude_2020_H1':keep=~((frame.index.year==2020)&(frame.index.month<=6))
        return np.asarray(keep)
    for row in records.itertuples():
        frame=before if row.period=='early' else late;keep=mask(frame,row.profile) if row.period=='early' else np.ones(len(frame),bool);ix=np.flatnonzero(keep);expected=full_OLS(frame,row.ticker,ix);actual=np.array([row.beta_plus,row.beta_minus,row.alpha_plus,row.alpha_minus,row.delta,row.intercept_jump]);np.testing.assert_allclose(actual,expected,atol=1e-10,rtol=1e-9);maximum=max(maximum,float(abs(actual-expected).max()))
        m=frame['^BVSP'].to_numpy();valid=keep&np.isfinite(frame[row.ticker])&(m!=0);assert (int(valid.sum()),int((valid&(m>0)).sum()),int((valid&(m<0)).sum()))==(row.n_pairs,row.n_plus,row.n_minus)
    def block_indices(N,L,rng):
        starts=rng.integers(0,N-L+1,size=(B,(N+L-1)//L));return (starts[:R,:,None]+np.arange(L)).reshape(R,-1)[:,:N]
    bank=np.load(out/'crisis_draws.npz');boot_max=0.;checked=0
    for L in [21,5,63]:
        rid=block_indices(len(late),L,np.random.default_rng(np.random.SeedSequence([fp['bootstrap']['seed'],L,1])))
        for pi,profile in [(1,'exclude_2020_03'),(2,'exclude_2020_H1')]:
            keep=mask(before,profile);ix=np.flatnonzero(keep);segments=np.split(ix,np.flatnonzero(np.diff(ix)>1)+1);rng=np.random.default_rng(np.random.SeedSequence([fp['bootstrap']['seed'],L,2,pi]));draws=[seg[block_indices(len(seg),L,rng)] for seg in segments];early=np.column_stack(draws);assert keep[early].all()
            for b in range(R):
                theta=np.array([full_OLS(late,t,rid[b])[4]-full_OLS(before,t,early[b])[4] for t in names])
                for stat,fn in [('mean',np.mean),('median',np.median)]:
                    a=bank[f'{profile}_{stat}_L{L}'][b];e=fn(theta);np.testing.assert_allclose(a,e,atol=1e-10,rtol=1e-9);boot_max=max(boot_max,abs(a-e));checked+=1
    aggregate=pd.read_csv(out/'crisis_aggregate.csv.gz',float_precision='round_trip')
    for row in aggregate.itertuples():
        b=bank[f'{row.profile}_{row.statistic}_L{row.block}'];err=b-row.estimate;lo,hi=np.quantile(err,[.025,.975]);p=(1+(abs(err)>=abs(row.estimate)).sum())/5000;assert row.invalid_draws==0;np.testing.assert_allclose([row.p_centered,row.ci_low,row.ci_high,row.bootstrap_mean,row.bootstrap_se],[p,row.estimate-hi,row.estimate-lo,b.mean(),b.std(ddof=1)],atol=1e-12,rtol=1e-9)
    for _,a in aggregate.groupby('block'):np.testing.assert_allclose(a.p_holm4,adjusted(a.p_centered),atol=1e-12)
    cdf=pd.read_csv(out/'cdf_diagnostics.csv',float_precision='round_trip');mc=pd.read_csv(ROOT/'results/tables/lab03g_pos_parecer_v3_20261024/calibration_replications.csv.gz',float_precision='round_trip')
    for row in cdf.itertuples():
        a=mc[mc.mechanism.eq(row.mechanism)&mc.family.eq(row.family)&mc.profile.eq(row.profile)&mc.scenario.eq(row.scenario)&mc.statistic.eq(row.statistic)];assert len(a)==1000;k=int(a.p_centered.le(row.observed_p).sum());assert k==row.null_tail_count;np.testing.assert_allclose(row.p_calibrated_diagnostic,(k+1)/1001,atol=1e-14)
    for _,a in cdf.groupby(['mechanism','family']):np.testing.assert_allclose(a.p_calibrated_Holm_diagnostic,adjusted(a.p_calibrated_diagnostic),atol=1e-12)
    # Independent dense Toeplitz covariance, rather than production lfilter.
    frame=mats['decada'];m=frame['^BVSP'].to_numpy();Y=frame[names].to_numpy();P=np.zeros_like(Y)
    for j,t in enumerate(names):
        for s,sgn in [(m>0,1.),(m<0,-1.)]:
            on=s&np.isfinite(Y[:,j]);X=np.column_stack([np.ones(on.sum()),m[on]]);P[on,j]+=sgn*np.linalg.pinv(X)[1]
    sigma=pd.read_csv(ROOT/'results/tables/lab03e_colab_20261023/asset_nuisance.csv.gz').set_index('ticker').loc[names,'sigma'].to_numpy();A=P*sigma[None,:]/80;h=np.sqrt(.5+.5*np.r_[m[0],m[:-1]]**2/np.mean(m*m));h/=np.linalg.norm(h)/np.sqrt(len(h));b=np.where(frame.index>=pd.Timestamp('2020-01-01'),2.,1.);b/=np.linalg.norm(b)/np.sqrt(len(b));sd=pd.read_csv(out/'scale_diagnostics.csv');distance=abs(np.arange(len(m))[:,None]-np.arange(len(m)))
    for name,scale,phi in [('gaussian_iid',np.ones(len(h)),0),('student_hetero',h,0),('student_ar',h,.3),('variance_break_t5',h*b,.3),('ar06_t5',h,.6)]:
        K=phi**distance;V=A*scale[:,None];c=V.sum(1);variance=.3*(c@K@c)+.7*np.sum(V*(K@V));expected=np.sqrt(variance);actual=sd[sd.mechanism.eq(name)].iloc[0].analytic_conditional_sd;np.testing.assert_allclose(actual,expected,atol=1e-11,rtol=1e-9)
    points=pd.read_csv(out/'crisis_asset_points.csv');economic=pd.read_csv(out/'economic_scale.csv');shocks=[-.05,-.01,.01,.05];assert len(economic)==1920
    lookup=points.set_index(['profile','papel_id'])
    for row in economic.itertuples():
        point=lookup.loc[(row.profile,row.papel_id)];market=np.log1p(row.simple_market_shock);delta=point['delta_'+row.period];jump=point['intercept_jump_'+row.period];np.testing.assert_allclose([row.log_market,row.down_minus_up_linear_log,row.down_minus_up_full_projection_log],[market,-delta*market,-delta*market-jump],atol=1e-12)
    sector=pd.read_csv(out/'sector_summary.csv');original=pd.read_csv(ROOT/'results/tables/lab03b_colab_20261023/sector_point.csv');pd.testing.assert_frame_equal(sector,original,check_exact=False,atol=1e-12)
    result=dict(passed=True,production_H_G_F_imports=False,explicit_period_OLS=480,max_OLS_difference=maximum,explicit_bootstrap_statistics=checked,max_bootstrap_difference=boot_max,complete_bootstrap_statistic_rows=12,CDF_rows_recomputed=84,dense_covariance_cases=5,economic_rows_checked=1920,prior_source_pins=len(lock['source_pins']),scope='numerical/method consistency;does not validate new masked-bootstrap size/coverage or CDF replacement')
    (out/'independent_verification.json').write_text(json.dumps(result,indent=2)+'\n');return result


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--x-archive',required=True,type=Path);p.add_argument('--output',required=True,type=Path);a=p.parse_args()
    with threadpool_limits(limits=1):print(json.dumps(verify(a.x_archive,a.output),indent=2))
