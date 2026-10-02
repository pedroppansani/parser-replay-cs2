# Decisão 22c: As 9 demos do corpus NÃO servem para calibrar contra a HLTV

- **ID:** 22c
- **Status:** vigente
- **Data:** 2026-09-17 (entrada no arquivo; o texto não traz data)
- **Resumo:** Partidas de FACEIT não servem para calibrar contra a HLTV.

## O que vale hoje

"As 9 demos do corpus" era o corpus inteiro na época. Hoje são 52 partidas, 43 profissionais; a regra vale para as 9 de FACEIT.

## Texto

22c. **As 9 demos do corpus NÃO servem para calibrar contra a HLTV.** São
    partidas de FACEIT -- arquivos identificados por UUID de FACEIT, elencos que
    são pugs (donk com companheiros diferentes a cada partida), não line-ups
    profissionais. **A HLTV não publica rating para partidas de FACEIT.** A
    calibração exige demos de partidas oficiais cobertas por ela, e o mínimo
    estatístico está em `scripts/fit_rating.py`: 7 de treino + 3 de teste, com a
    divisão feita por PARTIDA e nunca por jogador.
