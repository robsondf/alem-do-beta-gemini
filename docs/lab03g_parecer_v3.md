# Lab03G — resposta empírica ao terceiro parecer

Protocolo pós-revisão escrito antes dos resultados G, com F conhecido; não é pré-registro independente. Bases incorporadas: original `2ab42138ebc272b63960ca4e9ce16df763bcc718` (PR88), pública `327fbfe1467a470cf2d110c2ce5c2c025784875c` (PR4). Nova branch/PR nos dois repositórios, sem merge automático.

## Colab G do autor conferido — 24/10/2026

[Cópia executada e salva](https://colab.research.google.com/drive/1wMxL0eVrRmteeY_igYPG9KOiP18VwYLQ);[export correspondente](https://drive.google.com/file/d/1jaKyp2CapivwnvHRoFGBtxneHr6N7Kd1/view),18.065.044 bytes/SHA256 `a8f391a7bf4edf67c109b303c9abcbd9cae8274e7a0d6b86430f407816df9158`. Dez fontes de células idênticas,seis códigos1–6,zero exceções;70 fontes e88 membros autenticados. A execução completa de6.000 réplicas está registrada como `Lab03G all`/`Colab`,sem novos downloads de mercado.

Conferência externa:seis tabelas e66 vetores bootstrap,**1.595.778 valores concordantes**,máximo6,786238238e−15 sob tolerâncias1e−10 absoluta/1e−9 relativa. Preservadas84.066 posições ajustadas e84.066 brutas de limiar. Três CSVs e três tabelas LaTeX são idênticos em bytes; não se alega identidade binária geral. Dois PNGs embutidos iguais aos exports,pixels iguais à preparação local e PDFs com render igual ao artigo em144dpi.

Verificador independente reexecutado sobre cópia autenticada da saída efetiva:198 estatísticas por OLS explícito,66 linhas/ICs/valores-p e276 taxas recalculadas,diferença máxima5,65e−15. Nenhum gerador foi repetido para esta auditoria. Registros:`data/lab03g/validacao_colab_20261024.json` e`manifesto_colab_20261024.json`;auditor reproduzível:`scripts/verify_lab03g_colab.py`. Os recibos locais anteriores permanecem históricos.

**Não repetir G/F/E/transferências; nenhum novo notebook nesta conferência.** Os resultados científicos e limitações permanecem:intervalos básicos com subcobertura51,8–95,8%,FWER temporal5,6% no estresse AR0,6,tamanho de modelos alternativos não calibrado,global0/197 econômico,sobrevivência/vintages/lacunas e KRR não implementado/avaliado. A reprodução computacional foi confirmada; validade econômica e inferencial geral não foram certificadas. Notebook e ZIP executados permanecem no Drive,sem mudança de organização ou compartilhamento.

## O que foi executado

- Cache X existente autenticado integralmente, sem download de cotações. Preservados80/117,ativo/classe/ISIN,dez setores, ausências e famílias originais197/474.
- Mudança pareada dos mesmos80 entre2016–2020 e2021–2025: média/mediana de theta. Holm4 inclui esses dois alvos e média/mediana inicial. Bloco21 principal,5/63 sensibilidades;4.999 sorteios compartilhados com F. Mediana das diferenças não é diferença de medianas.
- Média/mediana em lag1,leadlag1,semanal nos três recortes: Holm18 por escolha correspondente de bloco;21/5/63 sessões e4/1/13 semanas. Defasagens construídas antes de reamostrar linhas; nenhum salto de calendário artificial recalcula uma defasagem.
- Calibração sob nulidade global:1.000 réplicas em cada um de seis mecanismos,4.999 sorteios internos/bloco21. Famílias10 e4 separadas; bancos,mercado e parâmetros fixados. Nenhuma seleção de método, aumento adaptativo ou extensão da antiga garantia finita. Os três últimos mecanismos são estresses.

A preparação inicial foi local e sua integração reutilizou o Monte Carlo completo, conforme o recibo histórico. Posteriormente, o autor executou G integralmente no Colab; a conferência externa efetiva está acima, separada da integração local.

## Resultados efetivos

Média inicial−0,176760; média recente comum−0,010080. Mudança média pareada+0,166680, IC básico[0,062722;0,306627], pHolm4=0,0252 no bloco21;5/63:0,0224/0,0216. Mediana da mudança+0,135591,pHolm4=0,0508;5/63:0,0594/0,0396. Não escolher63 para concluir sobre a mediana. A mudança de um resumo do conjunto não demonstra mudança de cada ativo nem causa econômica.

Na família microestrutural, a escolha principal não rejeita nenhum dos18 alvos; p mínimo0,0756. Os dois recortes recentes têm todos os ajustados1. Em63 sessões, lag1 década rejeita média/mediana com0,0216/0,0238, sensibilidade preservada; não representa robustez uniforme. Esse tamanho e outros comprimentos não foram calibrados.

FWER ajustada original10: 1,6–3,1%; temporal4: 1,8–5,6%. Os Wilson95% estão na tabela completa. Frequências sob nulidade global não certificam controle forte para toda configuração ou lei financeira. No estresse AR0,6, a família temporal atinge5,6%,Wilson[4,34;7,20]; a cobertura da média inicial cai a51,8%.

**Falha material de cobertura:** entre84 casos alvo/mecanismo, ICs básicos cobrem 51,8–95,8%. A média inicial sob t5 heterocedástico/AR0,3 cobre60,7%. O rótulo95% não recebeu validação nominal. Teste bilateral centrado e IC básico não são duais; exportam-se os dois desempenhos. Não usar os extremos como limites econômicos garantidos nem trocar o procedimento para favorecer significância.

## Matriz do terceiro parecer

| Ponto | Ação e evidência | Estado/alcance |
|---|---|---|
| Mudança agregada ausente | Quatro testes,80 diferenças pareadas,12 linhas observadas e bancos completos | Executado; média detectável na família secundária, mediana sensível; ICs com subcobertura simulada |
| Tamanho do bootstrap principal desconhecido |6.000 simulações,84.000 linhas,252 taxas por caso e24 taxas familiares | Executado no bloco21/globalnull; não certifica controle forte nem elimina falha dos ICs |
| Só sinais nas versões defasada/semanal |54 linhas,Holm18,ICs e sorteios completos | Executado; principal sem rejeição; sensibilidade63 declarada; tamanho desses modelos pendente |
| Holm30 contado como30 hipóteses científicas | Principal mantém Holm10/bloco21; reporta0,0080/0,0234/0,0108 para média da década | Corrigido; Holm30 preservado como proteção conservadora entre escolhas |
| Explicação exclusiva por março | Retirada de março pHolm10=0,0826; retirada de semestre altera alvo/precisão | Alegação causal retirada; exclusões não identificam mecanismo |
| Média bootstrap inferida pelo ponto médio do IC | Média real do banco F−0,1199983054; viés+0,0106696262; ponto médio dos quantis−0,1070899131 | Correção factual; não confundir quantis com esperança |
| Referência brasileira Faria/Santos | Fonte primária e Eq8/9 consultadas; amostra21,2006–2010,Ibovespa/Selic; ano da edição2010 | Acrescentada; D-CAPM trunca ambos os excessos e tem outro estimando |
| Excesso operacional/preditivo | Previsão condensada; calibração individual detalhada e algoritmo/gráficos em suplemento | Principal e suplemento compiláveis separadamente; dados/resultados históricos preservados |
| Relevância econômica por carteira | Mantida escala de inclinação e risco por ativo | Não criar carteira,pesos empresariais ou perda esperada a partir de delta isolado |
| Publicação/linha de pesquisa | KRR permanece proposta,não implementação/resultado | Parecer IA não é revisão humana; elegibilidade normativa deve ser confirmada com orientação/PPGC |

Parecer3:4 páginas,SHA256 `b02c396931703704c54def82616aeafa50965d1d83f8d64ff6e390d3a8895d55`; examinou a revisão F, não repetiu o bootstrap. Não se incorporou o PDF do avaliador ao GitHub. A frase de que o início era estatisticamente detectável não era fato validado antes de G; agora há teste próprio. Não se adotam automaticamente seus juízos de publicação ou exigência genérica de ML.

## Reprodução e próximos passos

Notebook novo:[abrir Lab03G no Colab](https://colab.research.google.com/github/robsondf/alem-do-beta-gemini/blob/f8bbed220998f002f390c31df0566b0cb942fce8/notebooks/Lab03G_mudanca_calibracao.ipynb). Código fixado no commit público `880de4fa25a6ced45b137bd9d5f5126abf869f25`,70 pins individuais. O notebook imutável está em `f8bbed220998f002f390c31df0566b0cb942fce8`;10 células/seis códigos/20.096bytes,sem outputs embutidos. Integração serializada passou sem exceções,1.594.818 valores comparados e88 membros do export autenticados; reutilizou o Monte Carlo local completo, sem alegar nova simulação ou execução Colab do autor. O autor já executou e salvou; não repetir G/F/E nesta conferência. Para reprodução futura, executar tudo em CPU e salvar cópia/export no Drive. Progresso a cada50 réplicas; a simulação é a célula longa. Usa cache X existente e verifica SHA antes de estimar. Sem preencher lacunas ou baixar preços.

CLI: `python scripts/run_lab03g.py --x-archive CAMINHO_X --output NOVA_PASTA --stage all`; depois `scripts/verify_lab03g.py` e `scripts/plot_lab03g.py` com os mesmos argumentos apropriados. Plano e manifesto em`data/lab03g/`; tabelas/sorteios/replicações em`results/tables/lab03g_pos_parecer_v3_20261024/`.

Artigo principal Overleaf:`paper/main.tex`/`main.tex`; suplemento:`paper/suplemento.tex`. A conferência computacional desta execução G foi concluída. Restam revisão humana do argumento, destino/regras e entrega27/10. Global0/197 econômico,lacunas,sobrevivência/vintages,taxa diária autenticada,exposição futura e extensão KRR continuam limitações/frentes distintas, sem novo prazo ou garantia de aceite.
