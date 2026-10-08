/* Prancheta do protótipo: tática no tempo. Tudo o que se vê é função pura de `e`
   (segundos desde o fim do freeze), como na decisão 35. Dados ilustrativos. */
(function () {
  "use strict";
  var NS = "http://www.w3.org/2000/svg";
  var VEL = 37;            // px/s no radar de 760 px ≈ 250 u/s andando com faca (só para o protótipo)
  var PLANT = 52, FIM = 92; // plant aos 52 s decorridos (relógio 1:03); bomba explode aos 92 s
  var DUR = { smoke: 18, molotov: 7, flash: 0.6, he: 0.6 }, VOO = 1.6;

  var J = [
    { id: "sp", nome: "Spinx", lado: "tr", func: "entry", pts: [{ x: 668, y: 268, espera: 3 }, { x: 640, y: 420, espera: 14 }, { x: 560, y: 520 }, { x: 470, y: 560, marco: "entrada" }], olhar: 200 },
    { id: "xe", nome: "xertioN", lado: "tr", func: "trade", pts: [{ x: 652, y: 246, espera: 4 }, { x: 618, y: 468, espera: 12 }, { x: 505, y: 560 }], olhar: 210 },
    { id: "br", nome: "Brollan", lado: "tr", func: "suporte", pts: [{ x: 684, y: 292, espera: 2 }, { x: 630, y: 452, espera: 30 }, { x: 560, y: 560 }], olhar: 220 },
    { id: "to", nome: "torzsi", lado: "tr", func: "AWP", pts: [{ x: 640, y: 236, espera: 6 }, { x: 600, y: 440, espera: 25 }, { x: 520, y: 520 }], olhar: 230 },
    { id: "ji", nome: "Jimpphat", lado: "tr", func: "lurk", pts: [{ x: 672, y: 304, espera: 2 }, { x: 540, y: 330, espera: 10 }, { x: 430, y: 360 }], olhar: 180, morre: 48 }
  ];
  var REAL = [ // round que aconteceu: camada travada (fantasma)
    { nome: "NiKo", lado: "ct", func: "âncora", pts: [[0, 330, 560], [30, 420, 576], [60, 430, 560]] },
    { nome: "m0NESY", lado: "ct", func: "AWP", pts: [[0, 300, 520], [20, 262, 560], [60, 262, 560]] },
    { nome: "Spinx", lado: "tr", func: "entry", pts: [[0, 668, 268], [20, 610, 440], [34, 480, 566]] }
  ];
  var G = [
    { de: "br", tipo: "smoke", e: 15, para: [470, 520], rot: "smoke CT", onde: "da rampa" },
    { de: "to", tipo: "smoke", e: 17, para: [520, 600], rot: "smoke Jungle", onde: "do T spawn" },
    { de: "xe", tipo: "flash", e: 27, para: [455, 575], rot: "flash por cima", onde: "da rampa" },
    { de: "ji", tipo: "molotov", e: 33, para: [420, 590], rot: "molotov no default", onde: "do Palácio" },
    { de: "sp", tipo: "he", e: 40, para: [400, 560], rot: "HE no CT", onde: "do site" }
  ];
  var MARCOS = [{ e: 0, nome: "saída" }, { e: 15, nome: "smokes da execução" }, { e: 0, nome: "entrada no A", id: "entrada" }, { e: PLANT, nome: "plant", cls: "plant" }];

  var $ = function (id) { return document.getElementById(id); };
  var svg = $("pr-svg"), e = 0, sel = null, modo = "livre", tocando = false, fantasma = true, pincel = null;

  /* ---------- tempo ---------- */
  function relogio(t) {
    if (t < PLANT) { var s = Math.max(0, Math.round(115 - t)); return Math.floor(s / 60) + ":" + String(s % 60).padStart(2, "0"); }
    var b = Math.max(0, Math.round(40 - (t - PLANT))); return "0:" + String(b).padStart(2, "0");
  }
  function chegadas(j) { // horário de chegada em cada ponto (função dos pontos, sem estado)
    var t = 0, r = [];
    j.pts.forEach(function (p, i) { if (i > 0) t += Math.hypot(p.x - j.pts[i - 1].x, p.y - j.pts[i - 1].y) / VEL; r.push(t); t += p.espera || 0; });
    return r;
  }
  function posicao(j, t) {
    var c = chegadas(j);
    for (var i = 0; i < j.pts.length - 1; i++) {
      var sai = c[i] + (j.pts[i].espera || 0);
      if (t <= sai) return [j.pts[i].x, j.pts[i].y];
      if (t < c[i + 1]) { var k = (t - sai) / (c[i + 1] - sai); return [j.pts[i].x + (j.pts[i + 1].x - j.pts[i].x) * k, j.pts[i].y + (j.pts[i + 1].y - j.pts[i].y) * k]; }
    }
    var u = j.pts[j.pts.length - 1]; return [u.x, u.y];
  }
  function posReal(r, t) {
    for (var i = 0; i < r.pts.length - 1; i++) {
      var a = r.pts[i], b = r.pts[i + 1];
      if (t <= b[0]) { var k = Math.max(0, (t - a[0]) / (b[0] - a[0])); return [a[1] + (b[1] - a[1]) * k, a[2] + (b[2] - a[2]) * k]; }
    }
    var u = r.pts[r.pts.length - 1]; return [u[1], u[2]];
  }
  // o marco "entrada no A" fica 2,3 s antes da chegada inicial do Spinx (dado de exemplo do aviso)
  MARCOS[2].e = Math.round((chegadas(J[0])[3] - 2.3) * 10) / 10;
  function atrasos() {
    var r = [];
    J.forEach(function (j) {
      var c = chegadas(j);
      j.pts.forEach(function (p, i) {
        if (!p.marco) return;
        var m = MARCOS.filter(function (x) { return x.id === p.marco; })[0];
        if (m && c[i] - m.e > 0.05) r.push({ j: j, i: i, s: c[i] - m.e, m: m });
      });
    });
    return r;
  }
  function porId(id) { return J.filter(function (j) { return j.id === id; })[0]; }

  /* ---------- desenho (mapa) ---------- */
  function el(tag, at, pai) { var n = document.createElementNS(NS, tag); for (var k in at) n.setAttribute(k, at[k]); if (pai) pai.appendChild(n); return n; }
  function desenha() {
    var cR = $("camada-real"), cC = $("camada-caminhos"), cG = $("camada-granadas"), cP = $("camada-pecas");
    [cR, cC, cG, cP].forEach(function (c) { c.innerHTML = ""; });
    var rot = svg.querySelector(".camada-rotulos"); if (rot) rot.innerHTML = "";
    var atr = atrasos();
    if (fantasma) REAL.forEach(function (r) {
      el("polyline", { "class": "caminho real", points: r.pts.map(function (p) { return p[1] + "," + p[2]; }).join(" ") }, cR);
      var p = posReal(r, e), g = el("g", { "class": "pc fantasma " + r.lado }, cR);
      el("circle", { "class": "halo-tr", cx: p[0], cy: p[1], r: 10 }, g);
      el("circle", { "class": "contorno-tr", cx: p[0], cy: p[1], r: 10 }, g);
      el("circle", { "class": "corpo", cx: p[0], cy: p[1], r: 10 }, g);
      el("text", { x: p[0], y: p[1] - 19, "text-anchor": "middle" }, g).textContent = r.nome + " · real";
    });
    J.forEach(function (j) {
      if (sel !== j.id && modo !== "tocando") return;
      if (j.pts.length < 2) return;
      el("polyline", { "class": "caminho", points: j.pts.map(function (p) { return p.x + "," + p.y; }).join(" ") }, cC);
      var c = chegadas(j);
      j.pts.forEach(function (p, i) {
        if (i === 0) return;
        var at = atr.filter(function (a) { return a.j === j && a.i === i; })[0];
        var g = el("g", { "class": "pt-cam" + (at ? " atraso" : "") }, cC);
        el("circle", { cx: p.x, cy: p.y, r: 6 }, g);
        el("text", { x: p.x + 11, y: p.y - 9 }, g).textContent = relogio(c[i]) + (at ? " · +" + at.s.toFixed(1).replace(".", ",") + " s" : "");
      });
    });
    G.forEach(function (gr) {
      var j = porId(gr.de); if (!j) return;
      var d = e - gr.e; if (d < 0 || d > VOO + DUR[gr.tipo]) return;
      var o = posicao(j, gr.e), x, y;
      if (d < VOO) {
        var k = d / VOO; x = o[0] + (gr.para[0] - o[0]) * k; y = o[1] + (gr.para[1] - o[1]) * k;
        el("line", { "class": "voo", x1: o[0], y1: o[1], x2: gr.para[0], y2: gr.para[1], stroke: "var(--" + gr.tipo + ")" }, cG);
      } else {
        x = gr.para[0]; y = gr.para[1];
        if (gr.tipo === "smoke") el("circle", { "class": "area-smoke", cx: x, cy: y, r: 30 }, cG);
        if (gr.tipo === "molotov") el("circle", { "class": "area-fogo", cx: x, cy: y, r: 24 }, cG);
      }
      el("circle", { "class": "placa", cx: x, cy: y, r: 15 }, cG);
      el("use", { href: "#g-" + gr.tipo, x: x - 12, y: y - 12, width: 24, height: 24 }, cG);
    });
    J.forEach(function (j) {
      var p = posicao(j, e), morto = j.morre !== undefined && e >= j.morre;
      var cls = "pc " + j.lado + (sel === j.id ? (modo === "tracando" ? " tracando" : " sel") : "") + (morto ? " morto" : "");
      var g = el("g", { "class": cls, "data-id": j.id, tabindex: morto ? -1 : 0, role: "button", "aria-label": j.nome + " (" + j.func + ")" + (morto ? ", morto" : "") }, cP);
      if (morto) {
        var dx = "M" + (p[0] - 8) + " " + (p[1] - 8) + "l16 16m0-16l-16 16";
        el("path", { "class": "x-halo", d: dx }, g); el("path", { "class": "x-contorno", d: dx }, g);
        el("path", { "class": "x-cor", d: dx, stroke: "var(--" + j.lado + ")" }, g);
      }
      else {
        var a = (j.olhar || 0) * Math.PI / 180;
        el("path", { "class": "olhar", d: "M" + p[0] + " " + p[1] + "L" + (p[0] + Math.cos(a - 0.35) * 24) + " " + (p[1] + Math.sin(a - 0.35) * 24) + "L" + (p[0] + Math.cos(a + 0.35) * 24) + " " + (p[1] + Math.sin(a + 0.35) * 24) + "Z" }, g);
        el("circle", { "class": "anel", cx: p[0], cy: p[1], r: 15 }, g);
        el("circle", { "class": "halo", cx: p[0], cy: p[1], r: 10 }, g);
        el("circle", { "class": "corpo", cx: p[0], cy: p[1], r: 10 }, g);
      }
      el("text", { x: p[0], y: p[1] - 21, "text-anchor": "middle" }, g).textContent = j.nome;
    });
    if (window.Proto) Proto.placas(svg.parentNode);
    // relógio grande e avisos
    var rg = $("pr-relogio-grande"); rg.querySelector(".num").textContent = relogio(e);
    rg.querySelector("small").textContent = e < PLANT ? "tempo do round" : "bomba plantada";
    rg.classList.toggle("bomba", e >= PLANT);
    $("pr-avisos").innerHTML = atr.map(function (a) {
      return '<div class="aviso-bloco"><span class="ico" aria-hidden="true">▲</span><p><b>' + a.j.nome + " chega " + a.s.toFixed(1).replace(".", ",") + " s atrasado</b> ao marco “" + a.m.nome + "” (" + relogio(a.m.e) + "). Encurte o caminho ou tire espera de um ponto.</p></div>";
    }).join("");
  }

  /* ---------- linha do tempo ---------- */
  function pct(t) { return (t / FIM * 100) + "%"; }
  function montaLinha() {
    var regua = $("tl-regua"), h = '<span class="zona-bomba" style="left:' + pct(PLANT) + ';right:0"></span>';
    for (var t = 0; t <= FIM; t += 10) if (Math.abs(t - PLANT) > 5) h += '<span style="left:' + pct(t) + '"' + (t >= PLANT ? ' class="bomba"' : "") + ">" + relogio(t) + "</span>";
    h += '<span class="bomba" style="left:' + pct(PLANT) + '">0:40</span>';
    regua.innerHTML = h;
    // marcos são rótulos; pular para eles é pelo roteiro (linhas de 44 px), não por alvo de 22 px
    $("tl-marcos").innerHTML = MARCOS.slice().sort(function (a, b) { return a.e - b.e; }).map(function (m, i) { return '<span class="marco ' + (m.cls || "") + '" style="left:' + pct(m.e) + ";top:" + (i % 2 ? 22 : 2) + 'px">' + m.nome + " <span class=\"num apagado\">" + relogio(m.e) + "</span></span>"; }).join("");
    var atr = atrasos(), f = "";
    J.forEach(function (j) {
      var c = chegadas(j), fim = j.morre !== undefined ? j.morre : FIM;
      f += '<div class="tl-faixa ' + j.lado + (sel === j.id ? " sel" : "") + '"><span class="tl-nome">' + j.nome + "<small>" + j.func + '</small></span><span class="tl-trilho" data-id="' + j.id + '">';
      f += '<span class="tl-vida" style="left:0;width:' + pct(fim) + '"></span>';
      c.forEach(function (t, i) {
        if (i === 0) return;
        var at = atr.some(function (a) { return a.j === j && a.i === i; });
        f += '<span class="tl-ponto' + (at ? " atraso" : "") + '" style="left:' + pct(t) + '" title="chega às ' + relogio(t) + '"></span>';
      });
      G.forEach(function (g) {
        if (g.de !== j.id) return;
        if (g.tipo === "smoke" || g.tipo === "molotov") f += '<span class="tl-dur ' + g.tipo + '" style="left:' + pct(g.e + VOO) + ";width:" + pct(DUR[g.tipo]) + '" title="dura ' + DUR[g.tipo] + ' s"></span>';
        f += '<span class="tl-gr" style="left:' + pct(g.e) + '" title="' + g.rot + " às " + relogio(g.e) + '"><svg class="glifo"><use href="#g-' + g.tipo + '"/></svg></span>';
      });
      if (j.morre !== undefined) f += '<span class="morte" style="left:' + pct(j.morre) + '" title="morre às ' + relogio(j.morre) + '">✕</span>';
      f += "</span></div>";
    });
    if (fantasma) REAL.filter(function (r) { return r.lado === "ct"; }).forEach(function (r) {
      f += '<div class="tl-faixa ct fantasma"><span class="tl-nome">' + r.nome + "<small>real · " + r.func + '</small></span><span class="tl-trilho"><span class="tl-vida" style="left:0;width:100%;opacity:.25"></span>' +
        r.pts.slice(1).map(function (p) { return '<span class="tl-ponto" style="left:' + pct(p[0]) + ';border-style:dashed"></span>'; }).join("") + "</span></div>";
    });
    $("tl-faixas").innerHTML = f;
    // roteiro sincronizado
    var linhas = G.map(function (g) { var j = porId(g.de); return { e: g.e, t: j.nome + " (" + j.func + ") · " + g.rot + " · " + g.onde }; })
      .concat(MARCOS.filter(function (m) { return m.e > 0; }).map(function (m) { return { e: m.e, t: "marco: " + m.nome }; }))
      .sort(function (a, b) { return a.e - b.e; });
    $("roteiro").innerHTML = linhas.map(function (l) { return '<li data-e="' + l.e + '"><button type="button" data-e="' + l.e + '"><span class="num">' + relogio(l.e) + "</span><span>" + l.t + "</span></button></li>"; }).join("");
    [].forEach.call(document.querySelectorAll("#roteiro button"), function (b) { b.addEventListener("click", function () { vaiPara(+b.dataset.e); }); });
    posicionaCabecote();
  }
  function posicionaCabecote() {
    var cab = $("cabecote"), grade = $("tl-grade"), rot = parseFloat(getComputedStyle(grade).getPropertyValue("--rot")) || 132;
    var largura = grade.clientWidth - 24 - rot;
    cab.style.left = (12 + rot + largura * e / FIM) + "px";
    cab.setAttribute("aria-valuenow", Math.round(e)); cab.setAttribute("aria-valuetext", relogio(e));
    $("tl-relogio").textContent = relogio(e);
    var ult = null;
    [].forEach.call(document.querySelectorAll("#roteiro li"), function (li) { li.classList.remove("agora"); if (+li.dataset.e <= e) ult = li; });
    if (ult) ult.classList.add("agora");
  }
  function vaiPara(t) { e = Math.max(0, Math.min(FIM, t)); desenha(); posicionaCabecote(); }
  function eDoPonteiro(ev) {
    var grade = $("tl-grade"), r = grade.getBoundingClientRect(), rot = parseFloat(getComputedStyle(grade).getPropertyValue("--rot")) || 132;
    return (ev.clientX - r.left - 12 - rot) / (r.width - 24 - rot) * FIM;
  }
  (function () {
    var arrastando = false, grade = $("tl-grade");
    grade.addEventListener("pointerdown", function (ev) {
      if (ev.target.closest(".tl-nome")) return;
      arrastando = true; grade.setPointerCapture(ev.pointerId); vaiPara(eDoPonteiro(ev));
    });
    grade.addEventListener("pointermove", function (ev) { if (arrastando) vaiPara(eDoPonteiro(ev)); });
    grade.addEventListener("pointerup", function () { arrastando = false; });
    $("cabecote").addEventListener("keydown", function (ev) {
      var p = ev.shiftKey ? 5 : 1;
      if (ev.key === "ArrowRight") vaiPara(e + p); else if (ev.key === "ArrowLeft") vaiPara(e - p);
      else if (ev.key === "Home") vaiPara(0); else if (ev.key === "End") vaiPara(FIM); else return;
      ev.preventDefault();
    });
    window.addEventListener("resize", posicionaCabecote);
  })();

  /* ---------- dica: o que o próximo clique faz ---------- */
  function dica() {
    var d = $("pr-dica"), j = sel && porId(sel);
    if (modo === "tocando") d.innerHTML = "<b>Reproduzindo.</b> Nada é editável agora. <kbd>Espaço</kbd> pausa.";
    else if (pincel) d.innerHTML = "<b>" + pincel[0].toUpperCase() + pincel.slice(1) + ".</b> Arraste no mapa para desenhar. <kbd>Esc</kbd> volta a mover jogadores.";
    else if (modo === "tracando" && j) {
      var c = chegadas(j), u = j.pts[j.pts.length - 1];
      d.innerHTML = "<b>Traçando o caminho de " + j.nome + ".</b> Próximo clique: novo ponto (a hora de chegada aparece nele, a partir de " + relogio(c[c.length - 1] + (u.espera || 0)) + "). Botão direito: " + j.nome + " olha para o ponto. <kbd>Esc</kbd> termina.";
    } else d.innerHTML = "<b>Clique</b> num jogador para traçar o caminho · <b>arraste</b> para mover · <b>botão direito</b> com um jogador selecionado: ele olha para o ponto.";
  }

  /* ---------- interação no mapa ---------- */
  function ptSvg(ev) { var p = svg.createSVGPoint(); p.x = ev.clientX; p.y = ev.clientY; var q = p.matrixTransform(svg.getScreenCTM().inverse()); return [q.x, q.y]; }
  var arr = null;
  svg.addEventListener("pointerdown", function (ev) {
    if (modo === "tocando" || ev.button === 2) return;
    var g = ev.target.closest(".pc:not(.fantasma):not(.morto)");
    if (g) { arr = { id: g.dataset.id, x0: ev.clientX, y0: ev.clientY, mexeu: false }; svg.setPointerCapture(ev.pointerId); }
  });
  svg.addEventListener("pointermove", function (ev) {
    if (!arr) return;
    if (!arr.mexeu && Math.hypot(ev.clientX - arr.x0, ev.clientY - arr.y0) < 4) return; // LIMIAR_ARRASTO_PX
    arr.mexeu = true;
    var j = porId(arr.id), c = chegadas(j), q = ptSvg(ev), alvo = 0, dmin = 1e9;
    c.forEach(function (t, i) { if (Math.abs(t - e) < dmin) { dmin = Math.abs(t - e); alvo = i; } });
    j.pts[alvo].x = q[0]; j.pts[alvo].y = q[1]; desenha();
  });
  svg.addEventListener("pointerup", function (ev) {
    if (arr) {
      if (!arr.mexeu) { sel = arr.id; modo = "tracando"; marcaBanco(); }
      else montaLinha();
      arr = null; desenha(); dica(); return;
    }
    if (modo === "tracando" && sel && ev.button === 0 && !ev.target.closest(".pc")) {
      var q = ptSvg(ev); porId(sel).pts.push({ x: q[0], y: q[1] }); montaLinha(); desenha(); dica();
    }
  });
  svg.addEventListener("contextmenu", function (ev) {
    ev.preventDefault();
    if (!sel) return;
    var j = porId(sel), p = posicao(j, e), q = ptSvg(ev);
    j.olhar = Math.atan2(q[1] - p[1], q[0] - p[0]) * 180 / Math.PI; desenha();
  });
  svg.addEventListener("keydown", function (ev) {
    var g = ev.target.closest && ev.target.closest(".pc");
    if (g && (ev.key === "Enter" || ev.key === " ")) { sel = g.dataset.id; modo = "tracando"; marcaBanco(); desenha(); dica(); ev.preventDefault(); }
  });
  document.addEventListener("keydown", function (ev) {
    if (ev.key === "Escape") { if (pincel) { pincel = null; marcaPinceis(); } else { modo = "livre"; } desenha(); dica(); }
    if (ev.key === " " && modo === "tocando") { ev.preventDefault(); toca(); }
  });

  /* ---------- painel ---------- */
  function marcaBanco() {
    [].forEach.call(document.querySelectorAll(".banco button"), function (b) { b.setAttribute("aria-pressed", b.dataset.id === sel ? "true" : "false"); });
    var j = sel && porId(sel), box = $("pr-sel");
    box.innerHTML = '<h2 class="rot">Selecionado</h2>' + (j ? "<p><b>" + j.nome + "</b> · " + (j.lado === "tr" ? "TR" : "CT") + " · " + j.func + " · " + (j.pts.length - 1) + " pontos de caminho · chega ao último às <span class=\"num\">" + relogio(chegadas(j)[j.pts.length - 1]) + "</span></p>" : '<p class="apagado">Nenhum. Clique num jogador no mapa ou aqui.</p>');
    montaLinha();
  }
  function montaBanco() {
    $("banco-tr").innerHTML = J.map(function (j) {
      return '<li class="tr' + (j.morre !== undefined ? " morto" : "") + '"><button type="button" data-id="' + j.id + '" aria-pressed="false"><span class="ficha">' + j.nome.slice(0, 2) + "</span><span>" + j.nome + '</span><span class="func">' + j.func + (j.morre !== undefined ? " · morre " + relogio(j.morre) : "") + "</span></button></li>";
    }).join("");
    $("banco-ct").innerHTML = REAL.filter(function (r) { return r.lado === "ct"; }).map(function (r) {
      return '<li class="ct"><button type="button" aria-pressed="false" title="Arraste para o mapa para planejar contra ele"><span class="ficha">' + r.nome.slice(0, 2) + "</span><span>" + r.nome + '</span><span class="func">' + r.func + " · real</span></button></li>";
    }).join("");
    [].forEach.call(document.querySelectorAll("#banco-tr button"), function (b) { b.addEventListener("click", function () { sel = b.dataset.id; modo = "tracando"; marcaBanco(); desenha(); dica(); }); });
  }
  function marcaPinceis() {
    [].forEach.call(document.querySelectorAll("[data-pincel]"), function (b) { b.setAttribute("aria-pressed", b.dataset.pincel === pincel ? "true" : "false"); });
    $("pr-ctx").hidden = !pincel; dica();
  }
  [].forEach.call(document.querySelectorAll("[data-pincel]"), function (b) {
    b.addEventListener("click", function () { pincel = pincel === b.dataset.pincel ? null : b.dataset.pincel; marcaPinceis(); });
  });
  [].forEach.call(document.querySelectorAll(".gr"), function (b) {
    b.addEventListener("click", function () {
      var on = b.getAttribute("aria-pressed") !== "true";
      [].forEach.call(document.querySelectorAll(".gr"), function (x) { x.setAttribute("aria-pressed", "false"); });
      b.setAttribute("aria-pressed", on ? "true" : "false");
      $("pr-dica").innerHTML = on ? (sel ? "<b>" + b.textContent.trim().replace(/\d$/, "") + " de " + porId(sel).nome + ".</b> Próximo clique: onde a granada cai (sai às " + relogio(e) + ")." : "<b>Selecione um jogador</b> antes: a granada sai dele.") : "";
    });
  });
  $("b-desfazer").addEventListener("click", function () { var j = sel && porId(sel); if (j && j.pts.length > 1) { j.pts.pop(); montaLinha(); desenha(); dica(); } });
  $("b-fantasma").addEventListener("click", function (ev) {
    fantasma = !fantasma; ev.currentTarget.setAttribute("aria-pressed", fantasma ? "true" : "false");
    ev.currentTarget.textContent = fantasma ? "Round real: visível" : "Round real: escondido"; montaLinha(); desenha();
  });
  $("pr-mapa-sel").addEventListener("change", function (ev) {
    var sem = ev.target.value === "cache" || ev.target.value === "vertigo";
    $("pr-sem-corpus").hidden = !sem;
    $("pr-sem-corpus").querySelector("b").textContent = (ev.target.value === "vertigo" ? "Vertigo" : "Cache") + " não tem partidas no corpus.";
    ["b-buscar", "b-fantasma"].forEach(function (id) { var b = $(id); b.disabled = sem; b.title = sem ? "Desligado: este mapa não tem partidas no corpus" : ""; });
  });

  /* ---------- reprodução ---------- */
  var raf = null, t0 = 0, e0 = 0, VELOC = 3;
  function toca() {
    var b = $("b-play");
    if (tocando) { tocando = false; cancelAnimationFrame(raf); modo = "livre"; document.querySelector(".pr").classList.remove("tocando"); b.textContent = "▶ Reproduzir"; desenha(); dica(); return; }
    tocando = true; modo = "tocando"; document.querySelector(".pr").classList.add("tocando"); b.textContent = "❚❚ Pausar e editar";
    if (e >= FIM) e = 0; t0 = performance.now(); e0 = e; dica();
    (function passo(agora) { e = Math.min(FIM, e0 + (agora - t0) / 1000 * VELOC); desenha(); posicionaCabecote(); if (e < FIM && tocando) raf = requestAnimationFrame(passo); else if (tocando) toca(); })(t0);
  }
  $("b-play").addEventListener("click", toca);

  montaBanco(); e = 18; sel = "sp"; modo = "tracando"; marcaBanco(); desenha(); dica();
})();
