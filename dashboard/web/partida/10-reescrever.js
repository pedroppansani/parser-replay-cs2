  /* ================= REESCREVER (R2, decisão 57) ================= */
  // O modo Reescrever é um modo da aba Replay (D1): o palco é o mesmo (o mapa fica no mesmo lugar e do mesmo tamanho em todo estado), a
  // moldura e as duas colunas viram o violeta da prancheta (D2) e as 10 peças ficam editáveis nas posições reais do instante em que o
  // Replay estava parado. Nesta fase: entrar, arrastar as peças vivas, "Voltar ao real" e sair. A "Sua versão" tocar, o fantasma e "O
  // que mudou" são as fases R3 em diante (o botão de tocar fica desligado e diz isso). Sair descarta as edições.
  // O estado compartilhado com o desenho é o objeto `reescrever` (02-replay.js); os rótulos vêm do Python (PAGINA.reescrever).
  (function () {
    var TX = PAGINA.reescrever;
    if (!TX) return;
    var palco = document.getElementById("palco"), mapwrap = document.getElementById("mapwrap");
    var hosts = { ct: document.getElementById("squad-ct"), t: document.getElementById("squad-t") };
    var stage = palco.closest(".stage");
    var acoes = document.getElementById("rh-acoes"), trEsq = document.getElementById("tr-esq");
    var playBtn = document.getElementById("play"), scrubEl = document.getElementById("scrub"), speedBtn = document.getElementById("speed");
    var ALVO = 24;            // px de tela: o raio de pegar a peça (alvo de 48 px)
    var MOVIDA = 8;           // unidades de jogo: menos que isso a peça não conta como editada
    var edicoes = {};         // nome -> {x, y} em unidades de jogo
    var origem = {};          // nome -> {x, y} no instante (o real)
    var pecas = [];           // {p, vivo, morreuEm}
    var arrasto = null;
    var t0 = 0;
    var rotulos = null;       // os aria-label dos elencos, de volta ao sair

    reescrever.escala = 1.25;
    reescrever.sel = null;

    function formata(texto, o) { return texto.replace(/\{(\w+)\}/g, function (_, k) { return o[k]; }); }
    function relogioNo(i) { return relogioDe(i / R.sample_hz).main; }
    function novo(tag, cls, texto) {
      var n = document.createElement(tag);
      if (cls) n.className = cls;
      if (texto != null) n.textContent = texto;
      return n;
    }
    function botao(texto, cls, aoClicar) {
      var b = novo("button", cls, texto);
      b.type = "button";
      b.addEventListener("click", aoClicar);
      return b;
    }

    reescrever.posicaoEditada = function (nome) { var e = edicoes[nome]; return e ? [e.x, e.y] : null; };

    // a "Sua versão" no mapa: o losango onde ela começa e o caminho novo, branco sobre o contorno (design §4.3)
    reescrever.desenhaSobre = function (c) {
      var contorno = C.contorno, tinta = CM.tinta;
      c.save();
      c.lineCap = "round"; c.lineJoin = "round";
      Object.keys(edicoes).forEach(function (nome) {
        var o = origem[nome], e = edicoes[nome];
        if (!o || !editada(nome)) return;
        var ax = mx(o.x), ay = my(o.y), bx = mx(e.x), by = my(e.y);
        [[contorno, 5.2], [tinta, 2.4]].forEach(function (par) {
          c.strokeStyle = par[0]; c.lineWidth = par[1];
          c.beginPath(); c.moveTo(ax, ay); c.lineTo(bx, by); c.stroke();
        });
        c.beginPath(); c.moveTo(ax, ay - 6.5); c.lineTo(ax + 6.5, ay); c.lineTo(ax, ay + 6.5); c.lineTo(ax - 6.5, ay); c.closePath();
        c.fillStyle = tinta; c.strokeStyle = contorno; c.lineWidth = 2; c.fill(); c.stroke();
      });
      if (reescrever.sel && origem[reescrever.sel]) {
        var q = edicoes[reescrever.sel] || origem[reescrever.sel];
        c.beginPath(); c.arc(mx(q.x), my(q.y), 15, 0, Math.PI * 2);
        c.strokeStyle = contorno; c.lineWidth = 4.4; c.stroke();
        c.strokeStyle = tinta; c.lineWidth = 2; c.stroke();
      }
      c.restore();
    };

    function editada(nome) {
      var o = origem[nome], e = edicoes[nome];
      return !!(o && e && Math.hypot(e.x - o.x, e.y - o.y) >= MOVIDA);
    }
    function algumaEditada() { return Object.keys(edicoes).some(editada); }

    /* ---------- o mapa: de um ponto da tela a unidades de jogo, e a peça sob o ponteiro ---------- */
    function matrizDaVista() {
      var sc = document.createElement("canvas"); sc.width = cv.width; sc.height = cv.height;
      var c = sc.getContext("2d");
      if (window.MapAnnotations && MapAnnotations.applyView) MapAnnotations.applyView(c);
      return c.getTransform();
    }
    function doPonteiro(e) {
      var r = cv.getBoundingClientRect(), k = cv.width / r.width;
      var cx = (e.clientX - r.left) * k, cy = (e.clientY - r.top) * k;
      return { cx: cx, cy: cy, k: k, r: r };
    }
    function aGameUnits(cx, cy) {
      var p = new DOMPoint(cx, cy).matrixTransform(matrizDaVista().inverse());
      return { x: p.x / RAD.scale_px_per_unit + RAD.origin_x, y: RAD.origin_y - p.y / RAD.scale_px_per_unit };   // p: pixels do radar (a vista já desfeita)
    }
    function acha(e) {
      var m = matrizDaVista(), q = doPonteiro(e), melhor = null, dist = ALVO;
      pecas.forEach(function (it) {
        if (!it.vivo) return;
        var pos2 = edicoes[it.p.name] || origem[it.p.name];
        var pt = new DOMPoint(mx(pos2.x), my(pos2.y)).matrixTransform(m);
        var d = Math.hypot(pt.x - q.cx, pt.y - q.cy) / q.k;
        if (d <= dist) { dist = d; melhor = it.p.name; }
      });
      return melhor;
    }

    mapwrap.addEventListener("pointerdown", function (e) {
      if (!reescrever.ativo || (e.button && e.button > 0)) return;
      var nome = acha(e);
      if (!nome) return;
      e.preventDefault(); e.stopPropagation();       // a peça vem antes do desenho e do arrastar do mapa
      seleciona(nome);
      arrasto = { nome: nome, id: e.pointerId };
      try { mapwrap.setPointerCapture(e.pointerId); } catch (x) { /* sem captura: o movimento segue pelo mapa */ }
    }, true);
    mapwrap.addEventListener("pointermove", function (e) {
      if (!arrasto || e.pointerId !== arrasto.id) return;
      e.preventDefault(); e.stopPropagation();
      var q = doPonteiro(e);
      var cx = Math.min(cv.width, Math.max(0, q.cx)), cy = Math.min(cv.height, Math.max(0, q.cy));   // a peça fica dentro do mapa
      var g = aGameUnits(cx, cy);
      edicoes[arrasto.nome] = { x: g.x, y: g.y };
      atualizaBanco();
      draw();
    }, true);
    function soltou(e) {
      if (!arrasto || e.pointerId !== arrasto.id) return;
      e.stopPropagation();
      arrasto = null;
    }
    mapwrap.addEventListener("pointerup", soltou, true);
    mapwrap.addEventListener("pointercancel", soltou, true);

    /* ---------- o banco (coluna da esquerda) e o painel (coluna da direita) ---------- */
    function seleciona(nome) {
      reescrever.sel = nome;
      atualizaBanco();
      draw();
    }
    function montaBanco() {
      var host = hosts.ct;
      host.className = "card squad banco";
      host.textContent = "";
      ["ct", "t"].forEach(function (lado) {
        var deste = pecas.filter(function (it) { return it.p.side === lado; });
        var h = novo("h4", lado);       // "CT  FURIA" e "TR  VITALITY", como as colunas do Assistir
        h.appendChild(document.createTextNode((lado === "ct" ? "CT" : "TR") + " ")); h.appendChild(novo("b", null, deste.length ? nomeLado(deste[0].p.team) : ""));
        host.appendChild(h);
        deste.forEach(function (it) {
          var b = novo("button", "peca-rw " + lado);
          b.type = "button";
          b.dataset.nome = it.p.name;
          b.setAttribute("aria-pressed", "false");
          var topo = novo("span", "pr-topo");
          topo.appendChild(novo("b", "pr-nome", it.p.name));
          topo.appendChild(novo("span", "pr-hp", it.vivo ? String(it.p.hp[t0]) : "0"));
          b.appendChild(topo);
          var w = it.vivo ? it.p.w[t0] : -1;
          var pi = it.vivo && it.p.p ? it.p.p[t0] : -1;
          var meio = it.vivo ? [(w >= 0 ? cur.weapons[w] : ""), (pi >= 0 ? cur.places[pi] : "")].filter(Boolean).join(" · ")
            : formata(TX.morto, { relogio: relogioNo(it.morreuEm), inicio: relogioNo(t0) });
          b.appendChild(novo("span", "pr-meio", meio));
          b.appendChild(novo("span", "pr-tag", TX.editado));
          if (it.vivo) b.addEventListener("click", function () { seleciona(it.p.name); });
          else b.setAttribute("aria-disabled", "true");
          host.appendChild(b);
        });
      });
    }
    function atualizaBanco() {
      Array.prototype.forEach.call(hosts.ct.querySelectorAll(".peca-rw"), function (b) {
        b.setAttribute("aria-pressed", String(b.dataset.nome === reescrever.sel));
        b.classList.toggle("editada", editada(b.dataset.nome));
      });
      var voltar = document.getElementById("rw-voltar");
      if (voltar) voltar.disabled = !algumaEditada();
    }
    function montaPainel() {
      var host = hosts.t;
      host.className = "card squad painel-rw";
      host.textContent = "";
      host.appendChild(novo("h4", null, TX.titulo));
      var fixa = novo("p", "rw-fixa"); fixa.appendChild(novo("b", null, TX.fixa_forte)); fixa.appendChild(document.createTextNode(" " + TX.fixa_resto));
      host.appendChild(fixa);
      host.appendChild(novo("p", "rw-comeca", formata(TX.comeca_em, { relogio: relogioNo(t0) })));
      var dica = novo("p", "rw-dica", TX.dica); dica.setAttribute("role", "status");
      host.appendChild(dica);
      var voltar = botao(TX.voltar, "rw-btn", function () { edicoes = {}; atualizaBanco(); draw(); });
      voltar.id = "rw-voltar"; voltar.disabled = true;
      host.appendChild(voltar);
    }

    /* ---------- o cabeçalho do palco e o transporte ---------- */
    var res = document.getElementById("rh-res"), resSalvo = "", resTitulo = "";
    function montaAcoes() {
      acoes.textContent = "";
      if (reescrever.ativo) {
        resSalvo = res.textContent; resTitulo = res.title; res.textContent = TX.curta; res.title = TX.curta;   // no modo, o resumo do round cede lugar à frase curta
        acoes.appendChild(novo("span", "rw-pilula", "● " + TX.pilula));
        var s = botao(TX.sair, "rw-btn", function () { reescrever.sai(); });
        s.id = "rw-sair";
        acoes.appendChild(s);
      } else {
        if (resSalvo) { res.textContent = resSalvo; res.title = resTitulo; resSalvo = ""; }
        var e = botao(TX.entrar, "rw-btn prim", function () { reescrever.entra(); });
        e.id = "rw-entrar";
        acoes.appendChild(e);
      }
    }
    var daqui = botao("", "rw-btn prim rw-daqui", function () { reescrever.entra(); });
    daqui.id = "rw-daqui";
    daqui.appendChild(novo("span", null, TX.daqui));
    daqui.appendChild(novo("span", "rw-hora", ""));
    trEsq.appendChild(daqui);

    // "Reescrever daqui · 0:55": só com o Replay parado e fora do modo; o espaço fica reservado (visibility), então nada se mexe
    reescrever.aoQuadro = function () {
      var vivo = !reescrever.ativo && !playing;
      daqui.style.visibility = vivo ? "visible" : "hidden";
      daqui.disabled = !vivo;
      if (vivo) daqui.lastChild.textContent = " · " + relogioNo(Math.floor(pos));
    };

    /* ---------- entrar e sair ---------- */
    reescrever.entra = function () {
      if (reescrever.ativo || !cur || document.querySelector("[data-panel='replay']").hidden) return;
      setPlaying(false);
      t0 = Math.floor(pos); pos = t0; frame = t0;     // o instante é o quadro gravado imediatamente anterior (o mesmo do `instante()`)
      scrubEl.value = t0;
      edicoes = {}; origem = {}; arrasto = null; reescrever.sel = null;
      pecas = cur.players.map(function (p) {
        var vivo = !!p.alive[t0], q = 0;
        if (!vivo) { while (q < t0 && p.alive[q]) q++; } else { origem[p.name] = { x: p.x[t0], y: p.y[t0] }; }
        return { p: p, vivo: vivo, morreuEm: q };
      });
      reescrever.ativo = true;
      palco.setAttribute("data-tema", "violeta");
      hosts.ct.setAttribute("data-tema", "violeta"); hosts.t.setAttribute("data-tema", "violeta");
      stage.classList.add("reescrevendo");
      rotulos = { ct: hosts.ct.getAttribute("aria-label"), t: hosts.t.getAttribute("aria-label") };
      hosts.ct.setAttribute("aria-label", TX.banco); hosts.t.setAttribute("aria-label", TX.titulo);   // as colunas deixam de ser os elencos
      playBtn.disabled = true; playBtn.title = TX.toca_desligado;
      scrubEl.disabled = true; speedBtn.disabled = true;
      montaBanco(); montaPainel(); montaAcoes();
      draw();
      var primeira = hosts.ct.querySelector(".peca-rw:not([aria-disabled])");
      if (primeira) primeira.focus({ preventScroll: true });
    };
    reescrever.sai = function (semFoco) {
      if (!reescrever.ativo) return;
      reescrever.ativo = false; reescrever.sel = null; arrasto = null; edicoes = {}; origem = {}; pecas = [];
      palco.setAttribute("data-tema", "escuro");
      hosts.ct.removeAttribute("data-tema"); hosts.t.removeAttribute("data-tema");
      stage.classList.remove("reescrevendo");
      if (rotulos) { hosts.ct.setAttribute("aria-label", rotulos.ct); hosts.t.setAttribute("aria-label", rotulos.t); rotulos = null; }
      playBtn.disabled = false; playBtn.removeAttribute("title");
      scrubEl.disabled = false; speedBtn.disabled = false;
      buildSquads(); montaAcoes();
      draw();
      if (!semFoco) { var e = document.getElementById("rw-entrar"); if (e) e.focus({ preventScroll: true }); }
    };
    // o Esc que fecha o "?" dos atalhos (ou outra caixa aberta) não deve descartar as edições: a captura vê o "?" ANTES de ele se fechar
    var escJaTinhaDono = false;
    document.addEventListener("keydown", function (e) {
      var pop = document.getElementById("atalhos");
      escJaTinhaDono = e.key === "Escape" && !!(pop && !pop.hidden);
    }, true);
    document.addEventListener("keydown", function (e) {
      if (e.key !== "Escape" || !reescrever.ativo || e.defaultPrevented || escJaTinhaDono) return;
      if (document.querySelector("[data-panel='replay']").hidden || (e.target.closest && e.target.closest("input, select, textarea"))) return;
      e.preventDefault(); reescrever.sai();
    });

    // o estado para os testes (como `__medicaoRotulos` e `__marcasDeBorda`): quem está editável e onde cada peça está
    window.__reescrever = function () {
      return {
        ativo: reescrever.ativo, instante: t0, relogio: relogioNo(t0), selecionada: reescrever.sel,
        pecas: pecas.map(function (it) {
          var e = edicoes[it.p.name], o = origem[it.p.name];
          return { nome: it.p.name, lado: it.p.side, editavel: it.vivo, editada: editada(it.p.name), x: e ? e.x : (o ? o.x : null), y: e ? e.y : (o ? o.y : null),
                   x0: o ? o.x : null, y0: o ? o.y : null };
        })
      };
    };

    montaAcoes();
    reescrever.aoQuadro();
  })();
