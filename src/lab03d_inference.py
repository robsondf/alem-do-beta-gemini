"""Complementary leverage/dependent-score inference; historical primary unchanged."""
import json
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.signal import lfilter
from scipy.stats import norm
from threadpoolctl import threadpool_limits
from lab03c import prepare, archive, kernel, draw_errors, patterns, holm_rows, probability, panel_rate, Z

METHODS=('HAC5_Holm','HC3_HAC5_Holm','HC3_HAC5_maxT')
VARIANTS=('referencia_n','jcp_duas_celulas_documentadas','jcp_condicional','jcp_rendimento_caixa_baixo','jcp_rendimento_caixa_alto')

def load(root,x,b):
    lock=json.loads((root/'data/lab03d/inputs_manifest.json').read_text())
    d=prepare(x,b,lock)
    with archive(x,lock['x_sha256']) as z:
        d['matrices']={v:{s:pd.read_csv(z.open(f'matrices/{v}/{s}/retornos_logaritmicos.csv.gz'),compression='gzip',index_col=0,parse_dates=True,float_precision='round_trip') for s in ['decada','recente']} for v in VARIANTS}
    for v in VARIANTS:
        for scenario in ['decada','recente']:
            q=d['matrices'][v][scenario];ref=d['matrices']['referencia_n'][scenario]
            assert q.index.equals(ref.index) and list(q.columns)==list(ref.columns)
            assert q.index.is_monotonic_increasing
            np.testing.assert_array_equal(q['^BVSP'].to_numpy(),ref['^BVSP'].to_numpy())
            np.testing.assert_array_equal(q.isna().to_numpy(),ref.isna().to_numpy())
    master=d['matrices']['referencia_n']['decada'].index;d['dates']=master
    annual=[];groups=[];index={};offset=0
    for year in range(2016,2026):
        panel=d['panels'][0 if year<2021 else 1];sample=panel['sample'];mat=d['matrices']['referencia_n'][panel['scenario']];mat=mat[mat.index.year==year]
        m=mat['^BVSP'].to_numpy();valid=np.isfinite(mat[sample.ticker].to_numpy());k=kernel(m,valid)
        groups.append(dict(kernel=k,time_index=master.get_indexer(mat.index),asset_index=panel['asset_index'],offset=offset))
        for j,row in enumerate(sample.itertuples()):
            index[(row.papel_id,year)]=offset+j
            annual.append(dict(year=year,papel_id=row.papel_id,ticker=row.ticker,n_pairs=int(valid[:,j].sum()),n_plus=int(k['plus'][1][j]),n_minus=int(k['minus'][1][j])))
        offset+=len(sample)
    assert offset==985
    amap=np.full((197,10),-1,int)
    for j,row in enumerate(d['design'].itertuples()):
        yrs=range(2016 if row.scenario=='decada' else 2021,2026)
        amap[j,:len(yrs)]=[index[(row.papel_id,y)] for y in yrs]
    theta=[];long=d['panels'][0];mat=d['matrices']['referencia_n']['decada']
    for early in [True,False]:
        q=mat[(mat.index.year<=2020)==early];m=q['^BVSP'].to_numpy();valid=np.isfinite(q[long['sample'].ticker].to_numpy())
        theta.append(dict(kernel=kernel(m,valid),time_index=master.get_indexer(q.index),asset_index=long['asset_index']))
    d.update(annual_groups=groups,annual_design=pd.DataFrame(annual),annual_map=amap,theta_panels=theta)
    return d


def details(y,k):
    valid=k['valid'];yy=np.where(valid,y,0.);fit=np.zeros_like(yy);lev=np.zeros_like(yy);co=[]
    for mask,n,mean,w in [k['plus'],k['minus']]:
        slope=np.sum(w*yy,axis=0);intercept=np.sum(np.where(mask,yy,0),axis=0)/n-slope*mean
        fit+=np.where(mask,intercept+slope*k['m'][:,None],0)
        center=np.where(mask,k['m'][:,None]-mean,0);ss=(center*center).sum(0)
        lev+=np.where(mask,1/n+center*center/ss,0)
        co.append((intercept,slope))
    if (lev>=1-1e-10).any():raise ArithmeticError('Near-unit leverage; no silent clipping')
    resid=np.where(valid,yy-fit,0);base=k['weights']*resid
    score=np.stack([base,base/(1-lev)])
    delta=np.sum(k['weights']*yy,axis=0)
    return delta,score,co,lev


def hac_variance(scores,L=5):
    v=np.einsum('...ij,...ij->...j',scores,scores)
    for h in range(1,L+1):v+=2*(1-h/(L+1))*np.einsum('...ij,...ij->...j',scores[...,h:,:],scores[...,:-h,:])
    if np.min(v)<-1e-12:raise ArithmeticError('Negative HAC variance')
    return np.maximum(v,0)


def static_project(d,noise):
    delta=[];ses=[];joint=np.zeros((len(d['market']),197));offset=0
    for p in d['panels']:
        y=noise[np.ix_(p['time_index'],p['asset_index'])];e,s,_,_=details(y,p['kernel'])
        s=s*np.sqrt(p['kernel']['correction'])[None,None,:]
        se=np.sqrt(hac_variance(s));delta.append(e);ses.append(se)
        joint[np.ix_(p['time_index'],np.arange(offset,offset+len(e)))]=s[1]
        offset+=len(e)
    return np.concatenate(delta),np.concatenate(ses,axis=1),joint


def multiplier_maxima(score,rng,B=999):
    # Moving sums including trailing padding exactly factor the Bartlett5 Toeplitz kernel.
    f=lfilter(np.ones(6)/np.sqrt(6),[1],np.pad(score,((0,5),(0,0))),axis=0)
    cov=f.T@f;sd=np.sqrt(np.diag(cov))
    if (sd<=1e-14).any():raise ArithmeticError('Degenerate multiplier score')
    corr=cov/sd[:,None]/sd[None,:];corr=(corr+corr.T)/2
    try:factor=np.linalg.cholesky(corr)
    except np.linalg.LinAlgError:
        val,vec=np.linalg.eigh(corr)
        if val.min()<-1e-10:raise ArithmeticError('Non-numerical non-PSD covariance')
        factor=vec*np.sqrt(np.maximum(val,0))[None,:]
    maxima=np.max(np.abs(rng.standard_normal((B,len(sd)))@factor.T),axis=1)
    critical=np.sort(maxima)[950]
    return critical,maxima,cov


def temporal_project(d,noise):
    annual=np.empty(985);ase=np.empty((2,985))
    for p in d['annual_groups']:
        y=noise[np.ix_(p['time_index'],p['asset_index'])];e,s,_,_=details(y,p['kernel']);n=len(e);i=p['offset']
        annual[i:i+n]=e;ase[:,i:i+n]=np.sqrt(hac_variance(s)*p['kernel']['correction'])
    vals=[];scores=np.zeros((2,len(d['market']),80));count=np.zeros(80)
    for h,p in enumerate(d['theta_panels']):
        e,s,_,_=details(noise[np.ix_(p['time_index'],p['asset_index'])],p['kernel']);vals.append(e)
        scores[:,p['time_index'],:]=(-1 if h==0 else 1)*s
        count+=p['kernel']['valid'].sum(0)
    tse=np.sqrt(hac_variance(scores)*(count/(count-8)))
    return annual,ase,vals[1]-vals[0],tse


def simulate(d,plan):
    R=plan['replications'];out={name:np.empty(shape) for name,shape in dict(error=(3,R,197),se=(3,2,R,197),critical=(3,R),annual_error=(3,R,985),annual_se=(3,2,R,985),theta_error=(3,R,80),theta_se=(3,2,R,80)).items()}
    with threadpool_limits(limits=1):
        for mi,spec in enumerate(plan['mechanisms']):
            for ri in range(R):
                noise=draw_errors(d,mi,ri,plan)
                e,se,s=static_project(d,noise);out['error'][mi,ri]=e;out['se'][mi,:,ri]=se
                rng=np.random.default_rng(np.random.SeedSequence([plan['seed_entropy'],mi,ri,991]))
                out['critical'][mi,ri]=multiplier_maxima(s,rng,plan['static']['multipliers'])[0]
                ae,ase,te,tse=temporal_project(d,noise)
                out['annual_error'][mi,ri]=ae;out['annual_se'][mi,:,ri]=ase;out['theta_error'][mi,ri]=te;out['theta_se'][mi,:,ri]=tse
                if ri%100==99:print(f'{spec["name"]}: {ri+1}/{R}, static197 + annual985 + temporal474',flush=True)
    for name,a in out.items():
        if not np.isfinite(a).all():raise ArithmeticError('Nonfinite '+name)
        if ('_se' in name or name=='se') and (a<=1e-14).any():raise ArithmeticError('Degenerate '+name)
    return out


def family_performance(raw,reject,null):
    result=dict(null_cases=int(null.sum()),nonnull_cases=int((~null).sum()))
    for name,ev in [('fwer_raw',raw),('fwer_adjusted',reject)]:
        vals=probability(ev[:,null].any(1)) if null.any() else [np.nan]*4
        result.update(zip([name,name+'_mcse',name+'_mc_low',name+'_mc_high'],[float(x) for x in vals]))
    for key,ev in [('power_raw',raw),('power_adjusted',reject)]:result[key],result[key+'_mcse']=panel_rate(ev[:,~null])
    return result


def analyze_static(d,plan,a):
    cal=[];rejections=[];families=[];panels=[];design=d['design']
    for mi,spec in enumerate(plan['mechanisms']):
        err=a['error'][mi]
        for method in METHODS:
            index=0 if method=='HAC5_Holm' else 1;se=a['se'][mi,index];crit=Z if method!=METHODS[2] else a['critical'][mi,:,None]
            covered=np.abs(err)<=crit*se;cs=probability(covered)
            for j,row in enumerate(design.to_dict('records')):
                cal.append(dict(**row,mechanism=spec['name'],method=method,interval_type='simultaneous197' if method==METHODS[2] else 'marginal95',bias=float(err[:,j].mean()),bias_mcse=float(err[:,j].std(ddof=1)/np.sqrt(len(err))),rmse=float(np.sqrt(np.mean(err[:,j]**2))),empirical_se=float(err[:,j].std(ddof=1)),mean_model_se=float(se[:,j].mean()),coverage=cs[0][j],coverage_mcse=cs[1][j],coverage_mc_low=cs[2][j],coverage_mc_high=cs[3][j]))
            for pattern,truth in patterns(design,d['nuisance'],dict(effect_patterns=dict(dense_delta=[-.5,-.25,-.1,0,.1,.25,.5],sparse_delta=[-.25,.25]))):
                z=(err+truth)/se;p=2*norm.sf(np.abs(z));raw=p<.05
                reject=holm_rows(p)<.05 if method!=METHODS[2] else np.abs(z)>crit
                null=truth==0;f=family_performance(raw,reject,null)
                f.update(mechanism=spec['name'],method=method,pattern=pattern,simultaneous_coverage=float(covered.all(1).mean()),simultaneous_coverage_mcse=float(covered.all(1).std(ddof=1)/np.sqrt(len(err))))
                families.append(f);pr=probability(reject);rr=probability(raw)
                for j,row in enumerate(design.itertuples()):
                    rejections.append(dict(mechanism=spec['name'],method=method,pattern=pattern,scenario=row.scenario,papel_id=row.papel_id,true_delta=truth[j],raw_rejection=rr[0][j],adjusted_rejection=pr[0][j],adjusted_mcse=pr[1][j],adjusted_mc_low=pr[2][j],adjusted_mc_high=pr[3][j]))
                for scenario in ['decada','recente']:
                    ix=design.scenario.eq(scenario).to_numpy();q=dict(mechanism=spec['name'],method=method,pattern=pattern,scenario=scenario)
                    for key,ev,mask in [('coverage',covered,ix),('power_adjusted',reject,ix&~null),('type1_raw',raw,ix&null)]:q[key],q[key+'_mcse']=panel_rate(ev[:,mask])
                    panels.append(q)
    return dict(static_calibration=pd.DataFrame(cal),static_rejection=pd.DataFrame(rejections),static_family=pd.DataFrame(families),static_panels=pd.DataFrame(panels))


def temporal_truth(d,pattern):
    ad=d['annual_design'];truth=np.zeros(len(ad))
    if pattern=='constant_positive_.25':truth[:]=.25
    elif pattern=='constant_negative_.25':truth[:]=-.25
    elif pattern=='early_negative_late_positive_.25':truth=np.where(ad.year<=2020,-.25,.25)
    elif pattern=='sparse_positive_.25':truth=np.where(ad.papel_id.isin(d['nuisance'].papel_id[:12]),.25,0)
    elif pattern!='zero':raise ValueError(pattern)
    theta=np.full(80,.5 if pattern=='early_negative_late_positive_.25' else 0.)
    amap=d['annual_map'];vals=truth[np.maximum(amap,0)];valid=amap>=0
    positive=np.all((vals>0)|~valid,axis=1);negative=np.all((vals<0)|~valid,axis=1)
    null=np.r_[theta==0,~positive,~negative]
    return truth,theta,null


def temporal_pvalues(d,annual,se,theta,tse):
    amap=d['annual_map'];valid=amap>=0;idx=np.maximum(amap,0)
    z=annual[:,idx]/se[:,idx]
    pp=np.where(valid[None,:,:],norm.sf(z),0).max(2);pn=np.where(valid[None,:,:],norm.cdf(z),0).max(2)
    return np.column_stack([2*norm.sf(np.abs(theta/tse)),pp,pn])


def analyze_temporal(d,plan,a):
    calibration=[];families=[];hypotheses=[]
    for mi,spec in enumerate(plan['mechanisms']):
        for method_index,method in enumerate(METHODS[:2]):
            ae=a['annual_error'][mi];se=a['annual_se'][mi,method_index];te=a['theta_error'][mi];ts=a['theta_se'][mi,method_index]
            for kind,design,e,s in [('annual',d['annual_design'],ae,se),('theta',d['design'].iloc[:80],te,ts)]:
                covered=np.abs(e)<=Z*s;cp=probability(covered)
                for j,row in enumerate(design.to_dict('records')):calibration.append(dict(**row,kind=kind,method=method,mechanism=spec['name'],bias=float(e[:,j].mean()),coverage=cp[0][j],coverage_mcse=cp[1][j],coverage_mc_low=cp[2][j],coverage_mc_high=cp[3][j],mean_model_se=float(s[:,j].mean()),empirical_se=float(e[:,j].std(ddof=1))))
            for pattern in plan['temporal']['patterns']:
                ta,tt,null=temporal_truth(d,pattern);p=temporal_pvalues(d,ae+ta,se,te+tt,ts);raw=p<.05;reject=holm_rows(p)<.05
                f=family_performance(raw,reject,null);f.update(mechanism=spec['name'],method=method,pattern=pattern);families.append(f)
                rates=probability(reject)
                for j in range(474):
                    kind='theta' if j<80 else ('positive_IUT' if j<277 else 'negative_IUT');case=j if j<80 else (j-80 if j<277 else j-277)
                    row=d['design'].iloc[case]
                    hypotheses.append(dict(mechanism=spec['name'],method=method,pattern=pattern,kind=kind,scenario=row.scenario,papel_id=row.papel_id,is_true_null=bool(null[j]),adjusted_rejection=rates[0][j],adjusted_mcse=rates[1][j],adjusted_mc_low=rates[2][j],adjusted_mc_high=rates[3][j]))
    return dict(temporal_calibration=pd.DataFrame(calibration),temporal_family=pd.DataFrame(families),temporal_hypotheses=pd.DataFrame(hypotheses))


def observed(d,plan):
    # Only existing observed N returns are used; unavailable pre2021 paths for37 assets are masked away.
    y=np.zeros((len(d['market']),117))
    for p in d['panels']:
        mat=d['matrices']['referencia_n'][p['scenario']]
        y[np.ix_(p['time_index'],p['asset_index'])]=mat[p['sample'].ticker].to_numpy()
    e,se,s=static_project(d,y)
    rng=np.random.default_rng(np.random.SeedSequence([plan['seed_entropy'],9,0,991]))
    with threadpool_limits(limits=1):crit,maxima,cov=multiplier_maxima(s,rng,999)
    tables=[]
    for mi,method in enumerate(METHODS):
        idx=0 if mi==0 else 1;z=e/se[idx];p=2*norm.sf(np.abs(z));adjusted=holm_rows(p[None,:])[0] if mi<2 else (1+np.sum(maxima[:,None]>=np.abs(z)[None,:],axis=0))/1000
        c=Z if mi<2 else crit
        for j,row in enumerate(d['design'].to_dict('records')):tables.append(dict(**row,method=method,delta=e[j],se_delta=se[idx,j],p_raw=p[j],p_adjusted=adjusted[j],ci_low=e[j]-c*se[idx,j],ci_high=e[j]+c*se[idx,j],interval_type='marginal95' if mi<2 else 'simultaneous197',critical_value=c))
    ae,ase,te,tse=temporal_project(d,y);temp=[]
    for mi,method in enumerate(METHODS[:2]):
        pp=temporal_pvalues(d,ae[None,:],ase[mi,None,:],te[None,:],tse[mi,None,:])[0];adj=holm_rows(pp[None,:])[0]
        for j in range(474):
            kind='theta' if j<80 else ('positive_IUT' if j<277 else 'negative_IUT');case=j if j<80 else (j-80 if j<277 else j-277);row=d['design'].iloc[case]
            temp.append(dict(method=method,kind=kind,scenario=row.scenario,papel_id=row.papel_id,p_raw=pp[j],p_adjusted=adj[j]))
    return dict(observed_static=pd.DataFrame(tables),observed_temporal=pd.DataFrame(temp),multiplier_maxima=pd.DataFrame({'maximum':maxima})),cov
