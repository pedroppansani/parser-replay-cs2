  /* ---------------------------------------------------------------------
     Ganchos do GRUPO (fase 13; dashboard/web/grupo.js, só no build com grupo).
     Sem grupo nenhum é preenchido e a prancheta é a de sempre. O grupo só
     TRANSPORTA operações: nenhuma muda de significado (decisão 47).
       autor()         o nick da sala, para as operações emitidas no grupo
       aoEmitir(op)    cada operação local, logo depois de entrar no log
       aoMudarTempo()  o cabeçote ou o play mudou por ação da pessoa
       aoAtualizar()   fim de cada atualizaTudo (o grupo liga/desliga controles)
       aoIniciar()     fim do init (o grupo monta a aba dele)
       aoDescartar(n)  n operações recebidas foram descartadas pela validação (B-1)
       dica()          texto que vale no lugar da linha de dica, ou ""
       abas            abas extras do painel, como em ABAS_DO_PAINEL
     --------------------------------------------------------------------- */
  var ganchos = {};
  function avisaTempo() { if (ganchos.aoMudarTempo) ganchos.aoMudarTempo(); }

  /** Toda mudança passa por aqui: uma operação nova no log. `desfazivel` põe o
      id na pilha de desfazer desta sessão (e limpa o refazer: ramo novo). */
  function emite(tipo, dados, desfazivel) {
    if (S.giro && tipo !== "gira_peca") confirmaGiro();
    var op = { id: novoId(), seq: S.doc.contador + 1, autor: autor(), em: agora(), tipo: tipo };
    Object.keys(dados).forEach(function (k) { op[k] = dados[k]; });
    S.doc.contador = op.seq;
    S.doc.operacoes.push(op);
    if (desfazivel !== false && DESFAZER.indexOf(tipo) < 0) {
      S.pilhaDesfazer.push(op.id);
      S.pilhaRefazer = [];
    }
    reaplica();
    agendaGravacao();
    if (ganchos.aoEmitir) ganchos.aoEmitir(op);
    return op;
  }

  function reaplica() {
    S.estado = aplica(S.doc.operacoes);
    S.e3 = M3 ? taticaNoTempo(S.doc.operacoes) : null;
    S.passo = Math.max(0, Math.min(S.passo, S.estado.passos.length - 1));
    if (S.sel) {
      var grupo = { peca: "pecas", granada: "granadas", traco: "tracos" }[S.sel.tipo];
      if (!S.estado[grupo][S.sel.id]) S.sel = null;
    }
    atualizaTudo();
  }

  // Uma AÇÃO pode emitir mais de uma operação (o caminho com o ponto do
  // arremesso, o "esperar aqui" que empurra os pontos seguintes): a pilha guarda
  // o lote, e desfazer anula o lote inteiro -- uma ação, um Ctrl+Z.
  function emiteLote(lista) {
    var ids = lista.map(function (par) { return emite(par[0], par[1], false).id; });
    if (ids.length) { S.pilhaDesfazer.push(ids.length === 1 ? ids[0] : ids); S.pilhaRefazer = []; }
    return ids;
  }

  function desfaz() {
    confirmaGiro();
    S.chegada = null;
    var fora = anuladas(S.doc.operacoes);
    while (S.pilhaDesfazer.length) {
      var item = S.pilhaDesfazer.pop();
      var ids = [].concat(item).filter(function (id) { return !fora[id]; });
      if (!ids.length) continue;
      ids.forEach(function (id) { emite("anula", { alvo: id }); });
      S.pilhaRefazer.push(item);
      return true;
    }
    return false;
  }

  function refaz() {
    confirmaGiro();
    if (!S.pilhaRefazer.length) return false;
    var item = S.pilhaRefazer.pop();
    [].concat(item).forEach(function (id) { emite("reativa", { alvo: id }); });
    S.pilhaDesfazer.push(item);
    return true;
  }

  function vazia(doc) { return doc.operacoes.length <= OPS_DA_CRIACAO; }

  function agendaGravacao() {
    clearTimeout(timerGravar);
    timerGravar = setTimeout(gravaAgora, ATRASO_GRAVACAO_MS);
  }
  function gravaAgora() {
    clearTimeout(timerGravar);
    if (!S.doc) return;
    Armazem.aberta(cfg.mapa, S.doc.id);
    if (!vazia(S.doc)) {
      S.aviso = Armazem.grava(S.doc) ? "" : "Não foi possível gravar neste navegador: exporte o arquivo para não perder.";
    }
    S.gravacoes++;
    atualizaBiblioteca();
    atualizaAviso();
  }

  function novaTatica() {
    S.doc = {
      formato: IDENTIFICADOR, versao: FORMATO, id: novoId(), mapa: cfg.mapa,
      criada_por: autor(), criada_em: agora(), calibracao: cfg.radar.calibracao,
      contador: 0, operacoes: []
    };
    S.passo = 0; S.sel = null; S.busca = null;
    S.pilhaDesfazer = []; S.pilhaRefazer = [];
    emite("renomeia", { titulo: "Nova tática" }, false);
    emite("cria_passo", { passo: novoId(), titulo: "" }, false);
    gravaAgora();
  }

  var AVISO_DA_RECUSADA = "A tática que estava guardada neste navegador tinha um formato inválido e não foi aberta: " +
    "uma cópia ficou guardada à parte e esta é uma tática nova.";

  /** Abre a tática guardada. Nunca lança e nunca trava o init: documento que a validação recusa (ou que faz o
      reaplica lançar) vai para a chave `...:recusada` do armazém, a tela volta ao que estava e devolve false. */
  function abre(id) {
    var doc = Armazem.carrega(id);
    if (!doc || VERSOES_ACEITAS.indexOf(doc.versao) < 0) return false;
    var antes = { doc: S.doc, passo: S.passo, sel: S.sel, busca: S.busca, desfazer: S.pilhaDesfazer, refazer: S.pilhaRefazer };
    var boa = false;
    try {
      if (!problemas(doc, ANDARES.length).length) {
        S.doc = migra(doc);
        S.passo = 0; S.sel = null; S.busca = null;
        S.pilhaDesfazer = []; S.pilhaRefazer = [];
        reaplica();
        boa = true;
      }
    } catch (e) { boa = false; }
    if (boa) { Armazem.aberta(cfg.mapa, S.doc.id); return true; }
    S.doc = antes.doc; S.passo = antes.passo; S.sel = antes.sel; S.busca = antes.busca;
    S.pilhaDesfazer = antes.desfazer; S.pilhaRefazer = antes.refazer;
    if (S.doc) { try { reaplica(); } catch (e) { /* a tela já estava assim */ } }
    if (Armazem.recusa) Armazem.recusa(id, doc);
    console.warn("[prancheta] tática guardada recusada pela validação e movida para a chave :recusada");
    S.aviso = AVISO_DA_RECUSADA;
    return false;
  }

  function passoAtual() { return S.estado.passos[S.passo].passo; }
  function indiceDoPasso(passo) {
    for (var i = 0; i < S.estado.passos.length; i++) if (S.estado.passos[i].passo === passo) return i;
    return -1;
  }
  // O editor mostra a tática NO CABEÇOTE (formato 3). `quadro(i)` com o índice
  // de um passo continua sendo o quadro daquele passo (o rastro do anterior).
  var EPS_T = 1e-6;
  function quadro(i) {
    if (i !== undefined || !S.e3) return quadroDoPasso(S.estado, i === undefined ? S.passo : i, CENTRO);
    var f = quadroNoTempo(S.e3, S.t, CENTRO), p = S.estado.passos[S.passo] || {}, granadas = {};
    Object.keys(f.granadas).forEach(function (id) {
      var g = f.granadas[id];
      // "nasceu aqui": jogada no horário do cabeçote -- é a que se edita
      granadas[id] = Object.assign({}, g, { nasceu_neste_passo: Math.abs(g.t - S.t) < EPS_T });
    });
    return { indice: S.passo, passo: p.passo, titulo: p.titulo, duracao_s: p.duracao_s,
             pecas: f.pecas, granadas: granadas, tracos: f.tracos, relogio: f.relogio, bomba: f.bomba, mortos: f.mortos };
  }

  /** O cabeçote está no horário de um marco (passo)? Ali, editar emite as
      operações do formato 2, que viram pontos-chave naquele horário. */
  function noMarco() {
    if (!S.e3) return true;
    var m = S.e3.marcos[S.passo];
    return !!m && Math.abs(m.t - S.t) < EPS_T;
  }
  function marcoQueContem(t) {
    var k = 0;
    (S.e3 ? S.e3.marcos : []).forEach(function (m, i) { if (m.t <= t + EPS_T) k = i; });
    return k;
  }
  function pontoNoHorario(pid) {
    var p = S.e3 && S.e3.pecas[pid];
    if (!p) return null;
    return p.pontos.filter(function (pt) { return !pt.fora && Math.abs(pt.t - S.t) < EPS_T; }).pop() || null;
  }
  function limiteDoTempo() {
    return S.e3 && S.e3.bomba ? S.e3.bomba.t + M3.SEGUNDOS_DA_BOMBA : (M3 ? M3.SEGUNDOS_DO_ROUND : 0);
  }
  /** Leva o cabeçote a t (e o passo atual ao marco que contém t). */
  function defineTempo(t) {
    confirmaGiro();
    S.chegada = null;
    S.t = Math.max(0, Math.min(limiteDoTempo(), Math.round(t * 100) / 100));
    S.passo = marcoQueContem(S.t);
    if (S.caminho && !S.caminho.pontos.length) iniciaCaminho(S.caminho.peca);
    atualizaTudo();
    avisaTempo();
  }

  /** Grava a posição da peça NO HORÁRIO DO CABEÇOTE: no marco, o move_peca de
      sempre; fora dele, o ponto-chave daquele horário (move_ponto) ou um novo. */
  function gravaPosicao(pid, x, y, nivel) {
    if (baseReal() !== null && S.t > EPS_T) {
      // Num round do replay, mover alguém em t não é teletransporte: ele sai de
      // onde estava DE VERDADE em t e chega lá na velocidade medida da função
      // dele (correndo). Antes de t, nada muda.
      var meu = pontoNoHorario(pid);
      if (meu && !ehPontoReal(pid, meu)) {
        emite("move_ponto", { peca: pid, ponto: meu.id, t: S.t, x: x, y: y, nivel: nivel });
        return;
      }
      var q = quadro().pecas[pid];
      if (!q) return;
      var chega = Math.round((S.t + Math.hypot(x - q.x, y - q.y) / velocidade(funcaoDe(pid), "correndo")) * 100) / 100;
      emiteNaPeca(pid, S.t, [["cria_caminho", { peca: pid, pontos: [{ t: chega, x: x, y: y, nivel: nivel }] }]]);
      // quem arrastou VÊ quando ele chega (resposta 3 do Pedro): a peça continua
      // no lugar em t, e sem isso pareceria que o arrasto não funcionou
      S.chegada = { peca: pid, t: chega, desde: S.t, x: x, y: y, nivel: nivel };
      atualizaDica(); desenha();
      return;
    }
    if (noMarco()) { emiteNaPeca(pid, S.t, [["move_peca", { peca: pid, passo: passoAtual(), x: x, y: y, nivel: nivel }]]); return; }
    var pt = pontoNoHorario(pid);
    if (pt) emiteNaPeca(pid, S.t, [["move_ponto", { peca: pid, ponto: pt.id, t: S.t, x: x, y: y, nivel: nivel }]]);
    else emiteNaPeca(pid, S.t, [["cria_caminho", { peca: pid, pontos: [{ t: S.t, x: x, y: y, nivel: nivel }] }]]);
  }
  /** O mesmo para a direção (botão direito, alça, Q/E). */
  function gravaYaw(pid, yaw) {
    if (noMarco() && !(baseReal() !== null && S.t > EPS_T)) {
      emiteNaPeca(pid, S.t, [["gira_peca", { peca: pid, passo: passoAtual(), yaw: yaw }]]); return;
    }
    var q = quadro().pecas[pid];
    if (!q) return;
    var pt = pontoNoHorario(pid);
    if (baseReal() !== null && pt && ehPontoReal(pid, pt)) {
      // o ponto real em t fica (âncora); a nova direção é um ponto do usuário no mesmo lugar
      emiteNaPeca(pid, S.t, [["cria_caminho", { peca: pid, pontos: [{ t: S.t, x: pt.x, y: pt.y, nivel: pt.nivel, yaw: yaw }] }]]);
      return;
    }
    if (pt) emiteNaPeca(pid, S.t, [["move_ponto", { peca: pid, ponto: pt.id, t: S.t, x: pt.x, y: pt.y, nivel: pt.nivel, yaw: yaw }]]);
    else emiteNaPeca(pid, S.t, [["cria_caminho", { peca: pid, pontos: [{ t: S.t, x: q.x, y: q.y, nivel: q.nivel, yaw: yaw }] }]]);
  }

