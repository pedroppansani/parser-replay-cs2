# Decisão 23: Anotação no mapa: coordenada de jogo, um único ponto de redimensionamento, camada sempre transparente

- **ID:** 23
- **Status:** vigente
- **Data:** 2026-09-26
- **Resumo:** Anotação em coordenada de jogo; um ponto de redimensionamento; sem texto no template.

## Texto

23. **Anotação no mapa: coordenada de jogo, um único ponto de redimensionamento,
    camada sempre transparente.** A camada vive em `dashboard/web/annotations.js`
    e `annotations.css`, injetados no build; o template não tem texto nem estilo
    dela (há teste).
    - Traço é guardado em **unidade de jogo**, com mapa e impressão da
      calibração do radar em CADA traço. A impressão sai de
      `metrics.annotations.impressao_da_calibracao` no build, a mesma função que
      valida o arquivo exportado.
    - Atribuir `width`/`height` a um canvas APAGA o conteúdo. Todo
      redimensionamento (carga, janela, tela cheia, densidade de pixel, aba que
      aparece) passa por `reprojetaTudo()`, que redesenha o mapa E as anotações
      a partir dos dados. Nunca redesenhe a partir do que está pintado.
    - **Regressão registrada:** o mapa "sumiu" porque a regra geral
      `.board canvas { background: #161d26 }` do template pegava as camadas de
      anotação, que ficavam opacas por cima do mapa. O mapa estava desenhado o
      tempo todo. Diagnóstico por captura de tela real, não por leitura do
      canvas: é o pixel composto que a pessoa vê.
    - Persistência: memória -> localStorage (chave por partida e round, com
      atraso) -> exportar/importar JSON. A página abre como arquivo local ou no
      GitHub Pages, e nenhum dos dois aceita escrita no servidor.
    - Os testes de comportamento rodam num Chrome de verdade
      (`tests/test_annotations_browser.py`, Playwright); sem navegador eles são
      pulados, e os estruturais de `test_annotations.py` ficam como rede de
      segurança.
    - **Pan com espaço + arrastar** (Fase H, 2026-09-26): com o espaço
      segurado o arrasto move o mapa, com qualquer botão e mesmo no modo de
      desenho, e NUNCA começa traço. O espaço só é capturado com o ponteiro
      sobre o mapa; fora dele a página rola como sempre. Soltar o espaço ou a
      janela perder o foco devolve o ponteiro ao desenho. Teste de aceitação:
      traço feito com zoom 3x tem o modelo IDÊNTICO depois de voltar a 1x e
      continua sobre o mesmo ponto do mapa na tela.
    - **Nenhum texto nem estilo novo no `template.html`** (regra do Pedro,
      2026-09-26). Rótulo de interface (botão, dica, aviso) sai do JS da
      própria camada -- `annotations.js`, `tactics.js`, `map_core.js` --, como
      o "Desenhar" e o "Direção". O template só ganha o ponto de injeção
      (`/*__MAP_CORE__*/`, `/*__PRANCHETA__*/`). A decisão 18 continua sendo
      sobre as FRASES dos cards, que saem do Python; esta é sobre a interface.
