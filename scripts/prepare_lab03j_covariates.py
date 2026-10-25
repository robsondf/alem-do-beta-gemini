#!/usr/bin/env python3
"""Reproduce dated disclosed-share capitalization proxy;no network or missing-value imputation.
The archived count received by2015 is not certified exact yearend/free-float inventory.
Canonical issuer/sector mapping is separately sourced and versioned in issuer_map.csv.
"""
import argparse
from pathlib import Path
import pandas as pd
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
def run(cvm_root,prices,output):
 mapping=pd.read_csv(ROOT/'data/lab03j/issuer_map.csv')
 capital=pd.concat([pd.read_csv(cvm_root/f'{year}/fre_cia_aberta_capital_social_{year}.csv',sep=';',encoding='latin-1').assign(source_year=year) for year in [2014,2015]],ignore_index=True)
 masters=pd.concat([pd.read_csv(cvm_root/f'{year}/fre_cia_aberta_{year}.csv',sep=';',encoding='latin-1') for year in [2014,2015]],ignore_index=True).drop_duplicates(['CNPJ_CIA','ID_DOC'])
 c=capital[capital.Tipo_Capital.isin(['Capital Emitido','Capital Integralizado'])].copy();c=c[pd.to_datetime(c.Data_Autorizacao_Aprovacao).le('2015-12-31')];c['preference']=c.Tipo_Capital.map({'Capital Emitido':1,'Capital Integralizado':0})
 c=c.merge(masters[['CNPJ_CIA','ID_DOC','DT_RECEB','VERSAO']],left_on=['CNPJ_Companhia','ID_Documento'],right_on=['CNPJ_CIA','ID_DOC'],validate='many_to_one')
 c=c[c.DT_RECEB.le('2015-12-31')].sort_values(['CNPJ_Companhia','DT_RECEB','Data_Autorizacao_Aprovacao','preference','Data_Referencia','Versao','ID_Documento']).drop_duplicates('CNPJ_Companhia',keep='last')
 quotes=pd.read_csv(prices);quotes=quotes[quotes.date.eq(20151230)].copy();quotes['prefix']=quotes.ticker.str[:4]
 values=[]
 for prefix,sub in mapping.groupby('prefix'):
  cap=c[c.CNPJ_Companhia.isin(sub.CNPJ.dropna())];prices=quotes[quotes.prefix.eq(prefix)];row=dict(prefix=prefix,market_cap_2015=np.nan,status='no_dated_issued_capital',capital_filing_date=None,capital_effective_date=None,document_id=None,size_information_available_by_2015=False)
  if len(cap)==1:
   cap=cap.iloc[0];parts=[];status='ok';details=[]
   for kind,field,suffix in [('ON','Quantidade_Acoes_Ordinarias','3'),('PN','Quantidade_Acoes_Preferenciais','4')]:
    quantity=int(cap[field]);
    if quantity==0:continue
    candidates=prices[prices.ticker.eq(prefix+suffix)]
    if kind=='PN' and len(candidates)==0:
     candidates=prices[prices.ticker.str[-1].isin(['5','6','7','8'])]
     # A single quoted preferred class does not certify that all PN belong to it.
     if len(candidates)==1:
      cls=pd.read_csv(cvm_root/'2015/fre_cia_aberta_capital_social_classe_acao_2015.csv',sep=';',encoding='latin-1');cls=cls[(cls.ID_Documento.eq(cap.ID_Documento))&(cls.Quantidade_Acoes.eq(quantity))]
      if len(cls)==0:candidates=candidates.iloc[:0]
    if len(candidates)!=1:status='missing_or_ambiguous_class_price';break
    q=candidates.iloc[0];parts.append(quantity*q.close);details.append(f'{q.ticker}:{quantity}x{q.close}')
   row.update(status=status if status!='ok' else ('ok' if parts else 'no_positive_capital'),market_cap_2015=float(sum(parts)) if status=='ok' and parts else np.nan,capital_filing_date=cap.DT_RECEB,capital_effective_date=cap.Data_Autorizacao_Aprovacao,document_id=int(cap.ID_Documento),size_information_available_by_2015=cap.DT_RECEB<='2015-12-31',count_kind=cap.Tipo_Capital,capital_source_year=int(cap.source_year),components=';'.join(details))
  values.append(row)
 v=pd.DataFrame(values);output.mkdir(parents=True,exist_ok=True);v.to_csv(output/'size_source_audit.csv',index=False);a=mapping.merge(v,on='prefix',validate='many_to_one');a['log_size']=np.log(a.market_cap_2015);a.to_csv(output/'covariates_2015.csv',index=False)
 return a
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--cvm-root',type=Path,required=True);p.add_argument('--prices',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();q=run(a.cvm_root,a.prices,a.output);print('dated-size assets:',q.log_size.notna().sum(),'of',len(q))
