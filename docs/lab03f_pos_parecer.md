# Lab03F — resposta empírica ao segundo parecer

## O que foi executado

Em 24/10/2026, após os PRs #86/#2 incorporados, o autor autorizou executar as pendências do segundo parecer Claude (3 páginas; SHA-256 `eb1671460c69f636c109d721bfdbc3b769c4e9613395d2c6e4fcef4e412be638`). O protocolo `data/lab03f/plano_pos_parecer_v1.json` foi escrito antes dos novos ajustes, após conhecimento de resultados anteriores e do parecer. Seu SHA-256 é `f94cac62a6aa03249fb102ae7f74d5f45f3c28ca4968e503899f11b07cff6d1f`; não é pré-registro independente.

Foram executados e conferidos localmente **1.939 ajustes**, sete especificações nos 277 recortes, e **4.999 reamostragens por bloco (5/21/63)** para dez alvos agregados. Há tabelas completas, sorteios bootstrap, escores HAC por defasagem, incerteza do salto de intercepto e dois gráficos novos. A execução pelo autor no Colab continua distinta da preparação local.

Reutilizou-se somente o ZIP X do Drive, 18.973.143 bytes, SHA-256 `297da2afde534082c398324f308df7af134c9692e7d61d6e0b2b820341ea5214`, com todos os 26 membros autenticados. Nenhuma cotação foi coletada novamente. As matrizes não foram alteradas ou copiadas para o repositório público.

## Definições e decisões

- Unidade: ativo/classe/ISIN. Amostras fixas 80/117, dez setores; nenhum peso empresarial ou carteira. A média dos contrastes é um resumo entre os ativos, não agregação das classes de uma empresa.
- Retornos logarítmicos observados e Ibovespa; sete ausências na década e sete no recente preservadas, incluindo os cinco direitos não identificáveis ABCB4/UGPA3. Light continua reconciliada.
- Referência individual original: família197, HAC5 e decisões históricas preservadas; família temporal474 e complemento E também preservados.
- Sete especificações: diário integral; sem março/2020; sem2020-S1; contínuo (g=0); contemporâneo+defasagem1; avanço1+contemporâneo+defasagem1; semanal. Todas atenderam 200 pares, 60 por regime, 95% de cobertura. Exportam-se contagens e erros HAC0/5/10/20.
- Crise: a exclusão muda a janela-alvo, não corrige um suposto erro. Os escores HAC mantêm a posição original de calendário.
- Assincronia: interações de todos os termos de mercado com o regime contemporâneo; contraste da soma das inclinações, com covariância conjunta. É adaptação descritiva de coeficientes agregados, não prova de correção não viesada. O avanço só participa da análise histórica, sem previsão.
- Semanal: somam-se logs de todas as sessões da semana; uma ausência invalida a semana do ativo. Semanas inicial/final descartadas, sinal do mercado semanal. Nenhum retorno diário é reconstruído.

O bootstrap move blocos não circulares de linhas conjuntas de ativos/mercado/NaNs, reestima inclinações e não reamostra ativos. Sorteia separadamente trechos contíguos antes/depois de2021; as exclusões de crise não permitem blocos atravessando as sessões removidas. Os80 comuns reutilizam exatamente os sorteios dos117 recentes. O alvo é condicional à mistura temporal de cada janela, exigindo dependência fraca/estacionariedade local nos trechos.

Dez testes: média/mediana dos três recortes integrais e da década sob duas exclusões. Principal: bloco21 e Holm10; sensibilidades5/63 e Holm30 sobre todos os30 testes/blocos, sem escolha por significância. ICs básicos95% são marginais e aproximados. O valor-p centrado com correção +1 não é randomização exata sob nulidade. Exportam-se caudas, erro Monte Carlo e Wilson da frequência simulada; nenhum desses controles demonstra cobertura finita. Mediana finita perto de empates centrais pode ser não regular.

## Resultados efetivos

| Alvo, bloco21 | Estimativa | IC marginal95% | Holm10 | Holm30 |
|---|---:|---|---:|---:|
| Média80, década | −0,130668 | [−0,224945; −0,083547] | 0,0234 | 0,0624 |
| Mediana80, década | −0,135720 | [−0,247058; −0,088326] | 0,0592 | 0,1480 |
| Média80, comum | −0,010080 | [−0,098349; 0,069210] | 1 | 1 |
| Média117, recente | −0,011379 | [−0,121590; 0,095498] | 1 | 1 |
| Média80, sem março/2020 | −0,088838 | [−0,166049; −0,034218] | 0,0826 | 0,2124 |
| Média80, sem2020-S1 | −0,097682 | [−0,162004; −0,044987] | 0,0160 | 0,0416 |

As duas medianas recentes também têm valores ajustados1. O lote acrescenta evidência de média negativa na década na família secundária principal, com dependência da janela/família; não comprova assimetria generalizada, equivalência recente ou persistência futura.

Os casos VULC3/BBDC4 não mantêm rejeição primária sob exclusão de março ou2020-S1, sob avanço/defasagem ou semanal. As contagens da década nas sete especificações são2/1/1/3/0/0/0; no recente, sempre0. Nas exclusões de2020, o nome rejeitado passa a SLCE3; isso não deve ser usado para selecionar a especificação. No contínuo, ALUP11 se soma aos dois originais.

Aplicando Holm aos197 ajustes de cada máscara já existente, VULC3 passa a0,025263/1 e BBDC4 a0,163571/0,051377 ao retirar1/5 pontos. Surgem SMTO3 no primeiro diagnóstico, HYPE3/LEVE3 no segundo. Essas máscaras dependem dos retornos observados: os valores-p não incorporam a seleção e **não são novas descobertas confirmatórias**. O envelope não foi recalibrado.

Os saltos g de VULC3/BBDC4 têm EP0,001956/0,001102. Suas não rejeições não validam g=0 universal: CSAN3/PETR3/RADL3 rejeitam nessa aproximação separada. Os escores permitem examinar HAC por defasagem, sem inferir sua autocorrelação a partir de contagens globais.

## Verificações

- 197 ajustes de referência reproduzidos antes do bootstrap.
- Seis testes com oráculos: sandwich em calendário com lacunas, soma dinâmica e covariância, refit por momentos, índices explícitos de blocos, propagação semanal de NaNs, proibição de blocos cruzando a crise.
- Verificador sem importar a implementação F: 1.939 regressões completas/sandwich; maior diferença1,98e−14. Reestimação por índices explícitos de150 estatísticas bootstrap; maior diferença2,56e−14. Todos os30 ICs/valores-p e ajustes conferidos.
- Integração do notebook:10 células/seis códigos, zero exceções,241.883 valores comparados com a preparação,15 fontes autenticadas por commit/SHA, export de3.783.932bytes autenticado. Ainda é execução local, não o Colab do autor.
- Os49 arquivos congelados E continuam íntegros. Aprovação numérica não certifica cobertura estatística ou homologação econômica.

## Execução Colab e local

Notebook: [abrir F no Colab](https://colab.research.google.com/github/robsondf/alem-do-beta-gemini/blob/c747c02c288b0bed45cda155e115624841e5e33b/notebooks/Lab03F_pos_parecer.ipynb). Arquivo: `notebooks/Lab03F_pos_parecer.ipynb`. Execute/salve **somente F**, sem repetir E/transferência/laboratórios anteriores. Ele baixa código público fixado por commit/SHA, reutiliza o ZIP X existente no Drive por nome+hash, roda os testes, todos os ajustes/bootstrap, verificador, gráficos e exporta os resultados ao Drive. Nenhuma cotação nova é solicitada. O tempo varia por CPU/autenticação; a preparação local do cálculo principal levou cerca de17s, sem incluir transferência/verificações/figuras. Há mensagens por especificação e bloco.

Execução local com o arquivo externo autenticado:

```bash
python scripts/run_lab03f.py --x-archive /caminho/lab02x.zip --output /caminho/novo_resultado_F
python scripts/verify_lab03f.py --x-archive /caminho/lab02x.zip --output /caminho/novo_resultado_F
python scripts/plot_lab03f.py --output /caminho/novo_resultado_F
```

Use `paper/main.tex` como principal no Overleaf. O PDF e suas fontes acompanham esta revisão; a referência enganosa ao snapshot público antigo foi retirada. A previsão do retorno seguinte foi deslocada para apêndice, preservando resultados e deixando explícito que não responde à exposição futura. Oito referências foram acrescentadas com escopo de consulta registrado em `data/lab03f/fontes_literatura.json`.

## Matriz após este lote

| Pendência do segundo parecer | Estado |
|---|---|
| Ausência de inferência agregada | Executada para média/mediana do universo fixo; aproximações e sensibilidade da família explicitadas. |
| Fragilidade das rejeições e crise2020 | Quantificada para todos os casos; resumo/discussão/conclusão corrigidos. Não se promete robustez que os resultados não mostram. |
| Assincronia | Dois modelos dinâmicos e semanal executados; não identificação causal/correção universal. |
| Continuidade e salto | Restrição comparada; g, EP e covariância exportados. |
| Extensão preditiva fora do foco | Detalhes preservados em apêndice; exposição futura continua não testada. |
| Snapshot desatualizado | PDF/fontes/tabelas sincronizados na revisão dos dois repositórios; manifesto identifica versões sem apontar o commit inicial como atual. |
| Literatura omitida | Oito referências primárias contextualizadas; não se alegam leitura integral ou reprodução de testes distintos. |
| Auditoria econômica, sobrevivência e vintages | Permanecem limitações materiais; este lote não as elimina. |
| Contribuição própria em representação/raciocínio | Continua proposta separada, não implementada/avaliada; nenhum resultado de IA atribuído a F. |

Arquivos completos em `results/tables/lab03f_pos_parecer_20261024/`; recibo em `data/lab03f/validacao_local.json`. Não se renomeiam recibos locais como Colab nem se anuncia homologação global concluída.
