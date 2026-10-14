# Decisão 45: Granada desenhada é desenho, não evento: tracejada, sem horário, convertível

- **ID:** 45
- **Status:** vigente
- **Data:** 2026-10-13
- **Resumo:** Smoke, flash, HE e molotov podem ser carimbadas como desenho no "Desenhar" do replay e nos pincéis da prancheta. Mesmo glifo das granadas reais, com o anel duplo tracejado em px de tela (halo e contorno no mesmo passo), o carimbo (quadrado cheio de 4 px no canto superior direito) e o corpo a 100% (fase 15: o 85% da fase 11 saiu). Na prancheta é a operação `desenha_granada` do log, que vive na camada de desenho e não entra na linha do tempo nem no roteiro; "Converter em granada com horário" a troca pela granada de verdade numa ação só.

## Texto

45. **Granada desenhada é desenho, não evento** (fase 11, 2026-10-13).

- **Para que serve.** Explicar uma jogada por cima do mapa ("aqui devia ter uma smoke"). Não tem
  horário, voo nem efeito, e não conta em nada.
- **Aparência.** O glifo é o `nadeGlyph` das granadas reais, com o anel duplo. O que a separa da
  granada que aconteceu (variante V3 da §19.7 do design, escolhida pelo Pedro na fase 15): o anel tracejado em
  px de TELA (`TRACEJADO_DO_DESENHO`, 3,5/3 px), o **carimbo** (quadrado cheio de 4 px de `--tinta` com 1 px de
  `--contorno` por fora, no canto superior direito, a 1,7 x raio + 2 px de tela do centro) e o item "granada
  desenhada" na legenda, com o carimbo. A área opcional (smoke e molotov, raios `RAIO_SMOKE_UNIDADES` e
  `RAIO_MOLOTOV_UNIDADES`) é tracejada no mesmo passo de tela.
- **O 85% saiu (fase 15).** A regra da fase 11 (corpo a 85%, `ALFA_GRANADA_DESENHADA`) foi substituída pelo
  carimbo: a medição do design (§19.7, ΔE76 no modo "mesmo tamanho") deu ΔE de 0,2 a 0,6 para o alfa de 85%,
  que quase não separa a desenhada da real e só tira contraste do corpo; o tracejado em px do radar (5/4) dava
  ΔE 1,0 em 375 px porque virava 1,6/1,3 px de tela e se dissolvia. Com o carimbo e o tracejado de tela o design
  mediu médias de 4,8 / 5,4 / 5,0 / 5,1 (pior tipo 3,9). No canvas real (`scripts/design/mede_granada_real.py`,
  todos os mapas com partida, 1440 e 375 px, 1x e 2x) a média dos quatro tipos fica entre 4,97 e 5,91 e o pior
  tipo em 4,01 (critério A25: média >= 4,5, nenhum tipo < 3,5).
- **Halo e contorno no mesmo passo.** Os dois anéis seguem o mesmo tracejado, como o fantasma
  (§4.1): onde há traço há os dois, e no vão nenhum. Assim o critério do anel duplo continua
  valendo nos pixels do anel (pior pixel 4,13:1 nos 13 andares, igual ao anel cheio; refeito na fase 15 com o passo de tela, `mede_anel_tracejado`). Tracejar
  só o halo deixaria no vão o contorno escuro sozinho, que cai a 1,00:1 sobre o radar escuro
  (`py -3.12 -m scripts.design.mede_anel_tracejado`).
- **No replay** (camada de anotação, decisão 23): o pincel "Granada" (tecla 8) guarda um traço
  `{ferramenta: "granada", arma, area, pontos: [ponto]}` na mesma lista, na mesma pilha de
  desfazer e na mesma persistência dos outros traços. Arrastar move e Delete apaga; mover e
  ligar a área não entram no desfazer, como a borracha. `metrics/annotations.valida` aceita o
  traço novo; a lista `FERRAMENTAS` do Python (a da prancheta) não muda.
- **Na prancheta:** duas operações novas do log, versão 3: `desenha_granada` (traço, passo,
  arma, x, y; opcionais nível, vida e área) e `define_area_desenho`. Elas materializam um item
  em `estado.tracos` com `ferramenta: "granada"`, então a vida por passo, a borracha, "Apagar
  desenho" e `remove_traco` valem como para qualquer traço. Espelho em `metrics/tactics.py`.
- **Converter em granada com horário.** Emite, numa ação só do desfazer, `cria_granada` (a arma
  do desenho, arremessador = o último jogador selecionado, t = o cabeçote, origem = onde o
  jogador está em t, destino = o ponto do desenho) e `remove_traco`. A seleção da prancheta é
  única, então "o jogador selecionado" é o último selecionado antes de selecionar o desenho.
- **Atalhos.** Com o pincel ligado, 1 a 4 escolhem o tipo; fora dele continuam armando a
  granada com horário (prancheta) ou escolhendo o pincel (replay). As setas movem um cursor no
  mapa (Shift: 4x) e Enter carimba. Os dois usos estão no "?".
