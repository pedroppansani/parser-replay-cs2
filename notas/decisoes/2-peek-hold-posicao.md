# Decisão 2: A classificação peek/hold usa posição medida, não a flag `is_scoped`

- **ID:** 2
- **Status:** vigente
- **Data:** 2026-09-16 (entrada no arquivo; o texto não traz data)
- **Resumo:** Peek/hold usa a posição medida, não a flag `is_scoped`.

## Texto

2. **A classificação peek/hold usa posição medida, não a flag `is_scoped`.**
   Posição é o sinal mais direto de deslocamento. (Registro: uma versão anterior
   afirmava que `is_scoped` era não confiável — aquilo era consequência do bug de
   tickrate, não defeito do dado. Com 64 tick as velocidades batem com a física
   do jogo: 29 u/s scopado, 104 u/s sem scope.)
