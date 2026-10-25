# Edição editorial v8 — 25/10/2026

Esta edição fecha M1–M4 e as recomendações de apresentação dos pareceres da sétima versão. A base pública autenticada é `cbd16eb77969310db1d0d7e7ce3ca58e9d25137f`; a privada é `3afd6f5d396b9cb0e305eff3e6b61c68e2ac3106`. Não houve nova seleção de ativos, download de cotações, estimação ou simulação. As fontes congeladas e famílias estatísticas anteriores permanecem intactas.

## Arquivos para compartilhar

- `distribution/alem_do_beta_v8_20261025.pdf`: artigo.
- `distribution/suplemento_alem_do_beta_v8_20261025.pdf`: suplemento.
- `distribution/alem_do_beta_v8_overleaf_20261025.zip`: fontes para compilar no Overleaf, com o conteúdo de `paper/` na raiz do ZIP, sem os PDFs compilados anteriores.
- `distribution/manifest_v8_20261025.json` e `SHA256SUMS_v8_20261025.txt`: identificação exata de arquivos e versões.
- Arquivo completo do GitHub, fixado no commit da entrega: código, dados derivados públicos, notebooks e recibos. Não inclui os arquivos externos do Drive.

O ZIP de Overleaf contém `main.tex` diretamente na raiz: selecione-o como principal e use pdfLaTeX/BibTeX. Para o suplemento, selecione `suplemento.tex`. Não renomear um PDF antigo como se fosse o novo: o verificador compara tamanho e SHA-256 e rejeita essa troca.

## Verificação em um checkout ou arquivo completo do GitHub

```bash
python scripts/verify_distribution.py
python scripts/build_editorial_tables.py --check
python -m unittest discover -s tests -p test_distribution.py -v
```

O primeiro comando usa somente a biblioteca padrão do Python, confere os arquivos científicos distribuídos e todos os membros do ZIP sem extrair nem executar código recebido. O segundo reconstrói a apresentação numérica a partir dos CSVs congelados e requer pandas. Nenhum dos comandos acessa o Drive ou executa estimadores.

Para recompilar os PDFs em ambiente com pdfLaTeX, BibTeX, Poppler e Babel para português:

```bash
python scripts/build_paper.py
```

Em Debian/Ubuntu, o suporte de idioma é normalmente fornecido por `texlive-lang-portuguese`; Overleaf costuma incluí-lo. O parâmetro opcional `--texinputs DIRETORIO` permite indicar uma instalação já existente, sem baixar ou substituir o pacote de idioma.

O build fixa a época e a metainformação do PDF. A reconstrução binária foi conferida em dois diretórios no mesmo ambiente; outra distribuição TeX pode produzir bytes diferentes. O SHA-256 identifica a cópia entregue, enquanto os recibos de estimação registram tolerâncias numéricas entre ambientes. Hashes não são prova de validade estatística ou assinatura digital do autor.

## Ajustes e critérios científicos

| Item | Entrega e critério |
|---|---|
| M1 | Abstract e resumo com menos de 150 palavras, contraste médio da década, comparação COTAHIST entre universos, associação inicial e teste conjunto; conclusão com resultados quantitativos e limites. |
| M2 | Tabela de controles mostra λ, γ e λ+γ com ICs nominais, mais p bruto/Holm 2 conjunto. Reparametrização não é nova robustez ou efeito individual ajustado. |
| M3 | ChatGPT/Codex, Claude e Gemini nomeados com papéis documentados. Não são inventadas versões, validações humanas ou autoria de terceiros. |
| M4 | Meta de até 15 páginas, incluindo referências, preservando os sete quadros de resultados/multiplicidade, o gráfico dos dez anos e todas as estimativas. Detalhes de métodos e a figura das exclusões foram transferidos ao suplemento. Fonte e margens do template permanecem. |
| R1 | Valores-p brutos e Holm 6 de todas as seis sensibilidades nos três blocos; quatro de seis, não cinco, têm p bruto abaixo de 0,05 no bloco 21. |
| R2 | Texto registra ausência de atenuação sistemática com defasagens, sem transformar o padrão em identificação causal de microestrutura ou risco econômico. |
| R3 | Famílias são nomeadas pelo alvo no corpo; histórico de experimentos fica nos recibos e suplemento. Correções e tamanhos das famílias são preservados. |

Os resumos não confundem −0,177 da referência original com −0,086 do outro universo como se variasse apenas seleção. A comparação comum COTAHIST é −0,1685/−0,0857. Não se adotam as afirmações de que seleção causou a diferença, colinearidade foi solucionada ou falhas de cobertura foram eliminadas. O sinal −0,297 e os cabeçalhos λ̂/γ̂ já estavam corretos no PDF anterior; não houve correção fictícia desses símbolos.

## Proveniência e limites

O Colab do autor já conferido é `1MCwjoZh864rnHgLbIScW0uM1HVXuVPZc`; recibos em `data/lab03k/`. A edição não exige outro notebook. As cinco ausências de direitos e demais lacunas, amostras 80/117, unidade ativo/classe e não agregação por empresa permanecem. A certificação econômica 0/197 e a subcobertura de alguns intervalos continuam limitações explícitas.

Consulte `DIREITOS_E_DADOS.md` antes de reutilização além da leitura/avaliação. Licença de terceiros e acesso às matrizes não são concedidos pelo manifesto. A escolha de veículo e o vínculo com a dissertação para o PPGC permanecem decisões a alinhar com o orientador.
