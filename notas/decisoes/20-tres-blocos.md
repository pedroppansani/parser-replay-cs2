# Decisão 20: A aba de leitura tem estrutura FIXA de três blocos

- **ID:** 20
- **Status:** vigente
- **Data:** 2026-09-17 (entrada no arquivo; o texto não traz data)
- **Resumo:** A aba de leitura tem três blocos fixos; o MVP é o maior rating, com empate dentro do erro.

## O que vale hoje

**MVP = maior rating da partida** (auditoria, item 4.6, 2026-10-02; `metrics/match_highlights.py`).
O índice com pesos sem origem (40% ADR, 30% KAST, 20% aberturas, 10% clutches) saiu: o MVP
divergia do maior rating em 18 das 52 partidas. Casado por steamid; a landing usa o MVP do card.
Quem fica a menos do erro do rating fora da amostra (`metrics/rating_validacao.json`, deixa uma
partida fora: 0,0788) está empatado, e a frase declara o empate. Sem rating (modo degradado), não
há MVP. Os componentes continuam no card como evidência, sem peso. Medido: o MVP muda em 17 das
52 partidas, 12 com empate declarado; o card de destaque muda em 6.

## Texto

20. **A aba de leitura tem estrutura FIXA de três blocos:** round decisivo em
    cima, MVP embaixo à esquerda, outro destaque embaixo à direita. Estrutura
    fixa é o que torna duas partidas comparáveis de relance -- se o layout
    mudasse conforme o que a partida teve, cada página ensinaria a ser lida de
    novo. O gráfico de probabilidade de vitória saiu daqui e vive só na aba
    Placar: a mesma informação duas vezes na mesma página só gasta espaço.

    O card do MVP mostra os COMPONENTES e não só o índice, cada um com o melhor
    valor entre os outros jogadores ao lado ("126,1 de ADR contra 107,3 de
    s-chilla"). Índice agregado sozinho não deixa conferir nada.
