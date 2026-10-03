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

## Estado completo (2026-10-02, auditoria 4.3)

O modelo passou de quatro entradas para o **estado completo** (`metrics/rating.py`,
`MODELO_DE_ROUND_COMPLETO = True`): além da diferença de vivos, equipamento, bomba com sinal e
lado, entram a razão de vivos, a eliminação de um lado, o tempo do round e o tempo da bomba.

As duas condições do Pedro para adotar:

1. Fora da dobra, agrupado por partida (`scripts/valida_modelo_de_round.py`): Brier 0,1287 →
   0,1245, AUC 0,900 → 0,907; o 1v0 deixa de ser previsto em 74% (vence 94%).
2. Erro do rating contra a HLTV no "deixa uma partida fora" completo (`scripts/valida_rating.py`,
   modelo de round, economia, referência e pesos refeitos por dobra) não piora mais que +0,001:

| validação (430 jogador-partidas) | quatro entradas | completo |
|---|---|---|
| só os pesos | 0,0812 (corr 0,9635) | 0,0789 (corr 0,9656) |
| deixa uma partida fora, completo | 0,0810 (corr 0,9637) | **0,0788** (corr 0,9658) |
| deixa um time fora, completo | 0,0816 (corr 0,9629) | 0,0793 (corr 0,9652) |

Melhorou 0,0022: adotado. Referência de escala e pesos reajustados com o modelo novo, corpus
reprocessado, catraca regravada em commit próprio com os dois números.
