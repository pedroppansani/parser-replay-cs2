/* =========================================================================
   A SALA de um grupo da prancheta (fase 13, item 13.2): só TRANSPORTE.

   A sala leva e traz as operações que a prancheta já tem (decisões 32 e 35);
   não conhece peça, granada nem passo, e não muda operação nenhuma. A ordem
   total continua a do log (Lamport + autor + id), aplicada pela prancheta.

   Uma interface, duas implementações -- a prancheta (via grupo.js) não sabe
   qual está usando:
     SalaSupabase  a real: Postgres + Realtime + login anônimo do Supabase.
     SalaFalsa     em memória, para os testes: simula o servidor INCLUSIVE as
                   recusas do RLS (as mesmas regras de supabase/migrations), o
                   atraso, a ordem embaralhada de entrega e a queda da conexão.

   Contrato (tudo devolve Promise):
     prepara()                 -> uid (login anônimo; nenhum pedido antes disto)
     criar({mapa, cabecalho})  -> {sala_id, codigo}
     entrar(codigo, nick)      -> {ok, motivo?, sala_id, codigo, mapa, cabecalho, lider,
                                   todos_podem_desenhar, encerrada}
     operacoes(desde?)         -> [{id, autor, lamport, op, criada_em}] em ordem de chegada
                                  (desde = {lamport, criada_em}: só as posteriores, ver abaixo)
     envia([{lamport, op}])    -> {ok: true} | {ok: false, motivo}
                                  motivo: permissao | ritmo | tamanho | invalida | duplicada | rede
     sala(), membros()         -> o que o RLS deixa ler agora
     permite(usuario, sim), todosPodem(sim), expulsa(usuario), transfere(usuario),
     encerra(), sai()          -> {ok, motivo?}
     conecta(ouvintes)         ouvintes: aoReceber(linha), aoMudar(aviso), aoPresenca([uid]),
                                  aoCabecote(estado), aoConexao("conectado" | "caiu")
     anunciaCabecote(estado)   (só a líder; o servidor recusa os outros)
     desconecta()
   ========================================================================= */
var Sala = (function () {
  "use strict";

  // Limites: os MESMOS números de supabase/migrations (teste em tests/test_grupos_migracoes.py).
  var MAX_MEMBROS = 10;                 // pedido da fase 13 (13.1)
  var MAX_OPS_POR_SEGUNDO = 20;         // proposta da fase 13 (13.1): o gatilho de ritmo do banco
  var MAX_BYTES_DA_OPERACAO = 8192;     // 8 KB no texto do jsonb (check operacao_ate_8kb)
  var MAX_ERROS_DE_CODIGO = 5;          // em 10 minutos, por pessoa (entrar_na_sala)
  var JANELA_DOS_ERROS_MS = 10 * 60 * 1000;
  var MAX_SALAS_POR_HORA = 5;           // gatilho antes_de_criar_sala
  // Na reconexão, além das operações com Lamport acima do último recebido, as
  // gravadas desde (a última recebida − esta folga): uma operação de quem estava
  // atrasado pode ter Lamport menor e chegar ao servidor depois (o relógio de
  // Lamport não é o horário). A folga cobre a demora de uma transação.
  var FOLGA_DA_RECONEXAO_MS = 60 * 1000;
  var ALFABETO = "ABCDEFGHJKMNPQRSTUVWXYZ23456789";   // 31, sem 0/O e 1/I/L (13.1)
  var NICK_VALIDO = /^[A-Za-z0-9À-ÖØ-öø-ÿ _.-]{1,24}$/;   // o check de membros.nick

  /** O tamanho da operação como o banco mede: o texto do jsonb, com ", " e ": "
      (é maior que o JSON.stringify compacto). Mede antes de enviar. */
  function tamanhoNoServidor(v) {
    function txt(x) {
      if (x === null || x === undefined) return "null";
      if (Array.isArray(x)) return "[" + x.map(txt).join(", ") + "]";
      if (typeof x === "object") {
        return "{" + Object.keys(x).filter(function (k) { return x[k] !== undefined; })
          .map(function (k) { return JSON.stringify(k) + ": " + txt(x[k]); }).join(", ") + "}";
      }
      return JSON.stringify(x);
    }
    return new TextEncoder().encode(txt(v)).length;
  }

  /* -------------------------------------------------------------------------
     SalaSupabase
     ------------------------------------------------------------------------- */
  /** opcoes: {url, chave, biblioteca (caminho do supabase-js, carregado SÓ aqui)} */
  function SalaSupabase(opcoes) {
    var cli = null, canal = null, eu = null, salaId = null;

    function carrega() {
      if (window.supabase && window.supabase.createClient) return Promise.resolve(window.supabase);
      return new Promise(function (ok, falha) {
        var s = document.createElement("script");
        s.src = opcoes.biblioteca;
        s.async = true;
        s.onload = function () { window.supabase ? ok(window.supabase) : falha(new Error("supabase-js não carregou")); };
        s.onerror = function () { falha(new Error("supabase-js não carregou")); };
        document.head.appendChild(s);
      });
    }
    function motivoDoErro(e) {
      if (!e) return null;
      var m = String(e.message || "") + " " + String(e.details || "") + " " + String(e.hint || "");
      if (/ritmo/.test(m)) return "ritmo";
      if (/operacao_ate_8kb/.test(m)) return "tamanho";
      if (/operacao_invalida/.test(m)) return "invalida";
      if (e.code === "23505") return "duplicada";
      if (e.code === "42501" || /row-level security|operacao_de_outro_autor/.test(m)) return "permissao";
      if (/sala_encerrada/.test(m)) return "encerrada";
      if (/muitas_salas/.test(m)) return "muitas_salas";
      return "rede";
    }
    function resultado(r) { return r.error ? { ok: false, motivo: motivoDoErro(r.error) } : { ok: true, dados: r.data }; }
    function rede(e) { return { ok: false, motivo: "rede", erro: String(e && e.message || e) }; }

    return {
      tipo: "supabase",
      prepara: function () {
        return carrega().then(function (lib) {
          cli = lib.createClient(opcoes.url, opcoes.chave, { auth: { persistSession: true, storageKey: "prancheta-grupo" } });
          return cli.auth.getSession();
        }).then(function (r) {
          if (r.data && r.data.session) return r.data.session.user;
          return cli.auth.signInAnonymously().then(function (x) {
            if (x.error) throw x.error;
            return x.data.user;
          });
        }).then(function (u) { eu = u.id; return eu; });
      },
      uid: function () { return eu; },
      criar: function (d) {
        return cli.from("salas").insert({ lider: eu, mapa: d.mapa, cabecalho: d.cabecalho }).select("id,codigo").single()
          .then(function (r) {
            if (r.error) return { ok: false, motivo: motivoDoErro(r.error) };
            return { ok: true, sala_id: r.data.id, codigo: r.data.codigo };
          }, rede);
      },
      entrar: function (codigo, nick) {
        return cli.rpc("entrar_na_sala", { p_codigo: codigo, p_nick: nick }).then(function (r) {
          if (r.error) return { ok: false, motivo: motivoDoErro(r.error) };
          if (r.data && r.data.ok) salaId = r.data.sala_id;
          return r.data;
        }, rede);
      },
      operacoes: function (desde) {
        var todas = [], PAGINA = 1000;
        function pagina(de) {
          var q = cli.from("operacoes").select("id,autor,lamport,op,criada_em").eq("sala_id", salaId);
          if (desde) {
            var limite = new Date(desde.criada_em - FOLGA_DA_RECONEXAO_MS).toISOString();   // criada_em em ms
            q = q.or("lamport.gt." + desde.lamport + ",criada_em.gt." + limite);
          }
          return q.order("id").range(de, de + PAGINA - 1).then(function (r) {
            if (r.error) throw r.error;
            todas = todas.concat(r.data);
            return r.data.length === PAGINA ? pagina(de + PAGINA) : todas;
          });
        }
        return pagina(0);
      },
      envia: function (linhas) {
        return cli.from("operacoes").insert(linhas.map(function (l) { return { sala_id: salaId, lamport: l.lamport, op: l.op }; }))
          .then(resultado, rede);
      },
      sala: function () {
        return cli.from("salas").select("id,codigo,lider,mapa,todos_podem_desenhar,encerrada").eq("id", salaId).maybeSingle()
          .then(function (r) { if (r.error) throw r.error; return r.data; });
      },
      membros: function () {
        return cli.from("membros").select("usuario,nick,pode_desenhar,entrou_em").eq("sala_id", salaId).order("entrou_em")
          .then(function (r) { if (r.error) throw r.error; return r.data; });
      },
      permite: function (usuario, sim) {
        return cli.from("membros").update({ pode_desenhar: !!sim }).eq("sala_id", salaId).eq("usuario", usuario).then(resultado, rede);
      },
      todosPodem: function (sim) {
        return cli.from("salas").update({ todos_podem_desenhar: !!sim }).eq("id", salaId).then(resultado, rede);
      },
      expulsa: function (usuario) {
        return cli.from("membros").delete().eq("sala_id", salaId).eq("usuario", usuario).then(resultado, rede);
      },
      transfere: function (usuario) {
        return cli.from("salas").update({ lider: usuario }).eq("id", salaId).then(resultado, rede);
      },
      encerra: function () { return cli.from("salas").update({ encerrada: true }).eq("id", salaId).then(resultado, rede); },
      sai: function () { return cli.from("membros").delete().eq("sala_id", salaId).eq("usuario", eu).then(resultado, rede); },
      conecta: function (o) {
        return cli.realtime.setAuth().then(function () {
          canal = cli.channel("sala:" + salaId, { config: { private: true, presence: { key: eu }, broadcast: { self: false } } })
            .on("postgres_changes", { event: "INSERT", schema: "public", table: "operacoes", filter: "sala_id=eq." + salaId },
                function (p) { o.aoReceber(p.new); })
            .on("broadcast", { event: "mudou" }, function (p) { o.aoMudar(p.payload); })
            .on("broadcast", { event: "cabecote" }, function (p) { o.aoCabecote(p.payload); })
            .on("presence", { event: "sync" }, function () { o.aoPresenca(Object.keys(canal.presenceState())); })
            .subscribe(function (estado) {
              if (estado === "SUBSCRIBED") { canal.track({ usuario: eu }); o.aoConexao("conectado"); }
              else if (estado === "CHANNEL_ERROR" || estado === "TIMED_OUT" || estado === "CLOSED") o.aoConexao("caiu");
            });
        });
      },
      anunciaCabecote: function (estado) {
        if (canal) canal.send({ type: "broadcast", event: "cabecote", payload: estado });
      },
      desconecta: function () { if (canal) { cli.removeChannel(canal); canal = null; } salaId = null; }
    };
  }

  /* -------------------------------------------------------------------------
     ServidorFalso + SalaFalsa: o servidor em memória dos testes. As regras são
     as de supabase/migrations, uma a uma (quem lê, quem escreve, 10 membros,
     20 por segundo, 8 KB, log imutável, expulso não volta, encerrada é só
     leitura, código de 8 do alfabeto sem ambíguos, 5 erros de código).
     ------------------------------------------------------------------------- */
  /** Gerador de números com semente (mulberry32): mesma semente, mesma ordem. */
  function aleatorio(semente) {
    var a = semente >>> 0;
    return function () {
      a = (a + 0x6D2B79F5) >>> 0;
      var t = a;
      t = Math.imul(t ^ (t >>> 15), t | 1);
      t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  }

  /** opcoes: {atrasoMs (resposta e entrega), embaralhaMs (atraso extra aleatório
      por entrega: muda a ordem de chegada), semente, agora (relógio em ms)} */
  function ServidorFalso(opcoes) {
    opcoes = opcoes || {};
    var rnd = aleatorio(opcoes.semente || 1);
    var agora = opcoes.agora || function () { return Date.now(); };
    var salas = {}, membros = {}, ops = [], expulsos = {}, tentativas = {}, criadas = {}, enviadasPor = {};
    var conexoes = [];     // {uid, sala, o (ouvintes), caida}
    var proximoId = 1, pedidos = [];
    var srv = {
      atrasoMs: opcoes.atrasoMs || 0,
      embaralhaMs: opcoes.embaralhaMs || 0,
      pedidos: pedidos,      // todo pedido feito (os testes conferem que não há nenhum sem grupo)
      ops: ops
    };
    function depois(fn) {
      return new Promise(function (ok) { setTimeout(function () { ok(fn()); }, srv.atrasoMs); });
    }
    function ehMembro(s, u) { return !!(membros[s] && membros[s][u]); }
    function podeDesenhar(s, u) {
      var x = salas[s];
      if (!x || x.encerrada) return false;
      if (x.lider === u) return true;
      var m = membros[s] && membros[s][u];
      return !!(m && (m.pode_desenhar || x.todos_podem_desenhar));
    }
    function entrega(c, fn) {
      var extra = srv.embaralhaMs ? rnd() * srv.embaralhaMs : 0;
      setTimeout(function () { if (!c.caida && conexoes.indexOf(c) >= 0) fn(); }, srv.atrasoMs + extra);
    }
    function avisa(s, aviso) {
      // o broadcast saído do banco: chega a quem está conectado ao canal (o expulso também, para saber)
      conexoes.forEach(function (c) { if (c.sala === s) entrega(c, function () { c.o.aoMudar(aviso); }); });
    }
    function presenca(s) {
      var online = conexoes.filter(function (c) { return c.sala === s && !c.caida; }).map(function (c) { return c.uid; });
      conexoes.forEach(function (c) { if (c.sala === s && !c.caida) entrega(c, function () { c.o.aoPresenca(online.slice()); }); });
    }
    function gera() {
      var c;
      do {
        c = "";
        for (var i = 0; i < 8; i++) c += ALFABETO[Math.floor(rnd() * ALFABETO.length)];
      } while (Object.keys(salas).some(function (k) { return salas[k].codigo === c; }));
      return c;
    }

    srv.chama = function (uid, nome, a) {
      pedidos.push(nome);
      return depois(function () { return srv[nome + "_"](uid, a); });
    };
    srv.criar_ = function (uid, d) {
      var h = (criadas[uid] || []).filter(function (t) { return t > agora() - 3600 * 1000; });
      if (h.length >= MAX_SALAS_POR_HORA) return { ok: false, motivo: "muitas_salas" };
      h.push(agora()); criadas[uid] = h;
      var id = "sala-" + (proximoId++);
      salas[id] = { id: id, codigo: gera(), lider: uid, mapa: d.mapa, cabecalho: JSON.parse(JSON.stringify(d.cabecalho)),
                    todos_podem_desenhar: false, encerrada: false };
      membros[id] = {};
      return { ok: true, sala_id: id, codigo: salas[id].codigo };
    };
    srv.entrar_ = function (uid, a) {
      var erros = (tentativas[uid] || []).filter(function (t) { return t > agora() - JANELA_DOS_ERROS_MS; });
      if (erros.length >= MAX_ERROS_DE_CODIGO) return { ok: false, motivo: "muitas_tentativas" };
      var codigo = String(a.codigo || "").trim().toUpperCase(), nick = String(a.nick || "").trim();
      var x = Object.keys(salas).map(function (k) { return salas[k]; }).filter(function (s) { return s.codigo === codigo; })[0];
      if (!x) { erros.push(agora()); tentativas[uid] = erros; return { ok: false, motivo: "nao_existe" }; }
      if (!ehMembro(x.id, uid)) {
        if (x.encerrada) return { ok: false, motivo: "encerrada" };
        if (expulsos[x.id + "|" + uid]) return { ok: false, motivo: "expulso" };
        if (!srv.semCheckDeNick && !NICK_VALIDO.test(nick)) return { ok: false, motivo: "nick_invalido" };
        var usados = Object.keys(membros[x.id]).map(function (u) { return membros[x.id][u].nick.toLowerCase(); });
        if (usados.indexOf(nick.toLowerCase()) >= 0) return { ok: false, motivo: "nick_em_uso" };
        if (Object.keys(membros[x.id]).length >= MAX_MEMBROS) return { ok: false, motivo: "sala_cheia" };
        membros[x.id][uid] = { usuario: uid, nick: nick, pode_desenhar: x.todos_podem_desenhar, entrou_em: proximoId++ };
        avisa(x.id, { tabela: "membros", evento: "INSERT", usuario: uid, pode_desenhar: x.todos_podem_desenhar });
      }
      return { ok: true, sala_id: x.id, codigo: x.codigo, mapa: x.mapa, cabecalho: JSON.parse(JSON.stringify(x.cabecalho)),
               lider: x.lider, todos_podem_desenhar: x.todos_podem_desenhar, encerrada: x.encerrada };
    };
    srv.operacoes_ = function (uid, a) {
      if (!ehMembro(a.sala, uid)) return [];
      var d = a.desde;
      return ops.filter(function (l) {
        return l.sala_id === a.sala && (!d || l.lamport > d.lamport || l.criada_em > d.criada_em - FOLGA_DA_RECONEXAO_MS);
      }).map(function (l) { return JSON.parse(JSON.stringify(l)); });
    };
    srv.envia_ = function (uid, a) {
      // a transação inteira passa ou não (o insert em lote do PostgREST)
      var lote = [];
      var feitas = (enviadasPor[uid] || []).filter(function (t) { return t > agora() - 1000; });
      for (var i = 0; i < a.linhas.length; i++) {
        var l = a.linhas[i], op = l.op;
        if (!op || typeof op.id !== "string" || typeof op.tipo !== "string" || typeof op.autor !== "string" ||
            typeof op.seq !== "number" || op.seq !== l.lamport) return { ok: false, motivo: "invalida" };
        if (tamanhoNoServidor(op) > MAX_BYTES_DA_OPERACAO) return { ok: false, motivo: "tamanho" };
        if (feitas.length + lote.length >= MAX_OPS_POR_SEGUNDO) return { ok: false, motivo: "ritmo" };
        if (!podeDesenhar(a.sala, uid)) return { ok: false, motivo: "permissao" };
        var repetida = ops.concat(lote).some(function (o) {
          return o.sala_id === a.sala && ((o.autor === uid && o.lamport === l.lamport) || o.op.id === op.id);
        });
        if (repetida) return { ok: false, motivo: "duplicada" };
        lote.push({ id: 0, sala_id: a.sala, autor: uid, lamport: l.lamport, op: JSON.parse(JSON.stringify(op)), criada_em: agora() });
      }
      lote.forEach(function (l) {
        l.id = proximoId++;
        ops.push(l);
        feitas.push(agora());
        // Postgres Changes: o RLS de leitura é conferido para cada assinante, na hora
        conexoes.forEach(function (c) {
          if (c.sala === a.sala) entrega(c, function () { if (ehMembro(a.sala, c.uid)) c.o.aoReceber(JSON.parse(JSON.stringify(l))); });
        });
      });
      enviadasPor[uid] = feitas;
      return { ok: true };
    };
    srv.sala_ = function (uid, a) {
      var x = salas[a.sala];
      if (!x || !(ehMembro(x.id, uid) || x.lider === uid)) return null;
      return { id: x.id, codigo: x.codigo, lider: x.lider, mapa: x.mapa, todos_podem_desenhar: x.todos_podem_desenhar, encerrada: x.encerrada };
    };
    srv.membros_ = function (uid, a) {
      if (!ehMembro(a.sala, uid)) return [];
      return Object.keys(membros[a.sala]).map(function (u) { return Object.assign({}, membros[a.sala][u]); })
        .sort(function (p, q) { return p.entrou_em - q.entrou_em; });
    };
    function soLider(uid, s) { return salas[s] && salas[s].lider === uid; }
    srv.permite_ = function (uid, a) {
      if (!soLider(uid, a.sala) || !ehMembro(a.sala, a.usuario)) return { ok: true, dados: [] };   // RLS: 0 linhas
      membros[a.sala][a.usuario].pode_desenhar = !!a.sim;
      avisa(a.sala, { tabela: "membros", evento: "UPDATE", usuario: a.usuario, pode_desenhar: !!a.sim });
      return { ok: true };
    };
    srv.todosPodem_ = function (uid, a) {
      var x = salas[a.sala];
      if (!soLider(uid, a.sala)) return { ok: true, dados: [] };
      if (x.encerrada) return { ok: false, motivo: "encerrada" };
      x.todos_podem_desenhar = !!a.sim;
      avisa(a.sala, { tabela: "salas", lider: x.lider, todos_podem_desenhar: x.todos_podem_desenhar, encerrada: x.encerrada });
      return { ok: true };
    };
    srv.expulsa_ = function (uid, a) {
      if (!soLider(uid, a.sala) || a.usuario === uid || !ehMembro(a.sala, a.usuario)) return { ok: true, dados: [] };
      delete membros[a.sala][a.usuario];
      expulsos[a.sala + "|" + a.usuario] = true;
      avisa(a.sala, { tabela: "membros", evento: "DELETE", usuario: a.usuario });
      return { ok: true };
    };
    srv.transfere_ = function (uid, a) {
      var x = salas[a.sala];
      if (!soLider(uid, a.sala)) return { ok: true, dados: [] };
      if (x.encerrada) return { ok: false, motivo: "encerrada" };
      if (!ehMembro(a.sala, a.usuario)) return { ok: false, motivo: "permissao" };
      x.lider = a.usuario;
      avisa(a.sala, { tabela: "salas", lider: x.lider, todos_podem_desenhar: x.todos_podem_desenhar, encerrada: x.encerrada });
      return { ok: true };
    };
    srv.encerra_ = function (uid, a) {
      var x = salas[a.sala];
      if (!soLider(uid, a.sala)) return { ok: true, dados: [] };
      x.encerrada = true;
      avisa(a.sala, { tabela: "salas", lider: x.lider, todos_podem_desenhar: x.todos_podem_desenhar, encerrada: true });
      return { ok: true };
    };
    srv.sai_ = function (uid, a) {
      if (!ehMembro(a.sala, uid) || soLider(uid, a.sala)) return { ok: true, dados: [] };
      delete membros[a.sala][uid];
      avisa(a.sala, { tabela: "membros", evento: "DELETE", usuario: uid });
      return { ok: true };
    };
    srv.conecta_ = function (uid, a) {
      if (!ehMembro(a.sala, uid)) return { ok: false, motivo: "permissao" };   // o canal privado recusa
      var c = { uid: uid, sala: a.sala, o: a.o, caida: false };
      conexoes.push(c);
      entrega(c, function () { c.o.aoConexao("conectado"); });
      presenca(a.sala);
      return { ok: true };
    };
    srv.desconecta_ = function (uid) {
      var antes = conexoes.length, salasDele = [];
      conexoes = conexoes.filter(function (c) { if (c.uid === uid) salasDele.push(c.sala); return c.uid !== uid; });
      salasDele.forEach(presenca);
      return antes !== conexoes.length;
    };
    srv.cabecote_ = function (uid, a) {
      if (!soLider(uid, a.sala)) return { ok: false, motivo: "permissao" };   // só a líder transmite (RLS)
      conexoes.forEach(function (c) {
        if (c.sala === a.sala && c.uid !== uid) entrega(c, function () { c.o.aoCabecote(JSON.parse(JSON.stringify(a.estado))); });
      });
      return { ok: true };
    };
    /** Os testes derrubam e religam a conexão de alguém: caída, nada chega e nada sai. */
    srv.derruba = function (uid) {
      conexoes.forEach(function (c) { if (c.uid === uid) { c.caida = true; c.o.aoConexao("caiu"); } });
      conexoes.filter(function (c) { return c.uid === uid; }).forEach(function (c) { presenca(c.sala); });
    };
    srv.religa = function (uid) {
      conexoes.forEach(function (c) {
        if (c.uid === uid && c.caida) { c.caida = false; entrega(c, function () { c.o.aoConexao("conectado"); }); presenca(c.sala); }
      });
    };
    srv.caido = function (uid) { return conexoes.some(function (c) { return c.uid === uid && c.caida; }); };
    return srv;
  }

  /** O cliente em memória: a mesma interface da SalaSupabase. */
  function SalaFalsa(servidor, opcoes) {
    opcoes = opcoes || {};
    var eu = opcoes.uid || null, salaId = null, conectado = false;
    function chama(nome, a) {
      if (servidor.caido(eu) && nome !== "conecta") {
        return new Promise(function (ok) { setTimeout(function () { ok({ ok: false, motivo: "rede" }); }, servidor.atrasoMs); });
      }
      return servidor.chama(eu, nome, Object.assign({ sala: salaId }, a || {}));
    }
    return {
      tipo: "falsa",
      prepara: function () {
        servidor.pedidos.push("prepara");
        if (!eu) eu = "anon-" + Math.random().toString(16).slice(2, 10);
        return Promise.resolve(eu);
      },
      uid: function () { return eu; },
      criar: function (d) { return chama("criar", d); },
      entrar: function (codigo, nick) {
        return chama("entrar", { codigo: codigo, nick: nick }).then(function (r) { if (r && r.ok) salaId = r.sala_id; return r; });
      },
      operacoes: function (desde) {
        if (servidor.caido(eu)) return Promise.reject(new Error("sem conexão"));
        return chama("operacoes", { desde: desde ? { lamport: desde.lamport, criada_em: desde.criada_em } : null });
      },
      envia: function (linhas) { return chama("envia", { linhas: linhas }); },
      sala: function () { return chama("sala"); },
      membros: function () { return chama("membros"); },
      permite: function (usuario, sim) { return chama("permite", { usuario: usuario, sim: sim }); },
      todosPodem: function (sim) { return chama("todosPodem", { sim: sim }); },
      expulsa: function (usuario) { return chama("expulsa", { usuario: usuario }); },
      transfere: function (usuario) { return chama("transfere", { usuario: usuario }); },
      encerra: function () { return chama("encerra"); },
      sai: function () { return chama("sai"); },
      conecta: function (o) { conectado = true; return chama("conecta", { o: o }); },
      anunciaCabecote: function (estado) { if (conectado) chama("cabecote", { estado: estado }); },
      desconecta: function () { conectado = false; servidor.desconecta_(eu); salaId = null; }
    };
  }

  return {
    SalaSupabase: SalaSupabase, SalaFalsa: SalaFalsa, ServidorFalso: ServidorFalso,
    tamanhoNoServidor: tamanhoNoServidor, aleatorio: aleatorio,
    MAX_MEMBROS: MAX_MEMBROS, MAX_OPS_POR_SEGUNDO: MAX_OPS_POR_SEGUNDO, MAX_BYTES_DA_OPERACAO: MAX_BYTES_DA_OPERACAO,
    NICK_VALIDO: NICK_VALIDO, ALFABETO: ALFABETO
  };
})();
