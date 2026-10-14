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
     criar({mapa, cabecalho})  -> {sala_id, codigo}   (sala vazia; o caminho antigo, só o gatilho de criar sala vale)
     criaComEstado({mapa, nick, cabecalho, operacoes})
                               -> {ok, motivo?, sala_id, codigo, mapa, cabecalho, lider, todos_podem_desenhar, encerrada}
                                  cria a sala e entra como líder, com as operações da tática numa linha só (fase 16b)
     entrar(codigo, nick)      -> {ok, motivo?, sala_id, codigo, mapa, cabecalho, lider,
                                   todos_podem_desenhar, encerrada, operacoes_iniciais}
                                  (operacoes_iniciais: a primeira parte do log; depois vêm as de operacoes())
     operacoes(desde?)         -> [{id, autor, lamport, op, criada_em}] em ordem de chegada
                                  (desde = {lamport, criada_em}: só as posteriores, ver abaixo)
     envia([{lamport, op}])    -> {ok: true} | {ok: false, motivo}
                                  motivo: permissao | ritmo | tamanho | invalida | duplicada | rede |
                                          sala_no_limite | autor_no_limite
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
  // Tetos de uso (fase 16b, B-2 da revisão de segurança; supabase/migrations 6 e 7). O teto por sala é o maior
  // entre 5.000 operações / 2 MB e 4x o maior round real: o maior round do corpus (1.152 rounds abertos pela
  // "Abrir round na prancheta") tem 68 operações e 88.835 bytes; 4x = 272 operações e 355 KB.
  var MAX_OPS_POR_SALA = 5000;          // inclui o estado inicial
  var MAX_BYTES_POR_SALA = 2097152;     // 2 MB no texto do jsonb, estado inicial incluído
  var MAX_OPS_POR_MINUTO = 300;         // por autor (todas as salas)
  var MAX_OPS_POR_HORA = 3000;          // por autor (todas as salas)
  var MAX_SALAS_ATIVAS = 200;           // global: 200 salas x 2 MB = 400 MB, abaixo dos 500 MB do plano grátis
  var MAX_CHAMADAS_POR_MINUTO = 30;     // entrar_na_sala, por conta
  var SALTO_DE_LAMPORT = 1000;          // L-2: no máximo 1.000 acima do maior número de ordem da sala
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
      // os tetos de uso (fase 16b) primeiro: cada um tem o seu código
      if (/sala_no_limite/.test(m)) return "sala_no_limite";
      if (/autor_no_limite/.test(m)) return "autor_no_limite";
      if (/servidor_cheio/.test(m)) return "servidor_cheio";
      if (/sem_login/.test(m)) return "sem_login";
      if (/nick_invalido/.test(m)) return "nick_invalido";
      if (/mapa_invalido|estado_invalido/.test(m)) return "invalida";
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
          if (!(r.data && r.data.session)) return loginAnonimo();
          // A sessão guardada pode ser de um usuário anônimo que a limpeza diária apagou (L-5): o servidor confirma
          // antes de a usarmos. Se ele já não existe, a sessão local sai e o login anônimo é refeito sozinho, sem
          // erro na tela. Falha de REDE na conferência não é "usuário apagado": segue com a sessão (e o grupo
          // indisponível aparece como sempre).
          var guardado = r.data.session.user;
          return cli.auth.getUser().then(function (u) {
            var e = u && u.error;
            if (!e && u && u.data && u.data.user) return u.data.user;
            if (e && (e.name === "AuthRetryableFetchError" || e.status === 0 || e.status >= 500)) return guardado;
            return cli.auth.signOut({ scope: "local" }).then(loginAnonimo, loginAnonimo);
          }, function () { return guardado; });
        }).then(function (u) { eu = u.id; return eu; });
        function loginAnonimo() {
          return cli.auth.signInAnonymously().then(function (x) {
            if (x.error) throw x.error;
            return x.data.user;
          });
        }
      },
      uid: function () { return eu; },
      criar: function (d) {
        return cli.from("salas").insert({ lider: eu, mapa: d.mapa, cabecalho: d.cabecalho }).select("id,codigo").single()
          .then(function (r) {
            if (r.error) return { ok: false, motivo: motivoDoErro(r.error) };
            return { ok: true, sala_id: r.data.id, codigo: r.data.codigo };
          }, rede);
      },
      /** Cria o grupo COM o estado inicial numa linha só (rpc cria_sala; d: {mapa, nick, cabecalho, operacoes}) e
          entra nele como líder. Devolve o mesmo que `entrar`, sem as operações (quem criou já as tem). */
      criaComEstado: function (d) {
        return cli.rpc("cria_sala", { p_mapa: d.mapa, p_nick: d.nick, p_estado_inicial: { cabecalho: d.cabecalho, operacoes: d.operacoes } })
          .then(function (r) {
            if (r.error) return { ok: false, motivo: motivoDoErro(r.error) };
            if (r.data && r.data.ok) salaId = r.data.sala_id;
            return r.data;
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
      por entrega: muda a ordem de chegada), semente, agora (relógio em ms),
      compartilhado (chave do localStorage: o estado do servidor passa a viver ali, e duas páginas do mesmo
      navegador falam com o MESMO servidor falso -- é como os testes do link entre mapas funcionam sem rede)} */
  function ServidorFalso(opcoes) {
    opcoes = opcoes || {};
    var rnd = aleatorio(opcoes.semente || 1);
    var agora = opcoes.agora || function () { return Date.now(); };
    var salas = {}, membros = {}, ops = [], expulsos = {}, tentativas = {}, criadas = {}, enviadasPor = {}, chamadas = {};
    // os limites do servidor (os de supabase/migrations); os testes baixam um deles para chegar ao teto sem milhares de operações
    var lim = Object.assign({ maxSalasAtivas: MAX_SALAS_ATIVAS, maxOpsPorSala: MAX_OPS_POR_SALA, maxBytesPorSala: MAX_BYTES_POR_SALA,
                              maxOpsPorMinuto: MAX_OPS_POR_MINUTO, maxOpsPorHora: MAX_OPS_POR_HORA,
                              maxChamadasPorMinuto: MAX_CHAMADAS_POR_MINUTO }, opcoes.limites || {});
    // os tipos de operação que o servidor aceita (L-3): a lista da prancheta (Prancheta.grupo.tipos()); sem ela, qualquer um
    var tiposAceitos = opcoes.tipos || null;
    var conexoes = [];     // {uid, sala, o (ouvintes), caida}
    var proximoId = 1, pedidos = [];
    var chaveCompartilhada = opcoes.compartilhado || null;
    function guardado(acao, valor) {
      try {
        if (acao === "le") return window.localStorage.getItem(chaveCompartilhada);
        window.localStorage.setItem(chaveCompartilhada, valor);
      } catch (e) { /* sem armazenamento: cada página fica com o servidor só dela */ }
      return null;
    }
    function carrega() {
      var t = guardado("le");
      if (!t) return;
      var d = JSON.parse(t);
      salas = d.salas; membros = d.membros; expulsos = d.expulsos; tentativas = d.tentativas;
      criadas = d.criadas; enviadasPor = d.enviadasPor; proximoId = d.proximoId; chamadas = d.chamadas || {};
      ops.length = 0;
      d.ops.forEach(function (l) { ops.push(l); });
    }
    function salva() {
      guardado("grava", JSON.stringify({ salas: salas, membros: membros, expulsos: expulsos, tentativas: tentativas,
        criadas: criadas, enviadasPor: enviadasPor, proximoId: proximoId, chamadas: chamadas, ops: ops }));
    }
    var srv = {
      atrasoMs: opcoes.atrasoMs || 0,
      embaralhaMs: opcoes.embaralhaMs || 0,
      pedidos: pedidos,      // todo pedido feito (os testes conferem que não há nenhum sem grupo)
      ops: ops,              // as linhas da tabela operacoes (o estado inicial NÃO está aqui: ver inicialDe)
      limites: lim,
      trafego: [],           // {nome, bytes} de cada pedido (o corpo, em JSON): a medição de rede usa
      /** O estado inicial da sala (a primeira parte do log): as operações que a tática já tinha ao virar grupo. */
      inicialDe: function (sala) { return salas[sala] ? JSON.parse(JSON.stringify(salas[sala].operacoes_iniciais || [])) : []; },
      /** O total que o servidor conta para a sala (estado inicial incluído). */
      totaisDe: function (sala) { return { ops: salas[sala].total_ops || 0, bytes: salas[sala].total_bytes || 0 }; }
    };
    // A rede simulada (opcoes.rede = {latenciaMs, subidaBps, descidaBps}): cada pedido demora a latência mais o
    // tempo de SUBIR os bytes do pedido, e a resposta, o tempo de descer os dela. É um modelo, não rede de verdade:
    // serve para medir o cliente inteiro contra um servidor de rede conhecida (scripts/mede_criacao_do_grupo.py).
    var rede = opcoes.rede || null;
    function bytesDe(v) {
      try { return new TextEncoder().encode(JSON.stringify(v, function (k, x) { return typeof x === "function" ? undefined : x; }) || "").length; }
      catch (e) { return 0; }
    }
    function depois(fn, bytesDoPedido) {
      var ida = srv.atrasoMs + (rede ? rede.latenciaMs + bytesDoPedido * 8 / rede.subidaBps * 1000 : 0);
      return new Promise(function (ok) {
        setTimeout(function () {
          var r = fn();
          if (!rede) { ok(r); return; }
          setTimeout(function () { ok(r); }, bytesDe(r) * 8 / rede.descidaBps * 1000);
        }, ida);
      });
    }
    var apagados = {};     // usuários anônimos que a limpeza diária apagou (L-5)
    /** A limpeza apagou o usuário: some das salas (on delete cascade) e a sessão dele deixa de valer. */
    srv.apagaUsuario = function (uid) {
      apagados[uid] = true;
      Object.keys(membros).forEach(function (s) { delete membros[s][uid]; });
    };
    srv.existe = function (uid) { return !apagados[uid]; };
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
      var bytes = bytesDe(a);
      srv.trafego.push({ nome: nome, bytes: bytes });
      return depois(function () {
        if (chaveCompartilhada) carrega();
        var r = srv[nome + "_"](uid, a);
        if (chaveCompartilhada) salva();
        return r;
      }, bytes);
    };
    /** A forma mínima de uma operação (grupos.valida_operacao): id, tipo (da lista), autor, em (texto) e seq inteiro. */
    function formaMinima(op) {
      return !!op && typeof op === "object" && !Array.isArray(op) &&
        typeof op.id === "string" && /^[0-9A-Za-z_-]{1,64}$/.test(op.id) &&
        typeof op.tipo === "string" && (!tiposAceitos || tiposAceitos.indexOf(op.tipo) >= 0) &&
        typeof op.autor === "string" && op.autor.length >= 1 && op.autor.length <= 64 &&
        typeof op.em === "string" && op.em.length <= 64 &&
        typeof op.seq === "number" && /^[0-9]{1,15}$/.test(String(op.seq));
    }
    function salasAtivas() {
      return Object.keys(salas).filter(function (k) { return salas[k].ultima_atividade > agora() - 30 * 24 * 3600 * 1000; }).length;
    }
    /** O que o gatilho antes_de_criar_sala confere: salas por hora e o teto global de salas ativas. */
    function tetosDeCriar(uid) {
      var h = (criadas[uid] || []).filter(function (t) { return t > agora() - 3600 * 1000; });
      if (h.length >= MAX_SALAS_POR_HORA) return { ok: false, motivo: "muitas_salas" };
      if (salasAtivas() >= lim.maxSalasAtivas) return { ok: false, motivo: "servidor_cheio" };
      h.push(agora()); criadas[uid] = h;
      return null;
    }
    function novaSala(uid, mapa, cabecalho, extra) {
      var id = "sala-" + (proximoId++);
      salas[id] = Object.assign({ id: id, codigo: gera(), lider: uid, mapa: mapa, cabecalho: JSON.parse(JSON.stringify(cabecalho)),
                    todos_podem_desenhar: false, encerrada: false, ultima_atividade: agora(),
                    operacoes_iniciais: [], ids_iniciais: [], lamport_inicial: 0, total_ops: 0, total_bytes: 0 }, extra || {});
      membros[id] = {};
      return salas[id];
    }
    srv.criar_ = function (uid, d) {
      var recusa = tetosDeCriar(uid);
      if (recusa) return recusa;
      var x = novaSala(uid, d.mapa, d.cabecalho);
      return { ok: true, sala_id: x.id, codigo: x.codigo };
    };
    /** public.cria_sala: valida o estado inicial (forma mínima, 8 KB por operação, tetos da sala) e cria a sala já com
        a líder dentro. Tudo ou nada. */
    srv.cria_sala_ = function (uid, d) {
      if (!/^de_[a-z0-9_]{1,30}$/.test(String(d.mapa || ""))) return { ok: false, motivo: "invalida" };
      var nick = String(d.nick || "").trim();
      if (!NICK_VALIDO.test(nick) && !srv.semCheckDeNick) return { ok: false, motivo: "nick_invalido" };
      if (!d.cabecalho || typeof d.cabecalho !== "object" || !Array.isArray(d.operacoes)) return { ok: false, motivo: "invalida" };
      if (tamanhoNoServidor(d.cabecalho) > MAX_BYTES_DA_OPERACAO) return { ok: false, motivo: "tamanho" };
      if (d.operacoes.length > lim.maxOpsPorSala) return { ok: false, motivo: "sala_no_limite" };
      var bytes = 0, maior = 0, ids = {};
      for (var i = 0; i < d.operacoes.length; i++) {
        var op = d.operacoes[i];
        if (!formaMinima(op) || op.seq < 1 || ids[op.id]) return { ok: false, motivo: "invalida" };
        var b = tamanhoNoServidor(op);
        if (b > MAX_BYTES_DA_OPERACAO) return { ok: false, motivo: "tamanho" };
        bytes += b;
        if (bytes > lim.maxBytesPorSala) return { ok: false, motivo: "sala_no_limite" };
        ids[op.id] = true; maior = Math.max(maior, op.seq);
      }
      var recusa = tetosDeCriar(uid);
      if (recusa) return recusa;
      var x = novaSala(uid, d.mapa, d.cabecalho, {
        operacoes_iniciais: JSON.parse(JSON.stringify(d.operacoes)), ids_iniciais: Object.keys(ids), lamport_inicial: maior,
        total_ops: d.operacoes.length, total_bytes: bytes });
      membros[x.id][uid] = { usuario: uid, nick: nick, pode_desenhar: false, entrou_em: proximoId++ };
      return { ok: true, sala_id: x.id, codigo: x.codigo, mapa: x.mapa, cabecalho: JSON.parse(JSON.stringify(x.cabecalho)),
               lider: uid, todos_podem_desenhar: false, encerrada: false };
    };
    srv.entrar_ = function (uid, a) {
      // no máximo 30 chamadas por minuto por conta (a janela recomeça na primeira chamada depois dela); a chamada
      // certa não grava nada em `tentativas`
      var c = chamadas[uid];
      if (!c || c.inicio < agora() - 60 * 1000) c = chamadas[uid] = { inicio: agora(), n: 1 };
      else c.n = Math.min(c.n + 1, lim.maxChamadasPorMinuto + 1);
      if (c.n > lim.maxChamadasPorMinuto) return { ok: false, motivo: "muitas_chamadas" };
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
        x.ultima_atividade = agora();
        avisa(x.id, { tabela: "membros", evento: "INSERT", usuario: uid, pode_desenhar: x.todos_podem_desenhar });
      }
      return { ok: true, sala_id: x.id, codigo: x.codigo, mapa: x.mapa, cabecalho: JSON.parse(JSON.stringify(x.cabecalho)),
               lider: x.lider, todos_podem_desenhar: x.todos_podem_desenhar, encerrada: x.encerrada,
               operacoes_iniciais: JSON.parse(JSON.stringify(x.operacoes_iniciais || [])) };
    };
    srv.operacoes_ = function (uid, a) {
      if (!ehMembro(a.sala, uid)) return [];
      var d = a.desde;
      return ops.filter(function (l) {
        return l.sala_id === a.sala && (!d || l.lamport > d.lamport || l.criada_em > d.criada_em - FOLGA_DA_RECONEXAO_MS);
      }).map(function (l) { return JSON.parse(JSON.stringify(l)); });
    };
    srv.envia_ = function (uid, a) {
      // a transação inteira passa ou não (o insert em lote do PostgREST); a ordem é a do gatilho antes_de_inserir_operacao
      var lote = [], x = salas[a.sala] || {};
      var feitas = (enviadasPor[uid] || []).filter(function (t) { return t > agora() - 3600 * 1000; });
      var totalOps = x.total_ops || 0, totalBytes = x.total_bytes || 0;
      var maiorLamport = Math.max(x.lamport_inicial || 0, ops.reduce(function (m, o) { return o.sala_id === a.sala ? Math.max(m, o.lamport) : m; }, 0));
      for (var i = 0; i < a.linhas.length; i++) {
        var l = a.linhas[i], op = l.op;
        if (!formaMinima(op) || op.seq !== l.lamport) return { ok: false, motivo: "invalida" };
        if (l.lamport > maiorLamport + SALTO_DE_LAMPORT) return { ok: false, motivo: "invalida" };   // L-2
        if ((x.ids_iniciais || []).indexOf(op.id) >= 0) return { ok: false, motivo: "duplicada" };
        var recentes = feitas.concat(lote.map(function () { return agora(); }));
        var no = function (ms) { return recentes.filter(function (t) { return t > agora() - ms; }).length; };
        if (no(1000) >= MAX_OPS_POR_SEGUNDO) return { ok: false, motivo: "ritmo" };
        if (no(60 * 1000) >= lim.maxOpsPorMinuto || recentes.length >= lim.maxOpsPorHora) return { ok: false, motivo: "autor_no_limite" };
        var bytes = tamanhoNoServidor(op);
        if (totalOps >= lim.maxOpsPorSala || totalBytes + bytes > lim.maxBytesPorSala) return { ok: false, motivo: "sala_no_limite" };
        if (bytes > MAX_BYTES_DA_OPERACAO) return { ok: false, motivo: "tamanho" };
        if (!podeDesenhar(a.sala, uid)) return { ok: false, motivo: "permissao" };
        var repetida = ops.concat(lote).some(function (o) {
          return o.sala_id === a.sala && ((o.autor === uid && o.lamport === l.lamport) || o.op.id === op.id);
        });
        if (repetida) return { ok: false, motivo: "duplicada" };
        totalOps++; totalBytes += bytes; maiorLamport = Math.max(maiorLamport, l.lamport);
        lote.push({ id: 0, sala_id: a.sala, autor: uid, lamport: l.lamport, op: JSON.parse(JSON.stringify(op)), criada_em: agora() });
      }
      if (x.id) { x.total_ops = totalOps; x.total_bytes = totalBytes; if (lote.length && x.ultima_atividade < agora() - 60 * 1000) x.ultima_atividade = agora(); }
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
    /** SÓ PARA TESTES (B-1 da revisão de segurança): o que um atacante faz pela API direta. Insere a linha SEM
        passar pela forma mínima de envia_ (o servidor real só confere id, tipo, autor e seq) e entrega como o
        Postgres Changes entrega. */
    srv.injeta = function (sala, uid, op) {
      var l = { id: proximoId++, sala_id: sala, autor: uid, lamport: op && op.seq, op: JSON.parse(JSON.stringify(op)), criada_em: agora() };
      ops.push(l);
      conexoes.forEach(function (c) {
        if (c.sala === sala) entrega(c, function () { if (ehMembro(sala, c.uid)) c.o.aoReceber(JSON.parse(JSON.stringify(l))); });
      });
      return l;
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
        // a sessão de um usuário que o servidor apagou não vale mais: o login anônimo é refeito sozinho (L-5)
        if (eu && servidor.existe && !servidor.existe(eu)) {
          eu = null;
          if (opcoes.compartilhado) { try { window.localStorage.removeItem(opcoes.compartilhado + ":uid"); } catch (e) { /* sem armazenamento */ } }
        }
        if (!eu && opcoes.compartilhado) {
          // o login anônimo que a página seguinte reaproveita (como o persistSession do supabase-js)
          try { eu = window.localStorage.getItem(opcoes.compartilhado + ":uid"); } catch (e) { eu = null; }
        }
        if (!eu) {
          eu = "anon-" + Math.random().toString(16).slice(2, 10);
          if (opcoes.compartilhado) { try { window.localStorage.setItem(opcoes.compartilhado + ":uid", eu); } catch (e) { /* sem armazenamento */ } }
        }
        return Promise.resolve(eu);
      },
      uid: function () { return eu; },
      criar: function (d) { return chama("criar", d); },
      criaComEstado: function (d) {
        return chama("cria_sala", d).then(function (r) { if (r && r.ok) salaId = r.sala_id; return r; });
      },
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
    MAX_OPS_POR_SALA: MAX_OPS_POR_SALA, MAX_BYTES_POR_SALA: MAX_BYTES_POR_SALA, MAX_OPS_POR_MINUTO: MAX_OPS_POR_MINUTO,
    MAX_OPS_POR_HORA: MAX_OPS_POR_HORA, MAX_SALAS_ATIVAS: MAX_SALAS_ATIVAS, MAX_CHAMADAS_POR_MINUTO: MAX_CHAMADAS_POR_MINUTO,
    SALTO_DE_LAMPORT: SALTO_DE_LAMPORT,
    NICK_VALIDO: NICK_VALIDO, ALFABETO: ALFABETO
  };
})();
