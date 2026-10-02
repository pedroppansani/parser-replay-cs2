# Decisão 9: Convenção de ângulos do CS2: pitch positivo = olhar para BAIXO

- **ID:** 9
- **Status:** vigente
- **Data:** 2026-09-15 (entrada no arquivo; o texto não traz data)
- **Resumo:** Pitch positivo olha para baixo; o teste roda a convenção invertida como controle.

## O que vale hoje

Os 1,76° e 6,52° são do corpus de 9 partidas. O valor atual está em `data/processed/numeros_citaveis.json` (bloco `convencao_de_angulos`).

## Texto

9. **Convenção de ângulos do CS2: pitch positivo = olhar para BAIXO.** Validada
   empiricamente (erro mediano de 1,76° no tick da kill, contra 6,52° na
   convenção invertida). O teste roda a convenção invertida como controle — se
   um dia passar nas duas, o teste não está medindo nada.
