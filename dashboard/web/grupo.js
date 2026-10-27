/* =========================================================================
   GRUPO na prancheta (fase 13, itens 13.2 e 13.3; decisão 47): a aba "Grupo"
   do painel e a ligação entre a prancheta e a sala (sala.js).

   - Sem grupo, nada muda: nenhum pedido de rede até "Criar grupo" ou "Entrar".
   - A sala só TRANSPORTA as operações do log (decisões 32 e 35). Toda operação
     local vai para a sala; a que o servidor recusa sai do log daqui (é a ação
     desfeita) e a linha de dica diz o motivo. As que chegam entram no log pela
     ordem total de sempre (Lamport + autor + id).
   - Quem pode desenhar é o SERVIDOR que decide (RLS). A tela só espelha:
     desliga os controles de edição com o motivo no `title` (§8).
   - Seguir a líder: o cabeçote e o play da líder valem para quem segue; mexer
     no cabeçote por conta própria solta, e "Voltar para a líder" religa.
   Todo nick passa por MapCore.esc() antes de ir para a tela.
   ========================================================================= */
var Grupo = (function () {
  "use strict";

  // Convenções de interface (não são dado de jogo):
  var DURACAO_DA_ETIQUETA_MS = 3000;     // "nomad moveu ztrike" na linha de dica (pedido da fase 13, 13.3)
  var DURACAO_DA_RECUSA_MS = 6000;       // o motivo de uma recusa fica um pouco mais, para dar tempo de ler
  var JANELA_DO_RITMO_MS = 1100;         // a fila manda no máximo MAX_OPS_POR_SEGUNDO por janela (folga sobre 1 s)
  var ANUNCIO_DO_CABECOTE_MS = 120;      // a líder arrastando o cabeçote: um anúncio a cada 120 ms, no máximo
  var REANUNCIO_TOCANDO_MS = 1000;       // tocando, a líder reanuncia o horário (quem segue corrige a deriva)

  var RECUSA = {
    permissao: "A líder não liberou desenho para você.",
    encerrada: "O grupo foi encerrado: a tática ficou só para leitura.",
    ritmo: "Alterações rápidas demais: o servidor recusou (até 20 por segundo).",
    tamanho: "Alteração grande demais para o grupo (mais de 8 KB): ela foi desfeita.",
    invalida: "O servidor recusou a alteração (formato inválido).",
    duplicada: "Outra aba sua alterou a tática ao mesmo tempo: a alteração foi desfeita.",
    // os tetos de uso (fase 16b, B-2): cada um com a sua frase
    sala_no_limite: "Esta sala chegou ao limite de alterações",
    autor_no_limite: "Você está alterando rápido demais; espere um pouco"
  };
  var ENTRADA = {
    nao_existe: "Nenhum grupo com esse código.",
    encerrada: "Esse grupo foi encerrado.",
    expulso: "A líder tirou você deste grupo.",
    sala_cheia: "Esse grupo já tem 10 pessoas.",
    nick_invalido: "O nick tem de 1 a 24 caracteres: letras, números, espaço, _ . -",
    nick_em_uso: "Já tem alguém com esse nick no grupo.",
    muitas_tentativas: "Muitos códigos errados seguidos: espere 10 minutos.",
    muitas_salas: "Você criou grupos demais na última hora.",
    sem_login: "O login anônimo não funcionou.",
    servidor_cheio: "O servidor de grupos está cheio agora",
    muitas_chamadas: "Muitas tentativas; espere um minuto",
    sala_no_limite: RECUSA.sala_no_limite
  };
  var INDISPONIVEL = "Grupo indisponível agora. A tática continua salva neste navegador.";
  var SO_NO_SITE = "Grupos funcionam no site publicado.";
  // B-3 (revisão de segurança): o que sobe ao servidor, dito por inteiro. O mesmo texto está na seção 2 de
  // notas/seguranca/grupos.md (teste compara). Contato por issue do GitHub: o site não tem e-mail nenhum.
  var CONTATO_DO_AVISO = "peça no GitHub";
  var LINK_DO_CONTATO = "https://github.com/pedroppansani/parser-replay-cs2/issues/new";
  var O_QUE_GUARDA = "O servidor guarda o nick, quem está em cada grupo e a tática inteira, incluindo os nomes de autor " +
    "que ela já tem. O login anônimo do Supabase também registra IP e navegador. Grupo parado há 30 dias é apagado. " +
    "Para apagar antes, " + CONTATO_DO_AVISO + ".";
  var DESCARTADA = "Uma alteração recebida estava malformada e foi ignorada.";
  var NOME_PADRAO_DO_AUTOR = "anônimo";   // o autor de quem não preencheu o campo (tactics.js): não é um nome
  var MAPA_DE_OUTRA_PAGINA = "A tática desse grupo é de outro mapa e a página dele não abriu.";
  var LEVANDO = "Esse grupo é de outro mapa: indo para a página dele…";
  var MAPA_VALIDO = /^de_[a-z0-9_]{1,30}$/;   // o check de salas.mapa (supabase/migrations)
  var VOCE_ACOMPANHA = "<b>Você acompanha a tática:</b> só a líder desenha agora. Você ainda pode mover o cabeçote e dar play.";
  var FOI_ENCERRADO = "<b>O grupo foi encerrado:</b> a tática ficou só para leitura.";
  var SEM_O_GRUPO = "Enquanto isso, a prancheta funciona como sempre, sozinho.";
  var SOZINHA = "Transferir fica desligado: ninguém mais no grupo.";
  var REMOVIDO = "A líder tirou você deste grupo. A tática continua salva neste navegador.";
  // as recusas que NÃO desfazem nada (o servidor só disse não) têm borda tracejada; as que desfazem levam ▲ e borda cheia (§19.6)
  var RECUSA_SEM_DESFAZER = { permissao: true, encerrada: true };
  var NO_GRUPO ="Num grupo, a tática é a do grupo. Saia do grupo para trocar de tática.";

  var cfg = null, sala = null, P = null;
  var G = novoEstado();

  function novoEstado() {
    return {
      fase: "fora",              // fora | entrando | dentro
      papel: null,               // lider | membro
      uid: null, nick: "", codigo: "", salaId: null, docId: null,
      lider: null, todos: false, encerrada: false,
      membros: [], online: {},
      seguir: true, ultimoCabecote: null, aplicandoCabecote: false,
      conexao: null,             // conectado | caiu
      fila: [], enviando: false, enviadasEm: [],
      recebidas: {}, ultimo: null,   // {lamport, criada_em}: a última recebida (para a reconexão)
      chegando: [],
      etiqueta: null,            // {autor, frase, ate}: "nomad moveu ztrike" (3 s)
      recusa: null,              // {texto, desfeita, ate}: o motivo da recusa do servidor (6 s)
      status: "", erro: "", info: "", erroCampo: null,   // erroCampo: {campo: "nick" | "codigo", texto}
      confirmando: null, alvoTransferencia: "", expulsando: null,
      form: { nick: "", codigo: "" },
      convite: null,             // o código do link #sala= com nick salvo: a aba mostra um botão só (§19.6)
      anuncio: { ultimo: 0, timer: null, intervalo: null }
    };
  }

  function $(id) { return document.getElementById(id); }
  function esc(v) { return MapCore.esc(v); }

  /* ----------------------------------------------------------------------
     Montagem: chamada ANTES de Prancheta.init (o build injeta este arquivo e
     a configuração só quando o grupo está ligado).
     cfg: {modo: "supabase" | "falsa", url, chave, biblioteca, site, pagina,
           arquivoLocal (grupo também aberto como arquivo?), falsa: {...}}
     ---------------------------------------------------------------------- */
  function prepara(config) {
    cfg = config || {};
    P = Prancheta.grupo;
    var g = Prancheta.ganchos;
    g.abas = [["grupo", "Grupo"]];
    g.autor = function () { return G.fase === "dentro" ? G.nick : ""; };
    g.aoEmitir = aoEmitir;
    g.aoMudarTempo = aoMudarTempo;
    g.aoAtualizar = aoAtualizar;
    g.aoDescartar = aoDescartar;
    g.dica = dicaDoGrupo;
    g.aoIniciar = aoIniciar;
    // o servidor em memória dos testes existe desde já (não é rede: os testes conferem que fica sem pedido)
    if (cfg.modo === "falsa") window.__servidorFalso = window.__servidorFalso || Sala.ServidorFalso(Object.assign({ tipos: P.tipos() }, cfg.falsa || {}));
  }

  function criaSala() {
    if (sala) return sala;
    if (cfg.modo === "falsa") {
      sala = Sala.SalaFalsa(window.__servidorFalso, { uid: (cfg.falsa || {}).uid, compartilhado: (cfg.falsa || {}).compartilhado });
    } else {
      sala = Sala.SalaSupabase({ url: cfg.url, chave: cfg.chave, biblioteca: cfg.biblioteca });
    }
    return sala;
  }

  /** Aberta como arquivo (file://) com o Supabase: o grupo fica para o site
      publicado enquanto a parte B não confirmar que funciona (decisão 47). */
  function soNoSite() { return cfg.modo === "supabase" && location.protocol === "file:" && !cfg.arquivoLocal; }

  function aoIniciar() {
    // #sala=CODIGO (o link) ou #sala=CODIGO&nick=NICK (o que a página de outro mapa manda ao redirecionar)
    var m = /^#sala=([A-Za-z0-9]{1,16})(?:&nick=([^&]*))?$/.exec(location.hash);
    var nickDoRedirecionamento = "";
    if (m) {
      G.form.codigo = m[1].toUpperCase(); Prancheta._interno.abaDoPainel("grupo");
      try { nickDoRedirecionamento = m[2] ? decodeURIComponent(m[2]) : ""; } catch (e) { nickDoRedirecionamento = ""; }
    }
    try { G.form.nick = localStorage.getItem("prancheta:grupo-nick") || ""; } catch (e) { G.form.nick = ""; }
    if (nickDoRedirecionamento) { G.form.nick = nickDoRedirecionamento; G.redirecionado = true; }
    // link #sala= com nick salvo: um botão só, "Entrar no grupo da Mirage como nomad". Abrir o link não entra
    // sozinho nem faz pedido nenhum: só o clique (decisão 47). O nick do armazém (autor) não conta como salvo.
    if (m && !nickDoRedirecionamento && /^[A-Z0-9]{8}$/.test(G.form.codigo) && nickValido(G.form.nick)) G.convite = G.form.codigo;
    if (!G.form.nick) G.form.nick = (Prancheta._interno.armazem().autor() || "").trim().slice(0, 24);
    var painel = $("pr-painel-grupo");
    painel.addEventListener("click", aoClicar);
    painel.addEventListener("input", function (e) {
      if (e.target.id === "gr-nick") { G.form.nick = e.target.value; atualizaBotaoDoConvite(); }
      if (e.target.id === "gr-codigo") G.form.codigo = e.target.value;
      if (e.target.id === "gr-transferir-para") G.alvoTransferencia = e.target.value;
    });
    painel.addEventListener("change", function (e) {
      if (e.target.id === "gr-transferir-para") G.alvoTransferencia = e.target.value;
    });
    painel.addEventListener("keydown", function (e) {
      if (e.key !== "Enter") return;
      if (e.target.id === "gr-codigo") { e.preventDefault(); entrar(); }
    });
    // "Expulsar nomad? Confirmar · Cancelar": Esc e clique fora cancelam (sem o confirm() do navegador)
    document.addEventListener("keydown", function (e) { if (e.key === "Escape" && G.expulsando) cancelaExpulsao(true); });
    document.addEventListener("click", function (e) {
      if (!G.expulsando || !e.target.isConnected) return;
      if (e.target.closest(".gr-confirma-expulsa") || e.target.closest('[data-acao="expulsa"]')) return;
      cancelaExpulsao(false);
    });
    renderiza();
    // veio de outra página de mapa com o nick: continua a entrada de onde ela parou (o servidor aceita
    // quem já é membro sem recontar nick nem limite). Sem o nick no link, só o clique em "Entrar" pede algo.
    if (nickDoRedirecionamento) entrar();
  }

  /* ----------------------------------------------------------------------
     Criar e entrar
     ---------------------------------------------------------------------- */
  function nickValido(n) { return Sala.NICK_VALIDO.test(n) && n === n.trim(); }
  function guardaNick(n) { try { localStorage.setItem("prancheta:grupo-nick", n); } catch (e) { /* sem armazenamento */ } }

  function cabecalhoDe(doc) {
    var c = {};
    Object.keys(doc).forEach(function (k) { if (k !== "operacoes" && k !== "contador") c[k] = doc[k]; });
    return c;
  }

  /** Os nomes de autor que a tática atual já tem (criada_por e o autor de cada operação) e que sobem ao servidor
      ao criar o grupo. Não regrava nada: só mostra (regrava-los mudaria operação, decisão 47). */
  function nomesDeAutor() {
    var doc = P && P.documento();
    if (!doc) return [];
    var vistos = {}, lista = [];
    [doc.criada_por].concat((doc.operacoes || []).map(function (o) { return o && o.autor; })).forEach(function (n) {
      if (typeof n !== "string" || !n || n === NOME_PADRAO_DO_AUTOR || Object.prototype.hasOwnProperty.call(vistos, n)) return;
      vistos[n] = true; lista.push(n);
    });
    return lista;
  }
  function aoAtualizar() {
    aplicaPermissao();
    // a aba "Grupo" fora do grupo mostra os nomes de autor da tática de agora: se mudaram, redesenha
    if (G.fase !== "dentro" && $("pr-painel-grupo") && G.nomesMostrados !== nomesDeAutor().join("\u0001")) renderiza();
  }
  /** Chegou operação que a validação descartou (tactics.js): a dica avisa uma vez por lote. */
  function aoDescartar() {
    G.recusa = { texto: DESCARTADA, desfeita: false, ate: Date.now() + DURACAO_DA_RECUSA_MS };
    expiraDaDica('recusa', DURACAO_DA_RECUSA_MS);
  }

  /** O que impede uma tática de virar grupo, ou "". */
  function impedimento(doc) {
    var grande = doc.operacoes.filter(function (o) { return Sala.tamanhoNoServidor(o) > Sala.MAX_BYTES_DA_OPERACAO; });
    if (grande.length) {
      return "Esta tática tem " + grande.length + " alteração(ões) grande(s) demais para o grupo (mais de 8 KB cada, " +
        "em geral o caminho de um jogador com muitos pontos).";
    }
    if (Sala.tamanhoNoServidor(cabecalhoDe(doc)) > Sala.MAX_BYTES_DA_OPERACAO) return "O cabeçalho desta tática passa de 8 KB.";
    var bytes = doc.operacoes.reduce(function (t, o) { return t + Sala.tamanhoNoServidor(o); }, 0);
    if (doc.operacoes.length > Sala.MAX_OPS_POR_SALA || bytes > Sala.MAX_BYTES_POR_SALA) {
      return "Esta tática passa do limite de um grupo (" + Sala.MAX_OPS_POR_SALA + " alterações ou 2 MB).";
    }
    var vistos = {}, repetido = false;
    doc.operacoes.forEach(function (o) { if (vistos[o.seq]) repetido = true; vistos[o.seq] = true; });
    if (repetido) {
      return "Esta tática junta cópias de mais de uma pessoa (números de ordem repetidos) e ainda não pode virar grupo.";
    }
    return "";
  }

  function criar() {
    if (G.fase !== "fora" || soNoSite()) return;
    var nick = (G.form.nick || "").trim();
    if (!nickValido(nick)) { G.erroCampo = { campo: "nick", texto: ENTRADA.nick_invalido }; renderiza(); return; }
    var doc = P.documento();
    var imp = impedimento(doc);
    if (imp) { G.status = imp; renderiza(); return; }
    G.fase = "entrando"; G.status = "Criando o grupo…"; G.erro = ""; G.erroCampo = null; renderiza();
    var s = criaSala(), iniciais = null;
    s.prepara().then(function (uid) {
      G.uid = uid;
      // o estado inicial (as operações que a tática já tem) sobe numa linha só, junto com a criação da sala (fase 16b)
      iniciais = doc.operacoes.slice();
      return s.criaComEstado({ mapa: doc.mapa, nick: nick, cabecalho: cabecalhoDe(doc), operacoes: iniciais });
    }).then(function (r) {
      if (!r || !r.ok) throw { motivo: r && r.motivo };
      guardaNick(nick);
      entra(r, nick, doc.id);
      var subiram = {};
      iniciais.forEach(function (o) { subiram[o.id] = true; G.recebidas[o.id] = true; });
      // o que a pessoa fez enquanto o grupo era criado não estava no estado inicial: vai pela fila
      P.documento().operacoes.forEach(function (o) { if (!subiram[o.id]) G.fila.push(o); });
      processaFila();
      return conecta();
    }).catch(function (x) { falhaAoEntrar(x); });
  }

  function entrar() {
    if (G.fase !== "fora" || soNoSite()) return;
    var nick = (G.form.nick || "").trim(), codigo = (G.form.codigo || "").trim().toUpperCase();
    if (!nickValido(nick)) { G.erroCampo = { campo: "nick", texto: ENTRADA.nick_invalido }; renderiza(); return; }
    if (!/^[A-Z0-9]{8}$/.test(codigo)) { G.erroCampo = { campo: "codigo", texto: "O código tem 8 letras e números." }; renderiza(); return; }
    G.fase = "entrando"; G.status = "Entrando no grupo…"; G.erro = ""; G.erroCampo = null; renderiza();
    var s = criaSala(), info = null;
    s.prepara().then(function (uid) {
      G.uid = uid;
      return s.entrar(codigo, nick);
    }).then(function (e) {
      if (!e || !e.ok) throw { motivo: e && e.motivo };
      info = e;
      // o código é de um grupo de OUTRO mapa: a tática dele não abre nesta página
      if (info.mapa !== P.documento().mapa) {
        var destino = destinoDoMapa(info.mapa, codigo, nick);
        if (G.redirecionado || !destino) throw { texto: MAPA_DE_OUTRA_PAGINA };    // nunca em laço
        guardaNick(nick);
        G.status = LEVANDO; renderiza();
        navegaPara(destino);
        return null;
      }
      return s.operacoes();
    }).then(function (linhas) {
      if (!linhas) return null;
      // o log da sala: o estado inicial (numa linha só) seguido das operações da tabela
      var doc = Object.assign({}, info.cabecalho, { operacoes: [], contador: 0 });
      (info.operacoes_iniciais || []).forEach(function (o) {
        doc.operacoes.push(o);
        if (o && typeof o.seq === "number" && isFinite(o.seq)) doc.contador = Math.max(doc.contador, o.seq);
        G.recebidas[o.id] = true;
      });
      linhas.forEach(function (l) {
        doc.operacoes.push(l.op);
        if (l.op && typeof l.op.seq === "number" && isFinite(l.op.seq)) doc.contador = Math.max(doc.contador, l.op.seq);
      });
      var erro = P.usaDocumento(doc);
      if (erro) { s.sai(); throw { texto: "A tática do grupo não abre aqui: " + erro + "." }; }
      guardaNick(nick);
      entra(info, nick, doc.id);
      linhas.forEach(marcaRecebida);
      return conecta();
    }).catch(function (x) { falhaAoEntrar(x); });
  }

  /** A URL da prancheta do mapa do grupo, na mesma pasta, com o código e o nick; "" se o mapa não é válido
      (o mapa vem do servidor e entra num endereço: só o formato de salas.mapa passa). */
  function destinoDoMapa(mapa, codigo, nick) {
    var atual = P.documento().mapa;
    if (!MAPA_VALIDO.test(String(mapa)) || !atual) return "";
    var caminho = location.pathname.split("/").pop();
    if (caminho.indexOf(atual) < 0) return "";
    var novo = caminho.replace(atual, mapa);
    var base = location.href.split("#")[0].split("?")[0];
    base = base.slice(0, base.lastIndexOf("/") + 1);
    return base + novo + location.search + "#sala=" + codigo + "&nick=" + encodeURIComponent(nick);
  }
  function navegaPara(url) { window.location.assign(url); }

  function entra(info, nick, docId) {
    G.fase = "dentro"; G.nick = nick; G.codigo = info.codigo; G.salaId = info.sala_id; G.docId = docId;
    G.lider = info.lider; G.todos = !!info.todos_podem_desenhar; G.encerrada = !!info.encerrada;
    G.papel = info.lider === G.uid ? "lider" : "membro";
    G.seguir = G.papel === "membro";
    G.status = ""; G.erro = ""; G.info = ""; G.erroCampo = null;
    P.limpaHistorico();      // desfazer só o que é seu, no grupo
    if (window.history && history.replaceState) history.replaceState(null, "", location.pathname + location.search + "#sala=" + G.codigo);
    atualizaMembros();
    renderiza();
    P.atualizaDica();
  }

  function falhaAoEntrar(x) {
    G.fase = "fora"; G.convite = null;      // a recusa aparece no formulário de sempre, com o campo do código
    G.status = ""; G.erro = ""; G.erroCampo = null;
    if (x && x.motivo && ENTRADA[x.motivo]) {
      // nick recusado: erro no campo do nick; código recusado: no campo do código (§19.6); o resto, na linha de status
      if (x.motivo === "nick_invalido" || x.motivo === "nick_em_uso") G.erroCampo = { campo: "nick", texto: ENTRADA[x.motivo] };
      else if (x.motivo === "muitas_salas" || x.motivo === "sem_login" || x.motivo === "servidor_cheio" ||
               x.motivo === "muitas_chamadas" || x.motivo === "sala_no_limite") G.status = ENTRADA[x.motivo];
      else G.erroCampo = { campo: "codigo", texto: ENTRADA[x.motivo] };
    } else if (x && x.texto) G.erroCampo = { campo: "codigo", texto: x.texto };
    else G.erro = INDISPONIVEL;
    if (sala && sala.desconecta) sala.desconecta();
    renderiza();
  }

  function conecta() {
    return sala.conecta({
      aoReceber: aoReceber, aoMudar: aoMudar, aoPresenca: aoPresenca, aoCabecote: aoCabecote, aoConexao: aoConexao
    });
  }

  /* ----------------------------------------------------------------------
     Enviar: otimista, em lotes, no ritmo do servidor
     ---------------------------------------------------------------------- */
  function aoEmitir(op) {
    if (G.fase !== "dentro" || P.documento().id !== G.docId) return;
    G.fila.push(op);
    processaFila();
  }

  function processaFila() {
    if (G.enviando || !G.fila.length || G.fase !== "dentro") return;
    if (G.conexao === "caiu") return;     // volta a mandar quando a conexão voltar
    var agora = Date.now();
    G.enviadasEm = G.enviadasEm.filter(function (t) { return t > agora - JANELA_DO_RITMO_MS; });
    var cabem = Sala.MAX_OPS_POR_SEGUNDO - G.enviadasEm.length;
    if (cabem <= 0) { setTimeout(processaFila, G.enviadasEm[0] + JANELA_DO_RITMO_MS - agora + 5); return; }
    // depois de uma recusa por duplicada num lote, uma por vez até achar qual era
    var lote = G.fila.splice(0, G.loteUnitario > 0 ? 1 : cabem);
    if (G.loteUnitario > 0) G.loteUnitario--;
    // a grande demais nem sai daqui: o servidor recusaria do mesmo jeito
    var grandes = lote.filter(function (o) { return Sala.tamanhoNoServidor(o) > Sala.MAX_BYTES_DA_OPERACAO; });
    if (grandes.length) {
      lote = lote.filter(function (o) { return grandes.indexOf(o) < 0; });
      recusa(grandes, "tamanho");
      if (!lote.length) { processaFila(); return; }
    }
    G.enviando = true;
    lote.forEach(function () { G.enviadasEm.push(agora); });
    sala.envia(lote.map(function (o) { return { lamport: o.seq, op: o }; })).then(function (r) {
      G.enviando = false;
      if (r && r.ok) { lote.forEach(function (o) { G.recebidas[o.id] = true; }); }
      else if (r && r.motivo === "rede") {
        // sem conexão: a operação continua aqui e volta para a fila (sai quando a conexão voltar)
        G.fila = lote.concat(G.fila);
        if (G.conexao !== "caiu") { G.conexao = "caiu"; G.erro = INDISPONIVEL; renderiza(); }
        return;
      } else if (r && r.motivo === "duplicada" && lote.length > 1) {
        // uma do lote já estava lá (reenvio depois de cair): uma por vez
        G.fila = lote.concat(G.fila);
        G.loteUnitario = lote.length;
      } else if (r && r.motivo === "duplicada") {
        confereDuplicada(lote[0]);
      } else {
        recusa(lote, (r && r.motivo) || "invalida");
      }
      processaFila();
    }, function () { G.enviando = false; G.fila = lote.concat(G.fila); });
  }

  function confereDuplicada(op) {
    sincroniza().then(function () { if (!G.recebidas[op.id]) recusa([op], "duplicada"); });
  }

  /** A recusa do servidor: a operação sai do log daqui e a dica diz por quê. */
  function recusa(ops, motivo) {
    P.retira(ops.map(function (o) { return o.id; }));
    var m = motivo === "permissao" && G.encerrada ? "encerrada" : motivo;
    G.recusa = { texto: RECUSA[m] || RECUSA.invalida, desfeita: !RECUSA_SEM_DESFAZER[m], ate: Date.now() + DURACAO_DA_RECUSA_MS };
    expiraDaDica('recusa', DURACAO_DA_RECUSA_MS);
  }

  /* ----------------------------------------------------------------------
     Receber
     ---------------------------------------------------------------------- */
  function marcaRecebida(l) {
    if (!l || !l.op) return;
    G.recebidas[l.op.id] = true;
    // o horário do servidor em ms (o Supabase manda texto ISO; a sala falsa, número)
    var em = typeof l.criada_em === "number" ? l.criada_em : Date.parse(l.criada_em);
    var u = G.ultimo;
    // o Lamport de uma operação que a validação recusa não move o ponto da reconexão (um número gigante
    // faria a busca seguinte pular as operações boas)
    var lamport = P.operacaoValida(l.op) ? l.lamport : 0;
    if (!u) G.ultimo = { lamport: lamport, criada_em: em };
    else {
      if (lamport > u.lamport) u.lamport = lamport;
      if (em > u.criada_em) u.criada_em = em;
    }
  }

  function aoReceber(l) {
    if (G.fase !== "dentro" || !l || !l.op) return;
    marcaRecebida(l);
    G.chegando.push(l);
    // várias no mesmo instante viram uma reaplicação só
    if (G.chegando.length === 1) Promise.resolve().then(aplicaChegadas);
  }

  function aplicaChegadas() {
    var lote = G.chegando; G.chegando = [];
    var deFora = lote.filter(function (l) { return l.autor !== G.uid && P.operacaoValida(l.op); });
    var estadoAntes = P.estado();
    P.recebe(lote.map(function (l) { return l.op; }));
    if (deFora.length) etiqueta(deFora[deFora.length - 1].op, estadoAntes);
  }

  /** "nomad moveu ztrike": quem fez a última alteração, por 3 segundos. */
  function etiqueta(op, estadoAntes) {
    var est = P.estado() || estadoAntes || { pecas: {} };
    function peca(id) { var p = (est.pecas || {})[id] || ((estadoAntes || {}).pecas || {})[id]; return p ? p.rotulo : "uma peça"; }
    var t = op.tipo, verbo;
    if (t === "move_peca" || t === "move_ponto" || t === "cria_caminho" || t === "remove_ponto") verbo = "moveu " + peca(op.peca);
    else if (t === "gira_peca") verbo = "virou " + peca(op.peca);
    else if (t === "cria_peca") verbo = "pôs " + (op.rotulo || "uma peça");
    else if (t === "remove_peca" || t === "tira_peca") verbo = "tirou " + peca(op.peca);
    else if (t === "cria_granada" || t === "move_granada") verbo = "mexeu numa granada";
    else if (t === "desenha_granada") verbo = "desenhou uma granada";
    else if (t === "cria_traco" || t === "define_area_desenho") verbo = "desenhou no mapa";
    else if (t === "define_funcao") verbo = "mudou a função de " + peca(op.peca);
    else if (t === "anula") verbo = "desfez uma alteração";
    else if (t === "reativa") verbo = "refez uma alteração";
    else if (t === "renomeia") verbo = "renomeou a tática";
    else verbo = "alterou a tática";
    G.etiqueta = { autor: String(op.autor), frase: String(op.autor) + " " + verbo, ate: Date.now() + DURACAO_DA_ETIQUETA_MS };
    expiraDaDica('etiqueta', DURACAO_DA_ETIQUETA_MS);
  }

  /** A etiqueta (3 s) e a recusa (6 s) saem sozinhas; uma nova substitui a anterior e reinicia o tempo. */
  function expiraDaDica(qual, ms) {
    P.atualizaDica();
    setTimeout(function () { if (G[qual] && Date.now() >= G[qual].ate) { G[qual] = null; P.atualizaDica(); } }, ms + 20);
  }
  /** O que a linha de dica mostra por causa do grupo (§19.6): {texto, html, classe, etiqueta} ou null. Prioridade:
      recusa > texto fixo do estado (só assiste, encerrado) > texto normal da dica; a etiqueta é sempre somada. */
  function dicaDoGrupo() {
    var agora = Date.now(), r = null;
    var rec = G.recusa && agora < G.recusa.ate ? G.recusa : null, et = G.etiqueta && agora < G.etiqueta.ate ? G.etiqueta : null;
    function simples(html) { return html.replace(/<[^>]+>/g, ""); }
    if (rec) r = { texto: rec.texto, html: "<b>" + esc(rec.texto) + "</b>", classe: rec.desfeita ? "recusa-desfeita" : "recusa" };
    else if (G.fase === "dentro" && G.encerrada) r = { texto: simples(FOI_ENCERRADO), html: FOI_ENCERRADO, classe: "bloqueado" };
    else if (G.fase === "dentro" && !podeDesenhar()) r = { texto: simples(VOCE_ACOMPANHA), html: VOCE_ACOMPANHA, classe: "bloqueado" };
    if (et) {
      r = r || {};
      r.etiqueta = '<span class="dica-etiqueta" role="status"><span class="gr-ficha" aria-hidden="true">' + esc(iniciais(et.autor)) +
        '</span><span class="dica-frase">' + esc(et.frase) + "</span></span>";
    }
    return r;
  }

  /** Na reconexão (ou depois de entrar): o que chegou ao servidor desde a última recebida. */
  function sincroniza() {
    if (G.fase !== "dentro") return Promise.resolve();
    return sala.operacoes(G.ultimo).then(function (linhas) {
      linhas.forEach(function (l) { aoReceber(l); });
    }, function () { /* ainda sem conexão: a próxima reconexão tenta de novo */ });
  }

  function aoConexao(estado) {
    if (G.fase !== "dentro") return;
    var antes = G.conexao;
    G.conexao = estado;
    if (estado === "caiu") { G.erro = INDISPONIVEL; renderiza(); return; }
    G.erro = "";
    if (antes === "caiu" || antes === null) {
      sincroniza().then(function () { processaFila(); });
      atualizaMembros();
    }
    renderiza();
  }

  /* ----------------------------------------------------------------------
     Membros, permissões e avisos da sala
     ---------------------------------------------------------------------- */
  function atualizaMembros() {
    if (G.fase !== "dentro") return;
    Promise.all([sala.sala(), sala.membros()]).then(function (r) {
      var s = r[0];
      if (s) {
        G.lider = s.lider; G.todos = !!s.todos_podem_desenhar; G.encerrada = !!s.encerrada;
        var era = G.papel;
        G.papel = s.lider === G.uid ? "lider" : "membro";
        if (era !== G.papel) { G.seguir = G.papel === "membro"; G.confirmando = null; }
      }
      G.membros = r[1] || [];
      renderiza();
      P.atualizaDica();
      aplicaPermissao();
    }, function () { /* sem conexão: fica o que já se sabia */ });
  }

  function aoMudar(aviso) {
    if (G.fase !== "dentro" || !aviso) return;
    if (aviso.tabela === "membros" && aviso.evento === "DELETE" && aviso.usuario === G.uid) {
      if (!G.saindo) saiDaSala(ENTRADA.expulso);
      return;
    }
    if (aviso.tabela === "salas") {
      G.todos = !!aviso.todos_podem_desenhar; G.encerrada = !!aviso.encerrada;
      if (aviso.lider) { G.lider = aviso.lider; G.papel = aviso.lider === G.uid ? "lider" : "membro"; }
    }
    if (aviso.tabela === "membros" && aviso.evento === "UPDATE") {
      G.membros.forEach(function (m) { if (m.usuario === aviso.usuario) m.pode_desenhar = !!aviso.pode_desenhar; });
    }
    aplicaPermissao();
    renderiza();
    atualizaMembros();
  }

  function aoPresenca(lista) {
    G.online = {};
    (lista || []).forEach(function (u) { G.online[u] = true; });
    renderiza();
  }

  function eu() { return G.membros.filter(function (m) { return m.usuario === G.uid; })[0] || null; }
  function podeDesenhar() {
    if (G.fase !== "dentro") return true;
    if (G.encerrada) return false;
    if (G.papel === "lider" || G.todos) return true;
    var m = eu();
    return !!(m && m.pode_desenhar);
  }
  function motivoSemPermissao() { return G.encerrada ? RECUSA.encerrada : RECUSA.permissao; }

  // os controles que alteram a tática (a barra de pincéis, desfazer/refazer, granadas, passos, título e o
  // painel do selecionado). Selecionar, tocar, o cabeçote e ler o painel continuam.
  var CONTROLES_DE_EDICAO = [
    '#pr-barra [data-ferramenta]:not([data-ferramenta="mover"])', "#pr-desfaz", "#pr-refaz",
    "aside [data-arma]", 'aside [data-ferramenta="buscar"]', 'aside [data-ferramenta="granada"]',
    "#pr-passos button", "#pr-passo-titulo", "#pr-passo-duracao", "#pr-remove-passo", "#pr-titulo",
    "#pr-selecao button", "#pr-selecao input", "#pr-selecao select", ".pr-funcao", ".pr-evento-nota"
  ];
  var CONTROLES_DA_TATICA = ["#pr-nova", "#pr-taticas", "#pr-apaga", "#pr-importa", "#pr-autor"];
  var desligados = [];

  /** Liga ou desliga os controles de edição (motivo no title, como o §8 manda). Roda no fim de cada atualizaTudo. */
  function aplicaPermissao() {
    desligados.forEach(function (d) { if (d.el.isConnected) { d.el.disabled = d.disabled; d.el.title = d.title; } });
    desligados = [];
    if (G.fase !== "dentro") return;
    function desliga(sel, motivo) {
      Array.prototype.forEach.call(document.querySelectorAll(sel), function (e) {
        if (e.dataset.grupoDesligado) return;
        desligados.push({ el: e, disabled: e.disabled, title: e.title });
        e.disabled = true; e.title = motivo;
      });
    }
    CONTROLES_DA_TATICA.forEach(function (s) { desliga(s, NO_GRUPO); });
    if (!podeDesenhar()) { var m = motivoSemPermissao(); CONTROLES_DE_EDICAO.forEach(function (s) { desliga(s, m); }); }
  }

  /* ----------------------------------------------------------------------
     Seguir a líder
     ---------------------------------------------------------------------- */
  function aoMudarTempo() {
    if (G.fase !== "dentro" || G.aplicandoCabecote) return;
    if (G.papel === "lider") { anunciaCabecote(); return; }
    if (G.seguir) { G.seguir = false; renderiza(); }     // mexeu no cabeçote por conta própria: solta
  }

  function anunciaCabecote() {
    var a = G.anuncio, agora = Date.now();
    clearTimeout(a.timer);
    var envia = function () {
      a.ultimo = Date.now();
      var c = P.cabecote();
      sala.anunciaCabecote(c);
      clearInterval(a.intervalo); a.intervalo = null;
      if (c.modo === "reproducao" && c.tocando) a.intervalo = setInterval(function () {
        var d = P.cabecote();
        if (G.fase !== "dentro" || G.papel !== "lider" || d.modo !== "reproducao" || !d.tocando) { clearInterval(a.intervalo); a.intervalo = null; return; }
        sala.anunciaCabecote(d);
      }, REANUNCIO_TOCANDO_MS);
    };
    if (agora - a.ultimo >= ANUNCIO_DO_CABECOTE_MS) envia();
    else a.timer = setTimeout(envia, ANUNCIO_DO_CABECOTE_MS - (agora - a.ultimo));
  }

  function aoCabecote(c) {
    if (G.fase !== "dentro" || G.papel === "lider") return;
    G.ultimoCabecote = c;
    if (G.seguir) segue(c);
  }
  function segue(c) {
    if (!c) return;
    G.aplicandoCabecote = true;
    try { P.segueCabecote(c); } finally { G.aplicandoCabecote = false; }
  }
  function voltaParaALider() { G.seguir = true; renderiza(); segue(G.ultimoCabecote); }

  /* ----------------------------------------------------------------------
     Ações da líder e do membro
     ---------------------------------------------------------------------- */
  function resultadoDaAcao(r) {
    if (r && r.ok === false) { G.status = r.motivo === "rede" ? "" : (RECUSA[r.motivo] || ENTRADA[r.motivo] || "O servidor recusou."); if (r.motivo === "rede") G.erro = INDISPONIVEL; }
    atualizaMembros();
    renderiza();
  }

  function saiDaSala(motivo) {
    G.saindo = true;
    clearInterval(G.anuncio.intervalo);
    if (sala) sala.desconecta();
    var form = G.form;
    G = novoEstado();
    G.form = form;
    if (motivo === ENTRADA.expulso) G.info = REMOVIDO;       // não é erro: aviso informativo no topo do formulário
    else G.status = motivo || "Você saiu do grupo. A tática continua salva neste navegador.";
    if (window.history && history.replaceState) history.replaceState(null, "", location.pathname + location.search);
    aplicaPermissao();
    Prancheta._interno.abaDoPainel("grupo");
    renderiza();
    P.atualizaDica();
  }

  function sair() {
    if (G.fase !== "dentro") return;
    G.saindo = true;
    // a líder não sai pelo servidor (precisa transferir antes); com o grupo encerrado, só fecha aqui
    if (G.papel === "lider") { saiDaSala(); return; }
    sala.sai().then(function () { saiDaSala(); }, function () { saiDaSala(); });
  }

  function copiaLink() {
    var link = linkDaSala();
    // o link fica escrito na tela de qualquer jeito (a área de transferência pode pedir permissão ou faltar)
    G.status = "Link copiado: " + link;
    renderiza();
    try {
      if (navigator.clipboard && navigator.clipboard.writeText) navigator.clipboard.writeText(link).catch(function () {});
    } catch (e) { /* sem área de transferência: o link está no texto */ }
  }
  function linkDaSala() {
    var base = location.protocol === "file:" && cfg.site ? cfg.site.replace(/\/?$/, "/") + (cfg.pagina || "") : location.href.split("#")[0];
    return base + "#sala=" + G.codigo;
  }

  function aoClicar(e) {
    var b = e.target.closest("[data-acao]");
    if (!b || b.disabled) return;
    var acao = b.getAttribute("data-acao"), u = b.getAttribute("data-usuario");
    G.status = ""; G.erroCampo = null; G.info = "";
    if (acao === "criar") criar();
    else if (acao === "entrar") entrar();
    else if (acao === "entrar-convite") { G.form.codigo = G.convite || G.form.codigo; entrar(); }
    else if (acao === "convite-outro") { G.convite = null; renderiza(); }
    else if (acao === "copiar") copiaLink();
    else if (acao === "todos") sala.todosPodem(!G.todos).then(resultadoDaAcao);
    else if (acao === "permite") {
      var m = G.membros.filter(function (x) { return x.usuario === u; })[0];
      if (m) sala.permite(u, !m.pode_desenhar).then(resultadoDaAcao);
    } else if (acao === "expulsa") { G.expulsando = u; renderiza(); }
    else if (acao === "cancela-expulsa") cancelaExpulsao(true);
    else if (acao === "confirma-expulsa") {
      var quem = G.membros.filter(function (x) { return x.usuario === u; })[0];
      G.expulsando = null;
      sala.expulsa(u).then(function (r) { resultadoDaAcao(r); if (r && r.ok !== false && quem) { G.status = quem.nick + " foi removido do grupo."; renderiza(); } });
    } else if (acao === "de-novo") { G.erro = ""; renderiza(); }
    else if (acao === "transferir") { G.confirmando = "transferir"; renderiza(); }
    else if (acao === "confirma-transferir") {
      var alvo = G.alvoTransferencia || (outros()[0] || {}).usuario;
      G.confirmando = null;
      if (alvo) sala.transfere(alvo).then(resultadoDaAcao);
    } else if (acao === "encerrar") { G.confirmando = "encerrar"; renderiza(); }
    else if (acao === "confirma-encerrar") { G.confirmando = null; sala.encerra().then(resultadoDaAcao); }
    else if (acao === "cancela") { G.confirmando = null; renderiza(); }
    else if (acao === "seguir") { if (G.seguir) { G.seguir = false; renderiza(); } else voltaParaALider(); }
    else if (acao === "voltar") voltaParaALider();
    else if (acao === "sair") sair();
  }

  function outros() { return G.membros.filter(function (m) { return m.usuario !== G.uid; }); }

  /* ----------------------------------------------------------------------
     A aba "Grupo" (§14 e §8: caixa, título, botões de 44 px; a chave é um
     botão com aria-pressed; sem cor nova -- a ficha do membro é neutra, e
     --erro só para o erro do sistema)
     ---------------------------------------------------------------------- */
  function iniciais(nick) { return String(nick || "?").trim().slice(0, 2).toUpperCase(); }

  function chave(acao, ligada, texto, extra, mini) {
    return '<button type="button" class="chave' + (mini ? " mini" : "") + '" role="switch" aria-checked="' + (ligada ? "true" : "false") +
      '" data-acao="' + acao + '"' + (extra || "") + "><span>" + esc(texto) + '</span><span class="estado">' + (ligada ? "Ligado" : "Desligado") +
      '</span><span class="pino" aria-hidden="true"></span></button>';
  }

  /** Campo com o rótulo acima; o erro do campo (§19.6) vai em ✕ "Erro:" (--erro), ligado por aria-describedby. */
  function campoComErro(id, rotulo, valor, extraInput, campo, classeDoInput) {
    var erro = G.erroCampo && G.erroCampo.campo === campo ? G.erroCampo.texto : "";
    return '<label class="gr-campo" for="' + id + '">' + esc(rotulo) +
      '<input type="text" id="' + id + '"' + (classeDoInput ? ' class="' + classeDoInput + '"' : "") + extraInput + ' value="' + esc(valor) + '"' +
      (erro ? ' aria-invalid="true" aria-describedby="gr-e-' + campo + '"' : "") + ">" +
      (erro ? '<span class="erro-campo" id="gr-e-' + campo + '" role="alert">✕ Erro: ' + esc(erro) + "</span>" : "") + "</label>";
  }

  /** O rótulo do botão do convite: o mapa da página (o do link) e o nick que está no campo. */
  function textoDoConvite() {
    var nick = (G.form.nick || "").trim();
    return "Entrar no grupo da " + P.nomeDoMapa() + (nick ? " como " + nick : "");
  }
  /** Digitar no campo do nick muda o botão sem redesenhar a aba (o foco fica no campo). */
  function atualizaBotaoDoConvite() {
    var b = $("gr-entrar-convite");
    if (b) b.textContent = textoDoConvite();
  }

  /** Bloco de aviso: "info" (nada deu errado) ou "erro" (falha de sistema: --erro, ✕ e a palavra "Erro:"). */
  function aviso(tipo, texto, id) {
    return '<div class="gr-aviso ' + tipo + '" role="' + (tipo === "erro" ? "alert" : "status") + '"' + (id ? ' id="' + id + '"' : "") + ">" +
      (tipo === "erro" ? '<p><span aria-hidden="true">✕</span> <b>Erro:</b> ' + esc(texto) + "</p>"
                       : '<span class="ico" aria-hidden="true">i</span><p>' + esc(texto) + "</p>") + "</div>";
  }

  function linhaDoMembro(m, comControles) {
    var online = !!G.online[m.usuario], ehLider = m.usuario === G.lider, souEu = m.usuario === G.uid;
    var papel = ehLider ? "líder" : (G.todos || m.pode_desenhar ? "pode desenhar" : "só assiste");
    var h = '<li class="gr-membro' + (online ? "" : " offline") + '" data-usuario="' + esc(m.usuario) + '">' +
      '<span class="gr-ficha" aria-hidden="true">' + esc(iniciais(m.nick)) + "</span>" +
      '<span class="gr-nome"><span class="gr-quem"><b>' + esc(m.nick) + "</b>" + (souEu ? " (você)" : "") + "</span>" +
      '<small><span class="gr-online ponto-status' + (online ? " on" : "") + '" aria-hidden="true"></span>' + (online ? "online" : "offline") +
      " · " + esc(papel) + "</small></span>";
    if (comControles && !ehLider) {
      if (G.expulsando === m.usuario) {
        // "Expulsar nomad? Confirmar · Cancelar": confirmação em linha (decisão do Pedro sobre a §19); o foco vai para Cancelar
        h += '<span class="gr-controles gr-confirma-expulsa" role="group" aria-label="Confirmar a expulsão de ' + esc(m.nick) + '">' +
          '<span class="gr-pergunta">Expulsar <b>' + esc(m.nick) + "</b>?</span>" +
          '<button type="button" class="pr-b" data-acao="confirma-expulsa" data-usuario="' + esc(m.usuario) + '">Confirmar</button>' +
          '<button type="button" class="pr-b" id="gr-cancela-expulsa" data-acao="cancela-expulsa">Cancelar</button></span>';
      } else {
        h += '<span class="gr-controles">' +
          chave("permite", m.pode_desenhar, "Pode desenhar", ' data-usuario="' + esc(m.usuario) + '" aria-label="' + esc(m.nick) + ' pode desenhar"' +
                (G.encerrada ? ' disabled title="' + esc(RECUSA.encerrada) + '"' : ""), true) +
          '<button type="button" class="pr-b" data-acao="expulsa" data-usuario="' + esc(m.usuario) + '" aria-label="Expulsar ' + esc(m.nick) + '"' +
          (G.encerrada ? " disabled" : "") + ">Expulsar</button></span>";
      }
    }
    return h + "</li>";
  }

  /** O contador da aba (§19.6): quantos estão online; só com grupo. */
  function atualizaContador() {
    var aba = $("pr-aba-grupo");
    if (!aba) return;
    var c = aba.querySelector(".aba-contador");
    if (G.fase !== "dentro") { if (c) c.remove(); return; }
    var n = G.membros.filter(function (m) { return G.online[m.usuario]; }).length;
    if (!c) { c = document.createElement("span"); c.className = "aba-contador"; aba.appendChild(c); }
    c.textContent = String(n); c.setAttribute("aria-label", n + " online");
  }

  function cancelaExpulsao(devolveFoco) {
    var u = G.expulsando;
    G.expulsando = null;
    renderiza();
    if (devolveFoco && u) {
      var b = document.querySelector('#pr-painel-grupo .gr-membro[data-usuario="' + (window.CSS && CSS.escape ? CSS.escape(u) : u) + '"] [data-acao="expulsa"]');
      if (b) b.focus();
    }
  }

  /** B-3: o aviso de privacidade antes de criar ou entrar. `comNomes`: ao criar, lista os nomes de autor da tática
      que vão para o servidor (o campo "autor" da prancheta). Tudo passa por esc(); o contato é um link para abrir uma
      issue no GitHub (o site não tem e-mail). */
  function avisoDePrivacidade(comNomes) {
    var i = O_QUE_GUARDA.lastIndexOf(CONTATO_DO_AVISO);
    var texto = esc(O_QUE_GUARDA.slice(0, i)) + '<a href="' + esc(LINK_DO_CONTATO) + '" target="_blank" rel="noopener noreferrer">' +
      esc(CONTATO_DO_AVISO) + "</a>" + esc(O_QUE_GUARDA.slice(i + CONTATO_DO_AVISO.length));
    var nomes = comNomes ? nomesDeAutor() : [];
    G.nomesMostrados = comNomes ? nomes.join("\u0001") : G.nomesMostrados;
    var autores = nomes.length
      ? '<p class="gr-autores" id="gr-autores">Esta tática tem estes nomes de autor, que vão para o servidor: ' + esc(nomes.join(", ")) + ".</p>"
      : "";
    return '<div class="gr-aviso info gr-guarda"><span class="ico" aria-hidden="true">i</span><div><p id="gr-guarda-texto">' + texto + "</p>" + autores + "</div></div>";
  }

  function renderiza() {
    var painel = $("pr-painel-grupo");
    if (!painel) return;
    if (G.expulsando && !G.membros.some(function (m) { return m.usuario === G.expulsando; })) G.expulsando = null;
    var foco = document.activeElement && painel.contains(document.activeElement) ? document.activeElement.id : null;
    var h = '<section class="caixa gr-caixa"><h2>Grupo</h2>';
    if (soNoSite()) {
      var link = cfg.site ? cfg.site.replace(/\/?$/, "/") + (cfg.pagina || "") : "";
      h += '<p class="gr-texto">' + esc(SO_NO_SITE) + (link ? ' <a href="' + esc(link) + '">' + esc(link) + "</a>" : "") + "</p>";
    } else if (G.fase !== "dentro" && G.erro) {
      // grupo indisponível: o formulário some (criar ou entrar falharia); a prancheta segue sozinha
      h += aviso("erro", G.erro, "gr-erro") + '<button type="button" class="pr-b gr-largo" data-acao="de-novo">Tentar de novo</button>' +
        '<p class="gr-texto gr-apagado">' + esc(SEM_O_GRUPO) + "</p>";
    } else if (G.fase !== "dentro" && G.convite && !(G.erroCampo && G.erroCampo.campo === "codigo")) {
      // §19.6 "Convite": o link trouxe o código e o nick está salvo; o campo do nick fica editável ao lado do botão
      var ocupadoC = G.fase === "entrando";
      if (G.info) h += aviso("info", G.info, "gr-info");
      h += '<div class="gr-convite">' +
        campoComErro("gr-nick", "Seu nick", G.form.nick, ' maxlength="24" autocomplete="nickname"', "nick") +
        '<button type="button" class="pr-b gr-principal gr-largo" id="gr-entrar-convite" data-acao="entrar-convite"' + (ocupadoC ? " disabled" : "") + ">" +
        esc(textoDoConvite()) + "</button>" +
        '<button type="button" class="pr-b gr-largo gr-outro" data-acao="convite-outro"' + (ocupadoC ? " disabled" : "") + ">Criar grupo ou usar outro código</button></div>" +
        avisoDePrivacidade(false);
    } else if (G.fase !== "dentro") {
      G.convite = null;
      var ocupado = G.fase === "entrando";
      if (G.info) h += aviso("info", G.info, "gr-info");
      h += '<p class="gr-texto">Desenhe a tática junto, ao vivo: crie um grupo e mande o link, ou entre com o código.</p>' +
        campoComErro("gr-nick", "Seu nick", G.form.nick, ' maxlength="24" autocomplete="nickname"', "nick") +
        '<button type="button" class="pr-b gr-principal gr-largo" data-acao="criar"' + (ocupado ? " disabled" : "") + ">Criar grupo</button>" +
        '<div class="gr-ou" aria-hidden="true">ou</div>' +
        campoComErro("gr-codigo", "Código do grupo", G.form.codigo, ' maxlength="8" autocomplete="off" spellcheck="false"', "codigo", "codigo") +
        '<button type="button" class="pr-b gr-largo" data-acao="entrar"' + (ocupado ? " disabled" : "") + ">Entrar num grupo</button>" +
        avisoDePrivacidade(true);
    } else {
      h += '<div class="gr-codigo-linha"><span class="gr-rotulo">Código</span> <span class="gr-codigo" id="gr-codigo-sala">' + esc(G.codigo) + "</span>" +
        (G.papel === "lider" ? '<button type="button" class="pr-b" data-acao="copiar">Copiar link</button>' : "") + "</div>";
      if (G.encerrada) h += aviso("info", RECUSA.encerrada, "gr-encerrada");
      if (G.papel === "lider") {
        h += chave("todos", G.todos, "Todos podem desenhar", G.encerrada ? ' disabled title="' + esc(RECUSA.encerrada) + '"' : "");
      } else {
        h += '<p class="gr-permissao" id="gr-permissao">' + esc(podeDesenhar() ? "✎ Você pode desenhar" : (G.encerrada ? "Só leitura" : "Só a líder desenha agora")) + "</p>" +
          chave("seguir", G.seguir, "Seguir a líder") +
          (G.seguir ? "" : '<button type="button" class="pr-b gr-largo" data-acao="voltar">Voltar para a líder</button>');
      }
      h += '<h3 class="gr-sub">Membros (' + G.membros.length + " de " + Sala.MAX_MEMBROS + ')</h3><ul class="gr-membros">' +
        G.membros.map(function (m) { return linhaDoMembro(m, G.papel === "lider"); }).join("") + "</ul>";
      if (G.papel === "lider" && !G.encerrada) {
        if (G.confirmando === "transferir") {
          var lista = outros();
          h += '<div class="gr-confirma"><label class="gr-campo" for="gr-transferir-para">Transferir a liderança para</label>' +
            '<select id="gr-transferir-para">' + lista.map(function (m) {
              return '<option value="' + esc(m.usuario) + '"' + (m.usuario === G.alvoTransferencia ? " selected" : "") + ">" + esc(m.nick) + "</option>";
            }).join("") + "</select>" +
            '<div class="gr-linha"><button type="button" class="pr-b gr-principal" data-acao="confirma-transferir"' + (lista.length ? "" : " disabled") + ">Transferir</button>" +
            '<button type="button" class="pr-b" data-acao="cancela">Cancelar</button></div>' +
            '<p class="gr-texto gr-apagado">Você vira membro e só desenha se a nova líder liberar.</p></div>';
        } else if (G.confirmando === "encerrar") {
          h += '<div class="gr-confirma"><p class="gr-texto"><b>Encerrar o grupo?</b> A tática fica só para leitura para todos, e ninguém mais entra.</p>' +
            '<div class="gr-linha"><button type="button" class="pr-b gr-principal" data-acao="confirma-encerrar">Encerrar de vez</button>' +
            '<button type="button" class="pr-b" data-acao="cancela">Cancelar</button></div></div>';
        } else {
          var sozinha = !outros().length;
          h += '<div class="gr-linha"><button type="button" class="pr-b" data-acao="transferir"' + (sozinha ? ' disabled title="' + esc(SOZINHA) + '"' : "") +
            ">Transferir liderança</button>" +
            '<button type="button" class="pr-b" data-acao="encerrar">Encerrar grupo</button></div>' +
            (sozinha ? '<p class="gr-texto gr-apagado" id="gr-sozinha">' + esc(SOZINHA) + "</p>" : "");
        }
      }
      if (G.papel !== "lider" || G.encerrada) h += '<button type="button" class="pr-b gr-largo" data-acao="sair">Sair do grupo</button>';
    }
    h += '<p class="gr-status" id="gr-status" role="status" aria-live="polite">' + esc(G.status) + "</p>";
    if (G.fase === "dentro" && G.erro) h += aviso("erro", G.erro, "gr-erro");
    h += "</section>";
    painel.innerHTML = h;
    atualizaContador();
    if (G.expulsando && $("gr-cancela-expulsa") && foco !== "gr-cancela-expulsa") $("gr-cancela-expulsa").focus();
    else if (foco && $(foco)) $(foco).focus();
  }

  return {
    prepara: prepara,
    _interno: {
      G: function () { return G; }, sala: function () { return sala; }, podeDesenhar: podeDesenhar,
      criar: criar, entrar: entrar, sair: sair, renderiza: renderiza, sincroniza: sincroniza,
      impedimento: impedimento, linkDaSala: linkDaSala,
      DURACAO_DA_ETIQUETA_MS: DURACAO_DA_ETIQUETA_MS, RECUSA: RECUSA, INDISPONIVEL: INDISPONIVEL, SO_NO_SITE: SO_NO_SITE,
      O_QUE_GUARDA: O_QUE_GUARDA, DESCARTADA: DESCARTADA, LINK_DO_CONTATO: LINK_DO_CONTATO, nomesDeAutor: nomesDeAutor
    }
  };
})();
