  /* ---------------------------------------------------------------------
     O que o grupo (grupo.js) usa da prancheta. Nenhuma destas funções cria
     operação: recebe as de fora, tira as que o servidor recusou e lê/segue o
     cabeçote.
     --------------------------------------------------------------------- */
  /** Operações que chegaram da sala entram no log SEM reemitir e sem ir para o
      desfazer de ninguém; a repetida (mesmo id) não entra duas vezes. O contador
      sobe como no relógio de Lamport (o mesmo da mescla). */
  function recebeDeFora(ops) {
    var ja = Object.create(null), descartadas = 0;
    S.doc.operacoes.forEach(function (o) { ja[o.id] = true; });
    var novas = (ops || []).filter(function (o) {
      // a MESMA validação de operação do arquivo e da tática guardada (B-1); a inválida nem entra no log
      if (problemaDaOperacao(o, ANDARES.length, FORMATO).length) { descartadas++; return false; }
      if (ja[o.id]) return false;
      ja[o.id] = true;
      return true;
    });
    var entraram = 0;
    if (novas.length) {
      var tamanho = S.doc.operacoes.length, contador = S.doc.contador;
      novas.forEach(function (o) {
        S.doc.operacoes.push(copia(o));
        S.doc.contador = Math.max(S.doc.contador, o.seq);
      });
      try { reaplica(); entraram = novas.length; } catch (e) {
        // alguma do lote derruba a prancheta: desfaz o lote inteiro e tenta uma por uma, ficando só com as que passam
        S.doc.operacoes.length = tamanho; S.doc.contador = contador;
        novas.forEach(function (o) {
          var t = S.doc.operacoes.length, c = S.doc.contador;
          S.doc.operacoes.push(copia(o));
          S.doc.contador = Math.max(S.doc.contador, o.seq);
          try { reaplica(); entraram++; } catch (e2) {
            S.doc.operacoes.length = t; S.doc.contador = c;
            descartadas++;
          }
        });
        try { reaplica(); } catch (e3) { /* o estado de antes não lança */ }
      }
      if (entraram) agendaGravacao();
    }
    if (descartadas) {
      // só a contagem: nada da operação (nem tipo, nem autor, nem campo) vai para o console
      console.warn("[prancheta] " + descartadas + " alteração(ões) recebida(s) descartada(s) por formato inválido");
      if (ganchos.aoDescartar) ganchos.aoDescartar(descartadas);
    }
    return entraram;
  }
  /** Operações LOCAIS que o servidor recusou: nunca chegaram ao log da sala, então
      saem do log daqui (e do desfazer e do refazer) -- é a ação desfeita. */
  function retiraRecusadas(ids) {
    var fora = {};
    (ids || []).forEach(function (id) { fora[id] = true; });
    var antes = S.doc.operacoes.length;
    S.doc.operacoes = S.doc.operacoes.filter(function (o) { return !fora[o.id]; });
    function limpaPilha(p) {
      return p.map(function (item) { return [].concat(item).filter(function (id) { return !fora[id]; }); })
        .filter(function (item) { return item.length; })
        .map(function (item) { return item.length === 1 ? item[0] : item; });
    }
    S.pilhaDesfazer = limpaPilha(S.pilhaDesfazer);
    S.pilhaRefazer = limpaPilha(S.pilhaRefazer);
    if (S.doc.operacoes.length === antes) return 0;
    S.chegada = null;
    reaplica();
    agendaGravacao();
    return antes - S.doc.operacoes.length;
  }
  /** Abre o documento da sala (cabeçalho + operações) no lugar da tática aberta.
      Devolve o motivo da recusa (mapa, calibração, arquivo inválido) ou "". */
  function usaDocumento(doc) {
    var erro = motivoDaRecusa(doc);
    if (erro) return erro;
    confirmaGiro();
    var anterior = S.doc, passoAntes = S.passo;
    S.doc = migra(copia(doc));
    S.passo = 0; S.sel = null; S.busca = null; S.caminho = null; S.acao = null; S.chegada = null;
    S.pilhaDesfazer = []; S.pilhaRefazer = [];
    bancoDe = null;
    try { reaplica(); } catch (e) {
      S.doc = anterior; S.passo = passoAntes; bancoDe = null;
      try { reaplica(); } catch (e2) { /* a tela já estava assim */ }
      return "o formato de uma operação não pôde ser lido";
    }
    Armazem.aberta(cfg.mapa, S.doc.id);
    gravaAgora();
    return "";
  }
  /** O cabeçote de agora: no editor, o horário; na reprodução, o horário, o play e a velocidade. */
  function cabecote() {
    var r = S.reproducao;
    return r ? { modo: "reproducao", t: r.t, tocando: !!r.tocando, velocidade: r.velocidade } : { modo: "editor", t: S.t };
  }
  /** Leva o cabeçote (e o play) ao estado de outra pessoa -- "Seguir a líder". */
  function segueCabecote(c) {
    if (!c || !ehNumero(c.t) || !S.estado) return;
    if (c.modo === "reproducao") {
      if (!S.reproducao) comecaReproducao();
      if (MapCore.VELOCIDADES.indexOf(c.velocidade) >= 0) S.reproducao.velocidade = c.velocidade;
      reproduzAte(c.t);
      toca(!!c.tocando);
    } else {
      if (S.reproducao) editaAqui();
      defineTempo(c.t);
    }
  }
  function limpaHistorico() { S.pilhaDesfazer = []; S.pilhaRefazer = []; atualizaBarra(); }

  return {
    init: init,
    recebeBiblioteca: recebeBiblioteca,
    ganchos: ganchos,
    grupo: {
      recebe: recebeDeFora, retira: retiraRecusadas,
      operacaoValida: function (op) { return !problemaDaOperacao(op, ANDARES.length, FORMATO).length; }, usaDocumento: usaDocumento, cabecote: cabecote,
      segueCabecote: segueCabecote, limpaHistorico: limpaHistorico, atualizaDica: atualizaDica,
      nomeDoMapa: function () {
        var m = (cfg.mapas || []).filter(function (x) { return x.mapa === cfg.mapa; })[0];
        return (m && m.nome) || cfg.mapa || "";
      },
      documento: function () { return S.doc; }, estado: function () { return S.estado; },
      tipos: function () { return Object.keys(OPERACOES); },   // a lista de tipos de operação (a do servidor é conferida contra ela)
      emReproducao: function () { return !!S.reproducao; }, aplica: aplica, chaveDeOrdem: chaveDeOrdem
    },
    _interno: {
      S: S, aplica: aplica, mescla: mescla, posicaoNoPasso: posicaoNoPasso, migra: migra,
      quadroDoPasso: quadroDoPasso, ordemDeCriacao: ordemDeCriacao, anuladas: anuladas,
      estadoNoTempo: estadoNoTempo, linhaDoTempo: linhaDoTempo,
      taticaNoTempo: taticaNoTempo, quadroNoTempo: quadroNoTempo, posicaoNoTempo: posicaoNoTempo,
      problemasNoTempo: problemasNoTempo,
      vooEstimado: vooEstimado, velocidade: velocidade, M3: function () { return M3; },
      defineTempo: defineTempo, abaDoPainel: abaDoPainel, douglasPeucker: douglasPeucker, noMarco: noMarco, emiteLote: emiteLote,
      TOLERANCIA_DP_PX: TOLERANCIA_DP_PX,
      criaDoRound: criaDoRound, voltaAoReal: voltaAoReal, alternaFantasma: alternaFantasma, e3Real: e3Real,
      cortaReal: cortaReal, baseReal: baseReal,
      atrasosDosPontos: atrasosDosPontos, atualizaTudo: atualizaTudo, adiaArremesso: adiaArremesso, lugarDe: lugarDe, eventosDe: eventosDe, eventoEm: eventoEm,
      fimDaTatica: fimDaTatica, cenaNoRelogio: cenaNoRelogio, tocaNoRelogio: tocaNoRelogio, relogioEm: relogioEm, mudaHorarioDaGranada: mudaHorarioDaGranada, reproduzAte: function (t) { reproduzAte(t); },
      comecaReproducao: comecaReproducao, editaAqui: editaAqui, toca: function (s) { toca(s); },
      problemas: problemas, problemaDaOperacao: problemaDaOperacao, problemasDaOrigem: problemasDaOrigem, textoDaOrigem: textoDaOrigem,
      centro: function () { return CENTRO; },
      jogoParaPixel: jogoParaPixel, pixelParaJogo: pixelParaJogo,
      importaTexto: importaTexto, gravaAgora: gravaAgora, busca: busca, usaArremesso: usaArremesso,
      desfaz: desfaz, refaz: refaz, aplicaZoom: aplicaZoom, reprojeta: reprojeta,
      alca: function (id) { var p = quadro().pecas[id]; return alca(jogoParaPixel(p.x, p.y), yawDaPeca(id, p)); },
      FERRAMENTAS_TRACO: FERRAMENTAS_TRACO, ESPESSURAS: ESPESSURAS, FORMATO: FORMATO,
      ESTADOS: ESTADOS, estadoDaInteracao: estadoDaInteracao, dicaAtual: dicaAtual,
      descreveFontes: descreveFontes,
      ATALHOS: ATALHOS.map(function (x) { return { tecla: x.tecla, rotulo: x.rotulo, acao: x.acao }; }),
      LIMIAR_ARRASTO_PX: LIMIAR_ARRASTO_PX,
      armazem: function () { return Armazem; },
      radar: function () { return cfg.radar; },
      biblioteca: function () { return cfg.biblioteca; }
    }
  };
