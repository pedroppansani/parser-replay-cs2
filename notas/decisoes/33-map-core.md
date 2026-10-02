# Decisão 33: Um núcleo só para o mapa: `dashboard/web/map_core.js` (`window.MapCore`)

- **ID:** 33
- **Status:** vigente
- **Data:** 2026-09-26
- **Resumo:** Um núcleo só para o mapa (`map_core.js`); extração aceita por pixel idêntico.

## Texto

33. **Um núcleo só para o mapa: `dashboard/web/map_core.js` (`window.MapCore`)**
    (etapa 0 da prancheta, 2026-09-26). Replay, anotação e prancheta usam UMA
    versão de: projeção jogo <-> pixel e evento -> pixel, `applyView`/zoom/pan,
    caixa do mapa e tamanho interno (x densidade, teto `MAX_LADO_INTERNO`),
    agrupamento por quadro, vigia de densidade, tela cheia, armazenamento
    seguro, seletor de cor, traço (`caminhoDoTraco`, `desenhaSeta`, acerto da
    borracha, traço curto demais), `nadeGlyph`, `NADE_COLOR`, área de smoke e
    molotov com `RAIO_SMOKE_UNIDADES` (144) e `RAIO_MOLOTOV_UNIDADES` (120),
    `desenhaJogador` e as `VELOCIDADES` de reprodução. Duas cópias divergem na
    primeira correção -- e já divergiam (a prancheta convertia o ponteiro pela
    escala de cada eixo, a anotação pela da largura).
    A extração foi aceita por PIXEL IDÊNTICO (`scripts/compara_capturas.py`,
    worktree de duas revisões, quadros fixos) e pelos testes de anotação e
    prancheta passando sem alteração. `desenhaJogador` altera o estado do
    contexto e NÃO restaura (é o que mantém o replay idêntico) -- está escrito
    na função; não "conserte" com save/restore.
