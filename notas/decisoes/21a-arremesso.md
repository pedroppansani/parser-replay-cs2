# Decisão 21a: A força do arremesso é inferida da velocidade RELATIVA ao jogador

- **ID:** 21a
- **Status:** vigente
- **Data:** 2026-09-26
- **Resumo:** Botão, "no ar" e postura: lidos da demo onde há `.dem`, inferidos pela rotina do jogo onde não há.

## Regra em vigor

- **Fonte por campo.** Botão, postura, "no ar" e ponto de saída de cada arremesso declaram a fonte:
  `lido` (a demo grava, nas partidas com `.dem` e parser 2) ou `inferido` (a rotina do jogo medida no
  gabarito, nas demais). Nunca se misturam em silêncio.
- **Inferido (rota A).** Velocidade relativa ao jogador com herança 1,25; três botões (202,5 / 438,7 /
  675,0 u/s); pitch remapeado por trechos; no pulo, vz fixa de 6 a 13 ticks depois da decolagem e vz real
  de 19 em diante; estado vertical ambíguo, janelas sem gabarito, vetor incoerente com o voo e velocidade
  fora da tolerância ficam NEUTROS, com o motivo. Tolerância, guarda do voo e faixa de postura são
  calculadas do gabarito (`metrics/gabarito_constantes.json`), nunca digitadas.
- **Lido (rota B).** A força é a da granada que saiu (último tick gravado antes do nascimento do
  projétil), nunca a da arma no tick da soltura. Botão = o mais próximo da força lida; agachamento
  parcial não é afirmado.
- **Piora.** Um arremesso que tinha botão dentro da tolerância e troca de botão, ou fica neutro sem
  regra explícita. Mudança na biblioteca só entra com piora 0 (`py -3.12 -m pesquisa.piora_rota_a`).
- **Teste permanente.** Lido contra inferido nas partidas com demo, nas metas da rota A
  (`tests/test_verdade_do_arremesso.py`).
- **Demos sem `grenade_thrown` (FACEIT).** O tick ainda vem da ancoragem; a regra do tick pelo projétil
  está pronta e DESLIGADA (`TICK_PELO_PROJETIL_SEM_EVENTO`), à espera do Pedro.

Os números atuais (metas dentro e fora da amostra, cobertura) estão em
`data/processed/numeros_citaveis.json`, bloco `arremessos`.

## Como se chegou aqui

- [O grupo de ~784 u/s e o jump-throw](../investigacoes/2026-09-27-grupo-de-784-e-jump-throw.md): De onde vem o grupo extra de velocidade: a soltura no ar herda a velocidade vertical da decolagem menos 0,1 s de gravidade, não a do instante.
- [Rota A: inferir botão, "no ar" e postura pela rotina do jogo](../investigacoes/2026-09-27-rota-a.md): Do protótipo ao main: metas, a cauda vertical, a obstrução refutada, a janela do jump-throw, a definição de piora, a validação fora da amostra, a guarda do voo e o estado final.
- [Rota B: a verdade do arremesso lida da demo](../investigacoes/2026-09-28-rota-b.md): O parser 2 grava a força, a velocidade e o ponto de nascimento de cada granada e o movimento do jogador; lido contra inferido é o teste permanente da rota A.
- [FACEIT: o tick da soltura pelo projétil](../investigacoes/2026-10-02-faceit-tick-pelo-projetil.md): Sem `grenade_thrown`, a ancoragem acerta o tick em 41%; o evento é reconstruível do projétil. Regra pronta e desligada à espera de aprovação.

## Texto original (a parte que define a regra de base)

21a. **A força do arremesso é inferida da velocidade RELATIVA ao jogador.** Sem
    descontar a velocidade de quem arremessou, todo run-throw curto vira
    arremesso longo. O desconto é vetorial (projetar o módulo na direção da
    granada superestima quem corria de lado) e usa `FATOR_HERANCA = 1,25`,
    medido: a inclinação de (v_relativa ~ v_jogador) cruza zero em 1,250 e o IQR
    do grupo dominante é mínimo no mesmo ponto. Dois critérios independentes
    coincidindo num 1,25 redondo dizem que é constante do jogo. Efeito: parado x
    correndo saiu de 674 x 727 u/s para 672,0 x 672,7.

    Os três grupos saem por moda (decisão 5, nada de bin fixo): 201, 440 e 674
    u/s. **Rótulos confirmados pelo Pedro em 2026-09-26: curto/médio/longo pela
    ordem** (`FORCA_CONFIRMADA = True`). Só se aplicam com exatamente três
    grupos; com outro número o rótulo continua neutro ("força A/B/...").
    Com tick oficial, no corpus de 43 partidas: 203 (868), 444 (957) e 677
    (18.764) u/s, mais quatro grupos pequenos que passam do mínimo absoluto de
    20 (331: 33, 608: 65, 788: 137, 916: 23) -- no corpus inteiro saem 7 grupos
    e o rótulo fica neutro; por partida saem 1 a 3 grupos (3 em 10 das 43).
    Pendente do Pedro: mínimo por grupo relativo ao tamanho da amostra, ou
    rotular pelo centro mais próximo dos três confirmados.
    O grupo extra mais frequente (730-800 u/s, 412 arremessos no corpus) é o
    JUMP-THROW: 97% saem no ar, 69% com o jogador parado na horizontal, pitch
    mediano -29° (contra -8° do cheio). É categoria real de jogo, não ruído; o
    desconto da velocidade vertical do pulo não o traz de volta ao grupo cheio.
    Nomear/separar (pela flag `no_ar` em vez da velocidade) é do Pedro.
