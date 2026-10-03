# Decisão 7b: As features do clustering são só COMPORTAMENTO

- **ID:** 7b
- **Status:** vigente
- **Data:** 2026-09-16 (entrada no arquivo; o texto não traz data)
- **Resumo:** Features do clustering são só comportamento; resultado (kills, dano) fica fora.

## O que vale hoje

A silhueta de 0,216 e os 56% são do corpus de 9 partidas. Hoje, com 52: silhueta 0,195 (`data/global_clusters/model_meta.json`).

## Round sem contato (2026-10-02, auditoria 4.7)

O tempo até o contato fica **nulo** quando não houve contato (antes: "mediana da partida x 2", um
valor diferente em cada partida que vazava para `player_roles`, `archetypes` e o perfil). A
coluna `sem_contato` marca o round na tabela; no agrupamento, o modelo global preenche o tempo
com a mediana dele (`fill_medians`). `sem_contato` como feature foi medida e recusada: ARI 0,652
contra o agrupamento anterior (mínimo 0,9) e o grupo "Mira fora da altura" some. A variante
adotada: ARI 0,936, quatro perfis mantidos (nomes remapeados pela tabela cruzada), estabilidade
por reamostragem das partidas 0,929 (era 0,920). `pesquisa/imputacao_clusters.py` refaz.
Efeito colateral medido: 11 rótulos "Abre o round" entram (o round sem contato saiu do
denominador); a mediana do 1º contato muda em 350 jogador-partidas (mediana 3,0 s).

## Texto

7b. **As features do clustering são só COMPORTAMENTO.** `damage`, `kills`,
   `trade_kills`, `utility_damage` e `survived` saíram da lista: são resultado, e
   com elas dentro o KMeans agrupava os rounds por como terminaram — o que a
   tabela de ADR já diz. Tirando as cinco, a silhueta foi de 0,168 para 0,216
   (k=4) e os dois eixos do gráfico passaram a explicar 56% em vez de 40%. Os
   grupos viraram estilo (fica parado longe / entra sem a mira pronta / roda o
   mapa / joga junto e rápido). **Não devolva features de resultado para a
   lista** — a lista removida está nomeada no módulo.
