# Decisão 19b: Partida sem round decisivo é RESULTADO, não lacuna

- **ID:** 19b
- **Status:** vigente
- **Data:** 2026-09-17 (entrada no arquivo; o texto não traz data)
- **Resumo:** Partida sem round decisivo é resultado; piso de 1,5× o round mais barato.

## Texto

19b. **Partida sem round decisivo é RESULTADO, não lacuna.** Numa partida de
    placar largo a diferença se construiu ao longo do jogo, e eleger um round à
    força inventa uma virada que não houve — era o que a soma de pontos fazia,
    porque sempre existe um máximo. O piso não é número solto: é 1,5x o round
    mais barato possível daquele formato (`P(1,0) - P(0,0)`, 0,081 no MR12), o
    mesmo fator com que o projeto ancora o piso de entry ao acaso. Medido: ficam
    sem round decisivo exatamente as 5 partidas de placar largo (13-5, 13-6,
    13-7, 13-8, 4-13) e ficam com as 4 apertadas (dois 13-9, dois 11-13). A
    interface renderiza esse caso com frase própria, não com card vazio.
