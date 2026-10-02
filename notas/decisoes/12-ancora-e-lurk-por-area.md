# Decisão 12: Âncora e lurk são medidos por ÁREA do mapa, não por distância nem por tempo

- **ID:** 12
- **Status:** vigente
- **Data:** 2026-09-16 (entrada no arquivo; o texto não traz data)
- **Resumo:** Âncora e lurk são medidos por área do mapa (A/Mid/B), não por distância.

## Texto

12. **Âncora e lurk são medidos por ÁREA do mapa, não por distância nem por
    tempo.** Definição de jogo do Pedro: âncora é o CT que fica no mesmo bombsite
    mesmo quando os T indicam o outro lado; lurker é o T que joga outra área
    enquanto o time executa. As versões antigas (contato tardio e distância média
    do time) mediam outra coisa — dois CTs em bombsites opostos estão à mesma
    distância um do outro que um lurker do time. `metrics/map_areas.py` particiona
    o mapa em A/Mid/B a partir dos plants do próprio demo.
