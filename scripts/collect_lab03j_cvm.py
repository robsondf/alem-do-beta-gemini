#!/usr/bin/env python3
"""Selected official CVM ZIP members only,ETag pinned and CRC/hash verified."""
import argparse,concurrent.futures,datetime,hashlib,json,struct,urllib.request,zlib
from pathlib import Path
def collect(year,output):
 output.mkdir(parents=True,exist_ok=True);receipt=output/'source.json'
 if receipt.exists():
  old=json.loads(receipt.read_text())
  for f in old['files']:assert hashlib.sha256((output/f['name']).read_bytes()).hexdigest()==f['sha256']
  return old
 url=f'https://dados.cvm.gov.br/dados/CIA_ABERTA/DOC/FRE/DADOS/fre_cia_aberta_{year}.zip'
 with urllib.request.urlopen(urllib.request.Request(url,headers={'Range':'bytes=-65557'}),timeout=30) as r:
  assert r.status==206;tail=r.read();etag=r.headers['ETag'];size=int(r.headers['Content-Range'].split('/')[-1])
 assert len(tail)==65557;pos=tail.rfind(b'PK\x05\x06');h=struct.unpack_from('<4s4H2LH',tail,pos);assert h[1]==h[2]==0 and h[3]==h[4] and h[7]==0
 cd=tail[h[6]-(size-len(tail)):pos];assert len(cd)==h[5];entries=[];i=0
 while i<len(cd):
  x=struct.unpack_from('<4s6H3L5H2L',cd,i);assert x[0]==b'PK\x01\x02';n,e,c=x[10:13];name=cd[i+46:i+46+n].decode();entries.append(dict(name=name,method=x[4],crc32=x[7],compressed_bytes=x[8],raw_bytes=x[9],offset=x[16]));i+=46+n+e+c
 (output/'directory.json').write_text(json.dumps(entries,indent=2)+'\n')
 selected=[e for e in entries if e['name']==f'fre_cia_aberta_{year}.csv' or (year in [2014,2015] and ('capital_social' in e['name'] or 'tesouraria_ultimo' in e['name'])) or (year not in [2014,2015] and 'capital_social_desdobramento' in e['name'])]
 def ranged(start,end):
  with urllib.request.urlopen(urllib.request.Request(url,headers={'Range':f'bytes={start}-{end}','If-Match':etag}),timeout=30) as r:
   assert r.status==206 and r.headers['ETag']==etag and r.headers['Content-Range']==f'bytes {start}-{end}/{size}';b=r.read();assert len(b)==end-start+1;return b
 def get(e):
  h=ranged(e['offset'],e['offset']+29);x=struct.unpack('<4s5H3L2H',h);assert x[0]==b'PK\x03\x04' and x[3]==e['method'];b=ranged(e['offset']+30,e['offset']+29+x[9]+x[10]+e['compressed_bytes']);assert b[:x[9]].decode()==e['name'];c=b[x[9]+x[10]:];raw=zlib.decompress(c,-15) if e['method']==8 else c;assert len(raw)==e['raw_bytes'] and zlib.crc32(raw)==e['crc32'];(output/e['name']).write_bytes(raw);return dict(e,sha256=hashlib.sha256(raw).hexdigest(),transferred_bytes=30+len(b))
 with concurrent.futures.ThreadPoolExecutor(6) as pool:files=list(pool.map(get,selected))
 result=dict(year=year,url=url,etag=etag,archive_bytes=size,full_archive_downloaded=False,archive_sha256=None,directory_sha256=hashlib.sha256(cd).hexdigest(),tail_sha256=hashlib.sha256(tail).hexdigest(),transferred_bytes=len(tail)+sum(f['transferred_bytes'] for f in files),retrieved_UTC=datetime.datetime.now(datetime.timezone.utc).isoformat(),files=files)
 receipt.write_text(json.dumps(result,indent=2)+'\n');print('CVM',year,len(files),'members',result['transferred_bytes'],'bytes',flush=True);return result
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--years',nargs='+',type=int,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
 with concurrent.futures.ThreadPoolExecutor(4) as pool:list(pool.map(lambda y:collect(y,a.output/str(y)),a.years))
