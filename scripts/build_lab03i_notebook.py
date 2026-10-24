#!/usr/bin/env python3
"""Single author launcher for H plus I; reads already existing Drive caches."""
import argparse,ast,hashlib,inspect,importlib.util,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('h_notebook',ROOT/'scripts/build_lab03h_notebook.py');h=importlib.util.module_from_spec(spec);spec.loader.exec_module(h)
REFERENCE='results/tables/lab03i_parecer_v4_20261024/'


def build(commit):
    nb=h.build(commit);cells=nb['cells']
    def setcell(i,text):
        text=inspect.cleandoc(text).strip()+'\n';cells[i]['source']=text.splitlines(True);cells[i]['id']=hashlib.sha1(text.encode()).hexdigest()[:12]
    setcell(0,'''
    # Lab03I — Seleção, liquidez e verificações H/I

    **Execute tudo em CPU e salve uma cópia do notebook e o ZIP no Drive. Este é o único notebook a executar nesta entrega.** Ele inclui H (exclusões de 2020 e diagnóstico da calibração) e I (reconstrução do adendo de 2015 e associação com liquidez). Não precisa executar H separadamente nem repetir F/G/E ou os 6.000 geradores.

    Usa X e os onze ZIPs COTAHIST de 2015–2025 já existentes no Drive, com hashes. Não consulta novas cotações. Processa os dois universos e todos os blocos no mesmo lote. Há progresso por ano, universo e bloco.

    Preserva os 80/117 principais, ativo/classe/ISIN, dez setores e ausências. O universo de 2015 é uma sensibilidade fixa. A reconstrução literal do avaliador é diagnóstica; a variante interpretada preserva as sete lacunas documentadas, incluindo os cinco dias de direitos. Os 83 eventos são marcações heurísticas, não homologação econômica. Liquidez é associação pós-parecer com inferência aproximada, sem identificação causal ou confirmação independente.
    ''')
    setcell(1,''.join(cells[1]['source']).replace('lab03h','lab03i').replace('Lab03H','Lab03I'))
    old=''.join(cells[3]['source']);tree=ast.parse(old);pins=next(ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(x,ast.Name) and x.id=='SOURCE_PINS' for x in n.targets))
    files=set(pins)|{'scripts/replicate_review_2015.py','scripts/verify_review_2015.py','scripts/plot_review_2015.py','scripts/sensitivity_review_2015_lags.py','tests/test_review_2015.py'}
    files|=set(json.loads((ROOT/'data/lab03i/inputs_manifest.json').read_text())['source_pins'])
    # Only runtime inputs; article and execution receipts can evolve separately.
    files|={'data/lab03i/inputs_manifest.json'}
    files|={REFERENCE+p.name for p in (ROOT/REFERENCE).iterdir() if p.is_file()}
    pins={n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in sorted(files)}
    code=old[old.index('for name,expected in SOURCE_PINS.items():'):]
    code+='''
    official=json.loads((ROOT/'data/lab03i/b3_cache_manifest.json').read_text())
    if LOCAL_MODE:B3_CACHE=Path(os.environ['ALEM_BETA_LOCAL_B3_CACHE'])
    else:
        B3_CACHE=RUN/'b3_cache';B3_CACHE.mkdir()
        original=Path('/content/drive/MyDrive/Além do Beta/cache_b3')
        if not original.is_dir():
            candidates=Path('/content/drive/MyDrive').rglob('COTAHIST_A2015.ZIP')
            first=next(candidates,None)
            if first is not None:original=first.parent
        for item in sorted(official,key=lambda x:x['name']):
            name=item['name'];target=B3_CACHE/name;candidate=original/name
            if candidate.is_file() and digest(candidate)==item['sha256']:target.symlink_to(candidate)
            else:
                with target.open('wb') as stream:
                    download=MediaIoBaseDownload(stream,service.files().get_media(fileId=item['drive_id']));done=False
                    while not done:_,done=download.next_chunk()
            assert digest(target)==item['sha256'],name
            print('Cache oficial autenticado:',name,'|',item['bytes'],'bytes')
        shutil.copy2(ROOT/'data/lab03i/b3_cache_manifest.json',B3_CACHE/'authenticated_manifest.json')
    for item in official:assert digest(B3_CACHE/item['name'])==item['sha256'],item['name']
    print('Onze caches B3 autenticados; nenhuma nova cotação consultada.')
    '''
    # Appended code is dedented separately to preserve its Python block structure.
    prefix=code[:code.index('    official=')];tail=inspect.cleandoc(code[code.index('    official='):]);setcell(3,f'SOURCE_COMMIT={commit!r}\nSOURCE_PINS={pins!r}\n'+prefix+tail)
    setcell(4,'''
    ## Métodos e limites

    H: exclusões somente da metade inicial, Holm4 novo por bloco e famílias anteriores preservadas. I: seleção única em 2015, perdas de elegibilidade explícitas, reprodução literal das 83 marcações e variante com as sete lacunas preservadas. A reamostragem é conjunta por sessão, sem tratar ativos como observações iid.

    As associações de postos foram declaradas após o parecer e o resultado externo inicial; Holm8 inclui quatro associações em duas variantes, por bloco. Mantêm-se 21 como principal e 5/63 como sensibilidades. O deslocamento bootstrap é reportado; não houve calibração específica de tamanho/cobertura. Não selecionar variante, universo ou bloco pela significância.
    ''')
    setcell(5,'''
    for name in ['test_lab03h.py','test_review_2015.py']:
        subprocess.run([sys.executable,'-m','unittest','discover','-s',str(ROOT/'tests'),'-p',name,'-v'],check=True)
    OUTPUT=RUN/'outputs';I_OUTPUT=RUN/'outputs_I'
    script('run_lab03h.py','--x-archive',X_ARCHIVE,'--output',OUTPUT)
    script('replicate_review_2015.py','--b3-cache',B3_CACHE,'--review-dir',ROOT/'data/lab03i/review_reference','--x-archive',X_ARCHIVE,'--output',I_OUTPUT)
    ''')
    previous=''.join(cells[6]['source'])
    extra='''
    script('plot_review_2015.py','--output',I_OUTPUT)
    script('sensitivity_review_2015_lags.py','--output',I_OUTPUT)
    script('verify_review_2015.py','--output',I_OUTPUT)
    iref=ROOT/'results/tables/lab03i_parecer_v4_20261024';iv=0;it=0
    for path in sorted(iref.glob('*.csv')):
        name=path.name
        actual_path=I_OUTPUT/'gaps_preserved'/name.removeprefix('gaps_') if name.startswith('gaps_') else I_OUTPUT/name
        actual=pd.read_csv(actual_path,float_precision='round_trip');expected=pd.read_csv(path,float_precision='round_trip')
        np.testing.assert_array_equal(sorted(actual.columns),sorted(expected.columns))
        pd.testing.assert_frame_equal(actual.reindex(columns=expected.columns),expected,check_exact=False,atol=1e-10,rtol=1e-9);iv+=actual.size
        for col in actual.select_dtypes(include='number'):
            if col=='p' or col.startswith('p_'):
                np.testing.assert_array_equal(actual[col].le(.05),expected[col].le(.05));it+=len(actual)
    for name,expected in SOURCE_PINS.items():assert digest(ROOT/name)==expected,name
    record.update(stage='H_and_I',external_2015_package_reproduced=True,run_stamp_UTC=STAMP,I_compared_values=iv,I_p_threshold_positions=it,I_independent_verification=json.loads((I_OUTPUT/'independent_verification.json').read_text()),only_existing_caches=True)
    (I_OUTPUT/'notebook_comparison.json').write_text(json.dumps(record,indent=2)+'\\n')
    print(json.dumps(record,indent=2))
    '''
    setcell(6,previous+inspect.cleandoc(extra))
    setcell(7,'''
    display(pd.read_csv(OUTPUT/'crisis_aggregate.csv.gz').query('block==21')[['profile','statistic','estimate','p_centered','p_holm4']])
    display(pd.read_csv(I_OUTPUT/'gaps_preserved/aggregate_reproduced.csv').query('bloco==21'))
    display(pd.read_csv(I_OUTPUT/'liquidity_all_variants.csv').query('variant=="gaps_preserved" and block==21'))
    for directory,name in [(OUTPUT,'lab03h_crise'),(OUTPUT,'lab03h_periodo_completo'),(I_OUTPUT,'lab03i_liquidez')]:display(Image(filename=str(directory/'figures'/(name+'.png'))))
    ''')
    setcell(8,'''
    ## Interpretação e salvamento

    As comparações usam retornos; preços são insumos de reconstrução. Nenhuma ponte vira retorno diário. A assimetria e a mudança dependem do universo e da elegibilidade. Os dados são compatíveis com uma relação de liquidez, sem identificar causa, efeito de melhora de liquidez, retorno de carteira ou prêmio de risco.

    Os ICs são nominais, não uniformemente validados. A calibração anterior não se transfere às novas máscaras, universos ou correlações. A reamostragem conjunta preserva dependência, mas há deslocamento bootstrap e seleção retrospectiva. A auditoria econômica global e KRR permanecem incompletos.

    O ZIP contém fontes, tabelas, gráficos, bancos bootstrap e matrizes derivadas de retorno para auditoria. Os ZIPs brutos COTAHIST não são incluídos. **Mantenha o export no Drive; as matrizes não integram o repositório público. Salve também este notebook executado e envie o link da cópia.**
    ''')
    export=''.join(cells[9]['source']).replace('lab03h','lab03i').replace("(OUTPUT,'outputs')","(OUTPUT,'outputs'),(I_OUTPUT,'outputs_I')")
    setcell(9,export);nb['metadata']['colab']['name']='Lab03I_selecao_liquidez.ipynb';return nb


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--source-commit',required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();nb=build(a.source_commit)
    for i,c in enumerate(nb['cells']):
        if c['cell_type']=='code':compile(''.join(c['source']),f'cell{i}','exec')
        else:assert not any(x.startswith('    ') for x in c['source'])
    a.output.write_text(json.dumps(nb,ensure_ascii=False,indent=1)+'\n');print('Notebook H/I:',len(nb['cells']),'cells;',a.output.stat().st_size,'bytes')
