# Leitura, execução e verificações

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

## LaTeX

```bash
cd paper
pdflatex -interaction=nonstopmode -halt-on-error main.tex
bibtex main
pdflatex -interaction=nonstopmode -halt-on-error main.tex
pdflatex -interaction=nonstopmode -halt-on-error main.tex
```

No Overleaf, carregue o conteúdo de `paper/`, defina `main.tex` como principal e use pdfLaTeX/BibTeX. É necessário suporte LaTeX para português brasileiro e os pacotes declarados no fonte. O PDF já incluído foi copiado sem recompilação.

## Alcance da verificação

A aprovação dos testes locais é diferente da conferência integral Colab registrada na origem, da calibração sob processos simulados e da identificação econômica dos retornos. Esta migração não repete essas etapas e não amplia suas garantias.
