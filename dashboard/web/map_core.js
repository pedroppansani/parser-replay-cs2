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

  // Smoke e Molotov ocupam área, então são desenhados como zona e não como
  // ponto. O raio segue o raio real de efeito no jogo, em UNIDADES DE JOGO, e
  // é convertido pela mesma escala do radar por quem desenha. (Medida no jogo.)
  var RAIO_SMOKE_UNIDADES = 144;
  var RAIO_MOLOTOV_UNIDADES = 120;

  // Cor de cada tipo de granada no replay: a paleta validada para daltonismo e
  // contraste da página da partida (decisão 10).
  var NADE_COLOR = { smoke: "#9fb0c2", molotov: "#eb6834", he: "#d1495b", flash: "#e8b53a", decoy: "#7d8a99" };

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

    // Contorno escuro por baixo do claro: o radar tem áreas claras E escuras, e
    // um traço branco sozinho sumia sobre o concreto claro da Mirage.
    ctx.shadowColor = "rgba(10,16,24,0.55)";
    ctx.shadowBlur = 3;
    ctx.fillStyle = col;
    ctx.strokeStyle = "rgba(255,255,255,0.95)";
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
      ctx.fillStyle = "rgba(255,255,255,0.95)";
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
      ctx.strokeStyle = "rgba(255,255,255,0.85)";
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

      O estado do contexto (fonte, alinhamento, espessura) fica como o desenho
      deixa, sem save/restore em volta: é o mesmo efeito que o código tinha
      quando vivia dentro do draw() do replay. */
  function desenhaJogador(ctx, X, Y, o) {
    var color = o.cor;

    if (o.estado === "morto") {
      ctx.globalAlpha = 0.5;
      ctx.strokeStyle = color;
      ctx.lineWidth = 1.6;
      ctx.beginPath();
      ctx.moveTo(X - 3.5, Y - 3.5); ctx.lineTo(X + 3.5, Y + 3.5);
      ctx.moveTo(X + 3.5, Y - 3.5); ctx.lineTo(X - 3.5, Y + 3.5);
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
      ctx.lineWidth = 2;
      ctx.beginPath(); ctx.arc(X, Y, 5.5, 0, Math.PI * 2); ctx.stroke();
      // seta indicando se está acima ou abaixo do andar mostrado
      ctx.fillStyle = color;
      ctx.font = "700 9px 'DM Mono', ui-monospace, monospace";
      ctx.textAlign = "center";
      ctx.fillText(o.acima ? "▼" : "▲", X, Y + 3);
      ctx.globalAlpha = 1;
      return;
    }

    ctx.save();
    ctx.shadowColor = "rgba(8,12,18,0.55)";
    ctx.shadowBlur = 6;
    ctx.shadowOffsetY = 1;
    ctx.fillStyle = "#fff";
    ctx.beginPath(); ctx.arc(X, Y, 8.2, 0, Math.PI * 2); ctx.fill();
    ctx.restore();

    ctx.fillStyle = color;
    ctx.beginPath(); ctx.arc(X, Y, 6, 0, Math.PI * 2); ctx.fill();

    // Cegueira: é o estado que explica por que um jogador parou de mirar, ou
    // andou pra frente sem reagir. Sem marcar isso no mapa, a sequência mais
    // comum do CS (flash entra, time entra atrás) fica sem causa visível.
    if (o.cego) {
      ctx.strokeStyle = NADE_COLOR.flash;
      ctx.globalAlpha = 0.9;
      ctx.lineWidth = 2.2;
      ctx.setLineDash([3, 3]);
      ctx.beginPath(); ctx.arc(X, Y, 12.5, 0, Math.PI * 2); ctx.stroke();
      ctx.setLineDash([]);
      ctx.globalAlpha = 1;
    }

    // anel de vida: encolhe conforme o jogador toma dano
    var hp = Math.max(0, Math.min(100, o.hp)) / 100;
    if (hp < 1) {
      ctx.strokeStyle = "#fff";
      ctx.lineWidth = 2.4;
      ctx.beginPath();
      ctx.arc(X, Y, 10.4, -Math.PI / 2, -Math.PI / 2 + hp * Math.PI * 2);
      ctx.stroke();
    }

    ctx.font = "500 12px 'DM Mono', ui-monospace, monospace";
    ctx.textAlign = "center";
    ctx.lineWidth = 3;
    ctx.strokeStyle = "rgba(14,20,27,0.85)";
    ctx.strokeText(o.nome.slice(0, 9), X, Y - 14);
    ctx.fillStyle = "#eef2f7";
    ctx.fillText(o.nome.slice(0, 9), X, Y - 14);
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

  return {
    MAX_LADO_INTERNO: MAX_LADO_INTERNO,
    ZOOM_MIN: ZOOM_MIN, ZOOM_MAX: ZOOM_MAX, ZOOM_PASSO: ZOOM_PASSO,
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
    emTelaCheia: emTelaCheia,
    alternaTelaCheia: alternaTelaCheia,
    criaArmazem: criaArmazem,
    lerJson: lerJson,
    caminhoDoTraco: caminhoDoTraco,
    desenhaSeta: desenhaSeta,
    nadeGlyph: nadeGlyph,
    desenhaJogador: desenhaJogador,
    normalizaCor: normalizaCor,
    botao: botao,
    seletorDeCor: seletorDeCor
  };
})();
