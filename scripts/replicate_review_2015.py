#!/usr/bin/env python3
"""Reviewed independent reconstruction of the external 2015 experiment.

No submitted Python/pickle is executed. Official cached ZIPs stay external.
This reproduces the heuristic mask; it does not validate economic events.
"""
import argparse,gzip,hashlib,io,json,os,re,time,zipfile
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.stats import rankdata
from threadpoolctl import threadpool_limits

ROOT=Path(__file__).resolve().parents[1]


def atomic_matrix(frame,path):
    raw=frame.to_csv().encode();payload=gzip.compress(raw,mtime=0);temporary=path.with_suffix('.part')
    with temporary.open('wb') as stream:stream.write(payload);stream.flush();os.fsync(stream.fileno())
    temporary.replace(path)
    with gzip.open(path,'rb') as stream:assert stream.read()==raw


def digest(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def holm(p):
    p=np.asarray(p);ix=np.argsort(p);a=np.empty(len(p));a[ix]=np.minimum(1,np.maximum.accumulate(p[ix]*np.arange(len(p),0,-1)));return a


def extract(cache,ids,out):
    records=[];all2015=[]
    manifest=json.loads((cache/'authenticated_manifest.json').read_text())
    for q in sorted(manifest,key=lambda x:x['name']):
        path=cache/q['name'];assert digest(path)==q['sha256'];year=int(q['name'][10:14]);count=0
        with zipfile.ZipFile(path) as z:
            members=[x for x in z.namelist() if x.upper().endswith('.TXT')];assert len(members)==1
            for line in io.TextIOWrapper(z.open(members[0]),encoding='latin-1'):
                if line[:2]!='01' or line[10:12]!='02' or line[24:27]!='010' or line[39:49].strip().startswith('DR'):continue
                ticker=line[12:24].strip()
                if re.fullmatch(r'[A-Z0-9]{4}([3-8]|11)',ticker) is None:continue
                isin=line[230:242].strip();date=line[2:10];vol=int(line[170:188])/100
                if year==2015:all2015.append((date,ticker,isin,vol))
                if isin not in ids:continue
                factor=int(line[210:217]);assert factor>0
                records.append((date,ticker,isin,int(line[108:121])/100/factor,vol));count+=1
        print('I official cached',year,count,'target rows',flush=True)
    p=pd.DataFrame(records,columns=['data','ticker','isin','preult','voltot']);p['data']=pd.to_datetime(p.data,format='%Y%m%d')
    duplicate=p[p.duplicated(['data','isin'],False)];duplicate.to_csv(out/'duplicate_records.csv',index=False)
    l=pd.DataFrame(all2015,columns=['data','ticker','papel_id','volume_financeiro']);l.to_csv(out/'liquidity_2015_full.csv.gz',index=False)
    p=p.sort_values('voltot').drop_duplicates(['data','isin'],keep='last');return p,l


def reconstruct(p,ibov,out):
    if ibov.is_file():
        ib=pd.read_csv(ibov,parse_dates=['data']).set_index('data').ibov;m=np.log(ib/ib.shift())
    else:m=pd.read_csv(ibov.parent/'market_returns_2015_2025.csv.gz',index_col=0,parse_dates=True,float_precision='round_trip')['market']
    assert m.index.is_unique and m.index.is_monotonic_increasing
    c=p.pivot(index='data',columns='isin',values='preult').reindex(m.index);r=np.log(c/c.shift());events=[];K=np.array([1.25,1.5,2.5,2,3,4,5,8,10])
    for col in r:
        for d,v in np.exp(r[col].dropna()).items():
            lr=float(np.log(v));md=float(m.get(d,np.nan))
            if abs(lr)<=.20:continue
            near=np.minimum(abs(v/K-1),abs(v*K-1)).min()<.02;big=abs(lr-(md if np.isfinite(md) else 0))>=np.log(2);standard=near and abs(lr)>=.35 and abs(md)<.05
            if big or standard:events.append((col,str(d.date()),round(lr,4),'|r-m|>=ln2' if big else 'fator padrão',round(md,4)));r.loc[d,col]=np.nan
    tk=p.groupby('isin').ticker.last();e=pd.DataFrame(events,columns=['isin','data','log_ret','regra','ret_mercado']);e['ticker']=e['isin'].map(tk);e.to_csv(out/'events_reproduced.csv',index=False)
    r=r.iloc[1:];m=m.iloc[1:];return r.loc['2016-01-01':'2025-12-31'],m.loc['2016-01-01':'2025-12-31']


def sufficient(W,R,M):
    out={}
    for g,mask in [('up',M>0),('dn',M<0)]:
        v=np.isfinite(R)&mask[:,None];r=np.where(v,R,0.);m=np.where(v,M[:,None],0.);out[g]=dict(n=W@v.astype(float),Sm=W@m,Smm=W@(m*m),Sr=W@r,Srm=W@(r*m))
    return out


def delta(s):
    def beta(v):
        with np.errstate(divide='ignore',invalid='ignore'):return (v['Srm']-v['Sr']*v['Sm']/v['n'])/(v['Smm']-v['Sm']**2/v['n'])
    return beta(s['up'])-beta(s['dn'])


def add(a,b):return {g:{k:a[g][k]+b[g][k] for k in a[g]} for g in a}


def floors(R,M):
    v=np.isfinite(R);n=v.sum(0);return (n>=200)&((v&(M>0)[:,None]).sum(0)>=60)&((v&(M<0)[:,None]).sum(0)>=60)&(n/len(M)>=.95)


def weights(T,L,rng,B):
    starts=rng.integers(0,T-L+1,size=(B,(T+L-1)//L));ix=(starts[:,:,None]+np.arange(L)).reshape(B,-1)[:,:T];w=np.zeros((B,T),dtype=np.float32)
    for j,row in enumerate(ix):w[j]=np.bincount(row,minlength=T)
    return w,ix[:3]


def estimate(r,m,universes,out,liquidity):
    B=4999;before=r.index.year<=2020;R={k:r.loc[mask].to_numpy() for k,mask in [('early',before),('late',~before)]};M={k:m.loc[mask].to_numpy() for k,mask in [('early',before),('late',~before)]};ok={k:floors(R[k],M[k]) for k in R};ok['decada']=floors(r.to_numpy(),m.to_numpy());obs={k:sufficient(np.ones((1,len(M[k]))),R[k],M[k]) for k in R};points={k:delta(obs[k])[0] for k in R};points['decada']=delta(add(obs['early'],obs['late']))[0];points['theta']=points['late']-points['early'];ok['theta']=ok['early']&ok['late'];rows=[];bank={};oracles=[];association=[]
    for L in [21,5,63]:
        rng=np.random.default_rng(20261024+L);bs={};indices={}
        for k in ['early','late']:
            W,indices[k]=weights(len(M[k]),L,rng,B);bs[k]=sufficient(W,R[k],M[k]);del W
        draws={k:delta(bs[k]) for k in ['early','late']};draws['decada']=delta(add(bs['early'],bs['late']));draws['theta']=draws['late']-draws['early']
        for name,ids in universes.items():
            jj=np.array([r.columns.get_loc(i) for i in ids]);per=pd.DataFrame({'papel_id':ids,**{f'ok_{k}':ok[k][jj] for k in ['early','late','decada']},**{f'd_{k}':points[k][jj] for k in ['early','late','decada']}})
            if L==21:per.to_csv(out/('assets_'+name+'.csv'),index=False)
            for target in ['early','theta','decada','late']:
                keep=jj[ok[target][jj]];o=points[target][keep];d=draws[target][:,keep];invalid=int((~np.isfinite(d)).sum());assert invalid==0,(name,target,L,invalid)
                for label,fn in [('media',np.mean),('mediana',np.median)]:
                    point=float(fn(o));b=fn(d,axis=1);q=np.quantile(b-point,[.025,.975]);pv=(1+np.count_nonzero(abs(b-point)>=abs(point)))/(B+1);rows.append(dict(universo=name,alvo=target,resumo=label,N=len(keep),est=point,p=pv,ic_inf=point-q[1],ic_sup=point-q[0],bloco=L,invalid_draws=invalid));bank[f'{name}_{target}_{label}_{L}']=b
            # Explicit-row OLS for three deterministic draws and three eligible assets.
            keep=jj[ok['theta'][jj]][:3]
            for b in range(3):
                for j in keep:
                    values=[]
                    for k in ['early','late']:
                        ii=indices[k][b];mm=M[k][ii];yy=R[k][ii,j];valid=np.isfinite(yy)&(mm!=0);D=mm>0;X=np.column_stack([np.ones(len(mm)),D,mm,D*mm]);coef=np.linalg.lstsq(X[valid],yy[valid],rcond=None)[0];values.append(coef[3])
                    error=abs((values[1]-values[0])-draws['theta'][b,j]);assert error<1e-10;oracles.append(error)
        for cohort,ids in [('original80',universes['originais_COTAHIST']),('union118',list(r.columns))]:
            jj=np.array([r.columns.get_loc(i) for i in ids])
            for target in ['early','theta']:
                keep=jj[ok[target][jj]];names=r.columns[keep];li=liquidity.reindex(names);assert li.notna().all(),'unknown2015 liquidity'
                x=rankdata(li.to_numpy());x=x-x.mean();y=rankdata(points[target][keep]);y=y-y.mean();point=float(x@y/np.sqrt((x@x)*(y@y)))
                yb=rankdata(draws[target][:,keep],axis=1);yb=yb-yb.mean(axis=1,keepdims=True);vb=(yb@x)/np.sqrt((x@x)*np.sum(yb*yb,axis=1));invalid=int((~np.isfinite(vb)).sum());assert invalid==0
                q=np.quantile(vb-point,[.025,.975]);pv=(1+np.count_nonzero(abs(vb-point)>=abs(point)))/(B+1)
                association.append(dict(cohort=cohort,target=target,N=len(keep),block=L,estimate=point,p_centered=pv,ci_low=point-q[1],ci_high=point-q[0],invalid_draws=invalid,bootstrap_mean=vb.mean(),bootstrap_bias=vb.mean()-point,bootstrap_se=vb.std(ddof=1)));bank[f'liquidity_{cohort}_{target}_{L}']=vb
        print('I all universes block',L,'completed',flush=True)
    df=pd.DataFrame(rows);df['p_holm']=np.nan
    for (_,L),g in df.groupby(['universo','bloco']):
        for targets in [['early','theta'],['decada'],['late']]:
            ix=g.index[g.alvo.isin(targets)];df.loc[ix,'p_holm']=holm(df.loc[ix,'p'])
    assoc=pd.DataFrame(association);assoc['p_holm4']=np.nan
    for L,g in assoc.groupby('block'):assoc.loc[g.index,'p_holm4']=holm(g.p_centered)
    assoc.to_csv(out/'liquidity_joint.csv',index=False)
    df.to_csv(out/'aggregate_reproduced.csv',index=False);np.savez_compressed(out/'bootstrap_draws.npz',**bank);return df,dict(explicit_row_OLS_theta_checks=len(oracles),max_difference=max(oracles),invalid_draws=0)


def main():
    a=argparse.ArgumentParser();a.add_argument('--b3-cache',type=Path,required=True);a.add_argument('--review-dir',type=Path,required=True);a.add_argument('--x-archive',type=Path,required=True);a.add_argument('--output',type=Path,required=True);p=a.parse_args();lock=json.loads((ROOT/'data/lab03i/inputs_manifest.json').read_text());assert digest(p.x_archive)==lock['X_sha256']
    for name,expected in lock['source_pins'].items():assert digest(ROOT/name)==expected,name
    p.output.mkdir(parents=True,exist_ok=False);start=time.monotonic();u=pd.read_csv(p.review_dir/'universo_2015.csv',index_col=0);inv=pd.read_csv(ROOT/'results/tables/resposta_pareceres_20261024/inventario_117.csv');universes={'universo_2015':list(u.index),'originais_COTAHIST':list(inv[inv.in_decade_80].papel_id)};ids=set(sum(universes.values(),[]));raw,l=extract(p.b3_cache,ids,p.output);r,m=reconstruct(raw,p.review_dir/'ibov.csv',p.output)
    # Private matrices are solely for independent verification and Colab exports.
    atomic_matrix(r,p.output/'external_log_price_changes_private.csv.gz');m.to_csv(p.output/'market_private.csv.gz',header=['market'])
    liquidity=l.groupby('papel_id').volume_financeiro.sum()/246
    with threadpool_limits(limits=2):df,oracle=estimate(r,m,universes,p.output,liquidity)
    expected=pd.read_csv(p.review_dir/'resultados_agregados.csv');keys=['universo','bloco','alvo','resumo'];pd.testing.assert_frame_equal(df[expected.columns].set_index(keys).sort_index(),expected.set_index(keys).sort_index(),check_exact=False,atol=1e-10,rtol=1e-9)
    expected_events=pd.read_csv(p.review_dir/'eventos_detectados.csv');pd.testing.assert_frame_equal(pd.read_csv(p.output/'events_reproduced.csv'),expected_events)
    assert digest(p.x_archive)=='297da2afde534082c398324f308df7af134c9692e7d61d6e0b2b820341ea5214'
    with zipfile.ZipFile(p.x_archive) as z:reference=pd.read_csv(z.open('matrices/referencia_n/decada/retornos_logaritmicos.csv.gz'),compression='gzip',index_col=0,parse_dates=True,float_precision='round_trip')
    controlled=r.copy();gaps=[];by_ticker=inv[inv.in_decade_80].set_index('ticker').papel_id
    for ticker in reference.columns:
        if ticker=='^BVSP':continue
        isin=by_ticker[ticker]
        for d in reference.index[reference[ticker].isna()]:
            gaps.append(dict(date=str(d.date()),ticker=ticker,papel_id=isin,external_was_finite=bool(np.isfinite(r.loc[d,isin]))));controlled.loc[d,isin]=np.nan
    assert len(gaps)==7;pd.DataFrame(gaps).to_csv(p.output/'documented_gaps.csv',index=False)
    gapout=p.output/'gaps_preserved';gapout.mkdir();atomic_matrix(controlled,gapout/'returns_private.csv.gz');m.to_csv(gapout/'market_private.csv.gz',header=['market'])
    with threadpool_limits(limits=2):gapdf,gaporacle=estimate(controlled,m,universes,gapout,liquidity)
    associations=[]
    for variant,directory in [('external_diagnostic',p.output),('gaps_preserved',gapout)]:
        a=pd.read_csv(directory/'liquidity_joint.csv');a.insert(0,'variant',variant);associations.append(a)
    combined=pd.concat(associations,ignore_index=True);combined['p_holm8']=np.nan
    for L,g in combined.groupby('block'):combined.loc[g.index,'p_holm8']=holm(g.p_centered)
    combined.to_csv(p.output/'liquidity_all_variants.csv',index=False)
    record={'date':'2026-10-24','environment':os.environ.get('ALEM_BETA_EXECUTION_ENV','local_not_author_Colab'),'complete_reconstruction':True,'official_cached_ZIPs':11,'new_quote_downloads':False,'calendar_rows_2016_2025':len(r),'ISINs':len(r.columns),'aggregate_rows':len(df),'event_flags_reproduced':len(expected_events),'documented_missing_cells_preserved_in_separate_variant':len(gaps),'gap_preserved_oracle':gaporacle,'association_targets_blocks_variants':len(combined),'oracle':oracle,'original_80_117_replaced':False,'economically_validated_events':False,'external_weak_null_calibration':False,'elapsed_seconds':time.monotonic()-start}
    (p.output/'replication.json').write_text(json.dumps(record,indent=2)+'\n')
    for artifact in p.output.rglob('*'):
        if artifact.is_file():
            with artifact.open('rb') as stream:os.fsync(stream.fileno())
    print(json.dumps(record,indent=2))


if __name__=='__main__':main()
