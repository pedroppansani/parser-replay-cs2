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
  function cmdNivel(alvo) { return alvo.andar === "baixo" && ANDARES.length > 1 ? 1 : 0; }
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
    return cmdT("q_sem");
  }
  /** Como o alvo se escreve na tela: o nome do Pedro (ponto, ou a área que ele apelidou, nos mapas conferidos) ou o nome da área que o botão "Lugares" desenha, com espaços ("Top of Mid"). */
  function cmdNomeDoAlvo(alvo) {
    return alvo.tipo === "area" ? (alvo.exibe || alvo.texto || alvo.nome) : alvo.nome + (alvo.qualificacao ? " (" + alvo.qualificacao + ")" : "");
  }
  /** A velocidade da estimativa: quem corre usa o TETO do jogo (250 u/s, medido no corpus), o que faz da linha reta um piso; andando e agachado seguem a velocidade de cada jeito. */
  function cmdVelocidadeDoPiso(pid, modo) { return modo === "correndo" ? cfg.comandos.velocidade_piso_correndo : velocidade(funcaoDe(pid), modo); }
  function cmdLinha(ac, plano) {
    var v = { quem: cmdQuem(ac), alvo: ac.alvo ? cmdNomeDoAlvo(ac.alvo) : cmdT("onde_vazio"), quando: cmdQuando(ac, plano),
              granada: ac.granada ? cmdT("granada_" + ac.granada) || ac.granada : "?", modo: ac.modo || "correndo", n: ac.espera_s };
    var chave = { lancar: "linha_lancar", mover: "linha_mover", segurar: "linha_segurar", esperar: "linha_esperar" }[ac.tipo] || "linha_incompleta";
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
  function cmdChaveDoAlvo(alvo) {
    return alvo.tipo === "ponto" ? (alvo.ids || [alvo.id]).map(function (id) { return parseInt(String(id).split(":")[1], 10); }).sort(function (a, b) { return a - b; }).join("+") : null;
  }
  function cmdAreaDoAlvo(alvo) { return alvo.tipo === "area" ? alvo.nome : (Tempos.areaDoTexto[alvo.lugar] || null); }
  /** O tempo real do corpus entre onde a peça está e o alvo, só para quem corre: entre pontos do Pedro, senão entre as áreas da demo; null = estimar. */
  function cmdTempoReal(pos, alvo, modo) {
    var T = Tempos.dados;
    if (!T || modo !== "correndo") return null;
    var kb = cmdChaveDoAlvo(alvo), ka = pos.chave || null;
    if (kb && !ka) {
      var d0 = T.raio_origem;
      Tempos.nos.forEach(function (n) { var d = Math.hypot(n[1] - pos.x, n[2] - pos.y); if (d <= d0) { d0 = d; ka = n[0]; } });
    }
    var linha = kb && ka && ka !== kb ? Tempos.pontos[ka + "|" + kb] : null;
    if (linha) return { fonte: "pontos", p25: linha[2], mediana: linha[3], p75: linha[4], casos: linha[5], partidas: linha[6] };
    var aa = pos.area || (typeof lugarDe === "function" ? lugarDe(pos.x, pos.y, pos.nivel || 0) : null), ab = cmdAreaDoAlvo(alvo);
    linha = aa && ab && aa !== ab ? Tempos.areas[aa + "|" + ab] : null;
    return linha ? { fonte: "areas", p25: linha[2], mediana: linha[3], p75: linha[4], casos: linha[5], partidas: linha[6] } : null;
  }

  /** Do que foi entendido às operações. Devolve { ops, chegadas, problemas, falta }: `falta` é a chegada que o site não estimou (troca de andar sem tempo
      real). `chegadas[i]` diz de onde veio o horário: "real" (a mediana do corpus, com a faixa e os casos) ou "estimado" (a linha reta na velocidade do jeito de
      andar: um PISO, não um palpite). A ordem é a do RELÓGIO, não a da escrita: cada comando com horário abre uma cadeia, e os que não têm ("depois", "junto",
      "espera") ficam presos ao comando anterior na escrita; as cadeias andam por horário e, no mesmo horário, na ordem em que foram escritas. Uma peça que ainda
      anda por um comando anterior parte do ponto por onde o plano a deixou naquele instante (interpolado em linha reta, como a prancheta toca): o caminho
      anterior termina ali e o novo segue dali. */
  function cmdPlano(leitura) {
    var ops = [], chegadas = {}, problemas = [], avisos = [], falta = null, trilha = {}, acaoFim = {}, EPS = 1e-6;
    var granadas = {}, inicios = {}, cortados = {}, pergunta = null, espera = false, livreEm = {};
    var passos = S.estado.passos;
    function interpola(pts, t) {
      for (var i = pts.length - 1; i > 0; i--) {
        if (t >= pts[i - 1].t - EPS) {
          var a = pts[i - 1], b = pts[i], f = b.t > a.t ? (t - a.t) / (b.t - a.t) : 1;
          return { x: a.x + (b.x - a.x) * f, y: a.y + (b.y - a.y) * f, nivel: f < 1 - EPS ? a.nivel : b.nivel, modo: b.modo };
        }
      }
      return null;
    }
    function posicaoEm(pid, t) {
      var tr = trilha[pid];
      if (tr) {
        var u = tr.pts, ultimo = u[u.length - 1];
        if (t >= ultimo.t - EPS) return { x: ultimo.x, y: ultimo.y, nivel: ultimo.nivel, t: t, chave: ultimo.chave, area: ultimo.area };
        var m = t >= u[0].t - EPS ? interpola(u, t) : null;
        if (m) return { x: m.x, y: m.y, nivel: m.nivel, t: t };
      }
      var q = quadroNoTempo(S.e3, t, CENTRO).pecas[pid];
      return q ? { x: q.x, y: q.y, nivel: q.nivel || 0, t: t } : null;
    }
    function anota(ac, pid, t0, fim) {
      var f = acaoFim[ac.indice] = acaoFim[ac.indice] || { pecas: {}, geral: null, inicio: null };
      f.pecas[pid] = fim; f.geral = fim; f.inicio = t0;
      livreEm[pid] = Math.max(livreEm[pid] || 0, fim); inicios[ac.indice] = t0;
    }
    /** A peça anda de `ini` (em t0) até `destino`. Cada peça tem UM caminho no plano (um `cria_caminho`): um comando novo acrescenta o ponto dela (ela fica onde chegou até t0); um que
        começa no meio de uma corrida do plano CORTA o caminho ali (os pontos de depois saem, com os comandos a que eles pertenciam, que o cartão marca como cortados) e segue dali. */
    function anda(ac, pid, t0, ini, destino) {
      destino.acao = ac.indice;
      var tr = trilha[pid];
      if (!tr) {
        var pts = [destino];
        if (baseReal() === null) pts.unshift({ t: t0, x: ini.x, y: ini.y, nivel: ini.nivel || 0, acao: ac.indice });   // a peça fica onde está até t0 e só então anda
        trilha[pid] = { pts: pts };
        ops = ops.concat(cortaReal(pid, t0), ancoraReal(pid, t0), [["cria_caminho", { peca: pid, pontos: null, trilha: trilha[pid] }]]);
        return;
      }
      var ultimo = tr.pts[tr.pts.length - 1];
      if (t0 < ultimo.t - EPS && t0 >= tr.pts[0].t - EPS) {
        var m = interpola(tr.pts, t0), cortadas = {}, primeira = null;
        tr.pts.forEach(function (p) {
          if (!(p.t > t0 + EPS)) return;
          if (primeira === null) primeira = p.acao;
          if (p.acao != null) cortadas[p.acao] = true;
        });
        // uma granada dessa peça que o plano já pôs DEPOIS do corte fica (nada some sem a pessoa ver), e o cartão avisa
        ops.forEach(function (op) {
          if (op[0] !== "cria_granada" || op[1].jogador !== pid || !(op[1].t > t0 + EPS)) return;
          avisos.push(cmdT("aviso_corte_granada", { n2: ac.indice + 1, n1: (primeira === null ? ac.indice : primeira) + 1, granada: String(cmdT("granada_" + op[1].arma) || op[1].arma).toLowerCase(), h: cmdDoRelogio(op[1].t) }));
        });
        tr.pts = tr.pts.filter(function (p) { return p.t < t0 - EPS; });
        tr.pts.push({ t: t0, x: m.x, y: m.y, nivel: m.nivel, modo: m.modo, acao: primeira }, destino);
        Object.keys(cortadas).forEach(function (k) { delete chegadas[k]; cortados[k] = ac.indice + 1; });     // a chegada que eles diziam não vale mais
      } else {
        if (baseReal() === null && t0 > ultimo.t + EPS) tr.pts.push({ t: t0, x: ultimo.x, y: ultimo.y, nivel: ultimo.nivel, acao: ac.indice });   // fica onde chegou até t0
        tr.pts.push(destino);
      }
    }
    /** "joga X em Y": o arremesso real da biblioteca (mesmo tipo e lado, que caiu perto), com a pergunta quando a saída é longe da peça ou ela só chega depois do horário. */
    function lanca(ac, pid, nome, t0, ini) {
      var lado = S.estado.pecas[pid].lado, busca = cmdBuscaReal(ac.granada, ac.alvo, lado, ini), aviso = cmdAvisoDeLado(ac.granada, lado, busca);
      if (aviso) avisos.push(aviso);
      if (busca.estado === "carregando") espera = true;
      var i = Math.min(ac.gr_i || 0, Math.max(0, busca.grupos.length - 1)), g = busca.grupos[i];
      if (g && ac.gr_decisao !== "sem") {
        var ox = g.r.origem[0], oy = g.r.origem[1], nivelO = nivelDoZ(g.r.origem[2]), perto = g.dist <= cmdGr().raio_saida, outroAndar = nivelO !== (ini.nivel || 0);
        var base = { acao: ac.indice, quem: nome, i: i + 1, n: busca.grupos.length, d: Math.round(g.dist), s: Math.max(1, Math.round(g.dist / cmdVelocidadeDoPiso(pid, "correndo"))), onde: lugarExibido(ox, oy, nivelO) || "", pode_levar: !outroAndar, ha_outro: i + 1 < busca.grupos.length };
        if (!perto && (ac.gr_decisao !== "levar" || outroAndar)) { pergunta = pergunta || Object.assign({ tipo: "longe" }, base); return; }
        var vel = cmdVelocidadeDoPiso(pid, "correndo"), livre = livreEm[pid] || 0, tSai = t0, inicio = t0 - Math.hypot(ox - ini.x, oy - ini.y) / vel;
        var iniS = posicaoEm(pid, Math.max(inicio, 0)) || ini, dur = Math.hypot(ox - iniS.x, oy - iniS.y) / vel;
        inicio = tSai - dur;
        if (inicio < livre - EPS) {                       // não dá tempo de chegar ao ponto do arremesso até o horário pedido
          var chegaTarde = Math.round((livre + dur) * 100) / 100;
          if (chegaTarde - t0 > 0.3 && !ac.gr_tarde_ok) { pergunta = pergunta || Object.assign({ tipo: "tarde", chega: chegaTarde, h: cmdDoRelogio(chegaTarde) }, base); return; }
          tSai = chegaTarde; inicio = livre;
        }
        if (tSai - inicio < 0.05) inicio = tSai - 0.05;
        var yaw = ((Math.round(g.r.yaw) % 360) + 360) % 360;
        anda(ac, pid, inicio, iniS, { t: tSai, x: ox, y: oy, nivel: nivelO, modo: "correndo", yaw: yaw, chave: null, area: null });
        ops.push(["cria_granada", { granada: novoId(), arma: ac.granada, passo: passos[marcoQueContem(tSai)].passo, nivel: nivelO, origem: [ox, oy],
                                    destino: g.r.destino.slice(0, 2), arremesso: g.r, t: Math.round(tSai * 100) / 100, jogador: pid }]);
        granadas[ac.indice] = { r: g.r, i: i + 1, n: busca.grupos.length, lado: lado, onde: base.onde, tSai: tSai, tCai: g.voo ? tSai + g.r.voo_s : null, levar: dur > 0.3 ? { chega: tSai } : null, quem: nome };
        anota(ac, pid, t0, tSai);
        return;
      }
      // sem arremesso real: a granada sai de onde o jogador está, como antes, e o cartão diz por quê
      ops.push(["cria_granada", { granada: novoId(), arma: ac.granada, passo: passos[marcoQueContem(t0)].passo, nivel: ini.nivel || 0, origem: [ini.x, ini.y],
                                  destino: [ac.alvo.x, ac.alvo.y], arremesso: null, t: t0, jogador: pid }]);
      granadas[ac.indice] = { sem: true, lado: lado, motivo: busca.estado === "carregando" ? "carregando" : busca.estado === "sem" ? "sem_biblioteca" : g ? "escolha" : "nenhum" };
      anota(ac, pid, t0, t0);
    }
    function executa(ac) {
      ac.quem.forEach(function (q) {
        var nome = q.lado.toUpperCase() + " " + q.num, pid = cmdPeca(q);
        if (!pid) { problemas.push(cmdT("erro_sem_peca", { quem: nome })); return; }
        var qd = ac.quando, t0 = null, ant = ac.indice > 0 ? acaoFim[ac.indice - 1] : null;
        if (qd && (qd.tipo === "relogio" || qd.tipo === "inicio")) t0 = qd.t_decorrido;
        else if (qd && qd.tipo === "depois") t0 = ant ? (ant.pecas[pid] != null ? ant.pecas[pid] : ant.geral) : null;
        else if (qd && qd.tipo === "junto") t0 = ant ? ant.inicio : null;
        else if (ac.tipo === "esperar" && qd && qd.tipo === "espera_ate") t0 = ant ? (ant.pecas[pid] != null ? ant.pecas[pid] : ant.geral) : null;
        if (t0 == null) { problemas.push(cmdT(qd ? "erro_inicio" : "erro_sem_horario", { quem: nome })); return; }
        t0 = Math.round(t0 * 100) / 100;
        var ini = posicaoEm(pid, t0);
        if (ac.tipo === "esperar") {
          anota(ac, pid, t0, qd && qd.tipo === "espera_ate" ? M3.SEGUNDOS_DO_ROUND - qd.segundos_restantes : t0 + (ac.espera_s || 0)); return;
        }
        if (!ini) { problemas.push(cmdT("erro_sem_peca", { quem: nome })); return; }
        if (ac.tipo === "lancar") { lanca(ac, pid, nome, t0, ini); return; }
        // mover e segurar: andar até o ponto (segurar é chegar e ficar)
        var modo = ac.modo || "correndo", nivel = cmdNivel(ac.alvo), chega, info = null;
        var real = cmdTempoReal(ini, ac.alvo, modo);
        if (real) {
          chega = Math.round((t0 + real.mediana) * 100) / 100;
          info = { tipo: "real", fonte: real.fonte, t: chega, t25: t0 + real.p25, t75: t0 + real.p75, casos: real.casos, partidas: real.partidas, duracao: real.mediana };
        } else if (nivel !== (ini.nivel || 0)) {
          if (ac.chegada_t == null) { falta = falta || { acao: ac.indice, quem: nome, alvo: cmdNomeDoAlvo(ac.alvo), t0: t0 }; return; }
          chega = ac.chegada_t;
        } else {
          chega = Math.round((t0 + Math.hypot(ac.alvo.x - ini.x, ac.alvo.y - ini.y) / cmdVelocidadeDoPiso(pid, modo)) * 100) / 100;
          info = { tipo: "estimado", t: chega };
        }
        if (chega <= t0) { problemas.push(cmdT("erro_inicio", { quem: nome })); return; }
        if (info) chegadas[ac.indice] = info;
        var destino = { t: chega, x: ac.alvo.x, y: ac.alvo.y, nivel: nivel, modo: modo, chave: cmdChaveDoAlvo(ac.alvo), area: cmdAreaDoAlvo(ac.alvo) };
        anda(ac, pid, t0, ini, destino);
        anota(ac, pid, t0, chega);
      });
    }
    // as cadeias: um comando com horário abre uma; os sem horário ficam presos ao comando anterior na escrita
    var cadeias = [], atual = null;
    leitura.acoes.forEach(function (ac) {
      var qd = ac.quando, explicito = qd && (qd.tipo === "relogio" || qd.tipo === "inicio");
      if (explicito || !atual) { atual = { t: explicito ? qd.t_decorrido : -Infinity, ordem: cadeias.length, acoes: [] }; cadeias.push(atual); }
      atual.acoes.push(ac);
    });
    cadeias.sort(function (a, b) { return a.t === b.t ? a.ordem - b.ordem : a.t - b.t; });
    cadeias.forEach(function (c) { c.acoes.forEach(executa); });
    // as operações levam só os campos que a prancheta conhece (sem a chave e a área, que servem à próxima viagem do plano)
    ops.forEach(function (op) {
      if (op[0] !== "cria_caminho" || !op[1].trilha) return;
      op[1].pontos = op[1].trilha.pts.slice().sort(function (p, q) { return p.t - q.t; }).map(function (p) { var o = { t: p.t, x: p.x, y: p.y, nivel: p.nivel }; if (p.modo) o.modo = p.modo; if (p.yaw !== undefined) o.yaw = p.yaw; return o; });
      delete op[1].trilha;
    });
    return { ops: ops, chegadas: chegadas, problemas: problemas, avisos: avisos, falta: falta, granadas: granadas, inicios: inicios, cortados: cortados, pergunta: pergunta, espera: espera };
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
    if (plano && plano.espera) raiz.appendChild(el("p", { class: "pr-cmd-aviso", id: "pr-cmd-carregando-granadas", role: "status", texto: cmdT("ui_carregando_granadas") }));
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
