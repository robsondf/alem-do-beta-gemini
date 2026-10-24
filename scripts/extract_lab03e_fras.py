#!/usr/bin/env python3
"""Read-only extraction of the archived primary XLSX; dates retained, not fixed."""
import datetime,hashlib,json,zipfile,xml.etree.ElementTree as ET
from pathlib import Path
import pandas as pd
ROOT=Path(__file__).resolve().parents[1];FOLDER=ROOT/'data/lab03e/primary'
NS={'m':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
def extract(path):
 with zipfile.ZipFile(path) as z:
  strings=[''.join(si.itertext()) for si in ET.fromstring(z.read('xl/sharedStrings.xml'))];rows=[]
  for raw in ET.fromstring(z.read('xl/worksheets/sheet1.xml')).findall('.//m:sheetData/m:row',NS):
   row={}
   for cell in raw:
    value=cell.find('m:v',NS)
    if value is None or value.text is None:continue
    if cell.find('m:f',NS) is not None and int(raw.attrib['r'])>=9:raise ValueError('Unreviewed formula in source data')
    row[''.join(c for c in cell.attrib['r'] if c.isalpha())]=strings[int(value.text)] if cell.attrib.get('t')=='s' else value.text
   if row.get('C') not in ['JSCP','Dividendos remanescentes']:continue
   def date(col):return (datetime.datetime(1899,12,30)+datetime.timedelta(days=float(row[col]))).date().isoformat()
   a,p,e=date('B'),date('I'),date('L');rows.append(dict(sheet='Dividendos e JSCP',source_row=int(raw.attrib['r']),approval=a,type=row['C'],event=row['D'],reference_period=row['E'],amount_source=row['F'],cash_ON_source=row['G'],cash_PN_source=row['H'],payment=p,competence=row['J'],cash_year=row['K'],ex_source=e,ex_in_2016_2025='2016-01-01'<=e<='2025-12-31',ex_in_2021_2025='2021-01-01'<=e<='2025-12-31',ex_before_approval=e<a,payment_before_approval=p<a,automatically_corrected=False))
 return pd.DataFrame(rows)
if __name__=='__main__':
 raw=FOLDER/'fras_cash.xlsx';meta=json.loads((FOLDER/'retrieval.json').read_text());assert hashlib.sha256(raw.read_bytes()).hexdigest()==meta[0]['sha256'];df=extract(raw);df.to_csv(FOLDER/'fras_published_cash_inventory.csv',index=False)
 old=pd.read_csv(ROOT/'data/lab02/semantica_caixa_v1/recuperacao_fras_visivel_2024_2025.csv');print('Old published rows columns:',list(old.columns));print(old.to_string(index=False));print('New extraction:',len(df),'rows; historical ex-window:',int(df.ex_in_2016_2025.sum()),'recent:',int(df.ex_in_2021_2025.sum()));print(df[df.ex_before_approval|df.payment_before_approval].to_string(index=False))
 record=dict(source_sha256=meta[0]['sha256'],rows=len(df),historical_ex_rows=int(df.ex_in_2016_2025.sum()),recent_ex_rows=int(df.ex_in_2021_2025.sum()),chronology_flags=int((df.ex_before_approval|df.payment_before_approval).sum()),full_published_table_extracted=True,issuer_history_completeness_proven=False,dates_corrected=False,returns_modified=False,global_homologated=0)
 (FOLDER/'fras_extraction_audit.json').write_text(json.dumps(record,indent=2)+'\n')
