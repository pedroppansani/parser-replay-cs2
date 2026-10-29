  /* --- o round real (fase 9) ------------------------------------------------
     A tática aberta de um round do replay guarda em `origem.base_real` o número
     de ordem da última operação do round real. Tudo até ali é o que aconteceu;
     o que vem depois é do usuário. Editar um jogador em t troca o caminho REAL
     dele DALI EM DIANTE pelo do usuário: os pontos reais depois de t saem
     (remove_ponto) na mesma ação da edição. Antes de t, e nos outros jogadores,
     nada muda. */
  function baseReal() { return S.doc && S.doc.origem && ehInteiro(S.doc.origem.base_real) ? S.doc.origem.base_real : null; }
  function idsDaBase() {
    var b = baseReal(), ids = {};
    if (b === null) return ids;
    S.doc.operacoes.forEach(function (op) { if (op.seq <= b) ids[op.id] = true; });
    return ids;
  }
  /** As remoções dos pontos REAIS da peça depois de t (vazio fora de um round). */
  function cortaReal(pid, t) {
    if (baseReal() === null || !S.e3 || !S.e3.pecas[pid]) return [];
    var base = idsDaBase();
    return S.e3.pecas[pid].pontos.filter(function (pt) {
      return pt.t > t + EPS_T && (pt.id.indexOf("passo:") === 0 || base[pt.id.split(":")[0]]);
    }).map(function (pt) { return ["remove_ponto", { peca: pid, ponto: pt.id }]; });
  }
  /** A âncora do corte: um ponto em t com o estado REAL naquele horário
      (posição, andar e direção), quando não há ponto ali. Sem ela, o trecho
      entre o último ponto real antes de t e o primeiro ponto do usuário
      mudaria a posição e a direção ANTES de t. */
  function ancoraReal(pid, t) {
    if (baseReal() === null || !S.e3 || !S.e3.pecas[pid]) return [];
    if (S.e3.pecas[pid].pontos.some(function (pt) { return !pt.fora && Math.abs(pt.t - t) < EPS_T; })) return [];
    var q = quadroNoTempo(S.e3, t, CENTRO).pecas[pid];
    if (!q) return [];
    return [["cria_caminho", { peca: pid, pontos: [{ t: t, x: q.x, y: q.y, nivel: q.nivel, yaw: q.yaw }] }]];
  }
  function ehPontoReal(pid, pt) {
    var base = idsDaBase();
    return pt.id.indexOf("passo:") === 0 ? baseReal() !== null : !!base[pt.id.split(":")[0]];
  }
  /** Emite as operações de uma edição na peça, precedidas do corte do real e
      da âncora: tudo numa ação só (um desfazer). */
  function emiteNaPeca(pid, t, lista) {
    var tudo = cortaReal(pid, t).concat(ancoraReal(pid, t)).concat(lista);
    if (tudo.length === 1) emite(tudo[0][0], tudo[0][1]);
    else emiteLote(tudo);
  }
  /** As operações do round real (até base_real), para o fantasma. */
  var cacheReal = { chave: null, e3: null };
  function e3Real() {
    var b = baseReal();
    if (b === null) return null;
    var chave = S.doc.id + ":" + b;
    if (cacheReal.chave !== chave) {
      cacheReal = { chave: chave, e3: taticaNoTempo(S.doc.operacoes.filter(function (op) { return op.seq <= b; })) };
    }
    return cacheReal.e3;
  }
  /** "Voltar ao real": anula toda operação do usuário ainda ativa. É UMA ação
      do mecanismo de desfazer (`anula`), e refazer devolve tudo. */
  function voltaAoReal() {
    var b = baseReal();
    if (b === null || S.reproducao) return;
    confirmaGiro();
    var fora = anuladas(S.doc.operacoes);
    var alvos = S.doc.operacoes.filter(function (op) {
      return op.seq > b && DESFAZER.indexOf(op.tipo) < 0 && !fora[op.id];
    }).map(function (op) { return op.id; });
    if (!alvos.length) return;
    alvos.forEach(function (id) { emite("anula", { alvo: id }); });
    S.pilhaRefazer.push(alvos);
    S.caminho = null;
    atualizaTudo();
  }
  function alternaFantasma() {
    S.fantasma = !S.fantasma;
    desenha();
    atualizaReal();
  }
  function atualizaReal() {
    var barra = $("pr-real");
    if (!barra) return;
    barra.hidden = baseReal() === null;
    var f = $("pr-fantasma");
    f.textContent = S.fantasma ? "Esconder o que aconteceu" : "Mostrar o que aconteceu";
    f.setAttribute("aria-pressed", S.fantasma ? "true" : "false");
    $("pr-volta-real").disabled = !!S.reproducao;
  }
  /** O fantasma: o round real no mesmo horário, esmaecido (o alfa do rastro). */
  function desenhaFantasma(t) {
    S.ultimoFantasma = null;
    if (!S.fantasma || t === null) return;
    var e = e3Real();
    if (!e) return;
    var f = quadroNoTempo(e, t, CENTRO), n = 0;
    ctx.save();
    Object.keys(f.granadas).forEach(function (id) {
      var g = f.granadas[id];
      if (g.fase !== "efeito" || (g.arma !== "smoke" && g.arma !== "molotov")) return;
      var b = jogoParaPixel(g.destino[0], g.destino[1]);
      var r = (g.arma === "smoke" ? MapCore.RAIO_SMOKE_UNIDADES : MapCore.RAIO_MOLOTOV_UNIDADES) * escalaUnidade();
      ctx.globalAlpha = ALFA_RASTRO * alfaDoAndar(g.nivel);
      MapCore.desenhaArea(ctx, g.arma, b[0], b[1], r);
    });
    Object.keys(f.pecas).forEach(function (id) {
      var q = f.pecas[id], c2 = jogoParaPixel(q.x, q.y);
      ctx.globalAlpha = ALFA_FANTASMA * alfaDoAndar(q.nivel);
      // fantasma (§14): sem preenchimento, contorno tracejado na cor do lado, nome em itálico "--tinta-2" + "· real"
      MapCore.desenhaJogador(ctx, c2[0], c2[1], { cor: cssVar(q.lado === "ct" ? "--ct-mapa" : "--tr-mapa"), estado: "fantasma", hp: 100,
                                                  cego: false, nome: rotuloDaPeca(q) + " · real", yaw: q.yaw, escala: ESCALA_PECA,
                                                  rotuloAcima: RAIO_PECA + 6 });
      n++;
    });
    ctx.restore();
    S.ultimoFantasma = { pecas: Object.keys(f.pecas).sort(), n: n };
  }
  /** A marca de morte: quem saiu morto fica marcado no último lugar. */
  function desenhaMortos(mortos) {
    Object.keys(mortos || {}).forEach(function (id) {
      var m = mortos[id], c2 = jogoParaPixel(m.x, m.y);
      ctx.save();
      ctx.globalAlpha = alfaDoAndar(m.nivel);
      MapCore.desenhaJogador(ctx, c2[0], c2[1], { cor: cssVar(m.lado === "ct" ? "--ct-mapa" : "--tr-mapa"), estado: "morto", hp: 0,
                                                  cego: false, nome: "", yaw: null, escala: ESCALA_PECA });
      ctx.restore();
      S.ultimoDesenho.push({ tipo: "morto", id: id });
    });
  }

