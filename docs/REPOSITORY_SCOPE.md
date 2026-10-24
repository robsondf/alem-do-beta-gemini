# Escopo desta cópia

Origem fixa: `robsondf/alem-do-beta`, commit `c21b086b976ec11549fb4feb211099e0d78c61cc`, após o merge do PR #85. Destino criado pelo autor: `robsondf/alem-do-beta-gemini`, com visibilidade pública observada em 24/10/2026.

## Revisão pós-parecer

A revisão do commit `f06060c6e7db7de4f966f152b362c88283b44469` do projeto de origem, PR #86, atualiza o manuscrito e acrescenta resposta aos pareceres, proposta KRR e tabelas derivadas exclusivamente de resultados já existentes. A proveniência preserva hashes anteriores e identifica cada revisão. A cópia pública inicial `774f11fccbcdc9ff8086cc4d7c64cc4fb64d494c` continua identificando a versão examinada pelos avaliadores. A proposta KRR não foi implementada/avaliada.

## Critério da seleção inicial

Mantiveram-se o manuscrito principal e suas dependências LaTeX, os módulos usados no escopo final e seus imports internos, testes, scripts de execução/verificação, protocolos, recibos e resultados efetivos das etapas temporal, setorial/de risco, C, D e E. As 49 fontes do runtime E foram preservadas, inclusive dependências documentais e o notebook D exigidos por esse runtime.

As tabelas em `results/tables/*_colab_20261023/` são os espelhos já presentes no GitHub, inclusive versões compactadas. Não são novos downloads dos resultados no Drive. Manifestos antigos continuam descrevendo os exports integrais originais; seus membros não devem ser confundidos com o subconjunto que existe nesta cópia.

Omitiram-se duplicatas de preparação local, notebooks de investigação anteriores sem dependência no runtime final, figuras não usadas no artigo, o dossiê histórico e a cronologia administrativa de acompanhamento. Esses arquivos não foram apagados da origem. A omissão não significa que suas evidências tenham sido invalidadas ou que as limitações documentadas tenham sido resolvidas.

## Registro auditável

`provenance/selection.json` identifica cada arquivo selecionado e cada arquivo omitido da árvore original, com caminho, tamanho e SHA-1 do objeto Git. As razões de omissão descrevem o recorte desta cópia. Novos textos de navegação e o verificador de empacotamento são identificados separadamente.

Na seleção inicial, nenhum código de estimação, teste original, protocolo congelado, resultado, figura ou fonte do manuscrito foi editado. Na revisão pós-parecer, o fonte e o PDF foram atualizados e os demais itens continuam preservados. Não houve execução de novos experimentos financeiros. Referências a repositório privado, recibos locais e arquivos externos são fatos das versões examinadas, sem atribuir disponibilidade pública aos respectivos dados.

## Materiais externos

Nenhum arquivo do Google Drive foi copiado, movido, apagado ou teve suas permissões alteradas. Identificadores e hashes já registrados no GitHub permanecem nos manifestos. A disponibilidade de um identificador não significa autorização de acesso ou redistribuição.

O histórico completo de commits não foi importado. A identificação do commit e os hashes preservam a ligação verificável com a versão de origem, sem transportar todo o histórico para o novo repositório.

## Lote F após o segundo parecer

A revisão F adiciona novas estimativas/sensibilidades explicitamente separadas das etapas congeladas. Código, plano, resultados locais conferidos, gráficos, notebook e artigo entram por nova PR. O único insumo financeiro reutilizado é o ZIP X autenticado que continua no Drive; nenhuma matriz de retornos é transferida para esta cópia. Veja `lab03f_pos_parecer.md`.
