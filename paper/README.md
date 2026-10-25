# Manuscrito — edição editorial v8 (25/10/2026)

Artigo: **15 páginas**, incluindo referências. Suplemento: **34 páginas**. Fonte e margens SBC preservados. Os PDFs desta edição são identificados por SHA-256 no manifesto da distribuição; não use arquivos de outras pastas ou cópias com nomes genéricos para avaliar esta edição.

## Compilar no Overleaf

Envie o ZIP `distribution/alem_do_beta_v8_overleaf_20261025.zip`. Ele contém este diretório diretamente na raiz. Defina **main.tex** como principal, com pdfLaTeX/BibTeX. Para o suplemento, defina **suplemento.tex**. Preserve as pastas `figures/` e `tables/`.

## Compilar localmente

Na raiz do repositório: `python scripts/build_paper.py`. Requer pdfLaTeX, BibTeX, Poppler e Babel para português brasileiro. O build não baixa dados nem executa estimadores; sua saída e recibo identificam versão e hashes. O ZIP também contém `docs/EDICAO_V8.md`, com o guia da edição.

Os valores de λ, γ e λ+γ e todos os p-valores da revisão são reconstruídos dos CSVs congelados por `scripts/build_editorial_tables.py`; a opção `--check` só confere as saídas. Os números e as famílias anteriores não foram recalculados ou alterados.

## Compartilhar e verificar

Distribua os PDFs com nomes de versão, o pacote de fontes e o manifesto em `distribution/`, ou os links fixados no commit da entrega. A compilação pode ser feita sem Drive; a reestimação integral exige os insumos externos identificados nos recibos. `docs/DIREITOS_E_DADOS.md`, incluído no ZIP, delimita direitos e acesso. Não se atribuiu licença geral a materiais de terceiros nem se certificou validade estatística universal.
