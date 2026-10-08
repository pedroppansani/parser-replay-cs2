/* Página da partida do protótipo: faixa de rounds, replay (função do tempo), placar e comparação. */
(function () {
  "use strict";
  var NS = "http://www.w3.org/2000/svg";

  /* ---- Rounds: lado de quem venceu cada round (ilustrativo, fecha 12-12 no 24 e 17-19 no 36) ---- */
  var vencedor = "FFMFFMFMFFMF" + "MFMFFMMFMMM" + "M" + "FMFMFM" + "MFMMFM"; // F = Falcons, M = MOUZ
  function ladoDaFalcons(r) { if (r <= 12) return "tr"; if (r <= 24) return "ct"; return ((Math.floor((r - 25) / 3)) % 2 === 0) ? "tr" : "ct"; }
  var faixa = document.getElementById("rodadas");
  if (faixa) {
    for (var r = 1; r <= 36; r++) {
      var f = vencedor[r - 1] === "F";
      var lado = f ? ladoDaFalcons(r) : (ladoDaFalcons(r) === "ct" ? "tr" : "ct");
      var b = document.createElement("button");
      b.type = "button"; b.className = "rd " + lado + (r === 24 ? " dec" : "");
      b.textContent = r; b.setAttribute("aria-pressed", r === 24 ? "true" : "false");
      b.setAttribute("aria-label", "Round " + r + ", " + (f ? "Falcons" : "MOUZ") + " venceu de " + lado.toUpperCase() + (r === 24 ? ", round decisivo" : ""));
      b.addEventListener("click", function (e) {
        [].forEach.call(faixa.querySelectorAll(".rd"), function (x) { x.setAttribute("aria-pressed", x === e.currentTarget ? "true" : "false"); });
      });
      faixa.appendChild(b);
      if (r === 12 || r === 24 || r === 30) { var s = document.createElement("span"); s.className = "meio-tempo"; s.setAttribute("aria-hidden", "true"); faixa.appendChild(s); }
    }
  }

  /* ---- Replay: peças como função pura do tempo (como a decisão 35 faz na prancheta) ---- */
  var JOG = [
    { n: "kyousuke", l: "ct", a: [184, 174], b: [520, 610], morre: 0.97 },
    { n: "kyxsan", l: "ct", a: [66, 196], b: [200, 300], morre: 0.43 },
    { n: "NiKo", l: "ct", a: [152, 243], b: [300, 360], morre: 0.25 },
    { n: "TeSeS", l: "ct", a: [632, 428], b: [560, 600], morre: 0.36 },
    { n: "m0NESY", l: "ct", a: [580, 510], b: [600, 560], morre: 0.18 },
    { n: "Spinx", l: "tr", a: [290, 294], b: [430, 600], morre: 0.47 },
    { n: "xertioN", l: "tr", a: [342, 288], b: [470, 560], morre: 0.24 },
    { n: "torzsi", l: "tr", a: [346, 316], b: [500, 520], morre: 0.51 },
    { n: "Jimpphat", l: "tr", a: [366, 340], b: [270, 640], morre: 2 },
    { n: "Brollan", l: "tr", a: [320, 300], b: [440, 640], morre: 0.33 }
  ];
  var pecas = document.getElementById("pecas");
  function desenha(t) {
    if (!pecas) return;
    var h = "";
    JOG.forEach(function (j) {
      var k = Math.min(1, t * 1.1), x = j.a[0] + (j.b[0] - j.a[0]) * k, y = j.a[1] + (j.b[1] - j.a[1]) * k;
      var cor = j.l === "ct" ? "var(--ct)" : "var(--tr)";
      if (t >= j.morre) {
        var dx = "M" + (x - 7) + " " + (y - 7) + "l14 14m0-14l-14 14";
        h += '<g class="peca morto"><path class="x-halo" d="' + dx + '"/><path class="x-contorno" d="' + dx + '"/><path class="x-cor" d="' + dx + '" stroke="' + cor + '"/></g>';
      } else {
        h += '<g class="peca"><path d="M' + x + " " + y + " l18 -8 v16z" + '" fill="#05080b" opacity=".75"/><circle class="halo" cx="' + x + '" cy="' + y + '" r="9"/><circle class="corpo" cx="' + x + '" cy="' + y + '" r="9" fill="' + cor + '"/><text x="' + x + '" y="' + (y - 18) + '" text-anchor="middle">' + j.n + "</text></g>";
      }
    });
    if (t > 0.1 && t < 0.9) h += '<g opacity=".9"><circle cx="400" cy="170" r="44" fill="var(--smoke)" opacity=".4"/><circle class="placa" cx="400" cy="170" r="15"/><use href="#g-smoke" x="388" y="158" width="24" height="24"/></g>';
    if (t > 0.42) h += '<g><circle class="placa" cx="466" cy="571" r="15"/><use href="#g-molotov" x="455" y="560" width="22" height="22"/></g>';
    var rot = pecas.ownerSVGElement.querySelector(".camada-rotulos"); if (rot) rot.innerHTML = "";
    pecas.innerHTML = h;
    if (window.Proto) Proto.placas(pecas.ownerSVGElement.parentNode);
  }
  var trilho = document.getElementById("trilho"), relogio = document.getElementById("relogio");
  var PLANT = 43, DUR = 135;
  function atualiza() {
    var t = trilho.value / 1000, dec = t * DUR, txt;
    if (dec < PLANT) { var s = Math.round(115 - dec); txt = Math.floor(s / 60) + ":" + String(s % 60).padStart(2, "0"); }
    else { var b = Math.max(0, Math.round(40 - (dec - PLANT))); txt = "0:" + String(b).padStart(2, "0"); }
    var d = Math.round(dec);
    relogio.innerHTML = txt + "<small>" + (dec < PLANT ? "decorrido " : "bomba · decorrido ") + "<span class=\"num\">" + Math.floor(d / 60) + ":" + String(d % 60).padStart(2, "0") + "</span></small>";
    trilho.setAttribute("aria-valuetext", txt);
    desenha(t);
  }
  if (trilho) {
    trilho.addEventListener("input", atualiza); atualiza();
    var tocando = null, btn = document.getElementById("tocar");
    btn.addEventListener("click", function () {
      if (tocando) { clearInterval(tocando); tocando = null; btn.textContent = "▶"; btn.setAttribute("aria-label", "Reproduzir"); return; }
      if (+trilho.value >= 1000) trilho.value = 0;
      btn.textContent = "❚❚"; btn.setAttribute("aria-label", "Pausar");
      tocando = setInterval(function () { trilho.value = Math.min(1000, +trilho.value + 4); atualiza(); if (+trilho.value >= 1000) btn.click(); }, 50);
    });
    var vels = ["1×", "2×", "0,5×", "0,25×"], vi = 0, vel = document.getElementById("vel");
    vel.addEventListener("click", function () { vi = (vi + 1) % vels.length; vel.textContent = vels[vi]; vel.setAttribute("aria-label", "Velocidade: " + vels[vi]); });
    document.getElementById("b-desenhar").addEventListener("click", function (e) {
      var on = e.currentTarget.getAttribute("aria-pressed") !== "true";
      e.currentTarget.setAttribute("aria-pressed", on ? "true" : "false");
      document.getElementById("ferr-desenho").hidden = !on;
    });
    document.getElementById("b-atalhos").addEventListener("click", function (e) {
      var p = document.getElementById("atalhos"); p.hidden = !p.hidden; e.currentTarget.setAttribute("aria-expanded", p.hidden ? "false" : "true");
    });
  }

  /* ---- Placar: diferença de rounds (linha neutra; bolinha com a cor do lado vencedor; decisivo = losango) ---- */
  var g = document.getElementById("graf-placar");
  if (g) {
    var W = 720, H = 220, L = 34, R = 10, T = 14, B = 26, n = 36, dif = 0, pts = [];
    for (var i = 0; i < n; i++) { dif += vencedor[i] === "F" ? 1 : -1; pts.push(dif); }
    var maxA = 4, x = function (i) { return L + (W - L - R) * i / (n - 1); }, y = function (v) { return T + (H - T - B) * (maxA - v) / (2 * maxA); };
    var h = "";
    for (var v = -maxA; v <= maxA; v += 2) h += '<line x1="' + L + '" x2="' + (W - R) + '" y1="' + y(v) + '" y2="' + y(v) + '" stroke="' + (v === 0 ? "var(--borda)" : "var(--linha)") + '"/><text x="' + (L - 6) + '" y="' + (y(v) + 4) + '" text-anchor="end">' + (v > 0 ? "+" + v : v) + "</text>";
    [12, 24, 30].forEach(function (r) { h += '<line x1="' + x(r - 0.5) + '" x2="' + x(r - 0.5) + '" y1="' + T + '" y2="' + (H - B) + '" stroke="var(--linha)" stroke-dasharray="3 3"/>'; });
    h += '<polyline fill="none" stroke="var(--tinta-2)" stroke-width="2" points="' + pts.map(function (p, i) { return x(i) + "," + y(p); }).join(" ") + '"/>';
    pts.forEach(function (p, i) {
      var r = i + 1, f = vencedor[i] === "F", lado = f ? ladoDaFalcons(r) : (ladoDaFalcons(r) === "ct" ? "tr" : "ct");
      if (r === 24) h += '<rect x="' + (x(i) - 7) + '" y="' + (y(p) - 7) + '" width="14" height="14" transform="rotate(45 ' + x(i) + " " + y(p) + ')" fill="var(--decisivo)" stroke="var(--fundo)" stroke-width="2"><title>Round 24, decisivo</title></rect>';
      else h += '<circle cx="' + x(i) + '" cy="' + y(p) + '" r="4.5" fill="var(--' + lado + ')" stroke="var(--superficie)" stroke-width="1.5"><title>Round ' + r + "</title></circle>";
    });
    h += '<text x="' + x(0) + '" y="' + (H - 6) + '">1</text><text x="' + x(11) + '" y="' + (H - 6) + '">12</text><text x="' + x(23) + '" y="' + (H - 6) + '">24</text><text x="' + x(35) + '" y="' + (H - 6) + '" text-anchor="end">36</text>';
    g.innerHTML = h;
  }

  /* ---- Comparar dois jogadores da partida: valores lado a lado, sem faixa ---- */
  var D = {
    m0NESY: { rating: "1,48", adr: "93,7", kast: [27, 36], ab: [5, 6] },
    xertioN: { rating: "1,45", adr: "90,7", kast: [27, 36], ab: [7, 12] },
    NiKo: { rating: "1,17", adr: "79,1", kast: [28, 36], ab: [3, 7] },
    Spinx: { rating: "1,14", adr: "69,6", kast: [28, 36], ab: [2, 3] }
  };
  var MINIMO = 10; // abaixo disso a taxa não vira porcentagem: só o bruto
  function taxa(k, n) {
    if (n < MINIMO) return '<span class="num">' + k + " de " + n + '</span> <span class="tag amostra">amostra pequena</span>';
    return '<span class="num">' + Math.round(k / n * 100) + '%</span><small class="apagado" style="display:block"><span class="num">' + k + " de " + n + "</span></small>";
  }
  function compara() {
    var a = document.getElementById("c1").value, b = document.getElementById("c2").value, alvo = document.getElementById("comp-barras");
    if (!alvo) return;
    if (a === b) { alvo.innerHTML = '<div class="aviso-bloco info"><span class="ico">i</span><p>Escolha dois jogadores diferentes.</p></div>'; return; }
    var A = D[a], B = D[b];
    alvo.innerHTML = '<div class="cmp"><span class="cab"></span><span class="cab">' + a + '</span><span class="cab">' + b + "</span>" +
      '<span>Rating</span><span class="num">' + A.rating + '</span><span class="num">' + B.rating + "</span>" +
      '<span>ADR</span><span class="num">' + A.adr + '</span><span class="num">' + B.adr + "</span>" +
      "<span>KAST</span><span>" + taxa(A.kast[0], A.kast[1]) + "</span><span>" + taxa(B.kast[0], B.kast[1]) + "</span>" +
      "<span>Aberturas vencidas</span><span>" + taxa(A.ab[0], A.ab[1]) + "</span><span>" + taxa(B.ab[0], B.ab[1]) + "</span></div>" +
      '<p class="bruto" style="margin-top:8px">Rating com erro típico de <span class="num">{erro_rating}</span> contra o oficial: diferenças menores que isso são empate.</p>';
  }
  ["c1", "c2"].forEach(function (id) { var s = document.getElementById(id); if (s) s.addEventListener("change", compara); });
  compara();

  /* ---- Grupos: começam fechados; aberto/fechado lembrado por quem vê (localStorage, sempre em try/catch) ---- */
  var CHAVE = "parser-cs2:grupos-jogadores";
  var lembrado = {};
  try { lembrado = JSON.parse(localStorage.getItem(CHAVE) || "{}") || {}; } catch (e) { lembrado = {}; }
  [].forEach.call(document.querySelectorAll("details.grupo[data-grupo]"), function (d) {
    if (lembrado[d.dataset.grupo] === true) d.open = true;
    d.addEventListener("toggle", function () {
      lembrado[d.dataset.grupo] = d.open;
      try { localStorage.setItem(CHAVE, JSON.stringify(lembrado)); } catch (e) { /* arquivo local ou armazenamento bloqueado: segue sem lembrar */ }
    });
  });
})();
