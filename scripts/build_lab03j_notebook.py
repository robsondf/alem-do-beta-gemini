#!/usr/bin/env python3
"""Build one blank-output author notebook pinned to a public immutable runtime commit."""
import argparse,hashlib,inspect,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def build(commit):
 pins=json.loads((ROOT/'data/lab03j/inputs_manifest.json').read_text())['source_pins'];pins=dict(pins);pins['data/lab03j/inputs_manifest.json']=hashlib.sha256((ROOT/'data/lab03j/inputs_manifest.json').read_bytes()).hexdigest();cells=[]
 def cell(kind,s):
  s=inspect.cleandoc(s).strip()+'\n';q={'cell_type':kind,'id':hashlib.sha1(s.encode()).hexdigest()[:12],'metadata':{},'source':s.splitlines(True)}
  if kind=='code':q.update(execution_count=None,outputs=[])
  cells.append(q)
 cell('markdown','''
 # Lab03J — Liquidez condicional e verificação dos pareceres

 **Único notebook novo a executar: CPU, executar tudo, salvar a cópia executada e o ZIP no Drive.** Não repita I/H/F/G/E. Este lote reutiliza o export I já conferido e os onze caches B3 de2015–2025; não consulta provedores nem baixa novamente cotações.

 Executa os oito subconjuntos de controles (porte/setor/beta), duas coortes e três blocos; mudança de liquidez,84 diagnósticos das simulações existentes,83 disposições de eventos e três continuidades documentadas. Preserva80/117, ativo/classe/ISIN, dez setores, pisos e lacunas. A continuidade é apenas sensibilidade, não alteração da matriz principal.

 O porte é capitalização aproximada de quantidade divulgada até2015, não inventário exato/free float. Inferência exploratória sem calibração específica. Não estabelece causalidade, equivalência ou homologação econômica global. Os modelos completos não rejeitam após Holm16; todos os resultados são mantidos.
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
 LOCAL_MODE=bool(os.environ.get('ALEM_BETA_LOCAL'))
 BASE=Path(os.environ.get('ALEM_BETA_LOCAL','/content/alem_beta_lab03j')).resolve();BASE.mkdir(parents=True,exist_ok=True)
 STAMP=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ');RUN=BASE/('run_'+STAMP);RUN.mkdir();ROOT=RUN/'runtime';ROOT.mkdir()
 def digest(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
 def script(name,*args):subprocess.run([sys.executable,str(ROOT/'scripts'/name),*map(str,args)],check=True)
 print('Lab03J | CPU |','integração local, não Colab do autor' if LOCAL_MODE else 'Colab','|',RUN.name)
 ''')
 cell('markdown','''
 ## Autenticação dos insumos existentes

 Código e tabelas têm commit imutável e SHA256 por arquivo. O export I é lido como dados, sem executar os scripts recebidos. Caches no Drive são procurados e autenticados antes de qualquer cópia; eventual transferência usa arquivos já existentes no próprio Drive. Nenhuma consulta Yahoo/B3/CVM é necessária neste lote.
 ''')
 cell('code',f'SOURCE_COMMIT={commit!r}\nSOURCE_PINS={pins!r}\n'+inspect.cleandoc('''
 for name,expected in SOURCE_PINS.items():
     target=ROOT/name;target.parent.mkdir(parents=True,exist_ok=True)
     if LOCAL_MODE:shutil.copy2(Path(os.environ['ALEM_BETA_LOCAL_SOURCE'])/name,target)
     else:urlretrieve('https://raw.githubusercontent.com/robsondf/alem-do-beta-gemini/'+SOURCE_COMMIT+'/'+name,target)
     assert digest(target)==expected,'Fonte divergente: '+name
 I_ID='1L5w3uJvjTU4XiQir1BGMF3XNCWLS-_Ru';I_SHA='ff67a56f9b9cc8b91f11bcbcad311d6253fcfe95aef3f9e02303bad677b41e0e'
 if LOCAL_MODE:
     I_ARCHIVE=Path(os.environ['ALEM_BETA_LOCAL_I']);assert digest(I_ARCHIVE) in [I_SHA,'2f61beb15aac8638cf92dae0eef58de8bc70cded3a6fe833519171f21f554f06']
 else:
     from google.colab import auth,drive
     auth.authenticate_user();drive.mount('/content/drive')
     import google.auth
     from googleapiclient.discovery import build
     from googleapiclient.http import MediaIoBaseDownload
     credentials,_=google.auth.default();service=build('drive','v3',credentials=credentials,cache_discovery=False)
     CACHE=Path('/content/drive/MyDrive/alem_do_beta/lab03j_cache');CACHE.mkdir(parents=True,exist_ok=True)
     def existing_drive_file(file_id,target,expected):
         if target.is_file() and digest(target)==expected:return target
         part=target.with_suffix('.part')
         with part.open('wb') as stream:
             download=MediaIoBaseDownload(stream,service.files().get_media(fileId=file_id));done=False
             while not done:_,done=download.next_chunk()
         assert digest(part)==expected,'Hash de insumo divergente';part.replace(target);return target
     candidates=list(Path('/content/drive/MyDrive/alem_do_beta/lab03i_resultados').glob('*.zip'))
     I_ARCHIVE=next((q for q in candidates if digest(q)==I_SHA),None)
     if I_ARCHIVE is None:I_ARCHIVE=existing_drive_file(I_ID,CACHE/'export_I_autenticado.zip',I_SHA)
     assert digest(I_ARCHIVE)==I_SHA
 I_OUTPUT=RUN/'input_I';I_OUTPUT.mkdir()
 required=['market_private.csv.gz','documented_gaps.csv','gaps_preserved/returns_private.csv.gz','gaps_preserved/assets_originais_COTAHIST.csv','gaps_preserved/assets_universo_2015.csv']
 with zipfile.ZipFile(I_ARCHIVE) as z:
     assert z.testzip() is None;inventory=json.loads(z.read('manifesto_exports.json'))
     for name in required:
         member='outputs_I/'+name;b=z.read(member);assert hashlib.sha256(b).hexdigest()==inventory[member],member
         target=I_OUTPUT/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(b)
 official=json.loads((ROOT/'data/lab03i/b3_cache_manifest.json').read_text())
 if LOCAL_MODE:B3_CACHE=Path(os.environ['ALEM_BETA_LOCAL_B3_CACHE'])
 else:
     B3_CACHE=RUN/'b3_cache';B3_CACHE.mkdir();original=Path('/content/drive/MyDrive/Além do Beta/cache_b3')
     if not original.is_dir():
         first=next(Path('/content/drive/MyDrive').rglob('COTAHIST_A2015.ZIP'),None)
         if first is not None:original=first.parent
     for item in sorted(official,key=lambda x:x['name']):
         target=B3_CACHE/item['name'];candidate=original/item['name']
         if candidate.is_file() and digest(candidate)==item['sha256']:target.symlink_to(candidate)
         else:existing_drive_file(item['drive_id'],target,item['sha256'])
         print('Cache existente autenticado:',item['name'])
     shutil.copy2(ROOT/'data/lab03i/b3_cache_manifest.json',B3_CACHE/'authenticated_manifest.json')
 for item in official:assert digest(B3_CACHE/item['name'])==item['sha256'],item['name']
 print('Fontes:',len(SOURCE_PINS),'| export I e11caches autenticados; nenhuma cotação nova.')
 '''))
 cell('markdown','''
 ## Lote completo e oráculos

 Bloco21 é principal;5/63 são sensibilidades. Holm16 abrange oito modelos em duas coortes; a nova família Holm4 de liquidez/mudança e a de continuidades são distintas. Os regressores gerados são reestimados em cada sorteio síncrono. Não se reamostram ativos como iid nem se escolhe modelo/bloco pelo resultado. O preparo de porte é reproduzido e conferido antes das regressões. Aprovação de capital não é data ex;41 fatores compatíveis não são41 ajustes integralmente homologados.
 ''')
 cell('code','''
 subprocess.run([sys.executable,'-m','unittest','discover','-s',str(ROOT/'tests'),'-p','test_lab03j.py','-v'],check=True)
 BATCH=RUN/'batch_J';script('run_lab03j_batch.py','--i-output',I_OUTPUT,'--b3-cache',B3_CACHE,'--output',BATCH)
 OUTPUT=BATCH/'outputs_J';reference=ROOT/'results/tables/lab03j_pareceres_20261024';compared=0;thresholds=0
 for path in sorted(reference.glob('*.csv')):
     actual=pd.read_csv(OUTPUT/path.name,float_precision='round_trip');expected=pd.read_csv(path,float_precision='round_trip')
     pd.testing.assert_frame_equal(actual,expected,check_exact=False,atol=1e-10,rtol=1e-9);compared+=actual.size
     for column in actual.select_dtypes(include='number'):
         if column=='p' or column.startswith('p_'):
             np.testing.assert_array_equal(actual[column].le(.05),expected[column].le(.05));thresholds+=len(actual)
 for name,expected in SOURCE_PINS.items():assert digest(ROOT/name)==expected,name
 for name in ['independent_verification.json','succession_verification.json']:assert json.loads((OUTPUT/name).read_text())['passed']
 record=dict(passed=True,environment='local_notebook_integration' if LOCAL_MODE else 'author_Colab',source_commit=SOURCE_COMMIT,source_files=len(SOURCE_PINS),compared_values=compared,p_threshold_positions=thresholds,atol=1e-10,rtol=1e-9,I_archive_sha256=digest(I_ARCHIVE),new_outer_generators=0,new_quote_downloads=0,python=sys.version,numpy=np.__version__,pandas=pd.__version__)
 (OUTPUT/'notebook_comparison.json').write_text(json.dumps(record,indent=2)+chr(10));print(json.dumps(record,indent=2))
 ''')
 cell('code','''
 display(pd.read_csv(OUTPUT/'controlled_regressions.csv').query('block==21')[['cohort','controls','N','estimate','ci_low','ci_high','p','p_holm16']])
 display(pd.read_csv(OUTPUT/'liquidity_change.csv').query('block==21')[['cohort','liquidity_target','N','estimate','bootstrap_bias','p','p_holm4']])
 display(pd.read_csv(OUTPUT/'event_audit_83.csv').groupby(['inside2016_2025','status']).size().rename('flags').to_frame())
 display(pd.read_csv(OUTPUT/'succession_sensitivity.csv').query('block==21'))
 for name in ['lab03j_assimetria_anual','lab03j_liquidez_inicial']:display(Image(filename=str(BATCH/'paper/figures/lab02'/(name+'.png'))))
 ''')
 cell('markdown','''
 ## Interpretação e salvamento

 Não há rejeição ajustada nos controles completos nem na associação entre mudanças. Não rejeição não demonstra equivalência ou ausência de efeito. ICs básicos são nominais e não duais dos testes centrados. A atenuação de postos é observada, mas não há teorema universal de erro nas variáveis para este desenho. Percentis de EP não validam ICs observados nem permitem excluir geradores desfavoráveis.

 O ZIP inclui códigos, tabelas, figuras, bancos e insumos diários derivados para auditoria, sem os11ZIPs brutos B3. **Mantenha o export no Drive; não publique as matrizes no Git. Salve esta cópia executada do notebook e compartilhe seu link.** Homologação econômica global, tamanho exato e causalidade continuam limites de evidência, não etapas automaticamente certificadas por execução sem exceções.
 ''')
 cell('code','''
 export=RUN/('resultados_lab03j_'+STAMP+'.zip');inventory={}
 with zipfile.ZipFile(export,'w',compression=zipfile.ZIP_DEFLATED) as z:
     for base,prefix in [(ROOT,'runtime'),(BATCH,'batch_J')]:
         for path in sorted(base.rglob('*')):
             if path.is_file() and '__pycache__' not in path.parts:
                 name=prefix+'/'+path.relative_to(base).as_posix();z.write(path,name);inventory[name]=digest(path)
     z.writestr('manifesto_exports.json',json.dumps(inventory,indent=2))
 with export.open('rb') as stream:os.fsync(stream.fileno())
 with zipfile.ZipFile(export) as z:
     assert z.testzip() is None;saved=json.loads(z.read('manifesto_exports.json'));assert set(saved)==set(z.namelist())-{'manifesto_exports.json'}
     for name,expected in saved.items():assert hashlib.sha256(z.read(name)).hexdigest()==expected,name
 print('Export:',export.name,'| bytes:',export.stat().st_size,'| SHA256:',digest(export))
 if not LOCAL_MODE:
     folder=Path('/content/drive/MyDrive/alem_do_beta/lab03j_resultados');folder.mkdir(parents=True,exist_ok=True);destination=folder/export.name;shutil.copy2(export,destination);assert digest(destination)==digest(export);print('SALVO NO DRIVE:',destination)
 else:print('Integração local concluída;execução do autor no Colab ainda distinta.')
 ''')
 return {'nbformat':4,'nbformat_minor':5,'metadata':{'colab':{'name':'Lab03J_liquidez_controles.ipynb','provenance':[]},'kernelspec':{'display_name':'Python3','language':'python','name':'python3'},'language_info':{'name':'python','version':'3'}},'cells':cells}
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--commit',required=True);p.add_argument('--output',type=Path,default=ROOT/'notebooks/Lab03J_liquidez_controles.ipynb');a=p.parse_args();a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(build(a.commit),ensure_ascii=False,indent=1)+'\n')
