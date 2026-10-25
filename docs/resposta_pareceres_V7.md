# Resposta aos pareceres da sétima versão

Edição de fechamento `editorial-v8-20261025`, sem novos modelos, testes ou simulações. Base avaliada: artigo de 18 páginas e suplemento de 29 no commit público `8f7126eef87added190bcc02ae2bc6b2b90fd647`, incorporado em `cbd16eb77969310db1d0d7e7ce3ca58e9d25137f`.

Pareceres recebidos: independente, 6 páginas, SHA-256 `779460017e737029b5ccdbae41965197aabfa4f34c3c3bca2fb310ebc73ffcd7`; sétima versão, 5 páginas, SHA-256 `7fe1d392ca2fd96c30df57ce885623ee11ee90115b8e9c5c7d2d7d168407592f`. Os PDFs de terceiros não são redistribuídos. O segundo declara participação na produção do experimento de 2015 e do diagnóstico de EP; o primeiro comenta explicitamente o segundo. Convergência não equivale a duas auditorias humanas independentes ou aceite editorial.

| Item | Disposição nesta edição |
|---|---|
| M1 — resultado no resumo/conclusão | Atendido com números, distinção de fontes e limites. A comparação COTAHIST usa −0,1685/−0,0857, não −0,177/−0,086 como se só variasse seleção. A conclusão mantém o núcleo de assimetria e sensibilidade temporal. Não se afirma que seleção causou a diferença ou que o choque de 2020 foi causalmente identificado. |
| M2 — giro e porte | Nova tabela apresenta λ, γ e λ+γ, ICs nominais e p bruto/Holm 2 conjunto. Coeficientes provêm dos CSVs congelados; nenhum contraste novo é testado. Sinais e intervalos são descritos, sem afirmar teste de maior estabilidade/importância econômica de porte. |
| M3 — ferramentas | ChatGPT/Codex, Claude e Gemini identificados pelos papéis documentados. Versões exatas não inventadas; responsabilidade humana e distinção de revisão por pares explícitas. |
| M4 — concisão | Artigo de até 15 páginas, incluindo referências; margens e fonte SBC preservadas. Os sete quadros principais e o gráfico dos dez anos permanecem. Detalhes técnicos, referências documentais específicas e a visualização da crise estão no suplemento, sem perda de dados. |
| R1 — valores brutos | Os seis alvos dos três blocos são expostos com p bruto e Holm 6. Corrigida a contagem do parecer: quatro, não cinco, têm p bruto abaixo de 0,05 no bloco 21. Amihud dos originais tem 0,0502; beta2015 dos originais, 0,1456. |
| R2 — defasagens | Registrado que a média não se aproxima sistematicamente de zero, sem converter mudanças de estimando em teste causal de negociação infrequente ou risco de liquidez. |
| R3 — rótulos | Famílias nomeadas pelo alvo no corpo. As letras internas permanecem somente onde necessárias à proveniência no suplemento/recibos. Tamanhos e correções preservados. |

## Recomendações que não foram copiadas literalmente

- O teste conjunto não soluciona colinearidade nem separa efeitos causais. VIFs e posto do modelo são diagnósticos, não demonstração de impossibilidade de estimar coeficientes.
- Fator simulado 0,04 é uma sensibilidade motivada pelo diagnóstico residual; não foi identificado como a verdadeira correlação latente. A cobertura marginal 89,5–94,8% continua materialmente abaixo de 95% em parte das leis.
- O sinal −0,297 e os cabeçalhos λ̂/γ̂ foram conferidos no PDF anterior e já estavam corretos. Não se aplicam correções fictícias sugeridas por leitura/OCR.
- O texto pronto de disponibilidade mistura tipos de banco e troca a diferença máxima externa: o recibo efetivo é 8,08e−14 nas tabelas e 1,20e−14 nos bancos, não um máximo conjunto de 8,44e−15. Valores originais permanecem nos recibos e suplemento.
- “Associação mais forte/estável” entre parametrizações não é inferida da simples comparação de coeficientes ou ICs nominais. Não se adiciona ML para aderência nominal à linha de pesquisa.
- Enquadramento em periódico e requisitos do PPGC continuam distintos. A documentação registra as limitações e não promete aceite, citações, acesso irrestrito às matrizes ou nova licença de terceiros.

## Verificação e distribuição

O pacote contém PDFs com nomes de edição, fontes completas para Overleaf, manifesto de hashes, tabelas de apresentação reconstruíveis, testes contra troca de versão e guias de direitos/acesso. As fontes científicas anteriores são preservadas por hash. Não é necessário executar outro notebook. Ver `EDICAO_V8.md` e os recibos em `data/editorial_v8/`.
