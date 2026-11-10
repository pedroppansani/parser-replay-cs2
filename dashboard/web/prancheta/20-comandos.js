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
  function cmdRelogio(restante) { return Math.floor(restante / 60) + ":" + String(Math.round(restante) % 60).padStart(2, "0"); }
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
  function cmdNivel(alvo) { return alvo.andar === "baixo" && ANDARES.length > 1 ? 1 : 0; }
  function cmdQuem(ac) {
    return ac.quem.length ? ac.quem.map(function (q) { return q.resolvido === false || !q.lado ? (q.ref || cmdT("quem_vazio")) : q.lado.toUpperCase() + " " + q.num; }).join(" + ") : cmdT("quem_vazio");
  }
  function cmdQuando(ac) {
    var q = ac.quando;
    if (!q) return cmdT("q_sem");
    if (q.tipo === "relogio") return cmdT("q_relogio", { h: cmdRelogio(q.segundos_restantes) });
    if (q.tipo === "inicio") return cmdT("q_inicio", { n: q.segundos });
    if (q.tipo === "depois") return cmdT("q_depois");
    if (q.tipo === "junto") return cmdT("q_junto");
    return cmdT("q_sem");
  }
  function cmdLinha(ac, plano) {
    var v = { quem: cmdQuem(ac), alvo: ac.alvo ? ac.alvo.nome + (ac.alvo.qualificacao ? " (" + ac.alvo.qualificacao + ")" : "") : cmdT("onde_vazio"), quando: cmdQuando(ac),
              granada: ac.granada ? cmdT("granada_" + ac.granada) || ac.granada : "?", modo: ac.modo || "correndo", n: ac.espera_s };
    var chave = { lancar: "linha_lancar", mover: "linha_mover", segurar: "linha_segurar", esperar: "linha_esperar" }[ac.tipo] || "linha_incompleta";
    var texto = cmdFmt(cfg.comandos.textos[chave], v);
    var chegada = plano && plano.chegadas[ac.indice];
    return chegada != null ? texto + " · " + cmdT("chegada", { h: cmdDoRelogio(chegada) }) : texto;
  }

  /** Do que foi entendido às operações. Devolve { ops, chegadas, problemas, falta }: `falta` é a chegada que o site não estimou (troca de andar). */
  function cmdPlano(leitura) {
    var ops = [], chegadas = {}, problemas = [], falta = null, fim = {}, pos = {}, inicioAnterior = null, fimGeral = null;
    var passos = S.estado.passos;
    function posicaoEm(pid, t) {
      if (pos[pid] && t >= pos[pid].t - 1e-9) return pos[pid];
      var q = quadroNoTempo(S.e3, t, CENTRO).pecas[pid];
      return q ? { x: q.x, y: q.y, nivel: q.nivel || 0, t: t } : null;
    }
    leitura.acoes.forEach(function (ac) {
      ac.quem.forEach(function (q) {
        var nome = q.lado.toUpperCase() + " " + q.num, pid = cmdPeca(q);
        if (!pid) { problemas.push(cmdT("erro_sem_peca", { quem: nome })); return; }
        var qd = ac.quando, t0 = null;
        if (qd && (qd.tipo === "relogio" || qd.tipo === "inicio")) t0 = qd.t_decorrido;
        else if (qd && qd.tipo === "depois") t0 = fim[pid] != null ? fim[pid] : fimGeral;
        else if (qd && qd.tipo === "junto") t0 = inicioAnterior;
        else if (ac.tipo === "esperar" && qd && qd.tipo === "espera_ate") t0 = fim[pid] != null ? fim[pid] : fimGeral;
        if (t0 == null) { problemas.push(cmdT(qd ? "erro_inicio" : "erro_sem_horario", { quem: nome })); return; }
        t0 = Math.round(t0 * 100) / 100;
        inicioAnterior = t0;
        var ini = posicaoEm(pid, t0);
        if (ac.tipo === "esperar") {
          fim[pid] = qd && qd.tipo === "espera_ate" ? M3.SEGUNDOS_DO_ROUND - qd.segundos_restantes : t0 + (ac.espera_s || 0); fimGeral = fim[pid]; return;
        }
        if (!ini) { problemas.push(cmdT("erro_sem_peca", { quem: nome })); return; }
        if (ac.tipo === "lancar") {
          ops.push(["cria_granada", { granada: novoId(), arma: ac.granada, passo: passos[marcoQueContem(t0)].passo, nivel: ini.nivel || 0, origem: [ini.x, ini.y],
                                      destino: [ac.alvo.x, ac.alvo.y], arremesso: null, t: t0, jogador: pid }]);
          fim[pid] = t0; fimGeral = t0; return;
        }
        // mover e segurar: andar até o ponto (segurar é chegar e ficar)
        var nivel = cmdNivel(ac.alvo), chega;
        if (nivel !== (ini.nivel || 0)) {
          if (ac.chegada_t == null) { falta = falta || { acao: ac.indice, quem: nome, alvo: ac.alvo.nome, t0: t0 }; return; }
          chega = ac.chegada_t;
        } else {
          chega = Math.round((t0 + Math.hypot(ac.alvo.x - ini.x, ac.alvo.y - ini.y) / velocidade(funcaoDe(pid), ac.modo || "correndo")) * 100) / 100;
          chegadas[ac.indice] = chega;
        }
        if (chega <= t0) { problemas.push(cmdT("erro_inicio", { quem: nome })); return; }
        var pontos = [{ t: chega, x: ac.alvo.x, y: ac.alvo.y, nivel: nivel, modo: ac.modo || "correndo" }];
        if (baseReal() === null) pontos.unshift({ t: t0, x: ini.x, y: ini.y, nivel: ini.nivel || 0 });   // a peça fica onde está até t0 e só então anda
        ops = ops.concat(cortaReal(pid, t0), ancoraReal(pid, t0), [["cria_caminho", { peca: pid, pontos: pontos }]]);
        pos[pid] = { x: ac.alvo.x, y: ac.alvo.y, nivel: nivel, t: chega }; fim[pid] = chega; fimGeral = chega;
      });
    });
    return { ops: ops, chegadas: chegadas, problemas: problemas, falta: falta };
  }

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
    if (!Cmd.leitura || !$("pr-cmd-resultado")) return;
    var chave = S.doc ? S.doc.operacoes.length + ":" + Object.keys(S.estado.pecas).join() : "";
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
    cmdChave = S.doc ? S.doc.operacoes.length + ":" + Object.keys(S.estado.pecas).join() : "";
    cmdDesenha(); cmdFoco();
  }
  function cmdAplica() {
    var l = Cmd.leitura;
    if (!l || l.perguntas.length || l.naoEntendido.length) return;
    var plano = cmdPlano(l);
    if (plano.falta || plano.problemas.length || !plano.ops.length) { cmdDesenha(); return; }
    emiteLote(plano.ops);
    Cmd.mensagem = cmdT("ok_aplicado", { n: plano.ops.length }); Cmd.leitura = null; $("pr-cmd-texto").value = ""; Cmd.textoVisto = "";
    cmdDesenha();
  }
  function cmdCorrige() { Cmd.leitura = null; Cmd.falta = null; Cmd.mensagem = ""; cmdDesenha(); var a = $("pr-cmd-texto"); a.focus(); a.select(); }
  function cmdResponde(indice, valor) {
    LeitorDeComandos.responde(Cmd.leitura, indice, valor, cmdContexto());
    cmdDesenha(); cmdFoco();
  }
  function cmdHorario(texto, aoAceitar) {
    var h = LeitorDeComandos.horario(texto, cmdContexto());
    if (!h || h.invalido || h.ambiguo) { Cmd.mensagem = cmdT(h && h.invalido ? "pergunta_horario_invalido" : "pergunta_quando", { horario: h && h.segundos_restantes != null ? cmdRelogio(h.segundos_restantes) : "", trecho: texto }); cmdDesenha(); return; }
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
    if (l.acoes.some(function (ac) { return ac.tipo === "lancar"; })) raiz.appendChild(el("p", { class: "pr-cmd-aviso", id: "pr-cmd-origem", texto: cmdT("aviso_origem") }));
    l.acoes.forEach(function (ac) { if (ac.depende_do_deslocamento) raiz.appendChild(el("p", { class: "pr-cmd-aviso", texto: cmdT("aviso_depende_do_deslocamento") })); });
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
    } else if (plano && plano.problemas.length) {
      plano.problemas.filter(function (m, i, v) { return v.indexOf(m) === i; }).forEach(function (m) { raiz.appendChild(el("p", { class: "pr-cmd-erro", role: "alert", texto: m })); });
    }
    if (Cmd.mensagem) raiz.appendChild(el("p", { class: "pr-cmd-aviso", role: "status", texto: Cmd.mensagem }));
    var acoes = $("pr-cmd-acoes"); acoes.hidden = false;
    $("pr-cmd-aplicar").disabled = !(pronta && plano && !plano.falta && !plano.problemas.length && plano.ops.length);
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
