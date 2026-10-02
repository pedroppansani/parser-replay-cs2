# Decisão 22h: O Swing OFICIAL soma zero -- confirmado, não suposto

- **ID:** 22h
- **Status:** vigente
- **Data:** 2026-09-19 (entrada no arquivo; o texto não traz data)
- **Resumo:** O Swing oficial soma zero; as exceções são mortes sem matador inimigo.

## O que vale hoje

A correção que "esperava a decisão do Pedro" foi feita na decisão 22k (sem a regra de corte).

## Texto

22h. **O Swing OFICIAL soma zero -- confirmado, não suposto.** Nos 310 Swings
    oficiais, a soma dos 10 de uma partida dá zero (dentro do arredondamento) em
    28 de 31, e as três exceções são exatamente as partidas com uma morte DENTRO
    do round sem matador inimigo (fogo amigo do FalleN e do molodoy no KSCERATO,
    queda do TeSeS): a vítima paga e ninguém recebe. Morte pela bomba e morte
    depois do fim do round somam zero -- o round já estava decidido. Nosso código
    faz o mesmo com fogo amigo (match_43: -0,54 nosso, -0,54 oficial). Isto
    REFUTA a regra do round perdido aplicada como corte: cortar o positivo de
    quem perdeu deixa a soma negativa em TODA partida (a nossa: mediana -8,7 por
    partida). Nosso Swing ainda vaza em três pontos, medidos: perdedor sem
    ninguém vivo no fim (o salto final não é debitado de ninguém), vencedor sem
    ninguém vivo (bomba explodindo com o TR todo morto: os CTs pagam e ninguém
    recebe), e eventos com o round já decidido (morte pela bomba, cauda). Com os
    três fechados a soma zera em 28 de 31, as mesmas três do oficial, e o erro
    por time cai de 4,89 para 3,29 p.p. A correção no código ESPERA a decisão do
    Pedro sobre como fica a regra do round perdido (sem a regra ou devolvendo o
    corte ao próprio time -- os dados não separam as duas).
