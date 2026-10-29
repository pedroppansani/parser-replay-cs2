  /* ---------------------------------------------------------------------
     FORMATO 3: o tempo do round é o eixo -- espelho de metrics/tactics.py
     (linha_do_tempo -> taticaNoTempo, estado_no_tempo -> quadroNoTempo).
     As constantes medidas (velocidade, voo, efeitos, vocabulário de funções)
     chegam do Python pelo build, em M3: nada digitado em dois lugares.
     --------------------------------------------------------------------- */
  var M3 = null;   // preenchido no init com cfg.modelo3

  function inicios(passos) {
    var out = [], t = 0;
    passos.forEach(function (p) { out.push(t); t += p.duracao_s; });
    return out;
  }

  function vooEstimado(arma, origem, destino) {
    var d = Math.hypot(destino[0] - origem[0], destino[1] - origem[1]);
    if (arma === "flash" || arma === "he") return M3.VOO_PAVIO_S;
    if (arma === "molotov") return Math.min(M3.VOO_MOLOTOV_MAX_S, M3.VOO_MOLOTOV[0] + M3.VOO_MOLOTOV[1] * d);
    return M3.VOO_SMOKE[0] + M3.VOO_SMOKE[1] * d;
  }

  function velocidade(funcao, modo) {
    var arma = funcao === M3.FUNCAO_COM_AWP ? "AWP" : "rifle";
    var m = M3.MODOS_DE_ANDAR.indexOf(modo) >= 0 ? modo : "correndo";
    return M3.VELOCIDADE_U_S[arma + "|" + m];
  }

  function interpolaAngulo(a, b, f) {
    var delta = ((b - a + 540) % 360) - 180;
    return (((a + delta * f) % 360) + 360) % 360;
  }

  function posicaoNoTempo(peca, t) {
    var pts = peca.pontos;
    if (!pts.length) return null;
    var ant = null, i;
    for (i = 0; i < pts.length; i++) if (pts[i].t <= t) ant = pts[i];
    if (ant === null) {
      ant = pts[0];
      if (ant.fora) return null;
      return { x: ant.x, y: ant.y, nivel: ant.nivel, movendo: false, rumo: null };
    }
    if (ant.fora) return null;
    var prox = null;
    for (i = 0; i < pts.length; i++) if (pts[i].t > t) { prox = pts[i]; break; }
    if (prox === null || prox.fora || prox.t <= ant.t) return { x: ant.x, y: ant.y, nivel: ant.nivel, movendo: false, rumo: null };
    var f = (t - ant.t) / (prox.t - ant.t);
    var movendo = prox.x !== ant.x || prox.y !== ant.y;
    var rumo = movendo ? (((Math.atan2(prox.y - ant.y, prox.x - ant.x) * 180 / Math.PI) % 360) + 360) % 360 : null;
    return { x: ant.x + (prox.x - ant.x) * f, y: ant.y + (prox.y - ant.y) * f, nivel: f < 0.5 ? ant.nivel : prox.nivel,
             movendo: movendo, rumo: rumo, _ant: ant, _prox: prox, _f: f };
  }

  function yawNoTempo(peca, t, pos, centro) {
    var prox = pos._prox;
    if (pos.movendo && prox && prox.caminho && prox.yaw === null) {
      var k = Math.pow(10, CASAS_DIRECAO_PADRAO);
      return [((Math.round(pos.rumo * k) / k) % 360 + 360) % 360, false];
    }
    var explicitos = peca.pontos.filter(function (pt) { return !pt.fora && pt.yaw !== null; });
    var antes = explicitos.filter(function (pt) { return pt.t <= t; });
    if (!antes.length) return [direcaoPadrao(pos.x, pos.y, centro), true];
    var a = antes[antes.length - 1];
    var depois = null;
    for (var i = 0; i < explicitos.length; i++) if (explicitos[i].t > t) { depois = explicitos[i]; break; }
    if (depois === null || !prox || depois !== prox) return [a.yaw, false];
    return [interpolaAngulo(a.yaw, depois.yaw, (t - a.t) / (depois.t - a.t)), false];
  }

  function taticaNoTempo(operacoes) {
    var base = aplica(operacoes);
    var passos = base.passos, ini = inicios(passos);
    var duracao = passos.reduce(function (s, p) { return s + p.duracao_s; }, 0);
    var indice = {}; passos.forEach(function (p, k) { indice[p.passo] = k; });
    function tDoPasso(passo) { return ini[indice[passo]]; }
    function fimDaVida(passo, dura) {
      var k = indice[passo];
      if (dura === null || dura === undefined || k + dura >= passos.length) return null;
      return ini[k + dura];
    }
    var estado = { titulo: base.titulo, duracao_s: duracao,
      marcos: passos.map(function (p, k) { return { passo: p.passo, titulo: p.titulo, t: ini[k], duracao_s: p.duracao_s }; }),
      pecas: {}, granadas: {}, tracos: {}, bomba: null, notas: {} };
    Object.keys(base.pecas).forEach(function (pid) {
      var p = base.pecas[pid], pontos = [];
      passos.forEach(function (q, k) {
        var chave = q.passo;
        if (!tem(p.posicoes, chave) && !tem(p.direcoes, chave)) return;
        if (tem(p.posicoes, chave) && p.posicoes[chave] === null) {
          pontos.push({ id: "passo:" + chave, t: ini[k], x: null, y: null, nivel: 0, yaw: null, fora: true, caminho: false, modo: null });
          return;
        }
        var pos = posicaoNoPasso(p, passos, k);
        if (pos === null) return;
        var nivel = 0;
        passos.slice(0, k + 1).forEach(function (q2) { if (tem(p.niveis, q2.passo)) nivel = p.niveis[q2.passo]; });
        pontos.push({ id: "passo:" + chave, t: ini[k], x: pos[0], y: pos[1], nivel: nivel,
                      yaw: tem(p.direcoes, chave) ? p.direcoes[chave] : null, fora: false, caminho: false, modo: null });
      });
      if (pontos.length && pontos[0].t > 0) {
        pontos.unshift({ id: "entrada", t: 0, x: null, y: null, nivel: 0, yaw: null, fora: true, caminho: false, modo: null });
      }
      estado.pecas[pid] = { lado: p.lado, rotulo: p.rotulo, funcao: null, criada_em_ordem: p.criada_em_ordem, pontos: pontos };
    });
    Object.keys(base.granadas).forEach(function (gid) {
      var g = base.granadas[gid], n = {};
      Object.keys(g).forEach(function (k) { if (k !== "dura_passos") n[k] = g[k]; });
      n.t = tDoPasso(g.passo); n.jogador = null;
      n.voo_s = vooEstimado(g.arma, g.origem, g.destino);
      n.efeito_s = tem(M3.DURACAO_EFEITO_S, g.arma) ? M3.DURACAO_EFEITO_S[g.arma] : 0;
      var fim = fimDaVida(g.passo, g.dura_passos);
      n.vida_s = fim === null ? null : fim - n.t;
      estado.granadas[gid] = n;
    });
    Object.keys(base.tracos).forEach(function (tid) {
      var tr = base.tracos[tid], n = {};
      Object.keys(tr).forEach(function (k) { if (k !== "dura_passos") n[k] = tr[k]; });
      n.t_inicio = tDoPasso(tr.passo); n.t_fim = fimDaVida(tr.passo, tr.dura_passos);
      estado.tracos[tid] = n;
    });
    Object.keys(estado.granadas).forEach(function (gid) {
      var g = estado.granadas[gid], melhor = null, dist = M3.RAIO_DO_ARREMESSADOR_U;
      Object.keys(estado.pecas).forEach(function (pid) {
        var pos = posicaoNoTempo(estado.pecas[pid], g.t);
        if (pos === null) return;
        var d = Math.hypot(pos.x - g.origem[0], pos.y - g.origem[1]);
        if (d <= dist && (melhor === null || d < dist || pid < melhor)) { melhor = pid; dist = d; }
      });
      g.jogador = melhor;
    });
    var fora = anuladas(operacoes);
    operacoes.slice().sort(chaveDeOrdem).forEach(function (op) {
      if (fora[op.id]) return;
      var t = op.tipo, peca = tem(op, "peca") ? estado.pecas[op.peca] : null;
      if (t === "cria_caminho" && peca) {
        op.pontos.forEach(function (pt, i) {
          peca.pontos.push({ id: op.id + ":" + i, t: pt.t, x: pt.x, y: pt.y, nivel: pt.nivel || 0,
                             yaw: pt.yaw === undefined || pt.yaw === null ? null : pt.yaw, fora: !!pt.fora, caminho: true,
                             modo: pt.modo === undefined ? null : pt.modo, morte: !!pt.morte });
        });
      } else if (t === "move_ponto" && peca) {
        peca.pontos.forEach(function (pt) {
          if (pt.id !== op.ponto || pt.fora) return;
          pt.t = op.t; pt.x = op.x; pt.y = op.y;
          if (tem(op, "nivel")) pt.nivel = op.nivel;
          if (tem(op, "yaw")) pt.yaw = op.yaw === null ? null : op.yaw;
        });
      } else if (t === "remove_ponto" && peca) {
        peca.pontos = peca.pontos.filter(function (pt) { return pt.id !== op.ponto; });
      } else if (t === "define_funcao" && peca) {
        peca.funcao = op.funcao;
      } else if (t === "planta_bomba") {
        estado.bomba = { t: op.t, x: op.x, y: op.y, nivel: op.nivel || 0 };
      } else if (t === "nota_de_evento") {
        estado.notas[op.alvo] = op.texto;
      } else if (t === "cria_granada" && estado.granadas[op.granada]) {
        var g = estado.granadas[op.granada];
        if (tem(op, "t")) g.t = op.t;
        if (tem(op, "jogador")) g.jogador = op.jogador;
        if (g.arremesso && g.arremesso.voo_s !== undefined && g.arremesso.voo_s !== null) g.voo_s = g.arremesso.voo_s;
        // fase 9: voo e efeito medidos no replay (granada de um round aberto)
        if (tem(op, "voo_s")) g.voo_s = op.voo_s;
        if (tem(op, "efeito_s")) g.efeito_s = op.efeito_s;
      }
    });
    Object.keys(estado.pecas).forEach(function (pid) {
      var pts = estado.pecas[pid].pontos.map(function (pt, i) { return [pt, i]; });
      pts.sort(function (a, b) { return a[0].t - b[0].t || a[1] - b[1]; });
      estado.pecas[pid].pontos = pts.map(function (x) { return x[0]; });
    });
    return estado;
  }

  function quadroNoTempo(e3, t, centro) {
    var pecas = {}, granadas = {}, tracos = {};
    Object.keys(e3.pecas).forEach(function (pid) {
      var p = e3.pecas[pid], pos = posicaoNoTempo(p, t);
      if (pos === null) return;
      var yd = yawNoTempo(p, t, pos, centro);
      pecas[pid] = { lado: p.lado, rotulo: p.rotulo, funcao: p.funcao, x: pos.x, y: pos.y, nivel: pos.nivel,
                     yaw: yd[0], direcao_padrao: yd[1] };
    });
    Object.keys(e3.granadas).forEach(function (gid) {
      var g = e3.granadas[gid];
      if (t < g.t) return;
      var chegada = g.t + g.voo_s, n = copia(g);
      if (t < chegada) { n.fase = "voo"; n.progresso = g.voo_s > 0 ? (t - g.t) / g.voo_s : 1; granadas[gid] = n; }
      else if (t < chegada + g.efeito_s) { n.fase = "efeito"; n.progresso = (t - chegada) / g.efeito_s; granadas[gid] = n; }
      else if ((g.vida_s === null || t < g.t + g.vida_s) && g.efeito_s === 0) { n.fase = "marca"; n.progresso = 1; granadas[gid] = n; }
    });
    Object.keys(e3.tracos).forEach(function (tid) {
      var tr = e3.tracos[tid];
      if (tr.t_inicio <= t && (tr.t_fim === null || t < tr.t_fim)) tracos[tid] = tr;
    });
    // a marca de morte (fase 9): quem saiu morto até t e não voltou ao mapa
    var mortos = {};
    Object.keys(e3.pecas).forEach(function (pid) {
      if (pecas[pid]) return;
      var p = e3.pecas[pid], ultimo = null;
      p.pontos.forEach(function (pt) { if (pt.t <= t) ultimo = pt; });
      if (ultimo && ultimo.morte) mortos[pid] = { lado: p.lado, rotulo: p.rotulo, x: ultimo.x, y: ultimo.y, nivel: ultimo.nivel, t: ultimo.t };
    });
    var marco = null;
    e3.marcos.forEach(function (m) { if (m.t <= t) marco = m.passo; });
    var plant = e3.bomba ? e3.bomba.t : null;
    return { t: t, relogio: MapCore.relogio(t, plant, null, M3.SEGUNDOS_DO_ROUND, M3.SEGUNDOS_DA_BOMBA), marco: marco,
             pecas: pecas, granadas: granadas, tracos: tracos, bomba: e3.bomba && t >= e3.bomba.t ? e3.bomba : null,
             mortos: mortos };
  }

  function ordemDeCriacao(estado) {
    var itens = [];
    Object.keys(estado.granadas).forEach(function (k) { itens.push(["granada", k, estado.granadas[k]]); });
    Object.keys(estado.tracos).forEach(function (k) { itens.push(["traco", k, estado.tracos[k]]); });
    itens.sort(function (a, b) {
      var x = a[2].criada_em_ordem, y = b[2].criada_em_ordem;
      return chaveDeOrdem({ seq: x[0], autor: x[1], id: x[2] }, { seq: y[0], autor: y[1], id: y[2] });
    });
    return itens.map(function (t) { return { tipo: t[0], id: t[1], passo: t[2].passo }; });
  }

  function mescla(a, b) {
    if (a.id !== b.id) throw new Error("mesclar táticas diferentes: ids distintos");
    var porId = {};
    a.operacoes.forEach(function (op) { porId[op.id] = op; });
    b.operacoes.forEach(function (op) { if (!porId[op.id]) porId[op.id] = op; });
    var saida = copia(a);
    saida.operacoes = Object.keys(porId).map(function (k) { return porId[k]; }).sort(chaveDeOrdem);
    saida.contador = Math.max(a.contador, b.contador);
    saida.versao = FORMATO;
    return saida;
  }

  /** Formato 1 -> atual, em memória: só a versão muda. */
  function migra(doc) {
    var d = Object.assign({}, doc);
    d.versao = FORMATO;
    return d;
  }

  function ehInteiro(v) { return typeof v === "number" && isFinite(v) && Math.floor(v) === v; }
  function ehNumero(v) { return typeof v === "number" && isFinite(v); }

