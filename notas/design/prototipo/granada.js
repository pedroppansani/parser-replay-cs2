/* Granada real x granada desenhada (fase 11): réplica FIEL, para o protótipo, do que o map_core.js desenha
   (nadeGlyph + anelDoGlifo + caminhoDoGlifo, lidos em 2026-10-13), mais três propostas de variante.
   Tudo em "px do radar" (1024 x 1024); `k` = px de tela por px do radar (0,508 a 1440; 0,321 a 375).
   Não é código para copiar para o projeto: o protótipo é referência (o mapa de lá é canvas do map_core.js). */
(function () {
  "use strict";
  var ANEL_C = 2.5, ANEL_H = 1.5, TRACO = [5, 4];          // map_core.js: ANEL_CONTORNO, ANEL_HALO, TRACEJADO_DO_DESENHO
  var R_REAL = 5.5, R_DESENHADA = 7, ALFA = 0.85;          // replay: 5 a 5,5 ; RAIO_GLIFO_DESENHADO ; ALFA_GRANADA_DESENHADA
  var RADAR = 1024;
  var MESMO_TAMANHO = false;         // medição: a desenhada com o raio da real, para isolar tracejado, alfa e forma do tamanho

  function tok(n) { return getComputedStyle(document.documentElement).getPropertyValue("--" + n).trim(); }
  function corComAlfa(nome, a) {
    var h = tok(nome).replace("#", ""), r = parseInt(h.slice(0, 2), 16), g = parseInt(h.slice(2, 4), 16), b = parseInt(h.slice(4, 6), 16);
    return "rgba(" + r + "," + g + "," + b + "," + a + ")";
  }

  function caminho(ctx, kind, r, ang) {
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
      ctx.moveTo(p0[0], p0[1]); ctx.quadraticCurveTo(q1[0], q1[1], p1[0], p1[1]); ctx.quadraticCurveTo(q2[0], q2[1], p0[0], p0[1]);
    } else {
      ctx.arc(-r * 0.52, r * 0.12, r * 0.62, 0, Math.PI * 2);
      ctx.moveTo(r * 1.14, r * 0.12); ctx.arc(r * 0.52, r * 0.12, r * 0.62, 0, Math.PI * 2);
      ctx.moveTo(r * 0.78, -r * 0.3); ctx.arc(0, -r * 0.3, r * 0.78, 0, Math.PI * 2);
    }
  }

  function anel(ctx, kind, r, ang, traco) {
    ctx.save(); ctx.lineJoin = "round";
    if (traco) ctx.setLineDash(traco);
    caminho(ctx, kind, r, ang);
    ctx.lineWidth = 2 * (ANEL_C + ANEL_H) + (kind === "he" ? 2 : 0); ctx.strokeStyle = tok("tinta"); ctx.stroke();
    ctx.lineWidth = 2 * ANEL_C + (kind === "he" ? 2 : 0); ctx.strokeStyle = tok("contorno"); ctx.stroke();
    ctx.restore();
  }

  /* o corpo do glifo (igual ao nadeGlyph); `oco` = proposta V2: só o contorno na cor da granada, com o radar a 55% por dentro */
  function corpo(ctx, kind, r, col, ang, oco, k) {
    ctx.shadowColor = corComAlfa("contorno", 0.55); ctx.shadowBlur = 3;
    ctx.fillStyle = col; ctx.strokeStyle = corComAlfa("tinta", 0.95); ctx.lineWidth = 1.2; ctx.lineJoin = "round";
    var preenche = function () {
      if (oco) { ctx.save(); ctx.shadowBlur = 0; ctx.fillStyle = corComAlfa("radar", 0.55); ctx.fill(); ctx.restore();
                 ctx.save(); ctx.shadowBlur = 0; ctx.lineWidth = Math.max(1.5 / k, 1.2); ctx.strokeStyle = col; ctx.stroke(); ctx.restore(); }
      else { ctx.fill(); ctx.stroke(); }
    };
    if (kind === "flash") {
      caminho(ctx, kind, r, ang); preenche();
      ctx.shadowBlur = 0; ctx.beginPath(); ctx.arc(0, 0, r * 0.3, 0, Math.PI * 2); ctx.fillStyle = corComAlfa("tinta", 0.95); ctx.fill();
    } else if (kind === "he") {
      caminho(ctx, kind, r, ang); ctx.lineWidth = 2; ctx.strokeStyle = col; ctx.stroke();
      ctx.shadowBlur = 0; ctx.lineWidth = 0.9; ctx.strokeStyle = corComAlfa("tinta", 0.85); ctx.stroke();
    } else if (kind === "molotov") {
      ctx.save(); ctx.rotate((ang || 0) + Math.PI / 2); ctx.beginPath();
      ctx.moveTo(0, -r * 1.5); ctx.quadraticCurveTo(r * 0.95, -r * 0.15, 0, r); ctx.quadraticCurveTo(-r * 0.95, -r * 0.15, 0, -r * 1.5);
      preenche(); ctx.restore();
    } else {
      ctx.beginPath();
      ctx.arc(-r * 0.52, r * 0.12, r * 0.62, 0, Math.PI * 2); ctx.arc(r * 0.52, r * 0.12, r * 0.62, 0, Math.PI * 2); ctx.arc(0, -r * 0.3, r * 0.78, 0, Math.PI * 2);
      preenche();
    }
  }

  /* Variantes:
     real          granada que aconteceu: anel duplo cheio, corpo a 100%, r 5,5 (map_core.js)
     atual         a desenhada do projeto: anel duplo tracejado (5/4 px do radar), corpo a 85%, r 7
     atual_solido  a mesma, sem tracejado (isola o efeito do tracejado)
     atual_cheia   a mesma, sem alfa (isola o efeito do 85%)
     v1            tracejado medido em px de TELA (3,5 on / 3 off), corpo 100%, r 7
     v2            v1 + corpo OCO (contorno na cor da granada, radar a 55% por dentro)
     v3            v1 + carimbo: quadrado cheio de 4 px de tela no canto superior direito (forma que sobrevive ao tamanho)
     v3p           o mesmo carimbo, com 3 px de tela
  */
  function desenha(ctx, kind, variante, x, y, k, col) {
    var ang = -Math.PI / 2, real = variante === "real";
    var r = (real || MESMO_TAMANHO) ? R_REAL : R_DESENHADA;
    var traco = null, alfa = 1, oco = false, carimbo = false;
    if (variante === "atual") { traco = TRACO; alfa = ALFA; }
    else if (variante === "atual_solido") { alfa = ALFA; }
    else if (variante === "atual_cheia") { traco = TRACO; }
    else if (variante === "v1") { traco = [3.5 / k, 3 / k]; }
    else if (variante === "v2") { traco = [3.5 / k, 3 / k]; oco = true; }
    else if (variante === "v3") { traco = [3.5 / k, 3 / k]; carimbo = 4; }
    else if (variante === "v3p") { traco = [3.5 / k, 3 / k]; carimbo = 3; }
    ctx.save(); ctx.translate(x, y);
    anel(ctx, kind, r, ang, traco);
    ctx.globalAlpha *= alfa;
    corpo(ctx, kind, r, col || tok(kind), ang, oco, k);
    ctx.restore();
    if (carimbo) {
      var s = carimbo / k, ox = x + r * 1.7 + 2 / k, oy = y - r * 1.7 - 2 / k;
      ctx.save(); ctx.fillStyle = tok("contorno"); ctx.fillRect(ox - s * 0.5 - 1 / k, oy - s * 0.5 - 1 / k, s + 2 / k, s + 2 / k);
      ctx.fillStyle = tok("tinta"); ctx.fillRect(ox - s * 0.5, oy - s * 0.5, s, s); ctx.restore();
    }
  }

  /* um cenário: o radar centrado em (px, py) (px do radar de 1024), na escala k, com densidade `dpr`; W x W px de tela */
  function cenario(img, px, py, k, dpr, W) {
    var c = document.createElement("canvas"); c.width = Math.round(W * dpr); c.height = Math.round(W * dpr);
    var ctx = c.getContext("2d");
    ctx.setTransform(k * dpr, 0, 0, k * dpr, W / 2 * dpr - px * k * dpr, W / 2 * dpr - py * k * dpr);
    ctx.fillStyle = tok("radar"); ctx.fillRect(0, 0, RADAR, RADAR);
    ctx.drawImage(img, 0, 0, RADAR, RADAR);
    ctx.setTransform(k * dpr, 0, 0, k * dpr, W / 2 * dpr, W / 2 * dpr);
    return { canvas: c, ctx: ctx };
  }

  function carrega(src) {
    return new Promise(function (ok, erro) { var i = new Image(); i.onload = function () { ok(i); }; i.onerror = erro; i.src = src; });
  }

  /* medição: devolve, por variante, ΔE76 médio e porcentagem de pixels diferentes entre a granada REAL e a variante,
     sobre posições do radar sorteadas com semente fixa (28) */
  function lab(r, g, b) {
    var f = function (c) { c /= 255; return c <= 0.04045 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4); };
    var R = f(r), G = f(g), B = f(b);
    var x = (R * 0.4124 + G * 0.3576 + B * 0.1805) / 0.95047, y = R * 0.2126 + G * 0.7152 + B * 0.0722, z = (R * 0.0193 + G * 0.1192 + B * 0.9505) / 1.08883;
    var h = function (t) { return t > 0.008856 ? Math.cbrt(t) : 7.787 * t + 16 / 116; };
    return [116 * h(y) - 16, 500 * (h(x) - h(y)), 200 * (h(y) - h(z))];
  }
  function mulberry(seed) { return function () { seed |= 0; seed = seed + 0x6D2B79F5 | 0; var t = Math.imul(seed ^ seed >>> 15, 1 | seed); t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t; return ((t ^ t >>> 14) >>> 0) / 4294967296; }; }

  function posicoes(img, n) {
    var c = document.createElement("canvas"); c.width = 256; c.height = 256; var g = c.getContext("2d"); g.drawImage(img, 0, 0, 256, 256);
    var d = g.getImageData(0, 0, 256, 256).data, rnd = mulberry(28), out = [], bg = tok("radar");
    var br = parseInt(bg.slice(1, 3), 16), bgG = parseInt(bg.slice(3, 5), 16), bb = parseInt(bg.slice(5, 7), 16), tent = 0;
    while (out.length < n && tent++ < 5000) {
      var x = 16 + Math.floor(rnd() * 224), y = 16 + Math.floor(rnd() * 224), i = (y * 256 + x) * 4;
      if (Math.abs(d[i] - br) + Math.abs(d[i + 1] - bgG) + Math.abs(d[i + 2] - bb) > 40) out.push([x * 4, y * 4]);
    }
    return out;
  }

  function dif(a, b, raio) {            // a, b: ImageData do mesmo tamanho; raio em px do canvas
    var w = a.width, cx = w / 2, cy = a.height / 2, soma = 0, n = 0, m5 = 0, m10 = 0;
    for (var y = 0; y < a.height; y++) for (var x = 0; x < w; x++) {
      if ((x - cx) * (x - cx) + (y - cy) * (y - cy) > raio * raio) continue;
      var i = (y * w + x) * 4, la = lab(a.data[i], a.data[i + 1], a.data[i + 2]), lb = lab(b.data[i], b.data[i + 1], b.data[i + 2]);
      var de = Math.hypot(la[0] - lb[0], la[1] - lb[1], la[2] - lb[2]);
      soma += de; n++; if (de >= 5) m5++; if (de >= 10) m10++;
    }
    return { medio: soma / n, p5: m5 / n, p10: m10 / n };
  }

  function mede(imgs, variantes, kinds, escalas, dprs, comparaCom) {
    var W = 40, saida = [];
    escalas.forEach(function (k) { dprs.forEach(function (dpr) { kinds.forEach(function (kind) { variantes.forEach(function (v) {
      var acc = [];
      Object.keys(imgs).forEach(function (mapa) {
        posicoes(imgs[mapa], 12).forEach(function (p) {
          var A = cenario(imgs[mapa], p[0], p[1], k, dpr, W), B = cenario(imgs[mapa], p[0], p[1], k, dpr, W);
          desenha(A.ctx, kind, comparaCom, 0, 0, k); desenha(B.ctx, kind, v, 0, 0, k);
          var da = A.ctx.getImageData(0, 0, A.canvas.width, A.canvas.height), db = B.ctx.getImageData(0, 0, B.canvas.width, B.canvas.height);
          acc.push(dif(da, db, 11 * dpr));        // raio de 11 px de tela: cobre o glifo, o anel e o carimbo
        });
      });
      var med = acc.map(function (o) { return o.medio; }).sort(function (a, b) { return a - b; });
      saida.push({ k: k, dpr: dpr, kind: kind, variante: v, comparaCom: comparaCom, n: acc.length,
        medio: med.reduce(function (s, x) { return s + x; }, 0) / med.length, p20: med[Math.floor(med.length * 0.2)],
        pior: med[0], p5: acc.reduce(function (s, o) { return s + o.p5; }, 0) / acc.length, p10: acc.reduce(function (s, o) { return s + o.p10; }, 0) / acc.length });
    }); }); }); });
    return saida;
  }

  window.Granada = { mesmoTamanho: function (v) { MESMO_TAMANHO = !!v; }, desenha: desenha, cenario: cenario, carrega: carrega, mede: mede, posicoes: posicoes, R_REAL: R_REAL, R_DESENHADA: R_DESENHADA };
})();
