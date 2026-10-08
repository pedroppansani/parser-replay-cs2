/* Comportamentos comuns do protótipo (sem dependências; abre como arquivo local). */
(function () {
  "use strict";

  /* ---- Glifos das granadas: as MESMAS formas do map_core.js (nadeGlyph) ---- */
  var SPRITE =
    '<svg width="0" height="0" style="position:absolute" aria-hidden="true"><defs>' +
    '<symbol id="g-smoke" viewBox="-10 -10 20 20"><g stroke="#05080b" stroke-width="1.1" fill="var(--smoke)"><circle cx="-3.1" cy="0.8" r="3.8"/><circle cx="3.1" cy="0.8" r="3.8"/><circle cx="0" cy="-1.9" r="4.7"/></g></symbol>' +
    '<symbol id="g-flash" viewBox="-10 -10 20 20"><path d="M0,-9.3 L1.8,-1.8 L9.3,0 L1.8,1.8 L0,9.3 L-1.8,1.8 L-9.3,0 L-1.8,-1.8Z" fill="var(--flash)" stroke="#05080b" stroke-width="1.1" stroke-linejoin="round"/><circle r="1.9" fill="#fff"/></symbol>' +
    '<symbol id="g-he" viewBox="-10 -10 20 20"><path d="M0,-8.4 L2.2,-5.2 L5.9,-6.4 L5.4,-2.6 L8.3,-0.6 L5.7,1.9 L6.8,5.5 L3,5.1 L1.3,8.4 L-1.3,5.7 L-4.7,7.1 L-4.9,3.4 L-8.2,1.8 L-5.7,-0.9 L-7,-4.4 L-3.2,-4.5Z" fill="none" stroke="var(--he)" stroke-width="2.3" stroke-linejoin="round"/></symbol>' +
    '<symbol id="g-molotov" viewBox="-10 -10 20 20"><path d="M0,-9.2 Q6.2,-1 0,6.8 Q-6.2,-1 0,-9.2Z" fill="var(--molotov)" stroke="#05080b" stroke-width="1.1"/></symbol>' +
    '<symbol id="g-aviso" viewBox="-10 -10 20 20"><path d="M0,-8.5 L8.5,7 L-8.5,7Z" fill="var(--aviso)" stroke="#05080b" stroke-width="1.2" stroke-linejoin="round"/><path d="M0,-3 V2.5" stroke="#05080b" stroke-width="2"/><circle cy="4.6" r="1.1" fill="#05080b"/></symbol>' +
    '</defs></svg>';
  document.body.insertAdjacentHTML("afterbegin", SPRITE);


  /* ---- Escala dos mapas: rótulos em px de tela ---- */
  function escalaMapas() {
    [].forEach.call(document.querySelectorAll("svg.mapa-esc"), function (s) {
      var w = s.getBoundingClientRect().width, vb = (s.viewBox && s.viewBox.baseVal && s.viewBox.baseVal.width) || 760;
      if (w > 0) s.style.setProperty("--esc", (w / vb).toFixed(4));
    });
  }
  /* placa escura atrás de cada rótulo do mapa: o texto nunca encosta em linha, anel ou área clara */
  function placas(raiz) {
    [].forEach.call((raiz || document).querySelectorAll("svg.mapa-esc"), function (s) {
      var esc = parseFloat(s.style.getPropertyValue("--esc")) || 1, pad = 4 / esc;
      // rótulos numa camada própria, por cima de tudo: nenhuma peça, anel ou caminho passa por cima do texto
      var topo = s.querySelector(":scope > g.camada-rotulos");
      if (!topo) { topo = document.createElementNS("http://www.w3.org/2000/svg", "g"); topo.setAttribute("class", "camada-rotulos"); }
      s.appendChild(topo);
      [].forEach.call(topo.querySelectorAll(".placa-rot"), function (r) { r.remove(); });
      var ocupados = [];
      [].forEach.call(s.querySelectorAll("text:not(.leg)"), function (t) {
        if (t.parentNode !== topo) {
          var cls = t.parentNode.getAttribute && t.parentNode.getAttribute("class");
          if (cls) t.setAttribute("data-de", cls);       // mantém o estilo do grupo de origem (atraso, fantasma)
          topo.appendChild(t);
        }
        var bb; try { bb = t.getBBox(); } catch (e) { return; }
        if (!bb.width) return;
        // colisão: tenta acima, abaixo e mais acima; se nada couber, esconde (o nome aparece no hover e na seleção)
        t.style.display = "";
        var y0 = parseFloat(t.getAttribute("data-y0") || t.getAttribute("y")); t.setAttribute("data-y0", y0);
        var passo = bb.height + pad * 1.4, tent = [0, -passo, passo, -2 * passo, 2 * passo], ok = false;
        for (var i = 0; i < tent.length && !ok; i++) {
          t.setAttribute("y", y0 + tent[i]); bb = t.getBBox();
          var cx0 = bb.x - pad, cy0 = bb.y - pad * 0.75, cx1 = bb.x + bb.width + pad, cy1 = bb.y + bb.height + pad * 0.75;
          ok = ocupados.every(function (o) { return cx1 < o[0] || cx0 > o[2] || cy1 < o[1] || cy0 > o[3]; });
          if (ok) ocupados.push([cx0, cy0, cx1, cy1]);
        }
        if (!ok) { t.setAttribute("y", y0); t.style.display = "none"; return; }
        var r = document.createElementNS("http://www.w3.org/2000/svg", "rect");
        r.setAttribute("class", "placa-rot");
        r.setAttribute("x", bb.x - pad); r.setAttribute("y", bb.y - pad * 0.75);
        r.setAttribute("width", bb.width + 2 * pad); r.setAttribute("height", bb.height + 1.5 * pad);
        r.setAttribute("rx", 2 / esc);
        t.parentNode.insertBefore(r, t);
      });
    });
  }
  window.addEventListener("resize", function () { escalaMapas(); placas(); });
  document.addEventListener("aba", function () { requestAnimationFrame(function () { escalaMapas(); placas(); }); });
  escalaMapas();
  if (document.fonts && document.fonts.ready) document.fonts.ready.then(function () { placas(); }); else placas();

  /* ---- Abas: setas, Home/End, painel, e pista de abas fora da tela ---- */
  function iniciaAbas(lista) {
    var abas = [].slice.call(lista.querySelectorAll('[role="tab"]'));
    var moldura = lista.closest(".abas-moldura");
    function ativa(i, foca) {
      abas.forEach(function (t, j) {
        var sel = j === i;
        t.setAttribute("aria-selected", sel ? "true" : "false");
        t.tabIndex = sel ? 0 : -1;
        var p = document.getElementById(t.getAttribute("aria-controls"));
        if (p) p.hidden = !sel;
      });
      if (foca) abas[i].focus();
      abas[i].scrollIntoView({ block: "nearest", inline: "nearest" });
      try { history.replaceState(null, "", "#" + abas[i].dataset.aba); } catch (e) { /* arquivo local sem history */ }
      document.dispatchEvent(new CustomEvent("aba", { detail: abas[i].dataset.aba }));
      sobra();
    }
    lista.addEventListener("keydown", function (e) {
      var i = abas.indexOf(document.activeElement);
      if (i < 0) return;
      var n = abas.length, k = e.key;
      if (k === "ArrowRight") ativa((i + 1) % n, true);
      else if (k === "ArrowLeft") ativa((i - 1 + n) % n, true);
      else if (k === "Home") ativa(0, true);
      else if (k === "End") ativa(n - 1, true);
      else return;
      e.preventDefault();
    });
    abas.forEach(function (t, i) { t.addEventListener("click", function () { ativa(i, false); }); });
    function sobra() {
      if (!moldura) return;
      var esq = lista.scrollLeft > 2;
      var dir = lista.scrollLeft + lista.clientWidth < lista.scrollWidth - 2;
      moldura.classList.toggle("sobra-esq", esq);
      moldura.classList.toggle("sobra-dir", dir);
    }
    lista.addEventListener("scroll", sobra, { passive: true });
    window.addEventListener("resize", sobra);
    var mais = moldura && moldura.querySelector(".abas-mais");
    if (mais) mais.addEventListener("click", function () { lista.scrollBy({ left: lista.clientWidth * 0.7, behavior: "smooth" }); });
    var inicial = 0, h = (location.hash || "").slice(1);
    abas.forEach(function (t, i) { if (t.dataset.aba === h) inicial = i; });
    ativa(inicial, false);
    requestAnimationFrame(sobra);
  }
  [].forEach.call(document.querySelectorAll('[role="tablist"]'), iniciaAbas);

  /* ---- Filtros de chips (aria-pressed; um grupo = um critério) ---- */
  [].forEach.call(document.querySelectorAll("[data-filtro-grupo]"), function (g) {
    g.addEventListener("click", function (e) {
      var b = e.target.closest(".chip");
      if (!b || b.getAttribute("aria-disabled") === "true") return;
      [].forEach.call(g.querySelectorAll(".chip"), function (x) { x.setAttribute("aria-pressed", x === b ? "true" : "false"); });
      aplicaFiltros();
    });
  });
  function aplicaFiltros() {
    var crit = {};
    [].forEach.call(document.querySelectorAll("[data-filtro-grupo]"), function (g) {
      var on = g.querySelector('.chip[aria-pressed="true"]');
      crit[g.dataset.filtroGrupo] = on ? on.dataset.valor : "";
    });
    var visiveis = 0;
    [].forEach.call(document.querySelectorAll("[data-card]"), function (c) {
      var ok = Object.keys(crit).every(function (k) { return !crit[k] || c.dataset[k] === crit[k]; });
      c.hidden = !ok; if (ok) visiveis++;
    });
    var vazio = document.getElementById("grade-vazia");
    if (vazio) vazio.hidden = visiveis > 0;
    var cont = document.getElementById("grade-contagem");
    if (cont) cont.textContent = visiveis;
  }

  /* ---- Alternar as notas de origem do texto (só protótipo) ---- */
  var alt = document.createElement("button");
  alt.className = "btn alterna-notas"; alt.type = "button";
  alt.textContent = "Ocultar notas"; alt.setAttribute("aria-pressed", "false");
  alt.addEventListener("click", function () {
    var on = document.body.classList.toggle("sem-notas");
    alt.textContent = on ? "Mostrar notas" : "Ocultar notas";
    alt.setAttribute("aria-pressed", on ? "true" : "false");
  });
  (document.querySelector(".pagina") || document.body).appendChild(alt);

  window.Proto = { aplicaFiltros: aplicaFiltros, escalaMapas: escalaMapas, placas: placas };
})();
