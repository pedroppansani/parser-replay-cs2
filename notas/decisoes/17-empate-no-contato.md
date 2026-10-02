# Decisão 17: Empate no primeiro contato não é abertura de ninguém

- **ID:** 17
- **Status:** vigente
- **Data:** 2026-09-16 (entrada no arquivo; o texto não traz data)
- **Resumo:** Empate no primeiro contato não é abertura de ninguém.

## Texto

17. **Empate no primeiro contato não é abertura de ninguém.** Quando uma granada
    pega vários do time no MESMO tick, todos empatam em primeiro lugar. Medido:
    24 de 374 lados-round nas 9 partidas, um deles com quatro jogadores em
    10,359375s. Contar os quatro como quem abriu o round inflava o entry do time
    inteiro. O empate sai do numerador nos dois módulos que usam a métrica
    (`archetypes` e `player_roles`), com teste de regressão.
