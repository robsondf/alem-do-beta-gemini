#!/usr/bin/env python3
"""Documented ticker-continuity sensitivity;primary ISIN matrices remain unchanged."""
import argparse,hashlib,json,sys,zipfile
from pathlib import Path
import numpy as np
import pandas as pd
from threadpoolctl import threadpool_limits
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from lab03j import estimates,block_weights,spearman,summarize,holm
def run(cache,i_output,turnover,output):
 plan=json.loads((ROOT/'data/lab03j/adendo_sucessoes_v1.json').read_text());ids={q['new_ISIN'] for q in plan['pairs']};records=[]
 for f in sorted(cache.glob('COTAHIST_A*.ZIP')):
  year=int(f.name[10:14])
  if year<2016:continue
  expected=next(q for q in json.loads((cache/'authenticated_manifest.json').read_text()) if q['name']==f.name);assert hashlib.sha256(f.read_bytes()).hexdigest()==expected['sha256']
  with zipfile.ZipFile(f) as z:
   member=next(n for n in z.namelist() if n.upper().endswith('.TXT'))
   for b in z.open(member):
    if b[:2]!=b'01' or b[10:12]!=b'02' or b[24:27]!=b'010':continue
    isin=b[230:242].decode().strip()
    if isin in ids:records.append((b[2:10].decode(),isin,int(b[108:121])/100/int(b[210:217]),int(b[170:188])/100))
  print('J succession cache',year,flush=True)
 quote=pd.DataFrame(records,columns=['date','isin','close','volume']);quote['date']=pd.to_datetime(quote.date,format='%Y%m%d');quote=quote.sort_values('volume').drop_duplicates(['date','isin'],keep='last')
 r=pd.read_csv(i_output/'gaps_preserved/returns_private.csv.gz',index_col=0,parse_dates=True,float_precision='round_trip');m=pd.read_csv(i_output/'market_private.csv.gz',index_col=0,parse_dates=True).iloc[:,0].reindex(r.index);old=pd.read_csv(turnover);old['date']=pd.to_datetime(old.date.astype(str),format='%Y%m%d');linked=r.copy();transitions=[];flags=[]
 for q in plan['pairs']:
  new=quote[quote['isin'].eq(q['new_ISIN'])].set_index('date').close.reindex(r.index);ret=np.log(new/new.shift());start=pd.Timestamp(q['effective']);j=r.index.get_loc(start);previous=old[old.papel_id.eq(q['old_ISIN'])&old.date.eq(r.index[j-1])];adjacent=len(previous)==1 and np.isfinite(new.loc[start])
  if adjacent:ret.loc[start]=np.log(new.loc[start]/float(previous.iloc[0].close))
  else:ret.loc[start]=np.nan
  K=np.array([1.25,1.5,2.5,2,3,4,5,8,10])
  for d,v in ret.loc[start:].dropna().items():
   ratio=np.exp(v);md=float(m.loc[d]);near=np.minimum(abs(ratio/K-1),abs(ratio*K-1)).min()<.02
   if abs(v)>.20 and (abs(v-md)>=np.log(2) or (near and abs(v)>=.35 and abs(md)<.05)):flags.append(dict(anchor=q['old_ISIN'],date=str(d.date()),log_return=v));ret.loc[d]=np.nan
  linked.loc[start:,q['old_ISIN']]=ret.loc[start:];transitions.append(dict(old=q['old'],new=q['new'],date=q['effective'],adjacent_sessions=bool(adjacent),factor=1,transition_return=float(ret.loc[start]) if adjacent else None,source=q['source']))
 assert np.array_equal(np.isnan(r.drop(columns=[q['old_ISIN'] for q in plan['pairs']])),np.isnan(linked.drop(columns=[q['old_ISIN'] for q in plan['pairs']])));
 before=linked.index.year<=2020;R=linked.loc[before].to_numpy();M=m.loc[before].to_numpy();valid=np.isfinite(R);eligible=(valid.sum(0)>=200)&((valid&(M>0)[:,None]).sum(0)>=60)&((valid&(M<0)[:,None]).sum(0)>=60)&(valid.mean(0)>=.95)
 for q in plan['pairs']:
  if q['new_ISIN'] in linked.columns:assert not (eligible[linked.columns.get_loc(q['old_ISIN'])] and eligible[linked.columns.get_loc(q['new_ISIN'])]),'Duplicate eligible lineage'
 output.mkdir(parents=True,exist_ok=True)
 pd.DataFrame({'papel_id':linked.columns,'eligible_early_linked':eligible,'lineage_anchor':linked.columns.isin([q['old_ISIN'] for q in plan['pairs']])}).to_csv(output/'succession_early_eligibility.csv',index=False)
 liquidity=old[old.date.dt.year.eq(2015)].groupby('papel_id').volume.sum()/246;point=estimates(R,M,np.ones((1,len(M))))[0];u=pd.read_csv(ROOT/'data/lab03i/review_reference/universo_2015.csv').papel_id;rows=[];bank={}
 for L in [21,5,63]:
  w,_=block_weights(len(M),L,np.random.default_rng(20261026+L),4999);draws=estimates(R,M,w)[0]
  for cohort,keep in [('universe2015',linked.columns.isin(u)),('union118',np.ones(118,bool))]:
   jj=np.flatnonzero(keep&eligible);liq=np.log(liquidity.reindex(linked.columns[jj]).to_numpy());assert np.isfinite(liq).all()
   for target,p,b in [('early_mean',point[0,jj].mean(),draws[:,jj].mean(1)),('liquidity_rank',spearman(liq,point[:,jj])[0],spearman(np.broadcast_to(liq,(4999,len(jj))),draws[:,jj]))]:
    rows.append(dict(cohort=cohort,target=target,block=L,N=len(jj),**summarize(p,b)));bank[f'{cohort}_{target}_{L}']=b
 table=pd.DataFrame(rows);table['p_holm4']=np.nan
 for L,g in table.groupby('block'):table.loc[g.index,'p_holm4']=holm(g.p)
 output.mkdir(parents=True,exist_ok=True);table.to_csv(output/'succession_sensitivity.csv',index=False);pd.DataFrame(transitions).to_csv(output/'succession_transitions.csv',index=False);pd.DataFrame(flags,columns=['anchor','date','log_return']).to_csv(output/'succession_new_flags.csv',index=False);np.savez_compressed(output/'succession_draws.npz',**bank);linked.to_csv(output/'succession_returns_private.csv.gz')
 return table
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--b3-cache',type=Path,required=True);p.add_argument('--i-output',type=Path,required=True);p.add_argument('--turnover',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
 with threadpool_limits(limits=2):print(run(a.b3_cache,a.i_output,a.turnover,a.output).query('block==21').to_string(index=False))
