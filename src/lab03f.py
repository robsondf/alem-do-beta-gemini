"""Post-review fixed-security robustness. No quotes, imputation or primary overwrite."""
from pathlib import Path
import hashlib
import json
import platform
import os
import sys
import time
import zipfile
import numpy as np
import pandas as pd
from scipy import sparse
from scipy.stats import norm
from lab02 import holm

PROFILES = ('daily','exclude_2020_03','exclude_2020_H1','continuous','lag1','leadlag1','weekly')
SCENARIOS = ('decada','decada_periodo_comum','recente')


def digest(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def load(root, archive):
    plan_path=root/'data/lab03f/plano_pos_parecer_v1.json'
    plan=json.loads(plan_path.read_text())
    assert digest(plan_path)==json.loads((plan_path.parent/'freeze.json').read_text())['plan_sha256']
    assert digest(archive)==plan['x_sha256'], 'Wrong audited return archive'
    assert digest(root/plan['metadata_path'])==plan['metadata_sha256']
    with zipfile.ZipFile(archive) as z:
        manifest=json.loads(z.read('manifesto_exports.json'))
        assert len(set(z.namelist()))==len(z.namelist())
        assert set(z.namelist())==set(manifest)|{'manifesto_exports.json'}
        for n,h in manifest.items():
            assert not Path(n).is_absolute() and '..' not in Path(n).parts
            assert hashlib.sha256(z.read(n)).hexdigest()==h,n
        matrices={s:pd.read_csv(z.open(f'matrices/referencia_n/{s}/retornos_logaritmicos.csv.gz'),
                    compression='gzip',index_col=0,parse_dates=True,float_precision='round_trip') for s in SCENARIOS}
    meta=pd.read_csv(root/plan['metadata_path'],float_precision='round_trip')
    samples={s:meta[meta.scenario.eq(s)].sort_values('papel_id').reset_index(drop=True) for s in SCENARIOS}
    assert {s:len(q) for s,q in samples.items()}==plan['samples']
    for s,q in matrices.items():
        assert not q.index.has_duplicates and q.index.is_monotonic_increasing
        assert q['^BVSP'].notna().all()
        assert set(samples[s].ticker)|{'^BVSP'}==set(q.columns)
    assert matrices['decada'].isna().sum().sum()==7
    assert matrices['recente'].isna().sum().sum()==7
    pd.testing.assert_frame_equal(matrices['decada'].loc[matrices['recente'].index],
                                 matrices['recente'][matrices['decada'].columns],check_exact=True)
    pd.testing.assert_frame_equal(matrices['decada_periodo_comum'],
                                 matrices['recente'][matrices['decada_periodo_comum'].columns],check_exact=True)
    return plan,matrices,samples


def profile_data(frame, profile):
    q=frame.copy();keep=np.ones(len(q),bool)
    if profile=='exclude_2020_03':keep=~((q.index>='2020-03-01')&(q.index<='2020-03-31'))
    if profile=='exclude_2020_H1':keep=~((q.index>='2020-01-01')&(q.index<='2020-06-30'))
    if profile=='weekly':
        # min_count alone would silently aggregate incomplete asset weeks.
        groups=q.resample('W-FRI');summed=groups.sum(min_count=1)
        complete=groups.count().eq(groups.size(),axis=0)
        q=summed.where(complete).iloc[1:-1]
        keep=np.ones(len(q),bool)
    return q,np.asarray(keep,bool)


def fit(y,m,keep=None,offsets=(0,),continuous=False):
    """Joint OLS contrasts, calendar-grid scores, no filtering before shifting."""
    y=np.asarray(y,float);m=np.asarray(m,float);N=len(m)
    keep=np.ones(N,bool) if keep is None else np.asarray(keep,bool)
    market=np.full((N,len(offsets)),np.nan)
    for j,k in enumerate(offsets):
        ids=np.arange(N)-k;ok=(ids>=0)&(ids<N)
        market[ok,j]=m[ids[ok]]
    eligible=keep&np.isfinite(market).all(1)&np.isfinite(m)&(m!=0)
    on=eligible&np.isfinite(y);D=(m>0).astype(float)
    n=int(on.sum());k=1+(not continuous)+2*len(offsets)
    out=dict(n_target=int(keep.sum()),n_eligible=int(eligible.sum()),n_pairs=n,
             n_plus=int((on&(m>0)).sum()),n_minus=int((on&(m<0)).sum()),
             n_missing=int((eligible&~np.isfinite(y)).sum()),
             coverage=float(n/eligible.sum()),status='insufficient')
    if min(out['n_plus'],out['n_minus'])<60 or n<200 or out['coverage']<.95:return out,None,None
    if min(np.var(m[on&(m>0)],ddof=1),np.var(m[on&(m<0)],ddof=1))<1e-12:return out,None,None
    X=np.column_stack(([np.ones(N)] if continuous else [np.ones(N),D])+[market,market*D[:,None]])
    xx=X[on];yy=y[on];q,r=np.linalg.qr(xx,mode='reduced')
    if np.linalg.matrix_rank(r)!=k:raise ArithmeticError('Rank deficient design')
    invr=np.linalg.inv(r);bread=invr@invr.T;coef=np.linalg.solve(r,q.T@yy)
    residual=yy-xx@coef;start=1 if continuous else 2;K=len(offsets)
    C=np.zeros((4,k));C[0,start:start+K]=1;C[1,start:start+K]=1;C[1,start+K:]=1;C[2,start+K:]=1
    if not continuous:C[3,1]=1
    estimates=C@coef
    scores=np.zeros((N,4));scores[on]=(xx@bread@C.T)*residual[:,None]
    cov=scores.T@scores;terms=[];ses={}
    for h in range(21):
        cross=cov if h==0 else scores[h:].T@scores[:-h]
        terms.append(float(cross[2,2]))
    for L in [0,5,10,20]:
        v=cov.copy()
        for h in range(1,L+1):
            cross=scores[h:].T@scores[:-h];v+=(1-h/(L+1))*(cross+cross.T)
        v*=n/(n-k)
        if np.diag(v).min() < -1e-12:raise ArithmeticError('Negative HAC variance')
        ses[L]=np.sqrt(np.maximum(0,np.diag(v)))
    out.update(status='estimated',parameters=k,beta_minus=estimates[0],beta_plus=estimates[1],
               delta=estimates[2],intercept_jump=estimates[3],
               alpha_minus=coef[0],alpha_plus=coef[0]+(0 if continuous else coef[1]),
               beta_traditional=float(np.linalg.lstsq(np.column_stack([np.ones(n),m[on]]),yy,rcond=None)[0][1]))
    for j,name in enumerate(['beta_minus','beta_plus','delta','intercept_jump']):
        se=ses[5][j];out[name+'_se_hac5']=se
        out[name+'_ci_low']=estimates[j]-norm.ppf(.975)*se
        out[name+'_ci_high']=estimates[j]+norm.ppf(.975)*se
    for L,se in ses.items():
        out[f'delta_se_hac{L}']=se[2];out[f'delta_p_hac{L}']=2*norm.sf(abs(estimates[2]/se[2]))
    out['intercept_jump_p']=np.nan if continuous else 2*norm.sf(abs(estimates[3]/ses[5][3]))
    # Zero scores mark omitted equations, never imputed returns.
    return out,terms,scores[:,2]


def individual(matrices,samples):
    rows=[];terms=[]
    for profile in PROFILES:
        for scenario in SCENARIOS:
            frame,keep=profile_data(matrices[scenario],profile)
            offsets=(0,1) if profile=='lag1' else ((-1,0,1) if profile=='leadlag1' else (0,))
            for asset in samples[scenario].itertuples():
                result,autocov,_=fit(frame[asset.ticker],frame['^BVSP'],keep,offsets,profile=='continuous')
                rows.append(dict(profile=profile,scenario=scenario,papel_id=asset.papel_id,ticker=asset.ticker,
                    setor_economico=asset.setor_economico,removed_target_sessions=int((~keep).sum()),**result))
                if profile=='daily' and scenario!='decada_periodo_comum':
                    for lag,v in enumerate(autocov):terms.append(dict(scenario=scenario,papel_id=asset.papel_id,ticker=asset.ticker,lag=lag,raw_score_product_sum=v))
        print('Fitted profile '+profile,flush=True)
    f=pd.DataFrame(rows)
    assert len(f)==7*277 and f.status.eq('estimated').all()
    for profile in PROFILES:
        ix=f.profile.eq(profile)&f.scenario.ne('decada_periodo_comum')
        for L in [0,5,10,20]:f.loc[ix,f'delta_p_holm197_hac{L}']=holm(f.loc[ix,f'delta_p_hac{L}'],197)
        f.loc[ix,'intercept_jump_p_holm197']=holm(f.loc[ix,'intercept_jump_p'],197)
        for i,row in f[f.profile.eq(profile)&f.scenario.eq('decada_periodo_comum')].iterrows():
            recent=f[f.profile.eq(profile)&f.scenario.eq('recente')&f.papel_id.eq(row.papel_id)].iloc[0]
            for key in ['delta','delta_se_hac5','n_pairs','n_plus','n_minus']:
                assert np.isclose(row[key],recent[key],rtol=1e-11,atol=1e-12),(profile,key)
            for key in [f'delta_p_holm197_hac{L}' for L in [0,5,10,20]]+['intercept_jump_p_holm197']:
                f.loc[i,key]=recent[key]
    return f,pd.DataFrame(terms)


def sufficient(frame, tickers):
    m=frame['^BVSP'].to_numpy();Y=frame[tickers].to_numpy()
    finite=np.isfinite(Y)&np.isfinite(m[:,None]);parts=[]
    for sign in [m>0,m<0]:
        on=finite&sign[:,None];x=np.where(on,m[:,None],0.);y=np.where(on,Y,0.)
        parts.extend([on.astype(float),x,x*x,y,x*y])
    return np.stack(parts,axis=1).reshape(len(frame),-1)


def deltas(moments,assets,sessions=None):
    a=np.asarray(moments).reshape(-1,10,assets);betas=[]
    for j in [0,5]:
        n,x,xx,y,xy=[a[:,j+k] for k in range(5)];ss=xx-x*x/n
        if (n<60).any() or (ss/(n-1)<1e-12).any():raise ArithmeticError('Invalid bootstrap regime; not redrawn')
        betas.append((xy-x*y/n)/ss)
    if ((a[:,0]+a[:,5])<200).any():raise ArithmeticError('Invalid bootstrap pair count')
    if sessions is not None and ((a[:,0]+a[:,5])/sessions<.95).any():raise ArithmeticError('Invalid bootstrap coverage; not redrawn')
    return betas[0]-betas[1]


def resample_moments(features,L,B,rng):
    """Exactly sum MBB draws using block-start multiplicities and prefix sums."""
    N,P=features.shape
    if L>N:raise ValueError('Block longer than contiguous stratum')
    prefix=np.vstack([np.zeros((1,P)),np.cumsum(features,axis=0)])
    blocks=prefix[L:]-prefix[:-L];full,tail=divmod(N,L)
    starts=rng.integers(0,N-L+1,size=(B,full+(tail>0)))
    rr=np.repeat(np.arange(B),full);cc=starts[:,:full].ravel()
    weights=sparse.csr_matrix((np.ones(len(rr)),(rr,cc)),shape=(B,N-L+1))
    result=weights@blocks
    if tail:
        ends=starts[:,-1];result+=prefix[ends+tail]-prefix[ends]
    return np.asarray(result)


def contiguous_segments(index,profile):
    keep=np.ones(len(index),bool)
    if profile=='exclude_2020_03':keep=~((index>='2020-03-01')&(index<='2020-03-31'))
    if profile=='exclude_2020_H1':keep=~((index>='2020-01-01')&(index<='2020-06-30'))
    ids=np.flatnonzero(keep);cuts=np.flatnonzero(np.diff(ids)>1)+1
    return [x for x in np.split(ids,cuts) if len(x)]


def aggregate(plan,matrices,samples):
    cfg=plan['bootstrap'];B=cfg['replications'];seed=cfg['seed'];rows=[];draws={}
    recent=matrices['recente'];long=matrices['decada'];ids=list(samples['recente'].papel_id)
    common=np.array([ids.index(p) for p in samples['decada'].papel_id]);J=117
    rfeatures=sufficient(recent,list(samples['recente'].ticker))
    before=long[long.index.year<2021];lfeatures=sufficient(before,list(samples['decada'].ticker))
    rpoint=deltas(rfeatures.sum(0),J,len(recent))[0]
    for L in [cfg['primary_block_sessions']]+cfg['sensitivity_block_sessions']:
        rng=np.random.default_rng(np.random.SeedSequence([seed,L,1]))
        rstar=resample_moments(rfeatures,L,B,rng)
        rd=deltas(rstar,J,len(recent))
        for profile_index,profile in enumerate(['daily','exclude_2020_03','exclude_2020_H1']):
            segments=contiguous_segments(before.index,profile);prepoint=sum(lfeatures[ix].sum(0) for ix in segments)
            pre=np.zeros((B,lfeatures.shape[1]));rng=np.random.default_rng(np.random.SeedSequence([seed,L,2,profile_index]))
            for ix in segments:pre+=resample_moments(lfeatures[ix],L,B,rng)
            rm=rstar.reshape(B,10,J)[:,:,common].reshape(B,-1)
            rp=rfeatures.sum(0).reshape(10,J)[:,common].reshape(-1)
            sessions=sum(len(ix) for ix in segments)+len(recent)
            dec=deltas(pre+rm,80,sessions);point=deltas(prepoint+rp,80,sessions)[0]
            cases=[('decada',point,dec)]
            if profile=='daily':cases.extend([('decada_periodo_comum',rpoint[common],rd[:,common]),('recente',rpoint,rd)])
            for scenario,est,a in cases:
                for stat in ['mean','median']:
                    fun=np.mean if stat=='mean' else np.median
                    theta=float(fun(est));boot=fun(a,axis=1);error=boot-theta
                    lo,hi=np.quantile(error,[.025,.975]);tail=np.count_nonzero(abs(error)>=abs(theta));p=(1+tail)/(B+1)
                    rate=tail/B;z=norm.ppf(.975);center=(rate+z*z/(2*B))/(1+z*z/B)
                    radius=z*np.sqrt(rate*(1-rate)/B+z*z/(4*B*B))/(1+z*z/B)
                    rows.append(dict(profile=profile,scenario=scenario,statistic=stat,assets=len(est),block=L,B=B,
                        estimate=theta,bootstrap_se=float(boot.std(ddof=1)),ci_low=theta-hi,ci_high=theta-lo,
                        p_centered=p,tail_exceedances=int(tail),p_mcse=float(np.sqrt(rate*(1-rate)/B)),
                        tail_rate_wilson_low=max(0,center-radius),tail_rate_wilson_high=min(1,center+radius),
                        negative_assets=int((est<0).sum()),interval='marginal_basic_approximate'))
                    draws[f'{profile}_{scenario}_{stat}_L{L}']=boot
        print(f'Bootstrap L={L}, B={B}, all10 targets complete',flush=True)
    f=pd.DataFrame(rows);assert len(f)==30
    for L in f.block.unique():
        ix=f.block.eq(L);assert ix.sum()==10;f.loc[ix,'p_holm10']=holm(f.loc[ix,'p_centered'],10)
    f['p_holm30']=holm(f.p_centered,30)
    return f,draws


def influence_holm(root):
    p=root/'results/tables/lab03e_colab_20261023/economic_sensitivities.csv.gz'
    assert digest(p)=='90ebc8dc0a71f65f0a41ebff6afe2d9deea6ffe9d18d57d7e86df4ba0a54fb11'
    f=pd.read_csv(p,float_precision='round_trip')
    for (reference,diagnostic),g in f.groupby(['reference','diagnostic']):
        assert len(g)==197
        f.loc[g.index,'p_normal']=2*norm.sf(abs(g.delta/g.se_hac5))
        f.loc[g.index,'p_holm197']=holm(f.loc[g.index,'p_normal'],197)
    f['scope']='post_review_diagnostic; response_selected_masks_not_FWER_calibrated; envelope_not_recomputed'
    return f


def run(root,archive,output):
    started=time.monotonic()
    plan,mats,samples=load(root,archive);output.mkdir(parents=True,exist_ok=False)
    estimates,terms=individual(mats,samples)
    ledger=pd.read_csv(root/'results/tables/lab03e_colab_20261023/economic_ledger.csv.gz',float_precision='round_trip')
    check=estimates[estimates.profile.eq('daily')&estimates.scenario.ne('decada_periodo_comum')].merge(ledger,on=['scenario','papel_id'],suffixes=('_new','_old'),validate='one_to_one')
    for n in ['delta','beta_plus','beta_minus']:
        np.testing.assert_allclose(check[n+'_new'],check[n+'_old'],atol=1e-11,rtol=1e-10)
    np.testing.assert_allclose(check.delta_se_hac5,check.se_hac5,atol=1e-11,rtol=1e-10)
    ag,draws=aggregate(plan,mats,samples);inf=influence_holm(root)
    for name,f in [('individual',estimates),('aggregate',ag),('hac_score_terms',terms),('existing_sensitivity_holm',inf)]:
        f.to_csv(output/(name+'.csv.gz'),index=False,compression={'method':'gzip','mtime':0})
    np.savez_compressed(output/'bootstrap_targets.npz',**draws)
    summary=[]
    for (p,s),g in estimates.groupby(['profile','scenario']):
        summary.append(dict(profile=p,scenario=s,assets=len(g),mean_delta=g.delta.mean(),median_delta=g.delta.median(),
            negative=int((g.delta<0).sum()),holm197=int((g.delta_p_holm197_hac5<.05).sum()),
            min_pairs=int(g.n_pairs.min()),min_plus=int(g.n_plus.min()),min_minus=int(g.n_minus.min())))
    pd.DataFrame(summary).to_csv(output/'profile_summary.csv',index=False)
    manifest={str(p.name):digest(p) for p in output.iterdir()}
    report=dict(stage='Lab03F',environment='Colab' if os.environ.get('ALEM_BETA_EXECUTION_ENV')=='Colab' else 'local_new_analysis_not_yet_user_Colab',plan_sha256=digest(root/'data/lab03f/plano_pos_parecer_v1.json'),
        archive_sha256=digest(archive),primary_reproduced_cases=len(check),individual_rows=len(estimates),
        aggregate_rows=len(ag),source_missing_decade=int(mats['decada'].isna().sum().sum()),source_missing_recent=int(mats['recente'].isna().sum().sum()),
        python=platform.python_version(),numpy=np.__version__,pandas=pd.__version__,files=manifest,elapsed_seconds=time.monotonic()-started,
        scope='post-review sensitivities and approximate aggregate inference; no economic homologation, no recalibrated envelope, no new market downloads')
    (output/'verification.json').write_text(json.dumps(report,indent=2)+'\n')
    return report
