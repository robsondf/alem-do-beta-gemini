#!/usr/bin/env python3
"""One bounded batch from authenticated J turnover and protected I returns."""
import argparse,hashlib,json,sys,time
from pathlib import Path
import numpy as np
import pandas as pd
from threadpoolctl import threadpool_limits
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from lab03j import estimates,block_weights,holm
from lab03k import design,coefficients,joint,floors,marginal_rows

def prepare(i_output,j_batch):
    r=pd.read_csv(i_output/'gaps_preserved/returns_private.csv.gz',index_col=0,parse_dates=True,float_precision='round_trip');r=r.loc[r.index.year<=2020]
    m=pd.read_csv(i_output/'market_private.csv.gz',index_col=0,parse_dates=True,float_precision='round_trip').iloc[:,0].reindex(r.index)
    out=j_batch/'outputs_J';c=pd.read_csv(out/'covariates_used.csv',float_precision='round_trip').set_index('papel_id').reindex(r.columns)
    audit=pd.read_csv(out/'complete_case_audit.csv');events=pd.read_csv(out/'event_audit_83.csv');v=pd.read_csv(j_batch/'private_inputs/turnover_private.csv.gz');v['date']=pd.to_datetime(v.date.astype(str),format='%Y%m%d')
    m15=pd.read_csv(ROOT/'data/lab03i/review_reference/market_returns_2015_2025.csv.gz',index_col=0,parse_dates=True,float_precision='round_trip').iloc[:,0].loc['2015']
    close=v.pivot(index='date',columns='papel_id',values='close').reindex(index=m15.index,columns=r.columns)
    # Consecutive market sessions only: pandas arithmetic never fills gaps.
    with np.errstate(divide='ignore',invalid='ignore'):r15=np.log(close/close.shift())
    for e in events.itertuples():
        date=pd.Timestamp(e.date)
        if date in r15.index and e.isin in r15:r15.loc[date,e.isin]=np.nan
    r15=r15.where(np.isfinite(r15));vol15=v.pivot(index='date',columns='papel_id',values='volume').reindex(index=m15.index,columns=r.columns)
    good=(vol15>0)&r15.notna();ami=(np.abs(np.expm1(r15))/vol15).where(good)
    n=ami.notna().sum();ami=ami.mean().where((n>=200)&(n/len(m15)>=.95)&(ami.mean()>0))
    c['log_amihud_2015']=np.log(ami);c['beta2015_ok']=floors(r15.to_numpy(),m15.to_numpy())
    c['unmatched_event_asset']=c.index.isin(events.loc[events.status.eq('no_matching_capital_record_in_recovered_tables'),'isin'])
    ids={k:r.columns.get_indexer(audit.query('cohort==@k and included').papel_id) for k in ['original80','union118']}
    return r,m,c,r15,m15,ids,v

def run(i_output,j_batch,output):
    start=time.monotonic();output.mkdir(parents=True,exist_ok=False)
    r,m,c,r15,m15,ids,v=prepare(i_output,j_batch);assert tuple(len(ids[k]) for k in ids)==(62,76)
    R=r.to_numpy();M=m.to_numpy();R15=r15.to_numpy();M15=m15.to_numpy();protected=np.isfinite(R).copy()
    point=estimates(R,M,np.ones((1,len(M))));b15=estimates(R15,M15,np.ones((1,len(M15))))[1]
    rows=[];tests=[];elig=[];bank={};max_equivalence=0.
    for L in [21,5,63]:
        w,_=block_weights(len(M),L,np.random.default_rng(20261025+L),4999);d,_=estimates(R,M,w);Y=np.vstack([point[0],d])
        w15,_=block_weights(len(M15),L,np.random.default_rng(20261027+L),4999);bb15=np.vstack([b15,estimates(R15,M15,w15)[1]])
        for cohort,base in ids.items():
            for model in ['reference','beta2015','exclude_unmatched','Amihud2015']:
                keep=np.ones(len(base),bool)
                if model=='beta2015':keep=c.iloc[base].beta2015_ok.to_numpy()
                if model=='exclude_unmatched':keep=~c.iloc[base].unmatched_event_asset.to_numpy()
                if model=='Amihud2015':keep=c.iloc[base].log_amihud_2015.notna().to_numpy()
                jj=base[keep];cc=c.iloc[jj];meta=dict(cohort=cohort,model=model,block=L,N=len(jj))
                if L==21:
                    for j,included in zip(base,keep):elig.append(dict(cohort=cohort,model=model,papel_id=r.columns[j],included=bool(included),beta2015_ok=bool(c.iloc[j].beta2015_ok),unmatched_event_asset=bool(c.iloc[j].unmatched_event_asset),amihud2015_available=bool(np.isfinite(c.iloc[j].log_amihud_2015))))
                x=cc.log_amihud_2015.to_numpy() if model=='Amihud2015' else cc.log_liquidity_2015.to_numpy()
                try:
                    X,labels=design(x,cc.log_size.to_numpy(),cc.sector.to_numpy())
                    coef=coefficients(Y[:,jj],X,bb15[:,jj] if model=='beta2015' else None)
                    if model=='beta2015':labels=labels+['beta2015']
                    meta.update(parameters=len(labels),residual_df=len(jj)-len(labels));rows+=marginal_rows(coef,labels,meta)
                    tests.append(dict(**meta,**joint(coef[0,1:3],coef[1:,1:3])));bank[f'{cohort}_{model}_{L}']=coef
                    if model=='reference':
                        Xg=X.copy();Xg[:,1]=X[:,1]-X[:,2];cg=coefficients(Y[:,jj],Xg)
                        expected=coef.copy();expected[:,2]=coef[:,1]+coef[:,2]
                        err=max(float(np.max(abs(cg-expected))),float(np.max(abs(cg@Xg.T-coef@X.T))))
                        assert err<1e-9;max_equivalence=max(max_equivalence,err)
                        jg=joint(cg[0,1:3],cg[1:,1:3]);assert jg['p']==tests[-1]['p']
                        rows+=marginal_rows(cg,labels,dict(meta,model='turnover_equivalent'));bank[f'{cohort}_turnover_equivalent_{L}']=cg
                except ValueError as e:
                    tests.append(dict(**meta,status=str(e),p=np.nan))
        print('K observed block',L,'finished',flush=True)
    t=pd.DataFrame(tests);t['p_holm_family']=np.nan;t['family']=''
    for (L,ref),g in t.groupby(['block',t.model.eq('reference')]):
        assert len(g)==(2 if ref else 6);t.loc[g.index,'p_holm_family']=holm(g.p.fillna(1));t.loc[g.index,'family']='reference_joint_Holm2' if ref else 'sensitivity_joint_Holm6'
    pd.DataFrame(rows).to_csv(output/'coefficients.csv',index=False);t.to_csv(output/'joint_tests.csv',index=False);pd.DataFrame(elig).to_csv(output/'eligibility.csv',index=False)
    c.to_csv(output/'covariates.csv');r15.to_csv(output/'preperiod_returns_private.csv.gz');np.savez_compressed(output/'draws_private.npz',**bank)
    # Descriptive observed history is not a delisting database.
    external=pd.read_csv(ROOT/'data/lab03i/review_reference/universo_2015.csv',index_col=0).index
    inventory=[]
    aliases={'KROT3':'COGN3','ESTC3':'YDUQ3','TBLE3':'EGIE3'}
    for isin in external:
        q=v[v.papel_id.eq(isin)].sort_values('date');original=bool(c.loc[isin,'original80']) if isin in c.index else False
        if original:continue
        ticks=list(q.ticker.drop_duplicates());known=[f'{a}->{b}' for a,b in aliases.items() if a in ticks]
        inventory.append(dict(papel_id=isin,first_observed=str(q.date.min().date()) if len(q) else '',last_observed=str(q.date.max().date()) if len(q) else '',observed_tickers=';'.join(ticks),documented_alias=';'.join(known),economic_exit_status='not established from observed quotation endpoints',primary_ISIN_unchanged=True))
    pd.DataFrame(inventory).to_csv(output/'succession_inventory.csv',index=False)
    assert np.array_equal(protected,np.isfinite(R));record=dict(stage='Lab03K',B=4999,blocks=[21,5,63],rows=len(rows),joint_tests=len(t),protected_missing_unchanged=True,reparameterization_max_error=max_equivalence,environment='local_not_author_Colab',elapsed_seconds=time.monotonic()-start)
    (output/'execution.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--i-output',type=Path,required=True);p.add_argument('--j-batch',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    with threadpool_limits(limits=2):run(a.i_output,a.j_batch,a.output)
