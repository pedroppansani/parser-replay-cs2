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
    var edicoes = {};         // nome -> {x, y} em unidades de jogo: a ÚLTIMA parada da trilha (é o que se arrasta e o que o banco mostra parado)
    var trilhas = {};         // nome -> [{f, x, y}]: as paradas da peça editada; `f` = o quadro em que ela parte (>= t0). Arrastar é UMA parada em t0 (CR1b)
    var segs = {};            // nome -> [{f0, ax, ay, bx, by, d, dur, f1}]: o que as paradas viram (a conta da trilha, refeita quando ela muda)
    var origem = {};          // nome -> {x, y} no instante (o real)
    var pecas = [];           // {p, vivo, morreuEm}
    var arrasto = null;
    var t0 = 0;
    var rotulos = null;       // os aria-label dos elencos, de volta ao sair
    var desfazer = [];        // a pilha do "Desfazer" (CR2): um item por comando aplicado = {foto: nome -> {trilha, pc} de ANTES, linha: o que o comando disse}
    var porComando = {};      // nome -> {f: true}: as paradas que vieram de um comando (o "O que mudou" as diz pela linha do comando, não pelo trecho)

    reescrever.escala = 1.25;
    reescrever.sel = null;
    reescrever.sua = false;        // a sua versão está tocando (ou pausada depois de tocar): nada é editável (decisão 35)
    reescrever.fantasma = true;    // o real, onde difere
    reescrever.ver = "sua";        // celular (R6b): o que o mapa mostra, "real" ou "sua" (no computador o real vem como fantasma por cima)
    var VAZIO = { nades: [], smokes: [], fires: [], pops: [] };
    function vendoReal() { return reescrever.ativo && reescrever.ver === "real" && !MODO_PALCO.matches; }
    reescrever.vv = function () { return vendoReal() ? VAZIO : reescrever.virtuais; };
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

    // A peça editada tem uma TRILHA (CR1b): até o quadro em que ela parte ela segue o caminho REAL (o dado existe); dali anda em linha reta, na velocidade medida da
    // função dela (a mesma conta da prancheta, decisão 43), até cada parada e fica na última (não há dado depois). Uma parada que parte no meio da anterior CORTA a
    // anterior: o caminho novo segue de onde a peça estava (como a prancheta toca). Arrastar uma peça é o caso de UMA parada, no instante (`f` = t0): a conta é a de
    // antes. Antes de tocar, mostra a última parada (é o que se arrasta).
    function velocidadeDe(nome) {
      var it = pecas.filter(function (q) { return q.p.name === nome; })[0], w = it ? it.p.w[t0] : -1;
      return TX.velocidade[w >= 0 && /awp/i.test(cur.weapons[w]) ? "AWP" : "rifle"];
    }
    function realEm(nome, f) {      // onde o real está no quadro f (fracionário): a mesma conta com que o replay desenha
      var p = pecas.filter(function (q) { return q.p.name === nome; })[0].p, i0 = Math.floor(f), i1 = Math.min(cur.frames - 1, i0 + 1), tt = f - i0;
      return tt === 0 || !p.alive[i0] || !p.alive[i1] ? [p.x[i0], p.y[i0]] : smoothPos(p, i0, i1, tt);
    }
    function naReta(sg, quadro) {      // a peça no trecho `sg` no quadro dado (>= a partida dele): na reta, e parada na chegada
      var el = Math.max(0, (quadro - sg.f0) / R.sample_hz), f = sg.dur > 0 ? Math.min(1, el / sg.dur) : 1;
      return { x: sg.ax + (sg.bx - sg.ax) * f, y: sg.ay + (sg.by - sg.ay) * f, f: f };
    }
    function recalcula(nome) {
      var v = velocidadeDe(nome), lista = [];
      trilhas[nome].forEach(function (pa, k) {
        var a = k === 0 ? realEm(nome, pa.f) : naReta(lista[k - 1], pa.f), ax = k === 0 ? a[0] : a.x, ay = k === 0 ? a[1] : a.y;
        var d = Math.hypot(pa.x - ax, pa.y - ay), dur = d / v;
        lista.push({ f0: pa.f, ax: ax, ay: ay, bx: pa.x, by: pa.y, d: d, dur: dur, f1: pa.f + dur * R.sample_hz });
      });
      segs[nome] = lista;
    }
    function poeTrilha(nome, paradas, fsDoComando) {      // [{f, x, y}] com f >= t0, em ordem; `fsDoComando`: os quadros das paradas que um comando acabou de pôr (CR2)
      var antes = porComando[nome] || {}, pc = {};
      if (fsDoComando) paradas.forEach(function (pa) { if (fsDoComando.indexOf(pa.f) >= 0 || antes[pa.f]) pc[pa.f] = true; });
      porComando[nome] = pc;
      trilhas[nome] = paradas.map(function (pa) { return { f: pa.f, x: pa.x, y: pa.y }; });
      var u = paradas[paradas.length - 1];
      edicoes[nome] = { x: u.x, y: u.y };
      recalcula(nome);
    }
    function poeParada(nome, g) { poeTrilha(nome, [{ f: t0, x: g.x, y: g.y }]); }      // o arrastar: uma parada, no instante
    function apagaEdicao(nome) { delete edicoes[nome]; delete trilhas[nome]; delete segs[nome]; delete porComando[nome]; }
    function limpaEdicoes() { edicoes = {}; trilhas = {}; segs = {}; porComando = {}; desfazer = []; }
    function partida(nome) { var sg = segs[nome]; return sg && sg.length ? sg[0].f0 : Infinity; }       // o quadro em que a peça deixa o real
    // {x, y, dur, d, f, k, antes}: o trecho que vale no quadro (o último, se já passou de todos); `antes` = ainda no real (a peça ainda não partiu)
    function trecho(nome, quadro) {
      var sg = segs[nome], k = 0;
      for (var i = 0; i < sg.length; i++) if (quadro >= sg[i].f0) k = i;
      if (quadro < sg[0].f0) { var r = realEm(nome, quadro); return { x: r[0], y: r[1], dur: sg[0].dur, d: sg[0].d, f: 0, k: 0, antes: true }; }
      var q = naReta(sg[k], quadro);
      return { x: q.x, y: q.y, dur: sg[k].dur, d: sg[k].d, f: q.f, k: k, antes: false };
    }
    reescrever.posicaoEditada = function (nome) {
      var e = edicoes[nome];
      if (!e || vendoReal()) return null;
      if (!reescrever.sua) return [e.x, e.y];
      if (!editada(nome)) return null;
      var q = trecho(nome, pos);
      return q.antes ? null : [q.x, q.y];      // antes de partir a peça é o real (o replay a desenha como sempre)
    };
    reescrever.yawEditada = function (nome) {
      if (vendoReal() || !reescrever.sua || !editada(nome)) return null;
      var q = trecho(nome, pos);
      if (q.antes) return null;
      var sg = segs[nome][q.k];
      return Math.atan2(sg.by - sg.ay, sg.bx - sg.ax) * 180 / Math.PI;
    };
    // quem foi editado não morre na sua versão: a morte do real só aparece no fantasma (a de antes de ele partir fica: até lá ele é o real)
    reescrever.semAMorte = function (e) { return !vendoReal() && e.type === "kill" && e.f > partida(e.victim) && editada(e.victim); };
    // a trilha para quem edita sem arrastar (os comandos, CR1c): `define` recusa o que o modelo não sustenta (peça morta, antes do instante, fora de ordem)
    reescrever.trilha = {
      define: function (nome, paradas, fsDoComando) {
        var it = pecas.filter(function (q) { return q.p.name === nome; })[0], ant = -Infinity;
        if (!reescrever.ativo || reescrever.sua || !it || !it.vivo || !paradas || !paradas.length) return false;
        for (var i = 0; i < paradas.length; i++) {
          var pa = paradas[i];
          if (!pa || typeof pa.f !== "number" || typeof pa.x !== "number" || typeof pa.y !== "number" || !isFinite(pa.f) || !isFinite(pa.x) || !isFinite(pa.y) || pa.f < t0 || pa.f > cur.frames - 1 || pa.f <= ant) return false;
          ant = pa.f;
        }
        if (!it.p.alive[Math.floor(paradas[0].f)]) return false;     // quem já morreu no real só existe no real (D3)
        var antesT = trilhas[nome] ? trilhas[nome].map(function (pa) { return { f: pa.f, x: pa.x, y: pa.y }; }) : null, antesPc = porComando[nome];
        poeTrilha(nome, paradas, fsDoComando);
        if (!editada(nome)) {      // não é edição: volta ao que era antes (uma trilha que já existia não some)
          if (antesT) { trilhas[nome] = antesT; edicoes[nome] = { x: antesT[antesT.length - 1].x, y: antesT[antesT.length - 1].y }; porComando[nome] = antesPc || {}; recalcula(nome); } else apagaEdicao(nome);
          return false;
        }
        atualizaBanco(); draw();
        return true;
      },
      de: function (nome) { return trilhas[nome] ? trilhas[nome].map(function (pa) { return { f: pa.f, x: pa.x, y: pa.y }; }) : []; },
      apaga: function (nome) { if (trilhas[nome]) { apagaEdicao(nome); atualizaBanco(); draw(); } }
    };
    // O "Desfazer" dos comandos (CR2): UM item por comando aplicado, mesmo quando mexe em mais de uma peça. A foto guarda, das peças que o comando tocou, a trilha de ANTES
    // (e as paradas que já vinham de comandos): desfazer a devolve exatamente. Mexer na peça à mão depois não impede o desfazer: ele devolve a trilha de antes do comando.
    function clonaTrilha(nome) { return trilhas[nome] ? trilhas[nome].map(function (pa) { return { f: pa.f, x: pa.x, y: pa.y }; }) : null; }
    reescrever.comandos = reescrever.comandos || {};
    reescrever.comandos.foto = function (nomes) {
      var o = {};
      nomes.forEach(function (n) { o[n] = { trilha: clonaTrilha(n), pc: porComando[n] ? Object.assign({}, porComando[n]) : null }; });
      return o;
    };
    reescrever.comandos.empurra = function (foto, linha) { desfazer.push({ foto: foto, linha: linha }); atualizaBanco(); };
    reescrever.comandos.desfaz = function () {
      var u = desfazer.length && !reescrever.sua ? desfazer.pop() : null;
      if (!u) return false;
      Object.keys(u.foto).forEach(function (n) {
        var f = u.foto[n];
        if (f.trilha) { trilhas[n] = f.trilha; edicoes[n] = { x: f.trilha[f.trilha.length - 1].x, y: f.trilha[f.trilha.length - 1].y }; porComando[n] = f.pc || {}; recalcula(n); } else apagaEdicao(n);
      });
      atualizaBanco(); draw();
      return true;
    };
    reescrever.comandos.profundidade = function () { return desfazer.length; };
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
      if (it._virtual || vendoReal()) return false;
      if (it.by && editada(it.by) && lancouEm(it) > partida(it.by)) return true;
      return !!(reescrever.granada && reescrever.granada.trocada(geradoraDe(it)));      // a granada trocada some da sua versão (fica só no fantasma)
    };
    reescrever.podeTocar = function () { return algumaMudanca(); };
    reescrever.esmaecida = function (nome) {     // depois da morte do real a peça editada fica esmaecida (o ✕ do fantasma mostra onde ele morreu)
      var it = pecas.filter(function (q) { return q.p.name === nome; })[0];
      return !!(!vendoReal() && reescrever.sua && it && !it.p.alive[Math.floor(pos)]);
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
      if (vendoReal()) return;      // vendo o real (celular): nada da sua versão por cima
      var contorno = C.contorno, tinta = CM.tinta;
      c.save();
      c.lineCap = "round"; c.lineJoin = "round";
      Object.keys(edicoes).forEach(function (nome) {
        var o = origem[nome];
        if (!o || !editada(nome)) return;
        segs[nome].forEach(function (sg, k) {
          var ax = mx(sg.ax), ay = my(sg.ay), bx = mx(sg.bx), by = my(sg.by);
          [[contorno, 5.2], [tinta, 2.4]].forEach(function (par) {
            c.strokeStyle = par[0]; c.lineWidth = par[1];
            c.beginPath(); c.moveTo(ax, ay); c.lineTo(bx, by); c.stroke();
          });
          if (k > 0) return;      // o losango marca onde a sua versão começa: onde a peça deixa o real (em t0, para quem foi arrastado)
          c.beginPath(); c.moveTo(ax, ay - 6.5); c.lineTo(ax + 6.5, ay); c.lineTo(ax, ay + 6.5); c.lineTo(ax - 6.5, ay); c.closePath();
          c.fillStyle = tinta; c.strokeStyle = contorno; c.lineWidth = 2; c.fill(); c.stroke();
        });
      });
      c.restore();
      Object.keys(edicoes).forEach(function (nome) {
        if (!editada(nome)) return;
        var sg = segs[nome], u = sg[sg.length - 1], q = naReta(u, pos);
        if ((!reescrever.sua || q.f < 1) && u.f1 <= cur.frames - 1) MapCore.rotulo(formata(TX.chega, { relogio: relogioNo(u.f1) }), mx(u.bx), my(u.by),
          { cor: CM.tinta, prioridade: 4, dy: 18 });
      });
      if (reescrever.sua && reescrever.fantasma && MODO_PALCO.matches) desenhaFantasmas(c);      // no celular o real tem a sua vez no alternador, não vem por cima
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

    function editada(nome) {      // algum trecho anda MOVIDA unidades ou mais (do ponto do real em que a peça parte, ou de onde estava): menos que isso não é edição
      var sg = segs[nome];
      return !!(origem[nome] && sg && sg.some(function (t) { return t.d >= MOVIDA; }));
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
      if (vendoReal()) defineVer("sua");               // tocar numa peça no celular volta à sua versão (é nela que se edita)
      e.preventDefault(); e.stopPropagation();       // a peça vem antes do desenho e do arrastar do mapa
      seleciona(nome);
      arrasto = { nome: nome, id: e.pointerId };
      try { mapwrap.setPointerCapture(e.pointerId); } catch (x) { /* sem captura: o movimento segue pelo mapa */ }
    }, true);
    // Nuke: a peça fica dentro da área do andar DELA (o editor é 2D e não troca de andar); em mapa de um andar, dentro da imagem do radar
    function limitaNaArea(nome, g) {
      var area = areaDoAndar(andarDaPeca(nome)) || { x0: 0, y0: 0, x1: RAD.width, y1: RAD.height };
      var px = Math.min(area.x1, Math.max(area.x0, (g.x - RAD.origin_x) * RAD.scale_px_per_unit)), py = Math.min(area.y1, Math.max(area.y0, (RAD.origin_y - g.y) * RAD.scale_px_per_unit));
      return { x: px / RAD.scale_px_per_unit + RAD.origin_x, y: RAD.origin_y - py / RAD.scale_px_per_unit };
    }
    // O teclado (R6b): com uma peça da lista em foco, as setas a movem (Shift anda mais); sobe = norte. O texto de "O que mudou" só é refeito ao SOLTAR
    // a tecla (o leitor de tela anuncia uma vez, não a cada passo)
    var PASSO = 20, PASSO_GRANDE = 100, SETAS = { ArrowUp: [0, 1], ArrowDown: [0, -1], ArrowLeft: [-1, 0], ArrowRight: [1, 0] }, moveuPorTeclado = false;
    hosts.ct.addEventListener("keydown", function (e) {
      var b = e.target.closest && e.target.closest(".peca-rw"), d = SETAS[e.key];
      if (!b || !d || !reescrever.ativo || reescrever.sua || reescrever.ferramenta === "granada" || e.altKey || e.ctrlKey || e.metaKey) return;
      var nome = b.dataset.nome, it = pecas.filter(function (q) { return q.p.name === nome; })[0];
      if (!it || !it.vivo) return;
      e.preventDefault();
      if (vendoReal()) defineVer("sua");
      if (reescrever.sel !== nome) { seleciona(nome, true); b.focus({ preventScroll: true }); }
      var base = edicoes[nome] || origem[nome], passo = e.shiftKey ? PASSO_GRANDE : PASSO;
      poeParada(nome, limitaNaArea(nome, { x: base.x + d[0] * passo, y: base.y + d[1] * passo }));
      moveuPorTeclado = true;
      atualizaBanco(true); draw();
    });
    hosts.ct.addEventListener("keyup", function (e) {
      if (!moveuPorTeclado || !SETAS[e.key]) return;
      moveuPorTeclado = false;
      var nome = reescrever.sel;
      if (nome && !editada(nome)) apagaEdicao(nome);      // de volta ao ponto do real: não conta como movida
      atualizaBanco(); draw();
    });
    mapwrap.addEventListener("pointermove", function (e) {
      if (!arrasto || reescrever.sua || e.pointerId !== arrasto.id) return;
      e.preventDefault(); e.stopPropagation();
      var q = doPonteiro(e);
      var cx = Math.min(cv.width, Math.max(0, q.cx)), cy = Math.min(cv.height, Math.max(0, q.cy));   // a peça fica dentro do mapa
      var g = limitaNaArea(arrasto.nome, aGameUnits(cx, cy));
      poeParada(arrasto.nome, g);
      atualizaBanco(true);     // durante o arrasto o texto de "O que mudou" não é refeito (leitor de tela)
      draw();
    }, true);
    function soltou(e) {
      if (!arrasto || e.pointerId !== arrasto.id) return;
      e.stopPropagation();
      if (!editada(arrasto.nome)) apagaEdicao(arrasto.nome);   // movida por menos de 8 u não conta: volta ao real já ao soltar
      arrasto = null;
      atualizaBanco();
      draw();
    }
    mapwrap.addEventListener("pointerup", soltou, true);
    mapwrap.addEventListener("pointercancel", soltou, true);

    /* ---------- o banco (coluna da esquerda) e o painel (coluna da direita) ---------- */
    function andarDaPeca(nome) {
      var it = pecas.filter(function (q) { return q.p.name === nome; })[0];
      return it && it.p.lv ? it.p.lv[t0] : 0;
    }
    function seleciona(nome, semTexto) {
      reescrever.sel = nome;
      if (LEVELS.length > 1 && nome && andarDaPeca(nome) !== activeLevel(Math.floor(pos))) travaAndar(andarDaPeca(nome));   // peça do outro andar: a vista vai para o andar dela
      atualizaBanco(semTexto);
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
          b.setAttribute("aria-pressed", "false"); b.setAttribute("aria-keyshortcuts", "ArrowUp ArrowDown ArrowLeft ArrowRight");
          var topo = novo("span", "pr-topo");
          topo.appendChild(novo("b", "pr-nome", it.p.name));
          var num = novo("span", "pr-num", String(deste.indexOf(it) + 1));      // o número dos comandos ("TR 2"): só no modo Reescrever (o banco só existe nele)
          num.title = formata(TX.numero_dica, { lado: lado === "ct" ? "CT" : "TR", n: deste.indexOf(it) + 1 });
          topo.appendChild(num);
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
      var desf = document.getElementById("rw-desfazer");
      if (desf) desf.disabled = !desfazer.length || reescrever.sua;
      if (reescrever.comandos.aoMudar) reescrever.comandos.aoMudar();
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
        segs[nome].forEach(function (sg, k) {
          if (sg.d < MOVIDA) return;      // uma parada no mesmo lugar não é um movimento
          if (porComando[nome] && porComando[nome][sg.f0]) return;      // a que um comando pôs: a linha do comando já a diz
          var lugar = k === 0 && it.p.p ? cur.places[it.p.p[Math.floor(sg.f0)]] : "", chega = sg.f1;
          var base = { nome: nome, de: lugar, relogio: relogioNo(sg.f0), chega: relogioNo(chega), seg: (Math.round(sg.dur * 10) / 10).toString().replace(".", ",") };
          itens.push(formata(chega > cur.frames - 1 ? TX.mudou_nao_chega : (lugar ? TX.mudou_move : TX.mudou_move_sem_lugar), base));
        });
        var ini = partida(nome);      // até partir a peça é o real: o que aconteceu antes dela partir é igual nos dois
        cur.events.forEach(function (e) {
          if (e.type !== "kill" || e.f <= ini) return;
          if (e.victim === nome) itens.push(formata(e.attacker ? TX.mudou_morreu : TX.mudou_morreu_sem_matador, { nome: nome, matador: e.attacker, relogio: relogioNo(e.f) }));
          else if (e.attacker === nome && !editada(e.victim)) itens.push(formata(TX.mudou_d3, { nome: nome, vitima: e.victim, relogio: relogioNo(e.f) }));
        });
        cur.events.forEach(function (e) {
          if (e.player !== nome || e.f <= ini) return;
          if (e.type === "plant") itens.push(formata(TX.mudou_plantou, { nome: nome, relogio: relogioNo(e.f) }));
          if (e.type === "defuse") itens.push(formata(TX.mudou_desarmou, { nome: nome, relogio: relogioNo(e.f) }));
        });
        (cur.pops || []).forEach(function (q) {
          if (q.k !== "flash" || q.by !== nome || q.f <= ini) return;
          var n = (q.hit || []).filter(function (v) { return v.e && v.s >= R.effective_blind_s; }).length;
          if (n) itens.push(formata(TX.mudou_cegou, { nome: nome, relogio: relogioNo(q.f), n: formata(n === 1 ? TX.cegos.um : TX.cegos.varios, { n: n }) }));
        });
        cur.nades.forEach(function (n) {
          if (n.by === nome && n.f0 > ini && !(reescrever.granada && reescrever.granada.temTrocaDe(n))) itens.push(formata(TX.mudou_granada, { tipo: TX.granadas[n.k] || n.k, nome: nome, relogio: relogioNo(n.f0) }));
        });
      });
      host.textContent = "";
      itens = desfazer.map(function (u) { return u.linha; }).concat(itens);      // uma linha por comando aplicado, na ordem em que foram aplicados
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
      if (reescrever.comandos.monta) reescrever.comandos.monta(host);      // a seção "Comandos" (CR2, 12-reescrever-comandos.js): entre a dica e o resto
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
      var desf = botao(TX.desfazer, "rw-btn", function () { reescrever.comandos.desfaz(); });
      desf.id = "rw-desfazer"; desf.disabled = true;
      host.appendChild(desf);
      var voltar = botao(TX.voltar, "rw-btn", function () { limpaEdicoes(); if (reescrever.granada) reescrever.granada.limpa(); voltaAEditar(); });
      voltar.id = "rw-voltar"; voltar.disabled = true;
      host.appendChild(voltar);
      host.appendChild(novo("h4", null, TX.mudou_titulo));
      var mudou = novo("ul", "rw-mudou"); mudou.id = "rw-mudou"; mudou.setAttribute("aria-live", "polite");
      host.appendChild(mudou);
      // "Depois" (R6b): o que ainda não existe, desligado e dito em texto ("em breve"); não recebe foco nem faz nada. Quando entrar, ocupa este espaço
      host.appendChild(novo("h4", null, TX.depois_titulo));
      var depois = novo("ul", "rw-depois"); depois.id = "rw-depois";
      [TX.breve_1, TX.breve_2, TX.breve_3].forEach(function (t) {
        var li = novo("li", "rw-breve"); li.setAttribute("aria-disabled", "true");
        li.appendChild(novo("span", null, t));
        li.appendChild(novo("span", "tag neutro", TX.breve));
        depois.appendChild(li);
      });
      host.appendChild(depois);
    }
    function textoFantasma(b) {
      b.textContent = TX.fantasma + ": " + (reescrever.fantasma ? TX.fantasma_ligado : TX.fantasma_desligado);
      b.setAttribute("aria-pressed", String(reescrever.fantasma));
    }
    // volta ao instante e ao editor (a sua versão para de tocar)
    function voltaAEditar() {
      setPlaying(false);
      reescrever.sua = false; reescrever.ver = "sua";
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

    // O alternador Real | Sua versão (R6b, celular): embaixo do transporte; o mapa mostra UM dos dois e o rótulo diz qual, com o relógio. No
    // computador some (o real vem como fantasma por cima). Aparece só dentro do modo (CSS: .stage.reescrevendo).
    var alt = novo("div", "rw-ver"); alt.id = "rw-ver"; alt.setAttribute("role", "radiogroup"); alt.setAttribute("aria-label", TX.ver_rotulo);
    var altBotoes = {};
    [["real", TX.ver_real], ["sua", TX.ver_sua]].forEach(function (par) {
      var b = botao(par[1], "rw-btn rw-ver-b", function () { defineVer(par[0]); });
      b.setAttribute("role", "radio"); b.dataset.ver = par[0];
      b.addEventListener("keydown", function (e) {       // o padrão de radiogroup: as setas trocam e levam o foco
        if (["ArrowLeft", "ArrowRight", "ArrowUp", "ArrowDown"].indexOf(e.key) < 0) return;
        e.preventDefault(); defineVer(par[0] === "real" ? "sua" : "real"); altBotoes[reescrever.ver].focus();
      });
      altBotoes[par[0]] = b; alt.appendChild(b);
    });
    var altRel = novo("span", "rw-ver-rel"); alt.appendChild(altRel);
    trEsq.closest(".transport").insertAdjacentElement("afterend", alt);
    function atualizaAlt() {
      ["real", "sua"].forEach(function (v) { altBotoes[v].setAttribute("aria-checked", String(reescrever.ver === v)); altBotoes[v].tabIndex = reescrever.ver === v ? 0 : -1; });
      altRel.textContent = formata(TX.ver_relogio, { qual: reescrever.ver === "real" ? TX.ver_real : TX.ver_sua, relogio: relogioNo(Math.floor(pos)) });
    }
    function defineVer(v) {
      if (reescrever.ver === v) return;
      reescrever.ver = v; atualizaAlt(); draw();
    }
    atualizaAlt();

    // "Reescrever daqui · 0:55": só com o Replay parado e fora do modo; o espaço fica reservado (visibility), então nada se mexe
    reescrever.aoQuadro = function () {
      var vivo = !reescrever.ativo && !playing;
      daqui.style.visibility = vivo ? "visible" : "hidden";
      daqui.disabled = !vivo;
      if (vivo) daqui.lastChild.textContent = " · " + relogioNo(Math.floor(pos));
      if (reescrever.ativo) playBtn.setAttribute("aria-label", playing ? TX.pausa : TX.toca);
      atualizaAlt();
    };

    /* ---------- entrar e sair ---------- */
    var andarAntes = null;
    reescrever.entra = function () {
      if (reescrever.ativo || !cur || document.querySelector("[data-panel='replay']").hidden) return;
      setPlaying(false);
      t0 = Math.floor(pos); pos = t0; frame = t0;     // o instante é o quadro gravado imediatamente anterior (o mesmo do `instante()`)
      scrubEl.value = t0;
      limpaEdicoes(); origem = {}; arrasto = null; reescrever.sel = null; reescrever.sua = false; reescrever.ver = "sua"; reescrever.instante = t0;
      andarAntes = levelLock;      // o andar travado de antes: a saída o devolve (selecionar peça do outro andar trava o dela)
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
      reescrever.ativo = false; reescrever.sua = false; reescrever.ver = "sua"; reescrever.sel = null; arrasto = null; limpaEdicoes(); origem = {}; pecas = [];
      if (LEVELS.length > 1 && levelLock !== andarAntes) travaAndar(andarAntes);
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
    // As portas de entrada (R5): o botão "Reescrever" dos momentos do "Por que perdeu" e dos chips do Perfil. Abre o round em
    // `t` (segundos desde o fim do freeze), 3 s antes (o mesmo pré-roll do Replay), já editando e com `quem` selecionado.
    // Se já estiver no modo, com edições, pergunta antes de descartar (como trocar de round).
    reescrever.abreEm = function (round, t, quem) {
      function vai() {
        if (reescrever.ativo) reescrever.sai(true);
        if (!abreNoReplay(round, t)) return;
        reescrever.entra();
        if (quem && reescrever.ativo && pecas.some(function (it) { return it.p.name === quem && it.vivo; })) seleciona(quem);
        if (MODO_PALCO.matches) rolaAtePalco();
        else {      // celular: o topo do palco (a pílula "Reescrever" e o "Sair") logo abaixo das faixas grudadas, não escondido atrás delas
          var abas = document.querySelector(".tabs").getBoundingClientRect(), pal = document.getElementById("palco").getBoundingClientRect();
          window.scrollBy({ top: pal.top - abas.bottom - 8, behavior: reduced ? "auto" : "smooth" });
        }
      }
      if (reescrever.ativo && reescrever.pedeDescartar(vai)) return;
      vai();
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
      dlg.addEventListener("close", function () {      // Esc ou Continuar: nada a seguir; e o endereço volta a ser o da aba à mostra (voltar do navegador)
        depoisDeDescartar = null;
        if (reescrever.aoFecharOAviso) setTimeout(reescrever.aoFecharOAviso, 0);
      });
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

    function telaDa(nome) {      // onde a peça está na TELA (px CSS, com o zoom e o pan da vista): o ponto em que o teste a pega
      var q = edicoes[nome] || origem[nome];
      if (!q) return null;
      var pt = new DOMPoint(mx(q.x), my(q.y)).matrixTransform(matrizDaVista()), r = cv.getBoundingClientRect(), k = cv.width / r.width;
      return [r.left + pt.x / k, r.top + pt.y / k];
    }
    // o estado para os testes (como `__medicaoRotulos` e `__marcasDeBorda`): quem está editável e onde cada peça está
    window.__reescrever = function () {
      return {
        andar: LEVELS.length > 1 ? activeLevel(Math.floor(pos)) : 0, area: LEVELS.length > 1 ? [0, 1].map(function (i) { return areaDoAndar(i); }) : null,
        ver: reescrever.ver, vendoReal: vendoReal(), rotuloVer: altRel.textContent,
        ativo: reescrever.ativo, sua: reescrever.sua, fantasma: reescrever.fantasma, instante: t0, quadro: pos,
        fantasmas: reescrever.ativo && reescrever.sua ? fantasmasAgora().map(function (g) { return { nome: g.it.p.name, vivo: g.vivo, x: g.sp[0], y: g.sp[1] }; }) : [],
        esmaecidas: reescrever.ativo ? pecas.filter(function (it) { return editada(it.p.name) && reescrever.esmaecida(it.p.name); }).map(function (it) { return it.p.name; }) : [],
        soNoReal: reescrever.ativo ? [].concat(cur.nades, cur.smokes, cur.fires, cur.pops || []).filter(function (it) { return reescrever.soNoReal(it); }).length : 0, relogio: relogioNo(t0), selecionada: reescrever.sel,
        trocas: reescrever.granada ? reescrever.granada.estado() : null, comandos: { desfazer: desfazer.length, linhas: desfazer.map(function (u) { return u.linha; }) },
        pecas: pecas.map(function (it) {
          var e = edicoes[it.p.name], o = origem[it.p.name];
          var ag = e && editada(it.p.name) ? reescrever.posicaoEditada(it.p.name) : null;
          return { nome: it.p.name, nivel: andarDaPeca(it.p.name), tela: telaDa(it.p.name), lado: it.p.side, editavel: it.vivo, editada: editada(it.p.name), x: e ? e.x : (o ? o.x : null), y: e ? e.y : (o ? o.y : null),
                   x0: o ? o.x : null, y0: o ? o.y : null, agora: ag, velocidade: it.vivo ? velocidadeDe(it.p.name) : null,
                   trilha: reescrever.trilha.de(it.p.name), partida: editada(it.p.name) ? partida(it.p.name) : null,
                   trechos: segs[it.p.name] ? segs[it.p.name].map(function (sg) { return { f0: sg.f0, f1: sg.f1, ax: sg.ax, ay: sg.ay, bx: sg.bx, by: sg.by, d: sg.d, dur: sg.dur }; }) : [] };
        })
      };
    };

    window.__reescrever.trilha = reescrever.trilha;      // quem edita sem arrastar (os testes, e os comandos na CR1c)

    // o que a granada (11-reescrever-granada.js) precisa do núcleo
    reescrever.nucleo = {
      t0: function () { return t0; }, pecas: function () { return pecas; }, editada: editada, relogioNo: relogioNo, formata: formata, novo: novo, botao: botao,
      atualizaBanco: atualizaBanco, algumaMudanca: algumaMudanca, velocidadeDe: velocidadeDe, andarDaPeca: andarDaPeca, atualizaMudou: atualizaMudou,
      posicaoNoQuadro: function (nome, f) { if (segs[nome] && segs[nome].length) { var q = trecho(nome, f); return { x: q.x, y: q.y }; } var r = realEm(nome, f); return { x: r[0], y: r[1] }; }, doPonteiro: doPonteiro, aGameUnits: aGameUnits, matrizDaVista: matrizDaVista, tracejado: tracejado
    };

    montaAcoes();
    reescrever.aoQuadro();
  })();
