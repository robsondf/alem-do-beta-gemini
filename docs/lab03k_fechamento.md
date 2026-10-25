# Lab03K — porte, liquidez e fechamento dos pareceres

## Estado

Lote executado e verificado localmente em 25/10/2026. A integração integral do notebook também passou: cinco códigos sem exceções, 20 fontes autenticadas, 72.724 valores e 12.381 posições de limiar concordantes. Execução do autor no Colab ainda não recebida. Não repetir J, I ou os demais labs. Amostras principais80/117, classes/ISINs, dez setores, retornos e ausências permanecem intactos.

O protocolo `data/lab03k/protocol_v1.json` antecede os novos contrastes nos commits original `695508cca5406b51558a467f70edfff8b030c29d` e público `29cba58a0c5d0b70b3486c1489bb8fae240c930e`. Resultados J e pareceres já eram conhecidos: trata-se de extensão exploratória, não pré-registro.

## Resultados efetivos

- Modelo de referência: Δ2016–20 ~ log volume2015 + log capitalização divulgada2015 + setor fixo. O setor inclui classificação arquivada de2022, não informação setorial disponível em2015. Casos comuns J:62/76, nove setores representados.
- No bloco21, λ=0,032954/0,020886 e γ=0,027204/0,051481. ICs e p marginais são nominais. A nula conjunta λ=γ=0 produz p=0,0172/0,0192 e Holm2=0,0344 em ambas as coortes. Rejeição conjunta não demonstra dois efeitos separados ou causalidade.
- β2015:59/73 casos, Holm6=0,1456/0,0800; exclusão integral dos ativos com qualquer marca sem correspondência em2015–25:54/67, 0,0800/0,0828; Amihud2015:59/73, 0,1004/0,0060. Sensibilidades não uniformes, diferentes casos/medidas. Blocos5/63 e todos os coeficientes exportados.
- Giro é reparametrização exata: coeficientes λ e λ+γ; não nova robustez. Erro máximo de equivalência4,06e−14. Correlações log-volume/porte0,705/0,724 e VIFs completos2,714/2,443.
- Família J de16 comparações preservada integralmente; dependência entre modelos não invalida Holm. Os modelos completos J continuam com Holm16=0,2424/0,4386.
- Calibração K:6leis×1000réplicas×4999sorteios, somente referência/bloco21/nula global condicional. FWER simulada0,6–2,6%; coberturas marginais89,5–94,8%, com subcobertura material. Wilson e erro Monte Carlo por alvo/lei exportados. Não valida universalmente os ICs, as sensibilidades, efeitos mistos ou os resultados anteriores.
- Oráculo independente:4248ajustes temporais,96transversais,24caudas, erro máximo8,44e−15. Aceleração:608ajustes ponderados, erro1,05e−16. Cinco testes unitários passaram.

## Execução

Abra `notebooks/Lab03K_porte_liquidez.ipynb` no Colab, faça uma cópia no Drive e execute tudo com CPU. O notebook autentica código por commit/SHA256, reutiliza os exports I/J existentes e baixa esses mesmos arquivos do Drive apenas se não encontrar cópia autenticada. Não baixa cotações ou onze ZIPs B3. Não modifique os IDs/hashes para aceitar arquivo divergente.

O lote roda estimações, calibração, testes e oráculos; mostra tabelas e o gráfico; compara saídas com referências locais; salva ZIP com manifesto no Drive. Salve também a cópia executada e forneça seu link. Matrizes diárias, pré-período e bancos de sorteios ficam no ZIP privado, nunca no Git.

CLI equivalente:

```bash
python scripts/run_lab03k.py --i-output CAMINHO_I --j-batch CAMINHO_BATCH_J --output SAIDA_NOVA
python scripts/calibrate_lab03k.py --i-output CAMINHO_I --j-batch CAMINHO_BATCH_J --output SAIDA_NOVA
python scripts/verify_lab03k.py --i-output CAMINHO_I --j-batch CAMINHO_BATCH_J --output SAIDA_NOVA
python scripts/build_lab03k_paper.py --source SAIDA_NOVA --paper SAIDA_PAPER
```

`CAMINHO_I` contém a matriz de retornos de `gaps_preserved/`; `CAMINHO_BATCH_J` é `batch_J` dentro do export J autenticado. Ambiente Python com numpy,pandas,scipy,matplotlib,threadpoolctl; memória de alguns GB para23matrizes de pesos. O tempo depende da CPU; não há prazo prometido nem execução do autor presumida.

## Limites que não são apagados

Capitalização aproximada, quantidade/free float exatos, datas ex não certificadas, cobertura de sucessões, eventos, seleção retrospectiva e sobrevivência continuam limitações reais. O inventário registra datas/códigos observados e estado econômico desconhecido, sem inferir saída de bolsa. Cinco dias de direitos e demais ausências continuam ausentes.0/197 históricos economicamente homologados não significa197erros.

O artigo principal é `paper/main.tex`; suplemento é `paper/suplemento.tex`. Gráficos de todo o período permanecem. Os novos resultados não estabelecem persistência, causalidade, ganho preditivo ou contribuição própria em representação/raciocínio. Não houve merge automático.
