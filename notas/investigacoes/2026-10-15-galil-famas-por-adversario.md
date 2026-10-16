# Galil ou FAMAS com colete contra cada compra do adversário (fase 17)

**Pergunta.** Na tabela dos grupos de compra da decisão 8i, a Galil ou a FAMAS com colete (`rifle_t2`, com
colete) fica em "força" e vence 61% dos rounds, mais que a compra cheia (56%). A suspeita era que esses 61%
viessem de pegar adversário em eco (o time que ganhou a pistola e joga contra o eco do outro), e não da
compra em si. A pergunta: qual é a vitória dessa linha separada pelo grupo de compra do **adversário**
naquele round (eco, pistola, força ou compra cheia)?

**Resposta.** Só 13% dos rounds são contra eco. A maior parte (58%) é contra compra cheia, e ali a Galil e a
FAMAS ainda vencem 55%. Os 61% não vêm de pegar eco.

## Como foi medido

- Script: `pesquisa/galil_famas_por_adversario.py`. A saída fixada, gravada com a versão das métricas 24, é
  `pesquisa/galil_famas_por_adversario.json`. Para conferir: `py -3.12 -m pesquisa.galil_famas_por_adversario --confere`
  (precisa do `data/interim/`).
- A fonte é a mesma da tabela da 8i: `scripts.fit_economia.confrontos_do_corpus`, nas 52 partidas, com o
  **empate dividido** da 8i. Por isso as contagens são time-rounds com frações. O grupo do adversário sai de
  `metrics.economia.grupo_de_compra`, aplicado à classe dele. O total bate com a linha publicada: 128,6
  rounds e 61%.
- Só mede. Não muda a classificação, nenhum número publicado nem nenhuma página.

## Os números

Galil ou FAMAS com colete (`rifle_t2`, grupo força), por grupo do adversário:

| grupo do adversário | rounds (amostra) | vitórias | fração dos rounds | vitória |
|---|---|---|---|---|
| eco | 16,5 | 14,5 | 13% | 88% |
| pistola | 0 | 0 | 0% | sem rounds |
| força | 37,5 | 22,9 | 29% | 61% |
| compra cheia | 74,5 | 40,9 | 58% | 55% |
| **total** | **128,6** | **78,2** | 100% | **61%** |

Para comparar, o rifle de compra cheia (`rifle_t1`, com colete) contra os mesmos grupos:

| grupo do adversário | rounds (amostra) | vitórias | fração dos rounds | vitória |
|---|---|---|---|---|
| eco | 122,5 | 110,0 | 8% | 90% |
| pistola | 4,7 | 3,2 | 0% | 68% |
| força | 282,9 | 182,7 | 19% | 65% |
| compra cheia | 1.093,7 | 546,6 | 73% | 50% |
| **total** | **1.503,8** | **842,5** | 100% | **56%** |

## Leitura

- A Galil e a FAMAS pegam eco numa fração parecida com a do rifle cheio (13% contra 8%). Contra eco, as
  duas vencem quase igual (88% e 90%).
- Contra compra cheia, a Galil e a FAMAS vencem 55%, e o rifle cheio vence 50%. Mas são 74,5 rounds. Com
  essa amostra, o erro padrão de uma taxa perto de 50% é de uns 6 pontos. A diferença de 5 pontos não
  separa as duas compras: o que o dado mostra é que a Galil e a FAMAS não perdem para a compra cheia.
- O que puxa os 61% para cima dos 56% é a mistura: a Galil e a FAMAS enfrentam menos compra cheia (58% dos
  rounds, contra 73% do rifle cheio) e mais força (29% contra 19%). Não é o eco.

## Conclusão

**Fica em força, sem mudança** (resposta do Pedro, 2026-10-15). "A suspeita era que a Galil e a FAMAS
ganhassem duelos por pegar adversários em eco. Os dados mostram o contrário: só 13% dos duelos são contra
eco, e contra compra cheia elas vencem 55%. Isso confirma 'força'; não é uma estatística inflada por eco."
A tabela da 8i e `metrics.economia.grupo_de_compra` ficam como estão.
