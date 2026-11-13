  /* ---------------------------------------------------------------------
     ABA COMANDOS (C2, decisão 64): a pessoa escreve o que cada jogador faz, o site mostra o que ENTENDEU antes de mexer em qualquer coisa e só o
     "Aplicar" muda a tática -- num lote só, então um desfazer volta o comando inteiro. O leitor é `comandos/leitor.js` (puro); aqui ficam a tela, o
     plano (do que foi entendido para operações que a prancheta já tem: `cria_caminho` e `cria_granada`, nenhuma operação nova) e a pergunta da chegada.
     Tempo de corrida: ESTIMADO (linha reta e a velocidade medida, a mesma conta do traçado), dito na tela; o do corpus entra na C3. Troca de andar não é
     estimada: pergunta a chegada, em vez de usar a linha reta (decisão 64).
     --------------------------------------------------------------------- */
  var Cmd = { leitura: null, falta: null, mensagem: "", textoVisto: "" };
  var LADO_DA_FRASE = { tr: "t", ct: "ct" };

  function cmdFmt(tpl, v) { return String(tpl || "").replace(/\{(\w+)\}/g, function (_, k) { return v && v[k] != null ? v[k] : ""; }); }
  function cmdT(k, v) { return cmdFmt(cfg.comandos.textos[k], v); }
  function cmdRelogio(restante) { var t = Math.round(restante); return Math.floor(t / 60) + ":" + String(t % 60).padStart(2, "0"); }      // arredonda UMA vez, antes de separar minutos e segundos
  function cmdDoRelogio(t) { return cmdRelogio(Math.max(0, M3.SEGUNDOS_DO_ROUND - t)); }

  /** As dez fichas do banco como "jogadores" do leitor; a função vem da peça que já está no mapa (o leitor entende "o AWPer"). */
  function cmdContexto() {
    var jog = [];
    ["tr", "ct"].forEach(function (l) { for (var n = 1; n <= 5; n++) jog.push({ lado: l, num: n }); });
    Object.keys(S.estado.pecas).forEach(function (pid) {
      var p = S.estado.pecas[pid], j = jog.filter(function (x) { return LADO_DA_FRASE[x.lado] === p.lado && x.num === parseInt(p.rotulo, 10); })[0];
      var f = funcaoDe(pid);
      if (j && f) j.funcao = f;
    });
    return Object.assign({}, cfg.comandos, { jogadores: jog });
  }
  function cmdPeca(q) {
    var ids = Object.keys(S.estado.pecas).filter(function (pid) {
      var p = S.estado.pecas[pid];
      return p.lado === LADO_DA_FRASE[q.lado] && parseInt(p.rotulo, 10) === q.num;
    });
    return ids[0] || null;
  }
  function cmdQuem(ac) {
    return ac.quem.length ? ac.quem.map(function (q) { return q.resolvido === false || !q.lado ? (q.ref || cmdT("quem_vazio")) : q.lado.toUpperCase() + " " + q.num; }).join(" + ") : cmdT("quem_vazio");
  }
  function cmdQuando(ac, plano) {
    var q = ac.quando;
    if (!q) return cmdT("q_sem");
    if (q.tipo === "relogio") return cmdT("q_relogio", { h: cmdRelogio(q.segundos_restantes) });
    if (q.tipo === "inicio") return cmdT("q_inicio", { n: q.segundos });
    if (q.tipo === "depois") return plano && plano.inicios[ac.indice] != null ? cmdT("q_depois_h", { h: cmdDoRelogio(plano.inicios[ac.indice]) }) : cmdT("q_depois");   // o horário que ficou valendo
    if (q.tipo === "junto") return cmdT("q_junto");
    if (q.tipo === "agora") return plano && plano.inicios[ac.indice] != null ? cmdT("q_agora_h", { h: cmdDoRelogio(plano.inicios[ac.indice]) }) : cmdT("q_agora");      // "segura X até H" sem início
    return cmdT("q_sem");
  }
  /** Como o alvo se escreve na tela: o nome do Pedro (ponto, ou a área que ele apelidou, nos mapas conferidos) ou o nome da área que o botão "Lugares" desenha, com espaços ("Top of Mid"). */
  function cmdNomeDoAlvo(alvo) {
    return alvo.tipo === "area" ? (alvo.exibe || alvo.texto || alvo.nome) : alvo.nome + (alvo.qualificacao ? " (" + alvo.qualificacao + ")" : "");
  }
  function cmdLinha(ac, plano) {
    var v = { quem: cmdQuem(ac), alvo: ac.alvo ? cmdNomeDoAlvo(ac.alvo) : cmdT("onde_vazio"), quando: cmdQuando(ac, plano),
              granada: ac.granada ? cmdT("granada_" + ac.granada) || ac.granada : "?", modo: ac.modo || "correndo", n: ac.espera_s, fim: ac.fim ? cmdRelogio(ac.fim.segundos_restantes) : "" };
    var chave = { lancar: "linha_lancar", mover: "linha_mover", segurar: "linha_segurar", esperar: "linha_esperar" }[ac.tipo] || "linha_incompleta";
    if (ac.tipo === "segurar" && ac.fim) chave = "linha_segurar_ate";      // CR1d
    var texto = cmdFmt(cfg.comandos.textos[chave], v);
    var chegada = plano && plano.chegadas[ac.indice];
    if (plano && plano.cortados[ac.indice]) texto += " · " + cmdT("cortado_por", { n: plano.cortados[ac.indice] });      // a chegada que ele dizia não vale mais
    else if (chegada) texto += " · " + cmdChegada(chegada);
    var gr = plano && plano.granadas[ac.indice];
    return gr && gr.r ? texto + " · " + cmdTextoDaGranada(gr) : texto;
  }
  /** De onde veio o horário de chegada, dito na tela: tempo real (faixa, casos, partidas) ou estimado (com o fator de desvio do mapa, se houver). */
  function cmdChegada(c) {
    if (c.tipo === "real") {
      var h1 = cmdDoRelogio(c.t25), h2 = cmdDoRelogio(c.t75);
      // faixa que cabe num segundo só: "entre 1:24 e 1:24" não diz nada, então a frase vem sem o "entre"
      return cmdT((c.fonte === "pontos" ? "chegada_real_pontos" : "chegada_real_areas") + (h1 === h2 ? "_unico" : ""), { h1: h1, h2: h2, h: cmdDoRelogio(c.t), d: Math.round(c.duracao), n: c.casos, p: c.partidas });
    }
    return cmdT("chegada_piso", { h: cmdDoRelogio(c.t) });
  }

  /* ---------- os tempos reais de corrida (C3): a tabela do mapa vem num arquivo próprio, carregado só quando a aba abre pela primeira vez ---------- */
  var Tempos = { estado: "inicial", dados: null, pontos: {}, areas: {}, nos: [], areaDoTexto: {} };
  function cmdIndiceDosTempos(t) {
    Tempos.dados = t || null; Tempos.pontos = {}; Tempos.areas = {}; Tempos.nos = [];
    if (!t) return;
    t.pontos.forEach(function (r) { Tempos.pontos[r[0] + "|" + r[1]] = r; });
    t.areas.forEach(function (r) { Tempos.areas[r[0] + "|" + r[1]] = r; });
    Tempos.nos = t.nos;
  }
  /** O arquivo dos tempos chama Prancheta.recebeTempos(...). */
  function cmdTemposChegaram(t) {
    Tempos.estado = "pronta"; cmdIndiceDosTempos(t);
    if ($("pr-cmd-resultado")) cmdDesenha();
  }
  /** Abrir a aba pela primeira vez busca os tempos. Sem arquivo (a página gerada sozinha, nos testes) a tabela já vem no cfg; sem tabela, só estimado. */
  function cmdAbriuAba() {
    cmdCarregaPlano();
    if (Tempos.estado !== "inicial") return;
    (cfg.comandos.areas || []).forEach(function (a) { Tempos.areaDoTexto[a.texto] = a.nome; });
    if (cfg.comandos.tempos) { Tempos.estado = "pronta"; cmdIndiceDosTempos(cfg.comandos.tempos); return; }
    if (!cfg.comandos.tempos_arquivo) { Tempos.estado = "pronta"; return; }
    Tempos.estado = "carregando";
    var sc = document.createElement("script");
    sc.src = cfg.comandos.tempos_arquivo;
    sc.onerror = function () { Tempos.estado = "erro"; if ($("pr-cmd-resultado")) cmdDesenha(); };
    document.body.appendChild(sc);
  }

  /* ---------- o plano, o tempo real e a busca da granada real (CR1a): moram em `comandos/plano.js` (puro; o Reescrever vai usar o mesmo), carregado só quando a aba abre ----------
     Aqui ficam o "mundo" que o módulo recebe (o estado da tática, o relógio, as peças, os textos) e os nomes de sempre (`cmdPlano`, `cmdBuscaReal`...), agora finos. */
  var PlanoArq = { estado: "inicial", mod: null };
  function cmdMundo() {
    return {
      S: function () { return S; }, cfg: function () { return cfg; }, M3: function () { return M3; }, ANDARES: function () { return ANDARES; }, CENTRO: function () { return CENTRO; },
      Tempos: Tempos, t: cmdT, doRelogio: cmdDoRelogio, peca: cmdPeca, nomeDoAlvo: cmdNomeDoAlvo, ladoEscrito: cmdLadoEscrito,
      velocidade: velocidade, funcaoDe: funcaoDe, lugarExibido: lugarExibido, nivelDoZ: nivelDoZ, quadroNoTempo: quadroNoTempo, baseReal: baseReal, cortaReal: cortaReal,
      ancoraReal: ancoraReal, novoId: novoId, marcoQueContem: marcoQueContem,
      agora: function () { return Math.max(0, S.t || 0); },      // "desde agora": o marcador do tempo da prancheta
      lugarDe: function (x, y, nivel) { return typeof lugarDe === "function" ? lugarDe(x, y, nivel) : null; },
      bibliotecaPronta: function () { return typeof bibliotecaPronta === "function" ? bibliotecaPronta() : true; }
    };
  }
  /** O módulo, criado na primeira vez que alguém precisa (a página gerada sozinha o traz embutido; no site chega pelo arquivo quando a aba abre). */
  function cmdModulo() {
    if (!PlanoArq.mod && typeof PlanoDeComandos !== "undefined") PlanoArq.mod = PlanoDeComandos.cria(cmdMundo());
    return PlanoArq.mod;
  }
  function cmdCarregaPlano() {
    if (PlanoArq.estado !== "inicial") return;
    if (typeof PlanoDeComandos !== "undefined" || !cfg.comandos.plano_arquivo) { PlanoArq.estado = "pronta"; return; }
    PlanoArq.estado = "carregando";
    var sc = document.createElement("script");
    sc.src = cfg.comandos.plano_arquivo;
    sc.onload = function () { PlanoArq.estado = "pronta"; if ($("pr-cmd-resultado")) cmdDesenha(); };
    sc.onerror = function () { PlanoArq.estado = "erro"; if ($("pr-cmd-resultado")) cmdDesenha(); };
    document.body.appendChild(sc);
  }
  var PLANO_SEM_MODULO = function () { return { ops: [], chegadas: {}, problemas: [], avisos: [], falta: null, granadas: {}, inicios: {}, cortados: {}, pergunta: null, espera: true }; };
  function cmdPlano(leitura) { var m = cmdModulo(); return m ? m.plano(leitura) : PLANO_SEM_MODULO(); }
  function cmdBuscaReal(arma, alvo, lado, ini) { var m = cmdModulo(); return m ? m.buscaReal(arma, alvo, lado, ini) : { estado: "carregando", grupos: [], mesmo: 0, outro: 0 }; }
  function cmdEstadoDaBiblioteca() { var m = cmdModulo(); return m ? m.estadoDaBiblioteca() : "carregando"; }

  /** A pergunta que acabou de aparecer recebe o foco (o campo do horário ou a primeira opção), para quem usa o teclado. */
  function cmdFoco() {
    var alvo = document.querySelector("#pr-cmd-resultado .pr-cmd-horario") || document.querySelector("#pr-cmd-resultado .pr-cmd-opcao");
    if (alvo) alvo.focus();
  }
  /** A tática mudou (uma ficha entrou no mapa, um desfazer): o cartão que está na tela refaz o plano, sem roubar o foco de quem digita. */
  var cmdChave = "";
  /** Num round real as fichas têm o nome do jogador, não "TR 2": o cartão avisa, em vez de dizer só que a ficha não está no mapa. */
  function cmdNotaDoRound() {
    var dica = $("pr-cmd-dica"), nota = $("pr-cmd-round");
    if (!dica || !S.estado) return;
    var nomeadas = Object.keys(S.estado.pecas).some(function (pid) { return !/^[1-9]$/.test(String(S.estado.pecas[pid].rotulo)); });
    if (nomeadas && !nota) dica.parentNode.insertBefore(el("p", { class: "pr-cmd-aviso", id: "pr-cmd-round", texto: cmdT("ui_round") }), dica.nextSibling);
    else if (!nomeadas && nota) nota.parentNode.removeChild(nota);
  }
  function cmdAtualiza() {
    cmdNotaDoRound();
    // o "Aplicado…" vale até a tática mudar de novo (desfazer, outra edição): depois disso ele mentiria
    if (Cmd.mensagem && Cmd.aplicadoEm != null && S.doc && S.doc.operacoes.length !== Cmd.aplicadoEm) { Cmd.mensagem = ""; Cmd.aplicadoEm = null; cmdChave = ""; if ($("pr-cmd-resultado")) cmdDesenha(); }
    if (!Cmd.leitura || !$("pr-cmd-resultado")) return;
    var chave = S.doc ? S.doc.operacoes.length + ":" + Object.keys(S.estado.pecas).join() + ":" + cmdEstadoDaBiblioteca() : "";
    if (chave === cmdChave) return;
    cmdChave = chave;
    var ativo = document.activeElement && document.activeElement.id;
    if (ativo === "pr-cmd-horario") return;
    cmdDesenha();
  }

  function cmdEntende() {
    var area = $("pr-cmd-texto"), texto = area.value.trim();
    Cmd.mensagem = ""; Cmd.falta = null; Cmd.textoVisto = texto;
    Cmd.leitura = texto ? LeitorDeComandos.le(texto, cmdContexto()) : null;
    cmdChave = S.doc ? S.doc.operacoes.length + ":" + Object.keys(S.estado.pecas).join() + ":" + cmdEstadoDaBiblioteca() : "";
    cmdDesenha(); cmdFoco();
  }
  function cmdAplica() {
    var l = Cmd.leitura;
    if (!l || l.perguntas.length || l.naoEntendido.length) return;
    var plano = cmdPlano(l);
    if (plano.falta || plano.pergunta || plano.espera || plano.problemas.length || !plano.ops.length) { cmdDesenha(); return; }
    emiteLote(plano.ops);
    Cmd.aplicadoEm = S.doc.operacoes.length;
    Cmd.mensagem = cmdT("ok_aplicado", { n: plano.ops.length }); Cmd.leitura = null; $("pr-cmd-texto").value = ""; Cmd.textoVisto = "";
    cmdDesenha();
  }
  function cmdCorrige() { Cmd.leitura = null; Cmd.falta = null; Cmd.mensagem = ""; cmdDesenha(); var a = $("pr-cmd-texto"); a.focus(); a.select(); }
  function cmdResponde(indice, valor) {
    LeitorDeComandos.responde(Cmd.leitura, indice, valor, cmdContexto());
    cmdDesenha(); cmdFoco();
  }
  /** Os botões da pergunta da granada real: levar a peça até o ponto do arremesso, jogar às X, usar outro arremesso, pôr a granada sem arremesso real. */
  function cmdGranadaDecide(acao, escolha) {
    var ac = Cmd.leitura && Cmd.leitura.acoes[acao];
    if (!ac) return;
    if (escolha === "levar") ac.gr_decisao = "levar";
    else if (escolha === "tarde") ac.gr_tarde_ok = true;
    else if (escolha === "sem") ac.gr_decisao = "sem";
    else if (escolha === "outro") { ac.gr_i = (ac.gr_i || 0) + 1; ac.gr_decisao = null; ac.gr_tarde_ok = false; }
    cmdDesenha(); cmdFoco();
  }
  function cmdHorario(texto, aoAceitar) {
    var h = LeitorDeComandos.horario(texto, cmdContexto());
    if (!h || h.invalido || h.ambiguo) {
      Cmd.mensagem = h && h.ambiguo ? cmdT("pergunta_quando_segundos", { n: h.segundos }) + " " + cmdT("ui_horario") + "."
        : cmdT(h && h.invalido ? "pergunta_horario_invalido" : "pergunta_quando", { horario: h && h.segundos_restantes != null ? cmdRelogio(h.segundos_restantes) : "", trecho: texto });
      cmdDesenha(); return;
    }
    aoAceitar(h);
  }

  function cmdPerguntaDoHorario(texto, aoConfirmar) {
    var campo = el("input", { type: "text", id: "pr-cmd-horario", class: "pr-cmd-horario", placeholder: cmdT("ui_horario"), autocomplete: "off", "aria-label": texto });
    var vai = function () { cmdHorario(campo.value, aoConfirmar); };
    campo.addEventListener("keydown", function (e) { if (e.key === "Enter") { e.preventDefault(); vai(); } });
    return el("div", { class: "linha pr-cmd-linha-horario" }, [campo, el("button", { type: "button", class: "pr-cmd-confirmar", texto: cmdT("ui_confirmar"), onclick: vai })]);
  }

  function cmdDesenha() {
    var raiz = $("pr-cmd-resultado");
    if (!raiz) return;
    limpa(raiz);
    var l = Cmd.leitura, plano = null;
    if (!l) {
      raiz.appendChild(el("p", { class: "pr-dica", id: "pr-cmd-vazio", texto: Cmd.mensagem || cmdT("ui_vazio") }));
      $("pr-cmd-acoes").hidden = true;
      return;
    }
    var pronta = !l.perguntas.length && !l.naoEntendido.length;
    if (pronta) { plano = cmdPlano(l); if (plano.falta) Cmd.falta = plano.falta; else Cmd.falta = null; }
    var lista = el("ol", { class: "pr-cmd-entendi", id: "pr-cmd-entendi" });
    l.acoes.forEach(function (ac) { lista.appendChild(el("li", { texto: cmdLinha(ac, plano) })); });
    raiz.appendChild(el("h3", { class: "pr-cmd-sub", texto: cmdT("ui_entendi") }));
    raiz.appendChild(lista);
    // avisos que a leitura marcou (não impedem de aplicar, mas ficam na tela)
    l.avisos.forEach(function (a) {
      if (a.codigo === "palavra_sobrando") return;
      var ac = l.acoes[a.acao], base = { n: a.segundos != null ? a.segundos : "" };
      if (a.codigo === "duracao_imposta" || a.codigo === "ordem_invertida") raiz.appendChild(el("p", { class: "pr-cmd-aviso", texto: cmdT("aviso_" + a.codigo, base) }));
    });
    l.acoes.forEach(function (ac) {          // a granada sem arremesso real diz por quê (nunca em silêncio)
      var g = plano && plano.granadas[ac.indice];
      if (!g || !g.sem) return;
      var chave = { sem_biblioteca: "aviso_sem_biblioteca", nenhum: "aviso_sem_real", escolha: "aviso_origem" }[g.motivo];
      if (chave) raiz.appendChild(el("p", { class: "pr-cmd-aviso", id: "pr-cmd-origem", texto: cmdT(chave, { lado: cmdLadoEscrito(g.lado) }) }));
    });
    if (plano && plano.espera && PlanoArq.estado !== "carregando") raiz.appendChild(el("p", { class: "pr-cmd-aviso", id: "pr-cmd-carregando-granadas", role: "status", texto: cmdT("ui_carregando_granadas") }));
    if (plano) plano.avisos.filter(function (m, i, v) { return v.indexOf(m) === i; }).forEach(function (m) { raiz.appendChild(el("p", { class: "pr-cmd-aviso", "data-aviso": "corte", texto: m })); });
    l.acoes.forEach(function (ac) {          // horário fixo: diz de qual comando fala e, se ele corta outros, quais
      if (!ac.depende_do_deslocamento) return;
      var h = plano && plano.inicios[ac.indice] != null ? cmdDoRelogio(plano.inicios[ac.indice]) : ac.quando && ac.quando.tipo === "relogio" ? cmdRelogio(ac.quando.segundos_restantes) : "";
      var cortados = plano ? Object.keys(plano.cortados).filter(function (k) { return plano.cortados[k] === ac.indice + 1; }).map(function (k) { return +k + 1; }) : [];
      var v = { n: ac.indice + 1, h: h, quem: cmdQuem(ac) };
      if (cortados.length) v.os_comandos = (cortados.length === 1 ? "o comando " : "os comandos ") + cortados.slice(0, -1).join(", ") + (cortados.length > 1 ? " e " : "") + cortados[cortados.length - 1];
      raiz.appendChild(el("p", { class: "pr-cmd-aviso", texto: cmdT(cortados.length ? "aviso_horario_fixo_corta" : "aviso_depende_do_deslocamento", v) }));
    });
    if (l.naoEntendido.length) {
      raiz.appendChild(el("p", { class: "pr-cmd-aviso", texto: cmdT("aviso_palavra_sobrando", { trechos: l.naoEntendido.map(function (x) { return "“" + x.trecho + "”"; }).join(", ") }) + " " + cmdT("ui_corrija") }));
    }
    // a pergunta da vez (uma de cada vez)
    var p = l.perguntas[0];
    if (p) {
      var bloco = el("div", { class: "pr-cmd-pergunta", role: "group", "aria-label": p.texto }, [el("p", { class: "pr-cmd-pergunta-texto", texto: p.texto })]);
      if (p.codigo === "quando" || p.codigo === "horario_invalido") {
        bloco.appendChild(cmdPerguntaDoHorario(p.texto, function (h) { cmdResponde(0, { quando: h }); }));
      } else if (p.opcoes && p.opcoes.length) {
        var opcoes = el("div", { class: "linha pr-cmd-opcoes" });
        p.opcoes.forEach(function (o, i) { opcoes.appendChild(el("button", { type: "button", class: "pr-cmd-opcao", "data-i": String(i), texto: o.rotulo, onclick: function () { cmdResponde(0, o.valor); } })); });
        bloco.appendChild(opcoes);
      } else bloco.appendChild(el("p", { class: "pr-dica", texto: cmdT("ui_corrija") }));
      raiz.appendChild(bloco);
    } else if (Cmd.falta) {
      var f = Cmd.falta;
      var b2 = el("div", { class: "pr-cmd-pergunta", role: "group" }, [el("p", { class: "pr-cmd-pergunta-texto", texto: cmdT("pergunta_chegada", { quem: f.quem, alvo: f.alvo }) })]);
      b2.appendChild(cmdPerguntaDoHorario(cmdT("pergunta_chegada", { quem: f.quem, alvo: f.alvo }), function (h) {
        if (h.t_decorrido == null || h.t_decorrido <= f.t0) { Cmd.mensagem = cmdT("erro_inicio", { quem: f.quem }); cmdDesenha(); return; }
        Cmd.leitura.acoes[f.acao].chegada_t = h.t_decorrido; Cmd.mensagem = ""; cmdDesenha(); $("pr-cmd-aplicar").focus();
      }));
      raiz.appendChild(b2);
    } else if (plano && plano.pergunta) {
      var q = plano.pergunta, textoQ = q.tipo === "tarde" ? cmdT("pergunta_granada_tarde", q) : cmdT("pergunta_granada_longe", q);
      var b3 = el("div", { class: "pr-cmd-pergunta", id: "pr-cmd-pergunta-granada", role: "group", "aria-label": textoQ }, [el("p", { class: "pr-cmd-pergunta-texto", texto: textoQ })]);
      var ops3 = el("div", { class: "linha pr-cmd-opcoes" });
      var botoes = [];
      if (q.tipo === "tarde") botoes.push(["tarde", cmdT("opcao_jogar_as", q)]);
      else if (q.pode_levar) botoes.push(["levar", cmdT("opcao_levar", q)]);
      if (q.ha_outro) botoes.push(["outro", cmdT("opcao_outro_arremesso")]);
      botoes.push(["sem", cmdT("opcao_sem_arremesso")]);
      botoes.forEach(function (b, i) { ops3.appendChild(el("button", { type: "button", class: "pr-cmd-opcao", "data-i": String(i), "data-escolha": b[0], texto: b[1], onclick: function () { cmdGranadaDecide(q.acao, b[0]); } })); });
      b3.appendChild(ops3); raiz.appendChild(b3);
    } else if (plano && plano.problemas.length) {
      plano.problemas.filter(function (m, i, v) { return v.indexOf(m) === i; }).forEach(function (m) { raiz.appendChild(el("p", { class: "pr-cmd-erro", role: "alert", texto: m })); });
    }
    if (PlanoArq.estado === "carregando") raiz.appendChild(el("p", { class: "pr-cmd-aviso", id: "pr-cmd-carregando-plano", role: "status", texto: cmdT("ui_carregando_plano") }));
    if (PlanoArq.estado === "erro") raiz.appendChild(el("p", { class: "pr-cmd-erro", id: "pr-cmd-sem-plano", role: "alert", texto: cmdT("aviso_plano_falhou") }));
    if (Tempos.estado === "carregando") raiz.appendChild(el("p", { class: "pr-cmd-aviso", id: "pr-cmd-carregando", role: "status", texto: cmdT("ui_carregando_tempos") }));
    if (Tempos.estado === "erro") raiz.appendChild(el("p", { class: "pr-cmd-aviso", id: "pr-cmd-sem-tempos", texto: cmdT("aviso_tempos_falhou") }));
    if (Cmd.mensagem) raiz.appendChild(el("p", { class: "pr-cmd-aviso", role: "status", texto: Cmd.mensagem }));
    var acoes = $("pr-cmd-acoes"); acoes.hidden = false;
    $("pr-cmd-aplicar").disabled = !(pronta && plano && !plano.falta && !plano.pergunta && !plano.espera && !plano.problemas.length && plano.ops.length) || Tempos.estado === "carregando";
  }

  /** O painel da aba, montado pelo `montaLateral`. */
  function montaComandos(painel) {
    var semNomes = !cfg.comandos.pontos.length;
    var area = el("textarea", { id: "pr-cmd-texto", class: "pr-cmd-texto", rows: "3", maxlength: "300", placeholder: cmdT("ui_exemplo"), "aria-describedby": "pr-cmd-dica" });
    area.addEventListener("keydown", function (e) { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); cmdEntende(); } });
    var nota = semNomes ? (cfg.comandos.areas.length ? cmdT("ui_sem_nomes") : cmdT("ui_sem_nenhum")) : "";
    var caixa = el("section", { class: "caixa pr-comandos", id: "pr-cmd" }, [
      el("h2", { texto: cmdT("ui_titulo") }),
      el("p", { class: "pr-dica", id: "pr-cmd-dica", texto: cmdT("ui_dica") }),
      nota ? el("p", { class: "pr-cmd-aviso", id: "pr-cmd-nomes", texto: nota }) : null,
      el("label", { class: "sr", for: "pr-cmd-texto", texto: cmdT("ui_rotulo") }),
      area,
      el("div", { class: "linha pr-cmd-barra" }, [el("button", { type: "button", id: "pr-cmd-entender", class: "pr-cmd-entender", texto: cmdT("ui_entender"), onclick: cmdEntende })]),
      el("div", { id: "pr-cmd-resultado", class: "pr-cmd-resultado", "aria-live": "polite" }),
      el("div", { id: "pr-cmd-acoes", class: "linha pr-cmd-acoes", hidden: "" }, [
        el("button", { type: "button", id: "pr-cmd-aplicar", class: "pr-cmd-aplicar", texto: cmdT("ui_aplicar"), onclick: cmdAplica }),
        el("button", { type: "button", id: "pr-cmd-corrigir", class: "pr-cmd-corrigir", texto: cmdT("ui_corrigir"), onclick: cmdCorrige })])
    ]);
    painel.appendChild(caixa);
    cmdNotaDoRound(); cmdDesenha();
  }
