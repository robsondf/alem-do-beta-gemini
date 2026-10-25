# Leitura, execução e verificações

## Checkpoint K — fechamento dos pareceres

Consulte [Lab03K](lab03k_fechamento.md) e [as disposições](resposta_pareceres_K.md). Execução do autor no Colab conferida: cinco códigos sem exceções, 20 fontes, 43 membros autenticados, 72.724 células de tabelas e 1.665.000 valores de bancos concordantes; 12.381 limiares preservados e gráfico idêntico. Não repetir os labs ou executar outro notebook nesta conferência. Artigo e suplemento registram a execução efetiva, preservando os resultados e as limitações.


## Colab J do autor conferido

[Registro, fontes e limites](lab03j_pareceres.md). Cinco códigos sem exceções, 372.959 valores concordantes, 816 limiares preservados e dois gráficos idênticos. Nenhum novo notebook nesta conferência; artigo/suplemento atualizados para nova revisão externa. Matrizes e export permanecem no Drive.


## Checkpoint anterior — Lab03J preparado localmente

Consulte [o lote J](lab03j_pareceres.md) e [as disposições dos pareceres](resposta_pareceres_J.md). A nova execução usa apenas export I e caches B3 já existentes; execução local conferida, Colab do autor ainda distinto. Artigo e suplemento distinguem associação condicional, limitações de mensuração e resultados efetivos. Não repetir estágios anteriores.


## Colab H/I do autor conferido — 24/10/2026

[Cópia executada e salva](https://colab.research.google.com/drive/1pHcTi0deFoiIiEvmFK4ZtYr5MM9p_i9l); [export correspondente](https://drive.google.com/file/d/1L5w3uJvjTU4XiQir1BGMF3XNCWLS-_Ru/view), 21.813.582 bytes, SHA256 `ff67a56f9b9cc8b91f11bcbcad311d6253fcfe95aef3f9e02303bad677b41e0e`. As dez fontes de células coincidem com a entrega imutável; seis códigos em sequência, zero exceções, 149 fontes autenticadas. O ZIP tem 207 membros: 206 arquivos cobertos pelo manifesto e o próprio manifesto. H e I foram reestimados no Colab; os 6.000 geradores anteriores não foram repetidos. Nenhuma nova cotação foi consultada.

Conferência externa: **722.947 valores concordantes** (123.067 de tabelas/bancos H e 599.880 dos bancos I), diferença máxima `8,881784197e−15`, tolerâncias absoluta `1e−10` e relativa `1e−9`; preservadas 612 posições de limiar de valores-p. Os três PNGs embutidos coincidem com os exports e os três PDFs renderizados coincidem com os do artigo em 144 dpi. Não se alega identidade binária geral. A tabela LaTeX de defasagens é formatação exclusiva do artigo; seu CSV subjacente foi comparado numericamente.

Oráculos independentes confiáveis reexecutados sobre cópias das saídas autenticadas: H confere 480 regressões por período, 36 estatísticas de sorteio, 84 linhas CDF, cinco covariâncias densas e 1.920 componentes econômicos; I confere 960 pontos/status, 120 linhas de IC/p, 360 estatísticas explícitas, 599.880 valores de bancos e 1.076 ajustes válidos separados por regime com defasagens. As sete lacunas estão preservadas. A checagem de tamanho/cobertura das novas associações e a validação econômica dos eventos continuam pendentes.

Recibos: `data/lab03i/validacao_colab_20261024.json`, `manifesto_colab_20261024.json` e `oraculos_colab_20261024.json`. Auditor reproduzível: `scripts/verify_lab03i_colab.py`. O notebook executado, ZIP, matrizes diárias derivadas e bancos I permanecem no Drive, com organização/compartilhamento preservados; somente recibos e hashes são adicionados ao Git.

**Não repetir H/I/F/G/E ou transferências. Nenhum notebook novo nesta conferência.** Os resultados, universos fixos 80/117, dez setores, famílias e interpretações permanecem. Auditoria econômica global 0/197 não significa 197 erros; eventos/cadeias de ISIN, seleção/attrition, vintages e calibração específica continuam limitações. KRR permanece proposta não implementada/avaliada. Próximo: revisão científica humana e fechamento editorial para entrega de 27/10/2026, extensão não confirmada.

## Reprodução atual H/I

[Link imutável do único Colab H/I](https://colab.research.google.com/github/robsondf/alem-do-beta-gemini/blob/fd51b25af552cb3dd3715c473c7b3156dd352b79/notebooks/Lab03I_selecao_liquidez.ipynb). Runtime `4689c35c49a303e84f35b66c55320190fb630937`, 149 fontes autenticadas.


Para reprodução futura, usar `notebooks/Lab03I_selecao_liquidez.ipynb`, em CPU; a execução atual foi conferida, sem necessidade de repetição. Inclui H e I e reutiliza os caches existentes; não repete F/G/E ou os 6.000 geradores. [Métodos, resultados, entradas e limites](lab03i_selecao_liquidez.md). A preparação local não é execução Colab do autor. O ZIP externo foi recebido e reproduzido; eventos e cobertura inferencial específica continuam pendentes.

## Ambiente

Use Python 3.12 ou superior em ambiente isolado. `requirements.txt` é a lista original do projeto, sem congelamento adicional de versões. Os recibos Colab preservados registram os ambientes efetivamente utilizados; este empacotamento não afirma igualdade de ambientes nem de resultados binários entre versões.

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

Os scripts de gráficos E também usam Pillow e PyMuPDF, e os geradores limitam threads com threadpoolctl. Caso não estejam no ambiente, instale essas dependências explicitamente:

```bash
python -m pip install pillow pymupdf threadpoolctl
```

## Conferir esta cópia sem caches financeiros

```bash
python scripts/check_repository.py
```

O comando verifica os bytes copiados contra os hashes Git registrados, os 49 hashes SHA-256 do runtime E, imports internos e dependências do artigo. Executa a suíte original com skips explícitos para os testes que exigem os caches externos ou o notebook histórico Lab02 deliberadamente omitido. Um skip não é uma validação aprovada. O código dos testes e dos modelos permanece inalterado.

Para exigir todos os testes originais, inclusive as entradas externas:

```bash
python scripts/check_repository.py --require-all-tests
```

Essa modalidade falhará se as respectivas entradas não forem fornecidas. A descoberta direta com `unittest discover` também exige os artefatos externos, pois os testes originais não foram reescritos para este recorte.

As variáveis `LAB02Y_X_ARCHIVE`, `LAB03_X_ARCHIVE` e `LAB03_Y_ARCHIVE` recebem caminhos locais dos ZIPs autenticados X/Y já existentes. O teste do notebook histórico exige a cópia exata de `notebooks/02_betas.ipynb` da origem; o arquivo não integra esta seleção. Não faça nova coleta de cotações para substituir esses artefatos.

## Repetir a análise E com as entradas existentes

Forneça os ZIPs X, B e D com os hashes de `data/lab03e/inputs_manifest.json`. As rotinas rejeitam entradas incompatíveis. Exemplo, após colocar os arquivos já autorizados em caminhos locais:

```bash
python scripts/run_lab03e_inference.py --x-archive /caminho/X.zip --b-archive /caminho/B.zip --d-archive /caminho/D.zip --output /caminho/execucao_E_inferencia
python scripts/run_lab03e_prediction.py --x-archive /caminho/X.zip --b-archive /caminho/B.zip --d-archive /caminho/D.zip --output /caminho/execucao_E_previsao
python scripts/run_lab03e_economic.py --x-archive /caminho/X.zip --b-archive /caminho/B.zip --d-archive /caminho/D.zip --output /caminho/execucao_E_economia
```

As pastas de saída devem ser novas. Os experimentos são computacionalmente caros e não são necessários para uma primeira avaliação do artigo. Os verificadores independentes `verify_lab03e_inference.py`, `verify_lab03e_prediction.py` e `verify_lab03e_economic.py` usam `--output`, `--x-archive` e `--b-archive`; `--output` deve apontar ao export completo adequado, não apenas ao espelho leve do GitHub. Os espelhos leves não contêm todas as matrizes NPZ exigidas pelos verificadores.

Os cinco notebooks copiados são versões congeladas da origem. Eles preservam URLs, versões e caminhos originais; não se afirma que sejam lançadores autossuficientes deste repositório público. Para trabalhar apenas com esta cópia, prefira os scripts e as entradas autenticadas descritas acima. Não é necessário executar nenhum Colab novo para esta migração.

## Conferência efetiva do Colab G

O autor executou/salvou G, e a conferência externa foi concluída em24/10/2026. Não repetir G/F/E/transferências; nenhum novo notebook nesta atualização. Fontes,88 arquivos e1.595.778 valores foram conferidos, preservando as decisões. Recibo:`data/lab03g/validacao_colab_20261024.json`.

Para auditar futuramente a cópia do notebook e o ZIP correspondente, já autorizados e baixados do Drive:

```bash
python scripts/verify_lab03g_colab.py --notebook /caminho/G_executado.ipynb --export /caminho/resultados_lab03g_20261024T173413Z.zip --output /caminho/NOVA_AUDITORIA_G
```

O auditor verifica hash/nome/tamanho do export contra o stdout, células, fontes, seis CSVs,66 vetores, três tabelas LaTeX e figuras; não executa o código do notebook/export. A opção `--reference-figures` compara adicionalmente os PNGs locais, se disponíveis. O cache X permite reexecutar o oráculo confiável `scripts/verify_lab03g.py` sobre uma cópia da saída autenticada, sem novos geradores. Pillow/PyMuPDF são necessários aos auditores de gráficos. Reproduzir o cálculo não certifica cobertura nominal, controle forte ou homologação econômica.

## Lançador G preservado para reprodução

F do autor já foi executado e conferido; não repetir F/E/transferência. Execute somente `notebooks/Lab03G_mudanca_calibracao.ipynb` em CPU, usando a cópia pública imutável indicada na entrega. O código autentica fontes/entrada X, reutiliza o cache do Drive e rejeita divergências antes de estimar. As células Markdown não usam recuo de bloco de código.

```bash
python scripts/run_lab03g.py --x-archive /caminho/X.zip --output /caminho/NOVA_G --stage all
python scripts/verify_lab03g.py --x-archive /caminho/X.zip --output /caminho/NOVA_G
python scripts/plot_lab03g.py --output /caminho/NOVA_G
```

A célula de simulação executa seis mecanismos ×1.000 réplicas com4.999 sorteios internos e informa progresso a cada50. O ZIP final e o notebook salvo permanecem no Drive. Uma interrupção antes do fim não é uma execução completa; não reduzir réplicas para obter o selo de conferência. As tabelas locais completas permitem comparar a nova execução, sob tolerância1e−10 absoluta/1e−9 relativa, sem exigir igualdade binária de CSV/PDF entre ambientes. Há testes da equivalência com OLS explícito, preservação de defasagens e retenção de sorteios inválidos.

O teste local de integração do notebook pode reutilizar a simulação completa já executada; seu recibo declara isso e não é conferência do Colab do autor. A calibração nova é condicional aos bancos/mercado e não valida nominalmente todos os ICs: as falhas são resultados, não exceções de código a esconder.

## LaTeX

```bash
cd paper
pdflatex -interaction=nonstopmode -halt-on-error main.tex
bibtex main
pdflatex -interaction=nonstopmode -halt-on-error main.tex
pdflatex -interaction=nonstopmode -halt-on-error main.tex
```

No Overleaf, carregue o conteúdo de `paper/`, defina `main.tex` como principal e use pdfLaTeX/BibTeX. É necessário suporte LaTeX para português brasileiro e os pacotes declarados no fonte. O PDF desta revisão foi recompilado. O suplemento independente usa `suplemento.tex`, com a mesma sequência pdfLaTeX/BibTeX (substitua `main` por `suplemento`). Não definir o suplemento ou o registro histórico como principal do artigo.

## Alcance da verificação

A aprovação dos testes locais é diferente da conferência integral Colab registrada na origem, da calibração sob processos simulados e da identificação econômica dos retornos. Esta migração não repete essas etapas e não amplia suas garantias.

## Auditar o Colab H/I salvo

O auditor não executa código recebido; a pasta de saída deve ser nova. Os hashes/nome/tamanho do ZIP são confrontados com o stdout do notebook salvo. São verificadas as 149 fontes, os 206 arquivos cobertos pelo manifesto, as tabelas, os bancos H e as figuras. A comparação adicional dos 120 bancos I exige o export local anterior autenticado por `data/lab03i/validacao_notebook_local.json`; com essa opção, o total é 722.947 valores. Sem ela, são 123.067, com a ausência declarada no recibo.

```bash
python scripts/verify_lab03i_colab.py --notebook /caminho/I_executado.ipynb --export /caminho/resultados_lab03i_20261024T220259Z.zip --output /caminho/NOVA_AUDITORIA_I --local-export /caminho/resultados_lab03i_20261024T214024Z.zip
```

Os oráculos confiáveis `verify_lab03h.py` e `verify_review_2015.py` podem ser executados em cópias das pastas autenticadas `outputs` e `outputs_I`; H exige também o cache X autenticado. Não executar scripts extraídos do pacote externo. A conferência computacional não elimina limites econômicos ou inferenciais.
