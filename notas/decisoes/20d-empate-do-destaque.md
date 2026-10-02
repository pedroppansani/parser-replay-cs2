# Decisão 20d: No empate do topo, vence o destaque NEGATIVO

- **ID:** 20d
- **Status:** vigente
- **Data:** 2026-09-17 (entrada no arquivo; o texto não traz data)
- **Resumo:** No empate do topo vence o destaque negativo.

## Texto

20d. **No empate do topo, vence o destaque NEGATIVO.** O percentil satura:
    vários candidatos batem em 0,99-1,00 e a pontuação perde resolução
    justamente no topo. Medido: o match_03 tinha um bottom frag em 1,00 empatado
    com um repick em 1,00, e vencia quem tivesse sido inserido antes na lista --
    acidente, não critério. O desempate é explícito e prefere o negativo, porque
    o card da esquerda já é um destaque positivo: um segundo positivo repete o
    tipo de informação, um negativo acrescenta. **Isso não afrouxa trava
    nenhuma** -- o negativo continua tendo que passar pela distância do bottom
    frag, pela vitória da mochila e pela evidência com número.

    Registro de um diagnóstico errado meu: antes de olhar os candidatos, a
    recomendação foi afrouxar `MIN_DISPERSOES_BOTTOM_FRAG` para fazer o card
    negativo aparecer. Era errado -- os negativos já competiam e já venciam
    empates; o defeito estava na ordenação.
