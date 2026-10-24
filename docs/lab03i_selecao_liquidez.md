# Lab03I — reprodução do adendo, seleção e liquidez

**[Lançador H/I imutável preservado para reprodução no Colab](https://colab.research.google.com/github/robsondf/alem-do-beta-gemini/blob/fd51b25af552cb3dd3715c473c7b3156dd352b79/notebooks/Lab03I_selecao_liquidez.ipynb)** — CPU; inclui H e I. Runtime imutável `4689c35c49a303e84f35b66c55320190fb630937`; notebook publicado em `fd51b25af552cb3dd3715c473c7b3156dd352b79`. Execução do autor conferida; não repetir. Cópia e ZIP permanecem no Drive.


Data: 24/10/2026. Este lote sucede H na mesma revisão em branch/PR nos dois repositórios, sem merge automático. O pacote externo foi recebido depois do primeiro preparo H; a pendência de recebimento registrada naquele checkpoint está resolvida.

## Colab H/I do autor conferido — 24/10/2026

[Cópia executada e salva](https://colab.research.google.com/drive/1pHcTi0deFoiIiEvmFK4ZtYr5MM9p_i9l); [export correspondente](https://drive.google.com/file/d/1L5w3uJvjTU4XiQir1BGMF3XNCWLS-_Ru/view), 21.813.582 bytes, SHA256 `ff67a56f9b9cc8b91f11bcbcad311d6253fcfe95aef3f9e02303bad677b41e0e`. As dez fontes de células coincidem com a entrega imutável; seis códigos em sequência, zero exceções, 149 fontes autenticadas. O ZIP tem 207 membros: 206 arquivos cobertos pelo manifesto e o próprio manifesto. H e I foram reestimados no Colab; os 6.000 geradores anteriores não foram repetidos. Nenhuma nova cotação foi consultada.

Conferência externa: **722.947 valores concordantes** (123.067 de tabelas/bancos H e 599.880 dos bancos I), diferença máxima `8,881784197e−15`, tolerâncias absoluta `1e−10` e relativa `1e−9`; preservadas 612 posições de limiar de valores-p. Os três PNGs embutidos coincidem com os exports e os três PDFs renderizados coincidem com os do artigo em 144 dpi. Não se alega identidade binária geral. A tabela LaTeX de defasagens é formatação exclusiva do artigo; seu CSV subjacente foi comparado numericamente.

Oráculos independentes confiáveis reexecutados sobre cópias das saídas autenticadas: H confere 480 regressões por período, 36 estatísticas de sorteio, 84 linhas CDF, cinco covariâncias densas e 1.920 componentes econômicos; I confere 960 pontos/status, 120 linhas de IC/p, 360 estatísticas explícitas, 599.880 valores de bancos e 1.076 ajustes válidos separados por regime com defasagens. As sete lacunas estão preservadas. A checagem de tamanho/cobertura das novas associações e a validação econômica dos eventos continuam pendentes.

Recibos: `data/lab03i/validacao_colab_20261024.json`, `manifesto_colab_20261024.json` e `oraculos_colab_20261024.json`. Auditor reproduzível: `scripts/verify_lab03i_colab.py`. O notebook executado, ZIP, matrizes diárias derivadas e bancos I permanecem no Drive, com organização/compartilhamento preservados; somente recibos e hashes são adicionados ao Git.

**Não repetir H/I/F/G/E ou transferências. Nenhum notebook novo nesta conferência.** Os resultados, universos fixos 80/117, dez setores, famílias e interpretações permanecem. Auditoria econômica global 0/197 não significa 197 erros; eventos/cadeias de ISIN, seleção/attrition, vintages e calibração específica continuam limitações. KRR permanece proposta não implementada/avaliada. Próximo: revisão científica humana e fechamento editorial para entrega de 27/10/2026, extensão não confirmada.

## Evidência efetivamente obtida

`teste_universo_2015.zip`: 38.552 bytes, SHA256 `8781dc2f8c7300c2bbdb4a620f73d3fa360f8724e0b39dc303aae1a01392e7d8`. Contém três scripts e sete arquivos de dados/resultados. Scripts lidos; nenhum código ou pickle do avaliador foi executado. Código próprio reconstruiu o experimento a partir dos onze ZIPs oficiais já existentes no Drive, autenticados contra os metadados anteriores: 476.502.933 bytes. Não houve nova consulta de cotações à B3 ou ao Yahoo. Preços foram usados apenas na reconstrução; as avaliações usam retornos/projeções de retornos. As entradas públicas de mercado estão em log-retornos.

A reprodução literal concorda com todas as 48 estimativas, N, ICs e valores-p do pacote (máximo numérico cerca de 1,1e−14; p/decisões iguais). As 83 marcações de eventos também coincidem, sem certificar a validade econômica de cada anulação. O bootstrap usa as sementes do avaliador, distintas das sementes F/G, e suas famílias Holm4 inicial/mudança e Holm2 década/recente. Não se apresenta a inferência externa como idêntica à família F10 original.

Foi identificada diferença material de mensuração: o experimento literal usa mudanças de cotação nos cinco dias de direitos ABCB4/UGPA3 e nos dois dias ANIM3 que mantemos ausentes. A reprodução literal permanece um diagnóstico. Uma segunda variante preserva as **sete células ausentes** da referência X autenticada; não altera X, não interpola ou distribui pontes. As duas variantes e os planos/adendos são preservados. A interpretação do artigo usa a variante com lacunas.

| Fonte COTAHIST com lacunas | Alvo médio | N | Estimativa | p bruto | p ajustado, L21 |
|---|---|---:|---:|---:|---:|
| 80 originais | 2016–2020 | 78 | −0,168506 | 0,0022 | 0,0088 (Holm4) |
| Seleção fixa de 2015 | 2016–2020 | 64 | −0,085653 | 0,0076 | 0,0304 (Holm4) |
| 80 originais | Mudança pareada | 77 | +0,148132 | 0,0196 | 0,0392 (Holm4) |
| Seleção fixa de 2015 | Mudança pareada | 46 | +0,064025 | 0,1288 | 0,2576 (Holm4) |
| 80 originais | Década | 78 | −0,127240 | 0,0010 | 0,0020 (Holm2) |
| Seleção fixa de 2015 | Década | 48 | −0,055876 | 0,0166 | 0,0332 (Holm2) |

Os universos compartilham 42 ISINs; 41 são elegíveis ao contraste pareado. Dos 38 exclusivos de 2015, só cinco são elegíveis nas duas metades; dos 38 exclusivos originais, 36. Portanto, o painel final de 2015 não é automaticamente livre de sobrevivência/perdas seletivas. Entre os dois universos da tabela, fonte e máscara são comuns; variam composição, elegibilidade e precisão. A comparação com a referência original acrescenta mudanças de fonte/ajustes. Essas diferenças pontuais não estimam isoladamente viés causal de seleção, nem foi realizado um teste direto entre universos. Não rejeitar theta em 46 pares não prova equivalência ou inexistência de mudança.

## Liquidez com dependência entre ativos preservada

Volume financeiro total de 2015 dividido por 246 sessões; postos fixados a partir dessa informação inicial. Em cada sorteio síncrono de sessões, os deltas de todos os ativos são reestimados antes das correlações. Não se usa o p de correlação que pressupõe ativos independentes. São quatro associações (dois alvos × duas coortes), duas variantes e três blocos. Holm8 reúne as duas variantes em cada bloco. Os protocolos são pós-parecer, com a correlação externa inicial conhecida, **não confirmação independente**.

| Variante com lacunas, L21 | N | Spearman | p bruto | Holm8 |
|---|---:|---:|---:|---:|
| Originais: liquidez × delta inicial | 78 | +0,530394 | 0,0006 | 0,0048 |
| Originais: liquidez × theta | 77 | −0,314186 | 0,0088 | 0,0344 |
| União: liquidez × delta inicial | 100 | +0,492793 | 0,0028 | 0,0168 |
| União: liquidez × theta | 82 | −0,287578 | 0,0124 | 0,0344 |

Sinais e rejeições aproximadas persistem nos blocos 5/63; todas as escolhas estão no export. A aproximação não recebeu calibração específica. O deslocamento bootstrap é apreciável: na união, média do banco menos ponto é −0,1054 para o nível e +0,0644 para theta. Exportam-se média, viés, EP e IC nominal. A reamostragem preserva dependência, mas não certifica cobertura ou tamanho nominal. Não se isola causalidade, melhora de liquidez, efeito de porte/setor ou uma fração explicada do resultado.

## Defasagens adicionais e auditoria da seleção

Sensibilidade descritiva com mercado corrente e 1/5/10 defasagens, regime contemporâneo e soma de inclinações. As defasagens são construídas no calendário original 2015–2025 antes de recortar períodos. Mantêm-se pisos 200/60/95% e exige-se posto completo, sem relaxamento. Exportam-se todas as 1.416 tentativas por ativo/período/K, incluindo insuficiências, e 36 resumos. Não se produzem novos valores-p ou se transfere a inferência do estimando contemporâneo.

Nos originais, a média inicial passa de −0,1685 (K0) para −0,1518/−0,2966/−0,2955 (K1/5/10). As correlações com liquidez inicial são 0,4818/0,5334/0,4417; com theta, −0,3244/−0,3522/−0,3057. O sinal se mantém, mas magnitudes e alvo mudam. Não se demonstra que as somas corrijam viés de negociação infrequente. Trade-to-trade não foi convertido em retorno diário.

O cache amplo de liquidez reproduz os 221 elegíveis informados; o filtro BDI02 do extrator recebido produz 211. Ambos recuperam exatamente os mesmos 80 eleitos, na ordem do volume por sessão. Há BDI não 02 no cache amplo (exemplo verificado MGEL4: 08/58 no mercado 010). O código da seleção não estava no pacote; não se certifica equivalência de toda a lista candidata. O campo `vol_med` usa 246 sessões, não dias ativos; CRUZ3 tem 226 dias, mas isso não muda o conjunto de 80 neste caso. Presenças futuras do arquivo externo não são usadas para selecionar.

## Verificações e material público

O oráculo independente não importa a produção. Confere 960 pontos/status por ativo/período, 120 linhas de IC/p, 360 estatísticas de sorteios e postos (máximo 6,44e−15), 120 vetores/599.880 valores, as sete ausências e a seleção inicial. Confere separadamente os regimes em 1.076 ajustes válidos com defasagens (máximo 1,66e−14), além dos status insuficientes. A suíte selecionada tem 110 testes: 108 aprovados, dois skips históricos, zero falhas. Os skips não são aprovações.

Os resultados públicos são resumos, pontos por ativo e diagnósticos; ZIPs brutos, matrizes diárias e bancos completos I permanecem fora do Git. Os hashes de cada membro recebido, dos caches e das fontes são preservados. A seleção pública anterior e as 49 fontes E permanecem inalteradas.

Integração local H/I concluída: dez células/seis códigos, 149 fontes imutáveis autenticadas, 123.067 valores de tabelas/H concordantes e 599.880 valores dos bancos I concordantes (máximo zero nesta repetição local), preservadas 612 posições de limiar. Três PNGs com pixels iguais à preparação do artigo. Export de 21.813.873 bytes/207 membros lido de volta e autenticado; SHA256 `2f61beb15aac8638cf92dae0eef58de8bc70cded3a6fe833519171f21f554f06`. Isso não é execução do autor no Colab. Recibos em `data/lab03i/validacao_notebook_local.json` e `manifesto_notebook_local.json`. O benchmark recebido em 2016–2025 coincide com X em 2.483 sessões: diferença máxima 9,98e−17 nos logs e nenhum desacordo de sinal; o segmento de 2015 tem a proveniência do pacote recebido, fora desse confronto.

## Lançador H/I preservado para reprodução

Para uma reprodução futura, o lançador é `notebooks/Lab03I_selecao_liquidez.ipynb`, em CPU; a execução atual já foi conferida e não deve ser repetida. Inclui H e I; não executar H separadamente nem repetir F/G/E ou os 6.000 geradores. O lançador autentica um commit imutável e arquivos por hash, reutiliza X e `Além do Beta/cache_b3`, processa todos os universos/blocos e compara as saídas. Se um cache faltar, busca o arquivo existente pelo ID do Drive, sem consultar novas cotações. O recibo local anterior permanece histórico; a execução efetiva do autor no Colab foi conferida separadamente, conforme o checkpoint acima.

Execução do autor conferida; não repetir. Cópia e ZIP permanecem no Drive. O ZIP contém matrizes derivadas de retorno para auditoria, sem os onze ZIPs brutos. Essas matrizes não devem ser confundidas com os resumos públicos. O export efetivo foi conferido por hash, conteúdo numérico, figuras e oráculos independentes; isso não certifica a homologação econômica.

Para execução local com entradas autenticadas:

```bash
python scripts/replicate_review_2015.py --b3-cache /caminho/cache_b3 --review-dir data/lab03i/review_reference --x-archive /caminho/X.zip --output /caminho/NOVA_SAIDA_I
python scripts/plot_review_2015.py --output /caminho/NOVA_SAIDA_I
python scripts/sensitivity_review_2015_lags.py --output /caminho/NOVA_SAIDA_I
python scripts/verify_review_2015.py --output /caminho/NOVA_SAIDA_I
```

`cache_b3` precisa conter os onze ZIPs e uma cópia de `data/lab03i/b3_cache_manifest.json` chamada `authenticated_manifest.json`. O notebook prepara isso sem alterar os caches originais. A pasta de saída deve ser nova.

## Pendências que a reprodução não elimina

Revisão econômica das 83 marcações e demais eventos; sucessões de ISIN documentadas; seleção/attrition e comparações condicionais de composição; calibração específica das novas correlações/universos/modelos e dos ICs; distinção entre fonte de cotação e retorno economicamente harmonizado. A auditoria global continua 0/197 homologados, sem significar 197 erros. KRR permanece proposta não implementada/avaliada; aderência à dissertação/destino editorial requer avaliação humana. Não se garante aceite ou se declara eliminada toda limitação.
