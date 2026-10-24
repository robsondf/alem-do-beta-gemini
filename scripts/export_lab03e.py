#!/usr/bin/env python3
"""Complete E export; rejects incomplete verification and skips transient files."""
import argparse,hashlib,json,os,platform,shutil,zipfile
from datetime import datetime,timezone
from pathlib import Path
import numpy,pandas,scipy,matplotlib,fitz,PIL
ROOT=Path(__file__).resolve().parents[1]
def export(output,destination):
    for name in ['validacao_inferencia_independente.json','validacao_previsao_independente.json','validacao_economia_independente.json']:
        assert json.loads((output/name).read_text())['passed'],name
    environment=os.environ.get('ALEM_BETA_EXECUTION_ENV','local preparation')
    record=dict(stage='Lab03E',environment=environment,executed_utc=datetime.now(timezone.utc).isoformat(),python=platform.python_version(),numpy=numpy.__version__,pandas=pandas.__version__,scipy=scipy.__version__,matplotlib=matplotlib.__version__,pymupdf=fitz.VersionBind,pillow=PIL.__version__,static_family=197,temporal_family=474,predictive_family=394,calibration_per_mechanism=99999,validation_per_mechanism=1000,independent_preregistration=False,prospective_untouched_holdout=False,global_homologated=0,all_limitations_eliminated=False,prepared_results_are_not_user_Colab_execution=environment!='Colab')
    (output/'registro_execucao.json').write_text(json.dumps(record,indent=2)+'\n')
    for name in ['plano_v1.json','inputs_manifest.json','runtime_manifest.json']:(output/name).write_bytes((ROOT/'data/lab03e'/name).read_bytes())
    dest=output/'primary';dest.mkdir(exist_ok=True)
    for p in (ROOT/'data/lab03e/primary').iterdir():
        if p.is_file():shutil.copy2(p,dest/p.name)
    files=sorted(p for p in output.rglob('*') if p.is_file() and p.name!='manifesto_exports.json' and p.suffix not in ['.stage','.part','.tmp'] and not any(part.startswith('.') or part=='__pycache__' for part in p.relative_to(output).parts));manifest={str(p.relative_to(output)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files};(output/'manifesto_exports.json').write_text(json.dumps(manifest,indent=2)+'\n')
    with zipfile.ZipFile(destination,'w') as z:
        for p in files+[output/'manifesto_exports.json']:z.write(p,str(p.relative_to(output)),compress_type=zipfile.ZIP_STORED if p.suffix in ['.npz','.gz','.xlsx'] else zipfile.ZIP_DEFLATED)
    with zipfile.ZipFile(destination) as z:
        assert set(z.namelist())==set(manifest)|{'manifesto_exports.json'}
        for name,h in manifest.items():assert hashlib.sha256(z.read(name)).hexdigest()==h
    print('Export:',len(manifest),'files;',destination.stat().st_size,'bytes; SHA256',hashlib.sha256(destination.read_bytes()).hexdigest());return record
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--output',required=True,type=Path);p.add_argument('--destination',required=True,type=Path);a=p.parse_args();export(a.output,a.destination)
