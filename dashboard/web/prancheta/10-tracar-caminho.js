  /* --- traçar caminho (8.2) ------------------------------------------------- */
  // Tolerância da simplificação do traço à mão livre (Douglas-Peucker), em
  // pixel do RADAR: 2 px é menos que o raio da peça (15) e tira o tremor da mão
  // sem cortar curva -- convenção de interface, como os outros raios daqui.
  var TOLERANCIA_DP_PX = 2;

  // TRAÇAR CAMINHO POR CLIQUE (8.2, ligado na 8a por decisão do Pedro): clicar
  // na peça, sem arrastar, entra em "traçando caminho"; segurar e arrastar move
  // livremente. O mover por clique no vazio deixou de existir (o modo desligado
  // foi removido na fase 17, decisão 43).

  function iniciaCaminho(pid) {
    var q = quadro().pecas[pid];
    if (!q) { S.caminho = null; return; }
    S.caminho = { peca: pid, inicio: { t: S.t, x: q.x, y: q.y, nivel: q.nivel }, pontos: [], mao: null };
  }
  function funcaoDe(pid) { return S.e3 && S.e3.pecas[pid] ? S.e3.pecas[pid].funcao : null; }
  function horarioDoProximo(x, y) {
    var c = S.caminho, ult = c.pontos.length ? c.pontos[c.pontos.length - 1] : c.inicio;
    var v = velocidade(funcaoDe(c.peca), S.modoCaminho);
    return Math.round((ult.t + Math.hypot(x - ult.x, y - ult.y) / v) * 100) / 100;
  }
  function adicionaPonto(g) {
    if (!S.caminho) return;
    S.caminho.pontos.push({ t: horarioDoProximo(g[0], g[1]), x: g[0], y: g[1], nivel: S.andar, modo: S.modoCaminho });
    atualizaDica(); desenha();
  }
  function concluiCaminho() {
    var c = S.caminho;
    if (!c) return;
    if (!c.pontos.length) { S.caminho = null; atualizaTudo(); return; }
    emiteNaPeca(c.peca, c.inicio.t, [["cria_caminho", { peca: c.peca, pontos: c.pontos.map(function (pt) { return Object.assign({}, pt); }) }]]);
    // a peça segue selecionada e o cabeçote vai para o fim: dá para emendar
    S.t = c.pontos[c.pontos.length - 1].t;
    S.passo = marcoQueContem(S.t);
    iniciaCaminho(c.peca);
    atualizaTudo();
  }
  function douglasPeucker(pts, tol) {
    if (pts.length < 3) return pts.slice();
    var a = pts[0], b = pts[pts.length - 1], maior = -1, k = 0;
    for (var i = 1; i < pts.length - 1; i++) {
      var p = pts[i], dx = b[0] - a[0], dy = b[1] - a[1], L = Math.hypot(dx, dy);
      var d = L === 0 ? Math.hypot(p[0] - a[0], p[1] - a[1]) : Math.abs(dy * p[0] - dx * p[1] + b[0] * a[1] - b[1] * a[0]) / L;
      if (d > maior) { maior = d; k = i; }
    }
    if (maior <= tol) return [a, b];
    var esq = douglasPeucker(pts.slice(0, k + 1), tol), dir = douglasPeucker(pts.slice(k), tol);
    return esq.slice(0, -1).concat(dir);
  }
  function terminaMao() {
    var c = S.caminho, mao = c && c.mao;
    if (!mao) return;
    c.mao = null;
    douglasPeucker(mao, TOLERANCIA_DP_PX).slice(1).forEach(function (px) { adicionaPonto(pixelParaJogo(px[0], px[1])); });
    atualizaTudo();
  }
  function desenhaCaminho() {
    var c = S.caminho;
    if (!c) return;
    var pts = [c.inicio].concat(c.pontos);
    ctx.save();
    ctx.strokeStyle = MapCore.token("tinta-mapa"); ctx.lineWidth = 2; ctx.setLineDash([5, 4]);
    ctx.beginPath();
    pts.forEach(function (pt, i) { var px = jogoParaPixel(pt.x, pt.y); if (i) ctx.lineTo(px[0], px[1]); else ctx.moveTo(px[0], px[1]); });
    if (c.mao) c.mao.forEach(function (px) { ctx.lineTo(px[0], px[1]); });
    ctx.stroke(); ctx.setLineDash([]);
    ctx.font = "600 13px " + MapCore.token("f-num"); ctx.textAlign = "left"; ctx.textBaseline = "bottom";
    c.pontos.forEach(function (pt) {
      var px = jogoParaPixel(pt.x, pt.y);
      ctx.fillStyle = MapCore.token("tinta-mapa"); ctx.beginPath(); ctx.arc(px[0], px[1], 4, 0, 2 * Math.PI); ctx.fill();
      // o horário em que o jogador chega ali, no relógio do jogo
      var rotulo = MapCore.relogio(pt.t, S.e3 && S.e3.bomba ? S.e3.bomba.t : null, null, M3.SEGUNDOS_DO_ROUND, M3.SEGUNDOS_DA_BOMBA);
      MapCore.rotulo(rotulo, px[0], px[1], { fonte: "num", dy: 6, prioridade: 2 });
    });
    ctx.restore();
  }

