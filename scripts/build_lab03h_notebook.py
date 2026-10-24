#!/usr/bin/env python3
"""Compact H launcher: immutable sources, existing X and existing G banks."""
import argparse,hashlib,inspect,json,importlib.util
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('g_notebook',ROOT/'scripts/build_lab03g_notebook.py');g=importlib.util.module_from_spec(spec);spec.loader.exec_module(g)
REFERENCE='results/tables/lab03h_pos_parecer_v4_20261024/'


def build(commit):
    nb=g.build(commit);cells=nb['cells']
    def setcell(i,text):
        text=inspect.cleandoc(text).strip()+'\n';cells[i]['source']=text.splitlines(True);cells[i]['id']=hashlib.sha1(text.encode()).hexdigest()[:12]
    setcell(0,'''
    # Lab03H — Crise de 2020 e diagnóstico da calibração

    **Execute tudo em CPU e salve a cópia e o ZIP no Drive.** Este notebook executa apenas as análises H. Não repete F/E nem os 6.000 geradores de G. Reutiliza o cache X autenticado e os bancos já publicados; não baixa cotações.

    Preserva as amostras fixas 80/117, ativo/classe/ISIN, dez setores e ausências. Exclui março ou 2020-S1 apenas da primeira metade e mantém os mesmos 80 ativos recentes. Mostra valores-p brutos/ajustados, quantidades, incerteza, diagnóstico de escala/CDF e gráficos dos dez anos. CDF é exploratório e não substitui a inferência original.

    O pacote do adendo sobre universo escolhido em 2015 foi recebido; sua reconstrução é tratada separadamente no lote I. Este notebook reproduz H e não certifica seleção, causalidade ou auditoria econômica global.
    ''')
    setcell(1,''.join(cells[1]['source']).replace('lab03g','lab03h').replace('Lab03G','Lab03H'))
    setcell(2,'''
    ## Fontes e cache

    O código vem de um commit público imutável e cada arquivo tem SHA256. O cache X já existente é autenticado antes do cálculo. A pasta compartilhada `alem_do_beta/lab03f_cache` é reutilizada; se o arquivo não estiver lá, procura-se uma cópia idêntica no Drive antes de transferi-lo pelo ID conhecido. Não há nova coleta de mercado.
    ''')
    lock=json.loads((ROOT/'data/lab03h/inputs_manifest.json').read_text());files=set(lock['source_pins'])
    files|={'src/lab03h.py','scripts/run_lab03h.py','scripts/verify_lab03h.py','scripts/plot_lab03h.py','tests/test_lab03h.py','data/lab03h/plano_v1.json','data/lab03h/inputs_manifest.json'}
    files|={REFERENCE+p.name for p in (ROOT/REFERENCE).iterdir() if p.is_file()}
    pins={n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in sorted(files)}
    code=''.join(cells[3]['source']);code=code[code.index('for name,expected in SOURCE_PINS.items():'):]
    setcell(3,f'SOURCE_COMMIT={commit!r}\nSOURCE_PINS={pins!r}\n'+code)
    setcell(4,'''
    ## Plano e verificações

    Plano pós-parecer, com F/G conhecidos. Nova família secundária H4: média/mediana da mudança × duas exclusões. G4 tem composição diferente; mostrar também valores brutos. Bloco principal 21, sensibilidades 5/63, todos preservados. Os pisos e as lacunas não são relaxados. Não se criam blocos através dos intervalos excluídos.

    O cálculo reproduz os bancos G originais, executa os novos contrastes e consulta os 84.000 registros de calibração já existentes. Não realiza nova simulação externa. Os quatro testes H e o verificador independente conferem fórmulas/cálculos, sem validar a cobertura dos novos alvos ou uma substituição CDF.
    ''')
    setcell(5,'''
    subprocess.run([sys.executable,'-m','unittest','discover','-s',str(ROOT/'tests'),'-p','test_lab03h.py','-v'],check=True)
    OUTPUT=RUN/'outputs'
    script('run_lab03h.py','--x-archive',X_ARCHIVE,'--output',OUTPUT)
    ''')
    setcell(6,'''
    script('verify_lab03h.py','--x-archive',X_ARCHIVE,'--output',OUTPUT)
    script('plot_lab03h.py','--output',OUTPUT)
    reference=ROOT/'results/tables/lab03h_pos_parecer_v4_20261024'
    compared=0;threshold_positions=0
    for expected_path in sorted(reference.glob('*.csv*')):
        name=expected_path.name
        observed=pd.read_csv(OUTPUT/name,float_precision='round_trip');expected=pd.read_csv(expected_path,float_precision='round_trip')
        pd.testing.assert_frame_equal(observed,expected,check_exact=False,atol=1e-10,rtol=1e-9);compared+=observed.size
        for col in observed.select_dtypes(include='number'):
            if col.startswith('p_'):
                np.testing.assert_array_equal(observed[col].le(.05),expected[col].le(.05));threshold_positions+=len(observed)
    with np.load(OUTPUT/'crisis_draws.npz') as actual,np.load(reference/'crisis_draws.npz') as expected:
        assert actual.files==expected.files
        for key in actual.files:np.testing.assert_allclose(actual[key],expected[key],atol=1e-10,rtol=1e-9);compared+=actual[key].size
    for name,expected in SOURCE_PINS.items():assert digest(ROOT/name)==expected,name
    record={'passed':True,'environment':'local_notebook_integration' if LOCAL_MODE else 'Colab','source_commit':SOURCE_COMMIT,'source_files':len(SOURCE_PINS),'compared_values':compared,'p_threshold_positions':threshold_positions,'atol':1e-10,'rtol':1e-9,'X_sha256':digest(X_ARCHIVE),'python':sys.version,'numpy':np.__version__,'pandas':pd.__version__,'new_outer_generators':0,'external_2015_package_reproduced':False}
    (OUTPUT/'notebook_comparison.json').write_text(json.dumps(record,indent=2)+'\\n')
    print(json.dumps(record,indent=2))
    ''')
    setcell(7,'''
    aggregate=pd.read_csv(OUTPUT/'crisis_aggregate.csv.gz')
    display(aggregate[aggregate.block.eq(21)][['profile','statistic','estimate','ci_low','ci_high','p_centered','p_holm4']])
    display(pd.read_csv(OUTPUT/'scale_diagnostics.csv'))
    display(pd.read_csv(OUTPUT/'period_observations.csv').groupby(['profile','period'])[['n_pairs','n_plus','n_minus']].agg(['min','median','max']))
    for name in ['lab03h_crise','lab03h_periodo_completo']:display(Image(filename=str(OUTPUT/'figures'/(name+'.png'))))
    ''')
    setcell(8,'''
    ## Interpretação e salvamento

    Sinais positivos não demonstram mudança causal; os novos contrastes não rejeitam na escolha principal H4. Valores-p centrados e ICs básicos nominais não são duais. A calibração anterior não valida automaticamente as novas máscaras; CDF é diagnóstico pós-observação com incerteza Monte Carlo, não uma inferência primária corrigida.

    Gráficos anuais mostram mediana e IQR entre ativos, não IC. A escala econômica é uma decomposição algébrica por ativo, sem carteira, perda esperada ou pesos de empresas. Preservam-se limitações de seleção retrospectiva/liquidez, eventos e auditoria econômica. KRR continua proposta não avaliada.

    O ZIP inclui fontes, resultados, gráficos e hashes, sem a matriz privada de retornos. Será salvo em `alem_do_beta/lab03h_resultados`. **Salve também este notebook executado no Drive e envie o link da cópia.**
    ''')
    export_code=''.join(cells[9]['source']).replace('lab03g','lab03h')
    export_code=export_code.replace("print('Export:',export.name","with export.open('rb') as stream:os.fsync(stream.fileno())\nwith zipfile.ZipFile(export) as verify_zip:\n    assert verify_zip.testzip() is None\n    saved=json.loads(verify_zip.read('manifesto_exports.json'))\n    assert set(saved)==set(verify_zip.namelist())-{'manifesto_exports.json'}\n    for name,expected in saved.items():assert hashlib.sha256(verify_zip.read(name)).hexdigest()==expected,name\nprint('Export:',export.name")
    setcell(9,export_code)
    nb['metadata']['colab']['name']='Lab03H_crise_calibracao.ipynb';return nb


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--source-commit',required=True);p.add_argument('--output',required=True,type=Path);a=p.parse_args();nb=build(a.source_commit)
    for i,c in enumerate(nb['cells']):
        if c['cell_type']=='code':compile(''.join(c['source']),f'cell{i}','exec')
        else:assert not any(x.startswith('    ') for x in c['source'])
    a.output.write_text(json.dumps(nb,ensure_ascii=False,indent=1)+'\n');print('Notebook H:',len(nb['cells']),'cells; bytes',a.output.stat().st_size)
