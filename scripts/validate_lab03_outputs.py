#!/usr/bin/env python3
"""Independent temporal audit. Imports a prior independent checker, no production modules."""
import argparse
import hashlib
import json
import math
import sys
from pathlib import Path
import zipfile

import numpy as np
import pandas as pd

from validate_lab02y_outputs import direct


def events(index,ticker):
    dates={'ABCB4.SA':[('2016-01-04','2016-01-05')],
           'UGPA3.SA':[('2021-06-28','2021-06-30')],
           'LIGT3.SA':[('2024-10-30','2024-10-30')],
           'PCAR3.SA':[('2021-03-01','2021-03-01'),('2023-08-23','2023-08-23')]}
    mask=np.ones(len(index),bool)
    for lo,hi in dates.get(ticker,[]):
        if not ((index>=lo)&(index<=hi)).any():continue
        a,b=index.searchsorted(lo),index.searchsorted(hi,side='right')
        mask[max(0,a-5):min(len(index),b+5)]=False
    if ticker=='LIGT3.SA':mask &= ~((index>='2024-10-01')&(index<='2024-12-31'))
    return mask


def joint(y,m,include,late,lag):
    mask=include&np.isfinite(y)&np.isfinite(m)&(m!=0)
    x=np.nan_to_num(m);d=(m>0).astype(float);q=late.astype(float)
    X=np.column_stack([np.ones(len(m)),d,x,d*x,q,q*d,q*x,q*d*x]);a=X[mask]
    coef=np.linalg.lstsq(a,y[mask],rcond=None)[0]
    scores=np.zeros_like(X);scores[mask]=a*(y[mask]-a@coef)[:,None]
    meat=scores.T@scores
    for k in range(1,lag+1):
        cross=scores[k:].T@scores[:-k];meat+=(1-k/(lag+1))*(cross+cross.T)
    bread=np.linalg.inv(a.T@a);cov=mask.sum()/(mask.sum()-8)*bread@meat@bread
    se=math.sqrt(cov[7,7]);theta=coef[7]
    return dict(theta=theta,theta_se=se,theta_ci_low=theta-1.959963984540054*se,
                theta_ci_high=theta+1.959963984540054*se,
                theta_p=math.erfc(abs(theta/se)/math.sqrt(2)),
                early_delta_joint=coef[3],late_delta_joint=coef[3]+coef[7],
                cross_covariance_early_late=cov[3,3]+cov[3,7])


def validate(root,x_archive,output):
    manifest=json.loads((output/'manifesto_exports.json').read_text())
    for name,digest in manifest.items():assert hashlib.sha256((output/name).read_bytes()).hexdigest()==digest,name
    plan=json.loads((root/'data/lab03/plano_execucao_v1.json').read_text());specs={c['name']:c for c in plan['configurations']}
    with zipfile.ZipFile(x_archive) as z:
        matrices={(v,s):pd.read_csv(z.open(name),compression='gzip',index_col=0,parse_dates=True,float_precision='round_trip')
                  for name in z.namelist() if name.startswith('matrices/') for _,v,s,_ in [name.split('/')]}
    annual,halves,family,common,rolling=[pd.read_csv(output/(n+'.csv'),float_precision='round_trip')
                                         for n in ['annual','halves','temporal_family','common_directions','rolling']]
    prepared={}
    def inputs(configuration,scenario,ticker):
        key=configuration,scenario,ticker
        if key not in prepared:
            c=specs[configuration];m=matrices[c['cash_variant'],scenario]
            if c['return']=='simple':m=np.expm1(m)
            include=events(m.index,ticker) if c['events'] else np.ones(len(m),bool)
            prepared[key]=(m,include)
        return prepared[key]
    maxfit=0.;fit_count=0;insufficient=0
    for number,row in enumerate(annual.itertuples(),1):
        m,include=inputs(row.configuration,row.scenario,row.ticker);sel=m.index.year==row.year
        fit,ok=direct(m.loc[sel,row.ticker].to_numpy(),m.loc[sel,'^BVSP'].to_numpy(),include[sel],row.hac_lags)
        assert (row.status_conditional=='ok')==ok
        for key,value in fit.items():
            actual=getattr(row,key)
            if key.startswith('n_'):assert actual==value
            else:
                maxfit=max(maxfit,abs(actual-value));assert np.isclose(actual,value,atol=1e-10,rtol=1e-9),(row.ticker,key)
        if ok:fit_count+=1
        else:insufficient+=1;assert np.isnan(row.delta)
        if number%5000==0:print(f'Conferência independente: {number}/{len(annual)} linhas anuais',file=sys.stderr,flush=True)
    maxjoint=0.
    for row in halves.itertuples():
        m,include=inputs(row.configuration,'decada',row.ticker)
        fit=joint(m[row.ticker].to_numpy(),m['^BVSP'].to_numpy(),include,m.index.year>=2021,row.hac_lags)
        for key,value in fit.items():
            actual=getattr(row,key);maxjoint=max(maxjoint,abs(actual-value));assert np.isclose(actual,value,rtol=1e-9,atol=1e-10),key
        assert row.status=='ok' and row.covariance_identity_error<1e-12
        for name,select in [('early',m.index.year<2021),('late',m.index.year>=2021)]:
            point,ok=direct(m[row.ticker].to_numpy(),m['^BVSP'].to_numpy(),include&select,row.hac_lags)
            assert ok
            for key in ['n_pairs','n_plus','n_minus','delta','delta_se']:
                assert np.isclose(getattr(row,name+'_'+key),point[key],rtol=1e-9,atol=1e-10)
    for configuration,g in family.groupby('configuration',sort=False):
        assert len(g)==474 and g.test.eq('magnitude_late_minus_early').sum()==80
        a=annual[annual.configuration.eq(configuration)];h=halves[halves.configuration.eq(configuration)].set_index('papel_id')
        for row in g.itertuples():
            if row.test=='magnitude_late_minus_early':p=h.loc[row.papel_id,'theta_p']
            else:
                years=range(2016,2026) if row.scenario=='decada' else range(2021,2026)
                part=a[a.scenario.eq(row.scenario)&a.papel_id.eq(row.papel_id)].sort_values('year')
                assert part.year.tolist()==list(years)
                ok=part.status_conditional.eq('ok') & np.isfinite(part.delta_se) & part.delta_se.gt(1e-14)
                assert row.years_eligible==ok.sum()
                if ok.all():
                    sign=1 if row.direction=='positive' else -1
                    p=max(.5*math.erfc(sign*r.delta/r.delta_se/math.sqrt(2)) for r in part.itertuples())
                else:p=np.nan
            if np.isnan(p):assert np.isnan(row.p_raw)
            else:assert abs(p-row.p_raw)<1e-12
        p=g.p_raw.to_numpy();valid=np.flatnonzero(np.isfinite(p));order=valid[np.argsort(p[valid],kind='stable')]
        adjusted=np.full(len(g),np.nan);adjusted[order]=np.minimum(1,np.maximum.accumulate((474-np.arange(len(order)))*p[order]))
        np.testing.assert_allclose(adjusted,g.p_holm_474,atol=1e-12,rtol=1e-10,equal_nan=True)
        np.testing.assert_array_equal(np.isfinite(adjusted)&(adjusted<.05),g.reject_005_conditional)
        reused=common[common.configuration.eq(configuration)].set_index(['papel_id','direction'])
        recent=g[g.scenario.eq('recente')].set_index(['papel_id','direction']).loc[reused.index]
        assert len(reused)==160
        np.testing.assert_allclose(reused.p_holm_474,recent.p_holm_474,rtol=0,atol=0,equal_nan=True)
    maxrolling=0.
    for number,row in enumerate(rolling.itertuples(),1):
        m=matrices['referencia_n',row.scenario];start=m.index.get_loc(pd.Timestamp(row.window_start));stop=m.index.get_loc(pd.Timestamp(row.window_end))+1
        assert start%21==0 and stop-start==row.width and row.width in [252,504]
        x=m.iloc[start:stop];fit,ok=direct(x[row.ticker].to_numpy(),x['^BVSP'].to_numpy(),np.ones(len(x),bool),5)
        assert (row.status_conditional=='ok')==ok
        for key,value in fit.items():
            actual=getattr(row,key)
            if key.startswith('n_'):assert actual==value
            else:maxrolling=max(maxrolling,abs(actual-value));assert np.isclose(actual,value,rtol=1e-9,atol=1e-10),key
        if number%5000==0:print(f'Conferência independente: {number}/{len(rolling)} linhas móveis',file=sys.stderr,flush=True)
    keys=['papel_id','width','window_start','window_end'];a=rolling[rolling.scenario.eq('decada_periodo_comum')].set_index(keys);b=rolling[rolling.scenario.eq('recente')].set_index(keys).loc[a.index]
    for name in ['beta','beta_plus','beta_minus','delta','delta_se','n_pairs','n_plus','n_minus']:
        np.testing.assert_allclose(a[name],b[name],rtol=0,atol=0,equal_nan=True)
    return dict(annual_rows_checked=len(annual),annual_estimable=fit_count,annual_insufficient=insufficient,
                annual_direct_max_difference=maxfit,joint_models_checked=len(halves),joint_direct_max_difference=maxjoint,
                family_slots_checked=len(family),common_direction_rows_reused_checked=len(common),
                rolling_rows_checked=len(rolling),rolling_direct_max_difference=maxrolling,
                source_production_modules_imported=False,global_homologated=0,
                scope='conditional_temporal_tests_not_equivalence_or_future_persistence')


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1]);parser.add_argument('--x-archive',type=Path,required=True);parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    print(json.dumps(validate(args.root,args.x_archive,args.output),indent=2))
