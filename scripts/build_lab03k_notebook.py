#!/usr/bin/env python3
"""Small blank-output Colab launcher; only authenticated prior I/J exports."""
import argparse,hashlib,inspect,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def build(commit):
 pins=json.loads((ROOT/'data/lab03k/inputs_manifest.json').read_text())['source_pins'];pins=dict(pins);pins['data/lab03k/inputs_manifest.json']=hashlib.sha256((ROOT/'data/lab03k/inputs_manifest.json').read_bytes()).hexdigest();cells=[]
 def cell(kind,text):
  text=inspect.cleandoc(text).strip()+'\n';c=dict(cell_type=kind,id=hashlib.sha1(text.encode()).hexdigest()[:12],metadata={},source=text.splitlines(True))
  if kind=='code':c.update(execution_count=None,outputs=[])
  cells.append(c)
 cell('markdown','''
 # Lab03K — Porte e liquidez: fechamento dos pareceres

 **Único notebook novo a executar.** Faça uma cópia no Drive, use CPU e execute tudo. Este lote reúne24 testes conjuntos, sensibilidades,6.000 simulações e oráculos. Reutiliza exports I/J já existentes; não repete os labs anteriores nem baixa cotações. A calibração pode demorar alguns minutos e imprime progresso a cada 250 réplicas.

 Amostras80/117, unidade ativo/classe, pisos e ausências permanecem. O teste conjunto não identifica dois efeitos separados ou causalidade. Os ICs são nominais, com subcobertura material nas simulações. A família J de 16 testes é preservada.
 ''')
 cell('code','''
 import os,sys,json,hashlib,zipfile,subprocess,shutil,importlib.util
 from pathlib import Path
 from datetime import datetime,timezone
 from urllib.request import urlretrieve
 for module,package in [('numpy','numpy'),('pandas','pandas'),('scipy','scipy'),('matplotlib','matplotlib'),('threadpoolctl','threadpoolctl')]:
     if importlib.util.find_spec(module) is None:subprocess.run([sys.executable,'-m','pip','install','--quiet',package],check=True)
 import numpy as np,pandas as pd
 from IPython.display import display,Image
 LOCAL=bool(os.environ.get('ALEM_BETA_LOCAL'));BASE=Path(os.environ.get('ALEM_BETA_LOCAL','/content/alem_beta_lab03k')).resolve();BASE.mkdir(parents=True,exist_ok=True)
 STAMP=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ');RUN=BASE/('run_'+STAMP);RUN.mkdir();ROOT=RUN/'runtime';ROOT.mkdir()
 def digest(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
 def script(name,*args):subprocess.run([sys.executable,str(ROOT/'scripts'/name),*map(str,args)],check=True)
 print('Lab03K | CPU |','integração local, não execução do autor' if LOCAL else 'Colab','|',RUN.name)
 ''')
 cell('markdown','''
 ## Fontes e exports autenticados

 Código público é fixado por commit e SHA256. Os ZIPs anteriores são lidos como dados, sem executar seus scripts. Primeiro procuram-se cópias nas pastas anteriores do Drive; apenas na ausência de hash válido é transferido o mesmo arquivo existente no Drive. Nenhum cache completo de cotações é baixado.
 ''')
 cell('code',f'SOURCE_COMMIT={commit!r}\nSOURCE_PINS={pins!r}\n'+inspect.cleandoc('''
 for name,sha in SOURCE_PINS.items():
     target=ROOT/name;target.parent.mkdir(parents=True,exist_ok=True)
     if LOCAL:shutil.copy2(Path(os.environ['ALEM_BETA_LOCAL_SOURCE'])/name,target)
     else:urlretrieve('https://raw.githubusercontent.com/robsondf/alem-do-beta-gemini/'+SOURCE_COMMIT+'/'+name,target)
     assert digest(target)==sha,'Fonte divergente: '+name
 I_ID='1L5w3uJvjTU4XiQir1BGMF3XNCWLS-_Ru';I_SHA='ff67a56f9b9cc8b91f11bcbcad311d6253fcfe95aef3f9e02303bad677b41e0e'
 J_ID='17DxLLmCd-UD0NXlFXDQNANbk1fxmqZ2q';J_SHA='96b56d0a9e3d8ace52f1f4a6b0307c769547e2bfe355a6f6318e6656ab5f8dce'
 if LOCAL:
     I_ARCHIVE=Path(os.environ['ALEM_BETA_LOCAL_I']);J_ARCHIVE=Path(os.environ['ALEM_BETA_LOCAL_J'])
     assert digest(I_ARCHIVE) in [I_SHA,'2f61beb15aac8638cf92dae0eef58de8bc70cded3a6fe833519171f21f554f06']
     assert digest(J_ARCHIVE)==J_SHA
 else:
     from google.colab import auth,drive
     auth.authenticate_user();drive.mount('/content/drive')
     import google.auth
     from googleapiclient.discovery import build
     from googleapiclient.http import MediaIoBaseDownload
     credentials,_=google.auth.default();service=build('drive','v3',credentials=credentials,cache_discovery=False)
     DRIVE=Path('/content/drive/MyDrive/alem_do_beta');CACHE=DRIVE/'lab03k_cache';CACHE.mkdir(parents=True,exist_ok=True)
     def existing(file_id,expected,filename,candidate_folders):
         candidates=[CACHE/filename]
         for folder in candidate_folders:candidates+=list((DRIVE/folder).glob('*.zip'))
         for q in candidates:
             if q.is_file() and digest(q)==expected:print('Reutilizado:',q.name);return q
         target=CACHE/filename;part=target.with_suffix('.part')
         with part.open('wb') as stream:
             dl=MediaIoBaseDownload(stream,service.files().get_media(fileId=file_id));done=False
             while not done:_,done=dl.next_chunk()
         assert digest(part)==expected,'Export divergente';part.replace(target);return target
     I_ARCHIVE=existing(I_ID,I_SHA,'export_I.zip',['lab03i_resultados','lab03j_cache'])
     J_ARCHIVE=existing(J_ID,J_SHA,'export_J.zip',['lab03j_resultados'])
 def extract_selected(archive,items):
     with zipfile.ZipFile(archive) as z:
         assert z.testzip() is None;manifest=json.loads(z.read('manifesto_exports.json'))
         for member,target in items:
             b=z.read(member);assert hashlib.sha256(b).hexdigest()==manifest[member],member
             target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(b)
 I_OUTPUT=RUN/'input_I';J_BATCH=RUN/'input_J';required=['market_private.csv.gz','gaps_preserved/returns_private.csv.gz']
 extract_selected(I_ARCHIVE,[('outputs_I/'+name,I_OUTPUT/name) for name in required])
 jrequired=['outputs_J/covariates_used.csv','outputs_J/complete_case_audit.csv','outputs_J/event_audit_83.csv','outputs_J/controlled_regressions.csv','private_inputs/turnover_private.csv.gz']
 extract_selected(J_ARCHIVE,[('batch_J/'+name,J_BATCH/name) for name in jrequired])
 print('Fontes:',len(SOURCE_PINS),'| I/J autenticados | nenhuma cotação nova')
 '''))
 cell('markdown','''
 ## Execução de todo o lote

 Bloco 21 principal e 5/63 sensibilidades. Holm 2 para duas nulas conjuntas de referência, Holm 6 para três sensibilidades em duas coortes; separados por bloco. ICs e p individuais são nominais. Beta 2015 reestimado em estrato próprio; setor mantém classificação arquivada, não point-in-time. A exclusão de ativos é retrospectiva e não muda as amostras principais. Giro é reparametrização exata.
 ''')
 cell('code','''
 subprocess.run([sys.executable,'-m','unittest','discover','-s',str(ROOT/'tests'),'-p','test_lab03k.py','-v'],check=True)
 OUTPUT=RUN/'outputs_K'
 script('run_lab03k.py','--i-output',I_OUTPUT,'--j-batch',J_BATCH,'--output',OUTPUT)
 script('calibrate_lab03k.py','--i-output',I_OUTPUT,'--j-batch',J_BATCH,'--output',OUTPUT)
 script('verify_lab03k.py','--i-output',I_OUTPUT,'--j-batch',J_BATCH,'--output',OUTPUT)
 script('build_lab03k_paper.py','--source',OUTPUT,'--paper',RUN/'paper')
 count=0;thresholds=0
 for expected in sorted((ROOT/'results/tables/lab03k_20261025').glob('*.csv*')):
     actual=pd.read_csv(OUTPUT/expected.name,float_precision='round_trip');reference=pd.read_csv(expected,float_precision='round_trip')
     pd.testing.assert_frame_equal(actual,reference,check_exact=False,atol=1e-10,rtol=1e-9);count+=actual.size
     for col in actual.select_dtypes(include='number'):
         if col=='p' or col.startswith('p_'):
             np.testing.assert_array_equal(actual[col].le(.05),reference[col].le(.05));thresholds+=len(actual)
 for name,sha in SOURCE_PINS.items():assert digest(ROOT/name)==sha,name
 for name in ['independent_verification.json','calibration_validation.json']:assert json.loads((OUTPUT/name).read_text())['passed']
 receipt=dict(passed=True,environment='local_notebook_integration' if LOCAL else 'author_Colab',source_commit=SOURCE_COMMIT,source_files=len(SOURCE_PINS),compared_values=count,p_threshold_positions=thresholds,atol=1e-10,rtol=1e-9,I_sha256=digest(I_ARCHIVE),J_sha256=digest(J_ARCHIVE),python=sys.version,numpy=np.__version__,pandas=pd.__version__)
 (OUTPUT/'notebook_comparison.json').write_text(json.dumps(receipt,indent=2)+chr(10));print(json.dumps(receipt,indent=2))
 ''')
 cell('code','''
 display(pd.read_csv(OUTPUT/'joint_tests.csv').query('block==21'))
 display(pd.read_csv(OUTPUT/'coefficients.csv').query('block==21 and parameter in ["liquidity","size"]'))
 display(pd.read_csv(OUTPUT/'calibration_summary.csv'))
 display(Image(filename=str(RUN/'paper/figures/lab02/lab03k_controls.png')))
 print('Rejeição conjunta não identifica dois efeitos separados. Cobertura nominal não é garantia de 95%.')
 ''')
 cell('markdown','''
 ## Salvar e compartilhar

 O ZIP inclui código, resultados, figura, máscaras e bancos privados para auditoria. **Mantenha o ZIP no Drive; não publique matrizes ou bancos no Git. Salve esta cópia executada e compartilhe seu link.** Homologação econômica, causalidade, sobrevivência e quantidade exata de ações permanecem limites; execução sem exceções não os certifica. Nenhum PR é mergeado por este notebook.
 ''')
 cell('code','''
 export=RUN/('resultados_lab03k_'+STAMP+'.zip');manifest={}
 with zipfile.ZipFile(export,'w',compression=zipfile.ZIP_DEFLATED) as z:
     for base,prefix in [(ROOT,'runtime'),(OUTPUT,'outputs_K'),(RUN/'paper','paper')]:
         for path in sorted(base.rglob('*')):
             if path.is_file() and '__pycache__' not in path.parts:
                 name=prefix+'/'+path.relative_to(base).as_posix();z.write(path,name);manifest[name]=digest(path)
     z.writestr('manifesto_exports.json',json.dumps(manifest,indent=2))
 with zipfile.ZipFile(export) as z:
     assert z.testzip() is None;saved=json.loads(z.read('manifesto_exports.json'));assert set(saved)==set(z.namelist())-{'manifesto_exports.json'}
     for name,sha in saved.items():assert hashlib.sha256(z.read(name)).hexdigest()==sha,name
 print('Export:',export.name,'| bytes:',export.stat().st_size,'| SHA256:',digest(export))
 if not LOCAL:
     folder=Path('/content/drive/MyDrive/alem_do_beta/lab03k_resultados');folder.mkdir(parents=True,exist_ok=True);destination=folder/export.name;shutil.copy2(export,destination);assert digest(destination)==digest(export);print('SALVO NO DRIVE:',destination)
 else:print('Integração local concluída; execução do autor no Colab ainda distinta.')
 ''')
 return dict(nbformat=4,nbformat_minor=5,metadata=dict(colab=dict(name='Lab03K_porte_liquidez.ipynb',provenance=[]),kernelspec=dict(display_name='Python3',language='python',name='python3'),language_info=dict(name='python',version='3')),cells=cells)

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--commit',required=True);p.add_argument('--output',type=Path,default=ROOT/'notebooks/Lab03K_porte_liquidez.ipynb');a=p.parse_args();a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(build(a.commit),ensure_ascii=False,indent=1)+'\n')
