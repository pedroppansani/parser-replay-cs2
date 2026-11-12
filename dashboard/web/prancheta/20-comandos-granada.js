  /* ---------------------------------------------------------------------
     ABA COMANDOS, a granada real (C4, decisão 64): "joga molotov na Caverna" puxa UM arremesso real da biblioteca que a prancheta já carrega, do MESMO tipo e do
     MESMO lado (o lado gravado no R0), que caiu perto do destino. Sem índice novo: a busca é linear na biblioteca (uns 2 mil por tipo).
       - perto do destino: a queda a até `raio_queda` (150 u) em xy de um ponto do Pedro (de qualquer ponto de um alvo do meio, como as duas TVs) ou DENTRO da área da demo;
         a flash vale pelo ponto onde estoura (o último ponto do projétil), só em xy;
       - as jogadas juntas pela posição de saída (a até `raio_saida`, 50 u: o mesmo lugar de lançamento); a que representa a jogada é a que caiu mais perto;
       - a lista: da saída mais perto da peça para a mais longe, em faixas de 50 u e, na mesma faixa, o voo conhecido antes do desconhecido.
     O voo desconhecido NUNCA vira horário de queda. Nada de outro lado nem de outro tipo, mesmo quando o lado certo tem poucos: o cartão só avisa.
     --------------------------------------------------------------------- */

  function cmdGr() { return cfg.comandos.granada; }

  /** "carregando" (o arquivo da biblioteca ainda não chegou), "sem" (o mapa não tem biblioteca) ou "ok". */
  function cmdEstadoDaBiblioteca() {
    if (cfg.biblioteca) return "ok";
    return typeof bibliotecaPronta === "function" && !bibliotecaPronta() ? "carregando" : "sem";
  }

  /** Os pontos do Pedro de um alvo (as duas TVs são um alvo só, com dois pontos). */
  function cmdPontosDoAlvo(alvo) {
    if (alvo.tipo !== "ponto") return [];
    var ids = alvo.ids || [alvo.id];
    var ps = cfg.comandos.pontos.filter(function (p) { return ids.indexOf(p.id) >= 0; });
    return ps.length ? ps : [{ x: alvo.x, y: alvo.y }];
  }

  /** A distância (xy) da queda ao alvo, ou null se não cai nele. */
  function cmdQuedaNoAlvo(r, alvo, pontos) {
    if (alvo.tipo === "area") {
      return lugarDe(r.destino[0], r.destino[1], nivelDoZ(r.destino[2])) === alvo.nome ? Math.hypot(r.destino[0] - alvo.x, r.destino[1] - alvo.y) : null;
    }
    var d = null;
    pontos.forEach(function (p) { var x = Math.hypot(r.destino[0] - p.x, r.destino[1] - p.y); if (d === null || x < d) d = x; });
    return d !== null && d <= cmdGr().raio_queda ? d : null;
  }

  /** Os arremessos reais de `arma` que caem no alvo, do lado da peça e do outro, e a lista de jogadas do lado certo ordenada pela peça em `ini`. */
  function cmdBuscaReal(arma, alvo, lado, ini) {
    var estado = cmdEstadoDaBiblioteca();
    if (estado !== "ok") return { estado: estado, grupos: [], mesmo: 0, outro: 0 };
    var pontos = cmdPontosDoAlvo(alvo), mesmo = [], outro = 0;
    cfg.biblioteca.arremessos.forEach(function (r) {
      if (r.arma !== arma) return;
      var d = cmdQuedaNoAlvo(r, alvo, pontos);
      if (d === null) return;
      if (r.lado === lado) mesmo.push({ r: r, d: d }); else outro++;
    });
    mesmo.sort(function (a, b) { return a.d - b.d || (a.r.id < b.r.id ? -1 : 1); });
    var grupos = [], saida = cmdGr().raio_saida;
    mesmo.forEach(function (x) {
      var g = grupos.filter(function (g) { return Math.hypot(g.r.origem[0] - x.r.origem[0], g.r.origem[1] - x.r.origem[1]) <= saida; })[0];
      if (g) g.jogadas++; else grupos.push({ r: x.r, d: x.d, jogadas: 1 });
    });
    grupos.forEach(function (g) { g.dist = Math.hypot(g.r.origem[0] - ini.x, g.r.origem[1] - ini.y); g.voo = g.r.voo_s !== null && g.r.voo_s !== undefined; });
    grupos.sort(function (a, b) {
      var fa = Math.floor(a.dist / 50), fb = Math.floor(b.dist / 50);
      return fa - fb || (a.voo === b.voo ? a.dist - b.dist : (a.voo ? -1 : 1));
    });
    return { estado: "ok", grupos: grupos, mesmo: mesmo.length, outro: outro };
  }

  function cmdLadoEscrito(lado) { return lado === "ct" ? "CT" : "TR"; }

  /** O aviso de lado: poucos do lado certo e muitos do outro. Nunca usa o do outro lado. */
  function cmdAvisoDeLado(arma, lado, busca) {
    var g = cmdGr();
    if (busca.estado !== "ok" || busca.mesmo >= g.poucos || busca.outro < g.muitos) return null;
    var v = { n: busca.mesmo, arremessos: busca.mesmo === 1 ? "arremesso real" : "arremessos reais", lado: cmdLadoEscrito(lado), outro: cmdLadoEscrito(lado === "ct" ? "t" : "ct"),
              granada: String(cmdT("granada_" + arma) || arma).toLowerCase(), m: busca.outro };
    return cmdT(busca.mesmo ? "aviso_poucos_do_lado" : "aviso_nenhum_do_lado", v);
  }

  /** O que a linha do cartão diz do arremesso real escolhido: qual (i de n), de que partida e round, de onde sai e, se o voo é conhecido, quando cai. */
  function cmdTextoDaGranada(g) {
    if (!g || !g.r) return "";
    var times = cfg.biblioteca && cfg.biblioteca.partidas_times && cfg.biblioteca.partidas_times[g.r.partida];      // os times, como a lista de Partidas ("FURIA × Vitality"); sem eles, o id
    var v = { i: g.i, n: g.n, lado: cmdLadoEscrito(g.lado), partida: times || g.r.partida, round: g.r.round, onde: g.onde, h: cmdDoRelogio(g.tSai), hc: g.tCai == null ? "" : cmdDoRelogio(g.tCai) };
    var texto = cmdT(g.tCai == null ? "granada_real_sem_voo" : "granada_real", v);
    return g.levar ? texto + "; " + cmdT("granada_levar", { quem: g.quem, h: cmdDoRelogio(g.levar.chega) }) : texto;
  }
