# O grupo de ~784 u/s e o jump-throw

- **Data:** 2026-09-27
- **Decisão:** [21a](../decisoes/21a-arremesso.md)
- **Resumo:** De onde vem o grupo extra de velocidade: a soltura no ar herda a velocidade vertical da decolagem menos 0,1 s de gravidade, não a do instante.

> Narrativa da investigação, como foi registrada na época. A regra que vale hoje está na decisão.

**Investigação do grupo de ~784 u/s (2026-09-27, item 7 (b)).** A
    velocidade da ficha JÁ é relativa (vetorial, com a vertical). Por
    movimento: parado, andando e correndo saem em exatamente 3 grupos (99,0 a
    99,8% perto de 198/443/675); só "no ar" não fecha (91,9%, 7 grupos). Contra
    um controle do mesmo tamanho, o grupo de 784 (126 arremessos) é 71%
    AGACHADO (controle 29%), com vz do jogador concentrada em 122-133 u/s e a
    parábola quebrando 11-12 ticks antes da soltura. H1 (soltura no tick da
    decolagem) REFUTADA: 12% a 0-1 tick nos dois. H2 (soltura errada) REFUTADA:
    resíduo 0,0u nos dois, tick oficial em 94%. O grupo não é um tipo à parte:
    entre os 1.091 arremessos agachados a 11-13 ticks, só 12,7% chegam a 784
    (mediana 714, contra 681 do controle) -- é a cauda de um desvio do
    arremesso AGACHADO NO AR -- leitura que as propriedades da demo
    DERRUBARAM no mesmo dia (abaixo).
    **Causa achada com as propriedades da demo (2026-09-27, só match_23 tem o
    .dem; `scripts/investiga_props_arremesso.py`).** O projétil grava
    `m_vInitialVelocity` e `m_vInitialPosition` (o gabarito), a arma grava
    `m_flThrowStrength` (0 / 0,5 / 1: o BOTÃO) e o jogador grava duck_amount,
    `m_hGroundEntity`, `m_nLastJumpTick` (= 2·tick + constante da demo) e
    `m_flLastJumpVelocityZ`; a velocidade do jogador NÃO é gravada
    (`velocity_X/Y/Z` do demoparser é diferença de posição). Medido nos 434
    arremessos:
    - no chão, |v0 - 1,25·vj| por botão gravado: 202,5 / 438,7 / 675,0, IQR
      abaixo de 1 u/s; a direção do lançamento é a mira com o pitch remapeado
      para -10 + pitch·80/90 (resíduo mediano 0,0°);
    - **no ar depois de um pulo, o jogo NÃO herda a vz do instante: herda a vz
      de decolagem gravada menos 0,1 s de gravidade** (298,87 - 80 = 218,87;
      vz usada menos essa conta: 0,0 [-0,1; 0,0] em 95 de 95), seja qual for o
      tick da soltura (6 a 13 depois do pulo). Com essa vz a herança é 1,25
      também na vertical (kv 1,249 [1,246; 1,250]; kh 1,250), sem fator novo.
      Quanto mais tarde no pulo, mais a vz real fica abaixo de 218,87 e mais a
      velocidade relativa da produção passa de 675: o grupo de ~784 é soltar
      12-13 ticks depois do pulo (os 12 da match_23 são todos botão 1 e em pé,
      duck 0). Os 9 "no ar" que a demo dá como no CHÃO (escada, rampa) herdam
      vz 0;
    - a posição segue a mesma regra: no ar, a altura do nascimento é FIXA sobre
      o chão da decolagem (91,6u [90,7; 92,7], de 90 a 92 do tick 6 ao 13),
      enquanto a altura sobre os pés na soltura cai de 65 para 47u. Era isso
      que fazia o grupo parecer agachado: a altura medida sobre os pés no fim
      do pulo cai abaixo do corte de 55u.
    Aplicada SÓ COM POSIÇÃO no corpus inteiro (parábola de queda livre na
    soltura -> vz 218,87; senão 0), a regra leva o "no ar" de 91,9% para
    **98,3%** dentro dos três grupos (todos: 97,8% -> 99,3%), e os grupos no ar
    passam de 7 para 202/436/673 mais um resto de 53 perto de 818. Os 97 que
    sobram (1,7% do "no ar") não seguem regra única e ficam com rótulo neutro.
    **NADA APLICADO**: é proposta ao Pedro (versão das métricas, sem parser).
