#!/usr/bin/env python3
"""Independent raw-moment checks; imports no production modules."""
from pathlib import Path
import argparse,json,zipfile,hashlib
import numpy as np
import pandas as pd

def validate(x_archive,y_archive,output):
    with zipfile.ZipFile(x_archive) as z:
        matrices={v:{s:pd.read_csv(z.open(f'matrices/{v}/{s}/retornos_logaritmicos.csv.gz'),compression='gzip',index_col=0,parse_dates=True,float_precision='round_trip') for s in ['decada','recente']} for v in ['referencia_n','jcp_duas_celulas_documentadas','jcp_condicional','jcp_rendimento_caixa_baixo','jcp_rendimento_caixa_alto']}
    full=pd.read_csv(output/'risk_full.csv');annual=pd.read_csv(output/'risk_annual.csv');errors=[];checked=0
    for table,yearly in [(full,False),(annual,True)]:
        for row in table.itertuples():
            scenario='recente' if row.scenario=='decada_periodo_comum' else row.scenario
            matrix=matrices[row.cash_variant][scenario]
            if yearly:matrix=matrix[matrix.index.year==row.year]
            y=matrix[row.ticker].to_numpy();m=matrix['^BVSP'].to_numpy();ok=np.isfinite(y)&np.isfinite(m);y=y[ok];m=m[ok];n=len(y)
            assert n==row.n_pairs and len(matrix)-n==row.n_missing
            assert int((m>0).sum())==row.n_plus and int((m<0).sum())==row.n_minus
            coef=np.linalg.lstsq(np.column_stack([np.ones(n),m]),y,rcond=None)[0];e=y-coef[0]-coef[1]*m
            total=np.var(y,ddof=1);associated=coef[1]**2*np.var(m,ddof=1);residual=np.var(e,ddof=1)
            losses=np.sort(-np.expm1(y))[::-1];mass=n*.05;weights=np.clip(mass-np.arange(n),0,1)
            expected={'beta_market_model':coef[1],'intercept_market_model':coef[0],'log_std_daily':np.std(y,ddof=1),
                'total_log_variance':total,'market_associated_log_variance':associated,'residual_log_variance':residual,
                'r2_market_model':1-np.sum(e**2)/np.sum((y-y.mean())**2),'downside_log_deviation_zero':np.sqrt(np.mean(np.minimum(y,0)**2)),
                'var95_simple_loss':np.sort(-np.expm1(y))[int(np.ceil(.95*n))-1],'es95_simple_loss':np.sum(losses*weights)/mass}
            for name,value in expected.items():
                actual=getattr(row,name);np.testing.assert_allclose(actual,value,rtol=1e-9,atol=1e-12);errors.append(abs(actual-value))
            checked+=1
    assert checked==3170
    b=pd.read_csv(output/'asset_betas.csv');checks=pd.read_csv(output/'bootstrap_y_check.csv')
    intervals=pd.read_csv(output/'sector_bootstrap.csv');etas=pd.read_csv(output/'sector_eta.csv')
    with zipfile.ZipFile(y_archive) as z:old=pd.read_csv(z.open('bootstrap.csv'))
    max_boot=0.;draw_count=0;cache={}
    def slopes(y,m):
        out=[]
        valid=np.isfinite(y)&np.isfinite(m[:,None]);count=valid.sum(axis=0)
        for mask in [valid&(m[:,None]>0),valid&(m[:,None]<0)]:
            k=mask.sum(axis=0);xx=np.where(mask,m[:,None],0);yy=np.where(mask,y,0)
            den=np.sum(xx*xx,axis=0)-np.sum(xx,axis=0)**2/k
            num=np.sum(xx*yy,axis=0)-np.sum(xx,axis=0)*np.sum(yy,axis=0)/k
            good=(count>=200)&(count/len(m)>=.95)&(k>=60)&(den/(k-1)>=1e-12)
            out.append(np.where(good,num/den,np.nan))
        return out[0]-out[1]
    def eta(v,labels):
        den=np.sum((v-v.mean())**2)
        return sum(np.count_nonzero(labels==s)*(v[labels==s].mean()-v.mean())**2 for s in np.unique(labels))/den
    for scenario,offset in [('decada',0),('recente',1)]:
        meta=b[b.scenario.eq(scenario)].sort_values('papel_id');mat=matrices['referencia_n'][scenario]
        y=mat[meta.ticker].to_numpy();m=mat['^BVSP'].to_numpy()
        for length in [5,10,20]:
            rng=np.random.default_rng(np.random.SeedSequence([20261011,offset,length]));draws=[]
            for _ in range(999):
                starts=rng.integers(0,len(m)-length+1,size=(len(m)+length-1)//length)
                ix=np.concatenate([np.arange(s,s+length) for s in starts])[:len(m)]
                draws.append(slopes(y[ix],m[ix]));draw_count+=1
            draws=np.asarray(draws);cache[(scenario,length)]=(meta,draws)
            original=old[old.scenario.eq(scenario)&old.block_length.eq(length)].set_index('papel_id').loc[meta.papel_id]
            se=np.nanstd(draws,axis=0,ddof=1);np.testing.assert_allclose(se,original.bootstrap_se,rtol=1e-9,atol=1e-12)
    common_ids=set(b[b.scenario.eq('decada_periodo_comum')].papel_id)
    for scenario in ['decada','recente','decada_periodo_comum']:
        for length in [5,10,20]:
            meta,draws=cache[('recente' if scenario=='decada_periodo_comum' else scenario,length)]
            if scenario=='decada_periodo_comum':
                take=meta.papel_id.isin(common_ids).to_numpy();meta=meta[take];draws=draws[:,take]
            labels=meta.setor_economico.to_numpy();draws=draws[np.isfinite(draws).all(axis=1)]
            for sector in sorted(set(labels)):
                q=labels==sector;values=np.median(draws[:,q],axis=1)-np.median(draws[:,~q],axis=1);bounds=np.quantile(values,[.025,.975])
                row=intervals[intervals.scenario.eq(scenario)&intervals.block_length.eq(length)&intervals.setor_economico.eq(sector)].iloc[0]
                np.testing.assert_allclose([row.ci_low,row.ci_high],bounds,rtol=1e-9,atol=1e-12)
                max_boot=max(max_boot,float(np.max(np.abs(bounds-[row.ci_low,row.ci_high]))));assert row.accepted==len(draws)
            values=np.array([eta(v,labels) for v in draws]);bounds=np.quantile(values,[.025,.975])
            row=etas[etas.scenario.eq(scenario)&etas.block_length.eq(length)].iloc[0]
            np.testing.assert_allclose([row.ci_low,row.ci_high],bounds,rtol=1e-9,atol=1e-12)
    # Same asset/year is not a second independent observation in the common panel.
    for table,keys in [(full,['cash_variant','papel_id']),(annual,['papel_id','year'])]:
        recent=table[table.scenario.eq('recente')].set_index(keys)
        common=table[table.scenario.eq('decada_periodo_comum')].set_index(keys)
        pd.testing.assert_frame_equal(recent.loc[common.index].drop(columns='scenario'),common.drop(columns='scenario'),check_exact=True)
    assert len(checks)==831 and len(intervals)==90 and len(etas)==9 and draw_count==5994
    return dict(risk_rows_checked=checked,maximum_direct_risk_difference=max(errors),bootstrap_draws_independently_reproduced=draw_count,
        sector_intervals_checked=90,eta_intervals_checked=9,Y_bootstrap_rows_reused=831,
        maximum_sector_bound_difference=max_boot,common_assets_exact_reuse=True,production_modules_imported=False,
        CAPM_pricing_tested=False,global_homologated=0)

if __name__=='__main__':
    p=argparse.ArgumentParser()
    for name in ['x-archive','y-archive','output']:p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();print(json.dumps(validate(a.x_archive,a.y_archive,a.output),indent=2))
