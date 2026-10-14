# clustering/: agrupamento de estilo

Complementa o `CLAUDE.md` da raiz e não o substitui. Uma regra por linha; (N) = nota em
`notas/decisoes/`. Vale também para `scripts/fit_global_clusters.py`.

- Clustering é por (jogador, round), não por jogador (7)
- As features são só COMPORTAMENTO: `damage`, `kills`, `trade_kills`, `utility_damage` e
  `survived` não voltam para a lista; `sem_contato` não é feature (o tempo até o contato nulo é
  preenchido pela mediana do modelo global, `fill_medians`) (7b)
- O KMeans é ajustado UMA vez no corpus (`global_model.json`, JSON e não pickle, por
  `scripts/fit_global_clusters.py`), nunca por partida (11)
- O KMeans não nomeia os grupos: o nome é do Pedro (`cluster_names.json`); não gere rótulo
  automático. A descrição exibida sai de `describe_clusters` sobre o perfil GLOBAL, nunca do recorte
  da partida (8)
- `cluster_names.json` entra no payload do site; o agrupamento não tem seção própria no site (só
  aparece no "jeito de jogar mais frequente" do Perfil) (8)

## Calibração do Pedro (não resolva sozinho)

- Nomes dos grupos (`cluster_names.json`): todo reajuste que renumerar os grupos exige conferir os
  nomes de novo (`py -3.12 -m scripts.fit_global_clusters --dry-run`).
