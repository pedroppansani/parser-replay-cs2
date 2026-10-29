  /* ================= PLACAR ================= */

  // O "maior acontecimento" do round, em ordem de quanto explica o resultado.
  // Clutch e multikill vêm primeiro porque são o round inteiro decidido por uma
  // pessoa; virada numérica vem depois porque é coletiva; abertura fica por
  // último porque acontece em todo round — só é a manchete quando não houve
  // nada mais forte.
  function roundHeadline(info, p) {
    if (info.clutch_player) {
      return info.clutch_player + " fechou 1v" + info.clutch_against;
    }
    if (info.multikill_player && info.multikill_count >= 3) {
      return info.multikill_player + " fez " + info.multikill_count + " kills no round";
    }
    if (info.worst_deficit_overcome >= 2) {
      return nomeLado(p.winner_team) + " virou de " + info.worst_deficit_overcome +
        " jogadores atrás";
    }
    if (info.opening) {
      return info.opening.player + " abriu o round matando " + info.opening.victim;
    }
    return "Round decidido no confronto direto";
  }

  /* ---------- Dica, clique e destaque comuns aos dois gráficos do Placar ----------
     "A virada em dois atos" e "Quanto cada round pesou" mostram o mesmo round no mesmo x: a dica é a
     mesma (o que mais pesou no round), o clique é o mesmo (abre o round no mapa) e passar o mouse num
     round de um gráfico acende o mesmo round no outro. */
  var PONTUADOS = {};
  (D.rounds_scored || []).forEach(function (r) { PONTUADOS[r.round] = r; });

  // O conteúdo da dica de um round. `extra` (opcional) é uma linha a mais, já escrita pelo Python.
  function dicaDoRound(p, extra) {
    var info = PONTUADOS[p.round] || p;
    return "<div class='rh'><span>Round " + esc(p.round) + "</span><span>" + esc(nomeLado(p.winner_team)) + " venceu</span></div>" +
      "<div class='rt'>" + esc(roundHeadline(info, p)) + "</div>" +
      (extra ? "<div class='rs'>" + esc(extra) + "</div>" : "") +
      "<div class='rs'>" + esc(p.score_a) + "–" + esc(p.score_b) + " · " + esc(REASON[p.reason] || p.reason) +
      (p.bomb_planted ? " · bomba plantada" : "") + "</div>" +
      "<div class='rgo'>clique para assistir este round</div>";
  }

  function assisteRound(roundNum) {
    var target = null;
    for (var j = 0; j < rounds.length; j++) {
      if (rounds[j].round === roundNum) { target = rounds[j]; break; }
    }
    if (!target) return;
    selectTab("replay");
    selectRound(target);
    document.querySelector(".board").scrollIntoView({ behavior: reduced ? "auto" : "smooth", block: "center" });
  }

  // Cada gráfico registra aqui, por round, a função que acende (on = true) ou apaga o round.
  var SINC = { swing: {}, peso: {} };
  function sincroniza(origem, round, on) {
    var outro = origem === "swing" ? SINC.peso : SINC.swing;
    if (outro[round]) outro[round](on);
  }

  /* ---------- Quanto cada round pesou ----------
     A curva da chance de vitória repetia o desenho do gráfico de cima: a chance depende quase só do
     placar, e as duas linhas subiam e desciam nos mesmos rounds. O que só a chance de vitória mostra é
     o PESO de cada round: a barra é o quanto o round mudou a chance do lado A (depois menos antes, a
     curva que o payload já publica), para cima a favor do A, para baixo a favor do B. A cor é a do time
     que ganhou o round (os mesmos tokens do gráfico de cima) e o round decisivo é o que o payload já
     traz (decRound), com o contorno e o rótulo no token do decisivo. Títulos e frases vêm prontos do
     Python (PAGINA.peso_dos_rounds, leitura/peso_dos_rounds.py). */
  (function pesoDosRounds() {
    var svg = document.getElementById("wpchart");
    var curva = (D.win_probability || {}).curve || [];
    var T = PAGINA.peso_dos_rounds || null;
    if (!svg || !curva.length || !T) return;
    document.getElementById("peso-titulo").textContent = T.titulo;
    document.getElementById("peso-abertura").textContent = T.abertura;
    var nota = document.getElementById("peso-nota");
    nota.textContent = T.nota || "";
    nota.hidden = !T.nota;
    svg.setAttribute("aria-label", T.titulo);

    // O eixo X é o do gráfico de cima: mesma largura do viewBox, mesmas margens laterais e o round i no
    // mesmo x, para o round 13 ficar exatamente embaixo do round 13.
    var W = 900, H = 300, pL = 32, pR = 12, pT = 30, pB = 70;
    var n = curva.length;
    var X = function (i) { return n > 1 ? pL + (i / (n - 1)) * (W - pL - pR) : (pL + W - pR) / 2; };
    var passo = n > 1 ? (W - pL - pR) / (n - 1) : 40;
    var larg = Math.max(2, Math.min(28, passo * 0.62));
    var delta = curva.map(function (c) { return c.wp_a_depois - c.wp_a_antes; });
    var maior = Math.max.apply(null, delta.map(Math.abs));
    // Escala simétrica que cabe a maior barra da partida, arredondada para cima de 5 em 5 pp.
    var teto = Math.max(5, Math.ceil(maior * 100 / 5 - 1e-9) * 5) / 100;
    var meia = (H - pT - pB) / 2, zero = pT + meia;
    var Y = function (v) { return zero - (v / teto) * meia; };
    // Em unidades do viewBox: a barra de um round que quase não mexeu afina, mas não some.
    var ALTURA_MINIMA = 3;
    var FONTE = 10;

    // grade: +teto, 0 e −teto, com o zero marcado; o rótulo fica sobre a linha (embaixo, na de −teto),
    // à esquerda, onde nenhum round tem barra
    var caixas = [];   // o que já ocupa lugar: rótulos da grade e do intervalo (para os rótulos das barras)
    function rotuloPp(v) {
      var pp = Math.round(v * 100);
      return pp === 0 ? "0" : (pp > 0 ? "+" : "−") + Math.abs(pp) + " pp";
    }
    [teto, 0, -teto].forEach(function (g) {
      svg.appendChild(svgEl("line", { x1: pL, x2: W - pR, y1: Y(g), y2: Y(g),
        stroke: g === 0 ? C.borda : C.linha, "stroke-width": g === 0 ? 1.4 : 1 }));
      var y = g < 0 ? Y(g) + FONTE + 3 : Y(g) - 5;
      var lb = svgEl("text", { x: 0, y: y, fill: C.apagado, "font-family": C.fNum, "font-size": FONTE });
      lb.textContent = rotuloPp(g);
      svg.appendChild(lb);
      caixas.push({ x0: 0, x1: rotuloPp(g).length * FONTE * 0.62, y0: y - FONTE, y1: y + 2 });
    });

    var hx = X(M.halftime - 1);
    svg.appendChild(svgEl("line", { x1: hx, x2: hx, y1: pT, y2: H - pB, stroke: C.borda,
      "stroke-width": 1, "stroke-dasharray": "3 4" }));
    var ht = svgEl("text", { x: hx + 6, y: pT - 8, fill: C.apagado, "font-family": C.fNum, "font-size": FONTE });
    ht.textContent = "intervalo";
    svg.appendChild(ht);
    caixas.push({ x0: hx + 6, x1: hx + 6 + 9 * FONTE * 0.62, y0: pT - 8 - FONTE, y1: pT - 6 });

    var tip = document.createElement("div");
    tip.className = "rtip";
    tip.hidden = true;
    svg.parentNode.appendChild(tip);

    var prog = {};
    (D.progression || []).forEach(function (p) { prog[p.round] = p; });

    function mostraDica(i, p, topo) {
      var box = svg.getBoundingClientRect(), pai = svg.parentNode.getBoundingClientRect();
      var k = box.width / W;
      tip.innerHTML = dicaDoRound(p, T.frases[i]);
      tip.hidden = false;
      tip.style.left = (box.left - pai.left + X(i) * k) + "px";
      tip.style.top = (box.top - pai.top + topo * k - 12) + "px";
      tip.classList.add("on");
    }
    function escondeDica() {
      tip.classList.remove("on");
      tip.hidden = true;
    }

    curva.forEach(function (c, i) {
      var p = prog[c.round] || c;
      var v = delta[i], dec = c.round === decRound;
      var h = Math.max(ALTURA_MINIMA, Math.abs(Y(v) - zero));
      var y = v >= 0 ? zero - h : zero;
      var barra = svgEl("rect", { x: X(i) - larg / 2, y: y, width: larg, height: h,
        fill: c.winner_team === "A" ? C.ct : C.tr, "class": "pesobar" + (dec ? " dec" : ""),
        "data-round": c.round, "data-variacao": v });
      if (dec) {
        barra.setAttribute("stroke", C.decisivo);
        barra.setAttribute("stroke-width", 3);
      }
      svg.appendChild(barra);

      function acende(on) { barra.classList.toggle("hot", on); }
      SINC.peso[c.round] = acende;

      // O alvo é a coluna inteira do round (a barra fina é difícil de mirar, e mais ainda no toque).
      var alvo = svgEl("rect", { x: X(i) - passo / 2, y: pT - 4, width: passo, height: H - pB - pT + 8,
        "class": "pesohit", tabindex: 0, role: "button",
        "aria-label": "Round " + c.round + ": " + T.frases[i] + ", " + T.placares[i] + ". " +
          nomeLado(c.winner_team) + " venceu. " + roundHeadline(PONTUADOS[c.round] || p, p) +
          (dec ? ". Round decisivo" : "") + ". Assistir no mapa" });
      var topo = Math.min(y, zero);
      function liga() { acende(true); mostraDica(i, p, topo); sincroniza("peso", c.round, true); }
      function desliga() { acende(false); escondeDica(); sincroniza("peso", c.round, false); }
      alvo.addEventListener("mouseenter", liga);
      alvo.addEventListener("mouseleave", desliga);
      alvo.addEventListener("focus", liga);
      alvo.addEventListener("blur", desliga);
      alvo.addEventListener("click", function () { assisteRound(c.round); });
      alvo.addEventListener("keydown", function (e) {
        if (e.key === "Enter" || e.key === " ") { e.preventDefault(); assisteRound(c.round); }
      });
      svg.appendChild(alvo);

      if (c.round % 2 === 1 || dec) {
        var t = svgEl("text", { x: X(i), y: H - pB + 42, "text-anchor": "middle",
          fill: dec ? C.decisivo : C.apagado, "font-family": C.fNum, "font-size": 10.5 });
        t.textContent = c.round;
        svg.appendChild(t);
      }
      if (dec) {
        var td = svgEl("text", { x: X(i), y: H - pB + 56, "text-anchor": "middle", fill: C.decisivo,
          "font-family": C.fTexto, "font-size": 10.5 });
        td.textContent = "decisivo";
        svg.appendChild(td);
      }
    });

    // Rótulo direto nas três maiores barras (as de `win_probability.top`, a ordenação que o payload já
    // publica). Um rótulo que bateria em outro sobe (ou desce) uma linha; se nem assim couber, nenhum
    // dos três fica no gráfico: os valores estão nos cartões logo abaixo.
    var indice = {};
    curva.forEach(function (c, i) { indice[c.round] = i; });
    var top = ((D.win_probability || {}).top || []).filter(function (t) { return indice[t.round] != null; });
    var rotulos = [];
    function bate(a, b) { return a.x0 < b.x1 && b.x0 < a.x1 && a.y0 < b.y1 && b.y0 < a.y1; }
    var cabem = top.every(function (t) {
      var i = indice[t.round], v = delta[i];
      var base = v >= 0 ? Math.min(Y(v), zero - ALTURA_MINIMA) - 5 : Math.max(Y(v), zero + ALTURA_MINIMA) + FONTE + 3;
      var w = T.rotulos[i].length * FONTE * 0.62;
      for (var tentativa = 0; tentativa < 3; tentativa++) {
        var y = base + (v >= 0 ? -1 : 1) * tentativa * (FONTE + 3);
        var cx = { x0: X(i) - w / 2 - 2, x1: X(i) + w / 2 + 2, y0: y - FONTE, y1: y + 2 };
        var dentro = v >= 0 ? cx.y0 >= 0 : cx.y1 <= H - pB + 30;
        if (!dentro) return false;
        if (!caixas.concat(rotulos.map(function (r) { return r.caixa; })).some(function (o) { return bate(cx, o); })) {
          rotulos.push({ i: i, y: y, caixa: cx });
          return true;
        }
      }
      return false;
    });
    var grupo = svgEl("g", { "class": "peso-rotulos", "aria-hidden": "true" });
    if (cabem) {
      rotulos.forEach(function (r) {
        var t = svgEl("text", { x: X(r.i), y: r.y, "text-anchor": "middle", fill: C.tinta2,
          "font-family": C.fNum, "font-size": FONTE });
        t.textContent = T.rotulos[r.i];
        grupo.appendChild(t);
      });
      svg.appendChild(grupo);
    }
    // Abaixo desta largura (em px na tela) o rótulo de 10 unidades do viewBox fica menor que 8 px e
    // deixa de ser lido: os valores ficam só nos cartões.
    var LARGURA_MINIMA_DOS_ROTULOS = 720;
    // A aba Placar abre escondida (largura 0): a largura é lida de novo cada vez que o gráfico muda de
    // tamanho, inclusive quando a aba aparece.
    function rotulosPelaLargura() {
      grupo.style.display = svg.getBoundingClientRect().width < LARGURA_MINIMA_DOS_ROTULOS ? "none" : "";
    }
    rotulosPelaLargura();
    if (window.ResizeObserver) new ResizeObserver(rotulosPelaLargura).observe(svg);
    else window.addEventListener("resize", rotulosPelaLargura);

    var leg = document.getElementById("wplegend");
    if (leg) {
      leg.innerHTML =
        "<span><i style='background:var(--ct)'></i> " + esc(LADO.A) + " venceu o round</span>" +
        "<span><i style='background:var(--tr)'></i> " + esc(LADO.B) + " venceu o round</span>" +
        (decRound != null ? "<span><i style='background:none;box-shadow:inset 0 0 0 2px var(--decisivo)'></i> round decisivo</span>" : "") +
        "<span style='color:var(--apagado)'>modelo neutro: cada round vale 50/50, " +
        "e a alavancagem vem só do placar</span>";
    }

    // Tabela para leitor de tela: o mesmo conteúdo das barras, round a round.
    var tab = document.getElementById("peso-tabela");
    if (tab) {
      tab.innerHTML = "<caption>" + esc(T.titulo) + "</caption>" +
        "<thead><tr><th scope='col'>Round</th><th scope='col'>Placar</th><th scope='col'>Variação</th>" +
        "<th scope='col'>Time que venceu o round</th></tr></thead><tbody>" +
        curva.map(function (c, i) {
          return "<tr><th scope='row'>" + esc(c.round) + (c.round === decRound ? " (decisivo)" : "") + "</th>" +
            "<td>" + esc(T.placares[i]) + "</td><td>" + esc(T.frases[i]) + "</td>" +
            "<td>" + esc(nomeLado(c.winner_team)) + "</td></tr>";
        }).join("") + "</tbody>";
    }

    // Os três rounds que mais mexeram, em ordem de peso: o mesmo texto da dica e o mesmo clique.
    var cartoes = document.getElementById("peso-cartoes");
    if (cartoes) {
      cartoes.innerHTML = top.map(function (t, j) {
        var c = curva[indice[t.round]], p = prog[t.round] || c, txt = T.cartoes[j] || {};
        return "<article class='card peso-cartao'>" +
          "<div class='pc-cab'><span>" + esc(txt.cabecalho) + "</span>" +
          (t.round === decRound ? "<span class='tag decisivo'>decisivo</span>" : "") + "</div>" +
          "<div class='pc-var'><i style='background:var(--" + (c.winner_team === "A" ? "ct" : "tr") + ")'></i>" +
          esc(txt.variacao) + "</div>" +
          "<p>" + esc(roundHeadline(PONTUADOS[t.round] || p, p)) + "</p>" +
          "<button type='button' class='pc-ir' data-round='" + esc(t.round) + "'>Assistir no mapa</button>" +
          "</article>";
      }).join("");
      Array.prototype.forEach.call(cartoes.querySelectorAll(".pc-ir"), function (b) {
        b.addEventListener("click", function () { assisteRound(Number(b.getAttribute("data-round"))); });
      });
    }
  })();

  (function swing() {
    var svg = document.getElementById("swing");
    var W = 900, H = 290, pL = 32, pR = 12, pT = 16, pB = 44;
    var prog = D.progression;
    var diffs = prog.map(function (p) { return p.score_a - p.score_b; });
    var mx2 = Math.max(4, Math.max.apply(null, diffs.map(Math.abs)));
    var X = function (i) { return pL + (i / (prog.length - 1)) * (W - pL - pR); };
    var Y = function (v) { return pT + (1 - (v + mx2) / (2 * mx2)) * (H - pT - pB); };
    var z = Y(0);

    svg.appendChild(svgEl("rect", { x: pL, y: pT, width: W - pL - pR, height: z - pT, fill: C.ct, "fill-opacity": 0.06 }));
    svg.appendChild(svgEl("rect", { x: pL, y: z, width: W - pL - pR, height: (H - pB) - z, fill: C.tr, "fill-opacity": 0.06 }));

    for (var g = -mx2; g <= mx2; g += 2) {
      svg.appendChild(svgEl("line", { x1: pL, x2: W - pR, y1: Y(g), y2: Y(g),
        stroke: g === 0 ? C.borda : C.linha, "stroke-width": g === 0 ? 1.4 : 1 }));
      var lb = svgEl("text", { x: pL - 8, y: Y(g) + 4, "text-anchor": "end", fill: C.apagado,
        "font-family": C.fNum, "font-size": 10.5 });
      lb.textContent = (g > 0 ? "+" : "") + g;
      svg.appendChild(lb);
    }

    // Área acima de zero em azul (Time A na frente), abaixo em laranja (Time B).
    // Os pontos em que a linha cruza o zero entram no contorno, senão a cor de
    // um time vazaria para o trecho em que o outro já liderava.
    var contorno = [];
    diffs.forEach(function (v, i) {
      if (i > 0 && diffs[i - 1] * v < 0) {
        var u = diffs[i - 1] / (diffs[i - 1] - v);
        contorno.push([X(i - 1) + (X(i) - X(i - 1)) * u, 0]);
      }
      contorno.push([X(i), v]);
    });
    function areaDoLado(sinal, cor) {
      var d = "M " + contorno[0][0] + " " + z;
      contorno.forEach(function (pt) {
        d += " L " + pt[0] + " " + Y(sinal > 0 ? Math.max(pt[1], 0) : Math.min(pt[1], 0));
      });
      d += " L " + contorno[contorno.length - 1][0] + " " + z + " Z";
      svg.appendChild(svgEl("path", { d: d, fill: cor }));
    }
    areaDoLado(1, C.ctArea);
    areaDoLado(-1, C.trArea);
    // A linha é UMA medida (diferença de rounds): fica em tinta neutra, e quem
    // carrega a cor de cada time são as áreas e as bolinhas.
    svg.appendChild(svgEl("path", {
      d: diffs.map(function (v, i) { return (i ? "L" : "M") + " " + X(i) + " " + Y(v); }).join(" "),
      fill: "none", stroke: C.tinta2, "stroke-width": 2, "stroke-linejoin": "round", "stroke-linecap": "round"
    }));

    // Cada round vira um alvo clicável. O círculo visível é pequeno demais pra
    // mirar com o mouse (e muito menos no toque), então por cima dele vai um
    // alvo transparente de raio 11 — é ele que recebe hover, clique e foco.
    var tip = document.createElement("div");
    tip.className = "rtip";
    tip.hidden = true;
    svg.parentNode.appendChild(tip);

    function showTip(i, p, dot) {
      var box = svg.getBoundingClientRect();
      var k = box.width / W;  // o SVG é responsivo: converte coordenada do viewBox em pixel

      // a dica é a de dicaDoRound, a mesma do gráfico "Quanto cada round pesou"
      tip.innerHTML = dicaDoRound(p);

      tip.hidden = false;
      tip.style.left = (X(i) * k) + "px";
      tip.style.top = (Y(diffs[i]) * k - 12) + "px";
      tip.classList.add("on");
      dot.classList.add("hot");
      dot.setAttribute("r", 6);
      sincroniza("swing", p.round, true);
    }

    function hideTip(dot, dec, round) {
      tip.classList.remove("on");
      tip.hidden = true;
      dot.classList.remove("hot");
      dot.setAttribute("r", dec ? 5.5 : 3.2);
      sincroniza("swing", round, false);
    }

    var goToRound = assisteRound;

    prog.forEach(function (p, i) {
      var dec = p.round === decRound;
      var dot = svgEl("circle", { cx: X(i), cy: Y(diffs[i]), r: dec ? 5.5 : 3.2,
        fill: dec ? C.decisivo : (diffs[i] > 0 ? C.ct : diffs[i] < 0 ? C.tr : C.apagado), stroke: C.superficie, "stroke-width": dec ? 2.5 : 1.5,
        "class": "swingdot" });
      svg.appendChild(dot);
      // o round acende aqui quando o mouse passa por ele no gráfico "Quanto cada round pesou"
      SINC.swing[p.round] = function (on) {
        dot.classList.toggle("hot", on);
        dot.setAttribute("r", on ? 6 : (dec ? 5.5 : 3.2));
      };

      // aria-label em vez de <title>: o <title> do SVG viraria um tooltip nativo
      // do navegador por cima do balão, dizendo menos e atrapalhando a leitura.
      var hit = svgEl("circle", { cx: X(i), cy: Y(diffs[i]), r: 11, "class": "swinghit",
        tabindex: 0, role: "button", "aria-label": "Round " + p.round + ": assistir" });

      hit.addEventListener("mouseenter", function () { showTip(i, p, dot); });
      hit.addEventListener("mouseleave", function () { hideTip(dot, dec, p.round); });
      hit.addEventListener("focus", function () { showTip(i, p, dot); });
      hit.addEventListener("blur", function () { hideTip(dot, dec, p.round); });
      hit.addEventListener("click", function () { goToRound(p.round); });
      hit.addEventListener("keydown", function (e) {
        if (e.key === "Enter" || e.key === " ") { e.preventDefault(); goToRound(p.round); }
      });
      svg.appendChild(hit);

      if (p.round % 2 === 1 || dec) {
        var t = svgEl("text", { x: X(i), y: H - pB + 17, "text-anchor": "middle",
          fill: dec ? C.decisivo : C.apagado, "font-family": C.fNum, "font-size": 10.5 });
        t.textContent = p.round;
        svg.appendChild(t);
      }
      if (p.bomb_planted) {
        svg.appendChild(svgEl("rect", { x: X(i) - 2.5, y: H - pB + 25, width: 5, height: 5, fill: C.apagado, opacity: 0.55 }));
      }
    });

    var hx = X(M.halftime - 1);
    svg.appendChild(svgEl("line", { x1: hx, x2: hx, y1: pT, y2: H - pB, stroke: C.borda,
      "stroke-width": 1, "stroke-dasharray": "3 4" }));
    var ht = svgEl("text", { x: hx + 6, y: pT + 11, fill: C.apagado, "font-family": C.fNum, "font-size": 10 });
    ht.textContent = "intervalo";
    svg.appendChild(ht);
  })();

