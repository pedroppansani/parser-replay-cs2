/* =========================================================================
   Núcleo compartilhado do mapa: o que o replay (template.html), a camada de
   anotação (annotations.js) e a prancheta (tactics.js) usam igual.

   POR QUE UM MÓDULO: projeção, zoom, tamanho do canvas, armazenamento, cor,
   traço, símbolo de granada e desenho do jogador existiam em mais de um lugar.
   Duas cópias divergem na primeira correção -- e já divergiam (a prancheta
   convertia o ponteiro com a escala de cada eixo, a anotação com a da largura).
   Aqui fica UMA versão de cada coisa; quem desenha passa o radar, a vista e o
   estado que são seus.

   Nada aqui guarda estado de página. As funções recebem o radar, a vista
   ({zoom, panX, panY}) e o contexto de desenho como argumento; o seletor de
   cor recebe o objeto de estado de quem o usa e escreve nele.

   Injetado no build antes dos outros scripts (scripts/build_web_page.py e
   scripts/build_tactics_page.py), como o annotations.js.
   ========================================================================= */
window.MapCore = (function () {
  "use strict";

  /* ---------------------------------------------------------------------
     Constantes
     --------------------------------------------------------------------- */

  // Teto da resolução interna do canvas. Numa tela 4K com densidade 2, o mapa
  // em tela cheia passaria de 4000px de lado, e redesenhar isso a cada quadro
  // custa mais do que a nitidez extra devolve. (Convenção visual.)
  var MAX_LADO_INTERNO = 4096;

  var ZOOM_MIN = 1, ZOOM_MAX = 6, ZOOM_PASSO = 1.18;

  // Dessaturação do radar por mapa: [saturação, brilho]. Gerado por gera_radar_ajuste.py (design, 2026-10-04;
  // refeito pelo projeto na design-B2b com os radares de assets/radars/, mesma saída; entrega-sala-de-demo §4.1):
  // maior brilho e, dentro dele, maior saturação com dE2000 >= 8 contra TR, decisivo, molotov e HE; passos de
  // 0,05; brilho >= 0,50. Os andares de um mapa usam o mesmo par.
  var RADAR_AJUSTE = { ancient: [0.65, 1.0], anubis: [0.10, 0.80], cache: [0.95, 0.80], dust2: [0.90, 1.0], inferno: [1.0, 1.0],
                       mirage: [1.0, 1.0], nuke: [0.45, 0.70], overpass: [0.80, 0.85], train: [1.0, 1.0], vertigo: [0.65, 1.0] };
  // Mapa sem entrada: o par mais conservador da tabela (menor saturação e menor brilho) -- e o build avisa.
  var RADAR_AJUSTE_PADRAO = [0.10, 0.70];

  // Velocidades de reprodução, do replay e da prancheta. (Convenção de interface.)
  var VELOCIDADES = [0.25, 0.5, 1, 2, 4];

  // Smoke e Molotov ocupam área, então são desenhados como zona e não como
  // ponto. O raio segue o raio real de efeito no jogo, em UNIDADES DE JOGO, e
  // é convertido pela mesma escala do radar por quem desenha. (Medida no jogo.)
  var RAIO_SMOKE_UNIDADES = 144;
  var RAIO_MOLOTOV_UNIDADES = 120;

  // Ponta da direção do olhar, em pixels do RADAR antes do zoom (convenção
  // visual). O halo branco do jogador (raio 8,2) vira uma gota: a ponta fica a
  // PONTA_DISTANCIA do centro, e os dois lados da ponta são TANGENTES ao halo --
  // a largura da base sai da geometria (8,2 * sen(acos(8,2 / 14)) = 6,6), não
  // de uma segunda constante. Tangente é o que faz a silhueta ler como uma peça
  // só, e não como um círculo com um triângulo espetado.
  var PONTA_DISTANCIA = 14;

  // Distância do nome acima do centro do jogador. Com a ponta, o nome sobe:
  // olhando para cima, a ponta chega a 14 do centro, exatamente onde o nome
  // tinha a base, e encostava nas letras (conferido na captura). Fixo enquanto
  // a direção está ligada -- variar com o ângulo faria o nome pular quando o
  // jogador gira. (Convenção visual.)
  var NOME_ACIMA = 14;
  var NOME_ACIMA_COM_DIRECAO = 19;

  /* Os tokens do CSS (dashboard/web/tokens.css) lidos uma vez e guardados: o canvas usa as MESMAS
     cores do resto da página, sem copiar hex para cá (entrega-sala-de-demo §3.1). Só guarda leitura
     não vazia: lida antes do CSS carregar, ela voltaria "" e ficaria presa. */
  var _tokens = {};
  function token(nome) {
    if (_tokens[nome]) return _tokens[nome];
    var v = getComputedStyle(document.documentElement).getPropertyValue("--" + nome).trim();
    if (v) _tokens[nome] = v;
    return v;
  }
  /** "#rrggbb" de um token e um alfa -> "rgba(r,g,b,a)" (sombra e contorno translúcidos). */
  function corComAlfa(nome, alfa) {
    var h = token(nome).replace("#", "");
    return "rgba(" + parseInt(h.slice(0, 2), 16) + "," + parseInt(h.slice(2, 4), 16) + "," +
      parseInt(h.slice(4, 6), 16) + "," + alfa + ")";
  }

  // Cor de cada tipo de granada: os tokens --smoke, --molotov, --he, --flash da direção "Sala de
  // demo" (decisão 44; contraste e ΔE medidos por metrics/paleta.py). decoy: --apagado.
  // Lidos dos tokens na carga: o `map_core.js` roda depois do <style> da página.
  var NADE_COLOR = { smoke: token("smoke"), molotov: token("molotov"), he: token("he"),
                     flash: token("flash"), decoy: token("apagado") };

  /* ---------------------------------------------------------------------
     Projeção. A mesma conta do resto do projeto (scripts/prepare_radar.py,
     metrics/annotations.py), nos dois sentidos.
     --------------------------------------------------------------------- */
  function jogoParaPixel(r, x, y) {
    return [(x - r.origin_x) * r.scale_px_per_unit, (r.origin_y - y) * r.scale_px_per_unit];
  }
  function pixelParaJogo(r, px, py) {
    return [px / r.scale_px_per_unit + r.origin_x, r.origin_y - py / r.scale_px_per_unit];
  }

  /** Ponteiro na tela -> pixel do radar, desfazendo o tamanho na tela, o zoom e
      o pan. `canvas` é o canvas do MAPA (as camadas ficam exatamente sobre
      ele); `view` pode faltar, e aí vale zoom 1 sem pan. */
  function eventoParaPixel(canvas, radar, e, view) {
    var caixa = canvas.getBoundingClientRect();
    var k = radar.width / caixa.width;
    var px = (e.clientX - caixa.left) * k;
    var py = (e.clientY - caixa.top) * k;
    if (!view) return [px, py];
    return [(px - view.panX) / view.zoom, (py - view.panY) / view.zoom];
  }

  /* ---------------------------------------------------------------------
     Ângulo
     --------------------------------------------------------------------- */

  /** Yaw do CS2 (graus) -> ângulo de TELA (radianos), na convenção do canvas.

      É a ÚNICA função que faz esta conta. A derivação: no jogo o yaw 0° aponta
      para +X e cresce no sentido anti-horário (decisão 9), então a direção é
      (cos yaw, sin yaw). O radar inverte o Y (my(y) = (origin_y - y) * escala),
      e a mesma direção vira o deslocamento em pixel (cos yaw, -sin yaw) =
      (cos(-yaw), sin(-yaw)). Logo θ = -yaw. Não se ajusta sinal "até parecer
      certo": o teste confere 0° -> direita, 90° -> cima, 180° -> esquerda, e o
      matador apontando para a vítima no dado real. */
  function anguloDeTela(yawGraus) {
    return -yawGraus * Math.PI / 180;
  }

  /** Interpola dois yaws (graus) pelo caminho MAIS CURTO e devolve em [0, 360).
      De 359° para 1° o caminho é +2°, não -358°: sem isso a ponta daria uma
      volta inteira na tela. Linear de propósito -- a mira muda por saltos, e
      suavizar (Catmull-Rom, como na posição) inventaria rotação. */
  function interpolaAngulo(a, b, t) {
    var delta = ((b - a + 540) % 360) - 180;
    var v = a + delta * t;
    return ((v % 360) + 360) % 360;
  }

  /* ---------------------------------------------------------------------
     Zoom e pan
     --------------------------------------------------------------------- */

  /** Aplica tamanho interno, zoom e pan a um contexto. O mapa e as camadas
      usam a MESMA transformação, senão os dois se descolam e a seta aponta
      para o lugar errado.

      O desenho acontece sempre em pixels do RADAR; a escala até a resolução
      interna do canvas entra aqui. */
  function applyView(ctx, radar, view) {
    var base = radar ? ctx.canvas.width / radar.width : 1;
    var z = base * view.zoom;
    ctx.setTransform(z, 0, 0, z, base * view.panX, base * view.panY);
  }

  /** Muda o zoom mantendo parado o ponto (centroX, centroY), em pixels do
      radar já com a vista aplicada. Devolve false quando nada mudou. */
  function aplicaZoom(view, radar, novo, centroX, centroY) {
    var z0 = view.zoom;
    var z = Math.min(ZOOM_MAX, Math.max(ZOOM_MIN, novo));
    if (z === z0) return false;
    // mantém o ponto sob o cursor parado enquanto o zoom muda
    view.panX = centroX - (centroX - view.panX) * (z / z0);
    view.panY = centroY - (centroY - view.panY) * (z / z0);
    view.zoom = z;
    limitaPan(view, radar);
    return true;
  }

  /** Impede que o mapa escape da área visível. Sem isso dá para arrastar o
      mapa para fora e ficar olhando para o vazio sem saber como voltar. */
  function limitaPan(view, radar) {
    var W = radar.width, H = radar.height;
    view.panX = Math.min(0, Math.max(W - W * view.zoom, view.panX));
    view.panY = Math.min(0, Math.max(H - H * view.zoom, view.panY));
  }

  /* ---------------------------------------------------------------------
     Tamanho. Quem muda tamanho de canvas é a função única de reprojeção de
     cada página; as contas dela vivem aqui.
     --------------------------------------------------------------------- */

  /** O mapa cresce até o limite da MENOR dimensão e fica centralizado; o
      excedente vira espaço vazio. Nunca esticado -- já houve bug de proporção
      neste projeto, e esticar é exatamente o que produz aquilo. Mesma conta de
      metrics/annotations.caixa_do_mapa. */
  function caixaDoMapa(radar, dispW, dispH) {
    var w = radar.width, h = radar.height;
    var escala = Math.min(dispW / w, dispH / h);
    return { largura: w * escala, altura: h * escala, escala: escala };
  }

  /** Resolução INTERNA = tamanho na tela x densidade de pixels, senão mapa e
      traços saem borrados em tela de alta densidade -- e o traço fino é o
      primeiro a sofrer. A altura sai da largura para a proporção ser exata. */
  function tamanhoInterno(radar, larguraCss, dpr) {
    var w = Math.max(1, Math.min(MAX_LADO_INTERNO, Math.round(larguraCss * dpr)));
    var h = Math.max(1, Math.round(w * radar.height / radar.width));
    return { w: w, h: h };
  }

  /** Vários gatilhos podem disparar no mesmo quadro (resize + observador de
      tamanho + tela cheia); a função devolvida junta todos numa chamada só,
      depois do layout. */
  function agrupaPorQuadro(fn) {
    var pedido = false;
    return function () {
      if (pedido) return;
      pedido = true;
      requestAnimationFrame(function () { pedido = false; fn(); });
    };
  }

  /** Mudança de densidade de pixel (arrastar a janela para outro monitor, zoom
      do navegador) não dispara `resize` em todo navegador. A media query da
      densidade atual avisa quando ela deixa de valer; aí `aoMudar` é chamado
      e o vigia passa a olhar a densidade nova. */
  function vigiaDensidade(aoMudar) {
    if (!window.matchMedia) return;
    var mq = window.matchMedia("(resolution: " + (window.devicePixelRatio || 1) + "dppx)");
    var mudou = function () {
      if (mq.removeEventListener) mq.removeEventListener("change", mudou);
      else if (mq.removeListener) mq.removeListener(mudou);
      aoMudar();
      vigiaDensidade(aoMudar);
    };
    if (mq.addEventListener) mq.addEventListener("change", mudou);
    else if (mq.addListener) mq.addListener(mudou);
  }

  function emTelaCheia(el) {
    return !!el && (document.fullscreenElement === el || document.webkitFullscreenElement === el);
  }

  function alternaTelaCheia(el) {
    if (emTelaCheia(el)) {
      (document.exitFullscreen || document.webkitExitFullscreen).call(document);
    } else {
      (el.requestFullscreen || el.webkitRequestFullscreen).call(el);
    }
  }

  /* ---------------------------------------------------------------------
     Armazenamento do navegador. TODO acesso passa por aqui, dentro de
     try/catch: até ler `window.localStorage` pode lançar erro (arquivo local
     com cookies bloqueados, aba anônima de alguns navegadores). `aoFalhar` é
     chamado a cada falha; quem usa decide o que avisar.
     --------------------------------------------------------------------- */
  function criaArmazem(aoFalhar) {
    var falhou = aoFalhar || function () {};
    function armazem(qual) {
      try { return window[qual] || null; } catch (err) { falhou(); return null; }
    }
    return {
      le: function (qual, chave) {
        try { var a = armazem(qual); return a ? a.getItem(chave) : null; }
        catch (err) { falhou(); return null; }
      },
      grava: function (qual, chave, valor) {
        try { var a = armazem(qual); if (!a) return false; a.setItem(chave, valor); return true; }
        catch (err) { falhou(); return false; }
      },
      // true quando removeu (ou não havia o que remover num armazém que existe)
      remove: function (qual, chave) {
        try { var a = armazem(qual); if (!a) return false; a.removeItem(chave); return true; }
        catch (err) { falhou(); return false; }
      },
      chaves: function (qual) {
        try {
          var a = armazem(qual), out = [];
          if (!a) return out;
          for (var i = 0; i < a.length; i++) out.push(a.key(i));
          return out;
        } catch (err) { falhou(); return []; }
      }
    };
  }

  function lerJson(texto) {
    if (!texto) return null;
    try { return JSON.parse(texto); } catch (err) { return null; }
  }

  /* ---------------------------------------------------------------------
     Traço (formato de metrics/annotations.py), em coordenada de jogo
     --------------------------------------------------------------------- */
  function caminhoDoTraco(ctx, t, radar) {
    var p = t.pontos.map(function (g) { return jogoParaPixel(radar, g[0], g[1]); });
    ctx.lineWidth = t.espessura;
    ctx.strokeStyle = t.cor;
    ctx.fillStyle = t.cor;
    ctx.lineJoin = "round";
    ctx.lineCap = "round";

    if (t.ferramenta === "texto") {
      ctx.font = (t.espessura * 5 + 10) + "px 'DM Sans', system-ui, sans-serif";
      ctx.textBaseline = "middle";
      ctx.fillText(t.texto || "", p[0][0], p[0][1]);
      return;
    }

    var a = p[0], b = p[p.length - 1];
    ctx.beginPath();
    if (t.ferramenta === "caneta") {
      if (p.length === 1) {
        // clique seco com a caneta é um ponto, e ponto também é anotação
        ctx.arc(a[0], a[1], t.espessura / 2, 0, Math.PI * 2);
        ctx.fill();
        return;
      }
      // Curva pelos pontos médios: a mão livre sai lisa, sem o serrilhado de
      // ligar amostra com amostra em linha reta.
      ctx.moveTo(p[0][0], p[0][1]);
      for (var i = 1; i < p.length - 1; i++) {
        var mx = (p[i][0] + p[i + 1][0]) / 2, my = (p[i][1] + p[i + 1][1]) / 2;
        ctx.quadraticCurveTo(p[i][0], p[i][1], mx, my);
      }
      ctx.lineTo(b[0], b[1]);
      ctx.stroke();
      return;
    }
    if (p.length < 2) return;
    if (t.ferramenta === "linha") {
      ctx.moveTo(a[0], a[1]); ctx.lineTo(b[0], b[1]); ctx.stroke();
    } else if (t.ferramenta === "seta") {
      desenhaSeta(ctx, a, b, t.espessura);
    } else if (t.ferramenta === "retangulo") {
      ctx.rect(a[0], a[1], b[0] - a[0], b[1] - a[1]); ctx.stroke();
    } else if (t.ferramenta === "elipse") {
      var cx = (a[0] + b[0]) / 2, cy = (a[1] + b[1]) / 2;
      ctx.ellipse(cx, cy, Math.abs(b[0] - a[0]) / 2, Math.abs(b[1] - a[1]) / 2, 0, 0, Math.PI * 2);
      ctx.stroke();
    }
  }

  /** Clique seco com ferramenta de duas pontas não vira traço: início e fim a
      menos de 8 pixels do radar um do outro, nos dois eixos. A caneta sempre
      vale (um clique dela é um ponto, e ponto também é anotação). */
  function tracoCurtoDemais(t, radar) {
    if (t.ferramenta === "caneta" || t.ferramenta === "texto") return false;
    var a = jogoParaPixel(radar, t.pontos[0][0], t.pontos[0][1]);
    var b = jogoParaPixel(radar, t.pontos[t.pontos.length - 1][0], t.pontos[t.pontos.length - 1][1]);
    return Math.abs(a[0] - b[0]) < 8 && Math.abs(a[1] - b[1]) < 8;
  }

  /** A borracha acertou o traço? `alvo` em pixels do radar; `raio` é o raio da
      borracha, somado à espessura do traço. Apaga o TRAÇO INTEIRO, não pixel a
      pixel: apagar pedaço de seta deixa meia seta, que é pior que não apagar. */
  function tracoEncosta(t, alvo, radar, raio) {
    var pts = t.pontos.map(function (g) { return jogoParaPixel(radar, g[0], g[1]); });
    var r = raio + t.espessura;
    if (t.ferramenta === "texto" || pts.length === 1) {
      return Math.hypot(pts[0][0] - alvo[0], pts[0][1] - alvo[1]) <= r * 3;
    }
    if (t.ferramenta === "retangulo" || t.ferramenta === "elipse") {
      var x0 = Math.min(pts[0][0], pts[1][0]), x1 = Math.max(pts[0][0], pts[1][0]);
      var y0 = Math.min(pts[0][1], pts[1][1]), y1 = Math.max(pts[0][1], pts[1][1]);
      return alvo[0] >= x0 - r && alvo[0] <= x1 + r && alvo[1] >= y0 - r && alvo[1] <= y1 + r;
    }
    for (var i = 0; i < pts.length - 1; i++) {
      if (distanciaAoSegmento(alvo, pts[i], pts[i + 1]) <= r) return true;
    }
    return false;
  }

  function distanciaAoSegmento(p, a, b) {
    var dx = b[0] - a[0], dy = b[1] - a[1];
    var L = dx * dx + dy * dy;
    var t = L === 0 ? 0 : Math.max(0, Math.min(1, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / L));
    return Math.hypot(p[0] - (a[0] + t * dx), p[1] - (a[1] + t * dy));
  }

  /** A seta é ferramenta de primeira classe, não linha com enfeite: a cabeça
      cresce com a espessura e fica sólida, para a leitura funcionar de longe. */
  function desenhaSeta(ctx, a, b, esp) {
    var ang = Math.atan2(b[1] - a[1], b[0] - a[0]);
    var cab = Math.max(11, esp * 3.4);
    var fim = [b[0] - Math.cos(ang) * cab * 0.55, b[1] - Math.sin(ang) * cab * 0.55];
    ctx.moveTo(a[0], a[1]); ctx.lineTo(fim[0], fim[1]); ctx.stroke();
    ctx.beginPath();
    ctx.moveTo(b[0], b[1]);
    ctx.lineTo(b[0] - Math.cos(ang - 0.42) * cab, b[1] - Math.sin(ang - 0.42) * cab);
    ctx.lineTo(b[0] - Math.cos(ang + 0.42) * cab, b[1] - Math.sin(ang + 0.42) * cab);
    ctx.closePath();
    ctx.fill();
  }

  /* ---------------------------------------------------------------------
     Granada
     --------------------------------------------------------------------- */

  // Símbolo de cada tipo de granada. A forma é o que permite ler o mapa sem
  // consultar a legenda, e é o que sobrevive a daltonismo — cor sozinha não é.
  // Cada forma remete ao efeito: smoke é a área que ela vira, flash é o estouro,
  // HE é o fragmento, molotov é a gota que espalha fogo.
  // `ang` gira o símbolo na direção do voo. Só é usado nos que têm frente
  // (molotov e HE); estrela e nuvem não têm, e girá-las só criaria tremor.
  function nadeGlyph(ctx, kind, x, y, r, col, ang) {
    ctx.save();
    ctx.translate(x, y);
    if (ESTILO.anelDuplo) anelDoGlifo(ctx, kind, r, ang);

    // Contorno escuro por baixo do claro: o radar tem áreas claras E escuras, e
    // um traço branco sozinho sumia sobre o concreto claro da Mirage.
    ctx.shadowColor = corComAlfa("contorno", 0.55);
    ctx.shadowBlur = 3;
    ctx.fillStyle = col;
    ctx.strokeStyle = corComAlfa("tinta", 0.95);
    ctx.lineWidth = 1.2;
    ctx.lineJoin = "round";

    if (kind === "flash") {
      // Estrela de quatro pontas com um núcleo claro: o estouro tem centro, e o
      // núcleo é o que a distingue do serrilhado da HE quando as duas estão
      // pequenas na tela.
      ctx.beginPath();
      for (var i = 0; i < 8; i++) {
        var a1 = (Math.PI / 4) * i - Math.PI / 2;
        var rad = i % 2 === 0 ? r * 1.55 : r * 0.42;
        var px = Math.cos(a1) * rad, py = Math.sin(a1) * rad;
        if (i === 0) ctx.moveTo(px, py); else ctx.lineTo(px, py);
      }
      ctx.closePath();
      ctx.fill();
      ctx.stroke();
      ctx.shadowBlur = 0;
      ctx.beginPath();
      ctx.arc(0, 0, r * 0.3, 0, Math.PI * 2);
      ctx.fillStyle = corComAlfa("tinta", 0.95);
      ctx.fill();
    } else if (kind === "he") {
      // Anel serrilhado, VAZADO. Cheio virava uma bolota no tamanho em que ela
      // aparece; vazado lê como fragmento e deixa o mapa aparecer por dentro.
      ctx.beginPath();
      for (var j = 0; j < 14; j++) {
        var a2 = (Math.PI / 7) * j - Math.PI / 2 + (ang || 0);
        var r2 = j % 2 === 0 ? r * 1.2 : r * 0.72;
        var qx = Math.cos(a2) * r2, qy = Math.sin(a2) * r2;
        if (j === 0) ctx.moveTo(qx, qy); else ctx.lineTo(qx, qy);
      }
      ctx.closePath();
      ctx.lineWidth = 2;
      ctx.strokeStyle = col;
      ctx.stroke();
      ctx.shadowBlur = 0;
      ctx.lineWidth = 0.9;
      ctx.strokeStyle = corComAlfa("tinta", 0.85);
      ctx.stroke();
    } else if (kind === "molotov") {
      // Gota com a ponta na direção do voo: é o único tipo em que a orientação
      // diz alguma coisa, porque ele espalha fogo para onde caiu.
      ctx.rotate((ang || 0) + Math.PI / 2);
      ctx.beginPath();
      ctx.moveTo(0, -r * 1.5);
      ctx.quadraticCurveTo(r * 0.95, -r * 0.15, 0, r * 1.0);
      ctx.quadraticCurveTo(-r * 0.95, -r * 0.15, 0, -r * 1.5);
      ctx.fill();
      ctx.stroke();
    } else if (kind === "decoy") {
      // Quadrado vazado com um ponto no meio: é o único que não faz nada, e o
      // "oco com miolo" lê como imitação de granada.
      ctx.beginPath();
      ctx.rect(-r * 0.82, -r * 0.82, r * 1.64, r * 1.64);
      ctx.lineWidth = 1.8;
      ctx.strokeStyle = col;
      ctx.stroke();
      ctx.shadowBlur = 0;
      ctx.beginPath();
      ctx.arc(0, 0, r * 0.26, 0, Math.PI * 2);
      ctx.fillStyle = col;
      ctx.fill();
    } else {
      // Smoke: silhueta de nuvem, três arcos. O círculo de antes era a mesma
      // forma do vulto do jogador, e num mapa cheio os dois se confundiam.
      ctx.beginPath();
      ctx.arc(-r * 0.52, r * 0.12, r * 0.62, 0, Math.PI * 2);
      ctx.arc(r * 0.52, r * 0.12, r * 0.62, 0, Math.PI * 2);
      ctx.arc(0, -r * 0.3, r * 0.78, 0, Math.PI * 2);
      ctx.fill();
      ctx.stroke();
    }

    ctx.restore();
  }

  /* ---------------------------------------------------------------------
     Radar dessaturado por mapa (§4.1): UMA vez na carga, por pixel, e o resultado é reaproveitado com
     drawImage -- nada de ctx.filter por quadro. Replay e prancheta chamam a mesma função (decisão 33).
       L = 0,2126 R + 0,7152 G + 0,0722 B ;  saída = clamp(b × (L + s × (cor − L))) ; alfa intacto
     --------------------------------------------------------------------- */
  function ajusteDoRadar(mapa) {
    var chave = String(mapa || "").replace(/^de_/, "");
    return RADAR_AJUSTE[chave] || RADAR_AJUSTE_PADRAO;
  }

  /** O radar já processado: um canvas do tamanho natural da imagem (ou a própria imagem, quando o par é
      1,00/1,00 ou o navegador não deixa ler os pixels). Guardado na imagem, por mapa. */
  function radarProcessado(imagem, mapa) {
    if (!imagem || !imagem.naturalWidth) return imagem;
    var par = ajusteDoRadar(mapa), s = par[0], b = par[1];
    if (s === 1 && b === 1) return imagem;
    var guardados = imagem.__radarProcessado || (imagem.__radarProcessado = {});
    var chave = s + "/" + b;
    if (guardados[chave]) return guardados[chave];
    var c = document.createElement("canvas");
    c.width = imagem.naturalWidth; c.height = imagem.naturalHeight;
    var g = c.getContext("2d");
    g.drawImage(imagem, 0, 0);
    var dados;
    try { dados = g.getImageData(0, 0, c.width, c.height); } catch (e) { return imagem; }
    var d = dados.data;
    for (var i = 0; i < d.length; i += 4) {
      var L = 0.2126 * d[i] + 0.7152 * d[i + 1] + 0.0722 * d[i + 2];
      d[i] = b * (L + s * (d[i] - L));            // o Uint8ClampedArray já faz o clamp e o arredondamento
      d[i + 1] = b * (L + s * (d[i + 1] - L));
      d[i + 2] = b * (L + s * (d[i + 2] - L));
    }
    g.putImageData(dados, 0, 0);
    guardados[chave] = c;
    return c;
  }

  /* ---------------------------------------------------------------------
     Anel duplo (entrega-sala-de-demo §4.1): contorno escuro --contorno de 2,5 px e halo claro --tinta
     de 1,5 px por fora, em toda peça e todo glifo. Em qualquer pixel do radar um dos dois contrasta
     >= 3:1 com o vizinho. Ligado por página (`MapCore.defineAnelDuplo`): o replay liga na design-B2,
     a prancheta na design-E -- até lá ela desenha como antes.
     --------------------------------------------------------------------- */
  var ESTILO = { anelDuplo: false };
  var ANEL_CONTORNO = 2.5, ANEL_HALO = 1.5;

  function defineAnelDuplo(ligado) { ESTILO.anelDuplo = !!ligado; }

  /** O mesmo caminho do glifo, só o contorno: halo claro (mais largo) e contorno escuro por cima. */
  function caminhoDoGlifo(ctx, kind, r, ang) {
    ctx.beginPath();
    if (kind === "flash") {
      for (var i = 0; i < 8; i++) {
        var a1 = (Math.PI / 4) * i - Math.PI / 2, rad = i % 2 === 0 ? r * 1.55 : r * 0.42;
        if (i === 0) ctx.moveTo(Math.cos(a1) * rad, Math.sin(a1) * rad); else ctx.lineTo(Math.cos(a1) * rad, Math.sin(a1) * rad);
      }
      ctx.closePath();
    } else if (kind === "he") {
      for (var j = 0; j < 14; j++) {
        var a2 = (Math.PI / 7) * j - Math.PI / 2 + (ang || 0), r2 = j % 2 === 0 ? r * 1.2 : r * 0.72;
        if (j === 0) ctx.moveTo(Math.cos(a2) * r2, Math.sin(a2) * r2); else ctx.lineTo(Math.cos(a2) * r2, Math.sin(a2) * r2);
      }
      ctx.closePath();
    } else if (kind === "molotov") {
      var c = Math.cos((ang || 0) + Math.PI / 2), s = Math.sin((ang || 0) + Math.PI / 2);
      var t = function (px, py) { return [px * c - py * s, px * s + py * c]; };
      var p0 = t(0, -r * 1.5), q1 = t(r * 0.95, -r * 0.15), p1 = t(0, r), q2 = t(-r * 0.95, -r * 0.15);
      ctx.moveTo(p0[0], p0[1]); ctx.quadraticCurveTo(q1[0], q1[1], p1[0], p1[1]);
      ctx.quadraticCurveTo(q2[0], q2[1], p0[0], p0[1]);
    } else if (kind === "decoy") {
      ctx.rect(-r * 0.82, -r * 0.82, r * 1.64, r * 1.64);
    } else {
      ctx.arc(-r * 0.52, r * 0.12, r * 0.62, 0, Math.PI * 2);
      ctx.moveTo(r * 1.14, r * 0.12);
      ctx.arc(r * 0.52, r * 0.12, r * 0.62, 0, Math.PI * 2);
      ctx.moveTo(r * 0.78, -r * 0.3);
      ctx.arc(0, -r * 0.3, r * 0.78, 0, Math.PI * 2);
    }
  }

  function anelDoGlifo(ctx, kind, r, ang) {
    ctx.save();
    ctx.lineJoin = "round";
    caminhoDoGlifo(ctx, kind, r, ang);
    ctx.lineWidth = 2 * (ANEL_CONTORNO + ANEL_HALO) + (kind === "he" ? 2 : 0);
    ctx.strokeStyle = token("tinta");
    ctx.stroke();
    ctx.lineWidth = 2 * ANEL_CONTORNO + (kind === "he" ? 2 : 0);
    ctx.strokeStyle = token("contorno");
    ctx.stroke();
    ctx.restore();
  }

  /** Disco com o anel duplo por baixo (peça viva): halo claro, contorno escuro e a cor do lado. */
  function discoComAnel(ctx, X, Y, r, cor, caminho) {
    ctx.fillStyle = token("tinta");
    ctx.beginPath(); caminho(r + ANEL_CONTORNO + ANEL_HALO); ctx.fill();
    ctx.fillStyle = token("contorno");
    ctx.beginPath(); caminho(r + ANEL_CONTORNO); ctx.fill();
    ctx.fillStyle = cor;
    ctx.beginPath(); ctx.arc(X, Y, r, 0, Math.PI * 2); ctx.fill();
  }

  /* ---------------------------------------------------------------------
     Rótulos do mapa (entrega-sala-de-demo §4.2): em px de TELA (12,5 px, peso 600), contorno escuro de
     6 px, placa --contorno a 88 % atrás, numa camada própria por cima de tudo e com desvio de colisão.
     Quem desenha um quadro chama `rotulosInicia(ctx, canvas)`, registra cada rótulo com `rotulo(...)`
     (no ponto do mapa, já com o zoom do contexto) e no fim `rotulosDesenha()`.
     --------------------------------------------------------------------- */
  var ROT = { ativo: false, ctx: null, canvas: null, lista: [], caixas: [], modo: "normal", redesenha: null };
  var ROT_TAM = 12.5, ROT_FOLGA_X = 4, ROT_FOLGA_Y = 3, ROT_CONTORNO = 6;

  function rotulosInicia(ctx, canvas, redesenha) {
    ROT.ativo = true; ROT.ctx = ctx; ROT.canvas = canvas; ROT.lista = [];
    if (redesenha) ROT.redesenha = redesenha;
  }

  /** Registra um rótulo centrado acima de (X, Y) do contexto atual. o: {cor, fonte ("texto"|"num"),
      italico, prioridade (maior desenha primeiro), dy (deslocamento para cima, em px de tela)}. */
  function rotulo(texto, X, Y, o) {
    if (!ROT.ativo || !texto) return;
    o = o || {};
    var m = ROT.ctx.getTransform();
    ROT.lista.push({ txt: String(texto), x: m.a * X + m.c * Y + m.e, y: m.b * X + m.d * Y + m.f,
                     cor: o.cor || token("tinta"), fonte: o.fonte || "texto", italico: !!o.italico,
                     prioridade: o.prioridade || 0, dy: o.dy || 0, alfa: o.alfa == null ? 1 : o.alfa });
  }

  function corHex(c) {
    var x = normalizaCor(c);
    return x || c;
  }

  function rotulosDesenha() {
    if (!ROT.ativo) return;
    ROT.ativo = false;
    var ctx = ROT.ctx, cv = ROT.canvas;
    var largura = cv.getBoundingClientRect().width || cv.width;
    var k = cv.width / largura;                 // px do canvas por px de tela
    ROT.caixas = [];
    if (ROT.modo === "sem_texto") return;
    ctx.save();
    ctx.setTransform(1, 0, 0, 1, 0, 0);
    ctx.textAlign = "center";
    ctx.textBaseline = "alphabetic";
    ctx.lineJoin = "round";
    var ocupadas = [];
    var ordem = ROT.lista.slice().sort(function (a, b) { return b.prioridade - a.prioridade; });
    ordem.forEach(function (r) {
      ctx.font = (r.italico ? "italic " : "") + "600 " + (ROT_TAM * k) + "px " + token(r.fonte === "num" ? "f-num" : "f-texto");
      var med = ctx.measureText(r.txt);
      // a placa usa a altura da FONTE (maiúscula e descendente: "Hg"), não a do texto: "zecco" sem
      // ascendente ficaria com a placa colada na letra e o contorno sem folga sobre o radar
      var ref = ctx.measureText("Hgjy");
      var asc = Math.max(ref.actualBoundingBoxAscent || ROT_TAM * 0.72 * k, med.actualBoundingBoxAscent || 0);
      var desc = Math.max(ref.actualBoundingBoxDescent || ROT_TAM * 0.2 * k, med.actualBoundingBoxDescent || 0);
      var ascT = med.actualBoundingBoxAscent || asc, descT = med.actualBoundingBoxDescent || desc;
      var w = med.width + 2 * ROT_FOLGA_X * k, hh = asc + desc + 2 * ROT_FOLGA_Y * k;
      var base = r.y - r.dy * k;
      // acima, abaixo, mais acima, mais abaixo (§4.2); sem lugar, o rótulo some (aparece no hover/seleção)
      var tentativas = [0, -hh, hh, -2 * hh, 2 * hh];
      var caixa = null;
      for (var i = 0; i < tentativas.length && !caixa; i++) {
        var y0 = base + tentativas[i] - asc - ROT_FOLGA_Y * k;
        var c = { x: r.x - w / 2, y: y0, w: w, h: hh };
        if (c.x < 0 || c.y < 0 || c.x + c.w > cv.width || c.y + c.h > cv.height) continue;
        var bate = ocupadas.some(function (o) {
          return c.x < o.x + o.w && o.x < c.x + c.w && c.y < o.y + o.h && o.y < c.y + c.h;
        });
        if (!bate) caixa = c;
      }
      if (!caixa) return;
      ocupadas.push(caixa);
      var yTexto = caixa.y + ROT_FOLGA_Y * k + asc;
      ctx.globalAlpha = r.alfa;
      ctx.fillStyle = corComAlfa("contorno", 0.88);
      ctx.fillRect(caixa.x, caixa.y, caixa.w, caixa.h);
      ctx.lineWidth = ROT_CONTORNO * k;
      ctx.strokeStyle = token("contorno");
      ctx.strokeText(r.txt, r.x, yTexto);
      if (ROT.modo !== "sem_preenchimento") {
        ctx.fillStyle = r.cor;
        ctx.fillText(r.txt, r.x, yTexto);
      }
      ctx.globalAlpha = 1;
      ROT.caixas.push({ x: (r.x - med.width / 2) / k, y: (yTexto - ascT) / k, w: med.width / k, h: (ascT + descT) / k,
                        txt: r.txt, cor: corHex(r.cor), peso: 600, alt: (ascT + descT) / k });
    });
    ctx.restore();
  }

  // Gancho de medição do A11 (scripts/design/mede_texto_mapa.py): o texto do canvas não está no DOM.
  if (typeof window !== "undefined") {
    window.__medicaoRotulos = {
      get modo() { return ROT.modo; },
      define: function (m) { ROT.modo = m; if (ROT.redesenha) ROT.redesenha(); },
      caixas: function () { return ROT.caixas.slice(); }
    };
  }

  /** Área de efeito de smoke ou molotov (a zona que ela ocupa, não o símbolo),
      centrada em (X, Y) com raio r, em pixels do radar. O raio vem de
      RAIO_SMOKE_UNIDADES / RAIO_MOLOTOV_UNIDADES convertido pela escala. */
  function desenhaArea(ctx, arma, X, Y, r) {
    var g = ctx.createRadialGradient(X, Y, 0, X, Y, r);
    if (arma === "smoke") {
      g.addColorStop(0, corComAlfa("smoke", 0.78));
      g.addColorStop(0.7, corComAlfa("smoke", 0.5));
      g.addColorStop(1, corComAlfa("smoke", 0));
    } else {
      g.addColorStop(0, corComAlfa("molotov", 0.62));
      g.addColorStop(1, corComAlfa("molotov", 0));
    }
    ctx.fillStyle = g;
    ctx.beginPath(); ctx.arc(X, Y, r, 0, Math.PI * 2); ctx.fill();
  }

  /* ---------------------------------------------------------------------
     Jogador
     --------------------------------------------------------------------- */

  /** O jogador no mapa, em pixels do radar (X, Y já projetados).

      o.cor      cor do lado
      o.estado   "vivo" (padrão), "morto" ou "outro_andar"
      o.acima    no estado "outro_andar": true se o jogador está ACIMA do andar
                 mostrado (a seta aponta para baixo, como no replay)
      o.hp       vida de 0 a 100; abaixo de 100 desenha o anel que encolhe
      o.cego     true desenha o anel tracejado de cegueira
      o.nome     texto acima do jogador (até 9 caracteres)
      o.yaw      direção do olhar em graus (convenção do CS2); ausente ou null =
                 sem ponta, e o jogador sai exatamente como antes da direção
      o.escala   fator de tamanho (padrão 1). A peça da prancheta é maior que o
                 jogador do replay para dar para pegar com o mouse: mesma forma,
                 outro tamanho. Tudo escala junto, inclusive traço e fonte.

      ATENÇÃO -- EFEITO COLATERAL DE PROPÓSITO: a função altera fillStyle,
      strokeStyle, lineWidth, font, textAlign e globalAlpha do contexto e NÃO
      os restaura (só a sombra do halo fica dentro de um save/restore). É
      exatamente o efeito que o código tinha quando vivia dentro do draw() do
      replay, e é o que mantém o replay idêntico pixel a pixel ao de antes da
      extração (etapa 0). Não "conserte" com save/restore em volta: o que for
      desenhado depois passaria a herdar outro estado, e o replay mudaria sem
      ninguém perceber. Quem chamar e depender do estado anterior, salve antes. */
  function desenhaJogador(ctx, X, Y, o) {
    if (ESTILO.anelDuplo) return desenhaJogadorComAnel(ctx, X, Y, o);
    var color = o.cor;
    var e = o.escala || 1;
    var comDirecao = o.yaw !== undefined && o.yaw !== null;

    if (o.estado === "morto") {
      ctx.globalAlpha = 0.5;
      ctx.strokeStyle = color;
      ctx.lineWidth = 1.6 * e;
      ctx.beginPath();
      ctx.moveTo(X - 3.5 * e, Y - 3.5 * e); ctx.lineTo(X + 3.5 * e, Y + 3.5 * e);
      ctx.moveTo(X + 3.5 * e, Y - 3.5 * e); ctx.lineTo(X - 3.5 * e, Y + 3.5 * e);
      ctx.stroke();
      ctx.globalAlpha = 1;
      return;
    }

    // Jogador em outro andar. Sem essa distinção, na Nuke um CT no B e um T
    // no A aparecem colados no mesmo ponto do mapa 2D, como se estivessem se
    // olhando — quando na verdade há uma laje entre os dois.
    if (o.estado === "outro_andar") {
      ctx.globalAlpha = 0.5;
      ctx.strokeStyle = color;
      ctx.lineWidth = 2 * e;
      ctx.beginPath(); ctx.arc(X, Y, 5.5 * e, 0, Math.PI * 2); ctx.stroke();
      // seta indicando se está acima ou abaixo do andar mostrado
      ctx.fillStyle = color;
      ctx.font = "700 " + (9 * e) + "px " + token("f-num");
      ctx.textAlign = "center";
      ctx.fillText(o.acima ? "▼" : "▲", X, Y + 3 * e);
      ctx.globalAlpha = 1;
      return;
    }

    // Halo branco. Com a direção, ele vira a gota (morto e outro andar já
    // saíram acima, sem ponta).
    ctx.save();
    ctx.shadowColor = corComAlfa("contorno", 0.55);
    ctx.shadowBlur = 6 * e;
    ctx.shadowOffsetY = 1 * e;
    ctx.fillStyle = token("tinta");
    ctx.beginPath();
    if (comDirecao) caminhoDaGota(ctx, X, Y, 8.2 * e, PONTA_DISTANCIA * e, anguloDeTela(o.yaw));
    else ctx.arc(X, Y, 8.2 * e, 0, Math.PI * 2);
    ctx.fill();
    ctx.restore();

    ctx.fillStyle = color;
    ctx.beginPath(); ctx.arc(X, Y, 6 * e, 0, Math.PI * 2); ctx.fill();

    // Cegueira: é o estado que explica por que um jogador parou de mirar, ou
    // andou pra frente sem reagir. Sem marcar isso no mapa, a sequência mais
    // comum do CS (flash entra, time entra atrás) fica sem causa visível.
    if (o.cego) {
      ctx.strokeStyle = NADE_COLOR.flash;
      ctx.globalAlpha = 0.9;
      ctx.lineWidth = 2.2 * e;
      ctx.setLineDash([3 * e, 3 * e]);
      ctx.beginPath(); ctx.arc(X, Y, 12.5 * e, 0, Math.PI * 2); ctx.stroke();
      ctx.setLineDash([]);
      ctx.globalAlpha = 1;
    }

    // anel de vida: encolhe conforme o jogador toma dano
    var hp = Math.max(0, Math.min(100, o.hp)) / 100;
    if (hp < 1) {
      ctx.strokeStyle = token("tinta");
      ctx.lineWidth = 2.4 * e;
      ctx.beginPath();
      ctx.arc(X, Y, 10.4 * e, -Math.PI / 2, -Math.PI / 2 + hp * Math.PI * 2);
      ctx.stroke();
    }

    var yNome = Y - (comDirecao ? NOME_ACIMA_COM_DIRECAO : NOME_ACIMA) * e;
    ctx.font = "600 " + (12 * e) + "px " + token("f-texto");   // o nome é texto: Archivo (mono só em número)
    ctx.textAlign = "center";
    ctx.lineWidth = 3 * e;
    ctx.strokeStyle = corComAlfa("contorno", 0.85);
    ctx.strokeText(o.nome.slice(0, 9), X, yNome);
    ctx.fillStyle = token("tinta");
    ctx.fillText(o.nome.slice(0, 9), X, yNome);
  }

  /** A peça com o anel duplo em todos os estados (§4.1) e o nome na camada de rótulos (§4.2).
      Restaura o estado do contexto (o efeito colateral do desenho antigo não vale aqui). */
  function desenhaJogadorComAnel(ctx, X, Y, o) {
    var color = o.cor;
    var e = o.escala || 1;
    var comDirecao = o.yaw !== undefined && o.yaw !== null;
    ctx.save();
    ctx.lineCap = "round"; ctx.lineJoin = "round";

    if (o.estado === "morto") {
      // ✕ com halo claro (8 px) e contorno escuro (5,5 px) inteiros por baixo; só o traço colorido a 60 %
      var d = 3.5 * e;
      var xis = function () {
        ctx.beginPath();
        ctx.moveTo(X - d, Y - d); ctx.lineTo(X + d, Y + d);
        ctx.moveTo(X + d, Y - d); ctx.lineTo(X - d, Y + d);
      };
      xis(); ctx.lineWidth = 8 * e; ctx.strokeStyle = token("tinta"); ctx.stroke();
      xis(); ctx.lineWidth = 5.5 * e; ctx.strokeStyle = token("contorno"); ctx.stroke();
      ctx.globalAlpha = 0.6;
      xis(); ctx.lineWidth = 3 * e; ctx.strokeStyle = color; ctx.stroke();
      ctx.restore();
      return;
    }

    if (o.estado === "outro_andar") {
      // anel vazado sobre o anel duplo inteiro; a seta ▲/▼ com o mesmo contorno escuro
      var rr = 5.5 * e;
      ctx.lineWidth = 2 * e + 2 * (ANEL_CONTORNO + ANEL_HALO); ctx.strokeStyle = token("tinta");
      ctx.beginPath(); ctx.arc(X, Y, rr, 0, Math.PI * 2); ctx.stroke();
      ctx.lineWidth = 2 * e + 2 * ANEL_CONTORNO; ctx.strokeStyle = token("contorno");
      ctx.beginPath(); ctx.arc(X, Y, rr, 0, Math.PI * 2); ctx.stroke();
      ctx.globalAlpha = 0.5;
      ctx.lineWidth = 2 * e; ctx.strokeStyle = color;
      ctx.beginPath(); ctx.arc(X, Y, rr, 0, Math.PI * 2); ctx.stroke();
      ctx.globalAlpha = 1;
      ctx.font = "700 " + (9 * e) + "px " + token("f-num");
      ctx.textAlign = "center";
      ctx.lineWidth = ANEL_CONTORNO * 1.6; ctx.strokeStyle = token("contorno");
      ctx.strokeText(o.acima ? "▼" : "▲", X, Y + 3 * e);
      ctx.fillStyle = color;
      ctx.fillText(o.acima ? "▼" : "▲", X, Y + 3 * e);
      ctx.restore();
      return;
    }

    var raio = 6 * e;
    discoComAnel(ctx, X, Y, raio, color, function (r) {
      if (comDirecao) caminhoDaGota(ctx, X, Y, r, PONTA_DISTANCIA * e + (r - raio), anguloDeTela(o.yaw));
      else ctx.arc(X, Y, r, 0, Math.PI * 2);
    });

    if (o.cego) {
      ctx.strokeStyle = NADE_COLOR.flash;
      ctx.globalAlpha = 0.9;
      ctx.lineWidth = 2.2 * e;
      ctx.setLineDash([3 * e, 3 * e]);
      ctx.beginPath(); ctx.arc(X, Y, 16 * e, 0, Math.PI * 2); ctx.stroke();
      ctx.setLineDash([]);
      ctx.globalAlpha = 1;
    }

    var hp = Math.max(0, Math.min(100, o.hp)) / 100;
    if (hp < 1) {
      ctx.strokeStyle = token("tinta");
      ctx.lineWidth = 2.2 * e;
      ctx.beginPath();
      ctx.arc(X, Y, 12.6 * e, -Math.PI / 2, -Math.PI / 2 + hp * Math.PI * 2);
      ctx.stroke();
    }
    ctx.restore();

    if (o.nome && ROT.ativo) {
      // `rotuloAcima` (px do contexto): quem desenha a peça maior (prancheta) diz onde o nome começa
      if (o.rotuloAcima != null) rotulo(o.nome.slice(0, 9), X, Y - o.rotuloAcima, { cor: token("tinta"), prioridade: o.selecionado ? 10 : 1, dy: 2 });
      else rotulo(o.nome.slice(0, 9), X, Y, { cor: token("tinta"), prioridade: o.selecionado ? 10 : 0,
                                              dy: (comDirecao ? NOME_ACIMA_COM_DIRECAO : NOME_ACIMA) - 4 });
    }
  }

  /** Gota: círculo de raio r com uma ponta a `dist` do centro, no ângulo de
      tela θ. Os lados da ponta são tangentes ao círculo (ângulo α = acos(r/dist)
      de cada lado), e o arco dá a volta por trás. Só o caminho: quem chama
      preenche. */
  function caminhoDaGota(ctx, X, Y, r, dist, theta) {
    var alfa = Math.acos(r / dist);
    ctx.moveTo(X + Math.cos(theta) * dist, Y + Math.sin(theta) * dist);
    ctx.lineTo(X + Math.cos(theta + alfa) * r, Y + Math.sin(theta + alfa) * r);
    ctx.arc(X, Y, r, theta + alfa, theta - alfa + Math.PI * 2);
    ctx.closePath();
  }

  /* ---------------------------------------------------------------------
     Cor: conversões e o seletor (bolinha com a cor atual, setinha que abre o
     seletor, recentes)
     --------------------------------------------------------------------- */

  /** Hex (#rgb, #rrggbb, com ou sem #) ou rgb(r, g, b) -> "#rrggbb", ou null. */
  function normalizaCor(texto) {
    var s = String(texto || "").trim().toLowerCase();
    var m = s.match(/^rgb\s*\(\s*(\d{1,3})\s*,\s*(\d{1,3})\s*,\s*(\d{1,3})\s*\)$/);
    if (m) return deRgb(Number(m[1]), Number(m[2]), Number(m[3]));
    if (s.charAt(0) === "#") s = s.slice(1);
    if (/^[0-9a-f]{3}$/.test(s)) s = s.charAt(0) + s.charAt(0) + s.charAt(1) + s.charAt(1) + s.charAt(2) + s.charAt(2);
    return /^[0-9a-f]{6}$/.test(s) ? "#" + s : null;
  }
  function deRgb(r, g, b) {
    if ([r, g, b].some(function (v) { return !isFinite(v) || v < 0 || v > 255 || v !== Math.floor(v); })) return null;
    return "#" + [r, g, b].map(function (v) { return (v < 16 ? "0" : "") + v.toString(16); }).join("");
  }
  function paraRgb(hex) {
    return [1, 3, 5].map(function (i) { return parseInt(hex.slice(i, i + 2), 16); });
  }

  /** HSV é o espaço do seletor visual: a matiz é a barra do arco-íris, e
      saturação x brilho é o quadrado. h em graus, s e v de 0 a 1. */
  function deHsv(h, sat, v) {
    var f = function (n) {
      var k = (n + h / 60) % 6;
      return v - v * sat * Math.max(0, Math.min(k, 4 - k, 1));
    };
    return deRgb(Math.round(f(5) * 255), Math.round(f(3) * 255), Math.round(f(1) * 255));
  }
  function paraHsv(hex) {
    var c = paraRgb(hex).map(function (x) { return x / 255; });
    var max = Math.max(c[0], c[1], c[2]), min = Math.min(c[0], c[1], c[2]), d = max - min;
    var h = 0;
    if (d) {
      if (max === c[0]) h = ((c[1] - c[2]) / d) % 6;
      else if (max === c[1]) h = (c[2] - c[0]) / d + 2;
      else h = (c[0] - c[1]) / d + 4;
      h = (h * 60 + 360) % 360;
    }
    return { h: h, s: max ? d / max : 0, v: max };
  }

  /** Botão da barra, no estilo da anotação (annotations.css). */
  /** Texto que vem do DADO, pronto para entrar em HTML montado por
      concatenação. É a ÚNICA função de escape do projeto (replay, anotação e
      prancheta): nome de jogador, arma, lugar e frase gerada passam por aqui
      antes de qualquer innerHTML. Onde der, prefira textContent. */
  var ESCAPES = { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" };
  // O relógio do jogo num instante (segundos desde o fim do freeze): 1:55
  // descendo e, depois do plant, os 40 s da bomba, congelados no desarme ou na
  // explosão (`fim`). Uma função só para o replay e a prancheta; o espelho em
  // Python é metrics/tactics.relogio.
  function relogio(t, plant, fim, segundosDoRound, segundosDaBomba) {
    function mmss(s) {
      s = Math.max(0, s);
      var m = Math.floor(s / 60), r = Math.floor(s % 60);
      return m + ":" + (r < 10 ? "0" : "") + r;
    }
    if (plant !== null && plant !== undefined && t >= plant) {
      var desde = (fim === null || fim === undefined ? t : Math.min(t, fim)) - plant;
      return mmss(segundosDaBomba - desde);
    }
    return mmss(segundosDoRound - t);
  }

  function esc(v) {
    if (v === null || v === undefined) return "";
    return String(v).replace(/[&<>"']/g, function (ch) { return ESCAPES[ch]; });
  }

  function botao(texto, titulo, aoClicar, classe) {
    var b = document.createElement("button");
    b.type = "button";
    b.className = "anot-b" + (classe ? " " + classe : "");
    b.textContent = texto;
    b.title = titulo;
    b.setAttribute("aria-label", titulo);
    b.addEventListener("click", aoClicar);
    return b;
  }

  /** O seletor de cor, ligado ao estado de quem o usa.

      c.estado        objeto com cor, recentes, corPendente e hsv -- o seletor
                      lê e escreve nele (é o S da página)
      c.armazem       o de criaArmazem, para lembrar as cores recentes
      c.chaveRecentes chave das recentes no localStorage
      c.maxRecentes   quantas recentes guardar
      c.palco         função que devolve o elemento que limita o seletor
      c.aoMudar       chamado depois de toda mudança de cor aplicada
   */
  function seletorDeCor(c) {
    var S = c.estado;

    function aplicaCor(hex) {
      var cor = normalizaCor(hex);
      if (!cor) return;
      S.cor = cor;
      S.recentes = [cor].concat(S.recentes.filter(function (x) { return x !== cor; })).slice(0, c.maxRecentes);
      c.armazem.grava("localStorage", c.chaveRecentes, JSON.stringify(S.recentes));
      c.aoMudar();
    }

    function seletorAberto() {
      var pop = document.getElementById("anot-seletor");
      return !!pop && !pop.hidden;
    }

    function abreSeletor() {
      var pop = document.getElementById("anot-seletor");
      S.corPendente = S.cor;
      sincronizaSeletor(null);
      pop.hidden = false;
      posicionaSeletor(pop);
      document.getElementById("anot-cor-seta").setAttribute("aria-expanded", "true");
      // sem rolar: o painel tem overflow escondido, e focar algo que passa da
      // borda faria o navegador deslizar a barra inteira para o lado
      document.getElementById("anot-cor-sv").focus({ preventScroll: true });
    }

    /** O seletor abre para baixo da bolinha, mas nunca para fora do painel: a
        bolinha pode estar perto da borda direita dependendo da largura da tela. */
    function posicionaSeletor(pop) {
      var MARGEM = 8;
      pop.style.left = "0px";
      var r = pop.getBoundingClientRect(), lim = c.palco().getBoundingClientRect();
      var desloca = 0;
      if (r.right > lim.right - MARGEM) desloca = lim.right - MARGEM - r.right;
      if (r.left + desloca < lim.left + MARGEM) desloca = lim.left + MARGEM - r.left;
      pop.style.left = desloca + "px";
    }

    /** Fechar o seletor APLICA a cor escolhida: à bolinha e aos PRÓXIMOS traços.
        Traço já feito guarda a própria cor e não muda. */
    function fechaSeletor() {
      if (!seletorAberto()) return;
      document.getElementById("anot-seletor").hidden = true;
      document.getElementById("anot-cor-seta").setAttribute("aria-expanded", "false");
      if (S.corPendente) aplicaCor(S.corPendente);
      S.corPendente = null;
    }

    /** Mantém o seletor igual à cor pendente. `origem` diz de onde veio a
        mudança: o campo que o usuário está digitando não é reescrito (senão o
        cursor pula), e a posição HSV não é recalculada a partir do hex quando foi
        ela que mudou -- num cinza a matiz não existe no hex, e a barra pularia
        para o vermelho. */
    function sincronizaSeletor(origem) {
      var cor = S.corPendente || S.cor;
      if (origem !== "sv" && origem !== "matiz") S.hsv = paraHsv(cor);
      var hsv = S.hsv;

      var sv = document.getElementById("anot-cor-sv");
      sv.style.backgroundColor = deHsv(hsv.h, 1, 1);
      var alca = document.getElementById("anot-cor-sv-alca");
      alca.style.left = (hsv.s * 100) + "%";
      alca.style.top = ((1 - hsv.v) * 100) + "%";
      alca.style.background = cor;
      sv.setAttribute("aria-valuetext", "saturação " + Math.round(hsv.s * 100) +
                      "%, brilho " + Math.round(hsv.v * 100) + "%");
      var matiz = document.getElementById("anot-cor-matiz");
      document.getElementById("anot-cor-matiz-alca").style.left = (hsv.h / 360 * 100) + "%";
      matiz.setAttribute("aria-valuenow", String(Math.round(hsv.h)));

      document.getElementById("anot-cor-amostra").style.background = cor;
      var hex = document.getElementById("anot-cor-hex");
      if (origem !== "hex") { hex.value = cor; hex.removeAttribute("aria-invalid"); }
    }

    /** Arrastar dentro de uma área (quadrado ou barra) com o mesmo código para
        mouse, toque e caneta. `aoMover` recebe a posição relativa, de 0 a 1. */
    function arrastavel(el, aoMover) {
      var ativo = false;
      function posicao(e) {
        var r = el.getBoundingClientRect();
        aoMover(Math.min(1, Math.max(0, (e.clientX - r.left) / r.width)),
                Math.min(1, Math.max(0, (e.clientY - r.top) / r.height)));
      }
      el.addEventListener("pointerdown", function (e) {
        ativo = true;
        el.setPointerCapture(e.pointerId);
        posicao(e);
        e.preventDefault();
      });
      el.addEventListener("pointermove", function (e) { if (ativo) posicao(e); });
      el.addEventListener("pointerup", function () { ativo = false; });
      el.addEventListener("pointercancel", function () { ativo = false; });
    }

    function montaCor() {
      var grupo = document.createElement("div");
      grupo.className = "anot-grupo anot-cor";
      grupo.id = "anot-cor";

      var bolinha = botao("", "Cor atual (clique para escolher outra)", function () {
        if (seletorAberto()) fechaSeletor(); else abreSeletor();
      }, "anot-bolinha");
      bolinha.className = "anot-bolinha";
      bolinha.id = "anot-cor-atual";
      grupo.appendChild(bolinha);

      var seta = botao("▾", "Escolher cor", function () {
        if (seletorAberto()) fechaSeletor(); else abreSeletor();
      }, "anot-seta");
      seta.id = "anot-cor-seta";
      seta.setAttribute("aria-haspopup", "dialog");
      seta.setAttribute("aria-expanded", "false");
      grupo.appendChild(seta);

      var recentes = document.createElement("div");
      recentes.className = "anot-recentes";
      recentes.id = "anot-recentes";
      recentes.setAttribute("role", "group");
      recentes.setAttribute("aria-label", "Cores usadas recentemente");
      grupo.appendChild(recentes);

      var pop = document.createElement("div");
      pop.className = "anot-seletor";
      pop.id = "anot-seletor";
      pop.hidden = true;
      pop.setAttribute("role", "dialog");
      pop.setAttribute("aria-label", "Escolher cor");

      function entrada(tipo, id) {
        var i = document.createElement("input");
        i.type = tipo;
        i.id = id;
        i.spellcheck = false;
        i.autocomplete = "off";
        return i;
      }

      // O ESPECTRO é o seletor: um quadrado de saturação x brilho sobre a matiz
      // escolhida na barra do arco-íris. Clicar ou arrastar escolhe a cor vendo a
      // cor -- o código hex fica embaixo, só para quem quiser colar um valor.
      function mudaHsv(origem) {
        S.corPendente = deHsv(S.hsv.h, S.hsv.s, S.hsv.v);
        sincronizaSeletor(origem);
      }

      var sv = document.createElement("div");
      sv.className = "anot-sv";
      sv.id = "anot-cor-sv";
      sv.tabIndex = 0;
      sv.setAttribute("role", "slider");
      sv.setAttribute("aria-label", "Saturação e brilho");
      var svAlca = document.createElement("div");
      svAlca.className = "anot-sv-alca";
      svAlca.id = "anot-cor-sv-alca";
      sv.appendChild(svAlca);
      arrastavel(sv, function (x, y) { S.hsv.s = x; S.hsv.v = 1 - y; mudaHsv("sv"); });
      sv.addEventListener("keydown", function (e) {
        var passo = e.shiftKey ? 0.1 : 0.02;
        var d = { ArrowLeft: [-passo, 0], ArrowRight: [passo, 0], ArrowUp: [0, passo], ArrowDown: [0, -passo] }[e.key];
        if (!d) return;
        e.preventDefault();
        S.hsv.s = Math.min(1, Math.max(0, S.hsv.s + d[0]));
        S.hsv.v = Math.min(1, Math.max(0, S.hsv.v + d[1]));
        mudaHsv("sv");
      });
      pop.appendChild(sv);

      var matiz = document.createElement("div");
      matiz.className = "anot-matiz";
      matiz.id = "anot-cor-matiz";
      matiz.tabIndex = 0;
      matiz.setAttribute("role", "slider");
      matiz.setAttribute("aria-label", "Matiz");
      matiz.setAttribute("aria-valuemin", "0");
      matiz.setAttribute("aria-valuemax", "360");
      var matizAlca = document.createElement("div");
      matizAlca.className = "anot-matiz-alca";
      matizAlca.id = "anot-cor-matiz-alca";
      matiz.appendChild(matizAlca);
      arrastavel(matiz, function (x) {
        S.hsv.h = Math.min(359.9, x * 360);
        // escolher a matiz num cinza não mostraria cor nenhuma: leva para a
        // cor cheia, que é o que quem clicou no arco-íris quer ver
        if (S.hsv.s < 0.05 || S.hsv.v < 0.05) { S.hsv.s = 1; S.hsv.v = 1; }
        mudaHsv("matiz");
      });
      matiz.addEventListener("keydown", function (e) {
        var d = { ArrowLeft: -1, ArrowRight: 1 }[e.key];
        if (!d) return;
        e.preventDefault();
        S.hsv.h = (S.hsv.h + d * (e.shiftKey ? 30 : 5) + 360) % 360;
        mudaHsv("matiz");
      });
      pop.appendChild(matiz);

      var linha = document.createElement("div");
      linha.className = "anot-cor-linha";
      var amostra = document.createElement("span");
      amostra.className = "anot-amostra";
      amostra.id = "anot-cor-amostra";
      amostra.setAttribute("aria-hidden", "true");
      linha.appendChild(amostra);
      var hex = entrada("text", "anot-cor-hex");
      hex.maxLength = 22;
      hex.setAttribute("aria-label", "Código da cor (hex ou rgb)");
      hex.placeholder = "#eb6834";
      hex.addEventListener("input", function () {
        var cor = normalizaCor(hex.value);
        if (!cor) { hex.setAttribute("aria-invalid", "true"); return; }
        hex.removeAttribute("aria-invalid");
        S.corPendente = cor;
        sincronizaSeletor("hex");
      });
      linha.appendChild(hex);
      pop.appendChild(linha);

      var ok = botao("Aplicar", "Aplicar a cor e fechar", fechaSeletor, "principal");
      pop.appendChild(ok);

      // Enter em qualquer campo fecha e aplica, como o botão
      pop.addEventListener("keydown", function (e) {
        if (e.key === "Enter") { e.preventDefault(); fechaSeletor(); }
      });
      grupo.appendChild(pop);

      // Clique fora do seletor fecha (e aplica). Em captura, para funcionar
      // mesmo quando o clique cai num elemento que interrompe a propagação.
      document.addEventListener("pointerdown", function (e) {
        if (seletorAberto() && !grupo.contains(e.target)) fechaSeletor();
      }, true);

      return grupo;
    }

    function atualizaCores() {
      var atual = document.getElementById("anot-cor-atual");
      if (atual) {
        atual.style.background = S.cor;
        atual.dataset.cor = S.cor;
        atual.setAttribute("aria-label", "Cor atual " + S.cor + " (clique para escolher outra)");
      }
      var host = document.getElementById("anot-recentes");
      if (!host) return;
      // só redesenha a fileira se ela mudou, para não perder o foco do teclado
      var assinatura = S.recentes.join(",");
      if (host.dataset.assinatura === assinatura) return;
      host.dataset.assinatura = assinatura;
      host.innerHTML = "";
      S.recentes.forEach(function (cor) {
        var b = botao("", "Usar " + cor, function () { aplicaCor(cor); }, "anot-recente");
        b.className = "anot-recente";
        b.style.background = cor;
        b.dataset.recente = cor;
        host.appendChild(b);
      });
    }

    return {
      montaCor: montaCor,
      atualizaCores: atualizaCores,
      aplicaCor: aplicaCor,
      seletorAberto: seletorAberto,
      fechaSeletor: fechaSeletor
    };
  }


  /* ---------------------------------------------------------------------
     O round inteiro para a prancheta (fase 9). Espelho de
     metrics/round_na_prancheta.py: o mesmo round do replay dá o mesmo dado
     nos dois lados (há teste).
     --------------------------------------------------------------------- */
  /** Índices dos pontos [t, x, y] que ficam no Douglas-Peucker com a distância
      SINCRONIZADA no tempo (o erro de posição no horário fica <= tol). */
  function douglasPeuckerNoTempo(pontos, tol) {
    var n = pontos.length, i;
    if (n <= 2 || tol <= 0) { var todos = []; for (i = 0; i < n; i++) todos.push(i); return todos; }
    var fica = new Array(n).fill(false);
    fica[0] = fica[n - 1] = true;
    var pilha = [[0, n - 1]];
    while (pilha.length) {
      var ab = pilha.pop(), a = ab[0], b = ab[1];
      var ta = pontos[a][0], ax = pontos[a][1], ay = pontos[a][2];
      var tb = pontos[b][0], bx = pontos[b][1], by = pontos[b][2];
      var pior = -1, ip = -1;
      for (i = a + 1; i < b; i++) {
        var f = tb > ta ? (pontos[i][0] - ta) / (tb - ta) : 0;
        var d = Math.hypot(pontos[i][1] - (ax + (bx - ax) * f), pontos[i][2] - (ay + (by - ay) * f));
        if (d > pior) { pior = d; ip = i; }
      }
      if (ip >= 0 && pior > tol) { fica[ip] = true; pilha.push([a, ip]); pilha.push([ip, b]); }
    }
    var out = [];
    for (i = 0; i < n; i++) if (fica[i]) out.push(i);
    return out;
  }

  /** Pontos [quadro, x, y, direção, andar] do trecho vivo de um jogador do
      replay e o quadro da morte (null se terminou vivo). Ficam sempre o
      primeiro e o último quadro vivo, os dois lados de cada troca de andar e
      os quadros `fixos` (o instante de onde a prancheta veio). */
  function caminhoDoJogador(p, tol, fixos) {
    var vivos = [], i;
    for (i = 0; i < p.alive.length; i++) if (p.alive[i]) vivos.push(i);
    if (!vivos.length) return { pontos: [], morte: null };
    var ini = vivos[0], fim = vivos[vivos.length - 1];
    var lv = p.lv || p.x.map(function () { return 0; });
    var marcos = {};
    marcos[ini] = true; marcos[fim] = true;
    for (var k = ini + 1; k <= fim; k++) if (lv[k] !== lv[k - 1]) { marcos[k - 1] = true; marcos[k] = true; }
    (fixos || []).forEach(function (q) { if (q >= ini && q <= fim) marcos[q] = true; });
    var lista = Object.keys(marcos).map(Number).sort(function (a, b) { return a - b; });
    var ficam = {};
    lista.forEach(function (q) { ficam[q] = true; });
    for (var m = 0; m + 1 < lista.length; m++) {
      var trecho = [];
      for (i = lista[m]; i <= lista[m + 1]; i++) trecho.push(i);
      douglasPeuckerNoTempo(trecho.map(function (q) { return [q, p.x[q], p.y[q]]; }), tol)
        .forEach(function (s) { ficam[trecho[s]] = true; });
    }
    var idx = Object.keys(ficam).map(Number).sort(function (a, b) { return a - b; });
    return { pontos: idx.map(function (q) { return [q, p.x[q], p.y[q], p.d[q], lv[q]]; }),
             morte: fim + 1 < p.alive.length ? fim + 1 : null };
  }

  /** O round no formato que viaja na URL (quadros, não segundos). `quadro` é o
      instante de onde a prancheta veio. Espelho de payload_do_round. */
  function roundParaPrancheta(hz, rd, tol, partida, quadro) {
    var plant = (rd.events || []).filter(function (e) { return e.type === "plant"; })[0] || null;
    var fixos = quadro === undefined || quadro === null ? [] : [quadro];
    var efeitos = {};
    (rd.smokes || []).concat(rd.fires || []).forEach(function (z) {
      if (z.l && !efeitos[z.l.id]) efeitos[z.l.id] = z;
    });
    return {
      partida: partida, round: rd.round, hz: hz,
      jogadores: rd.players.map(function (p) {
        var c = caminhoDoJogador(p, tol, fixos);
        return { nome: p.name, lado: p.side, pontos: c.pontos, morte: c.morte };
      }),
      granadas: (rd.nades || []).filter(function (g) { return g.x && g.x.length; }).map(function (g) {
        var l = g.l || {};
        var z = (g.k === "smoke" || g.k === "molotov") && l.id !== undefined ? efeitos[l.id] || null : null;
        return { k: g.k, by: g.by === undefined ? null : g.by, f: g.f0, o: [g.x[0], g.y[0]],
                 d: [g.x[g.x.length - 1], g.y[g.y.length - 1]], l: l.id !== undefined ? l.id : null,
                 lo: l.o ? l.o.slice(0, 2) : null,
                 v: z ? z.f0 - g.f0 : g.x.length - 1, e: z ? z.f1 - z.f0 : null };
      }),
      bomba: plant ? { f: plant.f, x: plant.x, y: plant.y, por: plant.player === undefined ? null : plant.player } : null
    };
  }

  /** Objeto -> deflate (CompressionStream, formato zlib) -> base64url, para ir
      no hash. Assíncrono (devolve uma Promise). */
  function compactaParaUrl(obj) {
    var bruto = new Blob([JSON.stringify(obj)]).stream().pipeThrough(new CompressionStream("deflate"));
    return new Response(bruto).arrayBuffer().then(function (buf) {
      var bytes = new Uint8Array(buf), s = "";
      for (var i = 0; i < bytes.length; i += 0x8000) s += String.fromCharCode.apply(null, bytes.subarray(i, i + 0x8000));
      return btoa(s).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
    });
  }

  /** O caminho de volta: base64url -> inflate -> objeto (Promise). */
  function descompactaDaUrl(texto) {
    var b64 = String(texto).replace(/-/g, "+").replace(/_/g, "/");
    while (b64.length % 4) b64 += "=";
    var bin = atob(b64), bytes = new Uint8Array(bin.length);
    for (var i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
    var fluxo = new Blob([bytes]).stream().pipeThrough(new DecompressionStream("deflate"));
    return new Response(fluxo).text().then(JSON.parse);
  }

  return {
    esc: esc, relogio: relogio, token: token, corComAlfa: corComAlfa,
    douglasPeuckerNoTempo: douglasPeuckerNoTempo, caminhoDoJogador: caminhoDoJogador,
    roundParaPrancheta: roundParaPrancheta, compactaParaUrl: compactaParaUrl, descompactaDaUrl: descompactaDaUrl,
    MAX_LADO_INTERNO: MAX_LADO_INTERNO,
    ZOOM_MIN: ZOOM_MIN, ZOOM_MAX: ZOOM_MAX, ZOOM_PASSO: ZOOM_PASSO,
    VELOCIDADES: VELOCIDADES,
    RAIO_SMOKE_UNIDADES: RAIO_SMOKE_UNIDADES,
    RAIO_MOLOTOV_UNIDADES: RAIO_MOLOTOV_UNIDADES,
    NADE_COLOR: NADE_COLOR,
    jogoParaPixel: jogoParaPixel,
    pixelParaJogo: pixelParaJogo,
    eventoParaPixel: eventoParaPixel,
    applyView: applyView,
    aplicaZoom: aplicaZoom,
    limitaPan: limitaPan,
    caixaDoMapa: caixaDoMapa,
    tamanhoInterno: tamanhoInterno,
    agrupaPorQuadro: agrupaPorQuadro,
    vigiaDensidade: vigiaDensidade,
    emTelaCheia: emTelaCheia,
    alternaTelaCheia: alternaTelaCheia,
    criaArmazem: criaArmazem,
    lerJson: lerJson,
    caminhoDoTraco: caminhoDoTraco,
    desenhaSeta: desenhaSeta,
    tracoCurtoDemais: tracoCurtoDemais,
    tracoEncosta: tracoEncosta,
    desenhaArea: desenhaArea,
    nadeGlyph: nadeGlyph,
    PONTA_DISTANCIA: PONTA_DISTANCIA,
    NOME_ACIMA_COM_DIRECAO: NOME_ACIMA_COM_DIRECAO,
    anguloDeTela: anguloDeTela,
    interpolaAngulo: interpolaAngulo,
    desenhaJogador: desenhaJogador,
    defineAnelDuplo: defineAnelDuplo,
    RADAR_AJUSTE: RADAR_AJUSTE,
    RADAR_AJUSTE_PADRAO: RADAR_AJUSTE_PADRAO,
    ajusteDoRadar: ajusteDoRadar,
    radarProcessado: radarProcessado,
    rotulosInicia: rotulosInicia,
    rotulo: rotulo,
    rotulosDesenha: rotulosDesenha,
    normalizaCor: normalizaCor,
    botao: botao,
    seletorDeCor: seletorDeCor
  };
})();
