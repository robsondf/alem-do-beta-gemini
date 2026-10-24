#!/usr/bin/env python3
"""Build a compact Colab notebook from the previously validated cache workflow."""
import argparse,inspect,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def build(runtime_id,runtime_sha,folder_id):
    old=json.loads((ROOT/'notebooks/Lab03D_inferencia_previsao.ipynb').read_text());cells=[]
    def add(kind,text):
        cell=dict(cell_type=kind,metadata={},source=inspect.cleandoc(text).strip().splitlines(True))
        if kind=='code':cell.update(execution_count=None,outputs=[])
        cells.append(cell)
    add('markdown','''
    # Lab03E - Precisão, potência e validação das limitações

    Avalia todos os **197 casos estáticos**, **474 hipóteses temporais** e **394 combinações preditivas** em um único laboratório. Estima e prevê **retornos logarítmicos**, não preços. Amostras fixas 80/117, classes e dez setores preservados.

    Execute **Ambiente de execução → Executar tudo**, CPU. Reutiliza os ZIPs autenticados X, B e D, sem baixar cotações ou repetir laboratórios anteriores. A validação completa pode levar dezenas de minutos; há progresso durante as simulações e conferências. Não interrompa uma célula que esteja emitindo progresso.

    **Estado:** preparação local calculada e verificada; execução efetiva deste novo Colab ainda será conferida depois de você salvar. O plano foi congelado antes dos resultados E, após resultados anteriores conhecidos; não é pré-registro independente. Os resultados desfavoráveis também são exportados.
    ''')
    setup=''.join(old['cells'][1]['source']).replace('lab03d','lab03e').replace('Lab03D','Lab03E');add('code',setup)
    add('markdown','''
    ## Entradas e proveniência

    Os três ZIPs e todos os membros internos são autenticados. Caches existentes no Drive são reutilizados por nome e SHA-256. Mantêm-se sete ausências na década, três nos 80 comuns e sete nos 117 recentes, incluindo os cinco retornos não identificáveis ABCB4/UGPA3. Sem preenchimento, interpolação ou pontes diárias inventadas. Light continua reconciliada.
    ''')
    obtain=''.join(old['cells'][3]['source']);start=obtain.index("RUNTIME_ID");end=obtain.index('def digest')
    constants=f'''RUNTIME_ID = {runtime_id!r}
RUNTIME_SHA = {runtime_sha!r}
X_ID = '1aExT7v-GD8s5xKzM0K-0LIIJER8E8Twg'
B_ID = '1hhLvxQpAnEGopDvnt1Mh9IbkV0gYt9Gb'
D_ID = '1MD8L0RcpMFbuKwPGErRaJxYO3_xmLZ9R'
X_SHA = '297da2afde534082c398324f308df7af134c9692e7d61d6e0b2b820341ea5214'
B_SHA = '645946c0bfee05cc7cbbc34b63af74700fcc7e0a3d3ac14ee7aaa398323fa26d'
D_SHA = 'c4e0ea2110cdd332296a671ff5d5758c39d8ca29572130e4af8bf34634b6e4c1'
FOLDER_ID = {folder_id!r}
''';obtain=constants+obtain[end:];obtain=obtain.replace('lab03d_cache','lab03e_cache');lo=obtain.index('    LOCAL_FILES = ');hi=obtain.index('\ndef obtain',lo);obtain=obtain[:lo]+"    LOCAL_FILES = {RUNTIME_ID:BASE/'runtime.zip', X_ID:BASE.parent/'work_lab03d_colab/x.zip', B_ID:BASE.parent/'work_lab03d_colab/b.zip', D_ID:BASE.parent/'work_lab03d_colab/resultados_colab.zip'}"+obtain[hi:];obtain+='\nD_ARCHIVE = obtain(D_ID,D_SHA)\n';add('code',obtain)
    unpack=''.join(old['cells'][4]['source']).replace('data/lab03d/','data/lab03e/');add('code',unpack)
    add('markdown','''
    ## Desenho congelado

    Banco novo de 99.999 sorteios por mecanismo, três fluxos independentes de 33.333, sem prolongamento condicionado ao valor-p. Validação inferencial: seis mecanismos × 1.000 réplicas, efeitos estáticos e dez padrões temporais. GARCH t5, quebra de variância e AR0,6 são estresses **fora da classe protegida de três mecanismos**; não ampliam a garantia do envelope. Primário HAC5 e famílias 197/474 preservados.

    Previsão: janelas 252/504, seis cenários × 1.000 réplicas, todos os 394 casos, blocos 21/42/63 e 1.999 reamostragens. O alvo é o risco esperado de previsão **condicional a todo o caminho observado do mercado, às máscaras e à lei geradora declarada**. Reestimam-se os modelos dos ativos em cada réplica, por operadores lineares exatos que só leem o passado. Inclui covariância treino-alvo sob AR. Não é validação da incerteza conjunta do mercado futuro, teste Clark-West/Giacomini-White ou holdout prospectivo intocado.
    ''')
    add('code','''
    check=subprocess.run([sys.executable,'-m','unittest','discover','-s',str(ROOT/'tests'),'-p','test_lab03e.py','-v'],capture_output=True,text=True)
    print(check.stdout+check.stderr);assert check.returncode==0
    from lab03e_common import load
    prepared=load(ROOT,X_ARCHIVE,B_ARCHIVE,D_ARCHIVE)
    display(prepared['design'].groupby('scenario').agg(ativos=('papel_id','size'),ausencias=('n_missing','sum')))
    assert prepared['design'].groupby('scenario').n_missing.sum().to_dict()=={'decada':7,'recente':7}
    ''')
    add('markdown','''
    ## Processamento integral

    Cada bloco trabalha o painel completo. As simulações preservam dependência entre ativos e sobreposição temporal. As verificações independentes podem continuar por alguns minutos entre mensagens de progresso. Não se escolhe um bloco, cenário ou método porque produziu rejeição ou cobertura melhor.
    ''')
    add('code','''
    OUTPUT=RUN/'outputs'
    CACHED_LOCAL=LOCAL_MODE and bool(os.environ.get('ALEM_BETA_LOCAL_CACHE'))
    if CACHED_LOCAL:
        shutil.copytree(Path(os.environ['ALEM_BETA_LOCAL_CACHE']),OUTPUT)
        print('Integração local com cálculos já realizados; não é nova simulação integral nem execução Colab.')
    else:
        OUTPUT.mkdir()
        script('run_lab03e_inference.py','--x-archive',X_ARCHIVE,'--b-archive',B_ARCHIVE,'--d-archive',D_ARCHIVE,'--output',OUTPUT/'inference')
    ''')
    add('code','''
    if not CACHED_LOCAL:
        script('run_lab03e_prediction.py','--x-archive',X_ARCHIVE,'--b-archive',B_ARCHIVE,'--d-archive',D_ARCHIVE,'--output',OUTPUT/'prediction')
    ''')
    add('code','''
    script('extract_lab03e_fras.py')
    if not CACHED_LOCAL:
        script('run_lab03e_economic.py','--x-archive',X_ARCHIVE,'--b-archive',B_ARCHIVE,'--d-archive',D_ARCHIVE,'--output',OUTPUT/'economic')
        for stage in ['inference','prediction','economic']:
            for p in (OUTPUT/stage).iterdir():
                target=OUTPUT/p.name;assert not target.exists();p.replace(target)
            (OUTPUT/stage).rmdir()
    for name,expected in source_manifest.items():assert digest(ROOT/name)==expected,name
    for name in ['metricas_inferencia.json','metricas_previsao.json','metricas_economia.json']:print((OUTPUT/name).read_text())
    ''')
    add('markdown','''
    ## Conferências e interpretação

    Três verificadores independentes: regressões completas com quatro/oito colunas, HC3-HAC5 e calendário original; risco quadrático exato, previsões e bootstrap por índices; todas as 1.970 sensibilidades econômicas e identidade de exclusão de uma observação. Aprovação numérica não é homologação econômica ou prova de cobertura nominal.

    A família preditiva adicional tem 394 posições (duas janelas × 80+117); os 80 comuns não são uma nova família. Os ICs conjuntos usam máximo padronizado por grupo e Bonferroni entre quatro grupos, **sem garantia automática**. Todos os cenários de cobertura, inclusive falhas, permanecem visíveis.
    ''')
    add('code','''
    reused=LOCAL_MODE and os.environ.get('ALEM_BETA_LOCAL_VERIFIED')=='1'
    for label in ['inference','prediction','economic']:
        if not reused:
            print('Iniciando conferência independente:',label,flush=True)
            script('verify_lab03e_'+label+'.py','--output',OUTPUT,'--x-archive',X_ARCHIVE,'--b-archive',B_ARCHIVE)
    for name in ['validacao_inferencia_independente.json','validacao_previsao_independente.json','validacao_economia_independente.json']:
        record=json.loads((OUTPUT/name).read_text());assert record['passed'];print(name,json.dumps(record,indent=2))
    if reused:print('Integração local reutiliza os três verificadores recém-executados e aprovados; no Colab esta opção não se aplica.')
    ''')
    add('code','''
    script('plot_lab03e.py','--output',OUTPUT)
    for name in ['lab03e_inferencia','lab03e_potencia_precisao','lab03e_cobertura_previsao','lab03e_intervalos_observados','lab03e_impacto_economico']:
        display(Image(filename=str(OUTPUT/'figures'/(name+'.png'))))
    ''')
    add('code','''
    display(pd.read_csv(OUTPUT/'observed_static_precision.csv').query("bank == 'pooled' and p_holm_197 < .05")[['ticker','scenario','delta','p_rank','p_holm_197']])
    coverage=pd.read_csv(OUTPUT/'predictive_family.csv')
    display(coverage[['mechanism','delta','block_length','method','mean_coverage','joint_coverage','fwer_gain_positive']])
    ledger=pd.read_csv(OUTPUT/'economic_ledger.csv')
    display(ledger.groupby('scenario')[['conditional_scenario_delta_spread','max_absolute_diagnostic_shift']].agg(['median','max']))
    ''')
    add('markdown','''
    ## Alcance e exportação

    A precisão Monte Carlo aumentou; a potência temporal e a cobertura preditiva agora foram avaliadas sob leis explícitas. Isso não elimina as falhas encontradas, não prova estabilidade por não rejeição e não autoriza selecionar retrospectivamente o bloco que passou. ICs preditivos permanecem exploratórios.

    Há 197 registros de impacto econômico. Remover as observações de maior influência ou vizinhos de lacunas é **diagnóstico**, não correção da base. A escala para um movimento de mercado de 1% contém só a inclinação, sem intercepto ou risco residual; não é previsão, VaR ou retorno total.

    Frasle: recuperou-se a planilha publicada com 46 linhas, 25 com data ex-fonte em 2016–2025 e 12 em 2021–2025. Existem duas inconsistências cronológicas nessa janela; datas não foram consertadas por suposição. Extração integral da tabela publicada não comprova completude econômica, harmonização fiscal ou vintage histórico. ANIM3 e conflito RENDIMENTO permanecem. **Global: 0/197 homologados.**

    Permanecem seleção retrospectiva/sobrevivência, vintages revisados, lacunas não identificáveis, setores pequenos e ausência de validação prospectiva. Protocolos, fontes, réplicas e todos os resultados serão exportados. O ZIP pode superar 350 MB; o salvamento no Drive usa upload retomável. **Salve também este notebook depois de executar tudo.**

    Referências: Dufour (2006), DOI 10.1016/j.jeconom.2005.06.007; Phipson e Smyth (2010), DOI 10.2202/1544-6115.1585; Bollerslev (1986), DOI 10.1016/0304-4076(86)90063-1; Morris et al. (2019), DOI 10.1002/sim.8086. Fonte Frasle: https://ri.fraslemobility.com/informacoes-aos-investidores/mercado-de-capitais/dividendos-e-juros-sobre-capital-proprio/ .
    ''')
    export=''.join(old['cells'][16]['source']).replace('lab03d','lab03e').replace('Lab03D','Lab03E');add('code',export)
    return dict(cells=cells,metadata={'colab':{'name':'Lab03E_validacao_limitacoes.ipynb','provenance':[]},'kernelspec':{'display_name':'Python 3','name':'python3'},'language_info':{'name':'python','version':'3'}},nbformat=4,nbformat_minor=5)
if __name__=='__main__':
    p=argparse.ArgumentParser()
    for n in ['runtime-id','runtime-sha','folder-id']:p.add_argument('--'+n,required=True)
    p.add_argument('--output',required=True,type=Path);a=p.parse_args();notebook=build(a.runtime_id,a.runtime_sha,a.folder_id)
    for i,cell in enumerate(notebook['cells']):
        if cell['cell_type']=='code':compile(''.join(cell['source']),f'cell{i}','exec')
        else:assert not any(line.startswith('    ') for line in cell['source'])
    a.output.write_text(json.dumps(notebook,ensure_ascii=False,indent=1)+'\n');print('Notebook:',len(notebook['cells']),'cells;',sum(c['cell_type']=='code' for c in notebook['cells']),'code cells')
