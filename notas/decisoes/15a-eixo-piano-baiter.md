# Decisão 15a: Carrega piano e baiter são as duas pontas de UM eixo

- **ID:** 15a
- **Status:** vigente
- **Data:** 2026-09-19 (entrada no arquivo; o texto não traz data)
- **Resumo:** Carrega piano e baiter são as pontas de um eixo; rótulo só além de ±0,5.

## Texto

15a. **Carrega piano e baiter são as duas pontas de UM eixo** (`sacrifice_index`
    em `metrics/archetypes.py`): percentil dos rounds em que ele pagou a conta E
    o time colheu, menos o percentil das mortes de companheiro por perto sem
    troca. De -1 a +1; rótulo só além de `PISO_CARREGA_PIANO` (0,5) ou
    `PISO_BAITER` (-0,5), então os dois nunca caem no mesmo jogador -- por
    construção, não por desempate. "O time colheu" é igual nas três formas:
    venceu o round, vingou a morte dele, OU matou alguém que ele cegou (a flash
    entrou aqui; antes o piano não usava flash). O retorno é o que separa
    carrega piano de jogador ruim, e isso foi medido: pagar a conta SEM retorno
    correlaciona -0,31 com o rating, COM retorno -0,05. A flash como único
    retorno é rara (43 de 2.308 rounds). Achado para o Pedro julgar: a ponta do
    baiter tem rating médio 1,15 contra 1,05 do meio -- "usa o time de isca
    para conseguir kills" pega muito astro que joga de segundo.
