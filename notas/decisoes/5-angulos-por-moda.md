# Decisão 5: Ângulos de pré-fire são derivados dos dados, não constantes inventadas

- **ID:** 5
- **Status:** vigente
- **Data:** 2026-09-15 (entrada no arquivo; o texto não traz data)
- **Resumo:** Ângulos de pré-fire saem dos dados por moda circular; nunca bins fixos.

## Texto

5. **Ângulos de pré-fire são derivados dos dados, não constantes inventadas.**
   Um ângulo chutado errado premia placement ruim em silêncio. A derivação usa
   agrupamento circular por moda — **não volte para bins de largura fixa**, que
   perdem ângulos caindo na borda do bin (bug real, pego por teste).
