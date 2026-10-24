# Além do Beta

**Além do Beta Tradicional: Assimetria, Heterogeneidade Setorial e Risco em Ações Brasileiras**  
Robson Dias Ferreira — CMP609, PPGC/UFRGS.

Esta é uma cópia selecionada do material de pesquisa já versionado em `robsondf/alem-do-beta`, destinada à avaliação do manuscrito. Não contém novas estimações, downloads financeiros ou alterações nos resultados. O repositório de origem e os arquivos do Google Drive foram preservados.

## Comece pelo artigo

- [PDF principal](paper/main.pdf): versão de 20 páginas incorporada no PR #85 do projeto de origem.
- [Fonte principal LaTeX](paper/main.tex) e [corpo do artigo](paper/artigo_revisado.tex).
- [Hipóteses e estimandos](docs/hipoteses_e_estimandos.md).
- [Escopo da seleção e proveniência](docs/REPOSITORY_SCOPE.md).
- [Execução e verificações](docs/REPRODUCTION.md).

Para uma avaliação independente, leia primeiro o PDF. Os recibos e testes permitem examinar a implementação e sua proveniência; não substituem a avaliação do mérito científico.

## Conteúdo

| Diretório | Conteúdo |
|---|---|
| `paper/` | Manuscrito atual, bibliografia usada, oito figuras e três arquivos de tabelas necessários à compilação |
| `src/` | Módulos da estimação, análises temporal/setorial/de risco, inferência, previsão e sensibilidades finais |
| `scripts/` | Execução, gráficos, verificadores e ferramentas congeladas necessárias aos protocolos preservados |
| `tests/` | Testes originais dos módulos retidos |
| `data/` | Protocolos, hashes, recibos e evidência documental já presente no GitHub |
| `results/tables/` | Uma cópia dos resultados Colab conferidos das etapas finais; sem duplicatas de preparação local |
| `notebooks/` | Cinco notebooks existentes necessários à leitura das etapas finais e à preservação do runtime E |
| `provenance/` | Relação completa dos arquivos selecionados e omitidos, com identificação do commit de origem |

As amostras são fixas: 80 ativos em 2016–2025 e 117 em 2021–2025, em dez setores; os mesmos 80 também são comparados em 2021–2025. A unidade é o ativo/classe/ISIN. As regressões utilizam retornos, com pares válidos e ausências preservadas.

## Limites do material

Esta cópia não é uma distribuição autossuficiente dos dados financeiros. Caches e exports integrais permanecem no Drive, com os hashes documentados nos protocolos. Sem essas entradas, podem-se ler os resultados e executar os testes que independem delas, mas não repetir toda a análise empírica.

Seleção retrospectiva, sobrevivência, identificação econômica incompleta e limitações inferenciais permanecem descritas no artigo. A reprodução numérica não equivale à homologação econômica integral. O estudo não estabelece assimetria generalizada, persistência futura ou superioridade preditiva.

## Origem e direitos

Origem: [commit c21b086b976ec11549fb4feb211099e0d78c61cc](https://github.com/robsondf/alem-do-beta/tree/c21b086b976ec11549fb4feb211099e0d78c61cc). Os arquivos científicos copiados mantêm seus bytes; o histórico de desenvolvimento permanece na origem. O acesso à origem privada não é requisito para ler os arquivos selecionados aqui.

Consulte [direitos e estado editorial](docs/RELEASE_STATUS.md). Não foi atribuída uma nova licença ao código, ao manuscrito ou a materiais de terceiros nesta cópia. O nome do repositório indica seu uso para avaliação por outro agente, não autoria ou validação por esse agente.
