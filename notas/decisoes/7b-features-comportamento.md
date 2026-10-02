# Decisão 7b: As features do clustering são só COMPORTAMENTO

- **ID:** 7b
- **Status:** vigente
- **Data:** 2026-09-16 (entrada no arquivo; o texto não traz data)
- **Resumo:** Features do clustering são só comportamento; resultado (kills, dano) fica fora.

## O que vale hoje

A silhueta de 0,216 e os 56% são do corpus de 9 partidas. Hoje, com 52: silhueta 0,195 (`data/global_clusters/model_meta.json`).

## Texto

7b. **As features do clustering são só COMPORTAMENTO.** `damage`, `kills`,
   `trade_kills`, `utility_damage` e `survived` saíram da lista: são resultado, e
   com elas dentro o KMeans agrupava os rounds por como terminaram — o que a
   tabela de ADR já diz. Tirando as cinco, a silhueta foi de 0,168 para 0,216
   (k=4) e os dois eixos do gráfico passaram a explicar 56% em vez de 40%. Os
   grupos viraram estilo (fica parado longe / entra sem a mira pronta / roda o
   mapa / joga junto e rápido). **Não devolva features de resultado para a
   lista** — a lista removida está nomeada no módulo.
