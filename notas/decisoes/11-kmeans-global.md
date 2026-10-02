# Decisão 11: O KMeans é ajustado UMA vez no conjunto das partidas, não por partida

- **ID:** 11
- **Status:** vigente
- **Data:** 2026-09-16 (entrada no arquivo; o texto não traz data)
- **Resumo:** O KMeans é ajustado uma vez no corpus (`global_model.json`), não por partida.

## Texto

11. **O KMeans é ajustado UMA vez no conjunto das partidas, não por partida.**
    O rótulo numérico do KMeans é arbitrário: treinando por partida, o "cluster
    3" de uma não tem relação com o da outra — e `cluster_names.json` é um
    arquivo único aplicado a todas. Medido nas 9 partidas: o grupo de dano alto
    era o cluster 3 em match_01, o 2 em match_02 e o 0 em match_04. O modelo vive
    em `clustering/global_model.json` (JSON, não pickle) e é ajustado por
    `scripts/fit_global_clusters.py`. Há teste travando a propriedade e um teste
    de controle mostrando que o modo antigo não a tinha.
