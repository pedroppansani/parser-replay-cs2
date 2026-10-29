  var D = JSON.parse(document.getElementById("payload").textContent);
  var R = JSON.parse(document.getElementById("replay").textContent);
  var BD = {};
  (JSON.parse(document.getElementById("breakdown").textContent) || []).forEach(function (b) { BD[b.round] = b; });
  // Cores do canvas e dos gráficos: lidas dos tokens do CSS (dashboard/web/tokens.css), uma fonte só
  // (entrega-sala-de-demo §3.1). Time A = azul (ct), Time B = dourado (tr), round decisivo = --decisivo.
  var raiz = getComputedStyle(document.documentElement);
  function tk(nome) { return raiz.getPropertyValue("--" + nome).trim(); }
  var C = { ct: tk("ct"), tr: tk("tr"), decisivo: tk("decisivo"), tinta: tk("tinta"), tinta2: tk("tinta-2"),
            apagado: tk("apagado"), linha: tk("linha"), borda: tk("borda"), fundo: tk("fundo"),
            superficie: tk("superficie"), radar: tk("radar"), flash: tk("flash"), contorno: tk("contorno"),
            ctArea: tk("ct-area"), trArea: tk("tr-area"), fNum: tk("f-num"), fTexto: tk("f-texto") };
  // O canvas do mapa é sempre escuro (decisão 48): peças, rastros, rótulos e a legenda dos glifos leem os *-mapa,
  // iguais nos dois temas; os gráficos e a página leem os do tema (C).
  var CM = { ct: tk("ct-mapa"), tr: tk("tr-mapa"), tinta: tk("tinta-mapa"), tinta2: tk("tinta-2-mapa"),
             apagado: tk("apagado-mapa") };
  var reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  function fmt(v, d) { return (v == null || isNaN(v)) ? "—" : Number(v).toFixed(d == null ? 1 : d); }
  function br(v, d) { return fmt(v, d).replace(".", ","); }
  function svgEl(tag, a) {
    var n = document.createElementNS("http://www.w3.org/2000/svg", tag);
    for (var k in a) n.setAttribute(k, a[k]);
    return n;
  }

  /* ---------------- Cabeçalho ---------------- */

  var M = D.match;
  // Todo texto que vem do DADO passa por esc() antes de entrar em HTML montado
  // por concatenação (nome de jogador, frase gerada, arma, lugar). A função é
  // uma só, a do map_core.js.
  var esc = MapCore.esc;
  // Origem da partida, nomes dos lados, linha do decisor e números do corpus: montados no BUILD a partir
  // do manifesto, do payload e de numeros_citaveis.json (nada disso é escrito à mão aqui -- há teste).
  var PAGINA = /*__PAGINA__*/null || {};
  var CAB = PAGINA.cabecalho || null;
  // Nome de cada lado: o do cabeçalho; sem ele (payload sem placar) cai no identificador interno.
  var LADO = { A: CAB ? CAB.lados.A.nome : "Lado A", B: CAB ? CAB.lados.B.nome : "Lado B" };
  // "começou CT/TR" de cada lado: a etiqueta é o único uso da cor de lado na identidade do time
  var COMECOU = { ct: "começou CT", tr: "começou TR" };
  function etiquetaComecou(time) {
    var l = CAB && CAB.lados[time];
    return l ? "<span class='tag comecou " + l.comecou + "'>" + COMECOU[l.comecou] + "</span>" : "";
  }
  // O nome do lado em qualquer texto montado aqui; id desconhecido (jogador sem time) vira "?".
  function nomeLado(t) { return LADO[t] || "?"; }
  Array.prototype.forEach.call(document.querySelectorAll("[data-lado]"), function (e) {
    e.textContent = LADO[e.dataset.lado];
  });
  (function () {
    var ROTULO = { venceu: "venceu", comecou: COMECOU };
    // h1: o placar no formato do HUD, montado com textContent (nome de time/jogador é dado, nunca HTML)
    var h1 = document.getElementById("titulo-partida");
    function el(tag, cls, txt) {
      var e = document.createElement(tag);
      if (cls) e.className = cls;
      if (txt != null) e.textContent = txt;
      return e;
    }
    function ladoDoPlacar(k, cls) {
      var l = CAB.lados[k], venceu = CAB.venceu === k;
      var s = el("span", "lado " + cls + " " + (venceu ? "venceu" : "perdeu"));
      var nome = el("span", "nome", l.nome);
      nome.title = l.nome;
      var pts = el("span", "pts", String(k === "A" ? M.score_a : M.score_b));
      var tag = el("span", "tag comecou " + l.comecou, ROTULO.comecou[l.comecou] || "");
      s.appendChild(cls === "a" ? nome : pts);
      s.appendChild(cls === "a" ? pts : nome);
      if (venceu) s.appendChild(el("span", "tag-venceu", ROTULO.venceu));
      s.appendChild(tag);
      return s;
    }
    if (h1.children.length) {
      // já veio pronto do build (o caso normal): nada a montar
    } else if (CAB) {
      h1.appendChild(ladoDoPlacar("A", "a"));
      var x = el("span", "x", "×");
      x.setAttribute("aria-hidden", "true");
      h1.appendChild(x);
      h1.appendChild(ladoDoPlacar("B", "b"));
      document.getElementById("decisor").textContent = CAB.decisor;
    } else {
      h1.textContent = PAGINA.mapa || M.map;
    }
    var nJog = (D.players || []).length;
    document.getElementById("jog-eyebrow").textContent = nJog + " jogadores, " + M.rounds + " rounds";
    Array.prototype.forEach.call(document.querySelectorAll(".n-rounds"), function (e) { e.textContent = M.rounds; });
  })();

