# Decisão 14: Spawn não é área de jogo e fica fora da partição do mapa

- **ID:** 14
- **Status:** vigente
- **Data:** 2026-09-16 (entrada no arquivo; o texto não traz data)
- **Resumo:** Spawn não é área de jogo; passagem rápida não conta como rotação.

## Texto

14. **Spawn não é área de jogo e fica fora da partição do mapa.** O CTSpawn da
    Ancient cai geometricamente do lado do A; contá-lo fazia todo CT "ir pro A"
    em todo round e zerava a métrica de não-rotação para times inteiros. Pelo
    mesmo motivo, passar rapidamente pela área do outro site não conta como
    rotação (`MIN_OTHER_SITE_SHARE`): os corredores de ligação caem de um dos
    lados. Ambos têm teste de regressão.
