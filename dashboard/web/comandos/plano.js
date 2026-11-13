/* O plano dos comandos (CR1a): do que o leitor ENTENDEU (`comandos/leitor.js`) às operações, o tempo real de corrida do corpus (C3) e a busca da granada real (C4).
   Puro: nada de DOM nem de rede. Quem usa (a prancheta, e depois o Reescrever) entrega o "mundo" em que o plano acontece (`W`): o estado da tática, o relógio,
   as peças, os textos, a biblioteca e os tempos; `PlanoDeComandos.cria(W)` devolve as funções. O texto das funções abaixo veio da prancheta (`prancheta/20-comandos.js`
   e `20-comandos-granada.js`) SEM mudança: só o que elas liam do escopo da prancheta passou a vir de `W`, por funções com o mesmo nome (o bloco "O MUNDO").
   Carregado só quando a aba Comandos abre (arquivo `comandos/plano.js` no site; embutido na página gerada sozinha). Estilo ES5, como o resto do JS do site. */
(function (global) {
  "use strict";

  function cria(W) {
    // ---------- O MUNDO: o que as funções abaixo liam do escopo da prancheta. Os objetos que a prancheta troca no init (cfg, M3, ANDARES, CENTRO) são relidos a cada entrada. ----------
    var S = null, cfg = null, M3 = null, ANDARES = null, CENTRO = null, Tempos = W.Tempos;
    function sincroniza() { S = W.S(); cfg = W.cfg(); M3 = W.M3(); ANDARES = W.ANDARES(); CENTRO = W.CENTRO(); }
    function cmdT(k, v) { return W.t(k, v); }
    function cmdDoRelogio(t) { return W.doRelogio(t); }
    function cmdPeca(q) { return W.peca(q); }
    function cmdNomeDoAlvo(alvo) { return W.nomeDoAlvo(alvo); }
    function cmdLadoEscrito(lado) { return W.ladoEscrito(lado); }
    function velocidade(funcao, modo) { return W.velocidade(funcao, modo); }
    function funcaoDe(pid) { return W.funcaoDe(pid); }
    function lugarDe(x, y, nivel) { return W.lugarDe(x, y, nivel); }
    function lugarExibido(x, y, nivel) { return W.lugarExibido(x, y, nivel); }
    function nivelDoZ(z) { return W.nivelDoZ(z); }
    function bibliotecaPronta() { return W.bibliotecaPronta(); }
    function quadroNoTempo(e3, t, centro) { return W.quadroNoTempo(e3, t, centro); }
    function baseReal() { return W.baseReal(); }
    function cortaReal(pid, t0) { return W.cortaReal(pid, t0); }
    function ancoraReal(pid, t0) { return W.ancoraReal(pid, t0); }
    function novoId() { return W.novoId(); }
    function marcoQueContem(t) { return W.marcoQueContem(t); }
    function agora() { return W.agora(); }

    // ---------- o texto que veio da prancheta ----------
  function cmdNivel(alvo) { return alvo.andar === "baixo" && ANDARES.length > 1 ? 1 : 0; }

  /** A velocidade da estimativa: quem corre usa o TETO do jogo (250 u/s, medido no corpus), o que faz da linha reta um piso; andando e agachado seguem a velocidade de cada jeito. */
  function cmdVelocidadeDoPiso(pid, modo) { return modo === "correndo" ? cfg.comandos.velocidade_piso_correndo : velocidade(funcaoDe(pid), modo); }

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
        else if (qd && qd.tipo === "agora") t0 = ant ? (ant.pecas[pid] != null ? ant.pecas[pid] : ant.geral) : agora();      // "segura X até H" sem início
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
        var fimDaEspera = chega;
        if (ac.tipo === "segurar" && ac.fim) {      // CR1d: "segura X até H": chega, fica em X até H; o comando seguinte parte de H
          if (ac.fim.t_decorrido > chega + EPS) {
            fimDaEspera = ac.fim.t_decorrido;
            if (baseReal() === null) trilha[pid].pts.push({ t: fimDaEspera, x: destino.x, y: destino.y, nivel: destino.nivel, acao: ac.indice });      // fica onde chegou até H
          } else avisos.push(cmdT("aviso_segura_curto", { quem: nome, alvo: cmdNomeDoAlvo(ac.alvo), h: cmdDoRelogio(chega), fim: cmdDoRelogio(ac.fim.t_decorrido) }));
        }
        anota(ac, pid, t0, fimDaEspera);
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

  function cmdGr() { return cfg.comandos.granada; }

  /** "carregando" (o arquivo da biblioteca ainda não chegou), "sem" (o mapa não tem biblioteca) ou "ok". */
  function cmdEstadoDaBiblioteca() {
    if (cfg.biblioteca) return "ok";
    return typeof bibliotecaPronta === "function" && !bibliotecaPronta() ? "carregando" : "sem";
  }

  /** Os pontos do Pedro de um alvo (as duas TVs são um alvo só, com dois pontos). */
  function cmdPontosDoAlvo(alvo) {
    if (alvo.tipo !== "ponto") return [];
    var ids = alvo.ids || [alvo.id];
    var ps = cfg.comandos.pontos.filter(function (p) { return ids.indexOf(p.id) >= 0; });
    return ps.length ? ps : [{ x: alvo.x, y: alvo.y }];
  }

  /** A distância (xy) da queda ao alvo, ou null se não cai nele. */
  function cmdQuedaNoAlvo(r, alvo, pontos) {
    if (alvo.tipo === "area") {
      return lugarDe(r.destino[0], r.destino[1], nivelDoZ(r.destino[2])) === alvo.nome ? Math.hypot(r.destino[0] - alvo.x, r.destino[1] - alvo.y) : null;
    }
    var d = null;
    pontos.forEach(function (p) { var x = Math.hypot(r.destino[0] - p.x, r.destino[1] - p.y); if (d === null || x < d) d = x; });
    return d !== null && d <= cmdGr().raio_queda ? d : null;
  }

  /** Os arremessos reais de `arma` que caem no alvo, do lado da peça e do outro, e a lista de jogadas do lado certo ordenada pela peça em `ini`. */
  function cmdBuscaReal(arma, alvo, lado, ini) {
    var estado = cmdEstadoDaBiblioteca();
    if (estado !== "ok") return { estado: estado, grupos: [], mesmo: 0, outro: 0 };
    var pontos = cmdPontosDoAlvo(alvo), mesmo = [], outro = 0;
    cfg.biblioteca.arremessos.forEach(function (r) {
      if (r.arma !== arma) return;
      var d = cmdQuedaNoAlvo(r, alvo, pontos);
      if (d === null) return;
      if (r.lado === lado) mesmo.push({ r: r, d: d }); else outro++;
    });
    mesmo.sort(function (a, b) { return a.d - b.d || (a.r.id < b.r.id ? -1 : 1); });
    var grupos = [], saida = cmdGr().raio_saida;
    mesmo.forEach(function (x) {
      var g = grupos.filter(function (g) { return Math.hypot(g.r.origem[0] - x.r.origem[0], g.r.origem[1] - x.r.origem[1]) <= saida; })[0];
      if (g) g.jogadas++; else grupos.push({ r: x.r, d: x.d, jogadas: 1 });
    });
    grupos.forEach(function (g) { g.dist = Math.hypot(g.r.origem[0] - ini.x, g.r.origem[1] - ini.y); g.voo = g.r.voo_s !== null && g.r.voo_s !== undefined; });
    grupos.sort(function (a, b) {
      var fa = Math.floor(a.dist / 50), fb = Math.floor(b.dist / 50);
      return fa - fb || (a.voo === b.voo ? a.dist - b.dist : (a.voo ? -1 : 1));
    });
    return { estado: "ok", grupos: grupos, mesmo: mesmo.length, outro: outro };
  }

  /** O aviso de lado: poucos do lado certo e muitos do outro. Nunca usa o do outro lado. */
  function cmdAvisoDeLado(arma, lado, busca) {
    var g = cmdGr();
    if (busca.estado !== "ok" || busca.mesmo >= g.poucos || busca.outro < g.muitos) return null;
    var v = { n: busca.mesmo, arremessos: busca.mesmo === 1 ? "arremesso real" : "arremessos reais", lado: cmdLadoEscrito(lado), outro: cmdLadoEscrito(lado === "ct" ? "t" : "ct"),
              granada: String(cmdT("granada_" + arma) || arma).toLowerCase(), m: busca.outro };
    return cmdT(busca.mesmo ? "aviso_poucos_do_lado" : "aviso_nenhum_do_lado", v);
  }

    return {
      plano: function (leitura) { sincroniza(); return cmdPlano(leitura); },
      buscaReal: function (arma, alvo, lado, ini) { sincroniza(); return cmdBuscaReal(arma, alvo, lado, ini); },
      estadoDaBiblioteca: function () { sincroniza(); return cmdEstadoDaBiblioteca(); },
      tempoReal: function (pos, alvo, modo) { sincroniza(); return cmdTempoReal(pos, alvo, modo); }
    };
  }

  global.PlanoDeComandos = { cria: cria };
  if (typeof module !== "undefined" && module.exports) module.exports = global.PlanoDeComandos;
})(typeof window !== "undefined" ? window : this);
