/* Os comandos dentro do Reescrever (CR2): a tela do cartão "O que entendi", as perguntas e o Aplicar. Carregado SÓ quando a seção "Comandos" abre (a casca está em
   `partida/12-reescrever-comandos.js`), depois de `leitor.js`, `plano.js` e `real.js`, que fazem o resto:
     - `ComandosDoReal` lê a frase (nicks, "TR 2", relógio da tela) e dá o veredito do round real a cada comando (morte real, antes do instante, "bomba ou round?");
     - `PlanoDeComandos` calcula os horários (o mesmo plano da prancheta, num "mundo" em que a peça anda em linha reta na velocidade medida, como no Reescrever);
     - aqui o plano vira trilha: `reescrever.trilha.define` (CR1b) e um item de "Desfazer" por comando aplicado.
   Nada muda antes do Aplicar. A granada (CR3, decisão (a) da CR0): "ropz joga smoke no janelão aos 1:05" TROCA uma granada que o jogador jogou de verdade neste round (do mesmo tipo)
   por um arremesso real da biblioteca (`reescrever.granada.poeTroca`); o site nunca cria uma granada nova e nunca usa um arremesso sem queda perto do destino. Estilo ES5, como o resto do site. */
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
    var TX = P.TX, N = P.N, C = P.C, G = P.G, RC = global.ComandosDoReal, hz = P.R.sample_hz;
    var ctx = RC.contexto(P.contexto, P.round, P.t0, P.R);
    var T = ctx.textos, cartao = P.cartao, campo = P.campo;
    // `grv`: os vereditos da granada (a granada real do round); `grPend`: a pergunta "qual granada?"; `escolhidas`: a granada real de cada (comando, jogador)
    var estado = { leitura: null, plano: null, vereds: [], grv: [], grPend: null, escolhidas: {}, msg: null, horario: null, prof: C.profundidade(), editando: P.editando() };
    var fins = {}, lancs = [];

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
      funcaoDe: function () { return null; },
      // o nome do lugar de um ponto: o que o mapa desenha (a tabela dos nomes dele), na chave que o alvo "área" do leitor usa (o nome do jogo); `lugarExibido` é o que se escreve na tela (o ponto do Pedro, senão a área)
      lugarDe: function (x, y, nivel) { var s = G.lugarDe(x, y, nivel), a = s === null ? null : (ctx.areas || []).filter(function (r) { return r.texto === s; })[0]; return s === null ? null : a ? a.nome : s; },
      lugarExibido: function (x, y, nivel) {
        var d0 = ctx.raio_do_ponto_u, ponto = null, s;
        if (d0) (ctx.pontos || []).forEach(function (p) { var d = Math.hypot(p.x - x, p.y - y); if (d <= d0) { d0 = d; ponto = p; } });
        if (ponto) return ponto.nome;
        s = G.lugarDe(x, y, nivel);
        var a = s === null ? null : (ctx.areas || []).filter(function (r) { return r.texto === s; })[0];
        return s === null ? null : a ? (a.exibe || a.texto) : s;
      },
      nivelDoZ: function (z) { return G.nivelDoPonto(z, 0); },
      bibliotecaPronta: function () { var e = G.biblioteca().estado; return e !== "nao" && e !== "carregando"; },      // "carregando" enquanto o arquivo não chega; erro e "sem biblioteca" valem como sem arremessos
      livreDesde: function () { return ctx.real.t0_s; },      // a peça não parte antes do instante do "Reescrever daqui": uma saída longe demais só chega depois ("Jogar às H?")
      aoLancar: function (info) { lancs.push(info); },
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
      var gr = detalheDaGranada(ac);
      return gr ? texto + " · " + gr : texto;
    }
    function jogadorPorNome(nome) { return ctx.jogadores.filter(function (x) { return x.lado.toUpperCase() + " " + x.num === nome; })[0] || null; }      // "TR 2" é como o plano chama a peça
    function nickDe(nome) { var j = jogadorPorNome(nome); return j ? fmt(TX.cmd_quem, { nick: j.nick, lado: j.lado.toUpperCase(), num: j.num }) : nome; }      // "ropz (TR 2)"
    function j1(nome) { var j = jogadorPorNome(nome); return j ? j.nick : nome; }      // "ropz"
    // nenhum comando recusado (um "pendente" ainda não foi julgado: o comando seguinte só tem horário depois da pergunta da saída)
    function todosOk() { return estado.vereds.every(function (v) { return v.aplica || v.codigo === "pendente"; }) && estado.grv.every(function (v) { return v.aplica; }); }
    // o arremesso real que o plano achou, dito como na prancheta: o lugar de saída "i de n", a partida e o round, e a hora em que a granada parte (e cai, se o voo é conhecido)
    function detalheDaGranada(ac) {
      var g = estado.plano && estado.plano.granadas[ac.indice];
      if (!g || !g.r) return "";
      var b = G.biblioteca().dados, times = b && b.partidas_times && b.partidas_times[g.r.partida];
      var v = { i: g.i, n: g.n, lado: mundo.ladoEscrito(g.lado), partida: times || g.r.partida, round: g.r.round, onde: g.onde, h: mundo.doRelogio(g.tSai), hc: g.tCai == null ? "" : mundo.doRelogio(g.tCai) };
      var s = t(g.tCai == null ? "granada_real_sem_voo" : "granada_real", v);
      return g.levar ? s + "; " + t("granada_levar", { quem: nickDe(g.quem), h: mundo.doRelogio(g.levar.chega) }) : s;
    }

    /* ---------- a leitura, o plano e os vereditos do round real ---------- */
    function pronta() { var l = estado.leitura; return !!l && !l.perguntas.length && !l.naoEntendido.length; }
    function temGranada() { return !!estado.leitura && estado.leitura.acoes.some(function (a) { return a.tipo === "lancar"; }); }
    function ehLancar(i) { return !!estado.leitura && !!estado.leitura.acoes[i] && estado.leitura.acoes[i].tipo === "lancar"; }
    function aoBiblioteca() {      // a biblioteca chegou (ou falhou): o cartão refaz a conta; o foco acompanha só se estava no cartão (ou em lugar nenhum): quem foi digitar em outro lugar não é puxado de volta
      if (!estado.leitura) return;
      var a = document.activeElement, no_cartao = !a || a === document.body || cartao.contains(a) || a === P.entender;
      recalcula(); desenha();
      if (no_cartao) foca(); else mostra();
    }
    function recalcula() {
      var l = estado.leitura; estado.plano = null; estado.vereds = []; estado.grv = []; estado.grPend = null; estado.escolhidas = {}; fins = {}; lancs = [];
      if (!l) return;
      var bib = G.biblioteca(); cfg.biblioteca = bib.estado === "pronta" ? bib.dados : null;
      if (temGranada() && pronta()) G.pede(aoBiblioteca);      // só uma frase com granada, já completa (sem pergunta aberta), pede a biblioteca (arquivo grande): abrir a seção ou digitar não a traz
      if (pronta()) estado.plano = plano.plano(l);
      var p = estado.plano;      // o horário que o plano calculou ("depois", "junto", "agora" depois de outro comando) entra no veredito como se estivesse escrito
      var copia = { acoes: l.acoes.map(function (ac) {
        var q = ac.quando, explicito = q && (q.tipo === "relogio" || q.tipo === "inicio") || (q && q.tipo === "agora" && ac.indice === 0);
        if (explicito || !p || p.inicios[ac.indice] == null) return ac;
        var c = {}; Object.keys(ac).forEach(function (k) { c[k] = ac[k]; });
        c.quando = { tipo: "relogio", segundos_restantes: ctx.segundos_do_round - p.inicios[ac.indice], t_decorrido: p.inicios[ac.indice] };
        return c;
      }), perguntas: l.perguntas };
      estado.vereds = RC.veredictos(copia, ctx, fins);
      if (pronta()) veredictosDaGranada();
    }
    function juntaE(v) { return v.length < 2 ? v.join("") : v.slice(0, -1).join(", ") + " e " + v[v.length - 1]; }
    function recusa(ac, j, codigo, texto) { return { acao: ac.indice, lado: j.lado, num: j.num, nick: j.nick, codigo: codigo, aplica: false, texto: texto, botoes: [{ codigo: "corrigir", rotulo: TX.cmd_corrigir }] }; }
    // O que o round real diz da GRANADA de cada comando "joga ...": o comando só troca uma que o jogador jogou de verdade, do mesmo tipo, DEPOIS do instante.
    //   nenhuma no round: recusado; só antes do instante: recusado (já faz parte do real); uma depois: é essa; várias: pergunta qual (um botão por granada, com o horário e o lugar reais).
    // Depois de o plano rodar: sem arremesso real para o destino, recusado (o Reescrever não "põe a granada sem arremesso real"); e a hora do arremesso vale para a morte real.
    function veredictosDaGranada() {
      var l = estado.leitura, inicio = RC.relogioNa(ctx.real, ctx.real.t0_s);
      l.acoes.forEach(function (ac) {
        if (ac.tipo !== "lancar" || !ac.granada) return;
        ac.quem.forEach(function (q) {
          var j = q.resolvido !== false && q.lado ? jogador(q.lado, q.num) : null;
          if (!j) return;
          var v = estado.vereds.filter(function (x) { return x.acao === ac.indice && x.nick === j.nick; })[0];
          if (v && v.codigo !== "ok" && v.codigo !== "pendente" && v.codigo !== "termina_depois_da_morte") return;      // o round real já recusou o comando: um motivo só
          var g = String(t("granada_" + ac.granada) || ac.granada).toLowerCase(), base = { nick: j.nick, granada: g, inicio: inicio };
          if (v && v.codigo === "termina_depois_da_morte") {      // a hora do arremesso é depois da morte real: a granada não sai da mão de quem já morreu
            var m = v.morte || {}, hm = { nick: j.nick, matador: m.matador, h_morte: m.h, h: RC.relogioNa(ctx.real, fins[ac.indice]) };
            estado.grv.push(recusa(ac, j, "gr_depois_da_morte", fmt(TX[m.matador ? "cmd_gr_depois_da_morte" : "cmd_gr_depois_da_morte_sem_matador"], hm)));
            return;
          }
          var reais = G.reais(j.nick, ac.granada), depois = reais.filter(function (r) { return r.f0 > P.t0; });
          if (!reais.length) { estado.grv.push(recusa(ac, j, "gr_nao_jogou", fmt(TX.cmd_gr_nao_jogou, base))); return; }
          if (!depois.length) { estado.grv.push(recusa(ac, j, "gr_antes", fmt(TX.cmd_gr_antes, { nick: j.nick, granada: g, inicio: inicio, h: juntaE(reais.map(function (r) { return N.relogioNo(r.f0); })) }))); return; }
          var escolhida = depois.length === 1 ? depois[0] : ac.gr_real && ac.gr_real[j.nick] !== undefined ? depois[ac.gr_real[j.nick]] : null;
          if (!escolhida) { estado.grPend = estado.grPend || { ac: ac, j: j, g: g, opcoes: depois, texto: fmt(TX.cmd_gr_qual, { nick: j.nick, n: depois.length, granada: g, inicio: inicio }) }; return; }
          var x = lancs.filter(function (a) { return a.acao === ac.indice && a.pid === j.nick; })[0];
          if (x && x.sem && x.sem !== "carregando") {
            if (G.biblioteca().estado === "erro") return;      // o arquivo não chegou: o cartão diz o erro (não é "o mapa não tem arremessos")
            estado.grv.push(recusa(ac, j, x.sem === "sem_biblioteca" ? "gr_sem_biblioteca" : "gr_sem_real",
              x.sem === "sem_biblioteca" ? TX.cmd_gr_sem_biblioteca : fmt(TX.cmd_gr_sem_real, { lado: mundo.ladoEscrito(x.lado), granada: g, alvo: ac.alvo ? mundo.nomeDoAlvo(ac.alvo) : "" })));
            return;
          }
          estado.escolhidas[ac.indice + ":" + j.nick] = escolhida;
        });
      });
    }
    function pode() {
      var p = estado.plano;
      return !!(P.editando() && pronta() && p && !p.falta && !p.pergunta && !p.espera && !p.problemas.length && p.ops.length && estado.vereds.length && estado.vereds.every(function (v) { return v.aplica; })
        && !estado.grPend && estado.grv.every(function (v) { return v.aplica; }) && lancs.every(function (x) { return !x.sem; }));
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
      estado.leitura = null; estado.plano = null; estado.vereds = []; estado.grv = []; estado.grPend = null; estado.msg = null; estado.horario = null;
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
      estado.vereds.concat(estado.grv).forEach(function (v) {      // o que o round real diz de cada comando: recusado (com botões) ou aplicado com aviso
        if (v.codigo === "ok" || v.codigo === "pendente" || !v.texto) return;
        if (v.codigo === "termina_depois_da_morte" && ehLancar(v.acao)) return;      // a granada não esmaece: o veredito dela (gr_depois_da_morte) é o que vale
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
      } else if (estado.grPend) {      // "qual granada?": um botão por granada do real, com o horário e o lugar reais
        var gp = estado.grPend, bg = el("div", "rw-cmd-pergunta", null, { role: "group", "aria-label": gp.texto, "data-codigo": "gr_qual" }), og = el("div", "rw-cmd-opcoes");
        bg.appendChild(el("p", "rw-cmd-pergunta-texto", gp.texto));
        gp.opcoes.forEach(function (r, i) {
          var b = el("button", "rw-btn rw-cmd-opcao", fmt(TX.cmd_gr_opcao, { granada: gp.g, h: N.relogioNo(r.f0), lugar: r.lugar ? " " + fmt(TX.em_lugar, { lugar: r.lugar }) : "" }), { type: "button", "data-i": String(i) });
          b.addEventListener("click", function () { gp.ac.gr_real = gp.ac.gr_real || {}; gp.ac.gr_real[gp.j.nick] = i; estado.msg = null; recalcula(); desenha(); foca(); });
          og.appendChild(b);
        });
        bg.appendChild(og); cartao.appendChild(bg);
      } else if (estado.plano && estado.plano.pergunta && todosOk()) {      // a saída do arremesso é longe, ou a peça só chega depois da hora: os botões da C4, sem "pôr a granada sem arremesso real" (isso é só da prancheta)
        var q = estado.plano.pergunta, tarde = q.tipo === "tarde", ac = estado.leitura.acoes[q.acao], quem1 = nickDe(q.quem);
        var qv = { quem: quem1, s: q.s, d: q.d, i: q.i, n: q.n, onde: q.onde, h: q.h };
        var texto = fmt(TX[tarde ? "cmd_gr_tarde" : "cmd_gr_longe"], qv), bq = el("div", "rw-cmd-pergunta", null, { role: "group", "aria-label": texto, "data-codigo": "gr_" + q.tipo }), oq = el("div", "rw-cmd-opcoes");
        bq.appendChild(el("p", "rw-cmd-pergunta-texto", texto));
        var opcao = function (rotulo, aoClicar) { var b = el("button", "rw-btn rw-cmd-opcao", rotulo, { type: "button" }); b.addEventListener("click", function () { aoClicar(); estado.msg = null; recalcula(); desenha(); foca(); }); oq.appendChild(b); };      // (var, não função em bloco: o site é ES5)
        if (tarde) opcao(t("opcao_jogar_as", { h: q.h }), function () { ac.gr_tarde_ok = true; });
        else if (q.pode_levar) opcao(t("opcao_levar", { quem: j1(q.quem) }), function () { ac.gr_decisao = "levar"; });
        if (q.ha_outro) opcao(t("opcao_outro_arremesso"), function () { ac.gr_i = (ac.gr_i || 0) + 1; ac.gr_decisao = null; ac.gr_tarde_ok = false; });
        bq.appendChild(oq);
        if (!tarde && !q.pode_levar) bq.appendChild(el("p", "rw-cmd-aviso", TX.cmd_gr_andar));
        cartao.appendChild(bq);
      } else if (estado.plano && estado.plano.falta) {
        var f = estado.plano.falta;
        cartao.appendChild(el("p", "rw-cmd-erro", fmt(TX.cmd_andar, { quem: f.quem, alvo: f.alvo }), { role: "alert" }));
      } else if (estado.plano && estado.plano.problemas.length) {
        estado.plano.problemas.filter(function (m, i, v) { return v.indexOf(m) === i; }).forEach(function (m) { cartao.appendChild(el("p", "rw-cmd-erro", m, { role: "alert" })); });
      }
      if (temGranada() && pronta()) {      // os arremessos reais vêm de um arquivo à parte: dito dentro do cartão (que tem altura fixa)
        var be = G.biblioteca().estado;
        if (be === "erro") cartao.appendChild(el("p", "rw-cmd-erro", TX.erro, { role: "alert", id: "rw-cmd-gr-erro" }));
        else if (be === "carregando" || be === "nao") cartao.appendChild(el("p", "rw-cmd-aviso", t("ui_carregando_granadas"), { role: "status", id: "rw-cmd-gr-carregando" }));
      }
      if (estado.msg) cartao.appendChild(el("p", "rw-cmd-aviso", estado.msg, { role: "status" }));
      botoes();
    }

    /* ---------- entender e aplicar ---------- */
    function entende() {
      var texto = campo.value.trim();
      estado.msg = null; estado.horario = null;
      if (!P.editando()) { desenha(); return; }
      try { estado.leitura = texto ? RC.le(texto, ctx) : null; } catch (e) { estado.leitura = null; estado.msg = TX.cmd_corrija; }
      if (temGranada() && pronta()) G.pede(aoBiblioteca, true);      // uma frase nova tenta de novo a biblioteca que falhou
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
      var novas = {}, nomes = [], anda = {}, ultimo = P.round.frames - 1, trocas = [];
      // quem anda: quem tem um comando que não é granada, ou uma granada com [Levar até lá]. Quem só joga uma granada de PERTO do lugar de saída não anda (o plano ainda desenha o passinho até lá, que a trilha não leva).
      estado.leitura.acoes.forEach(function (ac) {
        ac.quem.forEach(function (q) {
          var j = jogador(q.lado, q.num);
          if (!j) return;
          if (ac.tipo !== "lancar") { anda[j.nick] = true; return; }
          var x = lancs.filter(function (a) { return a.acao === ac.indice && a.pid === j.nick; })[0];
          if (x && x.levar) anda[j.nick] = true;
          if (x && !x.sem && estado.escolhidas[ac.indice + ":" + j.nick]) trocas.push({ real: estado.escolhidas[ac.indice + ":" + j.nick], x: x, ac: ac, j: j });
        });
      });
      for (var k = 0; k < trocas.length; k++) {      // o arremesso sai da mão depois do fim do round: nada a trocar
        var f = Math.round(trocas[k].x.tSai * hz);
        if (f > ultimo) { estado.msg = fmt(TX.cmd_nao_aplicou_fim, { quem: fmt(TX.cmd_quem, { nick: trocas[k].j.nick, lado: trocas[k].j.lado.toUpperCase(), num: trocas[k].j.num }), h_cmd: N.relogioNo(f), h_fim: N.relogioNo(ultimo) }); desenha(); mostra(); return; }
      }
      estado.plano.ops.forEach(function (op) { if (op[0] === "cria_caminho" && anda[op[1].peca]) { var ps = paradasDe(op); if (ps.length) { novas[op[1].peca] = ps; nomes.push(op[1].peca); } } });
      if (!nomes.length && !trocas.length) { estado.msg = TX.cmd_nao_aplicou.replace("{quem}", ""); desenha(); mostra(); return; }
      var foto = C.foto(nomes), trocasAntes = G.foto(), feitos = [], falhou = null;
      nomes.forEach(function (nome) {
        if (falhou) return;
        var ps = novas[nome], antes = P.trilha.de(nome).filter(function (pa) { return pa.f < ps[0].f - 1e-6; });      // o que a peça já tinha ANTES deste comando fica; dali em diante vale o comando
        if (P.trilha.define(nome, antes.concat(ps), ps.map(function (pa) { return pa.f; }))) feitos.push(nome); else falhou = nome;
      });
      if (falhou) {
        if (feitos.length) { var sub = {}; feitos.forEach(function (n) { sub[n] = foto[n]; }); C.empurra(sub, ""); C.desfaz(); }      // tudo ou nada: o que já tinha entrado volta
        estado.msg = porQueNao(falhou, novas[falhou]); desenha(); mostra(); return;
      }
      trocas.forEach(function (tr) {      // cada granada trocada: o arremesso real sai da mão na hora do comando (ou na da chegada), do lugar de saída dele
        G.poeTroca(tr.real.n, tr.x.r, Math.round(tr.x.tSai * hz), tr.x.origem, { i: tr.x.i, total: tr.x.n, onde: tr.ac.alvo ? mundo.nomeDoAlvo(tr.ac.alvo) : "", levar: !!tr.x.levar });
      });
      var resumo = estado.leitura.acoes.filter(function (ac) { return ac.tipo !== "lancar"; }).map(linha).join("; ");      // a granada tem a sua linha ("troca a smoke das 1:12 ..."), dita pela troca
      C.empurra(foto, resumo ? fmt(TX.cmd_mudou, { linha: resumo }) : null, trocasAntes);
      estado.prof = C.profundidade();
      estado.leitura = null; estado.plano = null; estado.vereds = []; estado.grv = []; estado.grPend = null; estado.msg = TX.cmd_aplicado;
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
      if (desfez) { estado.leitura = null; estado.plano = null; estado.vereds = []; estado.grv = []; estado.grPend = null; estado.msg = TX.cmd_desfeito; } else if (estado.leitura) recalcula();
      desenha();
    }
    desenha();
    return { entende: entende, aoMudar: aoMudar, estado: function () { return { leitura: estado.leitura, plano: estado.plano, vereds: estado.vereds, grv: estado.grv, grPend: !!estado.grPend, lancs: lancs, pode: pode() }; } };
  }

  global.ComandosNoReescrever = { inicia: inicia };
})(typeof window !== "undefined" ? window : this);
