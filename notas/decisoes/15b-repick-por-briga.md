# Decisão 15b: Repick classifica CADA briga, e a junção é pelo tick da briga

- **ID:** 15b
- **Status:** vigente
- **Data:** 2026-09-19 (entrada no arquivo; o texto não traz data)
- **Resumo:** Repick classifica cada briga; a junção inclui o tick da briga.

## Texto

15b. **Repick classifica CADA briga, e a junção é pelo tick da briga.**
    REGRESSÃO: `awp_metrics.classify_engagement_style` foi escrito para a
    primeira briga de AWP (uma por jogador e round) e juntava o resultado por
    (round, jogador). O repick o reusa para todas as brigas, e as k brigas de um
    jogador no round cruzavam com os k estilos dele (k² linhas: 916 em vez de
    480 numa partida), ponderando o `repick_share` errado. A chave agora inclui
    `engagement_tick`. Junto: `scripts/fit_archetype_reference.py` lia o
    interim CRU (sem o filtro de kills do round jogado, sem a correção de dano,
    sem a cegueira) e passou a usar `load_interim` -- a referência era ajustada
    sobre um dado diferente do que ela depois escala.
    Os 10 casos de `scripts/casos_repick.py` mostram 9 com UMA saída e volta só:
    a métrica pega um jiggle, não necessariamente o "fica repickando" repetido.
    Se exige 2+ saídas, é decisão do Pedro.
