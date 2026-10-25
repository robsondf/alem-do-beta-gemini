#!/usr/bin/env python3
"""Read bounded prefixes of original CVM2015 filings and verify complete XML members.

Filing endpoints ignore HTTP Range. Only a bounded response prefix is read;the
unfinished outer FRE/archive is never certified. Complete nested XMLs each have
their declared size and ZIP CRC checked. No attachment or executable is run.
"""
import argparse,concurrent.futures,hashlib,json,struct,urllib.request,zlib
from pathlib import Path
import xml.etree.ElementTree as ET
import pandas as pd

def members(raw,partial=False):
    i=0;found={}
    while i+30<=len(raw) and raw[i:i+4]==b'PK\x03\x04':
        h=struct.unpack_from('<4s5H3L2H',raw,i);assert not(h[2]&9)
        name=raw[i+30:i+30+h[9]].decode();start=i+30+h[9]+h[10];end=start+h[7]
        if end>len(raw):
            if partial and h[3]==8:found[name]=zlib.decompressobj(-15).decompress(raw[start:])
            break
        b=zlib.decompress(raw[start:end],-15) if h[3]==8 else raw[start:end]
        assert len(b)==h[8] and zlib.crc32(b)==h[6],name
        found[name]=b;i=end
    return found

def collect(row,output):
    code=int(row.CD_CVM);folder=output/str(code);folder.mkdir(parents=True,exist_ok=True)
    receipt=folder/'source.json'
    if receipt.exists():
        result=json.loads(receipt.read_text())
        for name,sha in result['XML_sha256'].items():assert hashlib.sha256((folder/name).read_bytes()).hexdigest()==sha
        return result
    url=row.LINK_DOC.replace('http:','https:')+'&descTipo=FRE';needed=['Documento.xml','CapitalSocial.xml'];wanted=needed+['DistribuicaoCapitalSocial.xml','DesdobramentoGrupamentoBonificacao.xml','AumentoCapitalEmissor.xml','ReducaoCapitalEmissor.xml','ValorMobiliarioMantidoTesourariaNegocios.xml']
    for limit in [262144,1048576]:
        with urllib.request.urlopen(url,timeout=30) as response:
            prefix=response.read(limit)
        outer=members(prefix,partial=True);fre=[b for name,b in outer.items() if name.endswith('.fre')]
        if len(fre)!=1:continue
        inner=members(fre[0]);
        if all(name in inner for name in needed):break
    else:raise ValueError('Required complete XML unavailable:'+str(code))
    document=ET.fromstring(inner['Documento.xml']);tags={e.tag.split('}')[-1]:e.text for e in document.iter() if e.text and e.text.strip()}
    assert int(tags['CodigoCvm'])==code
    assert tags['NumeroCnpjCompanhiaAberta'].zfill(14)==''.join(x for x in row.CNPJ_CIA if x.isdigit()).zfill(14)
    assert int(document.findtext('NumeroVersaoDocumento'))==int(row.VERSAO)
    assert row.DT_RECEB<='2015-12-31'
    saved={}
    for name in wanted:
        if name in inner:
            ET.fromstring(inner[name]);(folder/name).write_bytes(inner[name]);saved[name]=hashlib.sha256(inner[name]).hexdigest()
    result=dict(codeCVM=code,CNPJ=row.CNPJ_CIA,ID_DOC=int(row.ID_DOC),version=int(row.VERSAO),received=row.DT_RECEB,url=url,prefix_bytes_read=len(prefix),prefix_sha256=hashlib.sha256(prefix).hexdigest(),full_archive_downloaded=False,outer_archive_CRC_not_claimed=True,complete_XML_members_CRC_verified=True,XML_sha256=saved)
    receipt.write_text(json.dumps(result,indent=2)+'\n');print('2015 original',code,row.DT_RECEB,len(prefix),'bytes',flush=True);return result

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--master',type=Path,required=True);p.add_argument('--mapping',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();master=pd.read_csv(a.master,sep=';',encoding='latin-1');codes=pd.read_csv(a.mapping).codeCVM.dropna().astype(int).unique();master=master[master.CD_CVM.isin(codes)&master.DT_RECEB.le('2015-12-31')].sort_values(['DT_RECEB','VERSAO','ID_DOC']).drop_duplicates('CD_CVM',keep='last');results=[];errors=[]
    with concurrent.futures.ThreadPoolExecutor(8) as pool:
        jobs={pool.submit(collect,row,a.output):int(row.CD_CVM) for row in master.itertuples()}
        for future in concurrent.futures.as_completed(jobs):
            try:results.append(future.result())
            except Exception as e:errors.append(dict(codeCVM=jobs[future],error=repr(e)));print('source error',errors[-1],flush=True)
    (a.output/'collection.json').write_text(json.dumps(dict(files=results,errors=errors),indent=2)+'\n')
    print('Originals complete',len(results),'errors',len(errors),flush=True)
