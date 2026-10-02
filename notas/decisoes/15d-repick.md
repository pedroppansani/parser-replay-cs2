# Decisão 15d: Repick é jiggle MAIS evento no ângulo

- **ID:** 15d
- **Status:** vigente
- **Data:** 2026-09-19 (entrada no arquivo; o texto não traz data)
- **Resumo:** Repick é jiggle mais evento no ângulo; o desfecho é campo à parte.

## Texto

15d. **Repick é jiggle MAIS evento no ângulo.** Sair e voltar sozinho é jiggle
    (decisão 1), não repick: dos 10 casos conferidos pelo Pedro, 9 eram uma
    saída e volta sem nada no meio. O critério agora exige que entre a saída e a
    volta tenha acontecido algo naquele ângulo -- ele atirou, causou ou sofreu
    dano, ou alguém morreu a menos de `BAIT_MAX_DISTANCE` dele. Uma saída só
    basta quando houve evento (é o refrag depois da morte do companheiro), e dez
    saídas não bastam sem evento. O NÚMERO de saídas vira sinal de qualidade
    (`saidas`), não critério.
    O DESFECHO é campo separado (`desfecho`: ganhou o duelo, perdeu o duelo,
    morreu para utility, nada) e NÃO entra na identificação: a causa da morte é
    resultado, e morrer para uma HE não desfaz o repick que aconteceu antes.
    Morte para utility é categoria própria e fica fora de qualquer taxa de duelo.
