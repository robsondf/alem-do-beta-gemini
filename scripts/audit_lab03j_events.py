#!/usr/bin/env python3
"""Cross all83 heuristic flags with official capital records;approval is not ex-date."""
import argparse,hashlib,json
from pathlib import Path
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]
def run(cvm_root,turnover,output):
 events=pd.read_csv(ROOT/'results/tables/lab03i_parecer_v4_20261024/events_reproduced.csv');mapping=pd.read_csv(ROOT/'data/lab03j/issuer_map.csv').set_index('papel_id');v=pd.read_csv(turnover);tables=[];sources=[]
 for p in sorted(cvm_root.glob('*/fre_cia_aberta_capital_social_desdobramento_*.csv')):
  d=pd.read_csv(p,sep=';',encoding='latin-1');d['source_member']=p.name;d['source_sha256']=hashlib.sha256(p.read_bytes()).hexdigest();tables.append(d);sources.append(dict(member=p.name,sha256=d.source_sha256.iloc[0] if len(d) else hashlib.sha256(p.read_bytes()).hexdigest(),rows=len(d)))
 capital=pd.concat(tables,ignore_index=True).drop_duplicates(['CNPJ_Companhia','Data_Aprovacao','Tipo_Evento','Quantidade_Total_Acoes_Antes_Aprovacao','Quantidade_Total_Acoes_Depois_Aprovacao']);capital['approval']=pd.to_datetime(capital.Data_Aprovacao);rows=[];candidates=[]
 for number,row in events.iterrows():
  info=mapping.loc[row['isin']];date=pd.Timestamp(row.data);part=capital[capital.CNPJ_Companhia.eq(info.CNPJ)&capital.approval.le(date)&capital.approval.ge(date-pd.Timedelta(days=180))].copy();possible=[]
  for _,q in part.iterrows():
   for kind in (['Ordinarias'] if row.ticker.endswith('3') else ['Preferenciais']):
    before=q.get(f'Quantidade_Acoes_{kind}_Antes_Aprovacao',0);after=q.get(f'Quantidade_Acoes_{kind}_Depois_Aprovacao',0)
    if before>0 and after>0:
     factor=after/before;error=abs(row.log_ret+np.log(factor)-row.ret_mercado)
     if abs(np.log(factor))>.15 and error<=.15:
      rec=dict(flag=number,isin=row['isin'],date=row.data,approval=q.Data_Aprovacao,type=q.Tipo_Evento,share_kind=kind,quantity_factor=factor,log_market_residual_after_factor=error,document_id=int(q.ID_Documento),member=q.source_member,source_sha256=q.source_sha256);possible.append(rec);candidates.append(rec)
  daily=v[v.papel_id.eq(row['isin'])].sort_values('date');qq=daily[daily.date.eq(int(row.data.replace('-','')))];tick=False
  if len(qq):
   pos=daily.index.get_indexer(qq.index)[0];current=float(qq.iloc[0].close);previous=float(daily.iloc[pos-1].close) if pos>0 else np.nan;tick=bool(max(current,previous)<=.10 and abs(abs(current-previous)-.01)<1e-8)
  status='capital_event_documented_consistent_factor' if possible else ('one_cent_price_grid_candidate' if tick else 'no_matching_capital_record_in_recovered_tables')
  rows.append(dict(flag=number,isin=row['isin'],ticker=row.ticker,date=row.data,inside2016_2025=date.year>=2016,log_return=row.log_ret,rule=row.regra,status=status,capital_candidates=len(possible),exact_ex_date_certified=False,one_cent_grid=tick,full_economic_adjustment_certified=False))
 ledger=pd.DataFrame(rows);assert len(ledger)==83;output.mkdir(parents=True,exist_ok=True);ledger.to_csv(output/'event_audit_83.csv',index=False);pd.DataFrame(candidates).to_csv(output/'event_capital_candidates.csv',index=False)
 record=dict(flags=83,status_counts=ledger.status.value_counts().to_dict(),inside_estimation=int(ledger.inside2016_2025.sum()),outside_estimation=int((~ledger.inside2016_2025).sum()),exact_ex_date_certifications=0,source_members=sources,scope='Cross-reference of disclosed capital movements and heuristic flags;approval dates/ratios do not certify exact ex dates,non-events,taxes or complete economic returns')
 (output/'event_audit_scope.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps({k:v for k,v in record.items() if k!='source_members'},indent=2));return ledger
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--cvm-root',type=Path,required=True);p.add_argument('--turnover',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();run(a.cvm_root,a.turnover,a.output)
