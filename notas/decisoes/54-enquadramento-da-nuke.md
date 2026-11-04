# Decisão 54: Enquadramento da Nuke no Replay (Fase B+)

- **ID:** 54
- **Status:** vigente
- **Data:** 2026-11-04
- **Resumo:** Na Nuke, a vista de cada round do Replay enquadra tudo o que o round mostra (jogadores dos dois andares, granadas, áreas
  de smoke e molotov, em todos os quadros). Nunca esconde jogador vivo nem granada. As outras partidas não mudam.

## Texto

54. **Enquadramento da Nuke** (Fase B+; aprovado pelo Pedro em 2026-11-04 como fase separada da decisão 53).

- **Regra principal:** o enquadramento nunca esconde jogador vivo nem granada. Se alguém sair do quadro, o zoom abre até caber todo
  mundo. Por isso a vista é calculada **uma vez por round**, sobre todos os quadros: nada sai do quadro durante o replay e a vista não pula
  ao tocar, arrastar a barra de tempo ou trocar de andar.
- **Conta** (`MapCore.enquadramento`): a caixa de todos os pontos (x, y, raio) do round, com margem de 12% do lado (no mínimo 90 px do
  radar, para o nome e a linha fina do jogador caberem); abaixo de zoom 1,1 não mexe na vista (fica em 1); no máximo o `ZOOM_MAX`.
  Os dois andares entram juntos: a vista não depende do andar escolhido.
- **Quando:** ao trocar de round (e ao abrir o Replay), só em `de_nuke` (`MAPAS_COM_ENQUADRAMENTO`, `02-replay.js`). O zoom manual da
  pessoa vale até a próxima troca de round; "100%" mostra o mapa inteiro.
- **Medido na partida da Nuke do corpus:** zoom 1,24 nos 17 rounds (o mapa inteiro já é largo: os dois lados têm gente em todo round).
  O "chiefkeef" do round 9 deixou de ficar cortado na borda.
- **Fora:** outros mapas e a prancheta; enquadrar por andar (seria esconder quem está no outro).
