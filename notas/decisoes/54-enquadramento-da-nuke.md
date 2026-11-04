# Decisão 54: Enquadramento da Nuke no Replay (Fase B+)

- **ID:** 54
- **Status:** vigente
- **Data:** 2026-11-04
- **Resumo:** Na Nuke, o Replay enquadra a ÁREA de cada andar (o retângulo dos nomes de lugar daquele andar, com margem), com zoom fixo
  por andar e trava de 2,5. Jogador vivo do outro andar fora do quadro vira um triângulo na borda, sem nome. As outras partidas não mudam.

## Texto

54. **Enquadramento da Nuke** (Fase B+; aprovado pelo Pedro em 2026-11-04 como fase separada da decisão 53).

- **Histórico:** a primeira versão enquadrava os pontos do round (zoom de 1 a 5,7, errático, às vezes só a Ramp); a segunda, um quadro por
  andar com os pontos do round, deixava os nomes do outro andar amontoados na borda. O Pedro pediu (2026-11-04) a área do andar. Este é o texto vigente.
- **Quadro = área do andar:** a caixa das âncoras dos nomes de lugar do andar (`RAD.lugares.rotulos[andar]`), com a margem de
  `MapCore.enquadramento` (12% do lado, no mínimo 90 px do radar). Zoom fixo por andar, igual em todos os rounds, travado em 2,5
  (`ENQ_ZOOM_MAXIMO`). Medido na Nuke do corpus: 1,14 em cima e 1,80 embaixo. Conferido: nos 17 rounds, todo ponto de cada andar
  (jogador, granada, área, detonação, kill, bomba) cai dentro do quadro do seu andar (0 fora em 51.486 pontos).
  Granada, área, detonação e kill não trazem andar no dado: valem o andar de quem as fez, no instante em que as fez.
- **Quando:** ao trocar de round e ao trocar de andar (botão ou "auto"), só em `de_nuke` (`MAPAS_COM_ENQUADRAMENTO`, `02-replay.js`). O zoom
  manual vale até lá; "100%" mostra o mapa inteiro. Reclicar o chip do round reenquadra (pendência 26).
- **Outro andar fora do quadro** (`desenhaMarcasDeBorda`): só um triângulo na borda, com a cor do lado, apontando para onde o jogador
  está; sem nome (o nome está nas colunas). Fica a 12 px da borda, dentro do mapa (que termina antes da barra de tocar), e dois perto se
  afastam ao longo da borda sem se sobrepor. Granada de quem está no outro andar fora do quadro não ganha marca (só jogador).
- **Fora:** outros mapas e a prancheta.
