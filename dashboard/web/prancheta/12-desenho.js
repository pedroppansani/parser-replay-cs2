  /* ---------------------------------------------------------------------
     Desenho
     --------------------------------------------------------------------- */
  function cssVar(nome) { return getComputedStyle(document.documentElement).getPropertyValue(nome).trim(); }
  function escalaUnidade() { return cfg.radar.scale_px_per_unit; }

  function desenha() {
    if (!ctx || !temQuadro()) return;
    S.ultimoDesenho = [];
    ctx.setTransform(1, 0, 0, 1, 0, 0);
    ctx.clearRect(0, 0, cv.width, cv.height);
    MapCore.applyView(ctx, cfg.radar, S.view);
    var im = imgs[S.andar] || imgs[0];
    // radar dessaturado por mapa (§4.1): processado uma vez e guardado na imagem; aqui só o drawImage
    if (im && im.complete && im.naturalWidth) ctx.drawImage(MapCore.radarProcessado(im, cfg.radar.map), 0, 0, cfg.radar.width, cfg.radar.height);

    // O editor e a reprodução desenham a mesma CENA; só o editor põe por cima
    // busca, rascunho, rastro do passo anterior e seleção.
    var editando = !S.reproducao;
    var cena = editando ? cenaDoEditor() : S.reproducao.cena;
    // nomes, funções e horários vão para a camada de rótulos (px de tela, por cima de tudo; §4.2)
    MapCore.rotulosInicia(ctx, cv, desenha);
    desenhaFantasma(tempoMostrado());
    if (editando) desenhaBusca();
    Object.keys(cena.granadas).forEach(function (id) { desenhaGranada(id, cena.granadas[id], editando); });
    Object.keys(cena.tracos).forEach(function (id) { desenhaTraco(id, cena.tracos[id]); });
    if (editando && S.tracando) MapCore.caminhoDoTraco(ctx, S.tracando, cfg.radar);
    if (editando && S.origemPendente) {
      var o = jogoParaPixel(S.origemPendente[0], S.origemPendente[1]);
      ctx.fillStyle = MapCore.NADE_COLOR[S.arma];
      ctx.beginPath(); ctx.arc(o[0], o[1], 5, 0, 2 * Math.PI); ctx.fill();
    }
    if (editando && S.caminho) desenhaCaminho();
    var ant = editando && S.passo > 0 && noMarco() ? quadro(S.passo - 1) : null;
    S.ultimaChegada = null;
    desenhaChegada();
    desenhaMortos(cena.mortos);
    Object.keys(cena.pecas).forEach(function (id) { desenhaPeca(id, cena.pecas[id], ant && ant.pecas[id], editando); });
    if (editando && S.ferramenta === "granada_desenho" && S.cursorDesenho) {
      // cursor de teclado do carimbo: a granada que vai sair, mais uma cruz
      MapCore.desenhaGranadaDesenhada(ctx, S.armaDesenho, S.cursorDesenho[0], S.cursorDesenho[1], cfg.radar, false);
      ctx.save(); ctx.strokeStyle = MapCore.token("foco-mapa"); ctx.lineWidth = 2; ctx.beginPath();
      ctx.moveTo(S.cursorDesenho[0] - 16, S.cursorDesenho[1]); ctx.lineTo(S.cursorDesenho[0] + 16, S.cursorDesenho[1]);
      ctx.moveTo(S.cursorDesenho[0], S.cursorDesenho[1] - 16); ctx.lineTo(S.cursorDesenho[0], S.cursorDesenho[1] + 16);
      ctx.stroke(); ctx.restore();
    }
    MapCore.rotulosDesenha();
    resumeOMapa(cena);
    desenhaBalao();
  }

  /** O que o canvas mostra, em texto, para o leitor de tela (o canvas é uma imagem): quem está no mapa, onde, e as
      granadas. Só reescreve quando muda, para não refazer a árvore de acessibilidade a cada quadro da reprodução. */
  function resumeOMapa(cena) {
    var alvo = $("pr-mapa-resumo");
    if (!alvo) return;
    var t = tempoMostrado();
    var pecas = Object.keys(cena.pecas).map(function (id) {
      var p = cena.pecas[id], lugar = lugarDe(p.x, p.y, p.nivel || 0);
      return rotuloDaPeca(p) + (p.funcao ? " (" + p.funcao + ")" : "") + (lugar ? " em " + lugar : "");
    }).sort();
    var granadas = Object.keys(cena.granadas || {}).map(function (id) {
      var g = cena.granadas[id], d = g.destino || [], lugar = d.length ? lugarDe(d[0], d[1], g.nivel || 0) : null;
      return (NOME_ARMA[g.arma] || g.arma) + (lugar ? " em " + lugar : "");
    }).sort();
    var texto = (t !== null ? "Às " + relogioEm(t) + ": " : "") +
      (pecas.length ? pecas.length + (pecas.length === 1 ? " jogador no mapa: " : " jogadores no mapa: ") + pecas.join("; ") + "."
                    : "Nenhum jogador no mapa.") +
      (granadas.length ? " Granadas: " + granadas.join("; ") + "." : "");
    if (alvo.textContent !== texto) alvo.textContent = texto;
  }

  /** O passo aberto no editor, no mesmo formato da cena da reprodução: a
      linha do arremesso só no passo em que a granada nasceu. */
  function cenaDoEditor() {
    var q = quadro(), c = { pecas: {}, granadas: {}, tracos: {}, mortos: q.mortos || {} };
    Object.keys(q.pecas).forEach(function (id) { c.pecas[id] = Object.assign({}, q.pecas[id], { alfa: 1 }); });
    Object.keys(q.granadas).forEach(function (id) {
      var g = q.granadas[id];
      var nasceu = g.nasceu_neste_passo && !g.origem_desconhecida;
      c.granadas[id] = Object.assign({}, g, {
        linha: nasceu ? 1 : (g.fase === "voo" && !g.origem_desconhecida ? g.progresso : 0),
        efeito: g.nasceu_neste_passo || g.fase !== "voo" ? 1 : 0, alfa: 1 });
    });
    Object.keys(q.tracos).forEach(function (id) { c.tracos[id] = Object.assign({}, q.tracos[id], { alfa: 1 }); });
    return c;
  }

  function alfaDoAndar(nivel) { return nivel === S.andar ? 1 : ALFA_OUTRO_ANDAR; }

  /** `g.linha` (0 a 1) é quanto da linha do arremesso está riscada e
      `g.efeito` (0 a 1) o quanto o efeito já abriu: no editor, 1 e 1 no passo
      de criação e 0 e 1 depois; na reprodução, o que o tempo disser. */
  function desenhaGranada(id, g, editando) {
    var o = g.origem, d = g.destino;
    if (editando && S.arrasto && S.arrasto.tipo === "granada" && S.arrasto.id === id) { o = S.arrasto.origem; d = S.arrasto.destino; }
    var a = jogoParaPixel(o[0], o[1]), b = jogoParaPixel(d[0], d[1]);
    var alfa = alfaDoAndar(g.nivel) * g.alfa, cor = MapCore.NADE_COLOR[g.arma];
    var area = g.arma === "smoke" || g.arma === "molotov";
    ctx.save();
    ctx.globalAlpha = alfa;
    if (area && g.efeito > 0) {
      var r = (g.arma === "smoke" ? MapCore.RAIO_SMOKE_UNIDADES : MapCore.RAIO_MOLOTOV_UNIDADES) * escalaUnidade();
      MapCore.desenhaArea(ctx, g.arma, b[0], b[1], r * g.efeito);
    }
    if (g.linha > 0) {
      var fim = [a[0] + (b[0] - a[0]) * g.linha, a[1] + (b[1] - a[1]) * g.linha];
      ctx.strokeStyle = cor; ctx.lineWidth = 2.5;
      if (!g.arremesso) ctx.setLineDash([6, 5]);   // desenhada à mão: tracejada
      ctx.beginPath(); ctx.moveTo(a[0], a[1]); ctx.lineTo(fim[0], fim[1]); ctx.stroke();
      ctx.setLineDash([]);
      ctx.fillStyle = cor;
      ctx.beginPath(); ctx.arc(a[0], a[1], 4, 0, 2 * Math.PI); ctx.fill();
    }
    if (g.efeito > 0) {
      MapCore.nadeGlyph(ctx, g.arma, b[0], b[1], RAIO_GRANADA * g.efeito, cor, Math.atan2(b[1] - a[1], b[0] - a[0]));
    } else if (g.voando && g.linha > 0) {
      // no ar: a granada na ponta da linha, no tempo de voo
      var ponta = [a[0] + (b[0] - a[0]) * g.linha, a[1] + (b[1] - a[1]) * g.linha];
      MapCore.nadeGlyph(ctx, g.arma, ponta[0], ponta[1], RAIO_GRANADA * 0.6, cor, Math.atan2(b[1] - a[1], b[0] - a[0]));
    }
    if (editando && S.sel && S.sel.id === id) {
      ctx.strokeStyle = MapCore.token("foco-mapa"); ctx.lineWidth = 3;
      ctx.beginPath(); ctx.arc(b[0], b[1], RAIO_GRANADA * 1.9, 0, 2 * Math.PI); ctx.stroke();
    }
    ctx.restore();
    S.ultimoDesenho.push({ tipo: "granada", id: id, linha: g.linha > 0, area: area && g.efeito > 0, alfa: alfa });
  }

  function desenhaTraco(id, t) {
    var alfa = alfaDoAndar(t.nivel) * t.alfa;
    ctx.save();
    ctx.globalAlpha = alfa;
    MapCore.caminhoDoTraco(ctx, t, cfg.radar);
    ctx.restore();
    S.ultimoDesenho.push({ tipo: "traco", id: id, alfa: alfa, pontos: t.pontos.length });
  }

  function yawDaPeca(id, p) {
    if (S.giro && S.giro.peca === id) return S.giro.yaw;
    if (S.arrasto && S.arrasto.tipo === "giro" && S.arrasto.id === id && S.arrasto.yaw !== null) return S.arrasto.yaw;
    return p.yaw;
  }

  function desenhaPeca(id, p, anterior, editando) {
    var pos = [p.x, p.y];
    if (editando && S.arrasto && S.arrasto.tipo === "peca" && S.arrasto.id === id) pos = S.arrasto.jogo;
    var c = jogoParaPixel(pos[0], pos[1]);
    var cor = cssVar(p.lado === "ct" ? "--ct-mapa" : "--tr-mapa");   // o canvas lê os *-mapa (decisão 48)
    var alfa = alfaDoAndar(p.nivel) * p.alfa, yaw = editando ? yawDaPeca(id, p) : p.yaw;
    // rastro do passo anterior: onde estava e para onde olhava
    if (anterior && (anterior.x !== pos[0] || anterior.y !== pos[1] || anterior.yaw !== yaw)) {
      var a = jogoParaPixel(anterior.x, anterior.y);
      ctx.save();
      ctx.globalAlpha = ALFA_RASTRO * alfa;
      if (anterior.x !== pos[0] || anterior.y !== pos[1]) {
        ctx.strokeStyle = cor; ctx.lineWidth = 2; ctx.setLineDash([8, 6]);
        ctx.beginPath(); ctx.moveTo(a[0], a[1]); ctx.lineTo(c[0], c[1]); ctx.stroke();
        ctx.setLineDash([]);
      }
      MapCore.desenhaJogador(ctx, a[0], a[1], { cor: cor, estado: "vivo", hp: 100, cego: false,
                                                nome: "", yaw: anterior.yaw, escala: ESCALA_PECA });
      ctx.restore();
    }
    ctx.save();
    ctx.globalAlpha = alfa;
    var selecionada = editando && S.sel && S.sel.id === id;
    MapCore.desenhaJogador(ctx, c[0], c[1], { cor: cor, estado: "vivo", hp: 100, cego: false,
                                              nome: rotuloDaPeca(p), yaw: yaw, escala: ESCALA_PECA,
                                              rotuloAcima: RAIO_PECA + 6, selecionado: selecionada });
    if (selecionada) {
      // selecionada: anel --foco de 3 px no raio 15 da escala da peça (§14)
      ctx.strokeStyle = MapCore.token("foco-mapa"); ctx.lineWidth = 3;
      ctx.beginPath(); ctx.arc(c[0], c[1], RAIO_PECA + 4, 0, 2 * Math.PI); ctx.stroke();
    }
    if (p.funcao) {
      // a função embaixo da peça (8.3): texto do vocabulário do projeto, na camada de rótulos
      MapCore.rotulo(p.funcao, c[0], c[1] + RAIO_PECA + 6, { dy: -16, prioridade: selecionada ? 9 : 0 });
    }
    if (editando && S.sel && S.sel.id === id) {
      var h = alca(c, yaw);
      ctx.globalAlpha = 1;
      ctx.fillStyle = MapCore.token("tinta-mapa"); ctx.strokeStyle = MapCore.token("contorno"); ctx.lineWidth = 2;
      ctx.beginPath(); ctx.arc(h[0], h[1], RAIO_ALCA, 0, 2 * Math.PI); ctx.fill(); ctx.stroke();
    }
    ctx.restore();
    S.ultimoDesenho.push({ tipo: "peca", id: id, x: c[0], y: c[1], yaw: yaw, alfa: alfa });
  }

  /** Peça do banco tem rótulo 1 a 5 e aparece como "CT 1"; peça que veio de um
      instante do replay tem o NOME do jogador, que já diz quem é. */
  function rotuloDaPeca(p) {
    return /^[1-9]$/.test(p.rotulo) ? (p.lado === "ct" ? "CT " : "TR ") + p.rotulo : p.rotulo;
  }

  /** Onde fica a alça de girar: na ponta da gota. */
  function alca(c, yaw) {
    var t = MapCore.anguloDeTela(yaw), d = MapCore.PONTA_DISTANCIA * ESCALA_PECA;
    return [c[0] + Math.cos(t) * d, c[1] + Math.sin(t) * d];
  }

  function desenhaBusca() {
    if (!S.busca) return;
    var c = jogoParaPixel(S.busca.ponto[0], S.busca.ponto[1]);
    ctx.save();
    ctx.strokeStyle = MapCore.corComAlfa("tinta", 0.8); ctx.setLineDash([6, 5]); ctx.lineWidth = 2;
    ctx.beginPath(); ctx.arc(c[0], c[1], S.busca.raio * escalaUnidade(), 0, 2 * Math.PI); ctx.stroke();
    ctx.setLineDash([]);
    S.busca.resultados.forEach(function (r, n) {
      var a = jogoParaPixel(r.origem[0], r.origem[1]), b = jogoParaPixel(r.destino[0], r.destino[1]);
      var foco = S.busca.foco === n;
      ctx.globalAlpha = foco ? 1 : 0.45;
      ctx.strokeStyle = MapCore.NADE_COLOR[r.arma]; ctx.lineWidth = foco ? 3 : 1.2;
      ctx.beginPath(); ctx.moveTo(a[0], a[1]); ctx.lineTo(b[0], b[1]); ctx.stroke();
      ctx.fillStyle = MapCore.NADE_COLOR[r.arma];
      ctx.beginPath(); ctx.arc(a[0], a[1], foco ? 6 : 3.5, 0, 2 * Math.PI); ctx.fill();
    });
    ctx.restore();
  }

