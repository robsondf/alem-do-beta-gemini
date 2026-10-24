#!/usr/bin/env python3
"""Independent OLS/rank/bootstrap oracle; imports no production module."""
import argparse,json
from pathlib import Path
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]


def adjusted(p):
    p=np.asarray(p);order=np.argsort(p);out=np.empty(len(p));run=0.
    for rank,j in enumerate(order):run=max(run,(len(p)-rank)*p[j]);out[j]=min(1,run)
    return out


def corr(x,y):
    a=pd.Series(x).rank(method='average').to_numpy();b=pd.Series(y).rank(method='average').to_numpy();a-=a.mean();b-=b.mean();return a.dot(b)/np.sqrt(a.dot(a)*b.dot(b))


def verify(out):
    all_assoc=pd.read_csv(out/'liquidity_all_variants.csv');liq=pd.read_csv(out/'liquidity_2015_full.csv.gz').groupby('papel_id').volume_financeiro.sum()/246;maximum=0.;explicit=0;complete=0;points_checked=0
    universe=pd.read_csv(ROOT/'data/lab03i/review_reference/universo_2015.csv',index_col=0);l=pd.read_csv(out/'liquidity_2015_full.csv.gz');g=l.groupby('papel_id').agg(dias=('data','nunique'),vol=('volume_financeiro','sum'));g['presence']=g.dias/246;g['adtv']=g.vol/246;eligible=g[g.presence>=.9].sort_values('adtv',ascending=False);assert len(eligible)==211;assert eligible.head(80).index.tolist()==universe.index.tolist()
    for variant,folder,filename in [('external_diagnostic',out,'external_log_price_changes_private.csv.gz'),('gaps_preserved',out/'gaps_preserved','returns_private.csv.gz')]:
        frame=pd.read_csv(folder/filename,index_col=0,parse_dates=True,float_precision='round_trip');m=pd.read_csv(folder/'market_private.csv.gz',index_col=0,parse_dates=True,float_precision='round_trip')['market'];assert frame.index.equals(m.index);R=frame.to_numpy();M=m.to_numpy();early=frame.index.year<=2020;parts={'early':np.flatnonzero(early),'late':np.flatnonzero(~early),'decada':np.arange(len(m))};point={};okay={}
        def direct(ii,j):
            yy=R[ii,j];mm=M[ii];slopes=[]
            for sign in [1,-1]:
                v=np.isfinite(yy)&np.isfinite(mm)&(mm*sign>0)
                if v.sum()<2 or np.ptp(mm[v])==0:slopes.append(np.nan)
                else:slopes.append(np.linalg.lstsq(np.column_stack([np.ones(v.sum()),mm[v]]),yy[v],rcond=None)[0][1])
            return slopes[0]-slopes[1]
        for name,ii in parts.items():
            point[name]=np.array([direct(ii,j) for j in range(R.shape[1])]);v=np.isfinite(R[ii]);nn=v.sum(0);okay[name]=(nn>=200)&((v&(M[ii,None]>0)).sum(0)>=60)&((v&(M[ii,None]<0)).sum(0)>=60)&(nn/len(ii)>=.95)
        point['theta']=point['late']-point['early'];okay['theta']=okay['early']&okay['late'];ids={}
        for name in ['universo_2015','originais_COTAHIST']:
            asset=pd.read_csv(folder/f'assets_{name}.csv').set_index('papel_id');ids[name]=[frame.columns.get_loc(i) for i in asset.index]
            for target in ['early','late','decada']:
                jj=ids[name];np.testing.assert_allclose(asset['d_'+target],point[target][jj],atol=1e-10,rtol=1e-9,equal_nan=True);np.testing.assert_array_equal(asset['ok_'+target],okay[target][jj]);points_checked+=len(jj)
        aggregate=pd.read_csv(folder/'aggregate_reproduced.csv');association=pd.read_csv(folder/'liquidity_joint.csv');bank=np.load(folder/'bootstrap_draws.npz');assert len(bank.files)==60
        for row in aggregate.itertuples():
            ii=np.array(ids[row.universo]);keep=ii[okay[row.alvo][ii]];expected=np.mean(point[row.alvo][keep]) if row.resumo=='media' else np.median(point[row.alvo][keep]);assert len(keep)==row.N;assert abs(expected-row.est)<1e-10;b=bank[f'{row.universo}_{row.alvo}_{row.resumo}_{row.bloco}'];q=np.quantile(b-row.est,[.025,.975]);pv=(1+np.sum(abs(b-row.est)>=abs(row.est)))/5000;np.testing.assert_allclose([pv,row.est-q[1],row.est-q[0]],[row.p,row.ic_inf,row.ic_sup],atol=1e-10,rtol=1e-9);complete+=1
        for (_,block),grp in aggregate.groupby(['universo','bloco']):
            for tt in [['early','theta'],['late'],['decada']]:
                a=grp[grp.alvo.isin(tt)];np.testing.assert_allclose(adjusted(a.p),a.p_holm,atol=1e-12)
        cohorts={'original80':ids['originais_COTAHIST'],'union118':list(range(R.shape[1]))}
        for row in association.itertuples():
            ii=np.array(cohorts[row.cohort]);keep=ii[okay[row.target][ii]];x=liq.reindex(frame.columns[keep]).to_numpy();expected=corr(x,point[row.target][keep]);assert abs(expected-row.estimate)<1e-10 and len(keep)==row.N;b=bank[f'liquidity_{row.cohort}_{row.target}_{row.block}'];q=np.quantile(b-row.estimate,[.025,.975]);pv=(1+np.sum(abs(b-row.estimate)>=abs(row.estimate)))/5000;np.testing.assert_allclose([pv,row.estimate-q[1],row.estimate-q[0]],[row.p_centered,row.ci_low,row.ci_high],atol=1e-10,rtol=1e-9);complete+=1
        for block,g in association.groupby('block'):np.testing.assert_allclose(adjusted(g.p_centered),g.p_holm4,atol=1e-12)
        for block in [21,5,63]:
            rng=np.random.default_rng(20261024+block);sample={}
            for name in ['early','late']:
                ii=parts[name];T=len(ii);starts=rng.integers(0,T-block+1,size=(4999,(T+block-1)//block));sample[name]=ii[(starts[:3,:,None]+np.arange(block)).reshape(3,-1)[:,:T]]
            for b in range(3):
                d={k:np.array([direct(ii[b],j) for j in range(R.shape[1])]) for k,ii in sample.items()};d['theta']=d['late']-d['early'];d['decada']=np.array([direct(np.concatenate([sample['early'][b],sample['late'][b]]),j) for j in range(R.shape[1])])
                for row in aggregate[aggregate.bloco.eq(block)].itertuples():
                    ii=np.array(ids[row.universo]);keep=ii[okay[row.alvo][ii]];e=np.mean(d[row.alvo][keep]) if row.resumo=='media' else np.median(d[row.alvo][keep]);a=bank[f'{row.universo}_{row.alvo}_{row.resumo}_{block}'][b];maximum=max(maximum,float(abs(a-e)));assert abs(a-e)<1e-10;explicit+=1
                for row in association[association.block.eq(block)].itertuples():
                    ii=np.array(cohorts[row.cohort]);keep=ii[okay[row.target][ii]];e=corr(liq.reindex(frame.columns[keep]),d[row.target][keep]);a=bank[f'liquidity_{row.cohort}_{row.target}_{block}'][b];maximum=max(maximum,float(abs(a-e)));assert abs(a-e)<1e-10;explicit+=1
    for block,g in all_assoc.groupby('block'):np.testing.assert_allclose(adjusted(g.p_centered),g.p_holm8,atol=1e-12)
    gaps=pd.read_csv(out/'documented_gaps.csv');assert len(gaps)==7
    protected=pd.read_csv(out/'gaps_preserved/returns_private.csv.gz',index_col=0)
    for row in gaps.itertuples():assert np.isnan(protected.loc[row.date,row.papel_id])
    lag_count=0;lag_max=0.
    if (out/'lag_asset_points.csv').is_file():
        lagrows=pd.read_csv(out/'lag_asset_points.csv');mm=pd.read_csv(ROOT/'data/lab03i/review_reference/market_returns_2015_2025.csv.gz',index_col=0,parse_dates=True,float_precision='round_trip')['market'];calendar=frame.index
        for K,sub in lagrows.groupby('K'):
            Z=np.column_stack([mm.shift(j).reindex(calendar) for j in range(int(K)+1)]);good=np.isfinite(Z).all(axis=1)&(Z[:,0]!=0)
            for row in sub[sub.status.eq('ok')].itertuples():
                window=calendar.year<=2020 if row.period=='early' else (calendar.year>=2021 if row.period=='late' else np.ones(len(calendar),bool));yy=frame[row.papel_id].to_numpy();v=good&window&np.isfinite(yy);slopes=[]
                for sign in [-1,1]:
                    use=v&(Z[:,0]*sign>0);coef=np.linalg.lstsq(np.column_stack([np.ones(use.sum()),Z[use]]),yy[use],rcond=None)[0];slopes.append(coef[1:].sum())
                error=max(abs(slopes[0]-row.beta_minus),abs(slopes[1]-row.beta_plus),abs(slopes[1]-slopes[0]-row.delta));assert error<1e-10;lag_max=max(lag_max,error);lag_count+=1
    record={'passed':True,'production_imported':False,'eligible_2015_submitted_BDI02_filter':211,'reported_broad_liquidity_cache_eligible':221,'top80_exact_order_reproduced':True,'asset_period_points_and_flags_checked':points_checked,'complete_CI_p_rows':complete,'explicit_row_resampled_aggregate_and_rank_statistics':explicit,'max_direct_draw_difference':maximum,'documented_missing_cells_protected':7,'bootstrap_vectors_verified':120,'bootstrap_values':599880,'separate_regime_lag_fits_checked':lag_count,'max_lag_difference':lag_max,'scope':'Computational/measurement consistency;not calibrated association size/coverage,economic event validation or causal selection identification'}
    (out/'independent_verification.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record,indent=2));return record


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);verify(p.parse_args().output)
