  /* ---------------------------------------------------------------------
     Ponteiro
     --------------------------------------------------------------------- */
  /** O que está sob o ponteiro (pixel do radar). Só o andar ativo é tocável:
      o que está esmaecido não se mexe sem querer. */
  function acha(px) {
    var q = quadro(), achado = null, melhor = Infinity;
    function perto(c, raio, qual) {
      var d = Math.hypot(c[0] - px[0], c[1] - px[1]);
      if (d <= raio && d < melhor) { melhor = d; achado = qual; }
    }
    if (S.sel && S.sel.tipo === "peca" && q.pecas[S.sel.id] && q.pecas[S.sel.id].nivel === S.andar) {
      var ps = q.pecas[S.sel.id];
      perto(alca(jogoParaPixel(ps.x, ps.y), ps.yaw), RAIO_ALCA + 3, { tipo: "giro", id: S.sel.id });
      if (achado) return achado;
    }
    Object.keys(q.pecas).forEach(function (id) {
      var p = q.pecas[id];
      if (p.nivel === S.andar) perto(jogoParaPixel(p.x, p.y), RAIO_PECA + 3, { tipo: "peca", id: id });
    });
    Object.keys(q.granadas).forEach(function (id) {
      var g = q.granadas[id];
      if (g.nivel !== S.andar || !g.nasceu_neste_passo) return;   // só se mexe no passo em que nasceu
      perto(jogoParaPixel(g.destino[0], g.destino[1]), RAIO_PONTA_GRANADA + 3, { tipo: "granada", id: id, ponta: "destino" });
      if (!g.origem_desconhecida) perto(jogoParaPixel(g.origem[0], g.origem[1]), RAIO_PONTA_GRANADA, { tipo: "granada", id: id, ponta: "origem" });
    });
    return achado;
  }

  function comecaPan(e) {
    if (S.view.zoom <= 1) return false;
    S.pan = { x: e.clientX, y: e.clientY, panX: S.view.panX, panY: S.view.panY };
    cv.setPointerCapture(e.pointerId);
    return true;
  }

  /* ---------------------------------------------------------------------
     Interação: UMA máquina de estados (prancheta fluida, 2026-09-27)

     Cada clique faz uma coisa previsível, e a linha de dica diz qual é ANTES
     do clique. O estado sai de três campos -- a ferramenta de desenho, a ação
     pendente e a seleção -- e nunca de condições espalhadas pelos handlers.
     Nada aqui cria operação nova: mover por clique emite o mesmo move_peca,
     virar emite o mesmo gira_peca, granada o mesmo cria_granada.
     --------------------------------------------------------------------- */
  // Ponteiro que anda menos que isto (px de tela) entre apertar e soltar é
  // CLIQUE; acima, ARRASTO. É a única distinção entre os dois no editor.
  var LIMIAR_ARRASTO_PX = 4;

  function nomePeca(id) { var p = S.estado.pecas[id]; return p ? rotuloDaPeca(p) : ""; }

  /** O estado atual da interação, pelo nome da tabela. */
  function estadoDaInteracao() {
    if (ROTULO_FERRAMENTA[S.ferramenta] || S.ferramenta === "borracha") return "desenhando";
    var a = S.acao;
    if (S.caminho && !(a && (a.tipo === "granada" || a.tipo === "busca" || a.tipo === "colocar"))) return "tracando_caminho";
    if (a && a.tipo === "colocar") return "colocando_peca";
    if (a && a.tipo === "busca") return "buscando";
    if (a && a.tipo === "granada") return a.origem ? "granada_destino" : "granada_origem";
    if (S.sel && S.sel.tipo === "peca") return "peca_selecionada";
    if (S.sel && S.sel.tipo === "granada") return "granada_selecionada";
    return "livre";
  }

  /** A tabela da máquina: como se entra, o que o próximo clique faz e a dica.
      A dica recebe o contexto (nomes, arma) e é a MESMA função que a tela usa. */
  var ESTADOS = {
    livre: { entra: "padrão; Esc", clique: "seleciona peça, granada ou traço; no vazio, nada",
      dica: function () { return "Clique num jogador para selecionar, ou escolha uma ferramenta"; } },
    peca_selecionada: { entra: "clique numa peça, ou no nome dela no banco",
      clique: "no vazio: a peça vai para lá no horário do cabeçote (move_peca no marco); em outra peça: seleciona a outra; botão direito: vira para o ponto (gira_peca)",
      dica: function (c) { return c.peca + " selecionado · clique no mapa para mover · botão direito para virar · 1–4 joga granada"; } },

    colocando_peca: { entra: "clique numa ficha do banco fora do mapa neste passo",
      clique: "cria (ou recoloca) a peça ali e a seleciona",
      dica: function (c) { return "Clique no mapa para colocar " + c.ficha + " · Esc cancela"; } },
    granada_destino: { entra: "tipo de granada com uma peça selecionada (ou origem já escolhida)",
      clique: "o destino: cria a granada e mostra os arremessos reais que caem ali",
      dica: function (c) { return c.arma + " de " + c.origem + " · clique onde ela deve cair"; } },
    granada_origem: { entra: "tipo de granada sem peça selecionada",
      clique: "numa peça: ela é a origem; no vazio: o ponto é a origem",
      dica: function (c) { return c.arma + " · clique em quem joga (ou no ponto de onde sai)"; } },
    granada_selecionada: { entra: "clique numa granada nascida neste passo",
      clique: "no vazio: muda onde ela cai (move_granada)",
      dica: function (c) { return c.arma + " selecionada · clique para mudar onde cai" + (c.real ? " (desfaz o arremesso real)" : ""); } },
    desenhando: { entra: "uma ferramenta de desenho",
      clique: "arrastar desenha; a borracha apaga o traço sob o clique; a granada desenhada carimba no clique",
      dica: function (c) {
        if (c.granadaDesenho) return "Granada (desenho) · clique carimba a " + c.granadaDesenho + " · 1 a 4 trocam o tipo · " +
          "setas e Enter pelo teclado · V volta a selecionar";
        return c.ferramenta + " · arraste para desenhar · V volta a selecionar";
      } },
    buscando: { entra: "“Buscar arremesso” no painel",
      clique: "lista os arremessos reais que caem perto do ponto",
      dica: function (c) { return "Buscar " + c.arma + " · clique onde ela deve cair"; } }
  };

  // os textos do caminho por clique
  var ESTADO_TRACANDO = { entra: "clique numa peça, sem arrastar",
    clique: "acrescenta um ponto ao caminho (arrastar desenha à mão); Enter ou duplo clique conclui (um cria_caminho); Backspace tira o último ponto; Esc cancela o trecho",
    dica: function (c) { return c.peca + " · clique para marcar o caminho · arraste para desenhar à mão · Enter conclui · Esc cancela"; } };
  var PECA_COM_CAMINHO = { entra: "Esc durante um caminho, ou o nome dela no banco",
    clique: "no vazio: começa um caminho até lá (não teleporta: teleportar é arrastar); em outra peça: seleciona a outra; botão direito: vira para o ponto no horário do cabeçote",
    dica: function (c) { return c.peca + " selecionado · clique no mapa para traçar o caminho · arraste a peça para mover · botão direito para virar · 1–4 joga granada"; } };
  ESTADOS.tracando_caminho = ESTADO_TRACANDO; ESTADOS.peca_selecionada = PECA_COM_CAMINHO;

  function contextoDaDica() {
    var a = S.acao || {}, g = S.sel && S.sel.tipo === "granada" ? S.estado.granadas[S.sel.id] : null;
    var origem = a.de ? nomePeca(a.de) : "um ponto";
    return {
      peca: S.sel && S.sel.tipo === "peca" ? nomePeca(S.sel.id) : "",
      ficha: a.rotulo ? (a.lado === "ct" ? "CT " : "TR ") + a.rotulo : "",
      arma: NOME_ARMA[a.arma || (g && g.arma) || S.arma],
      origem: origem,
      real: !!(g && g.arremesso),
      ferramenta: ROTULO_FERRAMENTA[S.ferramenta] || (S.ferramenta === "borracha" ? "Borracha" : ""),
      granadaDesenho: S.ferramenta === "granada_desenho" ? NOME_ARMA[S.armaDesenho] : null
    };
  }

  /** O que o grupo põe na linha de dica (grupo.js): {texto, html, classe, etiqueta} ou null. Sem grupo, nada. */
  function dicaDoGrupo() { return ganchos.dica ? ganchos.dica() : null; }
  function dicaAtual() {
    var doGrupo = dicaDoGrupo();   // o texto fixo do estado ou a recusa do servidor (grupo.js)
    if (doGrupo && doGrupo.texto) return doGrupo.texto;
    if (S.chegada && !S.reproducao) return textoDaChegada();
    return ESTADOS[estadoDaInteracao()].dica(contextoDaDica());
  }
  /** "Spinx anda até o ponto: chega 1:31, 2,4 s depois de agora" */
  function textoDaChegada() {
    var c = S.chegada;
    return nomePeca(c.peca) + " anda até o ponto: chega " + relogioEm(c.t) + ", " +
      (Math.round((c.t - c.desde) * 10) / 10).toFixed(1).replace(".", ",") + " s depois de agora";
  }
  /** O rótulo "chega 1:31" no ponto de chegada, até a próxima ação. */
  function desenhaChegada() {
    if (!S.chegada || S.reproducao) return;
    var c = S.chegada, px = jogoParaPixel(c.x, c.y), texto = "chega " + relogioEm(c.t);
    ctx.save();
    ctx.globalAlpha = alfaDoAndar(c.nivel);
    ctx.strokeStyle = MapCore.token("tinta-mapa"); ctx.lineWidth = 2; ctx.setLineDash([4, 4]);
    ctx.beginPath(); ctx.arc(px[0], px[1], RAIO_PECA, 0, 2 * Math.PI); ctx.stroke();
    ctx.setLineDash([]);
    ctx.restore();
    MapCore.rotulo(texto, px[0], px[1] - RAIO_PECA - 4, { dy: 2, prioridade: 8 });
    S.ultimaChegada = texto;
  }

  /** Com grupo a linha de dica tem dois espaços (§19.6): o texto e, à direita, a etiqueta temporária de quem mexeu. */
  function pintaDicaDoGrupo(d) {
    var g = dicaDoGrupo() || {};
    d.className = "pr-dica-estado com-grupo" + (g.classe ? " " + g.classe : "");
    d.textContent = "";
    var t = el("span", { class: "dica-texto" });
    if (g.html) t.innerHTML = g.html; else t.textContent = dicaAtual();      // o html vem do grupo.js, com esc() em todo nome
    d.appendChild(t);
    if (g.etiqueta) { var e = el("span", { class: "dica-espaco" }); e.innerHTML = g.etiqueta; d.appendChild(e); }
  }

  /** No computador a dica tem UMA linha e o que não cabe termina em reticências (v2-5b, decisão 2 do Pedro): o texto
      inteiro fica no `title` (aparece ao passar o mouse), só quando foi cortado; o leitor de tela lê tudo pelo
      role=status, e um `title` igual ao texto o faria ler duas vezes. */
  function tituloDaDica() {
    var d = $("pr-dica-estado");
    if (!d) return;
    var t = d.querySelector(".dica-texto") || d;
    var cortada = t.scrollWidth > t.clientWidth || t.scrollHeight > t.clientHeight;
    if (cortada) d.title = t.textContent; else d.removeAttribute("title");
  }

  function atualizaDica() {
    var d = $("pr-dica-estado");
    if (d && !ganchos.dica) d.textContent = dicaAtual();
    else if (d) pintaDicaDoGrupo(d);
    tituloDaDica();
    if (!cv) return;
    var e = estadoDaInteracao();
    cv.style.cursor = (e === "colocando_peca" || e === "granada_origem" || e === "granada_destino" ||
                       e === "buscando" || e === "desenhando") ? "crosshair" : (S.sobrePeca ? "pointer" : "default");
  }

  /* --- ações pendentes --------------------------------------------------------- */
  /** Escolher um tipo de granada: com peça selecionada, a origem é ela. */
  function escolheArma(arma) {
    confirmaGiro();
    abaDoPainel("granadas");     // escolher a granada (pelo atalho 1-4 também) mostra onde ela está
    S.arma = arma;
    if (S.acao && S.acao.tipo === "busca") { S.acao.arma = arma; if (S.busca) busca(S.busca.ponto); atualizaTudo(); return; }
    if (ROTULO_FERRAMENTA[S.ferramenta] || S.ferramenta === "borracha") S.ferramenta = "mover";
    var q = quadro();
    if (S.sel && S.sel.tipo === "peca" && q.pecas[S.sel.id]) {
      var p = q.pecas[S.sel.id];
      S.acao = { tipo: "granada", arma: arma, de: S.sel.id, origem: [p.x, p.y], nivel: p.nivel };
    } else {
      S.acao = { tipo: "granada", arma: arma, de: null, origem: null };
    }
    S.busca = null;
    atualizaTudo();
  }

  /** Cria a granada à mão e, se o mapa tem biblioteca, abre as sugestões de
      arremesso real para o destino -- a primeira opção é manter a desenhada. */
  function criaGranadaDaAcao(destino) {
    var a = S.acao;
    var dados = { granada: novoId(), arma: a.arma, passo: passoAtual(),
                  nivel: a.nivel === undefined ? S.andar : a.nivel,
                  origem: [a.origem[0], a.origem[1]], destino: [destino[0], destino[1]], arremesso: null };
    // formato 3: o horário é o do cabeçote e o arremessador, o jogador de onde
    // ela sai (no marco os dois já saem da conversão dos passos)
    if (M3 && (!noMarco() || a.de)) { dados.t = S.t; if (a.de) dados.jogador = a.de; }
    var op = emite("cria_granada", dados);
    if (a.legado) {
      // "Desenhar à mão" do painel: a ferramenta fica, como sempre foi
      S.acao = { tipo: "granada", arma: a.arma, de: null, origem: null, legado: true };
      S.sel = { tipo: "granada", id: op.granada };
    } else if (a.de && S.estado.pecas[a.de]) {
      S.acao = null; S.sel = { tipo: "peca", id: a.de };
    } else {
      S.acao = null; S.sel = { tipo: "granada", id: op.granada };
    }
    if (cfg.biblioteca && !a.legado) {
      S.sugestao = { granada: op.granada, de: a.de ? nomePeca(a.de) : "o ponto escolhido", peca: a.de || null };
      busca(destino, a.arma);
    } else if (!temBiblioteca() && !a.legado) {
      S.aviso = "Sem arremessos reais neste mapa: não há partidas dele no corpus, então a granada fica desenhada à mão.";
    } else if (!a.legado) {
      S.aviso = "Os arremessos reais ainda estão carregando: a granada fica desenhada à mão.";
    }
    atualizaTudo();
  }

  /** Trocar a granada desenhada pelo arremesso real escolhido na lista. */
  function trocaPorArremesso(r) {
    var s = S.sugestao, antes = [];
    if (s && S.estado.granadas[s.granada]) antes.push(["remove_granada", { granada: s.granada }]);
    var pid = s ? s.peca : null;
    S.sugestao = null;
    usaArremesso(r, pid, antes);
  }

  /** Quando o arremessador consegue chegar à posição do arremesso: do último
      ponto-chave dele antes do cabeçote, na velocidade da função dele. */
  function chegadaPossivel(pid, x, y) {
    var p = S.e3 && S.e3.pecas[pid];
    if (!p) return null;
    var antes = p.pontos.filter(function (pt) { return !pt.fora && pt.t < S.t - EPS_T; });
    var base = antes.length ? antes[antes.length - 1] : null;
    if (!base) { var q = quadro().pecas[pid]; if (!q) return null; base = { t: S.t, x: q.x, y: q.y }; }
    return base.t + Math.hypot(x - base.x, y - base.y) / velocidade(funcaoDe(pid), "correndo");
  }

  /** As operações que põem a peça em (x, y) com o yaw NO HORÁRIO t: no marco,
      move_peca e gira_peca do passo; fora dele, o ponto daquele horário ou um novo. */
  function opsDoPonto(pid, t, x, y, nivel, yaw) {
    // num round do replay, o real do jogador depois do cabeçote sai na mesma
    // ação, com a âncora no estado real do cabeçote (antes dele nada muda)
    var corte = baseReal() === null ? [] : cortaReal(pid, Math.min(S.t, t)).concat(t > S.t + EPS_T ? ancoraReal(pid, S.t) : []);
    var m = S.e3.marcos[marcoQueContem(t)];
    if (m && Math.abs(m.t - t) < EPS_T) {
      return corte.concat([["move_peca", { peca: pid, passo: m.passo, x: x, y: y, nivel: nivel }],
                           ["gira_peca", { peca: pid, passo: m.passo, yaw: yaw }]]);
    }
    var p = S.e3.pecas[pid], pt = p && p.pontos.filter(function (q) { return !q.fora && Math.abs(q.t - t) < EPS_T; }).pop();
    if (pt) return corte.concat([["move_ponto", { peca: pid, ponto: pt.id, t: t, x: x, y: y, nivel: nivel, yaw: yaw }]]);
    return corte.concat([["cria_caminho", { peca: pid, pontos: [{ t: t, x: x, y: y, nivel: nivel, yaw: yaw }] }]]);
  }

  /** Um nível para trás: ação pendente -> ferramenta de desenho -> seleção. */
  function volta() {
    if (S.editor) { fechaEditorTexto(false); return; }
    if (S.caminho && !S.acao) { S.caminho = null; atualizaTudo(); return; }
    if (S.ajuda) { alternaAjuda(false); return; }
    if (S.busca || S.sugestao) { S.busca = null; S.sugestao = null; atualizaTudo(); return; }
    if (S.acao) { S.acao = null; atualizaTudo(); return; }
    if (ROTULO_FERRAMENTA[S.ferramenta] || S.ferramenta === "borracha") { S.ferramenta = "mover"; atualizaTudo(); return; }
    S.sel = null; atualizaTudo();
  }

  /* --- ponteiro ------------------------------------------------------------------ */
  function pointerDown(e) {
    if (!S.doc) return;
    if (S.chegada) { S.chegada = null; atualizaDica(); }
    if (S.reproducao) { if (S.espaco || e.button === 1) comecaPan(e); return; }
    if (S.espaco || e.button === 1) { comecaPan(e); e.preventDefault(); return; }
    var px = eventoParaPixel(e), g = eventoParaJogo(e);
    if (e.button === 2) {
      // botão direito: a peça selecionada passa a olhar para o ponto
      e.preventDefault();
      var q = quadro();
      if (S.sel && S.sel.tipo === "peca" && q.pecas[S.sel.id]) {
        var p = q.pecas[S.sel.id];
        confirmaGiro();
        gravaYaw(S.sel.id, yawInteiro(Math.atan2(g[1] - p.y, g[0] - p.x) * (180 / Math.PI)));
      }
      return;
    }
    if (e.button !== 0) return;
    if (S.editor) fechaEditorTexto(true);
    var estado = estadoDaInteracao();
    if (estado === "desenhando") { comecaTraco(e, px, g); return; }
    cv.setPointerCapture(e.pointerId);
    var alvo = acha(px);
    S.toque = { x: e.clientX, y: e.clientY, px: px, g: g, alvo: alvo, estado: estado, arrastou: false };
    if (estado === "tracando_caminho" && !(alvo && alvo.tipo === "peca")) {
      S.arrasto = { tipo: "mao", mexeu: false };
      S.caminho.mao = [px];
      return;
    }
    // arrastar peça, alça ou ponta de granada continua como sempre (quando não
    // há ação pendente): o arrasto é armado aqui e só vira operação se andar
    if (alvo && (estado === "livre" || estado === "peca_selecionada" || estado === "granada_selecionada" ||
                 (estado === "tracando_caminho" && alvo.tipo !== "granada"))) {
      S.sel = { tipo: alvo.tipo === "giro" ? "peca" : alvo.tipo, id: alvo.id };
      var q2 = quadro();
      if (alvo.tipo === "giro") S.arrasto = { tipo: "giro", id: alvo.id, yaw: null, mexeu: false };
      else if (alvo.tipo === "peca") S.arrasto = { tipo: "peca", id: alvo.id, jogo: [q2.pecas[alvo.id].x, q2.pecas[alvo.id].y], mexeu: false };
      else {
        var gr = S.estado.granadas[alvo.id];
        S.arrasto = { tipo: "granada", id: alvo.id, ponta: alvo.ponta, origem: gr.origem.slice(), destino: gr.destino.slice(), mexeu: false };
      }
      atualizaPainel(); atualizaDica();
    }
    desenha();
  }

  function pointerMove(e) {
    if (S.pan) {
      var k = cfg.radar.width / cv.getBoundingClientRect().width;
      S.view.panX = S.pan.panX + (e.clientX - S.pan.x) * k;
      S.view.panY = S.pan.panY + (e.clientY - S.pan.y) * k;
      MapCore.limitaPan(S.view, cfg.radar);
      desenha();
      return;
    }
    if (S.tracando) { continuaTraco(e); return; }
    if (S.toque && !S.toque.arrastou &&
        Math.hypot(e.clientX - S.toque.x, e.clientY - S.toque.y) >= LIMIAR_ARRASTO_PX) S.toque.arrastou = true;
    if (!S.arrasto) {
      if (!S.toque && S.doc && !S.reproducao) {
        var sobre = !!acha(eventoParaPixel(e));
        if (sobre !== !!S.sobrePeca) { S.sobrePeca = sobre; atualizaDica(); }
      }
      return;
    }
    if (!S.toque || !S.toque.arrastou) return;
    var g = eventoParaJogo(e);
    if (S.arrasto.tipo === "mao") { S.arrasto.mexeu = true; S.caminho.mao.push(eventoParaPixel(e)); desenha(); return; }
    S.arrasto.mexeu = true;
    if (S.arrasto.tipo === "peca") S.arrasto.jogo = g;
    else if (S.arrasto.tipo === "giro") {
      var p = quadro().pecas[S.arrasto.id];
      S.arrasto.yaw = yawInteiro(Math.atan2(g[1] - p.y, g[0] - p.x) * (180 / Math.PI));
    } else S.arrasto[S.arrasto.ponta] = [g[0], g[1]];
    desenha();
  }

  function yawInteiro(v) { return ((Math.round(v) % 360) + 360) % 360; }

  function pointerUp() {
    if (S.pan) { S.pan = null; return; }
    if (S.tracando) { terminaTraco(); return; }
    var a = S.arrasto, t = S.toque;
    S.arrasto = null; S.toque = null;
    if (a && a.tipo === "mao") { if (a.mexeu) terminaMao(); else if (t) clique(t); return; }
    if (a && a.mexeu) {
      // arrastar a peça MOVE livremente: o ponto-chave do horário do cabeçote
      if (a.tipo === "peca") { gravaPosicao(a.id, a.jogo[0], a.jogo[1], S.andar); if (S.caminho) iniciaCaminho(S.caminho.peca); }
      else if (a.tipo === "giro") { if (a.yaw !== null) gravaYaw(a.id, a.yaw); }
      else emite("move_granada", { granada: a.id, origem: a.origem, destino: a.destino, nivel: S.estado.granadas[a.id].nivel });
      return;
    }
    if (t && !t.arrastou) clique(t);
    else desenha();
  }

  /** O clique (ponteiro que não andou), resolvido pelo estado em que começou. */
  function clique(t) {
    var g = t.g, alvo = t.alvo, q = quadro();
    switch (t.estado) {
      case "colocando_peca": {
        var ac = S.acao;
        S.acao = null;
        colocaPeca(ac.lado, ac.rotulo, g);
        return;
      }
      case "buscando":
        if (cfg.biblioteca) busca(g, S.acao.arma);
        return;
      case "granada_origem":
        if (alvo && alvo.tipo === "peca" && q.pecas[alvo.id]) {
          var p = q.pecas[alvo.id];
          S.acao.de = alvo.id; S.acao.origem = [p.x, p.y]; S.acao.nivel = p.nivel;
        } else {
          S.acao.origem = [g[0], g[1]];
        }
        atualizaTudo();
        return;
      case "granada_destino":
        criaGranadaDaAcao(g);
        return;
      case "peca_selecionada":
        if (!alvo) {
          // no vazio: começa um caminho até lá (teleportar é arrastar)
          iniciaCaminho(S.sel.id);
          adicionaPonto(g);
          atualizaTudo();
          return;
        }
        break;
      case "tracando_caminho":
        if (S.caminho) S.caminho.mao = null;
        if (!alvo || alvo.tipo !== "peca" || alvo.id === S.caminho.peca) { adicionaPonto(g); atualizaTudo(); return; }
        break;
      case "granada_selecionada":
        if (!alvo) {
          var gr = S.estado.granadas[S.sel.id];
          emite("move_granada", { granada: S.sel.id, origem: gr.origem.slice(), destino: [g[0], g[1]], nivel: gr.nivel });
          return;
        }
        break;
      default:
        break;
    }
    // livre, ou clique num item: seleciona o que está sob o ponteiro
    S.sel = alvo ? { tipo: alvo.tipo === "giro" ? "peca" : alvo.tipo, id: alvo.id } : (t.estado === "livre" ? null : S.sel);
    // clicar numa peça, sem arrastar, entra em "traçando caminho" (8.2)
    if (alvo && alvo.tipo === "peca" && M3) iniciaCaminho(alvo.id);
    else if (!(S.sel && S.sel.tipo === "peca")) S.caminho = null;
    if (!alvo && t.estado === "livre") {
      var tr = tracoSob(t.px);
      if (tr) S.sel = { tipo: "traco", id: tr };
    }
    atualizaTudo();
  }

  /** O traço mais recente sob o ponto, no andar ativo. */
  function tracoSob(px) {
    var q = quadro();
    var alvos = ordemDeCriacao(S.estado).filter(function (x) {
      return x.tipo === "traco" && q.tracos[x.id] && q.tracos[x.id].nivel === S.andar &&
             MapCore.tracoEncosta(q.tracos[x.id], px, cfg.radar, RAIO_BORRACHA);
    });
    return alvos.length ? alvos[alvos.length - 1].id : null;
  }

  /** Põe a ficha do banco no mapa: a peça existente volta (move_peca) ou uma
      nova nasce (cria_peca) -- o mesmo que soltar o arrasto do banco. */
  function colocaPeca(lado, rotulo, g) {
    var existente = Object.keys(S.estado.pecas).filter(function (id) {
      return S.estado.pecas[id].lado === lado && S.estado.pecas[id].rotulo === rotulo;
    })[0];
    if (existente) {
      emite("move_peca", { peca: existente, passo: passoAtual(), x: g[0], y: g[1], nivel: S.andar });
      S.sel = { tipo: "peca", id: existente };
    } else {
      var op = emite("cria_peca", { peca: novoId(), lado: lado, rotulo: rotulo, passo: passoAtual(),
                                    x: g[0], y: g[1], nivel: S.andar });
      S.sel = { tipo: "peca", id: op.peca };
    }
    atualizaTudo();
  }

  /** Clique numa ficha do banco: seleciona a peça se ela está no mapa neste
      passo; senão arma a colocação. */
  function cliqueNaFicha(lado, rotulo) {
    confirmaGiro();
    var q = quadro();
    var noMapa = Object.keys(q.pecas).filter(function (id) {
      return q.pecas[id].lado === lado && q.pecas[id].rotulo === rotulo;
    })[0];
    if (ROTULO_FERRAMENTA[S.ferramenta] || S.ferramenta === "borracha") S.ferramenta = "mover";
    S.busca = null; S.sugestao = null;
    if (noMapa) { S.acao = null; S.sel = { tipo: "peca", id: noMapa }; }
    else S.acao = { tipo: "colocar", lado: lado, rotulo: rotulo };
    atualizaTudo();
  }

  /** Gira a peça selecionada no passo atual (Q/E e os botões do painel). */
  function giraSelecionada(delta) {
    var q = quadro();
    if (!S.sel || S.sel.tipo !== "peca" || !q.pecas[S.sel.id]) return;
    var base = yawDaPeca(S.sel.id, q.pecas[S.sel.id]);
    confirmaGiro();
    gravaYaw(S.sel.id, yawInteiro(base + delta));
  }

  /** Muda de passo mantendo a seleção quando a peça existe no passo novo. */
  function mudaPasso(i) {
    confirmaGiro();
    S.passo = Math.max(0, Math.min(i, S.estado.passos.length - 1));
    if (S.e3 && S.e3.marcos[S.passo]) S.t = S.e3.marcos[S.passo].t;
    if (S.caminho) iniciaCaminho(S.caminho.peca);
    if (S.sel) {
      var q = quadro();
      var grupo = { peca: "pecas", granada: "granadas", traco: "tracos" }[S.sel.tipo];
      if (!q[grupo][S.sel.id]) S.sel = null;
    }
    if (S.acao && S.acao.tipo === "granada" && S.acao.de) {
      var pq = quadro().pecas[S.acao.de];
      if (pq) { S.acao.origem = [pq.x, pq.y]; S.acao.nivel = pq.nivel; } else S.acao = null;
    }
    atualizaTudo();
  }

  /* --- texto no próprio mapa (sem window.prompt) --------------------------------- */
  function abreEditorTexto(g) {
    fechaEditorTexto(false);
    var px = jogoParaPixel(g[0], g[1]);
    var r = cv.getBoundingClientRect(), k = r.width / cfg.radar.width;
    var x = (px[0] * S.view.zoom + S.view.panX) * k, y = (px[1] * S.view.zoom + S.view.panY) * k;
    var campo = el("input", { type: "text", id: "pr-editor-texto", class: "pr-editor-texto",
                              "aria-label": "Texto da anotação (Enter confirma, Esc cancela)",
                              placeholder: "texto · Enter confirma · Esc cancela" });
    campo.style.left = (cv.offsetLeft + x) + "px";
    campo.style.top = (cv.offsetTop + y) + "px";
    campo.addEventListener("keydown", function (e) {
      if (e.key === "Enter") { e.preventDefault(); fechaEditorTexto(true); }
      else if (e.key === "Escape") { e.preventDefault(); e.stopPropagation(); fechaEditorTexto(false); }
    });
    $("pr-tela").appendChild(campo);
    S.editor = { g: g, campo: campo };
    setTimeout(function () { campo.focus(); }, 0);
  }

  function fechaEditorTexto(confirma) {
    var ed = S.editor;
    if (!ed) return;
    S.editor = null;
    var txt = ed.campo.value.trim();
    if (ed.campo.parentNode) ed.campo.parentNode.removeChild(ed.campo);
    if (confirma && txt) {
      var op = emite("cria_traco", { traco: novoId(), passo: passoAtual(), ferramenta: "texto", texto: txt,
                                     cor: S.cor, espessura: S.espessura, pontos: [ed.g], nivel: S.andar });
      S.sel = { tipo: "traco", id: op.traco };
    }
    atualizaTudo();
  }

  /* --- atalhos: UM mapa, sem tecla repetida (há teste) ----------------------------- */
  var ATALHOS = [
    { tecla: "v", rotulo: "V", acao: "Selecionar", fn: function () { escolheFerramenta("mover"); } },
    { tecla: "1", rotulo: "1", acao: "Smoke", fn: function () { armaOuDesenho("smoke"); } },
    { tecla: "2", rotulo: "2", acao: "Flash", fn: function () { armaOuDesenho("flash"); } },
    { tecla: "3", rotulo: "3", acao: "HE", fn: function () { armaOuDesenho("he"); } },
    { tecla: "4", rotulo: "4", acao: "Molotov", fn: function () { armaOuDesenho("molotov"); } },
    { tecla: "c", rotulo: "C", acao: "Caneta", fn: function () { escolheFerramenta("caneta"); } },
    { tecla: "a", rotulo: "A", acao: "Seta", fn: function () { escolheFerramenta("seta"); } },
    { tecla: "l", rotulo: "L", acao: "Linha", fn: function () { escolheFerramenta("linha"); } },
    { tecla: "t", rotulo: "T", acao: "Texto", fn: function () { escolheFerramenta("texto"); } },
    { tecla: "x", rotulo: "X", acao: "Borracha", fn: function () { escolheFerramenta("borracha"); } },
    { tecla: "q", rotulo: "Q", acao: "Girar a peça 15° (Shift: 1°) no sentido anti-horário",
      fn: function (e) { giraSelecionada(e.shiftKey ? PASSO_GIRO_FINO : PASSO_GIRO); } },
    { tecla: "e", rotulo: "E", acao: "Girar a peça 15° (Shift: 1°) no sentido horário",
      fn: function (e) { giraSelecionada(-(e.shiftKey ? PASSO_GIRO_FINO : PASSO_GIRO)); } },
    { tecla: ",", rotulo: ",", acao: "Passo anterior", fn: function () { mudaPasso(S.passo - 1); } },
    { tecla: ".", rotulo: ".", acao: "Próximo passo", fn: function () { mudaPasso(S.passo + 1); } },
    { tecla: "n", rotulo: "N", acao: "Novo passo", fn: function () { novoPasso(); } },
    { tecla: "delete", rotulo: "Delete", acao: "Remover o selecionado", fn: function () { removeSelecionado(); } },
    { tecla: "escape", rotulo: "Esc", acao: "Um nível para trás", fn: function () { volta(); } },
    { tecla: "f", rotulo: "F", acao: "Tela cheia", fn: function () { MapCore.alternaTelaCheia($("pr-palco")); } },
    { tecla: "0", rotulo: "0", acao: "Zoom original", fn: function () { resetaZoom(); } },
    { tecla: "?", rotulo: "?", acao: "Ajuda: esta lista", fn: function () { alternaAjuda(); } },
    { tecla: "ctrl+z", rotulo: "Ctrl+Z", acao: "Desfazer", fn: function () { desfaz(); } },
    { tecla: "ctrl+y", rotulo: "Ctrl+Y", acao: "Refazer (também Ctrl+Shift+Z)", fn: function () { refaz(); } },
    { tecla: "espaço", rotulo: "Espaço + arrastar", acao: "Mover o mapa (com zoom)", fn: null },
    // fase 11 -- no fim da tabela: os botões de giro acima pegam o rótulo por posição (ATALHOS[10] e [11])
    { tecla: "1-4 no pincel", rotulo: "1 a 4", acao: "Com o pincel Granada (desenho): escolhem o tipo da granada desenhada", fn: null },
    { tecla: "g", rotulo: "G", acao: "Granada (desenho)", fn: function () { escolheFerramenta("granada_desenho"); } },
    { tecla: "setas no pincel", rotulo: "Setas + Enter", acao: "Com o pincel Granada (desenho): movem o cursor no mapa e carimbam", fn: null }
  ];
  var ATALHO_DE = {};
  ATALHOS.forEach(function (a) { ATALHO_DE[a.acao] = a.rotulo; });
  function comAtalho(texto, acao) { var r = ATALHO_DE[acao]; return r ? texto + " (" + r + ")" : texto; }

  function teclaDoEvento(e) {
    var k = e.key === "Del" ? "delete" : e.key.toLowerCase();
    if (e.ctrlKey || e.metaKey) {
      if (k === "z" && e.shiftKey) return "ctrl+y";
      return "ctrl+" + k;
    }
    if (k === "backspace") return "delete";
    return k;
  }

  function alternaAjuda(abrir) {
    var ja = $("pr-ajuda");
    var abre = abrir === undefined ? !ja : abrir;
    if (ja) ja.parentNode.removeChild(ja);
    S.ajuda = false;
    if (!abre) return;
    var lista = el("dl", { class: "pr-atalhos" });
    ATALHOS.forEach(function (a) {
      lista.appendChild(el("dt", { texto: a.rotulo }));
      lista.appendChild(el("dd", { texto: a.acao }));
    });
    var painel = el("div", { id: "pr-ajuda", class: "pr-ajuda", role: "dialog", "aria-label": "Atalhos da prancheta" },
      [el("h3", { texto: "Atalhos" }), lista,
       el("button", { class: "pr-b", texto: "Fechar (Esc)", onclick: function () { alternaAjuda(false); } })]);
    $("pr-palco").appendChild(painel);
    S.ajuda = true;
  }

  function novoPasso() {
    emite("cria_passo", { passo: novoId(), titulo: "" });
    mudaPasso(S.estado.passos.length - 1);
  }

  /* --- roda: gira a peça selecionada sob o ponteiro, ou dá zoom ------------ */
  function roda(e) {
    e.preventDefault();
    if (S.reproducao) {
      var pz = eventoParaPixel(e);
      aplicaZoom(S.view.zoom * (e.deltaY < 0 ? MapCore.ZOOM_PASSO : 1 / MapCore.ZOOM_PASSO),
                 pz[0] * S.view.zoom + S.view.panX, pz[1] * S.view.zoom + S.view.panY);
      return;
    }
    var px = eventoParaPixel(e);
    var q = quadro();
    if (S.sel && S.sel.tipo === "peca" && q.pecas[S.sel.id]) {
      var p = q.pecas[S.sel.id], c = jogoParaPixel(p.x, p.y);
      if (Math.hypot(c[0] - px[0], c[1] - px[1]) <= RAIO_PECA + 3) {
        var base = S.giro && S.giro.peca === S.sel.id ? S.giro.yaw : p.yaw;
        var passo = e.shiftKey ? PASSO_GIRO_FINO : PASSO_GIRO;
        // roda para cima gira no sentido anti-horário da tela = yaw crescente
        var novo = yawInteiro(base + (e.deltaY < 0 ? passo : -passo));
        if (!S.giro) S.giro = { peca: S.sel.id, yaw: novo, timer: null };
        S.giro.yaw = novo;
        clearTimeout(S.giro.timer);
        S.giro.timer = setTimeout(confirmaGiro, MS_AGRUPA_GIRO);
        desenha(); atualizaPainel();
        return;
      }
    }
    var z = px[0] * S.view.zoom + S.view.panX, w = px[1] * S.view.zoom + S.view.panY;
    aplicaZoom(S.view.zoom * (e.deltaY < 0 ? MapCore.ZOOM_PASSO : 1 / MapCore.ZOOM_PASSO), z, w);
  }

  function confirmaGiro() {
    var g = S.giro;
    if (!g) return;
    clearTimeout(g.timer);
    S.giro = null;
    if (S.estado.pecas[g.peca]) gravaYaw(g.peca, g.yaw);
  }

  /* --- desenho livre --------------------------------------------------------- */
  function comecaTraco(e, px, g) {
    cv.setPointerCapture(e.pointerId);
    if (S.ferramenta === "granada_desenho") { carimbaGranada(px, g); return; }
    if (S.ferramenta === "borracha") { apagaTraco(px); return; }
    if (S.ferramenta === "texto") { abreEditorTexto(g); return; }
    S.tracando = { ferramenta: S.ferramenta, pontos: S.ferramenta === "caneta" ? [g] : [g, g],
                   cor: S.cor, espessura: S.espessura };
    desenha();
  }

  function continuaTraco(e) {
    var eventos = (S.tracando.ferramenta === "caneta" && e.getCoalescedEvents) ? e.getCoalescedEvents() : [e];
    if (!eventos.length) eventos = [e];
    eventos.forEach(function (ev) {
      var g = eventoParaJogo(ev), pts = S.tracando.pontos;
      if (S.tracando.ferramenta !== "caneta") { pts[1] = g; return; }
      var ult = jogoParaPixel(pts[pts.length - 1][0], pts[pts.length - 1][1]), novo = jogoParaPixel(g[0], g[1]);
      if (Math.hypot(novo[0] - ult[0], novo[1] - ult[1]) * S.view.zoom >= PASSO_MIN_CANETA) pts.push(g);
    });
    desenha();
  }

  function terminaTraco() {
    var t = S.tracando; S.tracando = null;
    if (MapCore.tracoCurtoDemais(t, cfg.radar)) { desenha(); return; }
    var op = emite("cria_traco", { traco: novoId(), passo: passoAtual(), ferramenta: t.ferramenta,
                                   cor: t.cor, espessura: t.espessura, pontos: t.pontos, nivel: S.andar });
    S.sel = { tipo: "traco", id: op.traco }; atualizaTudo();
  }

  /** A granada desenhada sob o ponto (px do radar), a de cima primeiro, ou null. */
  function granadaDesenhadaSob(px) {
    var q = quadro();
    var alvos = ordemDeCriacao(S.estado).filter(function (x) {
      return x.tipo === "traco" && q.tracos[x.id] && q.tracos[x.id].ferramenta === "granada" &&
             q.tracos[x.id].nivel === S.andar && MapCore.tracoEncosta(q.tracos[x.id], px, cfg.radar, RAIO_BORRACHA);
    });
    return alvos.length ? alvos[alvos.length - 1].id : null;
  }

  /** O pincel "Granada (desenho)": carimba a granada no ponto, ou seleciona a desenhada que já está ali. */
  function carimbaGranada(px, g) {
    var ja = granadaDesenhadaSob(px);
    if (ja) { S.sel = { tipo: "traco", id: ja }; atualizaTudo(); return; }
    var op = emite("desenha_granada", { traco: novoId(), passo: passoAtual(), arma: S.armaDesenho,
                                        x: g[0], y: g[1], nivel: S.andar });
    S.sel = { tipo: "traco", id: op.traco };
    atualizaTudo();
  }

  /** "Converter em granada com horário": a granada desenhada vira a granada de verdade da tática -- sai do
      último jogador selecionado, no horário do cabeçote, e cai no ponto do desenho. UMA ação no desfazer. */
  function converteDesenho(tid) {
    var t = S.estado.tracos[tid], pid = S.ultimaPeca;
    var p = pid && S.e3 ? quadroNoTempo(S.e3, S.t, CENTRO).pecas[pid] : null;
    if (!t || !p) return;
    var ids = emiteLote([
      ["cria_granada", { granada: novoId(), arma: t.arma, passo: passoAtual(), nivel: p.nivel || 0,
                         origem: [p.x, p.y], destino: t.pontos[0].slice(), arremesso: null, t: S.t, jogador: pid }],
      ["remove_traco", { traco: tid }]]);
    var criada = S.doc.operacoes.filter(function (o) { return o.id === ids[0]; })[0];
    S.sel = criada ? { tipo: "granada", id: criada.granada } : null;
    atualizaTudo();
  }

  /** Liga ou desliga a área da granada desenhada (smoke e molotov). */
  function alternaAreaDesenho(tid) {
    var t = S.estado.tracos[tid];
    if (!t || (t.arma !== "smoke" && t.arma !== "molotov")) return;
    emite("define_area_desenho", { traco: tid, area: !t.area });
    atualizaTudo();
  }

  /** 1 a 4: com o pincel "Granada (desenho)" ligado, escolhem o tipo do carimbo; fora dele, armam a granada com
      horário, como sempre. */
  function armaOuDesenho(arma) {
    if (S.ferramenta === "granada_desenho") { S.armaDesenho = arma; atualizaTudo(); return; }
    escolheArma(arma);
  }

  function apagaTraco(px) {
    var q = quadro();
    var alvos = ordemDeCriacao(S.estado).filter(function (x) {
      return x.tipo === "traco" && q.tracos[x.id] && q.tracos[x.id].nivel === S.andar &&
             MapCore.tracoEncosta(q.tracos[x.id], px, cfg.radar, RAIO_BORRACHA);
    });
    if (alvos.length) emite("remove_traco", { traco: alvos[alvos.length - 1].id });
  }

  /* --- banco de peças -------------------------------------------------------- */
  /** Arrastar do banco para o mapa: peça nova, ou -- se esse jogador já existe
      na tática e só não está no mapa neste passo -- a mesma peça de volta. */
  function soltaDoBanco(e, lado, rotulo) {
    if (S.reproducao) return;
    var c = cv.getBoundingClientRect();
    if (e.clientX < c.left || e.clientX > c.right || e.clientY < c.top || e.clientY > c.bottom) return;
    var g = eventoParaJogo(e);
    var existente = Object.keys(S.estado.pecas).filter(function (id) {
      return S.estado.pecas[id].lado === lado && S.estado.pecas[id].rotulo === rotulo;
    })[0];
    if (existente) {
      emite("move_peca", { peca: existente, passo: passoAtual(), x: g[0], y: g[1], nivel: S.andar });
      S.sel = { tipo: "peca", id: existente };
    } else {
      var op = emite("cria_peca", { peca: novoId(), lado: lado, rotulo: rotulo, passo: passoAtual(),
                                    x: g[0], y: g[1], nivel: S.andar });
      S.sel = { tipo: "peca", id: op.peca };
    }
    atualizaTudo();
  }

  function removeSelecionado() {
    if (!S.sel) return;
    if (S.sel.tipo === "peca") emite("remove_peca", { peca: S.sel.id });
    else if (S.sel.tipo === "granada") emite("remove_granada", { granada: S.sel.id });
    else emite("remove_traco", { traco: S.sel.id });
    S.sel = null; atualizaTudo();
  }

