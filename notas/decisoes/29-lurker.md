# Decisão 29: Lurker: sem os rounds com AWP, relativo à função e com amostra mínima

- **ID:** 29
- **Status:** vigente
- **Data:** 2026-09-24
- **Resumo:** Lurker: sem os rounds de AWP, relativo à função, mínimo de 8 rounds.

## O que vale hoje

O piso de 1,5× foi trocado por 1,284 (decisão 31).

## Texto

29. **Lurker: sem os rounds com AWP, relativo à função e com amostra mínima**
    (decisão do Pedro, 2026-09-24). O caso: o m0NESY levava "Lurker" como
    característica secundária (match_32) sendo que o título dele é "AWPer, AWP
    na mão em 63% dos rounds". São DUAS causas diferentes, e as duas foram
    corrigidas -- escolher uma só deixaria a outra de pé:
    - **estrutural**: segurar ângulo longe do time COM a AWP é trabalho do
      AWPer. Os rounds com AWP saem da conta. E a régua passa a ser a taxa
      esperada da FUNÇÃO estrutural daqueles rounds (princípio da decisão 15c),
      não a média do elenco: medido no corpus, "fora da área do time" nos rounds
      sem AWP é 0,175 para o trader, 0,203 para o suporte, 0,291 para o entry e
      0,232 sem função reconhecida. A própria função "lurker" FICA DE FORA da
      régua: ela é definida por jogar em outra área (decisão 12) e tem taxa
      esperada 0,97 -- normalizar por ela faria um lurker de verdade perder o
      rótulo. Piso: `PISO_LURK_RELATIVO`, nascido 1,5x o esperado (o fator com
      que o projeto ancora outros pisos ao acaso) e trocado em 2026-09-26 pelo
      corte estatístico 1,284 (decisão 31);
    - **amostra**: `MIN_ROUNDS_SEM_AWP` = 8, o mesmo mínimo que o projeto já usa
      para afirmar uma taxa de jogador (`player_profile.MIN_ROUNDS_PARA_TAXA`).
      Abaixo disso é DADO INSUFICIENTE, não "não qualifica" -- a distinção está
      no código e no teste.
    Efeito medido nas 52: característica Lurker 94 -> 55 (50 saem, 11 entram);
    dos 64 rótulos de líderes, 22 saíram por amostra e 4 por ficarem abaixo de
    1,5x. Nenhuma outra característica mudou. 35 títulos mudaram, todos de
    "Lurker" para âncora, principal fragger ou nenhum. **m0NESY: zero rótulos de
    Lurker em 12 jogador-partidas.** (Corrigido em 2026-09-26: são 12 pelo
    steamid, não 17.)
    O PISO ABSOLUTO ANTIGO (0,40) foi mantido como referência histórica no
    material de calibração: a proposta estatística de baixá-lo para 0,264 foi
    REFUTADA pelo julgamento de jogo do Pedro -- naquele corte, um AWPer com
    ângulo recuado virava lurker.
