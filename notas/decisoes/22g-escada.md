# Decisão 22g: Escada de validação: contagem exata antes de olhar o rating

- **ID:** 22g
- **Status:** vigente
- **Data:** 2026-09-22
- **Resumo:** Escada de validação: contagem exata antes de olhar o rating.

## O que vale hoje

As contagens atuais estão em `data/processed/numeros_citaveis.json` (bloco `escada`).

## Texto

22g. **Escada de validação: contagem exata antes de olhar o rating**
    (`scripts/escada_validacao.py`, K-D-ADR oficiais de 410 jogadores em
    `data/reference/hltv_placar.json`; `tests/test_escada.py` trava os degraus 1
    e 2). Rounds 41/41, kills e mortes 410/410, ADR 401/410, KAST 247/330 (era
    230/310 até 2026-09-22: +20 KASTs de match_21/22 e a correção do SH1R0).
    Multi-kills e aberturas sem dado oficial ainda. Cada print foi casado com a
    partida pelo RATING, não pelo K-D, para o degrau 1 não ser circular.
