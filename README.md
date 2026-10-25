# Além do Beta

**Lab03J do autor conferido:** cinco códigos sem exceções, 372.959 valores concordantes e gráficos idênticos. [Registro e limites](docs/lab03j_pareceres.md). Os PDFs atualizados registram a execução efetiva; pronto para nova revisão externa.

## Lab03J — controles e pareceres adicionais (24/10/2026)

[Resultados, limites e único notebook a executar](docs/lab03j_pareceres.md). A associação com liquidez diminui com porte, setor e beta tradicional; modelos completos não rejeitam após Holm16. O lote inclui84 diagnósticos das simulações existentes,83 disposições de eventos e três continuidades documentadas. Artigo16 páginas, suplemento26; gráfico dos dez anos preservado. Execução do autor no Colab e export conferidos; nenhum novo notebook necessário nesta conferência. Não repetir H/I/F/G/E ou os geradores. Limites de mensuração e calibração são explícitos. Branch+PR, sem merge automático.


## Colab H/I do autor conferido — 24/10/2026

[Cópia executada e salva](https://colab.research.google.com/drive/1pHcTi0deFoiIiEvmFK4ZtYr5MM9p_i9l); [export correspondente](https://drive.google.com/file/d/1L5w3uJvjTU4XiQir1BGMF3XNCWLS-_Ru/view), 21.813.582 bytes, SHA256 `ff67a56f9b9cc8b91f11bcbcad311d6253fcfe95aef3f9e02303bad677b41e0e`. As dez fontes de células coincidem com a entrega imutável; seis códigos em sequência, zero exceções, 149 fontes autenticadas. O ZIP tem 207 membros: 206 arquivos cobertos pelo manifesto e o próprio manifesto. H e I foram reestimados no Colab; os 6.000 geradores anteriores não foram repetidos. Nenhuma nova cotação foi consultada.

Conferência externa: **722.947 valores concordantes** (123.067 de tabelas/bancos H e 599.880 dos bancos I), diferença máxima `8,881784197e−15`, tolerâncias absoluta `1e−10` e relativa `1e−9`; preservadas 612 posições de limiar de valores-p. Os três PNGs embutidos coincidem com os exports e os três PDFs renderizados coincidem com os do artigo em 144 dpi. Não se alega identidade binária geral. A tabela LaTeX de defasagens é formatação exclusiva do artigo; seu CSV subjacente foi comparado numericamente.

Oráculos independentes confiáveis reexecutados sobre cópias das saídas autenticadas: H confere 480 regressões por período, 36 estatísticas de sorteio, 84 linhas CDF, cinco covariâncias densas e 1.920 componentes econômicos; I confere 960 pontos/status, 120 linhas de IC/p, 360 estatísticas explícitas, 599.880 valores de bancos e 1.076 ajustes válidos separados por regime com defasagens. As sete lacunas estão preservadas. A checagem de tamanho/cobertura das novas associações e a validação econômica dos eventos continuam pendentes.

Recibos: `data/lab03i/validacao_colab_20261024.json`, `manifesto_colab_20261024.json` e `oraculos_colab_20261024.json`. Auditor reproduzível: `scripts/verify_lab03i_colab.py`. O notebook executado, ZIP, matrizes diárias derivadas e bancos I permanecem no Drive, com organização/compartilhamento preservados; somente recibos e hashes são adicionados ao Git.

**Não repetir H/I/F/G/E ou transferências. Nenhum notebook novo nesta conferência.** Os resultados, universos fixos 80/117, dez setores, famílias e interpretações permanecem. Auditoria econômica global 0/197 não significa 197 erros; eventos/cadeias de ISIN, seleção/attrition, vintages e calibração específica continuam limitações. KRR permanece proposta não implementada/avaliada. Próximo: revisão científica humana e fechamento editorial para entrega de 27/10/2026, extensão não confirmada.


**Além do Beta Tradicional: Assimetria, Liquidez e Seleção em Ações Brasileiras**  
Robson Dias Ferreira — CMP609, PPGC/UFRGS.

Esta é uma cópia selecionada do material de pesquisa já versionado em `robsondf/alem-do-beta`, destinada à avaliação do manuscrito. A seleção inicial foi seguida pelas revisões identificadas na proveniência; o lote F acrescenta análises pós-parecer, preservando os resultados e protocolos anteriores. Não contém a matriz privada de retornos ou downloads novos de cotações. O repositório de origem e os arquivos do Google Drive foram preservados.

## H/I — adendo reproduzido e análise de liquidez (24/10/2026)

[Resultados, métodos, limites e instruções](docs/lab03i_selecao_liquidez.md). Reprodução própria dos onze caches oficiais B3 (476,5 MB), 48 resultados externos e 83 marcações; nenhuma nova consulta B3/Yahoo. A variante interpretada preserva as sete lacunas documentadas, incluindo os cinco dias de direitos. Nos elegíveis da seleção fixa de 2015, média inicial −0,0857 (64) e mudança +0,0640 (46; Holm4=0,2576); não é uma estimativa causal de viés de seleção.

Associação pós-parecer na união elegível: liquidez inicial × assimetria +0,4928 (100) e × mudança −0,2876 (82), Holm8/21=0,0168/0,0344. Reamostragem síncrona preserva dependência; há deslocamento bootstrap e falta calibração específica. Sensibilidades com 1/5/10 defasagens são descritivas, com todos os casos/status preservados. As amostras principais 80/117, dez setores, ausências e famílias anteriores permanecem intactas.

**[Abrir no Colab — único lote H/I](https://colab.research.google.com/github/robsondf/alem-do-beta-gemini/blob/fd51b25af552cb3dd3715c473c7b3156dd352b79/notebooks/Lab03I_selecao_liquidez.ipynb)** — CPU. Executar somente `notebooks/Lab03I_selecao_liquidez.ipynb`, que inclui H e I; não executar H separadamente nem repetir F/G/E ou os 6.000 geradores. Reutiliza X e `Além do Beta/cache_b3`. Execução do autor no Colab conferida; não repetir H/I. Notebook e ZIP permanecem no Drive.

**Artigo principal: 15 páginas, 29 referências, quatro figuras e seis tabelas. Suplemento: 21 páginas, 29 referências, nove figuras e 12 tabelas; 43 referências distintas no conjunto.** Principal Overleaf: `paper/main.tex` (`main.tex` se o conteúdo de `paper/` estiver na raiz). Mantidos os dez setores e gráficos de todo 2016–2025. A suíte tem 108 aprovações, dois skips históricos, zero falhas; verificadores independentes aprovados. Auditoria econômica global, eventos/sucessões e calibração dos novos testes permanecem pendentes; KRR não implementado/avaliado.

Integração local do único notebook H/I concluída: dez células/seis códigos, 149 fontes, 207 membros do export autenticados, 612 decisões preservadas. Execução do autor no Colab conferida, em recibo separado da integração local.

## Colab G do autor conferido — 24/10/2026

[Cópia executada e salva](https://colab.research.google.com/drive/1wMxL0eVrRmteeY_igYPG9KOiP18VwYLQ);[export correspondente](https://drive.google.com/file/d/1jaKyp2CapivwnvHRoFGBtxneHr6N7Kd1/view),18.065.044 bytes/SHA256 `a8f391a7bf4edf67c109b303c9abcbd9cae8274e7a0d6b86430f407816df9158`. Dez fontes de células idênticas,seis códigos1–6,zero exceções;70 fontes e88 membros autenticados. A execução completa de6.000 réplicas está registrada como `Lab03G all`/`Colab`,sem novos downloads de mercado.

Conferência externa:seis tabelas e66 vetores bootstrap,**1.595.778 valores concordantes**,máximo6,786238238e−15 sob tolerâncias1e−10 absoluta/1e−9 relativa. Preservadas84.066 posições ajustadas e84.066 brutas de limiar. Três CSVs e três tabelas LaTeX são idênticos em bytes; não se alega identidade binária geral. Dois PNGs embutidos iguais aos exports,pixels iguais à preparação local e PDFs com render igual ao artigo em144dpi.

## Revisão G — terceiro parecer

**[Abrir o único notebook novo no Colab](https://colab.research.google.com/github/robsondf/alem-do-beta-gemini/blob/f8bbed220998f002f390c31df0566b0cb942fce8/notebooks/Lab03G_mudanca_calibracao.ipynb)** — execução do autor já conferida; não repetir.

[Análises, matriz de resposta e reprodução](docs/lab03g_parecer_v3.md): mudança agregada entre quinquênios, inferência defasada/semanal e calibração de seis mecanismos. São6.000 réplicas,84.000 linhas e66 alvos/blocos observados, com verificador independente. **A simulação expõe falhas:** cobertura dos ICs básicos51,8–95,8%; erro familiar temporal5,6% no estresse AR0,6. Não se declara validade nominal ou robustez uniforme.

**Único notebook novo:** [Lab03G_mudanca_calibracao.ipynb](notebooks/Lab03G_mudanca_calibracao.ipynb). [Cópia do autor executada e conferida](https://colab.research.google.com/drive/1wMxL0eVrRmteeY_igYPG9KOiP18VwYLQ). Não repetir G/F/E/transferências; nenhum notebook novo nesta conferência. Códigos/dados/recibos anteriores preservados.

## Colab F conferido

[Notebook executado e salvo pelo autor](https://colab.research.google.com/drive/11biQglsj9zdEMXcEH71sijGvSuEAEQJH):10 fontes de células idênticas,seis códigos,zero exceções;ZIP de3.783.941bytes/31 membros autenticados;309.848 valores concordantes,máximo1,46e−14;decisões e gráficos preservados. [Recibo da conferência](data/lab03f/validacao_colab_20261024.json). Não repetir F/anteriores. Notebook e export permanecem no Drive; nenhum resultado científico foi modificado nesta conferência.

## Comece pelo artigo

- [PDF principal](paper/main.pdf): edição H/I: 15 páginas, 29 referências citadas, quatro figuras e seis tabelas. [Suplemento independente](paper/suplemento.pdf):21 páginas, 29 referências; 43 referências distintas no conjunto.
- [Fonte principal LaTeX](paper/main.tex) e [corpo do artigo](paper/artigo_revisado.tex).
- [Hipóteses e estimandos](docs/hipoteses_e_estimandos.md).
- [Escopo da seleção e proveniência](docs/REPOSITORY_SCOPE.md).
- [Execução e verificações](docs/REPRODUCTION.md).
- [Lote F executado: métodos, resultados, limites e Colab](docs/lab03f_pos_parecer.md).
- [Resposta aos dois pareceres](docs/resposta_pareceres_20261024.md) e [proposta de representação de conhecimento e raciocínio](docs/protocolo_representacao_raciocinio.md). A proposta de IA ainda não foi implementada ou avaliada.

Para uma avaliação independente, leia primeiro o PDF. Os recibos e testes permitem examinar a implementação e sua proveniência; não substituem a avaliação do mérito científico.

## Conteúdo

| Diretório | Conteúdo |
|---|---|
| `paper/` | Manuscrito, suplemento, bibliografia e todas as figuras/tabelas necessárias à compilação |
| `src/` | Módulos da estimação, análises temporal/setorial/de risco, inferência, previsão e sensibilidades finais |
| `scripts/` | Execução, gráficos, verificadores e ferramentas congeladas necessárias aos protocolos preservados |
| `tests/` | Testes originais dos módulos retidos |
| `data/` | Protocolos, hashes, recibos e evidência documental já presente no GitHub |
| `results/tables/` | Resultados Colab anteriores e revisões F/G com identificação separada da execução local e das conferências Colab |
| `notebooks/` | Sete notebooks, incluindo G,F e os cinco existentes necessários à leitura das etapas finais e à preservação do runtime E |
| `provenance/` | Relação completa dos arquivos selecionados e omitidos, com identificação do commit de origem |

As amostras são fixas: 80 ativos em 2016–2025 e 117 em 2021–2025, em dez setores; os mesmos 80 também são comparados em 2021–2025. A unidade é o ativo/classe/ISIN. As regressões utilizam retornos, com pares válidos e ausências preservadas.

## Limites do material

Esta cópia não é uma distribuição autossuficiente dos dados financeiros. Caches e exports integrais permanecem no Drive, com os hashes documentados nos protocolos. Sem essas entradas, podem-se ler os resultados e executar os testes que independem delas, mas não repetir toda a análise empírica.

Seleção retrospectiva, sobrevivência, identificação econômica incompleta e limitações inferenciais permanecem descritas no artigo. A reprodução numérica não equivale à homologação econômica integral. O estudo não estabelece assimetria generalizada, persistência futura ou superioridade preditiva.

## Origem e direitos

Origem inicial: [commit c21b086b976ec11549fb4feb211099e0d78c61cc](https://github.com/robsondf/alem-do-beta/tree/c21b086b976ec11549fb4feb211099e0d78c61cc). A revisão pós-parecer corresponde ao commit `f06060c6e7db7de4f966f152b362c88283b44469` do PR #86, já incorporado. O registro de proveniência mantém os hashes iniciais e identifica os arquivos revisados ou acrescentados. Código de estimação, protocolos e resultados congelados foram preservados; F acrescenta arquivos próprios, sem sobrescrever as etapas anteriores. O acesso à origem privada não é requisito para ler os arquivos selecionados aqui.

O recibo inicial é `provenance/verification.json`; a conferência desta revisão está em `provenance/verification_review_20261024.json`; a conferência F está em `provenance/verification_F_20261024.json`. Os resultados antigos e a versão de 20 páginas permanecem identificáveis no commit público `774f11fccbcdc9ff8086cc4d7c64cc4fb64d494c`.

Consulte [direitos e estado editorial](docs/RELEASE_STATUS.md). Não foi atribuída uma nova licença ao código, ao manuscrito ou a materiais de terceiros nesta cópia. O nome do repositório indica seu uso para avaliação por outro agente, não autoria ou validação por esse agente.
