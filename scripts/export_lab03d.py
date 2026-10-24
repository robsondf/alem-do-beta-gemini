#!/usr/bin/env python3
"""Complete authenticated export; precompressed arrays are not recompressed."""
import argparse,hashlib,json,os,platform,zipfile
from datetime import datetime,timezone
from pathlib import Path
import numpy,pandas,scipy,matplotlib,fitz,PIL
ROOT=Path(__file__).resolve().parents[1]
def export(output,destination):
 environment=os.environ.get('ALEM_BETA_EXECUTION_ENV','local preparation')
 record=dict(stage='Lab03D',environment=environment,executed_utc=datetime.now(timezone.utc).isoformat(),python=platform.python_version(),numpy=numpy.__version__,pandas=pandas.__version__,scipy=scipy.__version__,matplotlib=matplotlib.__version__,pymupdf=fitz.VersionBind,pillow=PIL.__version__,static_family=197,temporal_family=474,calibration_per_mechanism=9999,validation_per_mechanism=1000,prospective_untouched_holdout=False,global_homologated=0,all_limitations_eliminated=False)
 (output/'registro_execucao.json').write_text(json.dumps(record,indent=2)+'\n')
 for p in (ROOT/'data/lab03d').glob('*.json'):
  if p.name.startswith(('plano','adendo','inputs_','runtime_')):(output/p.name).write_bytes(p.read_bytes())
 files=sorted(p for p in output.rglob('*') if p.is_file() and p.name!='manifesto_exports.json' and p.suffix!='.stage');manifest={str(p.relative_to(output)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files};(output/'manifesto_exports.json').write_text(json.dumps(manifest,indent=2)+'\n')
 with zipfile.ZipFile(destination,'w') as z:
  for p in files+[output/'manifesto_exports.json']:z.write(p,str(p.relative_to(output)),compress_type=zipfile.ZIP_STORED if p.suffix in ['.npz','.gz'] else zipfile.ZIP_DEFLATED)
 print('Export:',destination.name,'|',len(manifest),'arquivos autenticados | SHA256',hashlib.sha256(destination.read_bytes()).hexdigest());return record
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--destination',type=Path,required=True);a=p.parse_args();export(a.output,a.destination)
