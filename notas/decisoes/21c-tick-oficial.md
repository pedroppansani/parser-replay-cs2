# Decisão 21c: Quando a demo traz o evento `grenade_thrown`, o tick dele É a soltura; a ancoragem vira validação

- **ID:** 21c
- **Status:** vigente
- **Data:** 2026-09-26
- **Resumo:** Com `grenade_thrown`, o tick do evento é a soltura; postura pela altura de saída.

## O que vale hoje

O texto diz que só a match_23 tem o `.dem`. Hoje são 13 partidas com a demo e com as tabelas da rota B no interim (`RECUPERACAO_DEMOS.md`).

## Texto

21c. **Quando a demo traz o evento `grenade_thrown`, o tick dele É a soltura; a
    ancoragem vira validação** (Fase G, 2026-09-26, decisão do Pedro). Roda em
    paralelo e grava `tick_soltura_ancoragem`, `delta_ancoragem_ticks` e
    `fonte_tick`. Medido em 20.863 arremessos de 43 partidas (99,9% casam com o
    evento): o primeiro sample do projétil cai no tick do evento em 100%; a
    ancoragem acerta o tick exato em 39,7%, +-1 em 87,9%, +-4 em 94,8%, com viés
    de +1 (9.353 casos) e cauda até -8.
    Com o tick dado, o deslocamento olhos -> projétil sai POR ARREMESSO
    (`avanco_na_mira`): no tick oficial ele fica todo na direção da mira
    (perpendicular p50 0,01u, p90 0,26u) e cresce com a força (17u a 100 u/s,
    34u a 900 u/s). O offset global transformava isso em resíduo falso (p50
    3,4u, 5,9% marcados "aproximado") e em erro de altura. Com tick oficial,
    `residuo` é o PERPENDICULAR; reprodução exata foi de 94,1% para 99,3%.
    **Altura dos olhos, divergência declarada, NÃO ajustada**: em pé 63,1-63,8u
    no corpus (esperado 64); em match_23, contra a postura real da demo
    (`duck_amount`), 62,6u em pé e 46,1u agachado (esperado 46), diferença 16,5
    contra 18. `ALTURA_OLHOS_EM_PE` e `OFFSET_VERTICAL_SOLTURA` seguem como
    estavam até o Pedro decidir.
    **Postura**: `user_ducking` do evento é a TRANSIÇÃO de agachar (trechos de
    ~12 ticks, sem correlação com a altura: 66,3 x 66,2u), não a postura -- vai
    para a tabela como `em_transicao_de_agachar`, e a postura segue saindo da
    altura. Contra a verdade de match_23 (434 arremessos, 23 agachados), o corte
    de 55u acerta 23/23 agachados mas marca 67 falsos agachados (84,6%); os
    arremessos com duck_amount = 0 têm desvio de 5u e p5 de 51,6u, e a origem
    dessa altura baixa ainda não foi achada. A postura de verdade (`ducked`,
    concorda 100% com duck_amount >= 0,99) existe na demo mas o parser não a
    grava: gravar exige subir `VERSAO_DO_PARSER` e só vale para demos novas.
    **Origem dos falsos agachados, medida com o gabarito da demo (2026-09-27,
    match_23):** o ponto de nascimento desce com o botão (em pé, tirado o avanço
    na direção do lançamento: 62,4 / 55,1 / 50,6u para botão 1 / 0,5 / 0;
    agachado 45,3u; `m_flDuckViewOffset` = -18,00 exato) e, no ar, fica fixo
    sobre o chão da decolagem (decisão 21a). Dos 62 falsos agachados, 29 são
    botão 0,5 ou 0 no chão e 28 são no ar; 5 (chão, botão 1) sem explicação.
    Agachados de verdade marcados: 28 de 29.
    **Cauda vertical da saída (2026-09-27): limitação conhecida, não modelada**
    (seria encaixar um decaimento). A postura passa a sair da ALTURA DE SAÍDA
    corrigida pelo botão (corte 54,43 = meio entre 63,31 e 45,55). A regra da
    decisão 6 pedia neutro "com subida recente e perto do corte", mas no
    gabarito os dois em pé mais perto do corte (+1,12 e +2,23u) NÃO subiram
    (0,8 e 3,9u em 64 ticks): a subida não é o que os aproxima. Proposta
    medida: faixa neutra entre o agachado mais alto (-2,43u) e o em pé mais
    baixo (+1,12u), sem condição de subida -- só os agachamentos parciais
    caem nela (n = 6). No corpus, 98 em pé sem subida e 254 com subida ficam a
    menos de 3u do corte.
    **Faixa de postura final (2026-09-27): por QUANTIL, recalculada a cada
    gabarito novo.** Escolhido o menor quantil com acerto >= 99,5% fora da
    faixa em TODAS as 13 partidas: o 0, faixa [-4,01; +2,10], cobertura 97,9%.
    Três ressalvas registradas: (1) a curva de acerto x quantil NÃO é
    monótona (0: 100%; 0,25: 99,33%; 0,5: 98,70%; ...; 5: 99,67%), sinal de que
    a parametrização por quantil é ruidosa com esta amostra; (2) na prática a
    faixa é o ENVELOPE dos erros observados nas 13 partidas; (3) ela é
    recalculada pela mesma função a cada gabarito novo. A hipótese "subida
    recente" foi testada e NÃO é a causa dos casos de fronteira. Os 6 erros que
    o corte sozinho faria no chão são todos em pé que saem baixos (a cauda da
    posição de saída) e caem na faixa. Anubis: o corte separa bem (em pé mais
    baixo +0,07, agachado mais alto -4,26); a concentração na faixa vem da
    mesma cauda.
