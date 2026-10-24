# Direção de pesquisa: representação de evidência e raciocínio financeiro

**Estado: proposta pós-parecer, não implementada nem avaliada.** Não constitui resultado do artigo atual, pré-registro independente, prova de novidade ou autorização para prometer aceite. O projeto original fornece domínio, casos e infraestrutura; uma contribuição em IA exige pergunta, método e avaliação próprios.

## Problema computacional

Como um sistema pode derivar conclusões financeiras justificadas a partir de evidências numéricas e documentais incompletas, temporalmente disponíveis e potencialmente conflitantes, preservando a distinção entre suporte estatístico, validade de mensuração e falta de informação?

O caso financeiro é concreto: um valor-p sobre a referência de retornos observada permite uma afirmação condicional específica; não implica por si só que ajustes econômicos estejam identificados, que o padrão seja universal, que não rejeição prove estabilidade ou que uma estratégia obtenha ganho. Essas diferenças devem fazer parte da representação e da semântica de inferência.

## Pergunta e hipótese de avaliação propostas

Pergunta: a representação explícita de fontes, hipóteses, identidade e dois tempos — validade econômica e disponibilidade da evidência — permite reduzir conclusões sem suporte e usos de informação futura, mantendo cobertura útil de respostas e justificativas auditáveis?

Hipótese a registrar antes do benchmark: um procedimento que verifica essas restrições produz menor taxa de afirmações sem suporte e violações temporais que os comparadores definidos, para cobertura equivalente ou explicitamente reportada. Não se assume resultado positivo, vantagem de grafos ou necessidade de aprendizado supervisionado. Trata-se de hipótese de desempenho do sistema proposto, não evidência já obtida.

## Representação proposta

Cada afirmação deve ter sujeito tipado (ativo/classe/ISIN, janela ou procedimento), predicado, valor, unidade, universo, definição do retorno/estimando, fonte, data ou intervalo econômico, instante de disponibilidade conhecido, método e hipóteses. A proveniência liga entradas, atividade de transformação e saída, com vocabulário compatível com PROV-O quando aplicável.

Os tempos não são intercambiáveis. Um documento sobre evento de 2016 recuperado em 2026 não comprova, sozinho, sua disponibilidade para uma decisão em 2016. Se essa disponibilidade não for identificada, o estado deve permanecer desconhecido para consultas históricas. Fonte recuperada e data econômica não podem preencher automaticamente esse campo.

Separar os estados de evidência para uma proposição: suporte, refutação, conflito e informação insuficiente. A escolha de uma lógica existente e sua semântica exigem revisão da literatura; não se declara aqui uma lógica nova. Não rejeição estatística não é refutação do efeito, e incerteza de mensuração não invalida automaticamente toda afirmação condicional.

## Método a especificar

1. Esquema de afirmações, vínculos de proveniência e restrições de identidade/unidade/tempo.
2. Regras explícitas de admissibilidade, composição e escopo de conclusões, com condições de aplicação.
3. Inferência com trilha verificável: premissas usadas, regras aplicadas, pendências e fontes conflitantes.
4. Atualização/retração de conclusões quando uma evidência é corrigida ou substituída, sem apagar a versão anterior.
5. Propriedades a demonstrar em relação à teoria codificada, como correção das derivações e bloqueio de premissas indisponíveis no instante de consulta. Correção formal é relativa às regras e fatos, não prova de verdade econômica das fontes.

Converter dados em RDF ou acrescentar uma interface de LLM, isoladamente, não demonstra contribuição. Identificar o que existe na literatura e qual dificuldade computacional ainda não é atendida deve preceder a alegação de novidade.

## Tarefas de avaliação possíveis

- Perguntas sobre quais afirmações de assimetria são sustentadas sob uma referência e família específicas.
- Identificação de inferências indevidas entre não rejeição, equivalência e persistência.
- Consultas históricas que devem bloquear documentos ou estimativas ainda indisponíveis.
- Conflito entre fontes sobre identidade, evento, quantidade ou convenção de caixa, mantendo resposta inconclusiva quando necessário.
- Atualização incremental de justificativas após corrigir uma premissa, sem reescrever o histórico.

Manter os 80/117 ativos e o ativo/classe/ISIN como unidade no domínio empírico. Relações com emissores servem à identificação/dependência; não autorizam agregar classes, atribuir pesos empresariais ou selecionar novos ativos anualmente.

## Comparadores e ablações

Comparar com consulta estruturada convencional e um motor de regras que recebam **a mesma informação**. Um CSV contendo os mesmos tempos e regras pode ser tão correto quanto um grafo; o formato não é tratamento causal de qualidade. O ganho pode estar na expressividade, explicação, atualização ou custo, e deve ser medido.

Ablações podem retirar uma dimensão por vez — tempo, proveniência ou tratamento de conflito —, identificando explicitamente a informação removida. Um comparador de recuperação/LLM só deve entrar com modelo, versão, prompts, contexto, parâmetros e custos fixados; nenhuma comparação com LLM foi executada ou presumida.

## Métricas e protocolo

Medir conjuntamente taxa de conclusões sem suporte, precisão/cobertura das respostas, conflitos corretamente preservados, violações temporais, validade de referências, suficiência de justificativas, latência e custo de atualização. Sempre-abster deve ser comparador de cobertura zero, não um sistema declarado superior apenas por não errar.

Rótulos precisam de avaliação independente, com manual e adjudicação; o motor não pode gerar o próprio gabarito e depois ser avaliado contra ele. Separar casos de desenvolvimento e avaliação por tempo, ativo/emissor ou família de eventos para evitar reutilização de padrões próximos. Casos sintéticos de controle podem verificar propriedades, mas devem ser identificados e não representam novos dados de mercado ou eficácia empírica.

Definir critérios e margens antes da avaliação; reportar incerteza e resultados desfavoráveis. Um benchmark construído após os pareceres é pós-revisão, mesmo que suas decisões sejam congeladas antes da execução. Nenhuma avaliação prospectiva intocada é presumida.

## Relação com aprendizado de máquina

O método pode incorporar aprendizado para priorizar revisão de documentos ou extrair relações, mas essa etapa é opcional e exige dados rotulados, cortes temporais, calibração e análise de erro próprias. O núcleo de representação/raciocínio pertence à IA sem depender de uma rede neural. Não é necessário cobrir simultaneamente todas as áreas da linha em um único artigo.

## Decisão editorial

A versão CMP609 pode ser corrigida como estudo de finanças. Uma versão centrada neste problema computacional deverá reorganizar pergunta, contribuição e experimento, com revisão por orientação e confronto com literatura de KRR. Este protocolo fornece um caminho verificável para discutir essa decisão; não transforma a versão atual em artigo de IA já validado.

Referência de modelagem: W3C PROV-O, https://www.w3.org/TR/prov-o/, seções 3.1–3.3. Enquadramento: tópicos oficiais AAAI-26, https://aaai.org/conference/aaai/aaai-26/keywords/. Usar essas fontes como referência de vocabulário/escopo, sem atribuir novidade ao seu simples uso.
