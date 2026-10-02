# Decisão 16: A escala dos papéis é ajustada no conjunto das partidas, não dentro da partida

- **ID:** 16
- **Status:** vigente
- **Data:** 2026-09-16 (entrada no arquivo; o texto não traz data)
- **Resumo:** A escala dos papéis é do corpus (`archetype_reference.json`).

## Texto

16. **A escala dos papéis é ajustada no conjunto das partidas, não dentro da
    partida.** `metrics/archetype_reference.json`, mesmo padrão do
    `global_model.json`. Normalizar dentro da partida faz alguém ficar em 1,0
    mesmo quando ninguém se destacou, e o card de destaque mostraria um jogador
    mediano como retrato da partida. Reajuste com
    `scripts/fit_archetype_reference.py` sempre que processar demo nova ou mexer
    num componente.
