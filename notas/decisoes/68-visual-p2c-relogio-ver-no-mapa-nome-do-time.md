# Decisão 68: Relógio translúcido, "Ver no mapa ↑" e o nome do time da FACEIT (P2c)

- **ID:** 68
- **Status:** vigente
- **Data:** 2026-11-15
- **Resumo:** O relógio grande da prancheta fica translúcido (fundo a 50%, números opacos, contraste >= 3:1 medido nos 10 mapas) quando uma peça ou o nome dela passa por baixo
  dele dentro do mapa; "Ver no mapa ↑" leva ao mapa depois do Aplicar no celular; "Time de <nick>" mantém a grafia do nick no cabeçalho da partida.

## Texto

68. **Três ajustes visuais da P2c** (pedido do Pedro; a navbar com a Prancheta é a 66 e arrastar de novo é a 67).

- **Relógio** (`map_core.rotulosSobReserva`, `prancheta/12-desenho.js`, `tactics.css`): a classe `sob-peca` liga quando uma caixa de peça ou de nome cruza a parte do relógio que está SOBRE o
  mapa. No computador o relógio fica na margem, fora do canvas: nunca liga. A transição é instantânea e o relógio segue sem receber o ponteiro. Escolha do Pedro entre translúcido, parar na borda
  e trocar de canto: translúcido (cobre qualquer origem da peça e não move nada). Contraste dos números do relógio com o fundo a 50% sobre o pixel mais claro do radar (p99,9) e sobre as
  cores das peças: mínimo 3,55:1 (Nuke), ver `tests/test_p2c_visual.py`.
- **Ver no mapa ↑:** botão no cartão aplicado (`#rw-cmd-ver-mapa`, `#pr-cmd-ver-mapa`), visível só no celular (janela sem o palco do computador no Reescrever; até 900 px na prancheta). `scrollIntoView` do
  palco (`behavior: auto`: sem animação, nenhum pulo além da subida), foco no canvas do mapa com `preventScroll` (o `focusin` do v2.js, decisão 53, não rola de novo) e o texto "O mapa está à vista." na região viva do cartão.
- **Nome do time:** o prefixo "Time de " é `metrics.times.PREFIXO_DO_TIME_FACEIT`; o cabeçalho põe a classe `nick` nesses nomes (`text-transform: none`).
