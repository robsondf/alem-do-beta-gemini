#!/usr/bin/env python3
"""Extract target turnover and December2015prices from11existing authenticated B3ZIPs.
All daily quotes remain private;no provider download or return replacement.
"""
from pathlib import Path
import argparse,zipfile,hashlib,json,re,time
import pandas as pd
p=argparse.ArgumentParser();p.add_argument('--b3-cache',type=Path,required=True);p.add_argument('--i-output',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();out=a.output;out.mkdir(parents=True,exist_ok=True)
ids=set(pd.read_csv(a.i_output/'gaps_preserved/returns_private.csv.gz',index_col=0,nrows=0).columns)
records=[];closing=[];start=time.monotonic();cache=a.b3_cache;manifest=json.loads((cache/'authenticated_manifest.json').read_text())
for meta in sorted(manifest,key=lambda x:x['name']):
 p=cache/meta['name'];assert hashlib.sha256(p.read_bytes()).hexdigest()==meta['sha256'];year=int(p.name[10:14]);count=0
 with zipfile.ZipFile(p) as z:
  member=next(x for x in z.namelist() if x.upper().endswith('.TXT'))
  for b in z.open(member):
   if b[:2]!=b'01' or b[10:12]!=b'02' or b[24:27]!=b'010':continue
   isin=b[230:242].decode().strip();date=b[2:10].decode();ticker=b[12:24].decode().strip()
   if year==2015 and date>='20151201' and re.fullmatch(r'[A-Z0-9]{4}([3-8]|11)',ticker):closing.append((date,ticker,isin,int(b[108:121])/100/int(b[210:217]),int(b[170:188])/100,b[27:39].decode('latin-1').strip(),b[39:49].decode('latin-1').strip()))
   if isin not in ids:continue
   records.append((date,isin,ticker,int(b[170:188])/100,int(b[108:121])/100/int(b[210:217]),int(b[152:170]),int(b[147:152])));count+=1
 print(year,count,'reused target records',round(time.monotonic()-start,1),'s',flush=True)
d=pd.DataFrame(records,columns=['date','papel_id','ticker','volume','close','quantity_traded','trades']);d=d.sort_values('volume').drop_duplicates(['date','papel_id'],keep='last');d.to_csv(out/'turnover_private.csv.gz',index=False)
pd.DataFrame(closing,columns=['date','ticker','papel_id','close','volume','issuer_short','class']).to_csv(out/'prices2015_private.csv.gz',index=False)
print('done',len(d),flush=True)
