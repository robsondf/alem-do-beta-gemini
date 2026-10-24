#!/usr/bin/env python3
"""Complete, hashed export of calibration results, including replication arrays."""
import os, argparse,hashlib,json,platform,sys,zipfile
from datetime import datetime,timezone
from pathlib import Path
import numpy,pandas,scipy,matplotlib
ROOT=Path(__file__).resolve().parents[1]
def export(output,destination):
    record=dict(stage='Lab03C',environment=os.environ.get('ALEM_BETA_EXECUTION_ENV','local preparation'),executed_utc=datetime.now(timezone.utc).isoformat(),python=platform.python_version(),numpy=numpy.__version__,pandas=pandas.__version__,scipy=scipy.__version__,matplotlib=matplotlib.__version__,primary_cases=197,replications_per_mechanism=1000,empirical_data_modified=False,global_homologated=0,temporal_family_474_calibrated=False)
    (output/'registro_execucao.json').write_text(json.dumps(record,indent=2)+'\n')
    for name in ['plano_v1.json','inputs_manifest.json','runtime_manifest.json']:
        (output/name).write_bytes((ROOT/'data/lab03c'/name).read_bytes())
    files=sorted(p for p in output.rglob('*') if p.is_file() and p.name!='manifesto_exports.json')
    manifest={str(p.relative_to(output)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    (output/'manifesto_exports.json').write_text(json.dumps(manifest,indent=2)+'\n')
    with zipfile.ZipFile(destination,'w',zipfile.ZIP_DEFLATED) as z:
        for p in files+[output/'manifesto_exports.json']:z.write(p,str(p.relative_to(output)))
    print('Export:',destination.name,'|',len(manifest),'arquivos autenticados | SHA256',hashlib.sha256(destination.read_bytes()).hexdigest())
    return record
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--destination',type=Path,required=True);a=p.parse_args();export(a.output,a.destination)
