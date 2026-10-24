# Argumento teórico, hipóteses e estimandos

Atualização: 23/10/2026. A formulação abaixo explicita o desenho já utilizado; os resultados empíricos eram conhecidos. **Não é pré-registro independente**, nem autorização para mudar alternativas, famílias ou decisões segundo os resultados.

## Fundamentação e alcance

A literatura de risco de queda motiva estudar a exposição em estados adversos (Ang, Chen e Xing, 2006, DOI10.1093/rfs/hhj035). Essa motivação econômica não implica logicamente que todo ativo tenha beta de queda maior. Também não torna nossa diferença de inclinações um teste do prêmio de risco previsto por modelos de equilíbrio. O CAPM em retornos esperados não basta para deduzir igualdade de projeções condicionais de retornos observados.

Uma referência estatística de simetria é `r_it = a_i + g_i D_t + b_i m_t + e_it`, com `D_t=1(m_t>0)` e `E(e_it | m_t,D_t)=0`. Admite interceptos distintos. Sob essa referência, as duas inclinações são iguais. A extensão inclui `Delta_i D_t m_t`; então `beta_minus=b_i`, `beta_plus=b_i+Delta_i`. Esses são coeficientes de projeção, não parâmetros causais identificados. Interpretar sua estabilidade como estrutural exigiria mais hipóteses.

## Correspondência com as análises

| Pergunta / proposição | Estimando | Evidência e decisão já especificadas |
|---|---|---|
| H1 de pesquisa: a exposição ao mercado difere entre altas e quedas em parte dos ativos selecionados. | `Delta_i=beta_plus-beta_minus` | Por ativo/período: H0 `Delta_i=0`, H1 `Delta_i!=0`; teste bilateral HAC5, Holm na família197. Rejeições individuais não provam prevalência populacional. |
| Expectativa direcional: risco de queda pode tornar exposição nas quedas particularmente relevante. | Sinal de `Delta_i` | `Delta_i<0` significa beta de queda maior. Frequências de sinais são descritivas; não se troca o teste bilateral por unilateral depois de conhecer resultados. |
| Questão setorial: a heterogeneidade se organiza por setor? | Medianas, contrastes e eta² | Exploratória; ICs marginais por blocos, setores pequenos e dependência comum. Sem novo teste global confirmatório ou causal de setor. |
| H2 de pesquisa: a assimetria pode mudar entre subperíodos. | `theta_i=Delta_2021_2025-Delta_2016_2020` | H0 `theta_i=0`, H1 `theta_i!=0`; 80 contrastes conjuntos. Junto às394 posições de direção anual, família temporal474, distinta da197. Não rejeitar não demonstra estabilidade/equivalência. |
| Direção em todos os anos observados | Todos os `Delta_iy` positivos ou todos negativos | Dois testes de interseção–união, preservando anos insuficientes; não é persistência futura. |
| Confiabilidade do método, Lab03C | Cobertura, viés, erroI/FWER e poder em DGPs conhecidos | Simulação condicional de desenho fixo. Não acrescenta observações do mercado nem calibra a família temporal474. |

A hipótese de pesquisa é uma proposição substantiva; H0/H1 são sua operacionalização estatística. Nenhum resultado nulo é interpretado como prova da nula, e nenhuma maioria de sinais é convertida em confirmação coletiva. A seleção retrospectiva e sobrevivência limitam generalização. A auditoria econômica global continua0/197.

## Integridade da formulação

Preservam-se os testes bilaterais, as famílias197/474, janelas80/117, retornos logarítmicos, estimandos e critérios anteriores. O artigo não afirma teoria nova nem confirmação do CAPM. Uma hipótese econômica direcional confirmatória adicional ou margem de equivalência deve ter fundamentação e validação próprias, preferencialmente em nova amostra; não será escolhida pelos resultados já observados.

## Extensão D autorizada em23/10

Acrescenta pergunta exploratória: a projeção condicional melhora MSE/MAE do retorno logarítmico seguinte contra projeção tradicional e referenciais zero/média? Não é H3 confirmatória pré-registrada. Treino252primário/504sensibilidade e origens móveis estritamente passadas; modelo de mercado usa somente m_(t−1) e integra inovações passadas. Períodos preditivos2019–2025/2024–2025, mantendo comum descritivo2021–2025. Hipóteses H1/H2 e famílias197/474 preservadas. Não se troca janela por ganho observado; não rejeição não prova equivalência. Envelope de postos é complemento com garantia na união finita de três mecanismos e resoluçãoMC explícita; não substituição silenciosa do primário nem certificação de qualquer erro financeiro.

## Complemento pós-terceiro-parecer

Lab03G acrescenta famílias secundárias, sem substituir197/474: Holm4 para média/mediana inicial e mudança pareada dos mesmos80; Holm18 para média/mediana de três modelos em três painéis. A mudança agregada média não testa mudança de todos os ativos. A mediana de theta é calculada nas diferenças por ativo. O protocolo foi escrito antes dos resultados G, com F conhecido, e não é pré-registro independente.

Calibração de tamanho/cobertura: famílias10/4 no bloco21 sob nulidade global, seis mecanismos,1.000 réplicas cada, bancos e mercado fixados. Não garante controle forte sob qualquer configuração, não se transfere ao18 e não remedia a subcobertura dos ICs básicos. Holm30 continua proteção conservadora entre escolhas, sem tratar os blocos como30 hipóteses científicas distintas. Ver `lab03g_parecer_v3.md` para resultados e matriz atual.
