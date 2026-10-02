# Decisão 22a: O Round Swing usa MODELO PARAMÉTRICO, não contagem por estado

- **ID:** 22a
- **Status:** vigente
- **Data:** 2026-09-17 (entrada no arquivo; o texto não traz data)
- **Resumo:** O Round Swing usa regressão logística, não contagem por estado.

## O que vale hoje

AUC 0,897 e Brier 0,129 são do corpus de 9 partidas. O modelo atual está em `metrics/rating_reference.json` (`modelo_de_round`).

## Texto

22a. **O Round Swing usa MODELO PARAMÉTRICO, não contagem por estado.** O espaço
    de estados (vivos x vivos x bomba x equipamento x lado) tem centenas de
    combinações e o corpus tem ~200 rounds por partida: frequência empírica por
    estado daria "100% de vitória" a partir de dois casos. Uma regressão
    logística com quatro entradas generaliza e nunca devolve certeza absoluta.
    Medido nas 9 partidas: AUC 0,897 e Brier 0,129 sobre 2.692 amostras.

    **A qualidade do Round Swing depende do tamanho do corpus e melhora a cada
    demo processada.** O desempenho é reportado no resumo de propósito, para não
    virar fé.

    Registro de um bug de modelagem: cada evento gera DUAS linhas, uma por lado,
    com rótulos opostos. Com a bomba entrando como flag `plantada` (1 nas duas),
    ela ficava perfeitamente não-informativa por construção e o coeficiente saiu
    em -0,0001. Bomba plantada é vantagem de quem plantou, então ela entra COM
    SINAL: +1 para o TR, -1 para o CT. Com o sinal, o coeficiente é +0,71.
