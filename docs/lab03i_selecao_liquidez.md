# Lab03I — reprodução do adendo, seleção e liquidez

Data: 24/10/2026. Este lote sucede H na mesma revisão em branch/PR nos dois repositórios, sem merge automático. O pacote externo foi recebido depois do primeiro preparo H; a pendência de recebimento registrada naquele checkpoint está resolvida.

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

Os universos compartilham 42 ISINs; 41 são elegíveis ao contraste pareado. Dos 38 exclusivos de 2015, só cinco são elegíveis nas duas metades; dos 38 exclusivos originais, 36. Portanto, o painel final de 2015 não é automaticamente livre de sobrevivência/perdas seletivas. Diferença de magnitude não estima isoladamente viés de seleção: mudam composição, elegibilidade, fonte e ajustes. Não rejeitar theta em 46 pares não prova equivalência ou inexistência de mudança.

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

## Execução do autor: um único lote H/I

Executar somente `notebooks/Lab03I_selecao_liquidez.ipynb`, em CPU. Inclui H e I; não executar H separadamente nem repetir F/G/E ou os 6.000 geradores. O lançador autentica um commit imutável e arquivos por hash, reutiliza X e `Além do Beta/cache_b3`, processa todos os universos/blocos e compara as saídas. Se um cache faltar, busca o arquivo existente pelo ID do Drive, sem consultar novas cotações. A execução local não é execução do autor no Colab; esta permanece pendente nesta preparação.

Salvar cópia executada e ZIP no Drive. O ZIP contém matrizes derivadas de retorno para auditoria, sem os onze ZIPs brutos. Essas matrizes não devem ser confundidas com os resumos públicos. Conferir o export antes de registrar homologação computacional da execução do autor.

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
