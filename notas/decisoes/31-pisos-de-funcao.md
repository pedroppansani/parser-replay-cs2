# Decisão 31: Registro dos pisos de função

- **ID:** 31
- **Status:** vigente
- **Data:** 2026-09-26
- **Resumo:** Registro dos pisos de função e de onde veio cada um.

## Texto

31. **Registro dos pisos de função** (`metrics/player_roles.py`, TRAIT_SPECS;
    revisão do Pedro em 2026-09-26 sobre 52 partidas, 430 jogador-partidas
    profissionais em 43 partidas, via `pesquisa/proposta_pisos.py`):
    | função | piso | origem |
    |---|---|---|
    | AWPer (`awp_share`) | 0,533 | corte estatístico (os três métodos concordam) |
    | Lurker (`off_team_relativo`) | 1,284 | corte estatístico (vazio e Otsu entre líderes) |
    | Abre o round (`first_contact_share`) | 0,320 | convenção validada pela fronteira |
    | Suporte de utility (`enemy_blind_seconds`) | 20,0 | convenção validada pela fronteira |
    | Âncora de bomb | 0,800 | convenção validada pela fronteira |
    | Segundo homem (`trade_share`) | 0,350 | convenção validada pela fronteira |
    | Principal fragger (`adr`) | 85,0 | convenção validada pela fronteira |
    "Validada pela fronteira" = os métodos não concordam, e o Pedro conferiu os
    jogadores dos dois lados do corte: ZywOo fora do entry nas duas partidas
    (0,316-0,318); sh1ro e chopper acima do suporte, apEX (13,6) longe abaixo;
    FalleN acima da âncora; ropz e KSCERATO acima do segundo homem, donk fora.
    **Fronteira mais apertada das cinco**: YEKINDAR fica fora do principal
    fragger por 0,1 de ADR (84,9, match_44) -- ruído puro, mas não é evidência
    para mover um piso que é convenção.
    O Lurker é medido por `off_team_relativo` (decisão 29), que SUBSTITUIU a
    taxa absoluta `off_team_share` (escala 0-1, piso antigo 0,40) como métrica
    que define o rótulo; a taxa absoluta continua na tabela só como informação.

## Resposta do Pedro ao material de calibração (registrada em 2026-10-17; paradas respondidas em 2026-10-24)

Corpus: 52 partidas e 520 jogador-partidas, das quais 43 partidas profissionais. Os pisos viraram
constantes no topo de `metrics/player_roles.py`: `PISO_AWPER`, `PISO_ABRE_O_ROUND`,
`PISO_SUPORTE_SEGUNDOS`, `PISO_ANCORA`, `PISO_SEGUNDO_HOMEM` e `PISO_PRINCIPAL_FRAGGER`. A data e o
corpus estão em `DATA_DOS_PISOS`, `PARTIDAS_DOS_PISOS` e `JOGADOR_PARTIDAS_DOS_PISOS`. Versão das
métricas: 28.

| função | resposta | piso |
|---|---|---|
| AWPer | 0,333 só se o `awp_share` fosse "AWP na mão / todos os rounds" | **0,533, mantido** (ver abaixo) |
| Abre o round | fica | 0,320 |
| Suporte de utility | testar 30 s; com sh1ro, w0nderful ou donk acima, usar 40 s | **40 s** (40/21 = 1,905 s por round) |
| Lurker | fica, mas não vale para quem tem "Abre o round" na mesma partida | 1,284 |
| Âncora de bomb | sobe | 0,90 |
| Segundo homem | fica | 0,350 |
| Principal fragger | fica | 85 |

**O que o `awp_share` mede:** dos rounds em que o TIME teve AWP, em quantos a AWP era dele
(`awp_do_time`). O round sem dinheiro para AWP já sai do denominador, e era esse o motivo do 1/3.
Nessa definição, um líder com 1/3 divide a AWP com mais dois, então o piso fica em 0,533. Nos dois
pisos o efeito é zero: o menor líder com amostra tem 0,556.

Os mais perto do corte, acima: lilpeepfan- e newnickname7 (0,556, FACEIT), 9amaterasu9 (0,600),
m0NESY (0,727, match_30) e Z_o_R_o (0,778). Abaixo não há nenhum líder com amostra; o não líder
mais alto é o FalleN (0,600, 12 de 20).

**Suporte em 40 s.** Com 30 s (1,429 s por round), ficavam acima sh1ro (match_38), w0nderful
(match_10 e match_25) e donk (match_04, match_05 e match_07, FACEIT). Com 40 s ainda ficam acima:
- sh1ro, match_38: 2,17 s por round;
- w0nderful, match_25: 2,54 s por round;
- donk, match_05: 2,46 s por round (FACEIT).

O Pedro aceitou (2026-10-24). Na tela, o AWPer aparece como AWPer, pela prioridade de exibição. O
suporte do donk numa partida é aceito, como foi aceito o do ZywOo. Na match_05, o título do donk é
"Principal fragger".

Fronteira em 40 s, registrada a pedido:
- acima: mezii 1,909, FalleN 1,982, apEX 1,998, xertioN 2,076 e torzsi 2,085;
- abaixo: chopper 1,894, FalleN 1,871, YEKINDAR 1,819, w0nderful 1,805 e chopper 1,773.

**Âncora em 0,90.** Os mais perto do corte:
- acima: Brollan 0,900, Aleksib 0,909, TeSeS 0,909, HLEB 0,917 e Alperen 0,917;
- abaixo: nedorufe, donk, jL e Brollan com 0,889 (8 de 9), e FalleN com 0,882.

**Regras novas** (`metrics/player_roles.py`; teste em `tests/test_pisos_de_funcao.py`):
- O Lurker não vale para quem tem "Abre o round" na mesma partida (`EXCLUSOES`). A regra vale no dado
  (`player_traits`) e também em cada reamostragem da estabilidade.
- O título do cartão sai de `ordem_na_tela`:
  - o AWPer sempre ganha;
  - sem AWPer, ganha a maior margem valor ÷ piso;
  - no empate, decide a prioridade.

  Os outros rótulos ficam no dado e aparecem como características, na mesma ordem
  (`player_traits.ordem`). Antes, o título era o rótulo de menor prioridade, e as características
  vinham por prioridade.

**Efeito nas 52.** Contagem de rótulos de líderes; entre parênteses, quantas vezes cada rótulo é o
título:

| rótulo | antes | depois |
|---|---|---|
| AWPer | 94 (94) | 94 (94) |
| Abre o round | 50 (43) | 50 (27) |
| Suporte de utility | 99 (72) | 76 (57) |
| Lurker | 56 (34) | 46 (43) |
| Âncora de bomb | 121 (73) | 79 (50) |
| Segundo homem | 39 (20) | 39 (24) |
| Principal fragger | 83 (25) | 83 (43) |
| sem função dominante | (159) | (182) |

Mudam 68 títulos. Saem 10 Lurkers por terem "Abre o round": ropz (três vezes), YEKINDAR, kyxsan,
iM, magixx, ZywOo, Brollan e flameZ.

**A `jogadores.html` muda os números exibidos. Decisão técnica de 2026-10-24: aceito.** Na página,
a função do jogador no corpus é o título mais frequente dele (`agregado_jogadores.funcao_por_jogador`).
Na opção padrão ("a média da função de cada um"), o número exibido é puxado para a média dessa
função. Os rótulos de função estavam autorizados a mudar, e a mudança dos números exibidos é
consequência direta disso; o dado embutido na página (linhas e k) não muda.

Mudam de função no corpus 21 jogadores:

| jogador | antes | depois |
|---|---|---|
| -EsD | Suporte de utility | Lurker |
| Alperen | Abre o round | Suporte de utility |
| b1t | Âncora de bomb | Principal fragger |
| bezimienny | Âncora de bomb | Segundo homem |
| bLitz | Abre o round | Suporte de utility |
| borzSE | Suporte de utility | sem função dominante |
| chopper | Suporte de utility | Lurker |
| Dafra1D | Suporte de utility | sem função dominante |
| donk | Abre o round | Principal fragger |
| hally- | Suporte de utility | Lurker |
| HLEB | Âncora de bomb | Segundo homem |
| Jimpphat | Âncora de bomb | Segundo homem |
| jL | Âncora de bomb | Principal fragger |
| llorente | Suporte de utility | Lurker |
| Magnojezzz | Suporte de utility | Principal fragger |
| nedorufe | Âncora de bomb | sem função dominante |
| pxd11 | Âncora de bomb | Principal fragger |
| R0Kk-_ | Âncora de bomb | sem função dominante |
| tezeuts- | Âncora de bomb | sem função dominante |
| Unihi | Suporte de utility | Principal fragger |
| zont1x | Âncora de bomb | Abre o round |

São 21, e não os 15 da primeira medição, porque ela foi feita com o suporte ainda em 20 s.

Efeito na página: mudam 3.316 dos 5.120 números exibidos, em 97 jogadores, inclusive rating e ADR.
Exemplo: o rating do Alperen passa de 1,00 para 0,83, porque a média da função dele passa de 1,18
para 0,94. Na opção "a média do corpus", nada muda.

