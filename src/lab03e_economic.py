"""All197 economic-impact diagnostics; no return correction or homologation."""
import numpy as np,pandas as pd
from scipy.stats import norm
from lab03d_inference import VARIANTS

def fit(m,y,keep=None):
    valid=np.isfinite(m)&np.isfinite(y)
    if keep is not None:valid&=keep
    plus=valid&(m>0);minus=valid&(m<0);on=plus|minus;n=int(on.sum())
    out=dict(n_pairs=int(valid.sum()),n_plus=int(plus.sum()),n_minus=int(minus.sum()),coverage=float(valid.mean()),status='insufficient')
    if valid.sum()<200 or valid.mean()<.95 or min(plus.sum(),minus.sum())<60:return out,None
    if min(np.var(m[valid],ddof=1),np.var(m[plus],ddof=1),np.var(m[minus],ddof=1))<1e-12:return out,None
    X=np.column_stack([np.ones(len(m)),m>0,m,m*(m>0)]);xx=X[on];yy=y[on];bread=np.linalg.inv(xx.T@xx);coef=np.linalg.lstsq(xx,yy,rcond=None)[0];res=yy-xx@coef;h=np.sum((xx@bread)*xx,axis=1);w=(xx@bread)[:,3]
    if np.max(h)>=1-1e-10:raise ArithmeticError('Near-unit leverage')
    ses=[]
    for hc3 in [False,True]:
        score=np.zeros(len(m));score[on]=w*res/(1-h if hc3 else 1);v=score@score
        for lag in range(1,6):v+=2*(1-lag/6)*(score[lag:]@score[:-lag])
        if v<=0:raise ArithmeticError('Nonpositive contrast variance')
        ses.append(np.sqrt(v*n/(n-4)))
    traditional=np.linalg.lstsq(np.column_stack([np.ones(valid.sum()),m[valid]]),y[valid],rcond=None)[0][1];influence=np.zeros(len(m));influence[on]=w*res/(1-h)
    out.update(status='estimated',beta_traditional=traditional,beta_minus=coef[2],beta_plus=coef[2]+coef[3],delta=coef[3],se_hac5=ses[0],se_hc3_hac5=ses[1],ci_low=coef[3]-norm.ppf(.975)*ses[0],ci_high=coef[3]+norm.ppf(.975)*ses[0])
    return out,influence

def masks(m,y,dates,influence,ticker):
    missing=~np.isfinite(y);out={}
    for radius in [1,5]:
        drop=np.zeros(len(y),bool)
        for k in np.flatnonzero(missing):drop[max(0,k-radius):min(len(y),k+radius+1)]=True
        out[f'neighbor{radius}_known_missing_returns']=~drop
    out['Light_2024Q4']=~((dates>=pd.Timestamp('2024-10-01'))&(dates<=pd.Timestamp('2024-12-31'))) if ticker=='LIGT3.SA' else np.ones(len(y),bool)
    order=np.argsort(-abs(influence),kind='stable');eligible=np.isfinite(y)&np.isfinite(m)&(m!=0);order=order[eligible[order]]
    for n in [1,5]:
        keep=np.ones(len(y),bool);keep[order[:n]]=False;out[f'remove{n}_largest_absolute_observation_influence']=keep
    return out

def run(d):
    rows=[];ledger=[];removed=[]
    for panel in d['panels']:
        scenario=panel['scenario'];ref=d['matrices']['referencia_n'][scenario];m=ref['^BVSP'].to_numpy();dates=ref.index
        for row in panel['sample'].itertuples():
            y=ref[row.ticker].to_numpy();base,inf=fit(m,y);assert base['status']=='estimated';choices=masks(m,y,dates,inf,row.ticker);baseid=dict(scenario=scenario,papel_id=row.papel_id,ticker=row.ticker,setor_economico=row.setor_economico)
            points=[];shifts=[]
            for variant in VARIANTS:
                values=d['matrices'][variant][scenario][row.ticker].to_numpy();np.testing.assert_array_equal(np.isnan(values),np.isnan(y));result,_=fit(m,values);points.append(result['delta']);rows.append(dict(**baseid,reference=variant,diagnostic='unmasked',removed_valid=0,**result,delta_shift=result['delta']-base['delta']))
            for name,keep in choices.items():
                result,_=fit(m,y,keep);shift=result.get('delta',np.nan)-base['delta'];shifts.append(shift);ids=np.flatnonzero(~keep&np.isfinite(y));rows.append(dict(**baseid,reference='referencia_n',diagnostic=name,removed_valid=len(ids),**result,delta_shift=shift))
                for k in ids:removed.append(dict(**baseid,diagnostic=name,date=str(dates[k].date()),observed_return=y[k],full_model_delete_one_delta_shift=-inf[k]))
            rank=np.argsort(-abs(inf),kind='stable');denom=abs(inf).sum();local='pending_ANIM3' if row.ticker=='ANIM3.SA' else 'not_reclassified_by_this_extension';cash='published_inventory_extracted_chronology_open' if row.ticker=='FRAS3.SA' else 'inherited_global_cash_identity_quantity_borders_open'
            ledger.append(dict(**baseid,global_homologated=False,documentary_status=cash,local_status=local,n_missing=int(np.isnan(y).sum()),**base,conditional_scenario_delta_min=min(points),conditional_scenario_delta_max=max(points),conditional_scenario_delta_spread=max(points)-min(points),max_absolute_diagnostic_shift=float(np.nanmax(abs(np.array(shifts)))),largest_absolute_delete_one_delta_shift=float(abs(inf).max()),top1_absolute_influence_share=float(abs(inf[rank[:1]]).sum()/denom),top5_absolute_influence_share=float(abs(inf[rank[:5]]).sum()/denom),slope_log_return_if_market_plus1pct=.01*base['beta_plus'],slope_log_return_if_market_minus1pct=-.01*base['beta_minus'],scale_scope='slope only; no intercept, residual, wealth adjustment or forecast'))
    return dict(economic_ledger=pd.DataFrame(ledger),economic_sensitivities=pd.DataFrame(rows),economic_removed_observations=pd.DataFrame(removed))
