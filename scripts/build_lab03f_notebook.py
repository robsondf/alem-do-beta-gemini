#!/usr/bin/env python3
"""Small readable Colab; immutable public commit plus per-file SHA256 pins."""
import argparse
import hashlib
import inspect
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
FILES=['src/lab02.py','src/lab03f.py','scripts/run_lab03f.py','scripts/verify_lab03f.py','scripts/plot_lab03f.py','tests/test_lab03f.py',
       'data/lab03f/plano_pos_parecer_v1.json','data/lab03f/freeze.json',
       'results/tables/lab03b_colab_20261023/asset_betas.csv.gz',
       'results/tables/lab03e_colab_20261023/economic_ledger.csv.gz',
       'results/tables/lab03e_colab_20261023/economic_sensitivities.csv.gz']
REFERENCE='results/tables/lab03f_pos_parecer_20261024/'
FILES += [REFERENCE+n for n in ['individual.csv.gz','aggregate.csv.gz','profile_summary.csv','bootstrap_targets.npz']]


def build(commit):
    pins={n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in FILES};cells=[]
    def add(kind,source):
        source=inspect.cleandoc(source).strip()+'\n'
        c=dict(cell_type=kind,metadata={},id=hashlib.sha1(source.encode()).hexdigest()[:12],source=source.splitlines(True))
        if kind=='code':c.update(execution_count=None,outputs=[])
        cells.append(c)
    add('markdown','''
    # Lab03F — Assimetria agregada e robustez após os pareceres

    **Execute tudo e salve uma cópia deste notebook.** Não repetir E, transferência ou laboratórios anteriores. CPU; não precisa GPU. Reutiliza somente o ZIP X autenticado do Drive, sem baixar cotações.

    Executa 1.939 ajustes (sete especificações, três recortes), 4.999 reamostragens por bloco5/21/63, média/mediana do universo fixo, seis testes e verificação independente. Preserva80/117 ativos, classes, dez setores, pares e NaNs. São retornos logarítmicos, não preços.

    A preparação local já foi calculada e conferida. Esta execução será comparada automaticamente às tabelas e a todos os sorteios locais. A homologação econômica global não foi concluída; o novo bootstrap é aproximado, sem garantia finita de cobertura.
    ''')
    add('code','''
    import os,sys,json,hashlib,zipfile,subprocess,shutil,importlib.util
    from pathlib import Path
    from datetime import datetime,timezone
    from urllib.request import urlretrieve
    for module,package in [('numpy','numpy'),('pandas','pandas'),('scipy','scipy'),('matplotlib','matplotlib'),('threadpoolctl','threadpoolctl')]:
        if importlib.util.find_spec(module) is None:subprocess.run([sys.executable,'-m','pip','install','--quiet',package],check=True)
    import numpy as np,pandas as pd
    try:
        from IPython.display import display,Image
    except ImportError:
        def display(value):print(str(value)[:6000])
        def Image(filename):
            from PIL import Image as PillowImage
            im=PillowImage.open(filename);im.load();return filename
    LOCAL_MODE=bool(os.environ.get('ALEM_BETA_LOCAL'))
    os.environ['ALEM_BETA_EXECUTION_ENV']='local_notebook_integration' if LOCAL_MODE else 'Colab'
    BASE=Path(os.environ.get('ALEM_BETA_LOCAL','/content/alem_beta_lab03f')).resolve();BASE.mkdir(parents=True,exist_ok=True)
    STAMP=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    RUN=BASE/('run_'+STAMP);RUN.mkdir();ROOT=RUN/'runtime';ROOT.mkdir()
    def digest(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
    def script(name,*args):subprocess.run([sys.executable,str(ROOT/'scripts'/name),*map(str,args)],check=True)
    print('Lab03F | CPU |', 'integração local, não Colab do autor' if LOCAL_MODE else 'Colab', '|',RUN.name)
    ''')
    add('markdown','''
    ## Fontes e entradas fixadas

    Código e referências compactas vêm de um commit público imutável e são autenticados individualmente. O ZIP de retornos continua externo no Drive. Nenhum download de Yahoo/B3 é executado.
    ''')
    add('code',f"SOURCE_COMMIT={commit!r}\nSOURCE_PINS={pins!r}\n"+inspect.cleandoc('''
    for name,expected in SOURCE_PINS.items():
        target=ROOT/name;target.parent.mkdir(parents=True,exist_ok=True)
        if LOCAL_MODE:shutil.copy2(Path(os.environ['ALEM_BETA_LOCAL_SOURCE'])/name,target)
        else:urlretrieve('https://raw.githubusercontent.com/robsondf/alem-do-beta-gemini/'+SOURCE_COMMIT+'/'+name,target)
        assert digest(target)==expected,'Fonte divergente: '+name
    print('Fontes autenticadas:',len(SOURCE_PINS),'| commit',SOURCE_COMMIT)
    X_ID='1aExT7v-GD8s5xKzM0K-0LIIJER8E8Twg'
    X_SHA='297da2afde534082c398324f308df7af134c9692e7d61d6e0b2b820341ea5214'
    if LOCAL_MODE:
        X_ARCHIVE=Path(os.environ['ALEM_BETA_LOCAL_X'])
    else:
        from google.colab import auth,drive
        auth.authenticate_user();drive.mount('/content/drive')
        import google.auth
        from googleapiclient.discovery import build
        from googleapiclient.http import MediaIoBaseDownload
        credentials,_=google.auth.default();service=build('drive','v3',credentials=credentials,cache_discovery=False)
        CACHE=Path('/content/drive/MyDrive/alem_do_beta/lab03f_cache');CACHE.mkdir(parents=True,exist_ok=True)
        X_ARCHIVE=CACHE/(X_ID+'.zip')
        if not X_ARCHIVE.exists() or digest(X_ARCHIVE)!=X_SHA:
            name=service.files().get(fileId=X_ID,fields='name').execute()['name']
            found=None
            for candidate in Path('/content/drive/MyDrive').rglob(name):
                if candidate.is_file() and digest(candidate)==X_SHA:found=candidate;break
            if found is not None:X_ARCHIVE=found
            else:
                part=X_ARCHIVE.with_suffix('.part')
                with part.open('wb') as stream:
                    download=MediaIoBaseDownload(stream,service.files().get_media(fileId=X_ID));done=False
                    while not done:_,done=download.next_chunk()
                assert digest(part)==X_SHA;part.replace(X_ARCHIVE)
    assert digest(X_ARCHIVE)==X_SHA
    print('Cache X autenticado:',X_ARCHIVE.name,'|',X_ARCHIVE.stat().st_size,'bytes')
    '''))
    add('markdown','''
    ## Protocolo e processamento completo

    Plano posterior aos pareceres, escrito antes dos novos ajustes, com resultados anteriores conhecidos. Mantém a referência197/474. Bloco21 e Holm10 são a análise agregada principal; blocos5/63 e Holm30 são sensibilidades, todas reportadas. As exclusões de2020 mudam a janela-alvo. As somas de coeficientes dinâmicos são outros estimandos, não prova de correção de assincronia. O avanço é somente histórico, sem uso em previsão.
    ''')
    add('code','''
    subprocess.run([sys.executable,'-m','unittest','discover','-s',str(ROOT/'tests'),'-p','test_lab03f.py','-v'],check=True)
    OUTPUT=RUN/'outputs'
    script('run_lab03f.py','--x-archive',X_ARCHIVE,'--output',OUTPUT)
    ''')
    add('code','''
    script('verify_lab03f.py','--x-archive',X_ARCHIVE,'--output',OUTPUT)
    script('plot_lab03f.py','--output',OUTPUT)
    reference=ROOT/'results/tables/lab03f_pos_parecer_20261024'
    compared=0
    for name in ['individual.csv.gz','aggregate.csv.gz','profile_summary.csv']:
        observed=pd.read_csv(OUTPUT/name,float_precision='round_trip');expected=pd.read_csv(reference/name,float_precision='round_trip')
        pd.testing.assert_frame_equal(observed,expected,check_exact=False,atol=1e-10,rtol=1e-9);compared+=observed.shape[0]*observed.shape[1]
    with np.load(OUTPUT/'bootstrap_targets.npz') as actual,np.load(reference/'bootstrap_targets.npz') as expected:
        assert actual.files==expected.files
        for key in actual.files:np.testing.assert_allclose(actual[key],expected[key],atol=1e-10,rtol=1e-9);compared+=actual[key].size
    for name,expected in SOURCE_PINS.items():assert digest(ROOT/name)==expected,name
    record={'passed':True,'environment':'local_not_author_Colab' if LOCAL_MODE else 'Colab','source_commit':SOURCE_COMMIT,'source_files':len(SOURCE_PINS),'compared_values':compared,'atol':1e-10,'rtol':1e-9,'X_sha256':digest(X_ARCHIVE),'python':sys.version,'numpy':np.__version__,'pandas':pd.__version__}
    (OUTPUT/'notebook_comparison.json').write_text(json.dumps(record,indent=2)+'\\n')
    print(json.dumps(record,indent=2))
    ''')
    add('code','''
    aggregate=pd.read_csv(OUTPUT/'aggregate.csv.gz')
    display(aggregate[aggregate.block.eq(21)][['profile','scenario','statistic','estimate','ci_low','ci_high','p_holm10','p_holm30']])
    display(pd.read_csv(OUTPUT/'profile_summary.csv'))
    for name in ['lab03f_agregado','lab03f_criticos']:display(Image(filename=str(OUTPUT/'figures'/(name+'.png'))))
    ''')
    add('markdown','''
    ## Interpretação e salvamento

    O novo resultado agrega evidência sobre a média da década, com sensibilidade à família e à janela. Não demonstra assimetria generalizada. As duas rejeições individuais originais são frágeis às exclusões de crise; não se escolhe outra especificação por rejeitar outro ativo. Os recortes recentes permanecem inconclusivos.

    ICs bootstrap são marginais/aproximados, sujeitos a estacionariedade local e regularidade; ajuste Holm não corrige valores-p descalibrados. Máscaras de influência são após seleção; seu Holm não garante FWER. Nada disso elimina a auditoria econômica incompleta, sobrevivência/vintages ou lacunas não identificáveis. A representação/raciocínio continua proposta separada.

    O ZIP final salva fontes necessárias, resultados, gráficos, hashes e comparação; não contém a matriz privada de retornos. A referência ao cache externo é mantida por ID/SHA. Depois de executar tudo, **salve também o notebook**.
    ''')
    add('code','''
    export=RUN/('resultados_lab03f_'+STAMP+'.zip')
    inventory={}
    with zipfile.ZipFile(export,'w',compression=zipfile.ZIP_DEFLATED) as z:
        for base,prefix in [(ROOT,'runtime'),(OUTPUT,'outputs')]:
            for path in sorted(base.rglob('*')):
                if path.is_file() and '__pycache__' not in path.parts:
                    name=prefix+'/'+str(path.relative_to(base));z.write(path,name);inventory[name]=digest(path)
        z.writestr('manifesto_exports.json',json.dumps(inventory,indent=2))
    print('Export:',export.name,'| bytes:',export.stat().st_size,'| SHA256:',digest(export))
    if not LOCAL_MODE:
        folder=Path('/content/drive/MyDrive/alem_do_beta/lab03f_resultados');folder.mkdir(parents=True,exist_ok=True)
        destination=folder/export.name;shutil.copy2(export,destination);assert digest(destination)==digest(export)
        print('SALVO NO DRIVE:',destination)
    else:print('Integração local concluída. Não é execução Colab do autor.')
    ''')
    return dict(nbformat=4,nbformat_minor=5,cells=cells,metadata={'colab':{'name':'Lab03F_pos_parecer.ipynb','provenance':[]},'kernelspec':{'display_name':'Python 3','name':'python3'},'language_info':{'name':'python'}})


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--source-commit',required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    nb=build(a.source_commit)
    for i,c in enumerate(nb['cells']):
        if c['cell_type']=='code':compile(''.join(c['source']),f'cell{i}','exec')
        else:assert not any(x.startswith('    ') for x in c['source'])
    a.output.write_text(json.dumps(nb,ensure_ascii=False,indent=1)+'\n')
    print('Notebook:',len(nb['cells']),'cells,',sum(c['cell_type']=='code' for c in nb['cells']),'code cells')
