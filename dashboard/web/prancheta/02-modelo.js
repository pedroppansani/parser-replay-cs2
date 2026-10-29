  /* ---------------------------------------------------------------------
     Modelo -- espelho de metrics/tactics.py
     --------------------------------------------------------------------- */
  function chaveDeOrdem(a, b) {
    if (a.seq !== b.seq) return a.seq - b.seq;
    if (a.autor !== b.autor) return a.autor < b.autor ? -1 : 1;
    if (a.id !== b.id) return a.id < b.id ? -1 : 1;
    return 0;
  }
  function ordemDe(op) { return [op.seq, String(op.autor), String(op.id)]; }
  function copia(v) { return JSON.parse(JSON.stringify(v)); }
  function tem(o, k) { return Object.prototype.hasOwnProperty.call(o, k); }

  /** Ids das operações desfeitas agora: para cada alvo vale a ÚLTIMA
      anula/reativa. Inválida (outro autor, alvo que é anula/reativa, alvo fora
      do log) não vale. */
  function anuladas(operacoes) {
    var porId = {}, ultima = {};
    operacoes.forEach(function (op) { porId[op.id] = op; });
    operacoes.slice().sort(chaveDeOrdem).forEach(function (op) {
      if (DESFAZER.indexOf(op.tipo) < 0) return;
      var alvo = porId[op.alvo];
      if (!alvo || DESFAZER.indexOf(alvo.tipo) >= 0 || alvo.autor !== op.autor) return;
      ultima[alvo.id] = op.tipo;
    });
    var fora = {};
    Object.keys(ultima).forEach(function (k) { if (ultima[k] === "anula") fora[k] = true; });
    return fora;
  }

  function aplica(operacoes) {
    var fora = anuladas(operacoes);
    var estado = { titulo: "", passos: [], pecas: {}, granadas: {}, tracos: {} };
    var passos = {}, ordem = [];
    operacoes.slice().sort(chaveDeOrdem).forEach(function (op) {
      if (fora[op.id]) return;
      var p, g, alvo;
      switch (op.tipo) {
        case "renomeia": estado.titulo = op.titulo; break;
        case "cria_passo":
          if (!passos[op.passo]) {
            passos[op.passo] = { passo: op.passo, titulo: op.titulo, duracao_s: DURACAO_PADRAO_S };
            ordem.push(op.passo);
          }
          break;
        case "renomeia_passo": if (passos[op.passo]) passos[op.passo].titulo = op.titulo; break;
        case "define_duracao": if (passos[op.passo]) passos[op.passo].duracao_s = +op.segundos; break;
        case "remove_passo":
          if (passos[op.passo]) { delete passos[op.passo]; ordem.splice(ordem.indexOf(op.passo), 1); }
          break;
        case "cria_peca":
          if (!estado.pecas[op.peca] && passos[op.passo]) {
            p = { lado: op.lado, rotulo: op.rotulo, criada_em_ordem: ordemDe(op),
                  posicoes: {}, niveis: {}, direcoes: {} };
            p.posicoes[op.passo] = [+op.x, +op.y];
            p.niveis[op.passo] = tem(op, "nivel") ? +op.nivel : 0;
            if (op.yaw !== undefined && op.yaw !== null) p.direcoes[op.passo] = +op.yaw;
            estado.pecas[op.peca] = p;
          }
          break;
        case "move_peca":
          p = estado.pecas[op.peca];
          if (p && passos[op.passo]) {
            p.posicoes[op.passo] = [+op.x, +op.y];
            p.niveis[op.passo] = tem(op, "nivel") ? +op.nivel : 0;
          }
          break;
        case "gira_peca":
          p = estado.pecas[op.peca];
          if (p && passos[op.passo]) p.direcoes[op.passo] = +op.yaw;
          break;
        case "tira_peca":
          p = estado.pecas[op.peca];
          if (p && passos[op.passo]) { p.posicoes[op.passo] = null; delete p.niveis[op.passo]; }
          break;
        case "remove_peca": delete estado.pecas[op.peca]; break;
        case "cria_granada":
          if (!estado.granadas[op.granada] && passos[op.passo]) {
            estado.granadas[op.granada] = {
              arma: op.arma, passo: op.passo,
              origem: op.origem.map(Number), destino: op.destino.map(Number),
              nivel: tem(op, "nivel") ? +op.nivel : 0,
              arremesso: op.arremesso === undefined ? null : op.arremesso,
              dura_passos: tem(op, "dura_passos") ? op.dura_passos : VIDA_PADRAO_GRANADA[op.arma],
              criada_em_ordem: ordemDe(op)
            };
            // o campo só existe quando é verdade (espelho do Python)
            if (op.origem_desconhecida === true) estado.granadas[op.granada].origem_desconhecida = true;
          }
          break;
        case "move_granada":
          g = estado.granadas[op.granada];
          if (g) {
            g.origem = op.origem.map(Number); g.destino = op.destino.map(Number);
            g.nivel = tem(op, "nivel") ? +op.nivel : 0;
            g.arremesso = null;   // arrastada à mão deixou de ser o arremesso real
            delete g.origem_desconhecida;
          }
          break;
        case "remove_granada": delete estado.granadas[op.granada]; break;
        case "cria_traco":
          if (!estado.tracos[op.traco] && passos[op.passo]) {
            estado.tracos[op.traco] = {
              passo: op.passo, ferramenta: op.ferramenta, cor: op.cor, espessura: op.espessura,
              pontos: op.pontos.map(function (q) { return [+q[0], +q[1]]; }),
              texto: op.texto === undefined ? null : op.texto,
              nivel: tem(op, "nivel") ? +op.nivel : 0,
              dura_passos: tem(op, "dura_passos") ? op.dura_passos : VIDA_PADRAO_TRACO,
              criada_em_ordem: ordemDe(op)
            };
          }
          break;
        case "desenha_granada":
          if (!estado.tracos[op.traco] && passos[op.passo]) {
            estado.tracos[op.traco] = {
              passo: op.passo, ferramenta: "granada", cor: null, espessura: ESPESSURA_DA_GRANADA_DESENHADA,
              pontos: [[+op.x, +op.y]], texto: null,
              nivel: tem(op, "nivel") ? +op.nivel : 0,
              dura_passos: tem(op, "dura_passos") ? op.dura_passos : VIDA_PADRAO_TRACO,
              criada_em_ordem: ordemDe(op),
              arma: op.arma, area: tem(op, "area") ? !!op.area : false
            };
          }
          break;
        case "define_area_desenho":
          if (estado.tracos[op.traco] && estado.tracos[op.traco].ferramenta === "granada") estado.tracos[op.traco].area = !!op.area;
          break;
        case "remove_traco": delete estado.tracos[op.traco]; break;
        case "define_vida":
          alvo = estado.granadas[op.alvo] || estado.tracos[op.alvo];
          if (alvo) alvo.dura_passos = op.dura_passos;
          break;
      }
    });
    estado.passos = ordem.map(function (k) { return passos[k]; });
    Object.keys(estado.pecas).forEach(function (k) {
      ["posicoes", "niveis", "direcoes"].forEach(function (campo) {
        var m = estado.pecas[k][campo], limpo = {};
        Object.keys(m).forEach(function (s) { if (passos[s]) limpo[s] = m[s]; });
        estado.pecas[k][campo] = limpo;
      });
    });
    ["granadas", "tracos"].forEach(function (grupo) {
      Object.keys(estado[grupo]).forEach(function (k) {
        if (!passos[estado[grupo][k].passo]) delete estado[grupo][k];
      });
    });
    return estado;
  }

  function posicaoNoPasso(peca, passos, indice) {
    var pos = null;
    for (var i = 0; i <= indice && i < passos.length; i++) {
      if (tem(peca.posicoes, passos[i].passo)) pos = peca.posicoes[passos[i].passo];
    }
    return pos;
  }

  function centroDoRadar(r) {
    return [r.width / 2 / r.scale_px_per_unit + r.origin_x, r.origin_y - r.height / 2 / r.scale_px_per_unit];
  }

  /** Da peça para o centro do radar, em graus do CS2, em [0, 360), arredondado
      como no Python (meio para cima, CASAS_DIRECAO_PADRAO casas). */
  function direcaoPadrao(x, y, centro) {
    var ang = Math.atan2(centro[1] - y, centro[0] - x) * (180 / Math.PI);
    ang = ((ang % 360) + 360) % 360;
    var k = Math.pow(10, CASAS_DIRECAO_PADRAO);
    return (Math.floor(ang * k + 0.5) / k) % 360;
  }

  function visivel(nasce, dura, i) { return nasce <= i && (dura === null || dura === undefined || i < nasce + dura); }

  function quadroDoPasso(estado, i, centro) {
    var passos = estado.passos, indice = {};
    passos.forEach(function (p, k) { indice[p.passo] = k; });
    var pecas = {};
    Object.keys(estado.pecas).forEach(function (pid) {
      var p = estado.pecas[pid], pos = null, nivel = 0, yaw = null;
      for (var k = 0; k <= i && k < passos.length; k++) {
        var s = passos[k].passo;
        if (tem(p.posicoes, s)) { pos = p.posicoes[s]; nivel = tem(p.niveis, s) ? p.niveis[s] : 0; }
        if (tem(p.direcoes, s)) yaw = p.direcoes[s];
      }
      if (pos === null) return;
      var padrao = yaw === null;
      pecas[pid] = { lado: p.lado, rotulo: p.rotulo, x: pos[0], y: pos[1], nivel: nivel,
                     yaw: padrao ? direcaoPadrao(pos[0], pos[1], centro) : yaw, direcao_padrao: padrao };
    });
    function vivos(grupo) {
      var out = {};
      Object.keys(estado[grupo]).forEach(function (id) {
        var e = estado[grupo][id], nasce = indice[e.passo];
        if (visivel(nasce, e.dura_passos, i)) {
          out[id] = Object.assign({}, e, { nasceu_neste_passo: nasce === i });
        }
      });
      return out;
    }
    return { indice: i, passo: passos[i].passo, titulo: passos[i].titulo, duracao_s: passos[i].duracao_s,
             pecas: pecas, granadas: vivos("granadas"), tracos: vivos("tracos") };
  }

