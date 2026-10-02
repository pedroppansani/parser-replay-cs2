# Decisão 22f: O Round Swing soma zero por evento e inclui o fim do round

- **ID:** 22f
- **Status:** vigente
- **Data:** 2026-09-19 (entrada no arquivo; o texto não traz data)
- **Resumo:** O Swing soma zero por evento e inclui o fim do round.

## O que vale hoje

A regra do round perdido citada no fim foi retirada (decisão 22k); a média hoje é -0,01.

## Texto

22f. **O Round Swing soma zero por evento e inclui o fim do round** (Fase D,
    conferido contra o Swing OFICIAL de 310 jogadores em
    `data/reference/hltv_componentes.json`). REGRESSÃO: o matador levava só
    CREDITO_KILL (55%) e a parte sem destinatário (sem dano de outro, sem
    flash, sem trade) sumia -- média -4,67 p.p. contra -0,01 oficial, escala
    0,70. Agora o matador fica com a sobra, e o salto final da chance (do
    último estado a 1 ou 0) vai em partes iguais para quem terminou vivo:
    correlação 0,892, escala 1,01, erro 1,93 p.p. Plantar a bomba como evento
    foi testado e não muda nada (fica de fora). A média ainda sai -0,81 por
    causa da regra do round perdido, que a HLTV declara mas aplica de um jeito
    que fecha em zero; como cada sub-rating é centrado na média do corpus, o
    deslocamento não afeta o rating. Rating: erro de TESTE 0,085, correlação
    0,956, erro por time entre 0,078 e 0,093 nos 6 times grandes.
