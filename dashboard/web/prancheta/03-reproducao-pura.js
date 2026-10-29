  /* ---------------------------------------------------------------------
     Reprodução -- FUNÇÃO PURA DO TEMPO
     O passo k ocupa o intervalo (início_k, início_k + duração_k] da linha do
     tempo (o primeiro inclui o 0). Durante ele as peças vão do passo k-1 ao k,
     e em t = fim do intervalo o quadro é exatamente quadro_do_passo(k). Não há
     estado de "onde a animação estava": arrastar a barra até t e tocar até t
     chamam a mesma função com o mesmo t.
     --------------------------------------------------------------------- */
  function linhaDoTempo(estado) {
    var inicios = [], total = 0;
    estado.passos.forEach(function (p) { inicios.push(total); total += p.duracao_s; });
    return { inicios: inicios, total: total };
  }

  // Entrada e saída suaves (smoothstep): começa e termina parado.
  function suave(u) { return u <= 0 ? 0 : u >= 1 ? 1 : u * u * (3 - 2 * u); }
  function entre(v) { return Math.max(0, Math.min(1, v)); }

  function tracoParcial(t, p) {
    var n = t.pontos.length, pontos;
    if (t.ferramenta === "caneta") pontos = t.pontos.slice(0, Math.max(1, Math.ceil(p * n)));
    else if (n >= 2) {
      var a = t.pontos[0], b = t.pontos[n - 1];
      pontos = p >= 1 ? t.pontos.slice() : [a, [a[0] + (b[0] - a[0]) * p, a[1] + (b[1] - a[1]) * p]];
    } else pontos = t.pontos.slice();
    return pontos;
  }

  function estadoNoTempo(estado, t, centro) {
    var lt = linhaDoTempo(estado), n = estado.passos.length;
    t = Math.max(0, Math.min(lt.total, t));
    var k = 0;
    while (k < n - 1 && t > lt.inicios[k] + estado.passos[k].duracao_s) k++;
    var dur = estado.passos[k].duracao_s;
    var u = dur > 0 ? entre((t - lt.inicios[k]) / dur) : 1;
    var qk = quadroDoPasso(estado, k, centro), qp = k > 0 ? quadroDoPasso(estado, k - 1, centro) : qk;
    var e = suave(u);

    var pecas = {};
    Object.keys(Object.assign({}, qp.pecas, qk.pecas)).forEach(function (id) {
      var a = qp.pecas[id], b = qk.pecas[id], p;
      if (a && b) {
        if (e >= 1) p = Object.assign({}, b);
        else if (e <= 0) p = Object.assign({}, a);
        else if (a.nivel !== b.nivel) p = Object.assign({}, u < 0.5 ? a : b);   // troca de andar não interpola
        else {
          p = Object.assign({}, b, { x: a.x + (b.x - a.x) * e, y: a.y + (b.y - a.y) * e,
                                     yaw: MapCore.interpolaAngulo(a.yaw, b.yaw, e) });
        }
        p.alfa = 1;
      } else if (b) { p = Object.assign({}, b, { alfa: e }); }        // entra aos poucos
      else { p = Object.assign({}, a, { alfa: 1 - e }); }             // sai aos poucos
      if (p.alfa > 0) pecas[id] = p;
    });

    // o que nasce neste passo aparece em ordem de criação, repartindo o passo
    var nascem = ordemDeCriacao(estado).filter(function (x) {
      var grupo = x.tipo === "granada" ? qk.granadas : qk.tracos;
      return grupo[x.id] && grupo[x.id].nasceu_neste_passo;
    });
    var janela = {};
    nascem.forEach(function (x, j) { janela[x.id] = entre((u - j / nascem.length) * nascem.length); });

    var granadas = {}, tracos = {};
    Object.keys(qk.granadas).forEach(function (id) {
      var g = qk.granadas[id];
      if (g.nasceu_neste_passo) {
        var p = janela[id];
        if (p <= 0) return;
        // sem origem conhecida não há linha: a janela inteira abre o efeito
        granadas[id] = g.origem_desconhecida
          ? Object.assign({}, g, { linha: 0, efeito: p, alfa: 1 })
          : Object.assign({}, g, { linha: entre(p / FRACAO_LINHA),
              efeito: entre((p - FRACAO_LINHA) / (1 - FRACAO_LINHA)), alfa: 1 });
      } else granadas[id] = Object.assign({}, g, { linha: 0, efeito: 1, alfa: 1 });
    });
    Object.keys(qk.tracos).forEach(function (id) {
      var tr = qk.tracos[id];
      if (tr.nasceu_neste_passo) {
        var p = janela[id];
        if (p <= 0) return;
        tracos[id] = Object.assign({}, tr, { pontos: tracoParcial(tr, p), progresso: p, alfa: 1 });
      } else tracos[id] = Object.assign({}, tr, { progresso: 1, alfa: 1 });
    });
    // o que acabou de viver some no começo do passo
    var saida = 1 - entre(u / FRACAO_SAIDA);
    if (k > 0 && saida > 0) {
      Object.keys(qp.granadas).forEach(function (id) {
        if (!qk.granadas[id]) granadas[id] = Object.assign({}, qp.granadas[id], { linha: 0, efeito: 1, alfa: saida });
      });
      Object.keys(qp.tracos).forEach(function (id) {
        if (!qk.tracos[id]) tracos[id] = Object.assign({}, qp.tracos[id], { progresso: 1, alfa: saida });
      });
    }
    return { t: t, total: lt.total, indice: k, u: u, passo: qk.passo, titulo: qk.titulo,
             pecas: pecas, granadas: granadas, tracos: tracos };
  }


