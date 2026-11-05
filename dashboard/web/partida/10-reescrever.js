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
    reescrever.sua = false;        // a sua versão está tocando (ou pausada depois de tocar): nada é editável (decisão 35)
    reescrever.fantasma = true;    // o real, onde difere
    reescrever.instante = 0;

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

    // A peça editada anda do ponto do real em t0 até o ponto novo na velocidade medida da função dela (a mesma conta da prancheta, decisão 43) e
    // fica lá: não há dado depois disso. Antes de tocar, mostra o ponto novo (é o que se arrasta).
    function velocidadeDe(nome) {
      var it = pecas.filter(function (q) { return q.p.name === nome; })[0], w = it ? it.p.w[t0] : -1;
      return TX.velocidade[w >= 0 && /awp/i.test(cur.weapons[w]) ? "AWP" : "rifle"];
    }
    function trecho(nome, quadro) {
      var o = origem[nome], e = edicoes[nome], v = velocidadeDe(nome), d = Math.hypot(e.x - o.x, e.y - o.y), dur = d / v;
      var el = Math.max(0, (quadro - t0) / R.sample_hz), f = dur > 0 ? Math.min(1, el / dur) : 1;
      return { x: o.x + (e.x - o.x) * f, y: o.y + (e.y - o.y) * f, dur: dur, d: d, f: f };
    }
    reescrever.posicaoEditada = function (nome) {
      var e = edicoes[nome];
      if (!e) return null;
      if (!reescrever.sua) return [e.x, e.y];
      if (!editada(nome)) return null;
      var q = trecho(nome, pos);
      return [q.x, q.y];
    };
    reescrever.yawEditada = function (nome) {
      if (!reescrever.sua || !editada(nome)) return null;
      var o = origem[nome], e = edicoes[nome];
      return Math.atan2(e.y - o.y, e.x - o.x) * 180 / Math.PI;
    };
    // quem foi editado não morre na sua versão: a morte do real só aparece no fantasma
    reescrever.semAMorte = function (e) { return e.type === "kill" && e.f > t0 && editada(e.victim); };
    // granada lançada DEPOIS do instante por quem foi editado dependia da posição dele no real: fica só no fantasma (design §9)
    // a granada que gerou o item (a própria granada, ou o arremesso que fez a zona/estouro): a ligação gravada pelo export, ou o tipo e o ponto final
    function geradoraDe(it) {
      if (it._ger !== undefined) return it._ger;
      var ger = null;
      if (it.x !== undefined && it.x.length !== undefined) ger = it;
      else {
        var f = it.f0 !== undefined ? it.f0 : it.f, tipo = it.k || (cur.smokes.indexOf(it) >= 0 ? "smoke" : "molotov"), ligado = it.l ? JSON.stringify(it.l) : null, achado = null;
        cur.nades.forEach(function (n) {
          var u = n.x.length - 1;
          if (n.by !== it.by || n.f0 > f + 1) return;
          var bate = ligado && n.l ? JSON.stringify(n.l) === ligado
            : (tipo === "molotov" ? n.k !== "smoke" && n.k !== "flash" && n.k !== "he" : n.k === tipo) && Math.hypot(n.x[u] - it.x, n.y[u] - it.y) <= 60;
          if (bate && (achado === null || n.f0 > achado.f0)) achado = n;
        });
        ger = achado;
      }
      it._ger = ger;
      return ger;
    }
    function lancouEm(it) {
      var g = geradoraDe(it);
      return g ? g.f0 : (it.x !== undefined && it.x.length !== undefined ? it.f0 : -Infinity);   // sem arremesso casado não dá para afirmar que dependia da peça editada: vale nos dois
    }
    reescrever.geradoraDe = geradoraDe;
    reescrever.soNoReal = function (it) {
      if (it._virtual) return false;
      if (it.by && editada(it.by) && lancouEm(it) > t0) return true;
      return !!(reescrever.granada && reescrever.granada.trocada(geradoraDe(it)));      // a granada trocada some da sua versão (fica só no fantasma)
    };
    reescrever.podeTocar = function () { return algumaMudanca(); };
    reescrever.esmaecida = function (nome) {     // depois da morte do real a peça editada fica esmaecida (o ✕ do fantasma mostra onde ele morreu)
      var it = pecas.filter(function (q) { return q.p.name === nome; })[0];
      return !!(reescrever.sua && it && !it.p.alive[Math.floor(pos)]);
    };
    reescrever.preparaTocar = function () {
      if (!algumaMudanca()) return false;
      if (!reescrever.sua || pos >= cur.frames - 1) { pos = t0; frame = t0; scrubEl.value = t0; }
      reescrever.sua = true;
      atualizaBanco();
      return true;
    };

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
      c.restore();
      Object.keys(edicoes).forEach(function (nome) {
        if (!editada(nome)) return;
        var e = edicoes[nome], q = trecho(nome, pos);
        if ((!reescrever.sua || q.f < 1) && t0 + q.dur * R.sample_hz <= cur.frames - 1) MapCore.rotulo(formata(TX.chega, { relogio: relogioNo(t0 + q.dur * R.sample_hz) }), mx(e.x), my(e.y),
          { cor: CM.tinta, prioridade: 4, dy: 18 });
      });
      if (reescrever.sua && reescrever.fantasma) desenhaFantasmas(c);
      if (reescrever.granada) reescrever.granada.desenha(c);
      c.save();
      if (reescrever.sel && origem[reescrever.sel]) {
        var q = edicoes[reescrever.sel] || origem[reescrever.sel];
        c.beginPath(); c.arc(mx(q.x), my(q.y), 15, 0, Math.PI * 2);
        c.strokeStyle = contorno; c.lineWidth = 4.4; c.stroke();
        c.strokeStyle = tinta; c.lineWidth = 2; c.stroke();
      }
      c.restore();
    };

    // o real, onde difere: a peça do real em anel tracejado (✕ se ela morreu), ligada por uma linha pontilhada à peça da sua versão; e as granadas
    // que só existem no real, tracejadas (design §4.4). Só desenha o que difere: quem não foi editado anda igual nos dois.
    function tracejado(c, fn, cor, larg) {
      c.setLineDash([5, 4]);
      [[CM.tinta, larg + 3], [C.contorno, larg + 1.8], [cor, larg]].forEach(function (par) { c.strokeStyle = par[0]; c.lineWidth = par[1]; c.beginPath(); fn(); c.stroke(); });
      c.setLineDash([]);
    }
    // quem tem fantasma agora: o real onde difere da sua versão (MOVIDA unidades ou mais)
    function fantasmasAgora() {
      var i0 = Math.floor(pos), i1 = Math.min(cur.frames - 1, i0 + 1), tt = pos - i0, lv = activeLevel(i0), out = [];
      pecas.forEach(function (it) {
        var p = it.p;
        if (!it.vivo || !editada(p.name) || (p.lv && p.lv[t0] !== lv)) return;
        var vivo = !!p.alive[i0], sp = vivo && p.alive[i1] ? smoothPos(p, i0, i1, tt) : [p.x[i0], p.y[i0]], q = trecho(p.name, pos);
        if (Math.hypot(sp[0] - q.x, sp[1] - q.y) < MOVIDA) return;
        out.push({ it: it, vivo: vivo, sp: sp, q: q, i0: i0 });
      });
      return out;
    }
    function desenhaFantasmas(c) {
      fantasmasAgora().forEach(function (g) {
        var p = g.it.p, vivo = g.vivo, sp = g.sp, q = g.q, i0 = g.i0;
        var cor = p.side === "ct" ? CM.ct : CM.tr;
        c.save();
        c.lineCap = "round";
        c.setLineDash([2, 4]);
        [[C.contorno, 3.4], [CM.tinta2 || CM.tinta, 1.4]].forEach(function (par) {
          c.strokeStyle = par[0]; c.lineWidth = par[1]; c.beginPath(); c.moveTo(mx(sp[0]), my(sp[1])); c.lineTo(mx(q.x), my(q.y)); c.stroke();
        });
        c.restore();
        MapCore.desenhaJogador(c, mx(sp[0]), my(sp[1]), { cor: cor, estado: vivo ? "fantasma" : "morto", escala: vivo ? 1.8 : reescrever.escala, raio: 12,
          yaw: vivo && p.d ? p.d[i0] : null, hp: p.hp[i0] });
      });
      var SMOKE_R = MapCore.RAIO_SMOKE_UNIDADES * RAD.scale_px_per_unit, FIRE_R = MapCore.RAIO_MOLOTOV_UNIDADES * RAD.scale_px_per_unit;
      c.save();
      c.lineCap = "round";
      [[cur.smokes, SMOKE_R, "smoke"], [cur.fires, FIRE_R, "molotov"]].forEach(function (g) {
        g[0].forEach(function (z) {
          if (pos < z.f0 || pos > z.f1 || !reescrever.soNoReal(z)) return;
          tracejado(c, function () { c.arc(mx(z.x), my(z.y), g[1], 0, Math.PI * 2); }, NADE_COLOR[g[2]] || CM.apagado, 2);
        });
      });
      cur.nades.forEach(function (n) {
        var k = pos - n.f0, u = n.x.length - 1;
        if (k < 0 || k > u || !reescrever.soNoReal(n)) return;
        var ka = Math.floor(k), kb = Math.min(u, ka + 1), gx = mx(lerp(n.x[ka], n.x[kb], k - ka)), gy = my(lerp(n.y[ka], n.y[kb], k - ka));
        tracejado(c, function () { c.moveTo(mx(n.x[0]), my(n.y[0])); for (var j = 1; j <= ka; j++) c.lineTo(mx(n.x[j]), my(n.y[j])); c.lineTo(gx, gy); }, NADE_COLOR[n.k] || CM.apagado, 1.2);
        tracejado(c, function () { c.arc(gx, gy, 6, 0, Math.PI * 2); }, NADE_COLOR[n.k] || CM.apagado, 2);
      });
      (cur.pops || []).forEach(function (q) {
        var age = pos - q.f;
        if (age < 0 || age > POP_FRAMES || !reescrever.soNoReal(q)) return;
        tracejado(c, function () { c.arc(mx(q.x), my(q.y), 8 + 18 * age / POP_FRAMES, 0, Math.PI * 2); }, NADE_COLOR[q.k] || CM.apagado, 2);
      });
      c.restore();
    }

    function editada(nome) {
      var o = origem[nome], e = edicoes[nome];
      return !!(o && e && Math.hypot(e.x - o.x, e.y - o.y) >= MOVIDA);
    }
    function algumaEditada() { return Object.keys(edicoes).some(editada); }
    function algumaMudanca() { return algumaEditada() || !!(reescrever.granada && reescrever.granada.temTroca()); }   // peça movida ou granada trocada

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
      if (!reescrever.ativo || reescrever.sua || reescrever.ferramenta === "granada" || (e.button && e.button > 0)) return;
      var nome = acha(e);
      if (!nome) return;
      e.preventDefault(); e.stopPropagation();       // a peça vem antes do desenho e do arrastar do mapa
      seleciona(nome);
      arrasto = { nome: nome, id: e.pointerId };
      try { mapwrap.setPointerCapture(e.pointerId); } catch (x) { /* sem captura: o movimento segue pelo mapa */ }
    }, true);
    mapwrap.addEventListener("pointermove", function (e) {
      if (!arrasto || reescrever.sua || e.pointerId !== arrasto.id) return;
      e.preventDefault(); e.stopPropagation();
      var q = doPonteiro(e);
      var cx = Math.min(cv.width, Math.max(0, q.cx)), cy = Math.min(cv.height, Math.max(0, q.cy));   // a peça fica dentro do mapa
      var g = aGameUnits(cx, cy);
      edicoes[arrasto.nome] = { x: g.x, y: g.y };
      atualizaBanco(true);     // durante o arrasto o texto de "O que mudou" não é refeito (leitor de tela)
      draw();
    }, true);
    function soltou(e) {
      if (!arrasto || e.pointerId !== arrasto.id) return;
      e.stopPropagation();
      if (!editada(arrasto.nome)) delete edicoes[arrasto.nome];   // movida por menos de 8 u não conta: volta ao real já ao soltar
      arrasto = null;
      atualizaBanco();
      draw();
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
          var tag = novo("span", "pr-tag", TX.editado); tag.title = TX.editado;   // um ponto na linha do nome: aparece sem mudar a altura do cartão (CLS 0) nem cortar o nome
          topo.appendChild(tag);
          topo.appendChild(novo("span", "pr-hp", it.vivo ? String(it.p.hp[t0]) : "0"));
          b.appendChild(topo);
          var w = it.vivo ? it.p.w[t0] : -1;
          var pi = it.vivo && it.p.p ? it.p.p[t0] : -1;
          var meio = it.vivo ? [(w >= 0 ? cur.weapons[w] : ""), (pi >= 0 ? cur.places[pi] : "")].filter(Boolean).join(" · ")
            : formata(TX.morto, { relogio: relogioNo(it.morreuEm), inicio: relogioNo(t0) });
          b.appendChild(novo("span", "pr-meio", meio));
          if (it.vivo) b.addEventListener("click", function () { seleciona(it.p.name); });
          else b.setAttribute("aria-disabled", "true");
          host.appendChild(b);
        });
      });
    }
    function atualizaBanco(semTexto) {
      Array.prototype.forEach.call(hosts.ct.querySelectorAll(".peca-rw"), function (b) {
        b.setAttribute("aria-pressed", String(b.dataset.nome === reescrever.sel));
        b.classList.toggle("editada", editada(b.dataset.nome));
      });
      var voltar = document.getElementById("rw-voltar");
      if (voltar) voltar.disabled = !algumaMudanca();
      var editar = document.getElementById("rw-editar");
      if (editar) editar.disabled = !reescrever.sua;
      var dica = document.getElementById("rw-dica");
      if (dica) dica.textContent = reescrever.sua ? TX.vendo : TX.dica;
      playBtn.disabled = !algumaMudanca();
      playBtn.title = algumaMudanca() ? "" : TX.toca_desligado;
      if (reescrever.granada) reescrever.granada.atualiza();
      if (!semTexto) atualizaMudou();
      var a = document.activeElement;       // um botão que acabou de se desligar não pode prender o foco
      if (a && a.disabled) { var alvo = playBtn.disabled ? hosts.ct.querySelector(".peca-rw:not([aria-disabled])") : playBtn; if (alvo) alvo.focus({ preventScroll: true }); }
    }
    /* "O que mudou": o texto da diferença (design §3 e D3), do dado e de nada mais */
    function atualizaMudou() {
      var host = document.getElementById("rw-mudou");
      if (!host) return;
      var itens = [];
      pecas.forEach(function (it) {
        var nome = it.p.name;
        if (!it.vivo || !editada(nome)) return;
        var q = trecho(nome, t0 + 1e9), lugar = it.p.p ? cur.places[it.p.p[t0]] : "";
        var chega = t0 + q.dur * R.sample_hz, base = { nome: nome, de: lugar, relogio: relogioNo(t0), chega: relogioNo(chega),
          seg: (Math.round(q.dur * 10) / 10).toString().replace(".", ",") };
        itens.push(formata(chega > cur.frames - 1 ? TX.mudou_nao_chega : (lugar ? TX.mudou_move : TX.mudou_move_sem_lugar), base));
        cur.events.forEach(function (e) {
          if (e.type !== "kill" || e.f <= t0) return;
          if (e.victim === nome) itens.push(formata(e.attacker ? TX.mudou_morreu : TX.mudou_morreu_sem_matador, { nome: nome, matador: e.attacker, relogio: relogioNo(e.f) }));
          else if (e.attacker === nome && !editada(e.victim)) itens.push(formata(TX.mudou_d3, { nome: nome, vitima: e.victim, relogio: relogioNo(e.f) }));
        });
        cur.events.forEach(function (e) {
          if (e.player !== nome || e.f <= t0) return;
          if (e.type === "plant") itens.push(formata(TX.mudou_plantou, { nome: nome, relogio: relogioNo(e.f) }));
          if (e.type === "defuse") itens.push(formata(TX.mudou_desarmou, { nome: nome, relogio: relogioNo(e.f) }));
        });
        (cur.pops || []).forEach(function (q) {
          if (q.k !== "flash" || q.by !== nome || q.f <= t0) return;
          var n = (q.hit || []).filter(function (v) { return v.e && v.s >= R.effective_blind_s; }).length;
          if (n) itens.push(formata(TX.mudou_cegou, { nome: nome, relogio: relogioNo(q.f), n: formata(n === 1 ? TX.cegos.um : TX.cegos.varios, { n: n }) }));
        });
        cur.nades.forEach(function (n) {
          if (n.by === nome && n.f0 > t0) itens.push(formata(TX.mudou_granada, { tipo: TX.granadas[n.k] || n.k, nome: nome, relogio: relogioNo(n.f0) }));
        });
      });
      host.textContent = "";
      if (reescrever.granada) itens = itens.concat(reescrever.granada.frases());
      if (!itens.length) { host.appendChild(novo("li", "rw-nada", TX.mudou_nada)); return; }
      itens.forEach(function (t) { host.appendChild(novo("li", null, t)); });
    }
    function montaPainel() {
      var host = hosts.t;
      host.className = "card squad painel-rw";
      host.textContent = "";
      host.appendChild(novo("h4", null, TX.titulo));
      var fixa = novo("p", "rw-fixa"); fixa.appendChild(novo("b", null, TX.fixa_forte)); fixa.appendChild(document.createTextNode(" " + TX.fixa_resto));
      host.appendChild(fixa);
      host.appendChild(novo("p", "rw-comeca", formata(TX.comeca_em, { relogio: relogioNo(t0) })));
      var dica = novo("p", "rw-dica", TX.dica); dica.id = "rw-dica"; dica.setAttribute("role", "status");
      host.appendChild(dica);
      if (reescrever.granada) reescrever.granada.monta(host);
      var fant = botao("", "rw-btn", function () {
        reescrever.fantasma = !reescrever.fantasma;
        textoFantasma(fant); draw();
      });
      fant.id = "rw-fantasma";
      textoFantasma(fant);
      host.appendChild(fant);
      host.appendChild(novo("p", "rw-leg", TX.fantasma_legenda));
      var editar = botao(TX.editar_de_novo, "rw-btn", function () { voltaAEditar(); });
      editar.id = "rw-editar"; editar.disabled = true;
      host.appendChild(editar);
      var voltar = botao(TX.voltar, "rw-btn", function () { edicoes = {}; if (reescrever.granada) reescrever.granada.limpa(); voltaAEditar(); });
      voltar.id = "rw-voltar"; voltar.disabled = true;
      host.appendChild(voltar);
      host.appendChild(novo("h4", null, TX.mudou_titulo));
      var mudou = novo("ul", "rw-mudou"); mudou.id = "rw-mudou"; mudou.setAttribute("aria-live", "polite");
      host.appendChild(mudou);
    }
    function textoFantasma(b) {
      b.textContent = TX.fantasma + ": " + (reescrever.fantasma ? TX.fantasma_ligado : TX.fantasma_desligado);
      b.setAttribute("aria-pressed", String(reescrever.fantasma));
    }
    // volta ao instante e ao editor (a sua versão para de tocar)
    function voltaAEditar() {
      setPlaying(false);
      reescrever.sua = false;
      pos = t0; frame = t0; scrubEl.value = t0;
      atualizaBanco(); draw();
    }

    /* ---------- o cabeçalho do palco e o transporte ---------- */
    var res = document.getElementById("rh-res"), resSalvo = "", resTitulo = "";
    function montaAcoes() {
      acoes.textContent = "";
      if (reescrever.ativo) {
        resSalvo = res.textContent; resTitulo = res.title; res.textContent = TX.curta; res.title = TX.curta;   // no modo, o resumo do round cede lugar à frase curta
        acoes.appendChild(novo("span", "rw-pilula", "● " + TX.pilula));
        var s = botao(TX.sair, "rw-btn", function () { pedeSair(); });
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
      if (reescrever.ativo) playBtn.setAttribute("aria-label", playing ? TX.pausa : TX.toca);
    };

    /* ---------- entrar e sair ---------- */
    reescrever.entra = function () {
      if (reescrever.ativo || !cur || document.querySelector("[data-panel='replay']").hidden) return;
      setPlaying(false);
      t0 = Math.floor(pos); pos = t0; frame = t0;     // o instante é o quadro gravado imediatamente anterior (o mesmo do `instante()`)
      scrubEl.value = t0;
      edicoes = {}; origem = {}; arrasto = null; reescrever.sel = null; reescrever.sua = false; reescrever.instante = t0;
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
      scrubEl.disabled = true; speedBtn.disabled = false;
      if (reescrever.granada) reescrever.granada.entra();
      montaBanco(); montaPainel(); montaAcoes(); atualizaBanco();
      draw();
      var primeira = hosts.ct.querySelector(".peca-rw:not([aria-disabled])");
      if (primeira) primeira.focus({ preventScroll: true });
    };
    reescrever.sai = function (semFoco) {
      if (!reescrever.ativo) return;
      if (dlg && dlg.open) dlg.close();
      setPlaying(false);
      if (reescrever.granada) reescrever.granada.sai();
      reescrever.ativo = false; reescrever.sua = false; reescrever.sel = null; arrasto = null; edicoes = {}; origem = {}; pecas = [];
      palco.setAttribute("data-tema", "escuro");
      hosts.ct.removeAttribute("data-tema"); hosts.t.removeAttribute("data-tema");
      stage.classList.remove("reescrevendo");
      if (rotulos) { hosts.ct.setAttribute("aria-label", rotulos.ct); hosts.t.setAttribute("aria-label", rotulos.t); rotulos = null; }
      playBtn.disabled = false; playBtn.removeAttribute("title"); playBtn.setAttribute("aria-label", "Reproduzir");
      scrubEl.disabled = false; speedBtn.disabled = false;
      buildSquads(); montaAcoes();
      draw();
      if (!semFoco) { var e = document.getElementById("rw-entrar"); if (e) e.focus({ preventScroll: true }); }
    };
    // Sair com edições pede confirmação (o <dialog> prende o foco; o Esc dele é "Continuar editando"); sem edição sai direto
    var dlg = null;
    function dialogo() {
      if (dlg) return dlg;
      dlg = novo("dialog", "rw-dialogo"); dlg.setAttribute("data-tema", "violeta"); dlg.setAttribute("aria-labelledby", "rw-dlg-t");
      var t = novo("h3", null, TX.descartar_titulo); t.id = "rw-dlg-t";
      var linhas = novo("div", "rw-dlg-linhas");
      var cont = botao(TX.continuar, "rw-btn prim", function () { depoisDeDescartar = null; dlg.close(); });
      cont.autofocus = true; cont.id = "rw-continuar";
      var desc = botao(TX.descartar, "rw-btn", function () {
        var seguir = depoisDeDescartar; depoisDeDescartar = null;
        dlg.close(); reescrever.sai(!!seguir);
        if (seguir) seguir();
      });
      desc.id = "rw-descartar";
      linhas.appendChild(cont); linhas.appendChild(desc);
      dlg.addEventListener("keydown", function (e) {      // o Tab dá a volta dentro do aviso (a página atrás fica inerte)
        if (e.key !== "Tab") return;
        var alvo = e.shiftKey ? cont : desc, outro = e.shiftKey ? desc : cont;
        if (document.activeElement === alvo) { e.preventDefault(); outro.focus(); }
      });
      dlg.appendChild(t); dlg.appendChild(novo("p", null, TX.descartar_texto)); dlg.appendChild(linhas);
      dlg.addEventListener("close", function () { depoisDeDescartar = null; });   // Esc ou Continuar: nada a seguir
      document.body.appendChild(dlg);
      return dlg;
    }
    var depoisDeDescartar = null;      // o que fazer se descartar (trocar de round ou de aba)
    reescrever.pedeDescartar = function (seguir) {     // true: abriu o aviso (quem chamou espera); false: sem edição, pode seguir
      if (!reescrever.ativo || !algumaMudanca()) return false;
      depoisDeDescartar = seguir;
      pedeSair();
      return true;
    };
    function pedeSair() {
      if (!algumaMudanca()) { reescrever.sai(); return; }
      setPlaying(false);       // a sua versão não segue tocando por trás do aviso
      var d = dialogo();
      if (!d.open) d.showModal();
    }
    // o Esc que fecha o "?" dos atalhos (ou outra caixa aberta) não deve descartar as edições: a captura vê o "?" ANTES de ele se fechar
    var escJaTinhaDono = false;
    document.addEventListener("keydown", function (e) {
      var pop = document.getElementById("atalhos");
      escJaTinhaDono = e.key === "Escape" && (!!(pop && !pop.hidden) || !!(dlg && dlg.open));
    }, true);
    document.addEventListener("keydown", function (e) {
      if (e.key !== "Escape" || !reescrever.ativo || e.defaultPrevented || escJaTinhaDono) return;
      if (document.querySelector("[data-panel='replay']").hidden || (e.target.closest && e.target.closest("input, select, textarea"))) return;
      e.preventDefault(); pedeSair();
    });

    // o estado para os testes (como `__medicaoRotulos` e `__marcasDeBorda`): quem está editável e onde cada peça está
    window.__reescrever = function () {
      return {
        ativo: reescrever.ativo, sua: reescrever.sua, fantasma: reescrever.fantasma, instante: t0, quadro: pos,
        fantasmas: reescrever.ativo && reescrever.sua ? fantasmasAgora().map(function (g) { return { nome: g.it.p.name, vivo: g.vivo, x: g.sp[0], y: g.sp[1] }; }) : [],
        esmaecidas: reescrever.ativo ? pecas.filter(function (it) { return editada(it.p.name) && reescrever.esmaecida(it.p.name); }).map(function (it) { return it.p.name; }) : [],
        soNoReal: reescrever.ativo ? [].concat(cur.nades, cur.smokes, cur.fires, cur.pops || []).filter(function (it) { return reescrever.soNoReal(it); }).length : 0, relogio: relogioNo(t0), selecionada: reescrever.sel,
        trocas: reescrever.granada ? reescrever.granada.estado() : null,
        pecas: pecas.map(function (it) {
          var e = edicoes[it.p.name], o = origem[it.p.name];
          var ag = e && editada(it.p.name) ? reescrever.posicaoEditada(it.p.name) : null;
          return { nome: it.p.name, lado: it.p.side, editavel: it.vivo, editada: editada(it.p.name), x: e ? e.x : (o ? o.x : null), y: e ? e.y : (o ? o.y : null),
                   x0: o ? o.x : null, y0: o ? o.y : null, agora: ag, velocidade: it.vivo ? velocidadeDe(it.p.name) : null };
        })
      };
    };

    // o que a granada (11-reescrever-granada.js) precisa do núcleo
    reescrever.nucleo = {
      t0: function () { return t0; }, pecas: function () { return pecas; }, editada: editada, relogioNo: relogioNo, formata: formata, novo: novo, botao: botao,
      atualizaBanco: atualizaBanco, algumaMudanca: algumaMudanca, doPonteiro: doPonteiro, aGameUnits: aGameUnits, matrizDaVista: matrizDaVista, tracejado: tracejado
    };

    montaAcoes();
    reescrever.aoQuadro();
  })();
