# Lab03J — Liquidez condicional, fontes e resposta aos pareceres

Checkpoint de 24/10/2026. Análise complementar exploratória, não pré-registrada. Os resultados anteriores e os pareceres eram conhecidos. O protocolo de oito subconjuntos de controles foi escrito e versionado em `ab3509ead421843b44cf2be49995ed3417604589` antes das saídas J; os adendos registram ajustes de recuperabilidade das fontes e o momento da sensibilidade de continuidade. Isso não é confirmação independente nem pré-registro externo.

## O que foi obtido

A unidade principal continua ativo/classe/ISIN, sem pesos empresariais. Os 80/117, dez setores, retornos logarítmicos e pisos 200/60/95% permanecem. As regressões J são uma sensibilidade COTAHIST com as sete lacunas documentadas preservadas, sem substituir a referência auditada. Nada foi interpolado ou distribuído de pontes. Nenhuma cotação foi consultada e nenhum dos 6.000 geradores anteriores foi repetido.

São 48 alvos de liquidez (oito especificações × duas coortes × três blocos), 336 coeficientes com incerteza nominal, 12 associações nível/mudança de liquidez × mudança de assimetria, 84 diagnósticos EP/simulação, 83 disposições de eventos e 12 alvos de continuidade. Os bancos e matrizes diárias ficam no export privado, não no repositório público.

No bloco21, os coeficientes de log-volume sem controles nos casos completos são 0,06468/0,06062, com N62/76. Com porte, setor e beta, caem para 0,031635/0,017201; p bruto 0,0404/0,1462, Holm16 0,2424/0,4386. Não há rejeição ajustada nos modelos completos. Isso não demonstra efeito zero nem equivalência. A capitalização é aproximada e os casos completos acrescentam seleção.

Na união de82 pares, a correlação entre mudanças de liquidez e de assimetria é 0,078896 (p0,4018; Holm4 0,4276). Nos77 originais é 0,133787 (Holm4 0,4276). A relação com o nível inicial não é evidência independente: theta contém menos delta inicial. Os testes/ICs são aproximações sem calibração própria; IC básico e p bilateral centrado não são duais.

## Fontes e limites de mensuração

`data/lab03j/cvm_selected_members.zip` reúne 63 membros públicos selecionados e recibos CVM, com hashes e atribuição ODbL em `cvm_sources_manifest.json`. Foram recuperados membros por byte ranges, não arquivos anuais completos; 2021 reutiliza o cache anterior. As tentativas limitadas de recuperar 95 originais de2015 produziram somente um XML completo. Não se afirma leitura/validação integral dos outros94.

O porte usa o último registro recuperado de quantidade emitida ou explicitamente integralizada, com recebimento e aprovação até31/12/2015, combinado a fechamentos por classe em30/12/2015. Contagens autorizadas/subscritas não integralizadas, tesouraria, free float e preços ambíguos não são presumidos. É capitalização de quantidade divulgada, não inventário exato no encerramento nem informação histórica exaustiva. Fontes arquivadas em2026 mantêm risco de vintage. O adendo deixa esse limite explícito, sem substituição por volume.

O cadastro original permanece fixo. Ativos extras usam classificação B3 arquivada de15/9/2022; DTEX é alias explícito de DXCO, mesmo CVM21091. HGTX/LAME/TIMP sem classificação recuperada ficam ausentes. Há79 portes recuperáveis em118 ISINs,62/76 casos completos e nove setores nos modelos; os dez setores das amostras principais não mudam.

Dos83 flags,41 têm fator de capital compatível,19 são candidatos da grade de um centavo e23 não têm correspondência nas tabelas recuperadas. Dentro de2016–2025 são56:37 com fator e19 sem correspondência. Aprovação não é data ex, cobertura das fontes não é exaustiva e **nenhuma das83 datas foi certificada integralmente por esse cruzamento**. A auditoria global permanece0/197, o que não significa197 erros.

A sensibilidade de linhagem encadeia somente KROT3/COGN3, ESTC3/YDUQ3 e TBLE3/EGIE3, documentadas por companhias, mesma classe/emissor, fator1. Exige pregões adjacentes na transição. A seleção2015 passa de64 a67 elegíveis iniciais (média −0,089429); a união de100 a103. Nenhum par antigo/novo aparece duas vezes entre os elegíveis iniciais. Não se encadeiam fusões, caixa ou conversões de classes; a matriz principal por ISIN permanece intacta.

## Execução em um lote

Execute somente `notebooks/Lab03J_liquidez_controles.ipynb`, CPU, executar tudo. Usa o export I já conferido do autor (`1L5w3uJvjTU4XiQir1BGMF3XNCWLS-_Ru`, SHA256 `ff67a56f9b9cc8b91f11bcbcad311d6253fcfe95aef3f9e02303bad677b41e0e`) e os onze ZIPs B32015–2025 existentes no Drive. Procura os caches antes de copiar bytes do próprio Drive; não acessa provedores de cotações. Fontes de código/tabelas são fixadas por commit público e SHA256. Não execute novamente I/H/F/G/E.

O notebook autentica membros do export I sem executar código recebido, extrai volumes dos caches, reproduz porte e todos os modelos, executa oráculos, compara tabelas/limiares e mostra os gráficos. O export final tem manifesto de membros, CRC, releitura SHA e é salvo no Drive em `alem_do_beta/lab03j_resultados`. Salve também a cópia executada do notebook e compartilhe seu link. A validação local do notebook não é execução do autor no Colab.

CLI equivalente, com arquivos autenticados disponíveis:

```bash
python scripts/run_lab03j_batch.py --i-output /caminho/outputs_I --b3-cache /caminho/cache_b3 --output /caminho/novo_lote_J
```

O diretório de saída deve ser novo. Insumos diários e bancos gerados são privados; não os publique no Git. O código das coletas CVM/originais fica para rastreabilidade, mas o notebook usa os membros congelados e **não repete as coletas**.

## Evidência e fechamento

Os oráculos próprios usam OLS densa e índices explícitos sem importar a produção: 7.080 regressões temporais,192 controles/IC/p,36 estatísticas de postos, diferença máxima2,26e−15. A continuidade tem2.360 ajustes por regime e diferença máxima1,12e−15. A exportação de todos os controles tem192 comparações densas adicionais. A suíte pública tem114 testes:112 passam, dois dependem de artefatos históricos externos não incluídos; estes não são contados como aprovados. Lacunas J recebem verificação própria.

O LaTeX principal continua `paper/main.tex`. Artigo16 páginas e suplemento26 nesta revisão, com gráfico dos dez anos no principal, controles completos e famílias explícitas, detalhes setoriais/risco no suplemento. O resumo deixa de apresentar theta/liquidez como confirmação independente. Três referências de liquidez foram incorporadas com alcance de leitura declarado. O experimento externo2015 foi fornecido no processo de avaliação assistida por IA; reprodução própria não equivale a revisão humana independente. KRR não foi implementado nem avaliado.

O quadro `docs/resposta_pareceres_J.md` dá disposição a todos os apontamentos novos. Limites científicos que a evidência não elimina são relatados, não marcados como resolvidos: inventário exato de ações/tesouraria, datas ex, conciliação econômica global, causalidade e calibração dos novos alvos. Não há merge automático nem garantia de publicação.
