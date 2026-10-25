"""Post-review liquidity regressions with generated regressors and joint resampling."""
import itertools
import numpy as np
import pandas as pd
from scipy.stats import rankdata

def holm(p):
    p=np.asarray(p,float);order=np.argsort(p);q=np.empty(len(p));q[order]=np.minimum(1,np.maximum.accumulate(p[order]*np.arange(len(p),0,-1)));return q

def block_weights(T,L,rng,B):
    starts=rng.integers(0,T-L+1,size=(B,(T+L-1)//L));ix=(starts[:,:,None]+np.arange(L)).reshape(B,-1)[:,:T];W=np.zeros((B,T),dtype=np.float64)
    for b,row in enumerate(ix):W[b]=np.bincount(row,minlength=T)
    return W,ix[:3]

def estimates(R,M,W):
    valid=np.isfinite(R)&np.isfinite(M)[:,None];Y=np.where(valid,R,0.);X=np.where(valid,M[:,None],0.)
    def slope(mask):
        v=valid&mask[:,None];n=W@v;mx=W@np.where(v,X,0.);my=W@np.where(v,Y,0.);xx=W@np.where(v,X*X,0.);xy=W@np.where(v,X*Y,0.)
        with np.errstate(divide='ignore',invalid='ignore'):return (xy-mx*my/n)/(xx-mx*mx/n)
    beta=slope(np.ones(len(M),bool));delta=slope(M>0)-slope(M<0);return delta,beta

def liquidity_coefficient(y,beta,logliq,logsize,sector,controls):
    """FWL with fixed control columns plus optional reestimated traditional beta."""
    y=np.atleast_2d(y);beta=np.atleast_2d(beta);Z=[np.ones(len(logliq))]
    if 'size' in controls:Z.append((logsize-np.mean(logsize))/np.std(logsize))
    if 'sector' in controls:
        for name in sorted(set(sector))[1:]:Z.append((np.asarray(sector)==name).astype(float))
    Z=np.column_stack(Z);assert np.linalg.matrix_rank(Z)==Z.shape[1]
    Q=np.linalg.qr(Z,mode='reduced')[0];x=logliq-Q@(Q.T@logliq);yr=y-(y@Q)@Q.T;den=x@x
    if 'beta' in controls:
        br=beta-(beta@Q)@Q.T;bb=np.sum(br*br,axis=1);bx=br@x;by=np.sum(br*yr,axis=1)
        with np.errstate(divide='ignore',invalid='ignore'):coef=(yr@x-bx*by/bb)/(den-bx*bx/bb)
        rank_valid=(bb>1e-12)&(den-bx*bx/bb>1e-12)
    else:coef=(yr@x)/den;rank_valid=np.full(len(y),den>1e-12)
    coef[~rank_valid]=np.nan
    return coef,int(Z.shape[1]+1+('beta' in controls))

def spearman(x,y):
    x=rankdata(np.atleast_2d(x),axis=1);y=rankdata(np.atleast_2d(y),axis=1);x=x-x.mean(axis=1,keepdims=True);y=y-y.mean(axis=1,keepdims=True)
    return np.sum(x*y,axis=1)/np.sqrt(np.sum(x*x,axis=1)*np.sum(y*y,axis=1))

def summarize(point,draws):
    draws=np.asarray(draws);invalid=int((~np.isfinite(draws)).sum())
    if invalid:return dict(estimate=float(point),invalid_draws=invalid,status='invalid_draws',p=np.nan,ci_low=np.nan,ci_high=np.nan)
    q=np.quantile(draws-point,[.025,.975]);return dict(estimate=float(point),invalid_draws=0,status='estimated',p=float((1+np.sum(abs(draws-point)>=abs(point)))/(len(draws)+1)),ci_low=float(point-q[1]),ci_high=float(point-q[0]),bootstrap_mean=float(draws.mean()),bootstrap_bias=float(draws.mean()-point),bootstrap_se=float(draws.std(ddof=1)))

MODELS=[tuple(name for name,use in zip(['size','sector','beta'],bits) if use) for bits in itertools.product([False,True],repeat=3)]

def run(returns,market,volume,covariates,eligibility,B=4999,blocks=(21,5,63),seed=20261025):
    names=returns.columns;cov=covariates.set_index('papel_id').reindex(names);assert cov.index.equals(names)
    early=returns.index.year<=2020;R=[returns.loc[mask].to_numpy() for mask in [early,~early]];M=[market.loc[mask].to_numpy() for mask in [early,~early]];V=[volume.loc[mask].to_numpy() for mask in [early,~early]]
    points=[estimates(r,m,np.ones((1,len(m)))) for r,m in zip(R,M)];d0,b0=points[0];theta=points[1][0]-d0
    logliq=cov.log_liquidity_2015.to_numpy();size=cov.log_size.to_numpy();sectors=cov.sector.to_numpy();finite=np.isfinite(size)&cov.sector.notna().to_numpy();model_ids={};excluded=[]
    for cohort in ['original80','union118']:
        candidate=eligibility['early'].copy()
        if cohort=='original80':candidate&=cov.original80.to_numpy()
        use=candidate&finite;model_ids[cohort]=np.flatnonzero(use)
        for j in np.flatnonzero(candidate):excluded.append(dict(cohort=cohort,papel_id=names[j],included=bool(use[j]),reason='included' if use[j] else ('missing_size' if not np.isfinite(size[j]) else 'missing_sector')))
    rows=[];associations=[];bank={};oracle=[]
    for L in blocks:
        rng=np.random.default_rng(seed+L);weights=[];draws=[];indices=[]
        for r,m in zip(R,M):
            w,ix=block_weights(len(m),L,rng,B);weights.append(w);indices.append(ix);draws.append(estimates(r,m,w))
        for cohort,jj in model_ids.items():
            for controls in MODELS:
                label='+'.join(controls) or 'none';N=len(jj)
                if N<40:rows.append(dict(cohort=cohort,controls=label,block=L,N=N,status='insufficient_cross_section'));continue
                point,p=liquidity_coefficient(d0[:,jj],b0[:,jj],logliq[jj],size[jj],sectors[jj],controls)
                if N-p<10:rows.append(dict(cohort=cohort,controls=label,block=L,N=N,status='insufficient_residual_df'));continue
                b,_=liquidity_coefficient(draws[0][0][:,jj],draws[0][1][:,jj],logliq[jj],size[jj],sectors[jj],controls);row=dict(cohort=cohort,controls=label,block=L,N=N,parameters=p,residual_df=N-p,**summarize(point[0],b));rows.append(row);bank[f'{cohort}_{label}_{L}']=b
                # Dense cross-sectional OLS is independent of the FWL implementation.
                for k in range(3):
                    X=[np.ones(N),logliq[jj]]
                    if 'size' in controls:X.append(size[jj])
                    if 'sector' in controls:
                        X.extend([(sectors[jj]==s).astype(float) for s in sorted(set(sectors[jj]))[1:]])
                    if 'beta' in controls:X.append(draws[0][1][k,jj])
                    direct=np.linalg.lstsq(np.column_stack(X),draws[0][0][k,jj],rcond=None)[0][1];oracle.append(float(abs(direct-b[k])))
        # Undefined volume changes for ineligible histories remain missing,never imputed.
        with np.errstate(divide='ignore',invalid='ignore'):
            mean_volume=[v.mean(axis=0) for v in V];change=np.log(mean_volume[1])-np.log(mean_volume[0]);change_draws=np.log(weights[1]@V[1]/len(M[1]))-np.log(weights[0]@V[0]/len(M[0]))
        theta_draws=draws[1][0]-draws[0][0]
        for cohort in ['original80','union118']:
            use=eligibility['theta']&np.isfinite(logliq)&np.isfinite(change)
            if cohort=='original80':use&=cov.original80.to_numpy()
            jj=np.flatnonzero(use)
            for target,x,xb in [('initial_level',logliq[jj],np.broadcast_to(logliq[jj],(B,len(jj)))),('period_change',change[jj],change_draws[:,jj])]:
                point=spearman(x,theta[:,jj])[0];b=spearman(xb,theta_draws[:,jj]);associations.append(dict(cohort=cohort,liquidity_target=target,block=L,N=len(jj),**summarize(point,b)));bank[f'change_{cohort}_{target}_{L}']=b
        print('J block',L,'complete;common-case N', {k:len(v) for k,v in model_ids.items()},flush=True)
    table=pd.DataFrame(rows);table['p_holm16']=np.nan
    for L,g in table.groupby('block'):
        values=g.p.fillna(1).to_numpy() if 'p' in g else np.ones(len(g));assert len(g)==16;table.loc[g.index,'p_holm16']=holm(values)
    assoc=pd.DataFrame(associations);assoc['p_holm4']=np.nan
    for L,g in assoc.groupby('block'):assoc.loc[g.index,'p_holm4']=holm(g.p.fillna(1))
    return table,assoc,bank,pd.DataFrame(excluded),dict(dense_FWL_checks=len(oracle),max_difference=max(oracle,default=0.),passed=max(oracle,default=0.)<1e-10)
