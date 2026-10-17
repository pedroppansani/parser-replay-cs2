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

## Resposta do Pedro ao material de calibração (registrada em 2026-10-17)

Corpus: 52 partidas, 520 jogador-partidas (43 profissionais). Os pisos viraram constantes no topo de
`metrics/player_roles.py` (`PISO_AWPER`, `PISO_ABRE_O_ROUND`, `PISO_ANCORA`, `PISO_SEGUNDO_HOMEM`,
`PISO_PRINCIPAL_FRAGGER`, com `DATA_DOS_PISOS`, `PARTIDAS_DOS_PISOS` e `JOGADOR_PARTIDAS_DOS_PISOS`).
Versão das métricas 27.

| função | resposta | piso |
|---|---|---|
| AWPer | 0,333 só se o `awp_share` fosse "AWP na mão / todos os rounds" | **0,533 mantido** (ver abaixo) |
| Abre o round | fica | 0,320 |
| Suporte de utility | testar 30 s; se sh1ro, w0nderful ou donk ficarem acima, 40 s | **sem mudança: parada** (ver abaixo) |
| Lurker | fica, e não vale para quem tem "Abre o round" na mesma partida | 1,284 |
| Âncora de bomb | sobe | 0,90 |
| Segundo homem | fica | 0,350 |
| Principal fragger | fica | 85 |

**O que o `awp_share` mede:** dos rounds em que o TIME teve AWP, a fração em que ela era dele
(`awp_do_time`). O round sem dinheiro para AWP já sai do denominador, que era o motivo do 1/3. Nessa
definição, um líder com 1/3 divide a AWP com mais dois, então o piso fica 0,533. Efeito zero
nos dois casos: o menor líder com amostra tem 0,556. Os mais perto do corte, acima: lilpeepfan- e
newnickname7 (0,556, FACEIT), 9amaterasu9 (0,600), m0NESY (0,727, match_30) e Z_o_R_o (0,778).
Abaixo, nenhum líder com amostra. O não líder mais alto é o FalleN (0,600, 12 de 20).

**Suporte: parada.** Em 30 s (1,429 s por round), sh1ro (match_38), w0nderful (match_10 e match_25) e
donk (match_04, 05 e 07, FACEIT) ficam acima. Em 40 s (1,905 s por round) ficam sh1ro (match_38, 2,17),
w0nderful (match_25, 2,54) e donk (match_05, 2,46, FACEIT). O donk profissional (match_40, 0,81) já
fica abaixo de 20 s. O piso continua 20/21 até a resposta do Pedro. Fronteira em 40 s: acima, mezii
1,909, FalleN 1,982, apEX 1,998, xertioN 2,076 e torzsi 2,085. Abaixo, chopper 1,894, FalleN 1,871,
YEKINDAR 1,819, w0nderful 1,805 e chopper 1,773.

**Âncora em 0,90:** mais perto acima, Brollan 0,900, Aleksib 0,909, TeSeS 0,909, HLEB 0,917 e Alperen
0,917. Abaixo, nedorufe, donk, jL e Brollan com 0,889 (8 de 9) e FalleN 0,882.

**Regras novas** (`metrics/player_roles.py`, teste `tests/test_pisos_de_funcao.py`):
- O Lurker não vale para quem tem "Abre o round" na mesma partida (`EXCLUSOES`). Vale no dado
  (`player_traits`) e também em cada reamostragem da estabilidade.
- Título do cartão (`ordem_na_tela`): o AWPer sempre ganha. Sem AWPer, ganha a maior margem
  valor ÷ piso. No empate, a prioridade. Os outros rótulos ficam no dado e aparecem como
  características, na mesma ordem (`player_traits.ordem`). Antes, o título era o de menor
  prioridade, e as características vinham por prioridade.

**Efeito nas 52** (rótulos; entre parênteses, os títulos):

| rótulo | antes | depois |
|---|---|---|
| AWPer | 94 (94) | 94 (94) |
| Abre o round | 50 (43) | 50 (26) |
| Suporte de utility | 99 (72) | 99 (78) |
| Lurker | 56 (34) | 46 (38) |
| Âncora de bomb | 121 (73) | 79 (48) |
| Segundo homem | 39 (20) | 39 (24) |
| Principal fragger | 83 (25) | 83 (38) |
| sem função dominante | (159) | (174) |

Mudam 50 títulos. Saem 10 Lurkers por terem "Abre o round" (ropz três vezes, YEKINDAR, kyxsan, iM,
magixx, ZywOo, Brollan e flameZ).

**Parada: a `jogadores.html` muda números.** A função do jogador no corpus é o título mais frequente
(`agregado_jogadores.funcao_por_jogador`), e o número exibido é puxado para a média dessa função
(opção padrão "a média da função de cada um"). Quinze jogadores mudam de função no corpus. Com isso,
3.187 dos 5.120 números exibidos mudam (97 jogadores), entre eles rating e ADR: o rating do Alperen
passa de 1,00 para 0,82. O dado embutido (linhas, k) é idêntico, e na opção "a média do corpus" nada
muda. A decisão é do Pedro.

As respostas da seção 7 (erros) ficam para o item 3 (nota 46).
