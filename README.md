# Além do Beta

Repositório público do artigo: [robsondf/alem-do-beta-publico](https://github.com/robsondf/alem-do-beta-publico). Histórico de desenvolvimento: `robsondf/alem-do-beta` (privado).

Manuscrito empírico sobre assimetria dos betas de alta e baixa, liquidez e seleção em ações brasileiras. Unidade de análise: ativo/classe; amostras fixas de 80 ativos em 2016–2025 e 117 em 2021–2025, em dez setores. Regressões sobre retornos, sem seleção anual ou preenchimento de lacunas.

## Edição editorial v8 — 25/10/2026

- [Artigo, 15 páginas](distribution/alem_do_beta_v8_20261025.pdf)
- [Suplemento, 34 páginas](distribution/suplemento_alem_do_beta_v8_20261025.pdf)
- [Fontes para Overleaf](distribution/alem_do_beta_v8_overleaf_20261025.zip)
- [Manifesto de arquivos](distribution/manifest_v8_20261025.json) e [SHA-256](distribution/SHA256SUMS_v8_20261025.txt)
- [Reprodução e ajustes editoriais](docs/EDICAO_V8.md) · [Direitos e dados](docs/DIREITOS_E_DADOS.md)

No Overleaf, use `main.tex` do ZIP como principal; para o suplemento, `suplemento.tex`. Código completo, tabelas públicas, notebooks e recibos estão nesta árvore e no arquivo ZIP do GitHub, fixado no commit da entrega. `CITATION.cff` identifica a edição como manuscrito de trabalho, sem DOI ou aceite atribuídos.

## Verificar a distribuição

```bash
python scripts/verify_distribution.py
python scripts/build_editorial_tables.py --check
```

O primeiro comando usa somente a biblioteca padrão do Python. O segundo exige pandas e confere a apresentação dos CSVs existentes, sem novos modelos. Para compilar os PDFs: `python scripts/build_paper.py`, com as dependências LaTeX descritas no guia.

## Estado da evidência

Os notebooks do autor, incluindo a execução de porte/liquidez, foram conferidos por exports autenticados. O último é [Lab03K executado](https://colab.research.google.com/drive/1MCwjoZh864rnHgLbIScW0uM1HVXuVPZc); recibos em `data/lab03k/`. **Nenhum novo notebook é necessário nesta edição.** Os protocolos, fontes congeladas e famílias anteriores são preservados.

Código, dados derivados, figuras e manifestos públicos permitem verificar a apresentação. Matrizes diárias e caches autenticados continuam no Drive; a reestimação integral exige seu acesso. Direitos e condições das fontes não são substituídos pelo manifesto. O projeto ainda não recebeu licença geral de reutilização.

A edição não elimina seleção retrospectiva/sobrevivência, incerteza de eventos ou subcobertura dos intervalos. Não afirma causalidade, persistência futura, ganho preditivo ou contribuição própria em IA. O histórico e os pareceres estão documentados em `docs/` e nos commits anteriores; o desenvolvimento de origem está em https://github.com/robsondf/alem-do-beta.
