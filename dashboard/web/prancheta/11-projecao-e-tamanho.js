  /* ---------------------------------------------------------------------
     Projeção e andares
     --------------------------------------------------------------------- */
  function jogoParaPixel(x, y) { return MapCore.jogoParaPixel(cfg.radar, x, y); }
  function pixelParaJogo(px, py) { return MapCore.pixelParaJogo(cfg.radar, px, py); }
  function eventoParaPixel(e) { return MapCore.eventoParaPixel(cv, cfg.radar, e, S.view); }
  function arredonda(v) { return Math.round(v * 10) / 10; }   // 0,1u, como a anotação
  function eventoParaJogo(e) {
    var p = eventoParaPixel(e), g = pixelParaJogo(p[0], p[1]);
    return [arredonda(g[0]), arredonda(g[1])];
  }

  /** Andares do radar, na ordem do replay (scripts/export_replay.map_levels):
      "default" primeiro, depois de cima para baixo. */
  function andaresDoRadar(r) {
    var sec = r.vertical_sections;
    if (!sec) return [{ nome: "default", min: -1e9, max: 1e9 }];
    return Object.keys(sec).map(function (k) { return { nome: k, min: sec[k].min, max: sec[k].max }; })
      .sort(function (a, b) {
        if ((a.nome !== "default") !== (b.nome !== "default")) return a.nome === "default" ? -1 : 1;
        return b.max - a.max;
      });
  }
  function nivelDoZ(z) {
    if (ANDARES.length < 2 || z === undefined || z === null) return 0;
    for (var i = 0; i < ANDARES.length; i++) if (z >= ANDARES[i].min && z < ANDARES[i].max) return i;
    return 0;
  }

  /* ---------------------------------------------------------------------
     Tamanho: O ÚNICO lugar que muda o tamanho do canvas
     --------------------------------------------------------------------- */
  function emTelaCheia() { return MapCore.emTelaCheia($("pr-palco")); }

  function reprojeta() {
    var tela = $("pr-tela"), est = getComputedStyle(tela);
    var util = tela.clientWidth - parseFloat(est.paddingLeft) - parseFloat(est.paddingRight);
    // as opções do pincel e da granada desenhada ficam numa coluna na borda direita da tela (v2-5b, decisão 2 do
    // Pedro): o mapa nunca passa por baixo dela. A coluna tem largura fixa no CSS e existe mesmo vazia (só fica
    // invisível), então a folga não depende da ferramenta de agora; no celular ela não aparece e não reserva nada
    var opcoes = $("pr-opcoes"), folga = opcoes && opcoes.offsetWidth ? opcoes.offsetWidth + FOLGA_DAS_OPCOES_PX : 0;
    // fora da tela cheia, o mapa e a linha do tempo cabem na janela a partir de onde o mapa COMEÇA (§14:
    // min(100%, 100svh - reserva)); com o topo do site e a barra de 44 px, "janela - 40" passava da tela e o
    // navegador rolava até a linha do tempo no meio do gesto
    var topo = tela.getBoundingClientRect().top + window.scrollY;
    var alto = emTelaCheia()
      ? tela.clientHeight - parseFloat(est.paddingTop) - parseFloat(est.paddingBottom)
      : window.innerHeight - topo - parseFloat(est.paddingTop) - parseFloat(est.paddingBottom) - 8;
    // a linha do tempo (8.5) divide a altura com o mapa: os dois cabem juntos. Desconta a altura RESERVADA dela (o
    // min-height do CSS, a altura com a primeira peça), e não a de agora: criar, desfazer ou refazer uma peça não
    // muda o mapa (v2-5b); com mais jogadores ela cresce para baixo do mapa
    var linha = $("pr-linha");
    if (linha) alto -= parseFloat(getComputedStyle(linha).minHeight) || linha.offsetHeight;
    // celular (<= 640 px, §14): o mapa ocupa a largura toda e a página rola até o painel e a linha do tempo
    if (!emTelaCheia() && window.innerWidth <= LARGURA_DO_CELULAR_PX) alto = util;
    if (util <= 0 || alto <= 0) return;
    // a proporção é a do radar, nunca a do espaço disponível: nada de mapa esticado
    var cx = MapCore.caixaDoMapa(cfg.radar, util - folga, Math.max(200, alto));
    var largura = Math.max(200, Math.floor(cx.largura));
    var altura = Math.round(largura * cfg.radar.height / cfg.radar.width);
    cv.style.width = largura + "px"; cv.style.height = altura + "px";
    // centrado na tela; só quando a sobra de cada lado é menor que a folga ele anda para a esquerda o que falta
    cv.style.marginRight = Math.max(0, 2 * folga - (util - largura)) + "px";
    var tam = MapCore.tamanhoInterno(cfg.radar, largura, window.devicePixelRatio || 1);
    if (cv.width !== tam.w || cv.height !== tam.h) { cv.width = tam.w; cv.height = tam.h; }
    S.reprojecoes++;
    tituloDaDica();   // com outra largura, outra dica pode passar a caber (ou não)
    desenha();
  }
  var pedeReprojecao = null;

  function aplicaZoom(novo, cx, cy) {
    if (MapCore.aplicaZoom(S.view, cfg.radar, novo,
        cx === undefined ? cfg.radar.width / 2 : cx, cy === undefined ? cfg.radar.height / 2 : cy)) {
      desenha(); atualizaBarra();
    }
  }
  function resetaZoom() { S.view = { zoom: 1, panX: 0, panY: 0 }; desenha(); atualizaBarra(); }

