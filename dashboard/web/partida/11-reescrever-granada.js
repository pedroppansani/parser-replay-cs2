  /* ================= REESCREVER · TROCAR A GRANADA (R4, decisão 59) ================= */
  // Com a ferramenta Granada, o jogador escolhe uma granada do real lançada DEPOIS do instante e a troca por um arremesso REAL da biblioteca
  // (`arremessos/<mapa>.js`, a mesma da prancheta): do mesmo tipo, do mesmo lado de quem lançou, a até 150 u de onde ele estava e com tempo de voo
  // conhecido (decoy fora; molotov também precisa do tempo de efeito). A granada trocada sai da mão no mesmo instante da original e cai
  // `voo_s` depois; o caminho dela é a reta até o destino (a biblioteca grava origem e destino, não a trajetória). O site não diz o que a troca muda.
  // Fala com o núcleo (10-reescrever.js) por `reescrever.nucleo` e é chamado por ele em `reescrever.granada`.
  (function () {
    var TX = PAGINA.reescrever, N = reescrever.nucleo;
    if (!TX || !N) return;
    var RAIO_U = 150, MAX_GRUPOS = 6;
    var bib = { estado: "nao", dados: null };   // nao | carregando | pronta | erro | sem
    var trocas = [];       // {n, alt}: n é a granada do real (objeto de cur.nades), alt a linha da biblioteca
    var sel = null, escolha = null, hover = null;
    var secao = null, ferr = {};
    var mapwrap = document.getElementById("mapwrap");
    reescrever.ferramenta = "mover";

    function nome1(n) { return n.by; }
    function jogadorDe(n) { return N.pecas().filter(function (q) { return q.p.name === n.by; })[0] || null; }
    function origemDe(n) { return n.l && n.l.o ? [n.l.o[0], n.l.o[1]] : [n.x[0], n.y[0]]; }
    function fimDe(n) { var u = n.x.length - 1; return [n.x[u], n.y[u]]; }
    function nivelDe(n) { var it = jogadorDe(n); return it && it.p.lv ? it.p.lv[n.f0] || 0 : 0; }
    function lugarDe(x, y, nivel) {
      var L = RAD.lugares && RAD.lugares.grade;
      if (!L || L.andares.length !== 1) return null;     // mapa de vários andares: o andar do destino não é conhecido (a Nuke dentro do Reescrever é do R6), então sem nome
      nivel = 0;
      var px = MapCore.jogoParaPixel(RAD, x, y), cx = Math.floor(px[0] / L.lado), cy = Math.floor(px[1] / L.lado), rle = L.andares[nivel][String(cy)];
      if (!rle) return null;
      for (var i = 0; i < rle.length; i += 3) if (rle[i] <= cx && cx < rle[i] + rle[i + 2]) return RAD.lugares.textos[rle[i + 1]];
      return null;
    }
    function segundos(v) { return (Math.round(v * 10) / 10).toString().replace(".", ","); }
    function tipoDe(k) { return TX.granadas[k] || k; }

    // as granadas do real que dá para trocar: lançadas depois do instante, menos o decoy
    function candidatas() {
      return cur.nades.filter(function (n) { return n.f0 > N.t0() && n.k !== "decoy" && n.k !== undefined; }).sort(function (a, b) { return a.f0 - b.f0; });
    }
    function trocaDe(n) { return trocas.filter(function (t) { return t.n === n; })[0] || null; }
    function efetivas() { return trocas.filter(function (t) { return !N.editada(t.n.by); }); }
    function trocada(n) { return !!n && efetivas().some(function (t) { return t.n === n; }); }
    function queda(n, alt) { return n.f0 + Math.max(1, Math.round(alt.voo_s * R.sample_hz)); }     // no desenho o voo anda em quadros inteiros (4 por segundo): a queda é no quadro em que a granada chega

    // as alternativas de uma granada: reais, do mesmo tipo e lado, perto de onde ele estava, agrupadas pelo lugar do destino
    function alternativas(n) {
      var it = jogadorDe(n), o = origemDe(n), nivel = nivelDe(n), orig = fimDe(n), nomeOrig = lugarDe(orig[0], orig[1], nivel), grupos = {}, lista = [];
      ((bib.dados && bib.dados.arremessos) || []).forEach(function (a) {
        if (a.arma !== n.k || !it || a.lado !== it.p.side || !(a.voo_s > 0)) return;
        if (a.arma === "molotov" && !(a.efeito_s > 0)) return;
        if (n.l ? a.id === n.l.id : (a.jogador === n.by && a.round === cur.round && Math.hypot(a.destino[0] - orig[0], a.destino[1] - orig[1]) <= 60)) return;     // o próprio arremesso do real (sem ligação gravada: mesmo jogador, round e destino)
        var d = Math.hypot(a.origem[0] - o[0], a.origem[1] - o[1]);
        if (d > RAIO_U) return;
        var lugar = lugarDe(a.destino[0], a.destino[1], nivel), chave = lugar || ("#" + a.id);     // destino sem nome não agrupa
        var g = grupos[chave];
        if (!g) { g = grupos[chave] = { lugar: lugar, n: 0, melhor: null, d: Infinity, mesmo: !!lugar && lugar === nomeOrig }; lista.push(g); }
        g.n++;
        if (d < g.d) { g.d = d; g.melhor = a; }
      });
      lista.sort(function (a, b) { return b.n - a.n || a.d - b.d; });
      return lista;
    }

    /* ---------- a biblioteca: um <script> próprio (funciona também com a página aberta como arquivo), carregado só ao usar a ferramenta ---------- */
    function carrega() {
      if (bib.estado === "carregando" || bib.estado === "pronta") return;
      if (!TX.biblioteca) { bib.estado = "sem"; render(); return; }
      bib.estado = "carregando"; render();
      var antes = window.Prancheta, s = document.createElement("script");
      function restaura() { if (antes === undefined) delete window.Prancheta; else window.Prancheta = antes; if (s.parentNode) s.parentNode.removeChild(s); }
      window.Prancheta = { recebeBiblioteca: function (b) { if (b && Array.isArray(b.arremessos)) { bib.dados = b; bib.estado = "pronta"; } } };      // o arquivo chama Prancheta.recebeBiblioteca(...)
      s.onload = function () { restaura(); if (bib.estado !== "pronta") bib.estado = "erro"; render(); };
      s.onerror = function () { restaura(); bib.estado = "erro"; render(); };
      s.src = TX.biblioteca;
      document.body.appendChild(s);
    }

    /* ---------- o painel ---------- */
    function el(tag, cls, texto) { return N.novo(tag, cls, texto); }
    function defineFerramenta(f) {
      if (reescrever.sua) return;
      reescrever.ferramenta = f;
      if (f !== "granada") { sel = null; escolha = null; }
      if (f === "granada") carrega();
      render();
      draw();
    }
    reescrever.granada = {
      monta: function (host) {
        var grupo = el("div", "rw-ferr"); grupo.setAttribute("role", "radiogroup"); grupo.setAttribute("aria-label", TX.ferramenta);
        ["mover", "granada"].forEach(function (f) {
          var b = el("button", "rw-btn", TX["ferr_" + f]); b.type = "button"; b.id = "rw-ferr-" + f; b.setAttribute("role", "radio");
          b.addEventListener("click", function () { defineFerramenta(f); });
          grupo.appendChild(b); ferr[f] = b;
        });
        grupo.addEventListener("keydown", function (e) {
          if (["ArrowLeft", "ArrowRight", "ArrowUp", "ArrowDown"].indexOf(e.key) < 0 || reescrever.sua) return;
          e.preventDefault();
          var f = reescrever.ferramenta === "mover" ? "granada" : "mover";
          defineFerramenta(f); focaNoPainel(ferr[f]);
        });
        host.appendChild(grupo);
        secao = el("div", "rw-granada"); secao.id = "rw-granada";
        host.appendChild(secao);
        render();
      },
      entra: function () { trocas = []; hover = null; sel = null; escolha = null; reescrever.ferramenta = "mover"; recalcula(); },
      sai: function () { trocas = []; hover = null; sel = null; escolha = null; reescrever.ferramenta = "mover"; secao = null; recalcula(); },
      limpa: function () { trocas = []; hover = null; sel = null; escolha = null; reescrever.ferramenta = "mover"; recalcula(); render(); },
      temTroca: function () { return efetivas().length > 0; },
      trocada: trocada,
      temTrocaDe: function (n) { return !!trocaDe(n); },
      atualiza: function () { recalcula(); render(); },
      desenha: desenha,
      frases: frases,
      estado: function () {
        return { hover: hover ? { k: hover.k, by: hover.by, f0: hover.f0 } : null, ferramenta: reescrever.ferramenta, biblioteca: bib.estado, selecionada: sel ? { k: sel.k, by: sel.by, f0: sel.f0 } : null,
                 escolhida: escolha ? escolha.id : null,
                 trocas: trocas.map(function (t) { return { k: t.n.k, by: t.n.by, f0: t.n.f0, alt: t.alt.id, voo_s: t.alt.voo_s, cai: queda(t.n, t.alt), valida: !N.editada(t.n.by) }; }),
                 candidatas: candidatas().map(function (n) { return { k: n.k, by: n.by, f0: n.f0, lid: n.l ? n.l.id : null, fim: fimDe(n), origem: origemDe(n) }; }),
                 grupos: sel && bib.estado === "pronta" ? alternativas(sel).map(function (g) { return { lugar: g.lugar, n: g.n, id: g.melhor.id, d: g.d, mesmo: g.mesmo }; }) : [],
                 zonas: reescrever.virtuais.smokes.concat(reescrever.virtuais.fires).map(function (z) { return { x: z.x, y: z.y, f0: z.f0, f1: z.f1, k: reescrever.virtuais.smokes.indexOf(z) >= 0 ? "smoke" : "molotov" }; }),
                 virtuais: { nades: reescrever.virtuais.nades.length, smokes: reescrever.virtuais.smokes.length, fires: reescrever.virtuais.fires.length, pops: reescrever.virtuais.pops.length } };
      },
      escolheNoMapa: function (k, by, f0) { var n = candidatas().filter(function (q) { return q.k === k && q.by === by && q.f0 === f0; })[0]; if (n) seleciona(n); }
    };

    // Foco sem mexer na página: o painel rola por dentro (no computador), então o item é trazido para a vista DENTRO do painel antes de receber o foco.
    // Um foco atrás das faixas grudadas faria o `focusin` do v2.js rolar a PÁGINA (decisão 53) e o palco sairia do lugar.
    function focaNoPainel(el) {
      var p = document.getElementById("squad-t");
      if (p && p.scrollHeight > p.clientHeight) {
        var r = el.getBoundingClientRect(), pr = p.getBoundingClientRect();
        if (r.top < pr.top + 8) p.scrollTop += r.top - pr.top - 12;
        else if (r.bottom > pr.bottom - 8) p.scrollTop += r.bottom - pr.bottom + 12;
      }
      el.focus({ preventScroll: true });
    }
    function render() {
      if (!secao) return;
      var foco = document.activeElement && document.activeElement.dataset ? document.activeElement.dataset.foco : null;
      var modo = reescrever.ferramenta;
      if (reescrever.sua) { sel = null; escolha = null; }     // tocando, nada fica escolhido pela metade
      ["mover", "granada"].forEach(function (f) {
        ferr[f].setAttribute("aria-checked", String(modo === f));
        ferr[f].tabIndex = modo === f ? 0 : -1;
        ferr[f].disabled = !!reescrever.sua;
        ferr[f].classList.toggle("ativa", modo === f);
      });
      var dica = document.getElementById("rw-dica");     // com a ferramenta Granada a dica do painel é a dela (o painel não cresce com duas)
      if (dica && !reescrever.sua) dica.textContent = modo === "granada" ? N.formata(TX.granada_dica, { relogio: N.relogioNo(N.t0()) }) : TX.dica;
      secao.textContent = "";
      secao.hidden = modo !== "granada" || !!reescrever.sua;     // tocando a sua versão, nada se escolhe
      if (secao.hidden) return;
      var t0 = N.t0();
      if (bib.estado === "carregando" || bib.estado === "nao") {
        var c = el("p", "rw-gr-carrega", TX.carregando); c.setAttribute("role", "status"); c.tabIndex = -1;
        if (foco === "tentar") setTimeout(function () { focaNoPainel(c); }, 0);     // o botão "Tentar de novo" some: o foco vai para o aviso
        secao.appendChild(c);
        var esq = el("div", "rw-esqueleto"); esq.setAttribute("aria-hidden", "true");
        for (var i = 0; i < 3; i++) esq.appendChild(el("span"));
        secao.appendChild(esq);
        return;
      }
      if (bib.estado === "erro") {
        var er = el("p", "rw-gr-erro", TX.erro); er.setAttribute("role", "alert");
        secao.appendChild(er);
        var de = N.botao(TX.de_novo, "rw-btn", function () { bib.estado = "nao"; carrega(); }); de.dataset.foco = "tentar"; de.id = "rw-gr-tentar";
        secao.appendChild(de);
        return;
      }
      if (bib.estado === "sem") { secao.appendChild(el("p", "rw-gr-erro", TX.sem_biblioteca)); return; }
      var lista = candidatas();
      secao.appendChild(el("h5", null, TX.granadas_titulo));
      if (!lista.length) { secao.appendChild(el("p", null, N.formata(TX.granadas_nenhuma, { relogio: N.relogioNo(t0) }))); return; }
      var ul = el("ul", "rw-grs");
      lista.forEach(function (n, i) {
        var li = el("li"), tr = trocaDe(n);
        var b = el("button", "rw-gr", N.formata(TX.granada_item, { tipo: tipoDe(n.k), nome: nome1(n), relogio: N.relogioNo(n.f0) }) + (tr ? " · " + TX.trocada : ""));
        b.type = "button"; b.dataset.foco = "gr:" + i; b.setAttribute("aria-pressed", String(sel === n));
        b.addEventListener("click", function () { seleciona(n); });
        ["mouseenter", "focus"].forEach(function (ev) { b.addEventListener(ev, function () { defineHover(n); }); });
        ["mouseleave", "blur"].forEach(function (ev) { b.addEventListener(ev, function () { defineHover(null); }); });
        li.appendChild(b); ul.appendChild(li);
      });
      secao.appendChild(ul);
      if (sel) detalhe();
      var alvo = foco ? secao.querySelector('[data-foco="' + foco + '"]') : null;
      if (alvo) focaNoPainel(alvo);
    }
    function detalhe() {
      var n = sel, o = fimDe(n), nivel = nivelDe(n), de = origemDe(n), nomeDe = lugarDe(de[0], de[1], nivel), nomePara = lugarDe(o[0], o[1], nivel);
      var base = { tipo: tipoDe(n.k), nome: nome1(n), relogio: N.relogioNo(n.f0), de: nomeDe, para: nomePara };
      var cx = el("div", "rw-gr-det");
      cx.appendChild(el("p", "rw-gr-real", N.formata(nomeDe && nomePara ? TX.granada_real_de_para : nomePara ? TX.granada_real_para : TX.granada_real, base)));
      if (N.editada(n.by)) { cx.appendChild(el("p", null, N.formata(TX.granada_movida, base))); secao.appendChild(cx); return; }
      var gs = alternativas(n);
      if (!gs.length) cx.appendChild(el("p", null, N.formata(TX.alt_nenhuma, { raio: RAIO_U })));
      else {
        cx.appendChild(el("p", null, N.formata(TX.alt_titulo, { raio: RAIO_U, nome: n.by })));
        gs.slice(0, MAX_GRUPOS).forEach(function (g) {
          var a = g.melhor, b = el("button", "rw-alt"); b.type = "button"; b.dataset.foco = "alt:" + a.id; b.setAttribute("aria-pressed", String(escolha === a));
          var topo = el("span", "rw-alt-topo"); topo.appendChild(el("b", null, g.lugar || TX.sem_nome)); topo.appendChild(el("span", "rw-alt-n", String(g.n)));
          b.appendChild(topo);
          if (g.mesmo) b.appendChild(el("span", "rw-alt-mesmo", TX.mesmo_do_real));
          var times = bib.dados.partidas_times && bib.dados.partidas_times[a.partida];
          b.appendChild(el("span", "rw-alt-l", N.formata(times ? TX.alt_quem : TX.alt_quem_sem_times, { jogador: a.jogador, times: times, round: a.round, dist: Math.round(g.d) })));
          b.appendChild(el("span", "rw-alt-l", descreve(a)));
          b.addEventListener("click", function () { escolha = a; render(); draw(); });
          cx.appendChild(b);
        });
        if (gs.length > MAX_GRUPOS) cx.appendChild(el("p", "rw-gr-mais", N.formata(TX.alt_mais, { n: gs.length - MAX_GRUPOS })));
        var fato = fatoReal(n, escolha, nivel);
        if (fato) cx.appendChild(el("p", "rw-gr-fato", fato));
      }
      var linha = el("div", "rw-gr-acoes");
      var trocar = N.botao(TX.trocar, "rw-btn prim", function () { aplica(); });
      trocar.dataset.foco = "trocar"; trocar.disabled = !escolha;
      linha.appendChild(trocar);
      linha.appendChild(N.botao(TX.cancelar, "rw-btn", function () { var n = sel; sel = null; escolha = null; render(); N.atualizaBanco(true); draw(); focoNaLista(n); })).dataset.foco = "cancelar";
      if (trocaDe(n)) {
        var v = N.botao(TX.voltar_granada, "rw-btn", function () { trocas = trocas.filter(function (t) { return t.n !== n; }); escolha = null; N.atualizaBanco(); draw(); focoNaLista(n); });
        v.dataset.foco = "desfaz"; linha.appendChild(v);
      }
      cx.appendChild(linha);
      secao.appendChild(cx);
    }
    function focoNaLista(n) {      // o foco volta à granada que acabou de ser mexida (ou ao topo da lista)
      var i = n ? candidatas().indexOf(n) : -1, b = secao && (secao.querySelector('[data-foco="gr:' + i + '"]') || secao.querySelector(".rw-gr"));
      if (b) focaNoPainel(b);
    }
    // postura, movimento e se estava no ar, mais de onde veio cada afirmação (decisão 21a): "lido da demo" ou "inferido"
    function descreve(a) {
      var p = [a.postura, a.movimento, a.no_ar === true ? TX.no_ar : a.no_ar === false ? TX.no_chao : null].filter(Boolean).join(" · ");
      var f = a.fontes || {}, v = Object.keys(f).map(function (k) { return f[k]; }), lido = v.filter(function (x) { return x === "lido"; }).length;
      return p + " · " + (!v.length ? TX.fonte_inferido : lido === v.length ? TX.fonte_lido : lido === 0 ? TX.fonte_inferido : TX.fonte_mista);
    }
    // "No real, o mezii joga uma smoke em SNIPERS NEST às 1:54": um fato do real sobre o lugar escolhido, quando existe
    function fatoReal(n, a, nivel) {
      if (!a) return "";
      var lugar = lugarDe(a.destino[0], a.destino[1], nivel);
      if (!lugar) return "";
      var achada = cur.nades.filter(function (q) { var f = fimDe(q); return q !== n && q.k === n.k && lugarDe(f[0], f[1], nivelDe(q)) === lugar; }).sort(function (x, y) { return x.f0 - y.f0; })[0];
      return achada ? N.formata(TX.fato_real, { nome: achada.by, tipo: tipoDe(n.k), lugar: lugar, relogio: N.relogioNo(achada.f0) }) : "";
    }
    function seleciona(n) {
      hover = null; sel = n; escolha = trocaDe(n) ? trocaDe(n).alt : null;
      render(); draw();
    }
    function aplica() {
      if (!sel || !escolha) return;
      trocas = trocas.filter(function (t) { return t.n !== sel; });
      var feita = sel;
      trocas.push({ n: sel, alt: escolha });
      sel = null; escolha = null;
      N.atualizaBanco();     // liga o ▶, refaz "O que mudou"
      draw();
      focoNaLista(feita);
    }

    /* ---------- as granadas trocadas na sua versão: desenhadas como as do real, no instante certo ---------- */
    function recalcula() {
      var v = reescrever.virtuais;
      v.nades = []; v.smokes = []; v.fires = []; v.pops = [];
      if (!reescrever.ativo || !reescrever.sua) return;
      efetivas().forEach(function (t) {
        var n = t.n, a = t.alt, fl = Math.max(1, Math.round(a.voo_s * R.sample_hz)), o = origemDe(n), d = a.destino, L = Math.max(1, Math.ceil(fl)), xs = [], ys = [], cai = queda(n, a);
        for (var i = 0; i <= L; i++) { var f = Math.min(1, i / fl); xs.push(o[0] + (d[0] - o[0]) * f); ys.push(o[1] + (d[1] - o[1]) * f); }
        v.nades.push({ k: n.k, by: n.by, f0: n.f0, x: xs, y: ys, _virtual: true });
        if (n.k === "smoke") v.smokes.push({ f0: cai, f1: cai + TX.smoke_s * R.sample_hz, x: d[0], y: d[1], by: n.by, _virtual: true });
        else if (n.k === "molotov") v.fires.push({ f0: cai, f1: cai + a.efeito_s * R.sample_hz, x: d[0], y: d[1], by: n.by, _virtual: true });
        else v.pops.push({ k: n.k, f: cai, x: d[0], y: d[1], by: n.by, hit: [], dmg: 0, _virtual: true });
      });
    }

    /* ---------- "O que mudou" ---------- */
    function frases() {
      return trocas.map(function (t) {
        var n = t.n, a = t.alt, nivel = nivelDe(n), o = fimDe(n), real = lugarDe(o[0], o[1], nivel), nova = lugarDe(a.destino[0], a.destino[1], nivel);
        var base = { tipo: tipoDe(n.k), nome: n.by, relogio: N.relogioNo(n.f0), seg: segundos(a.voo_s), chega: N.relogioNo(queda(n, a)),
                     real: real ? N.formata(TX.em_lugar, { lugar: real }) : TX.no_ponto_real, nova: nova ? N.formata(TX.em_lugar, { lugar: nova }) : TX.no_ponto_escolhido };
        if (N.editada(n.by)) return N.formata(TX.mudou_troca_parada, base);
        return N.formata(queda(n, a) > cur.frames - 1 ? TX.mudou_troca_nao_cai : TX.mudou_troca, base);
      });
    }

    /* ---------- o mapa: as granadas que dá para escolher, a escolhida e as trocas (antes de tocar) ---------- */
    function trajeto(c, n) {
      c.moveTo(mx(n.x[0]), my(n.y[0]));
      for (var j = 1; j < n.x.length; j++) c.lineTo(mx(n.x[j]), my(n.y[j]));
    }
    function desenha(c) {
      if (reescrever.sua) return;
      var SMOKE_R = MapCore.RAIO_SMOKE_UNIDADES * RAD.scale_px_per_unit, FIRE_R = MapCore.RAIO_MOLOTOV_UNIDADES * RAD.scale_px_per_unit;
      c.save();
      c.lineCap = "round";
      if (reescrever.ferramenta === "granada") {
        candidatas().forEach(function (n) {
          if (n === sel || trocaDe(n)) return;
          var u = n.x.length - 1, cor = NADE_COLOR[n.k] || CM.apagado;
          if (n === hover) N.tracejado(c, function () { trajeto(c, n); }, cor, 1.4);       // o traço só aparece na que está sob o mouse ou o foco (e na selecionada)
          c.beginPath(); c.arc(mx(n.x[u]), my(n.y[u]), n === hover ? 7 : 5, 0, Math.PI * 2);       // as outras: um ponto pequeno no lugar onde cai
          c.fillStyle = cor; c.fill(); c.strokeStyle = C.contorno; c.lineWidth = 1.6; c.stroke();
        });
      }
      var mostrar = trocas.map(function (t) { return t.n; });
      if (sel && mostrar.indexOf(sel) < 0) mostrar.push(sel);
      mostrar.forEach(function (n) {
        var u = n.x.length - 1, cor = NADE_COLOR[n.k] || CM.apagado, tr = trocaDe(n), a = N.editada(n.by) ? null : ((sel === n ? escolha : null) || (tr && tr.alt));
        var r = n.k === "smoke" ? SMOKE_R : n.k === "molotov" ? FIRE_R : 9;
        N.tracejado(c, function () { trajeto(c, n); }, cor, 1.4);                                                   // a original, em fantasma
        N.tracejado(c, function () { c.arc(mx(n.x[u]), my(n.y[u]), r, 0, Math.PI * 2); }, cor, 2);
        if (a) {
          var dx = mx(a.destino[0]), dy = my(a.destino[1]), o0 = origemDe(n);
          c.save();
          c.setLineDash([2, 4]);
          [[C.contorno, 3.6], [cor, 1.6]].forEach(function (par) { c.strokeStyle = par[0]; c.lineWidth = par[1]; c.beginPath(); c.moveTo(mx(o0[0]), my(o0[1])); c.lineTo(dx, dy); c.stroke(); });
          c.restore();
          if (n.k === "smoke" || n.k === "molotov") MapCore.desenhaArea(c, n.k, dx, dy, r);
          else { c.beginPath(); c.arc(dx, dy, r, 0, Math.PI * 2); c.strokeStyle = C.contorno; c.lineWidth = 4.4; c.stroke(); c.strokeStyle = cor; c.lineWidth = 2.4; c.stroke(); }
          MapCore.rotulo(N.formata(TX.cai, { relogio: N.relogioNo(queda(n, a)) }), dx, dy, { cor: CM.tinta, prioridade: 4, dy: 18 });
        }
        if (sel === n) {      // a origem ganha o anel tracejado branco
          var o = origemDe(n);
          c.setLineDash([3, 3]);
          [[C.contorno, 4.4], [CM.tinta, 2]].forEach(function (par) { c.strokeStyle = par[0]; c.lineWidth = par[1]; c.beginPath(); c.arc(mx(o[0]), my(o[1]), 10, 0, Math.PI * 2); c.stroke(); });
        }
      });
      c.restore();
    }

    // a granada cujo ponto de queda está mais perto do ponteiro (até `alvo` px de tela)
    function sobOPonteiro(e, alvo) {
      var m = N.matrizDaVista(), q = N.doPonteiro(e), melhor = null, dist = alvo;
      candidatas().forEach(function (n) {
        var u = n.x.length - 1, pt = new DOMPoint(mx(n.x[u]), my(n.y[u])).matrixTransform(m), d = Math.hypot(pt.x - q.cx, pt.y - q.cy) / q.k;
        if (d <= dist) { dist = d; melhor = n; }
      });
      return melhor;
    }
    function defineHover(n) { if (hover !== n) { hover = n; draw(); } }
    mapwrap.addEventListener("pointermove", function (e) {
      if (!reescrever.ativo || reescrever.sua || reescrever.ferramenta !== "granada" || e.buttons) return;
      defineHover(sobOPonteiro(e, 18));
    });
    mapwrap.addEventListener("pointerleave", function () { defineHover(null); });
    // clicar numa granada do real no mapa (a ferramenta Granada): a que passa mais perto do ponto, até o alvo de 24 px
    mapwrap.addEventListener("pointerdown", function (e) {
      if (!reescrever.ativo || reescrever.sua || reescrever.ferramenta !== "granada" || bib.estado !== "pronta" || (e.button && e.button > 0)) return;
      var melhor = sobOPonteiro(e, 24);
      if (!melhor) return;
      e.preventDefault(); e.stopPropagation();
      seleciona(melhor);
    }, true);
  })();
