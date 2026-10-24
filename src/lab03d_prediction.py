"""Historical pseudo-OOS next-return forecasts; selection/vintage bias remains."""
import numpy as np
import pandas as pd
from threadpoolctl import threadpool_limits

MODELS=('zero','historical_mean','traditional_market','conditional_market')
CONFIGS=(('N252','referencia_n',252,None),('N504','referencia_n',504,None),('gap_guard252','referencia_n',252,'gap'),('LightQ4252','referencia_n',252,'light'),('jcp_duas_celulas_documentadas252','jcp_duas_celulas_documentadas',252,None),('jcp_condicional252','jcp_condicional',252,None),('jcp_rendimento_caixa_baixo252','jcp_rendimento_caixa_baixo',252,None),('jcp_rendimento_caixa_alto252','jcp_rendimento_caixa_alto',252,None))


def masked_matrix(matrix,mode):
    if mode is None:return matrix
    a=matrix.copy()
    if mode=='gap':raise ValueError('Use forecast_fold gap_guard=True; masking must respect each origin')
    if mode=='light':
        col='LIGT3.SA';a.loc[(a.index>='2024-10-01')&(a.index<='2024-12-31'),col]=np.nan
    else:raise ValueError(mode)
    assert np.array_equal(matrix['^BVSP'].to_numpy(),a['^BVSP'].to_numpy())
    assert a.isna().sum().sum()>=matrix.isna().sum().sum()
    return a


def moments(y,m,mask):
    n=mask.sum(0);safe=np.maximum(n,1);xm=np.where(mask,m[:,None],0).sum(0)/safe;ym=np.where(mask,y,0).sum(0)/safe
    center=np.where(mask,m[:,None]-xm,0);ss=(center*center).sum(0)
    slope=np.divide(np.sum(center*np.where(mask,y-ym,0),axis=0),ss,out=np.zeros_like(ss),where=ss>0)
    intercept=ym-slope*xm
    return n,xm,ym,ss,intercept,slope


def forecast_fold(matrix,tickers,origin,window,target_indices,gap_guard=False):
    """Reads training rows<=origin and only lagged market for each future target."""
    if origin-window+1<0:raise ValueError('Insufficient pre-evaluation warmup')
    train=matrix.iloc[origin-window+1:origin+1].copy()
    if gap_guard:
        for col in tickers:
            # Future missing flags are deliberately inaccessible to this rule.
            known=np.flatnonzero(matrix[col].iloc[:origin+1].isna().to_numpy())
            neighbors=np.unique(np.r_[known-1,known,known+1]);neighbors=neighbors[(neighbors>=origin-window+1)&(neighbors<=origin)]
            train.iloc[neighbors-(origin-window+1),train.columns.get_loc(col)]=np.nan
    m=train['^BVSP'].to_numpy();y=train[tickers].to_numpy()
    if len(train)!=window or not np.isfinite(m).all():raise ValueError('Invalid market training window')
    valid=np.isfinite(y)&(m[:,None]!=0)
    allm=moments(y,m,valid);plus=moments(y,m,valid&(m[:,None]>0));minus=moments(y,m,valid&(m[:,None]<0))
    n,xm,mean,ss,atrad,btrad=allm
    eligible=(n>=200)&(n/window>=.95)&(plus[0]>=60)&(minus[0]>=60)&(ss/np.maximum(n-1,1)>=1e-12)
    for pieces in [plus,minus]:eligible&=pieces[3]/np.maximum(pieces[0]-1,1)>=1e-12
    if (n==0).any():raise ValueError('No historical observations; cannot invent a forecast')
    # Market model is fitted only inside the same historical session window.
    arx=np.column_stack([np.ones(window-1),m[:-1]]);ar=np.linalg.lstsq(arx,m[1:],rcond=None)[0]
    eps=m[1:]-arx@ar;eps-=eps.mean();eps=np.sort(eps);prefix=np.r_[0.,np.cumsum(eps)];B=len(eps)
    previous=matrix['^BVSP'].to_numpy()[np.asarray(target_indices)-1]
    mu=ar[0]+ar[1]*previous
    lo=np.searchsorted(eps,-mu,side='left');hi=np.searchsorted(eps,-mu,side='right')
    nneg=lo;npos=B-hi;nzero=hi-lo
    neg_m=prefix[lo]+nneg*mu;pos_m=prefix[-1]-prefix[hi]+npos*mu
    forecasts=np.zeros((len(target_indices),len(tickers),4));forecasts[:,:,1]=mean
    forecasts[:,:,2]=atrad[None,:]+btrad[None,:]*(mu+eps.mean())[:,None]
    forecasts[:,:,3]=(nneg[:,None]*minus[4]+npos[:,None]*plus[4]+neg_m[:,None]*minus[5]+pos_m[:,None]*plus[5]+nzero[:,None]*atrad)/B
    forecasts[:,~eligible,2]=mean[~eligible];forecasts[:,~eligible,3]=mean[~eligible]
    if not np.isfinite(forecasts).all():raise ArithmeticError('Nonfinite prediction')
    stats=dict(n_pairs=n,n_plus=plus[0],n_minus=minus[0],coverage=n/window,status=np.where(eligible,'estimated','historical_mean_fallback'),ar_intercept=ar[0],ar_lag=ar[1])
    last=np.array([np.flatnonzero(valid[:,j])[-1] for j in range(len(tickers))])
    stats['max_train_date']=train.index[last]
    return forecasts,stats


def forecast_panel(matrix,sample,window,start_year,configuration,gap_guard=False):
    assert matrix.index.is_monotonic_increasing and not matrix.index.has_duplicates
    targets=np.flatnonzero((matrix.index.year>=start_year)&(matrix.index.year<=2025));dates=matrix.index[targets]
    periods=dates.to_period('M');forecasts=np.empty((len(targets),len(sample),4));origins=np.empty(len(targets),int);audit=[]
    for period in periods.unique():
        positions=np.flatnonzero(periods==period);idx=targets[positions];origin=int(idx[0]-1)
        f,stats=forecast_fold(matrix,list(sample.ticker),origin,window,idx,gap_guard=gap_guard);forecasts[positions]=f;origins[positions]=origin
        assert matrix.index[origin]<matrix.index[idx[0]]
        for j,row in enumerate(sample.itertuples()):
            audit.append(dict(configuration=configuration,papel_id=row.papel_id,ticker=row.ticker,origin=matrix.index[origin].date().isoformat(),window_start=matrix.index[origin-window+1].date().isoformat(),max_train_date=stats['max_train_date'][j].date().isoformat(),target_start=matrix.index[idx[0]].date().isoformat(),target_end=matrix.index[idx[-1]].date().isoformat(),n_pairs=int(stats['n_pairs'][j]),n_plus=int(stats['n_plus'][j]),n_minus=int(stats['n_minus'][j]),coverage=float(stats['coverage'][j]),status=stats['status'][j],window=window,ar_intercept=stats['ar_intercept'],ar_lag=stats['ar_lag']))
    actual=matrix[sample.ticker].to_numpy()[targets].copy()
    if gap_guard:
        # Target filtering uses current/previous missingness only, never a future gap.
        actual[np.isnan(matrix[sample.ticker].to_numpy()[targets-1])]=np.nan
    return dict(dates=dates,target_indices=targets,forecasts=forecasts,actual=actual,market_realized_for_evaluation=matrix['^BVSP'].to_numpy()[targets],origins=matrix.index[origins],previous_market_dates=matrix.index[targets-1],sample=sample.reset_index(drop=True),audit=audit,window=window,configuration=configuration)


def summaries(panel,scenario,selection=None):
    ids=np.arange(len(panel['sample'])) if selection is None else np.asarray(selection)
    sample=panel['sample'].iloc[ids];y=panel['actual'][:,ids];f=panel['forecasts'][:,ids];m=panel['market_realized_for_evaluation'];dates=panel['dates']
    metrics=[];gains=[]
    periods=[('full',np.ones(len(dates),bool),regime) for regime in ['all','positive','negative']]+[(str(year),dates.year==year,'all') for year in sorted(set(dates.year))]
    for period,time,regime in periods:
        time=time & (np.ones(len(m),bool) if regime=='all' else (m>0 if regime=='positive' else m<0))
        valid=np.isfinite(y)&time[:,None];n=valid.sum(0)
        errors=np.where(valid[:,:,None],y[:,:,None]-f,0);mse=(errors**2).sum(0)/np.maximum(n,1)[:,None];mae=np.abs(errors).sum(0)/np.maximum(n,1)[:,None]
        mse[n==0]=np.nan;mae[n==0]=np.nan
        for j,row in enumerate(sample.itertuples()):
            base=dict(configuration=panel['configuration'],scenario=scenario,papel_id=row.papel_id,ticker=row.ticker,setor_economico=row.setor_economico,period=period,regime=regime,n=int(n[j]),common_reused=scenario=='decada_periodo_comum')
            for k,model in enumerate(MODELS):metrics.append(dict(**base,model=model,mse=mse[j,k],mae=mae[j,k],r2_vs_zero=1-mse[j,k]/mse[j,0] if mse[j,0]>0 else np.nan,r2_vs_mean=1-mse[j,k]/mse[j,1] if mse[j,1]>0 else np.nan))
            gains.append(dict(**base,mse_traditional=mse[j,2],mse_conditional=mse[j,3],loss_gain=mse[j,2]-mse[j,3],relative_mse_gain=1-mse[j,3]/mse[j,2] if mse[j,2]>0 else np.nan))
    return metrics,gains


def daily_frame(p,scenario):
    T,A=p['actual'].shape
    frame=pd.DataFrame(dict(date=np.repeat(p['dates'].date.astype(str),A),scenario=scenario,papel_id=np.tile(p['sample'].papel_id,T),ticker=np.tile(p['sample'].ticker,T),configuration=p['configuration'],training_origin=np.repeat(p['origins'].date.astype(str),A),previous_market_date=np.repeat(p['previous_market_dates'].date.astype(str),A),actual=p['actual'].ravel(),valid_target=np.isfinite(p['actual']).ravel(),market_realized_for_evaluation=np.repeat(p['market_realized_for_evaluation'],A)))
    for k,name in enumerate(MODELS):frame[name]=p['forecasts'][:,:,k].ravel()
    return frame


def block_uncertainty(p,scenario,plan,panel_index):
    y=p['actual'];f=p['forecasts'];valid=np.isfinite(y);gain=np.where(valid,(y-f[:,:,2])**2-(y-f[:,:,3])**2,0);rows=[];T,A=y.shape;B=1999
    with threadpool_limits(limits=1):
        for block in [21,42,63]:
            rng=np.random.default_rng(np.random.SeedSequence([plan['seed_entropy'],701,p['window'],panel_index,block]));draw=np.empty((B,A))
            for start in range(0,B,128):
                count=min(128,B-start);starts=rng.integers(0,T-block+1,size=(count,int(np.ceil(T/block))))
                indices=(starts[:,:,None]+np.arange(block)).reshape(count,-1)[:,:T]
                weights=np.array([np.bincount(ix,minlength=T) for ix in indices],float)
                denom=weights@valid
                if (denom==0).any():raise ArithmeticError('Empty bootstrap asset; no redraw/drop')
                draw[start:start+count]=(weights@gain)/denom
            lo,hi=np.quantile(draw,[.025,.975],axis=0)
            for j,row in enumerate(p['sample'].itertuples()):rows.append(dict(configuration=p['configuration'],scenario=scenario,papel_id=row.papel_id,block_length=block,bootstrap_replications=B,loss_gain=float(gain[:,j].sum()/valid[:,j].sum()),ci_low=float(lo[j]),ci_high=float(hi[j]),interval_scope='exploratory marginal conditional on recorded forecast losses',common_reused=False))
    return rows


def run(d,plan,output):
    metrics=[];gains=[];folds=[];intervals=[];daily=[];long_ids=set(d['panels'][0]['sample'].papel_id)
    for configuration,variant,window,mode in CONFIGS:
        panels=[]
        for pi,(scenario,year) in enumerate([('decada',2019),('recente',2024)]):
            sample=d['panels'][pi]['sample'];mat=masked_matrix(d['matrices'][variant][scenario],None if mode=='gap' else mode)
            p=forecast_panel(mat,sample,window,year,configuration,gap_guard=mode=='gap');panels.append(p)
            for row in p['audit']:row['scenario']=scenario
            folds.extend(p['audit']);mm,gg=summaries(p,scenario);metrics.extend(mm);gains.extend(gg)
            if configuration in ['N252','N504']:
                daily.append(daily_frame(p,scenario));intervals.extend(block_uncertainty(p,scenario,plan,pi))
        recent=panels[1];ix=np.flatnonzero(recent['sample'].papel_id.isin(long_ids).to_numpy());mm,gg=summaries(recent,'decada_periodo_comum',ix);metrics.extend(mm);gains.extend(gg)
        lp=panels[0];ti=lp['dates'].get_indexer(recent['dates']);mapping=[int(recent['sample'].index[recent['sample'].papel_id.eq(pid)][0]) for pid in lp['sample'].papel_id]
        np.testing.assert_allclose(lp['forecasts'][ti],recent['forecasts'][:,mapping],atol=0,rtol=0)
        np.testing.assert_allclose(lp['actual'][ti],recent['actual'][:,mapping],atol=0,rtol=0,equal_nan=True)
        if configuration in ['N252','N504']:
            sub=[dict(row,scenario='decada_periodo_comum',common_reused=True) for row in intervals if row['configuration']==configuration and row['scenario']=='recente' and row['papel_id'] in long_ids];intervals.extend(sub)
        print('Forecast configuration complete:',configuration,flush=True)
    tables=dict(prediction_metrics=pd.DataFrame(metrics),prediction_gains=pd.DataFrame(gains),prediction_folds=pd.DataFrame(folds),prediction_intervals=pd.DataFrame(intervals))
    for name,t in tables.items():t.to_csv(output/(name+'.csv'),index=False)
    pd.concat(daily,ignore_index=True).to_csv(output/'prediction_daily.csv.gz',index=False,compression='gzip')
    return tables
