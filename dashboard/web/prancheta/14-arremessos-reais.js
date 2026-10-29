  /* ---------------------------------------------------------------------
     Arremessos reais: "quero a granada AQUI"
     --------------------------------------------------------------------- */
  function busca(ponto, arma) {
    var arr = (cfg.biblioteca && cfg.biblioteca.arremessos) || [];
    var raio = S.raioBusca, res = [];
    arma = arma || S.arma;
    arr.forEach(function (r) {
      if (r.arma !== arma) return;
      if (S.soParado && (r.movimento !== "parado" || r.no_ar)) return;
      var d = Math.hypot(r.destino[0] - ponto[0], r.destino[1] - ponto[1]);
      if (d <= raio) res.push({ r: r, d: d });
    });
    res.sort(function (a, b) { return a.d - b.d || (a.r.id < b.r.id ? -1 : 1); });
    S.busca = { ponto: ponto, raio: raio, total: res.length, arma: arma,
                resultados: res.slice(0, MAX_RESULTADOS).map(function (x) { return x.r; }), foco: null };
    desenha(); atualizaBusca();
  }

  /** Arremesso real escolhido. Com arremessador: a granada sai no horário do
      cabeçote, o caminho dele ganha um ponto-chave na posição do arremesso (com
      o yaw do arremesso), e se não dá tempo de chegar lá a interface AVISA
      quanto atrasa e oferece adiar -- nunca teleporta em silêncio. Tudo é UMA
      ação no desfazer (o lote inclui a granada desenhada que ele substitui). */
  function usaArremesso(r, pid, antes) {
    pid = pid === undefined ? (S.sel && S.sel.tipo === "peca" ? S.sel.id : null) : pid;
    var dados = { granada: novoId(), arma: r.arma, passo: passoAtual(), nivel: nivelDoZ(r.origem[2]),
                  origem: r.origem.slice(0, 2), destino: r.destino.slice(0, 2), arremesso: r };
    var ops = (antes || []).slice();
    S.atraso = null;
    if (M3 && pid && S.estado.pecas[pid]) {
      dados.t = S.t; dados.jogador = pid;
      ops.push(["cria_granada", dados]);
      var yaw = ((Math.round(r.yaw) % 360) + 360) % 360;
      ops = ops.concat(opsDoPonto(pid, S.t, r.origem[0], r.origem[1], dados.nivel, yaw));
      var chega = chegadaPossivel(pid, r.origem[0], r.origem[1]);
      if (chega !== null && chega > S.t + 0.05) {
        S.atraso = { granada: dados.granada, peca: pid, segundos: chega - S.t, t: Math.round(chega * 100) / 100,
                     dados: dados, yaw: yaw };
      }
    } else {
      if (M3 && !noMarco()) dados.t = S.t;
      ops.push(["cria_granada", dados]);
    }
    emiteLote(ops);
    S.sel = { tipo: "granada", id: dados.granada };
    S.busca = null; S.sugestao = null; S.acao = null; S.ferramenta = "mover";
    atualizaTudo();
  }

  /** "Adiar o arremesso": a granada passa para o horário em que ele chega, e o
      ponto do arremesso vai junto. Uma ação no desfazer. */
  function adiaArremesso() {
    var a = S.atraso;
    if (!a || !S.estado.granadas[a.granada]) return;
    var dados = Object.assign({}, a.dados, { t: a.t });
    S.atraso = null;
    var t0 = S.t;
    S.t = a.t; S.passo = marcoQueContem(S.t);
    var ops = [["remove_granada", { granada: a.granada }], ["cria_granada", dados]];
    // o ponto do horário antigo sai (se era ponto de caminho) e entra no novo
    var p = S.e3.pecas[a.peca], velho = p && p.pontos.filter(function (q) {
      return q.caminho && !q.fora && Math.abs(q.t - t0) < EPS_T && q.x === a.dados.origem[0] && q.y === a.dados.origem[1];
    }).pop();
    if (velho) ops.push(["move_ponto", { peca: a.peca, ponto: velho.id, t: a.t, x: velho.x, y: velho.y, nivel: velho.nivel, yaw: a.yaw }]);
    else ops = ops.concat(opsDoPonto(a.peca, a.t, a.dados.origem[0], a.dados.origem[1], a.dados.nivel, a.yaw));
    emiteLote(ops);
    S.sel = { tipo: "granada", id: a.granada };
    atualizaTudo();
  }

  /** Muda o horário de uma granada: sai e entra de novo com o MESMO id (as
      notas e a seleção continuam valendo). Uma ação no desfazer. */
  function mudaHorarioDaGranada(gid, t) {
    var op = S.doc.operacoes.filter(function (o) { return o.tipo === "cria_granada" && o.granada === gid; }).pop();
    var g = S.e3 && S.e3.granadas[gid];
    if (!op || !g) return;
    var dados = {};
    Object.keys(op).forEach(function (k) { if (["id", "seq", "autor", "em", "tipo"].indexOf(k) < 0) dados[k] = op[k]; });
    var est = S.estado.granadas[gid];
    dados.origem = est.origem.slice(); dados.destino = est.destino.slice(); dados.nivel = est.nivel;
    dados.arremesso = est.arremesso; dados.t = Math.max(0, Math.round(t * 100) / 100);
    if (g.jogador) dados.jogador = g.jogador;
    emiteLote([["remove_granada", { granada: gid }], ["cria_granada", dados]]);
  }

