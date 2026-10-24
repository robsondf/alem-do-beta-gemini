#!/usr/bin/env python3
"""Compact G notebook; immutable runtime and existing authenticated X cache."""
import argparse,hashlib,inspect,json,importlib.util
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('f_notebook',ROOT/'scripts/build_lab03f_notebook.py');f=importlib.util.module_from_spec(spec);spec.loader.exec_module(f)


def build(commit):
    nb=f.build(commit);cells=nb['cells']
    def setcell(i,text):
        text=inspect.cleandoc(text).strip()+'\n';cells[i]['source']=text.splitlines(True);cells[i]['id']=hashlib.sha1(text.encode()).hexdigest()[:12]
    setcell(0,'''
    # Lab03G — Mudança temporal agregada e calibração após o terceiro parecer

    **Execute tudo, em CPU, e salve uma cópia do notebook.** Este é o único notebook novo; não repetir F/E/transferências. A execução completa faz as sensibilidades observadas e 1.000 réplicas em cada um de seis mecanismos, cada uma com 4.999 sorteios. Há mensagens de avanço a cada 50 réplicas e salvamento ao terminar cada mecanismo. É a célula mais demorada; não requer GPU.

    Reutiliza o cache X autenticado do Drive, sem baixar cotações. Preserva 80/117 ativos, classes, dez setores, retornos logarítmicos, pares e ausências. Não seleciona ativos anualmente nem cria pesos de empresas. O cálculo local completo já foi realizado; a conferência desta execução será registrada separadamente.

    O estudo mede mudança média/mediana entre quinquênios e inferência agregada defasada/semanal. A calibração também preserva falhas de cobertura. Não conclui homologação econômica ou uma contribuição de IA.
    ''')
    setcell(1,''.join(cells[1]['source']).replace('lab03f','lab03g').replace('Lab03F','Lab03G'))
    lock=json.loads((ROOT/'data/lab03g/inputs_manifest.json').read_text());files=set(lock['source_pins'])|set(lock['frozen_E_pins'])
    files|={'src/lab03g.py','scripts/run_lab03g.py','scripts/verify_lab03g.py','scripts/plot_lab03g.py','tests/test_lab03g.py','data/lab03g/plano_v1.json','data/lab03g/inputs_manifest.json','results/tables/lab03b_colab_20261023/asset_betas.csv.gz'}
    reference='results/tables/lab03g_pos_parecer_v3_20261024/'
    files|={reference+n for n in ['observed_aggregate.csv.gz','observed_draws.npz','temporal_asset_points.csv','calibration_replications.csv.gz','calibration_cases.csv','calibration_families.csv']}
    pins={n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in sorted(files)}
    code=''.join(cells[3]['source']);code=code[code.index('for name,expected in SOURCE_PINS.items():'):]
    # Keep F's shared Drive cache directory; do not download a second full archive.
    setcell(3,f'SOURCE_COMMIT={commit!r}\nSOURCE_PINS={pins!r}\n'+code)
    setcell(4,'''
    ## Plano, testes e processamento

    Plano pós-revisão, escrito antes dos resultados G, com F conhecido. A família nova de quatro testes cobre média/mediana inicial e mudança pareada; a família de 18 cobre três modelos, três painéis e dois resumos. Famílias individuais originais 197/474 preservadas. Bloco principal 21 sessões ou 4 semanas; sensibilidades completas mantidas.

    As defasagens são construídas no calendário original antes da reamostragem. A calibração de tamanho/cobertura usa as famílias agregadas de dez e quatro testes, bloco 21, bancos/mercado fixados; não certifica os modelos dinâmicos/semanais. Nenhum sorteio inválido é descartado. O resultado da calibração não determina um novo método escolhido por significância.
    ''')
    setcell(5,'''
    subprocess.run([sys.executable,'-m','unittest','discover','-s',str(ROOT/'tests'),'-p','test_lab03g.py','-v'],check=True)
    OUTPUT=RUN/'outputs'
    if LOCAL_MODE and os.environ.get('ALEM_BETA_LOCAL_COMPLETED_G'):
        # Only for the declared local integration test of serialized cells.
        # The author Colab always performs the complete calculation below.
        shutil.copytree(Path(os.environ['ALEM_BETA_LOCAL_COMPLETED_G']),OUTPUT)
        print('Integração local: reutiliza cálculo G local já concluído; não é uma nova simulação nem execução do autor no Colab.')
    else:
        script('run_lab03g.py','--x-archive',X_ARCHIVE,'--output',OUTPUT,'--stage','all')
    ''')
    setcell(6,'''
    script('verify_lab03g.py','--x-archive',X_ARCHIVE,'--output',OUTPUT)
    script('plot_lab03g.py','--output',OUTPUT)
    reference=ROOT/'results/tables/lab03g_pos_parecer_v3_20261024'
    compared=0
    for name in ['observed_aggregate.csv.gz','temporal_asset_points.csv','calibration_replications.csv.gz','calibration_cases.csv','calibration_families.csv']:
        observed=pd.read_csv(OUTPUT/name,float_precision='round_trip');expected=pd.read_csv(reference/name,float_precision='round_trip')
        pd.testing.assert_frame_equal(observed,expected,check_exact=False,atol=1e-10,rtol=1e-9);compared+=observed.size
    with np.load(OUTPUT/'observed_draws.npz') as actual,np.load(reference/'observed_draws.npz') as expected:
        assert actual.files==expected.files
        for key in actual.files:np.testing.assert_allclose(actual[key],expected[key],atol=1e-10,rtol=1e-9);compared+=actual[key].size
    for name,expected in SOURCE_PINS.items():assert digest(ROOT/name)==expected,name
    record={'passed':True,'environment':'local_integration_reuses_completed_MC' if LOCAL_MODE else 'Colab','source_commit':SOURCE_COMMIT,'source_files':len(SOURCE_PINS),'compared_values':compared,'atol':1e-10,'rtol':1e-9,'X_sha256':digest(X_ARCHIVE),'python':sys.version,'numpy':np.__version__,'pandas':pd.__version__}
    (OUTPUT/'notebook_comparison.json').write_text(json.dumps(record,indent=2)+'\\n')
    print(json.dumps(record,indent=2))
    ''')
    setcell(7,'''
    aggregate=pd.read_csv(OUTPUT/'observed_aggregate.csv.gz')
    display(aggregate[aggregate.family.eq('temporal4')&aggregate.block.eq(21)][['profile','statistic','estimate','ci_low','ci_high','p_adjusted']])
    calibration=pd.read_csv(OUTPUT/'calibration_families.csv');display(calibration[calibration.adjusted])
    coverage=pd.read_csv(OUTPUT/'calibration_cases.csv');display(coverage[coverage.event.eq('coverage')].groupby(['mechanism','family']).rate.agg(['min','max']))
    for name in ['lab03g_temporal','lab03g_calibracao']:display(Image(filename=str(OUTPUT/'figures'/(name+'.png'))))
    ''')
    setcell(8,'''
    ## Interpretação e salvamento

    Os valores-p são aproximações centradas, e os ICs básicos são marginais. A calibração expõe subcobertura: não interpretar o rótulo 95% como cobertura demonstrada. Controle sob nulidade global simulada não demonstra controle forte sob todas as alternativas ou leis financeiras. Os modelos dinâmicos/semanais e outros comprimentos ainda não receberam essa calibração.

    Mudança média agregada não é mudança de cada ativo; ausência de rejeição não prova simetria, equivalência ou persistência. Retirar março ou um semestre muda o alvo temporal e não identifica uma causa. Auditoria econômica global, sobrevivência e dados disponíveis em cada época continuam limitando o alcance. Representação/raciocínio permanece uma proposta não avaliada.

    O ZIP final preserva fontes, resultados, gráficos e hashes, sem a matriz privada de retornos. Ele será salvo em `alem_do_beta/lab03g_resultados`. **Salve também o notebook executado no Drive e envie o link da cópia.**
    ''')
    setcell(9,''.join(cells[9]['source']).replace('lab03f','lab03g'))
    nb['metadata']['colab']['name']='Lab03G_mudanca_calibracao.ipynb';return nb


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--source-commit',required=True);p.add_argument('--output',required=True,type=Path);a=p.parse_args();nb=build(a.source_commit)
    for i,c in enumerate(nb['cells']):
        if c['cell_type']=='code':compile(''.join(c['source']),f'cell{i}','exec')
        else:assert not any(x.startswith('    ') for x in c['source'])
    a.output.write_text(json.dumps(nb,ensure_ascii=False,indent=1)+'\n');print('Notebook G:',len(nb['cells']),'cells; bytes',a.output.stat().st_size)
