# Decisão 54: Enquadramento da Nuke no Replay (Fase B+)

- **ID:** 54
- **Status:** vigente
- **Data:** 2026-11-04
- **Resumo:** Na Nuke, a vista de cada round do Replay tem um quadro por andar, que enquadra tudo o que acontece naquele andar no
  round inteiro (jogadores, granadas, áreas, detonações, kills e bomba). Jogador vivo do outro andar fora do quadro ganha uma marca na
  borda. As outras partidas não mudam.

## Texto

54. **Enquadramento da Nuke** (Fase B+; aprovado pelo Pedro em 2026-11-04 como fase separada da decisão 53).

- **Regra principal:** o enquadramento nunca esconde jogador vivo nem granada. Primeira versão (um quadro com os dois andares juntos)
  deixava o andar de baixo em zoom 1,24 em todos os rounds, porque quem está em cima abre o quadro; o Pedro pediu um quadro por andar
  (2026-11-04), e é este o texto vigente.
- **Um quadro por andar, calculado uma vez por round** sobre todos os quadros do round: nada sai do quadro durante o replay e a vista
  não pula ao tocar nem ao arrastar a barra de tempo. O que muda a vista é só a troca do andar mostrado (botão ou "auto"), que passa
  para o quadro daquele andar. O dado não traz andar em granada, área, detonação, kill e bomba: valem o andar de quem as fez, no instante
  em que as fez (jogador: o andar de cada amostra).
- **Marca na borda** (`desenhaMarcasDeBorda`): jogador vivo do outro andar que o quadro deixou fora da tela ganha um triângulo pequeno na
  borda, com a cor do lado, apontando para onde ele está. Ninguém vivo some sem aviso. Granada de quem está no outro andar que cai fora do
  quadro não ganha marca (só jogador).
- **Conta** (`MapCore.enquadramento`): a caixa dos pontos (x, y, raio), margem de 12% do lado (no mínimo 90 px do radar); abaixo de zoom
  1,1 não mexe na vista (1); no máximo o `ZOOM_MAX`.
- **Quando:** ao trocar de round e ao trocar de andar, só em `de_nuke` (`MAPAS_COM_ENQUADRAMENTO`, `02-replay.js`). O zoom manual vale até
  a próxima troca de round ou de andar; "100%" mostra o mapa inteiro. Reclicar o chip do round reenquadra (pendência 26).
- **Fora:** outros mapas e a prancheta.
