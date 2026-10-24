# Além do Beta

**Além do Beta Tradicional: Assimetria, Heterogeneidade Setorial e Risco em Ações Brasileiras**  
Robson Dias Ferreira — CMP609, PPGC/UFRGS.

Esta é uma cópia selecionada do material de pesquisa já versionado em `robsondf/alem-do-beta`, destinada à avaliação do manuscrito. A seleção inicial foi seguida pelas revisões identificadas na proveniência; o lote F acrescenta análises pós-parecer, preservando os resultados e protocolos anteriores. Não contém a matriz privada de retornos ou downloads novos de cotações. O repositório de origem e os arquivos do Google Drive foram preservados.

## Revisão G — terceiro parecer

[Análises, matriz de resposta e reprodução](docs/lab03g_parecer_v3.md): mudança agregada entre quinquênios, inferência defasada/semanal e calibração de seis mecanismos. São6.000 réplicas,84.000 linhas e66 alvos/blocos observados, com verificador independente. **A simulação expõe falhas:** cobertura dos ICs básicos51,8–95,8%; erro familiar temporal5,6% no estresse AR0,6. Não se declara validade nominal ou robustez uniforme.

**Único notebook novo:** [Lab03G_mudanca_calibracao.ipynb](notebooks/Lab03G_mudanca_calibracao.ipynb). Executar tudo em CPU,salvar cópia/ZIP no Drive; não repetir F/E. A preparação G é local; o Colab novo do autor permanece pendente. Códigos/dados/recibos anteriores preservados.

## Colab F conferido

[Notebook executado e salvo pelo autor](https://colab.research.google.com/drive/11biQglsj9zdEMXcEH71sijGvSuEAEQJH):10 fontes de células idênticas,seis códigos,zero exceções;ZIP de3.783.941bytes/31 membros autenticados;309.848 valores concordantes,máximo1,46e−14;decisões e gráficos preservados. [Recibo da conferência](data/lab03f/validacao_colab_20261024.json). Não repetir F/anteriores. Notebook e export permanecem no Drive; nenhum resultado científico foi modificado nesta conferência.

## Comece pelo artigo

- [PDF principal](paper/main.pdf): edição G:25 páginas,38 referências citadas,9 figuras e11 tabelas. [Suplemento independente](paper/suplemento.pdf):7 páginas,8 referências;43 referências distintas no conjunto.
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
