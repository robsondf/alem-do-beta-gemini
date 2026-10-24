# Lab03H — quarto parecer e adendo sobre seleção/liquidez

**Checkpoint H histórico.** O pacote de 2015 foi recebido posteriormente e reproduzido no [lote I](lab03i_selecao_liquidez.md), que registra diferenças, sete lacunas, associação conjunta e defasagens. Para a execução atual, usar somente o notebook I que inclui H. As pendências de recebimento descritas abaixo registram o estado anterior, já superado.


Data: 24/10/2026. Bases: original `5cbb4bea8c327f42936673212444f52405905b8c`; pública `67858e47e1f5961c345684917ccd95f83cd51163`. Nova branch/PR nos dois repositórios, sem merge automático.

## O que foi efetivamente executado

O plano `data/lab03h/plano_v1.json` foi escrito antes dos novos resultados de exclusão, com F/G e o quarto parecer conhecidos. Não é pré-registro independente. SHA256 `c792d6b12948418ee54f904fa9fad75ea40156fc6236df881467f161638e6511`. O adendo de oito páginas chegou depois dos resultados H; seu recebimento tem registro separado e não altera retrospectivamente o plano.

Reutilizados o X autenticado, 78 fontes congeladas e os bancos F/G. Nenhum download de cotações, novo gerador externo Monte Carlo, preenchimento ou seleção anual. Preservados ativo/classe/ISIN, amostras 80/117, dez setores, ausências e famílias anteriores. As exclusões são aplicadas apenas à metade 2016–2020; os mesmos 80 ativos em 2021–2025 permanecem intactos.

| Primeira metade | Resumo pareado | Estimativa | p bruto, L21 | p ajustado, L21 | Família |
|---|---|---:|---:|---:|---|
| Integral | Média | +0,166680 | 0,0126 | 0,0252 | G4 original |
| Integral | Mediana | +0,135591 | 0,0508 | 0,0508 | G4 original |
| Sem março/2020 | Média | +0,125359 | 0,0602 | 0,1794 | H4 nova |
| Sem março/2020 | Mediana | +0,102872 | 0,1840 | 0,1840 | H4 nova |
| Sem 2020-S1 | Média | +0,145623 | 0,0170 | 0,0680 | H4 nova |
| Sem 2020-S1 | Mediana | +0,144703 | 0,0598 | 0,1794 | H4 nova |

H4 contém média/mediana da mudança × duas exclusões. G4 continha média/mediana inicial e da mudança; as famílias têm composições distintas. Mostrar p bruto evita atribuir toda diferença à janela. Nenhum H4 rejeita na escolha principal de 21 sessões; a média sem 2020-S1 rejeita em 63 sessões (0,0448), mas não em 5/21. Não escolher o bloco pela rejeição. Os sinais positivos não demonstram mudança causal, e as não rejeições não provam equivalência ou ausência de assimetria. Os ICs básicos nominais não são duais dos valores-p centrados; a calibração G não valida automaticamente os novos alvos mascarados.

## Calibração: precisão da interpretação

A média quadrática global de h é 1; nas metades, 1,21705/0,78452. O fator de quebra também tem média quadrática global 1; o produto tem 1,02955, cerca de 1,47% em RMS. Não foi identificado o erro de normalização simples sugerido como possibilidade. A concentração temporal da variância, os pesos do contraste e a correlação serial ajudam a explicar a dispersão; seis mecanismos foram preservados, sem selecionar os favoráveis pela proximidade ao EP observado. Esse EP não é a verdadeira dispersão amostral conhecida.

Na média da década, normal iid/GARCH têm cobertura 94,8%/95,1%; outros mecanismos têm subcobertura. A faixa 51,8–95,8% se refere ao conjunto dos 84 casos alvo/mecanismo, não a todos os alvos em todos os geradores. A validade dos ICs e do teste são propriedades distintas.

O diagnóstico exploratório aplica `(1+k)/(1000+1)` a **todas** as marginais F10/G4 antes de reordenar e aplicar Holm. Não se usa um multiplicador fixo extraído da ordenação original. Faixas CDF/Holm: média da década 0,01998–0,08092; média inicial 0,003996–0,035964; mudança média 0,029970–0,061938; mudança mediana 0,052947–0,119880. Logo, não se confirma a afirmação de robustez ajustada da década em todos os mecanismos. Exportam-se contagem, MCSE e Wilson marginal. O mesmo banco, nuisances estimadas e nulidade global individual não constituem validação independente ou controle forte para todas as nulas agregadas. Esses diagnósticos não substituem a inferência primária.

## Outras respostas concretas

- Microestrutura: tabela principal mostra p brutos e Holm18, com a composição da família preservada. Export completo tem 54 linhas. Semanal tem 518–520 pares na década e 258–259 nos recortes recentes; menor precisão não é evidência de equivalência.
- Escala econômica: 1.920 componentes por ativo, convertendo choques simples em `log1p`. Exportam-se a diferença de inclinações, a de interceptos e sua soma. Comparar os dois regimes no mesmo choque extrapola uma projeção. Não é retorno de carteira, perda esperada, prêmio de risco ou causalidade. Mantida a decisão de não criar pesos de empresas.
- Texto principal reduzido; métodos individuais, WEGE3, influência, figuras setoriais/de risco, calibrações completas e previsão exploratória preservados no suplemento independente. O principal mantém os dez setores e uma visão anual de todo o período 2016–2025. Faixas entre ativos são IQR descritivo, não IC.
- Resumos identificam os valores ajustados por Holm e a fragilidade das exclusões. Resultados de IA/KRR não são alegados.

## Verificação e execução

Quatro testes H verificam OLS conjunto com lacunas, variância AR contra Toeplitz, reordenação após CDF/empates e conversão econômica com intercepto. O verificador independente não importa H/G/F: 480 OLS por período, 36 estatísticas bootstrap por linhas explícitas, 12 linhas completas de IC/p/Holm, 84 diagnósticos CDF, cinco covariâncias densas e 1.920 componentes econômicas. Diferenças máximas OLS/bootstrap: 3,11e−15/2,29e−15. O baseline G é reproduzido integralmente pelo cálculo H. Isso verifica consistência computacional, sem homologar a economia dos dados nem a cobertura dos novos alvos.

```bash
python scripts/run_lab03h.py --x-archive /caminho/X.zip --output /caminho/NOVA_SAIDA_H
python scripts/verify_lab03h.py --x-archive /caminho/X.zip --output /caminho/NOVA_SAIDA_H
python scripts/plot_lab03h.py --output /caminho/NOVA_SAIDA_H
```

O novo notebook H reproduz apenas H e diagnósticos dos bancos existentes; não repete os 6.000 geradores G. Reutiliza `alem_do_beta/lab03f_cache`. Executar em CPU, salvar notebook e ZIP no Drive. Execução local e execução do autor no Colab são registradas separadamente; a segunda permanece pendente nesta preparação.

## Adendo recebido: seleção em 2015 e liquidez

Documento de oito páginas, SHA256 `dfbf818c4992382d43b23ec41f5e1c41430c663da1a876e4c5616855f5a025f1`. Páginas 6–8 acrescentam um experimento externo. O PDF relata, em universo escolhido em 2015, média inicial −0,086 (64 elegíveis), mudança média +0,064 (46 pares), e correlação de Spearman 0,49 entre assimetria e liquidez inicial. São **resultados do avaliador, ainda não reproduzidos ou autenticados pelo projeto**. Não foram incorporados às tabelas de resultados do artigo. O pacote mencionado `teste_universo_2015.zip` não acompanha o PDF e não foi localizado no workspace ou pela busca disponível no Drive; a ausência de resultado da busca não prova ausência no Drive.

O relato é relevante, mas a passagem de −0,177 para −0,086 não estima isoladamente viés de seleção: mudam fonte/ajustes, composição e elegibilidade. Para theta são 46 contra 77 pares na reconstrução COTAHIST; a redução de potência e a mudança de alvo precisam ser mostradas. A fonte reproduzir resultados próximos no universo original não prova equivalência econômica dos retornos ou de dividendos. Regra de anulação baseada no tamanho do retorno é uma máscara dependente dos dados, não comprovação de evento corporativo. Correlação e tercis pós-observação são exploratórios. Não se chama essa verificação futura de confirmação independente ou pré-registro, pois os resultados já foram vistos.

### Próximo lote, dependente do pacote externo

1. Receber ZIP, inventariar/hash e ler scripts sem executar código não revisado. Conferir 11 hashes COTAHIST, calendário, 80 ISINs escolhidos, ranking/volume de 2015, elegibilidade, sementes, famílias e eventos. Reutilizar caches originais; não baixar toda a série outra vez.
2. Reproduzir exatamente o experimento do avaliador antes de corrigi-lo. Separar diferença de implementação, fonte, ajuste econômico e composição. Mostrar todos os N e motivos de saída por ativo/período.
3. Comparar fontes no mesmo conjunto elegível e comparar universos sob mesma fonte, tratamento de eventos e pisos. Mostrar conjunto fixo completo, interseção elegível e perdas; não eliminar sobrevivência apenas com o rótulo “seleção em 2015”. Manter 80/117 como baseline e identificar o novo universo apenas como sensibilidade fixa, sem nova seleção anual.
4. Auditar os 83 retornos anulados, sucessões de ISIN e calendário/ausência de negócio. Não encadear identidades sem evidência documental nem distribuir pontes como retornos diários. Não endossar genericamente a afirmação de que yfinance sempre repete preços sem negócio sem verificar casos e campos.
5. Congelar depois da auditoria um teste pós-parecer da relação liquidez–assimetria e liquidez–mudança. Reamostrar sessões de forma síncrona, recalcular deltas e associações em cada sorteio e preservar estratos/metades; não usar p de correlação que trate ativos dependentes como independentes. Informar condicionamento aos volumes de 2015, composição, incerteza e multiplicidade. Controles setoriais/porte e tercis adicionais seriam exploratórios; não selecionar controles ou defasagens pela significância.
6. Avaliar negociação infrequente com mais defasagens e, se necessário, intervalos trade-to-trade. Cada retorno acumulado deve ser confrontado ao mercado no **mesmo intervalo** e identificado como outro estimando; não pode entrar na matriz diária ou ser dividido em retornos não identificáveis. Documentar dependência de intervalos sobrepostos, pisos e viabilidade antes da inferência.
7. Só após isso reescrever a contribuição empírica sobre liquidez/seleção. Até lá, é explicação concorrente e limitação material, não mecanismo demonstrado. Regras do PPGC e aderência à dissertação dependem da situação real do autor e de confirmação institucional; o parecer não determina inelegibilidade. KRR continua proposta não implementada/avaliada.

**Pendente de entrada:** `teste_universo_2015.zip` ou link de acesso. A reprodução H não resolve esta pendência nem a auditoria econômica global (0/197 homologados). A atualização editorial não é certificação de aceite/publicabilidade.
