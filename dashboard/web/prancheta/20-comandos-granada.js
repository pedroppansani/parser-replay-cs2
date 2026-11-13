  /* ---------------------------------------------------------------------
     ABA COMANDOS, a granada real (C4, decisão 64): "joga molotov na Caverna" puxa UM arremesso real da biblioteca que a prancheta já carrega, do MESMO tipo e do
     MESMO lado (o lado gravado no R0), que caiu perto do destino. Sem índice novo: a busca é linear na biblioteca (uns 2 mil por tipo).
       - perto do destino: a queda a até `raio_queda` (150 u) em xy de um ponto do Pedro (de qualquer ponto de um alvo do meio, como as duas TVs) ou DENTRO da área da demo;
         a flash vale pelo ponto onde estoura (o último ponto do projétil), só em xy;
       - as jogadas juntas pela posição de saída (a até `raio_saida`, 50 u: o mesmo lugar de lançamento); a que representa a jogada é a que caiu mais perto;
       - a lista: da saída mais perto da peça para a mais longe, em faixas de 50 u e, na mesma faixa, o voo conhecido antes do desconhecido.
     O voo desconhecido NUNCA vira horário de queda. Nada de outro lado nem de outro tipo, mesmo quando o lado certo tem poucos: o cartão só avisa.
     --------------------------------------------------------------------- */

  function cmdLadoEscrito(lado) { return lado === "ct" ? "CT" : "TR"; }

  /** O que a linha do cartão diz do arremesso real escolhido: qual (i de n), de que partida e round, de onde sai e, se o voo é conhecido, quando cai. */
  function cmdTextoDaGranada(g) {
    if (!g || !g.r) return "";
    var times = cfg.biblioteca && cfg.biblioteca.partidas_times && cfg.biblioteca.partidas_times[g.r.partida];      // os times, como a lista de Partidas ("FURIA × Vitality"); sem eles, o id
    var v = { i: g.i, n: g.n, lado: cmdLadoEscrito(g.lado), partida: times || g.r.partida, round: g.r.round, onde: g.onde, h: cmdDoRelogio(g.tSai), hc: g.tCai == null ? "" : cmdDoRelogio(g.tCai) };
    var texto = cmdT(g.tCai == null ? "granada_real_sem_voo" : "granada_real", v);
    return g.levar ? texto + "; " + cmdT("granada_levar", { quem: g.quem, h: cmdDoRelogio(g.levar.chega) }) : texto;
  }
