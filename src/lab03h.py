"""Post-fourth-review crisis contrasts and read-only calibration diagnostics.

Frozen F/G code and banks are reused. No quotation downloads, filling,
annual reselection, new Monte Carlo generators or posthoc primary replacement.
"""
import hashlib,json,gc
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.signal import lfilter
from scipy.stats import norm
from lab02 import holm
from lab03f import profile_data
from lab03g import load as load_g,PanelOperator,f_counts,statistics

GDIR='results/tables/lab03g_pos_parecer_v3_20261024/'
FDIR='results/tables/lab03f_pos_parecer_20261024/'
BDIR='results/tables/lab03b_colab_20261023/'


def digest(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def load(root,x):
    lock=json.loads((root/'data/lab03h/inputs_manifest.json').read_text())
    assert digest(root/'data/lab03h/plano_v1.json')==lock['plan_sha256']
    for n,h in lock['source_pins'].items():assert digest(root/n)==h,n
    assert digest(x)==lock['x_sha256']
    gp,fp,mats,samples=load_g(root,x)
    return json.loads((root/'data/lab03h/plano_v1.json').read_text()),fp,mats,samples


def period_fits(frame,tickers,keep=None):
    m=frame['^BVSP'].to_numpy();keep=np.ones(len(m),bool) if keep is None else np.asarray(keep,bool);eligible=keep&np.isfinite(m)&(m!=0);rows=[]
    for ticker in tickers:
        y=frame[ticker].to_numpy();on=eligible&np.isfinite(y);row=dict(ticker=ticker,n_target=int(keep.sum()),n_eligible=int(eligible.sum()),n_pairs=int(on.sum()),n_missing=int((eligible&~np.isfinite(y)).sum()),n_plus=int((on&(m>0)).sum()),n_minus=int((on&(m<0)).sum()),coverage=float(on.sum()/eligible.sum()))
        assert row['n_pairs']>=200 and min(row['n_plus'],row['n_minus'])>=60 and row['coverage']>=.95
        for sign,mask in [('plus',m>0),('minus',m<0)]:
            ix=on&mask;center=m[ix]-m[ix].mean();assert np.var(m[ix],ddof=1)>1e-12
            b=float(center@(y[ix]-y[ix].mean())/(center@center));row['beta_'+sign]=b;row['alpha_'+sign]=float(y[ix].mean()-b*m[ix].mean())
        row['delta']=row['beta_plus']-row['beta_minus'];row['intercept_jump']=row['alpha_plus']-row['alpha_minus'];rows.append(row)
    return pd.DataFrame(rows)


def crisis(root,plan,fp,mats,samples,out):
    before=mats['decada'].loc[:'2020-12-31'];recent=mats['recente'];names=list(samples['decada'].ticker);meta=samples['decada'][['papel_id','ticker','setor_economico']]
    baseline=pd.read_csv(root/GDIR/'observed_aggregate.csv.gz',float_precision='round_trip');frozen=np.load(root/GDIR/'observed_draws.npz');rows=[];draws={};periods=[];points=[]
    latefits=period_fits(recent,names)
    for profile in ['daily',*plan['crisis_theta']['profiles']]:
        _,keep=profile_data(before,profile);earlyfits=period_fits(before,names,keep)
        wide=meta.merge(earlyfits,on='ticker',validate='one_to_one').merge(latefits,on='ticker',suffixes=('_early','_late'),validate='one_to_one');wide['profile']=profile;wide['theta']=wide.delta_late-wide.delta_early;points.append(wide)
        for period,q in [('early',earlyfits),('late',latefits)]:q=q.copy();q['profile']=profile;q['period']=period;periods.append(q)
    for L in [21,5,63]:
        counts=f_counts(fp,mats,L);late=PanelOperator(recent,names,counts['recent']);lp,lb=late.evaluate()
        for profile in ['daily',*plan['crisis_theta']['profiles']]:
            _,keep=profile_data(before,profile);early=PanelOperator(before,names,counts['early'] if profile=='daily' else counts[profile][:,:len(before)],keep);ep,eb=early.evaluate();stats=statistics(lp-ep,lb-eb)
            for stat,q in stats.items():
                if profile=='daily':
                    r=baseline[baseline.profile.eq('theta')&baseline.block.eq(L)&baseline.statistic.eq(stat)].iloc[0];np.testing.assert_allclose([q['estimate'][0],q['ci_low'][0],q['ci_high'][0],q['p_centered'][0]],[r.estimate,r.ci_low,r.ci_high,r.p_centered],atol=1e-10,rtol=1e-9);np.testing.assert_allclose(q['draws'][:,0],frozen[f'theta_decada_{stat}_L{L}'],atol=1e-10,rtol=1e-9)
                else:
                    row=dict(profile=profile,statistic=stat,block=L,B=4999,assets=80,family='crisis_theta_Holm4',interval='basic_nominal95_not_coverage_validated_for_this_new_mask');row.update({k:float(v[0]) for k,v in q.items() if k!='draws'});row['status']='estimated' if row['invalid_draws']==0 else 'inference_withheld_invalid_draws';rows.append(row);draws[f'{profile}_{stat}_L{L}']=q['draws'][:,0]
            del early,eb;gc.collect()
        del counts,late,lb;gc.collect();print(f'H crisis block{L}: four new targets; G baseline and all paired draws reproduced',flush=True)
    frame=pd.DataFrame(rows)
    for _,a in frame.groupby('block'):assert len(a)==4;frame.loc[a.index,'p_holm4']=holm(a.p_centered,4)
    frame.to_csv(out/'crisis_aggregate.csv.gz',index=False,compression={'method':'gzip','mtime':0});np.savez_compressed(out/'crisis_draws.npz',**draws)
    point=pd.concat(points,ignore_index=True);point.to_csv(out/'crisis_asset_points.csv',index=False);pd.concat(periods,ignore_index=True).to_csv(out/'period_observations.csv',index=False)
    return frame,point


def tail_rate(k,n):
    p=k/n;z=norm.ppf(.975);den=1+z*z/n;c=(p+z*z/(2*n))/den;r=z*np.sqrt(p*(1-p)/n+z*z/(4*n*n))/den
    return dict(tail_rate=p,tail_mcse=np.sqrt(p*(1-p)/n),tail_prob_wilson_low=max(0,c-r),tail_prob_wilson_high=min(1,c+r))


def cdf_family(observed,null):
    rows=[]
    for r in observed.itertuples():
        a=null[null.profile.eq(r.profile)&null.scenario.eq(r.scenario)&null.statistic.eq(r.statistic)];R=len(a);assert R>0
        k=int(a.p_centered.le(r.p_centered).sum());rows.append(dict(profile=r.profile,scenario=r.scenario,statistic=r.statistic,observed_p=r.p_centered,null_tail_count=k,R=R,p_calibrated_diagnostic=(k+1)/(R+1),**tail_rate(k,R)))
    for r,p in zip(rows,holm([a['p_calibrated_diagnostic'] for a in rows],len(rows))):r['p_calibrated_Holm_diagnostic']=p
    return rows


def conditional_variance(A,h,phi,rho=.3):
    """Variance of mean contrast for shared stationary AR factor/idiosyncrasy."""
    B=A*h[:,None];c=B.sum(1);cs=lfilter([1],[1,-phi],c);bs=lfilter([1],[1,-phi],B,axis=0)
    return float(rho*(2*(c@cs)-c@c)+(1-rho)*(2*np.sum(B*bs)-np.sum(B*B)))


def calibration_diagnostics(root,mats,samples,out):
    mc=pd.read_csv(root/GDIR/'calibration_replications.csv.gz',float_precision='round_trip');f=pd.read_csv(root/FDIR/'aggregate.csv.gz',float_precision='round_trip');f=f[f.block.eq(21)].copy();f['family']='F'
    g=pd.read_csv(root/GDIR/'observed_aggregate.csv.gz',float_precision='round_trip');g=g[g.family.eq('temporal4')&g.block.eq(21)].copy();g['family']='temporal';obs=pd.concat([f,g],ignore_index=True);assert len(mc)==84000 and len(obs)==14
    cdf=[];coverage=[];scales=[]
    for mechanism in mc.mechanism.unique():
        a=mc[mc.mechanism.eq(mechanism)]
        for family,q in obs.groupby('family'):
            n=a[a.family.eq(family)];rows=cdf_family(q,n)
            for row in rows:assert row['R']==1000;row.update(mechanism=mechanism,family=family,scope='exploratory_existing_bank_global_null_not_validated_replacement')
            cdf+=rows
        for keys,q in a.groupby(['family','profile','scenario','statistic']):coverage.append(dict(mechanism=mechanism,family=keys[0],profile=keys[1],scenario=keys[2],statistic=keys[3],R=len(q),coverage=((q.ci_low<=0)&(q.ci_high>=0)).mean(),raw_rejection=q.p_centered.lt(.05).mean(),adjusted_rejection=q.p_adjusted.lt(.05).mean()))
        q=a[a.family.eq('F')&a.profile.eq('daily')&a.scenario.eq('decada')&a.statistic.eq('mean')];scales.append(dict(mechanism=mechanism,sd_estimator=q.estimate.std(ddof=1),mean_bootstrap_se=q.bootstrap_se.mean(),sd_over_mean_se=q.estimate.std(ddof=1)/q.bootstrap_se.mean(),coverage=((q.ci_low<=0)&(q.ci_high>=0)).mean(),raw_rejection=q.p_centered.lt(.05).mean()))
    cdf=pd.DataFrame(cdf);assert len(cdf)==84;cdf.to_csv(out/'cdf_diagnostics.csv',index=False);pd.DataFrame(coverage).to_csv(out/'coverage_by_target.csv',index=False)
    frame=mats['decada'];market=frame['^BVSP'].to_numpy();names=list(samples['decada'].ticker);Y=frame[names].to_numpy();W=np.zeros_like(Y)
    for j in range(80):
        for on,mult in [(market>0,1.),(market<0,-1.)]:
            on=on&np.isfinite(Y[:,j]);v=market[on]-market[on].mean();W[on,j]+=mult*v/(v@v)
    h=np.sqrt(.5+.5*np.r_[market[0],market[:-1]]**2/np.mean(market**2));h/=np.sqrt(np.mean(h*h));b=np.where(frame.index>=pd.Timestamp('2020-01-01'),2.,1.);b/=np.sqrt(np.mean(b*b))
    normal=[]
    for component,scale in [('hetero_h',h),('break_factor',b),('break_product',h*b)]:
        for period,on in [('full',np.ones(len(h),bool)),('early',frame.index.year<2021),('late',frame.index.year>=2021)]:normal.append(dict(component=component,period=period,mean_square=np.mean(scale[on]**2),rms=np.sqrt(np.mean(scale[on]**2))))
    pd.DataFrame(normal).to_csv(out/'normalization.csv',index=False)
    nuisance=pd.read_csv(root/'results/tables/lab03e_colab_20261023/asset_nuisance.csv.gz').set_index('ticker');A=W*nuisance.loc[names,'sigma'].to_numpy()[None,:]/80
    methods=[('gaussian_iid',np.ones(len(h)),0),('student_hetero',h,0),('student_ar',h,.3),('variance_break_t5',h*b,.3),('ar06_t5',h,.6)];analytic={name:np.sqrt(conditional_variance(A,s,phi)) for name,s,phi in methods}
    observed_se=float(f[f.profile.eq('daily')&f.scenario.eq('decada')&f.statistic.eq('mean')].iloc[0].bootstrap_se)
    for row in scales:row.update(observed_bootstrap_se=observed_se,sd_over_observed_se=row['sd_estimator']/observed_se,analytic_conditional_sd=analytic.get(row['mechanism'],np.nan),analytic_scope='fixed_market_masks_scales_AR_stationary_covariance;not_GARCH;burn_error_negligible')
    pd.DataFrame(scales).to_csv(out/'scale_diagnostics.csv',index=False)
    concentration=[]
    for name,scale in [('unit',np.ones(len(h))),('hetero_h',h),('break_product',h*b)]:
        contribution=scale**2*(.3*A.sum(1)**2+.7*np.sum(A*A,axis=1));march=(frame.index>='2020-03-01')&(frame.index<='2020-03-31');concentration.append(dict(scale=name,variance_no_AR=contribution.sum(),march2020_share=contribution[march].sum()/contribution.sum(),march_sessions=int(march.sum()),total_sessions=len(frame),scope='variance_weight_concentration_not_causal_attribution'))
    pd.DataFrame(concentration).to_csv(out/'variance_concentration.csv',index=False)
    return cdf


def economic_rows(point,shocks):
    rows=[]
    for r in point.itertuples():
        for period in ['early','late']:
            delta=getattr(r,'delta_'+period);jump=getattr(r,'intercept_jump_'+period)
            for shock in shocks:
                m=float(np.log1p(shock));linear=-delta*m;rows.append(dict(profile=r.profile,papel_id=r.papel_id,ticker=r.ticker,period=period,simple_market_shock=shock,log_market=m,down_minus_up_linear_log=linear,down_minus_up_intercept_log=-jump,down_minus_up_full_projection_log=linear-jump,scope='algebraic_asset_projection_components_one_regime_extrapolated_no_portfolio_or_expected_loss'))
    return pd.DataFrame(rows)


def presentation_inputs(root,point,plan,out):
    economic_rows(point,plan['economic_scale']['simple_market_shocks']).to_csv(out/'economic_scale.csv',index=False)
    annual=pd.read_csv(root/'results/tables/lab03_colab_20261023/annual_primary.csv.gz');risk=pd.read_csv(root/BDIR/'risk_annual.csv.gz');rows=[]
    for (scenario,year),a in annual[annual.scenario.isin(['decada','recente'])].groupby(['scenario','year']):
        N=80 if scenario=='decada' else 117;assert len(a)==N
        q=risk[risk.scenario.eq(scenario)&risk.year.eq(year)&risk.cash_variant.eq('referencia_n')];assert len(q)==N
        d=a.loc[a.status_conditional.eq('ok'),'delta'];e=q.loc[q.status.eq('ok'),'es95_simple_loss'];row=dict(scenario=scenario,year=year,fixed_assets=N,estimated_delta=len(d),estimated_ES=len(e))
        for name,v in [('delta',d),('es95',e)]:row.update({name+'_median':v.median(),name+'_q25':v.quantile(.25),name+'_q75':v.quantile(.75)})
        rows.append(row)
    pd.DataFrame(rows).to_csv(out/'annual_overview.csv',index=False)
    g=pd.read_csv(root/GDIR/'observed_aggregate.csv.gz');g=g[g.family.eq('micro18')].copy();i=pd.read_csv(root/FDIR/'individual.csv.gz');counts=i.groupby(['profile','scenario']).n_pairs.agg(['min','median','max']).rename(columns={'min':'n_min','median':'n_median','max':'n_max'}).reset_index();g=g.merge(counts,on=['profile','scenario'],validate='many_to_one');g.to_csv(out/'microstructure_raw_and_adjusted.csv',index=False)
    pd.read_csv(root/BDIR/'sector_point.csv').to_csv(out/'sector_summary.csv',index=False)
