# Decisão 22k: O Round Swing é variação de probabilidade PURA, sem regra de corte para round perdido

- **ID:** 22k
- **Status:** vigente
- **Data:** 2026-09-19
- **Resumo:** O Swing é variação de probabilidade pura; soma zero é teste de integridade.

## O que vale hoje

A pendência do fim (média ~1,105 e teste `xfail`) foi resolvida pela recalibração da decisão 22l: o teste não tem mais a marca, e a média é 1,0720 contra 1,0726 da HLTV (decisão 26).

## Texto

22k. **O Round Swing é variação de probabilidade PURA, sem regra de corte para
    round perdido** (decisão do Pedro, 2026-09-19). A HLTV escreve que "round
    perdido não gera Swing positivo", mas isso descreve o TIME, não é regra por
    jogador: o time que perde o round soma negativo por construção. Cortar o
    positivo de quem perdeu quebra a soma zero -- medido, deixava a nossa soma em
    -8,7 por partida, e o Swing oficial soma zero em 28 de 31. A soma zero é
    consequência do modelo (toda variação de probabilidade de um processo que
    começa em p e termina em 0 ou 1 se cancela) e vale como TESTE DE INTEGRIDADE
    permanente: `test_swing_soma_zero_por_round_exceto_morte_sem_matador_inimigo`.
    A alternativa (cortar e devolver o corte ao time) foi descartada: exigiria
    escolher para quem e em que proporção -- parâmetro livre sem significado,
    que é o que a decisão 6 chama de chute disfarçado de métrica.
    Junto vieram os três vazamentos do fim do round (perdedor sem ninguém vivo,
    vencedor sem ninguém vivo, eventos com o round já decidido). Antes/depois:
    Swing correlação 0,892 -> 0,904, erro 1,93 -> 1,82 p.p., média -0,81 -> -0,01
    (oficial -0,01), soma zero 0 -> 28 de 31 partidas; rating de teste 0,085 ->
    0,086 (igual, dentro do ruído).
    **PENDÊNCIA REGISTRADA:** a média do rating no corpus está em ~1,105 porque a
    referência de escala e os pesos são anteriores a esta mudança. O conserto é a
    recalibração (passo 7 do plano); até lá
    `test_a_media_do_rating_no_corpus_fica_perto_de_um` está marcado
    `xfail(strict=True)` -- quando voltar a passar, o pytest acusa e obriga a
    tirar a marca.
