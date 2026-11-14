/* Os comandos dentro do Reescrever (CR2): a tela do cartão "O que entendi", as perguntas e o Aplicar. Carregado SÓ quando a seção "Comandos" abre (a casca está em
   `partida/12-reescrever-comandos.js`), depois de `leitor.js`, `plano.js` e `real.js`, que fazem o resto:
     - `ComandosDoReal` lê a frase (nicks, "TR 2", relógio da tela) e dá o veredito do round real a cada comando (morte real, antes do instante, "bomba ou round?");
     - `PlanoDeComandos` calcula os horários (o mesmo plano da prancheta, num "mundo" em que a peça anda em linha reta na velocidade medida, como no Reescrever);
     - aqui o plano vira trilha: `reescrever.trilha.define` (CR1b) e um item de "Desfazer" por comando aplicado.
   Nada muda antes do Aplicar. A granada fica para a CR3: um comando "joga ..." não é aplicado e o cartão diz isso. Estilo ES5, como o resto do site. */
(function (global) {
  "use strict";

  function fmt(tpl, v) { return String(tpl == null ? "" : tpl).replace(/\{(\w+)\}/g, function (_, k) { return v && v[k] != null ? v[k] : "{" + k + "}"; }); }
  function mmss(s) { s = Math.max(0, s); var m = Math.floor(s / 60), r = Math.floor(s % 60); return m + ":" + (r < 10 ? "0" : "") + r; }
  function el(tag, cls, texto, attrs) {
    var n = document.createElement(tag);
    if (cls) n.className = cls;
    if (texto != null) n.textContent = texto;
    Object.keys(attrs || {}).forEach(function (k) { n.setAttribute(k, attrs[k]); });
    return n;
  }

  function inicia(P) {
    var TX = P.TX, N = P.N, C = P.C, RC = global.ComandosDoReal, hz = P.R.sample_hz;
    var ctx = RC.contexto(P.contexto, P.round, P.t0, P.R);
    var T = ctx.textos, cartao = P.cartao, campo = P.campo;
    var estado = { leitura: null, plano: null, vereds: [], msg: null, horario: null, prof: C.profundidade(), editando: P.editando() };
    var fins = {};

    function t(k, v) { return fmt(T[k] != null ? T[k] : TX[k] != null ? TX[k] : k, v); }
    function jogador(lado, num) { return ctx.jogadores.filter(function (j) { return j.lado === lado && j.num === num; })[0] || null; }

    /* ---------- o mundo do plano: a peça no Reescrever anda em linha reta, na velocidade medida da arma na mão (a mesma conta da trilha) ---------- */
    var andares = new Array(Math.max(1, P.andares));
    var sx = { estado: { passos: [{ passo: 0 }], pecas: {} }, e3: null, t: 0 };
    ctx.jogadores.forEach(function (j) { sx.estado.pecas[j.nick] = { lado: j.lado === "ct" ? "ct" : "t", rotulo: String(j.num) }; });
    var cfg = { comandos: { velocidade_piso_correndo: ctx.velocidade_piso_correndo, pontos: ctx.pontos, granada: ctx.granada, textos: T }, biblioteca: null };
    var mundo = {
      S: function () { return sx; }, cfg: function () { return cfg; }, M3: function () { return { SEGUNDOS_DO_ROUND: ctx.segundos_do_round }; },
      ANDARES: function () { return andares; }, CENTRO: function () { return null; },
      Tempos: { estado: "pronta", dados: null, pontos: {}, areas: {}, nos: [], areaDoTexto: {} },      // sem a tabela do corpus: a corrida é a do Reescrever, em linha reta
      t: t, doRelogio: function (s) { return RC.relogioNa(ctx.real, s); },
      peca: function (q) { var j = jogador(q.lado, q.num); return j ? j.nick : null; },
      nomeDoAlvo: function (a) { return a.tipo === "area" ? (a.exibe || a.texto || a.nome) : a.nome + (a.qualificacao ? " (" + a.qualificacao + ")" : ""); },
      ladoEscrito: function (l) { return l === "ct" ? "CT" : "TR"; },
      velocidade: function () { return ctx.velocidade_piso_correndo; }, velocidadePiso: function (pid, modo) { return N.velocidadeDe(pid, modo); },      // andando e agachado têm a velocidade própria (a da C3), igual à da trilha
      funcaoDe: function () { return null; }, lugarDe: function () { return null; }, lugarExibido: function () { return null; }, nivelDoZ: function () { return 0; },
      bibliotecaPronta: function () { return true; },
      quadroNoTempo: function (e3, tt) {      // onde cada peça está em `tt` na SUA versão (a trilha que já existe) ou, sem edição, no real
        var f = Math.min(P.round.frames - 1, Math.max(0, tt * hz)), o = { pecas: {} };
        ctx.jogadores.forEach(function (j) { var q = N.posicaoNoQuadro(j.nick, f); o.pecas[j.nick] = { x: q.x, y: q.y, nivel: N.andarDaPeca(j.nick) }; });
        return o;
      },
      baseReal: function () { return null; }, cortaReal: function () { return []; }, ancoraReal: function () { return []; }, novoId: function () { return "c" + (++seq); },
      marcoQueContem: function () { return 0; }, agora: function () { return ctx.real.t0_s; },
      aoAnotar: function (i, pid, t0, fim) { fins[i] = Math.max(fins[i] === undefined ? -Infinity : fins[i], fim); }
    };
    var seq = 0, plano = global.PlanoDeComandos.cria(mundo);

    /* ---------- o cartão: o que o site entendeu, dito do jeito da prancheta, com o nick sempre ---------- */
    function quem(ac) {
      if (!ac.quem.length) return t("quem_vazio");
      return ac.quem.map(function (q) {
        var j = q.resolvido !== false && q.lado ? jogador(q.lado, q.num) : null;
        return j ? fmt(TX.cmd_quem, { nick: j.nick, lado: j.lado.toUpperCase(), num: j.num }) : (q.ref || t("quem_vazio"));
      }).join(" + ");
    }
    function quando(ac) {
      var q = ac.quando, p = estado.plano;
      if (!q) return t("q_sem");
      if (q.tipo === "relogio") return t("q_relogio", { h: mmss(q.segundos_restantes) });
      if (q.tipo === "inicio") return t("q_inicio", { n: q.segundos });
      if (q.tipo === "depois") return p && p.inicios[ac.indice] != null ? t("q_depois_h", { h: mundo.doRelogio(p.inicios[ac.indice]) }) : t("q_depois");
      if (q.tipo === "junto") return t("q_junto");
      if (q.tipo === "agora") return p && p.inicios[ac.indice] != null ? t("q_agora_h", { h: mundo.doRelogio(p.inicios[ac.indice]) }) : t("q_agora");
      return t("q_sem");
    }
    function linha(ac) {
      var v = { quem: quem(ac), alvo: ac.alvo ? mundo.nomeDoAlvo(ac.alvo) : t("onde_vazio"), quando: quando(ac), granada: ac.granada ? (t("granada_" + ac.granada) || ac.granada) : "?",
                modo: ac.modo || "correndo", n: ac.espera_s, fim: ac.fim ? mmss(ac.fim.segundos_restantes) : "" };
      var chave = { lancar: "linha_lancar", mover: "linha_mover", segurar: "linha_segurar", esperar: "linha_esperar" }[ac.tipo] || "linha_incompleta";
      if (ac.tipo === "segurar" && ac.fim) chave = "linha_segurar_ate";
      var texto = t(chave, v), ch = estado.plano && estado.plano.chegadas[ac.indice];
      if (estado.plano && estado.plano.cortados[ac.indice]) texto += " · " + t("cortado_por", { n: estado.plano.cortados[ac.indice] });
      else if (ch) texto += " · " + t("cmd_chega", { h: mundo.doRelogio(ch.t) });
      return texto;
    }

    /* ---------- a leitura, o plano e os vereditos do round real ---------- */
    function pronta() { var l = estado.leitura; return !!l && !l.perguntas.length && !l.naoEntendido.length; }
    function temGranada() { return !!estado.leitura && estado.leitura.acoes.some(function (a) { return a.tipo === "lancar"; }); }
    function recalcula() {
      var l = estado.leitura; estado.plano = null; estado.vereds = []; fins = {};
      if (!l) return;
      if (pronta() && !temGranada()) estado.plano = plano.plano(l);
      var p = estado.plano;      // o horário que o plano calculou ("depois", "junto", "agora" depois de outro comando) entra no veredito como se estivesse escrito
      var copia = { acoes: l.acoes.map(function (ac) {
        var q = ac.quando, explicito = q && (q.tipo === "relogio" || q.tipo === "inicio") || (q && q.tipo === "agora" && ac.indice === 0);
        if (explicito || !p || p.inicios[ac.indice] == null) return ac;
        var c = {}; Object.keys(ac).forEach(function (k) { c[k] = ac[k]; });
        c.quando = { tipo: "relogio", segundos_restantes: ctx.segundos_do_round - p.inicios[ac.indice], t_decorrido: p.inicios[ac.indice] };
        return c;
      }), perguntas: l.perguntas };
      estado.vereds = RC.veredictos(copia, ctx, fins);
    }
    function pode() {
      var p = estado.plano;
      return !!(P.editando() && pronta() && !temGranada() && p && !p.falta && !p.pergunta && !p.problemas.length && p.ops.length && estado.vereds.length && estado.vereds.every(function (v) { return v.aplica; }));
    }

    /* ---------- o desenho ---------- */
    // O que acabou de aparecer (veredito, pergunta, cartão) tem de estar À VISTA sem ninguém rolar: o cartão rola até o bloco, e a coluna do painel (só ela, nunca a página) rola até o cartão.
    function mostra() {
      var bloco = cartao.querySelector(".rw-cmd-veredito.recusa") || cartao.querySelector(".rw-cmd-pergunta") || cartao.querySelector(".rw-cmd-veredito"), c = cartao.getBoundingClientRect();
      cartao.scrollLeft = 0;
      if (bloco) cartao.scrollTop = Math.max(0, cartao.scrollTop + bloco.getBoundingClientRect().top - c.top - 6);
      var col = cartao.closest(".painel-rw");
      if (col && col.scrollHeight > col.clientHeight + 1) {
        var r = col.getBoundingClientRect(), k = cartao.getBoundingClientRect(), fim = P.aplicar.getBoundingClientRect().bottom;
        if (k.top < r.top || fim > r.bottom) col.scrollTop += k.top - r.top - 6;      // o topo do cartão no alto da coluna (o cartão tem altura fixa: cabe)
      }
    }
    function foca() {
      var a = cartao.querySelector(".rw-cmd-horario") || cartao.querySelector(".rw-cmd-opcao:not(:disabled)");
      if (a) a.focus({ preventScroll: true });
      mostra();
    }
    function botoes() {
      P.aplicar.disabled = !pode();
      P.corrigir.disabled = !estado.leitura;
    }
    function responde(valor) {
      estado.leitura = RC.responde(estado.leitura, 0, valor, ctx);
      estado.horario = null; estado.msg = null;
      recalcula(); desenha(); foca();
    }
    function corrige() {
      estado.leitura = null; estado.plano = null; estado.vereds = []; estado.msg = null; estado.horario = null;
      desenha(); campo.focus({ preventScroll: true }); campo.select(); mostra();
    }
    function botaoDoVeredito(v, b) {
      var bt = el("button", "rw-btn rw-cmd-opcao", b.rotulo, { type: "button", "data-botao": b.codigo });
      bt.addEventListener("click", function () {
        if (b.codigo === "corrigir") { corrige(); return; }
        if (b.codigo === "outro_jogador") estado.leitura = RC.escolherOutro(estado.leitura, v.acao, { lado: v.lado, num: v.num }, ctx);
        else if (b.codigo === "comecar_em") estado.leitura = RC.comecarNoInstante(estado.leitura, v.acao, ctx);
        estado.msg = null; recalcula(); desenha(); foca();
      });
      return bt;
    }
    function perguntaDoHorario(p, aoEscolher) {
      var cx = el("input", "rw-cmd-horario", null, { type: "text", placeholder: t("ui_horario"), autocomplete: "off", "aria-label": p.texto, inputmode: "text" });
      function vai() {
        var h = RC.horario(cx.value, ctx);
        if (!h || h.invalido || h.ambiguo || (h.segundos_restantes == null && !h.ambiguo_relogio)) {
          estado.msg = h && h.ambiguo ? t("pergunta_quando_segundos", { n: h.segundos }) + " " + t("ui_horario") + "." : t("pergunta_horario_invalido", { horario: h && h.segundos_restantes != null ? mmss(h.segundos_restantes) : cx.value });
          desenha(); return;
        }
        if (h.ambiguo_relogio) { estado.horario = h.pergunta; estado.msg = null; desenha(); foca(); return; }      // "bomba ou round?"
        aoEscolher({ quando: h });
      }
      cx.addEventListener("keydown", function (e) { if (e.key === "Enter") { e.preventDefault(); vai(); } });
      var ok = el("button", "rw-btn", t("ui_confirmar"), { type: "button" });
      ok.addEventListener("click", vai);
      var d = el("div", "rw-cmd-linha-horario"); d.appendChild(cx); d.appendChild(ok);
      return d;
    }
    function desenha() {
      cartao.textContent = ""; cartao.scrollTop = 0;
      var l = estado.leitura;
      if (!P.editando()) {      // a sua versão está tocando: nada se aplica, mas o que o cartão dizia por último não some
        if (estado.msg) cartao.appendChild(el("p", "rw-cmd-aviso", estado.msg));
        cartao.appendChild(el("p", "rw-cmd-aviso", TX.cmd_so_editando, { role: "status" })); botoes(); return;
      }
      if (!l) {
        cartao.appendChild(el("p", estado.msg ? "rw-cmd-aviso" : "rw-cmd-vazio", estado.msg || TX.cmd_vazio, estado.msg ? { role: "status" } : {}));
        botoes(); return;
      }
      cartao.appendChild(el("h5", "rw-cmd-sub", TX.cmd_entendi));
      var lista = el("ol", "rw-cmd-entendi", null, { id: "rw-cmd-entendi" });
      l.acoes.forEach(function (ac) { lista.appendChild(el("li", null, linha(ac))); });
      cartao.appendChild(lista);
      l.avisos.forEach(function (a) {
        if (a.codigo === "duracao_imposta" || a.codigo === "ordem_invertida") cartao.appendChild(el("p", "rw-cmd-aviso", t("aviso_" + a.codigo, { n: a.segundos != null ? a.segundos : "" })));
      });
      if (estado.plano) estado.plano.avisos.filter(function (m, i, v) { return v.indexOf(m) === i; }).forEach(function (m) { cartao.appendChild(el("p", "rw-cmd-aviso", m)); });
      if (l.naoEntendido.length) cartao.appendChild(el("p", "rw-cmd-aviso", t("aviso_palavra_sobrando", { trechos: l.naoEntendido.map(function (x) { return "“" + x.trecho + "”"; }).join(", ") }) + " " + TX.cmd_corrija));
      estado.vereds.forEach(function (v) {      // o que o round real diz de cada comando: recusado (com botões) ou aplicado com aviso
        if (v.codigo === "ok" || v.codigo === "pendente" || !v.texto) return;
        var b = el("div", "rw-cmd-veredito " + (v.aplica ? "aviso" : "recusa"), null, { "data-codigo": v.codigo, role: "group" });
        b.appendChild(el("p", null, v.texto));
        if (v.botoes.length) { var op = el("div", "rw-cmd-opcoes"); v.botoes.forEach(function (bt) { op.appendChild(botaoDoVeredito(v, bt)); }); b.appendChild(op); }
        cartao.appendChild(b);
      });
      var p = l.perguntas[0];
      if (estado.horario) {      // "bomba ou round?" do horário que a pessoa acabou de digitar
        var qh = estado.horario, bh = el("div", "rw-cmd-pergunta", null, { role: "group", "aria-label": qh.texto });
        bh.appendChild(el("p", "rw-cmd-pergunta-texto", qh.texto));
        var oh = el("div", "rw-cmd-opcoes");
        qh.opcoes.forEach(function (o) { var b = el("button", "rw-btn rw-cmd-opcao", o.rotulo, { type: "button" }); b.addEventListener("click", function () { responde(o.valor); }); oh.appendChild(b); });
        bh.appendChild(oh); cartao.appendChild(bh);
      } else if (p) {
        var bp = el("div", "rw-cmd-pergunta", null, { role: "group", "aria-label": p.texto });
        bp.appendChild(el("p", "rw-cmd-pergunta-texto", p.texto));
        var op2 = el("div", "rw-cmd-opcoes");
        (p.opcoes || []).forEach(function (o) {
          var b = el("button", "rw-btn rw-cmd-opcao", o.rotulo, { type: "button" }), j = o.valor && o.valor.lado ? jogador(o.valor.lado, o.valor.num) : null;
          if (j && !j.vivo) { b.disabled = true; b.setAttribute("data-morto", "1"); }      // quem já morreu não serve: o botão fica, desligado, e o rótulo diz o motivo
          else b.addEventListener("click", function () { responde(o.valor); });
          op2.appendChild(b);
        });
        if (p.codigo === "quando" || p.codigo === "horario_invalido") { bp.appendChild(op2); bp.appendChild(perguntaDoHorario(p, responde)); }
        else if (p.opcoes && p.opcoes.length) bp.appendChild(op2);
        else bp.appendChild(el("p", "rw-cmd-aviso", TX.cmd_corrija));
        cartao.appendChild(bp);
      } else if (estado.plano && estado.plano.falta) {
        var f = estado.plano.falta;
        cartao.appendChild(el("p", "rw-cmd-erro", fmt(TX.cmd_andar, { quem: f.quem, alvo: f.alvo }), { role: "alert" }));
      } else if (estado.plano && estado.plano.problemas.length) {
        estado.plano.problemas.filter(function (m, i, v) { return v.indexOf(m) === i; }).forEach(function (m) { cartao.appendChild(el("p", "rw-cmd-erro", m, { role: "alert" })); });
      }
      if (temGranada()) cartao.appendChild(el("p", "rw-cmd-erro", TX.cmd_granada_nao_pronta, { id: "rw-cmd-granada" }));      // depois da pergunta (se houver): a pergunta vem primeiro
      if (estado.msg) cartao.appendChild(el("p", "rw-cmd-aviso", estado.msg, { role: "status" }));
      botoes();
    }

    /* ---------- entender e aplicar ---------- */
    function entende() {
      var texto = campo.value.trim();
      estado.msg = null; estado.horario = null;
      if (!P.editando()) { desenha(); return; }
      try { estado.leitura = texto ? RC.le(texto, ctx) : null; } catch (e) { estado.leitura = null; estado.msg = TX.cmd_corrija; }
      recalcula(); desenha(); foca();
    }
    // o plano vira paradas da trilha: cada trecho do caminho parte do instante em que a peça estava no ponto anterior (a espera "fica até H" é só o intervalo entre duas paradas)
    function paradasDe(op) {
      var pts = op[1].pontos.slice().sort(function (a, b) { return a.t - b.t; }), out = [];
      for (var k = 1; k < pts.length; k++) if (Math.hypot(pts[k].x - pts[k - 1].x, pts[k].y - pts[k - 1].y) > 0.5) { var pa = { f: pts[k - 1].t * hz, x: pts[k].x, y: pts[k].y }; if (pts[k].modo && pts[k].modo !== "correndo") pa.modo = pts[k].modo; out.push(pa); }
      return out;
    }
    // a causa certa de o Aplicar não valer: o round acabou antes da partida do comando, ou a peça já está lá (menos de 8 u); senão a mensagem geral
    function porQueNao(nome, ps) {
      var ultimo = P.round.frames - 1, j = ctx.jogadores.filter(function (x) { return x.nick === nome; })[0], rotulo = j ? fmt(TX.cmd_quem, { nick: j.nick, lado: j.lado.toUpperCase(), num: j.num }) : nome;
      if (ps[0].f > ultimo) return fmt(TX.cmd_nao_aplicou_fim, { quem: rotulo, h_cmd: N.relogioNo(Math.round(ps[0].f)), h_fim: N.relogioNo(ultimo) });
      var q = N.posicaoNoQuadro(nome, ps[0].f);
      if (ps.every(function (pa) { return Math.hypot(pa.x - q.x, pa.y - q.y) < 8; })) return fmt(TX.cmd_nao_aplicou_parado, { quem: rotulo, u: 8 });
      return fmt(TX.cmd_nao_aplicou, { quem: rotulo });
    }
    function aplica() {
      if (!pode()) return;
      var novas = {}, nomes = [];
      estado.plano.ops.forEach(function (op) { if (op[0] === "cria_caminho") { var ps = paradasDe(op); if (ps.length) { novas[op[1].peca] = ps; nomes.push(op[1].peca); } } });
      if (!nomes.length) { estado.msg = TX.cmd_nao_aplicou.replace("{quem}", ""); desenha(); mostra(); return; }
      var foto = C.foto(nomes), feitos = [], falhou = null;
      nomes.forEach(function (nome) {
        if (falhou) return;
        var ps = novas[nome], antes = P.trilha.de(nome).filter(function (pa) { return pa.f < ps[0].f - 1e-6; });      // o que a peça já tinha ANTES deste comando fica; dali em diante vale o comando
        if (P.trilha.define(nome, antes.concat(ps), ps.map(function (pa) { return pa.f; }))) feitos.push(nome); else falhou = nome;
      });
      if (falhou) {
        if (feitos.length) { var sub = {}; feitos.forEach(function (n) { sub[n] = foto[n]; }); C.empurra(sub, ""); C.desfaz(); }      // tudo ou nada: o que já tinha entrado volta
        estado.msg = porQueNao(falhou, novas[falhou]); desenha(); mostra(); return;
      }
      var resumo = estado.leitura.acoes.map(linha).join("; ");
      C.empurra(foto, fmt(TX.cmd_mudou, { linha: resumo }));
      estado.prof = C.profundidade();
      estado.leitura = null; estado.plano = null; estado.vereds = []; estado.msg = TX.cmd_aplicado;
      campo.value = "";
      desenha(); campo.focus({ preventScroll: true }); mostra();
    }
    P.aplicar.onclick = aplica;
    P.corrigir.onclick = corrige;
    function aoMudar() {      // chamado a cada mudança do banco (arrasto, desfazer, tocar): barato quando nada que importa mudou
      var prof = C.profundidade(), ed = P.editando();
      if (prof === estado.prof && ed === estado.editando) return;
      var desfez = prof < estado.prof;
      estado.prof = prof; estado.editando = ed;
      if (desfez) { estado.leitura = null; estado.plano = null; estado.vereds = []; estado.msg = TX.cmd_desfeito; } else if (estado.leitura) recalcula();
      desenha();
    }
    desenha();
    return { entende: entende, aoMudar: aoMudar, estado: function () { return { leitura: estado.leitura, plano: estado.plano, vereds: estado.vereds, pode: pode() }; } };
  }

  global.ComandosNoReescrever = { inicia: inicia };
})(typeof window !== "undefined" ? window : this);
