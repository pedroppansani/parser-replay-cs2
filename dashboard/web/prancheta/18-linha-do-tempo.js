  /* ---------------------------------------------------------------------
     Linha do tempo, relógio grande e roteiro (fase 8, item 8.5)
     A linha do tempo embaixo do mapa mostra a tática no relógio do round: a
     régua (1:55 descendo; depois do plant, os 40 s da bomba), o cabeçote, os
     marcos (passos) e uma faixa por jogador com os pontos-chave e as granadas.
     Arrastar uma marca muda o horário dela numa ação só (um desfazer). O
     roteiro é a lista dos eventos da tática em ordem de horário, com o nome do
     lugar quando a tabela do mapa sabe (data/lugares, metrics/lugares.py).
     --------------------------------------------------------------------- */
  var LUGARES = null;   // preenchido no init com cfg.lugares (ou null: sem nome)
  var TEXTOS = {};      // frases de interface que vêm do Python (build_tactics_page.TEXTOS_DA_PRANCHETA)

  /** O nome do lugar no ponto (unidades do jogo), ou null. Espelho de
      metrics/lugares.lugar. */
  function lugarDe(x, y, nivel) {
    if (!LUGARES || !(nivel < LUGARES.andares.length)) return null;
    var px = jogoParaPixel(x, y), lado = LUGARES.lado;
    var cx = Math.floor(px[0] / lado), cy = Math.floor(px[1] / lado);
    var rle = LUGARES.andares[nivel][String(cy)];
    if (!rle) return null;
    for (var i = 0; i < rle.length; i += 3) if (rle[i] <= cx && cx < rle[i] + rle[i + 2]) return LUGARES.nomes[rle[i + 1]];
    return null;
  }

  /** A tática tem horário (alguma operação do formato 3, ou granada com `t`):
      toca no relógio do round. A que só tem passos -- toda tática das versões 1
      e 2, que a migração sobe de versão sem mudar nada -- continua tocando
      passo a passo, como sempre: o significado das operações dela não muda. */
  function tocaNoRelogio() {
    if (!(M3 && S.e3 && S.doc)) return false;
    var fora = anuladas(S.doc.operacoes);
    return S.doc.operacoes.some(function (op) {
      return !fora[op.id] && (OPERACOES_DO_FORMATO_3.indexOf(op.tipo) >= 0 || (op.tipo === "cria_granada" && tem(op, "t")));
    });
  }

  function plantDe(e3) { return e3 && e3.bomba ? e3.bomba.t : null; }
  function relogioEm(t) { return MapCore.relogio(t, plantDe(S.e3), null, M3.SEGUNDOS_DO_ROUND, M3.SEGUNDOS_DA_BOMBA); }

  /** Quanto cada ponto-chave chega ATRASADO (decisão 35 + 44): CALCULADO do log, nunca guardado.
      O jogador sai do ponto anterior e anda na velocidade medida da função dele (no modo do
      ponto); se o horário do ponto vem antes disso, atraso = chegada possível - t do ponto.
      Só conta atraso de pelo menos LIMIAR_ATRASO_S. Pontos do round real são fato, não
      plano: não ganham aviso. Devolve { idDoPonto: segundos }. */
  var LIMIAR_ATRASO_S = 0.05;
  function atrasosDosPontos(e3, doc) {
    var res = {};
    if (!e3) return res;
    var base = doc && doc.origem && ehInteiro(doc.origem.base_real) ? doc.origem.base_real : 0, real = {};
    if (base) (doc.operacoes || []).forEach(function (o) { if (o.seq <= base) real[o.id] = true; });
    Object.keys(e3.pecas).forEach(function (pid) {
      var p = e3.pecas[pid];
      p.pontos.forEach(function (pt, i) {
        var ant = i > 0 ? p.pontos[i - 1] : null;
        if (!ant || pt.fora || ant.fora || real[pt.id.split(":")[0]]) return;
        var chega = ant.t + Math.hypot(pt.x - ant.x, pt.y - ant.y) / velocidade(p.funcao, pt.modo);
        if (chega - pt.t >= LIMIAR_ATRASO_S) res[pt.id] = chega - pt.t;
      });
    });
    return res;
  }
  /** "2,3" (um decimal, vírgula) para o texto do atraso. */
  function segundosEmTexto(s) { return (Math.round(s * 10) / 10).toFixed(1).replace(".", ","); }

  /** Os eventos da tática, em ordem de horário: cada ponto-chave de cada peça,
      cada granada, o plant e cada marco. `alvo` é a chave da nota de evento
      (nota_de_evento): "<peça>/<ponto>", "<granada>", "bomba" ou "marco:<passo>". */
  function eventosDe(e3) {
    var ev = [];
    if (!e3) return ev;
    var atrasos = atrasosDosPontos(e3, S.doc);
    e3.marcos.forEach(function (m, k) {
      ev.push({ alvo: "marco:" + m.passo, tipo: "marco", ordem: 0, t: m.t, x: null, y: null, nivel: 0,
                texto: "Passo " + (k + 1) + (m.titulo ? " · " + m.titulo : "") });
    });
    Object.keys(e3.pecas).forEach(function (pid) {
      var p = e3.pecas[pid], nome = rotuloDaPeca(p);
      p.pontos.forEach(function (pt, i) {
        if (pt.fora) return;
        var lugar = lugarDe(pt.x, pt.y, pt.nivel);
        var acao = i === 0 || p.pontos[i - 1].fora ? "começa" : "chega";
        ev.push({ alvo: pid + "/" + pt.id, tipo: "ponto", peca: pid, ponto: pt.id, ordem: 1, t: pt.t,
                  x: pt.x, y: pt.y, nivel: pt.nivel,
                  texto: nome + (p.funcao ? " (" + p.funcao + ")" : "") + " " + acao + (lugar ? " em " + lugar : "") +
                         (tem(atrasos, pt.id) ? " (" + segundosEmTexto(atrasos[pt.id]) + " s atrasado)" : "") });
      });
    });
    Object.keys(e3.granadas).forEach(function (gid) {
      var g = e3.granadas[gid], quem = g.jogador && e3.pecas[g.jogador] ? rotuloDaPeca(e3.pecas[g.jogador]) : null;
      var lugar = lugarDe(g.destino[0], g.destino[1], g.nivel);
      ev.push({ alvo: gid, tipo: "granada", granada: gid, ordem: 2, t: g.t, x: g.destino[0], y: g.destino[1], nivel: g.nivel,
                texto: (quem ? quem + " joga " : "") + NOME_ARMA[g.arma] + (lugar ? " em " + lugar : "") });
    });
    if (e3.bomba) {
      var lb = lugarDe(e3.bomba.x, e3.bomba.y, e3.bomba.nivel);
      ev.push({ alvo: "bomba", tipo: "bomba", ordem: 3, t: e3.bomba.t, x: e3.bomba.x, y: e3.bomba.y, nivel: e3.bomba.nivel,
                texto: "Bomba plantada" + (lb ? " em " + lb : "") });
    }
    ev.forEach(function (e) { e.nota = tem(e3.notas, e.alvo) ? e3.notas[e.alvo] : ""; });
    ev.sort(function (a, b) { return a.t - b.t || a.ordem - b.ordem || (a.alvo < b.alvo ? -1 : a.alvo > b.alvo ? 1 : 0); });
    return ev;
  }

  /** O evento aceso em t: o último que já aconteceu. */
  function eventoEm(eventos, t) {
    var atual = null;
    eventos.forEach(function (e) { if (e.t <= t + EPS_T) atual = e; });
    return atual;
  }

  /** O fim da tática no relógio: o último horário em que algo acontece ou
      termina (ponto-chave, granada com voo e efeito, plant, marcos). */
  function fimDaTatica(e3) {
    var fim = e3.duracao_s;
    Object.keys(e3.pecas).forEach(function (pid) {
      e3.pecas[pid].pontos.forEach(function (pt) { fim = Math.max(fim, pt.t); });
    });
    Object.keys(e3.granadas).forEach(function (gid) {
      var g = e3.granadas[gid];
      fim = Math.max(fim, g.t + g.voo_s + g.efeito_s);
    });
    if (e3.bomba) fim = Math.max(fim, e3.bomba.t);
    return Math.min(fim, e3.bomba ? e3.bomba.t + M3.SEGUNDOS_DA_BOMBA : M3.SEGUNDOS_DO_ROUND);
  }

  /** A cena da reprodução no relógio: o quadro do formato 3 em t, no formato
      que o desenho usa. A granada voa no tempo de voo (a linha cresce até o
      destino), abre o efeito pela duração real e o arremessador vira para o
      ângulo do arremesso (do arremesso real; sem ele, para o destino) do
      instante em que joga até a granada cair. */
  function cenaNoRelogio(t) {
    var f = quadroNoTempo(S.e3, t, CENTRO), c = { pecas: {}, granadas: {}, tracos: {}, total: fimDaTatica(S.e3),
      indice: marcoQueContem(t), relogio: f.relogio, bomba: f.bomba, mortos: f.mortos };
    Object.keys(f.pecas).forEach(function (id) { c.pecas[id] = Object.assign({}, f.pecas[id], { alfa: 1 }); });
    Object.keys(f.granadas).forEach(function (id) {
      var g = f.granadas[id], voando = g.fase === "voo";
      c.granadas[id] = Object.assign({}, g, {
        linha: voando && !g.origem_desconhecida ? g.progresso : 0,
        efeito: voando ? 0 : 1, voando: voando, alfa: 1 });
      if (voando && g.jogador && c.pecas[g.jogador]) {
        var yaw = g.arremesso && ehNumero(g.arremesso.yaw) ? g.arremesso.yaw
          : (((Math.atan2(g.destino[1] - g.origem[1], g.destino[0] - g.origem[0]) * 180 / Math.PI) % 360) + 360) % 360;
        c.pecas[g.jogador].yaw = yaw;
        c.pecas[g.jogador].jogando = id;
      }
    });
    Object.keys(f.tracos).forEach(function (id) { c.tracos[id] = Object.assign({}, f.tracos[id], { progresso: 1, alfa: 1 }); });
    return c;
  }

  /** O horário que a linha do tempo, o relógio grande e o roteiro mostram. */
  function tempoMostrado() {
    if (S.reproducao) return S.reproducao.modo === "relogio" ? S.reproducao.t : null;
    return M3 ? S.t : null;
  }

  function atualizaRelogioGrande() {
    var r = $("pr-relogio-grande");
    if (!r) return;
    var t = tempoMostrado();
    r.hidden = t === null;
    if (t === null) return;
    r.textContent = relogioEm(t);
    r.classList.toggle("bomba", plantDe(S.e3) !== null && t >= plantDe(S.e3));
  }

  function pctDe(t, limite) { return (100 * Math.max(0, Math.min(1, t / limite))).toFixed(4) + "%"; }

  /** Monta a linha do tempo inteira a partir do estado (chamada a cada mudança). */
  function atualizaLinhaDoTempo() {
    var caixa = $("pr-linha");
    if (!caixa) return;
    var t = tempoMostrado(), antes = caixa.hidden ? 0 : caixa.offsetHeight;
    caixa.hidden = t === null || !S.e3;
    if (caixa.hidden) { if (antes) reprojeta(); return; }
    var e3 = S.e3, limite = limiteDoTempo(), plant = plantDe(e3);
    var regua = limpa($("pr-regua")), faixas = limpa($("pr-faixas"));
    // régua: um rótulo a cada 5 s de relógio (no relógio do jogo; convenção de
    // leitura, como as marcas de um cronômetro)
    for (var s = 0; s <= limite + EPS_T; s += 5) {
      regua.appendChild(el("span", { class: "pr-regua-marca" + (plant !== null && s >= plant ? " bomba" : ""),
        style: "left:" + pctDe(s, limite), texto: s % 15 === 0 ? relogioEm(s) : "" }));
    }
    if (plant !== null) {
      // a zona da bomba sombreada em --tr-area, do plant até o fim (§14)
      regua.insertBefore(el("span", { class: "pr-regua-zona", style: "left:" + pctDe(plant, limite) }), regua.firstChild);
      regua.appendChild(el("span", { class: "pr-regua-plant", style: "left:" + pctDe(plant, limite),
        title: "Bomba plantada · " + relogioEm(plant) }));
    }
    // marcos
    var marcos = el("div", { class: "pr-faixa pr-faixa-marcos" }, [el("span", { class: "pr-faixa-nome", texto: "Passos" })]);
    var trilho = el("div", { class: "pr-trilho" });
    e3.marcos.forEach(function (m, k) {
      trilho.appendChild(el("button", { class: "pr-marco" + (k === S.passo && !S.reproducao ? " ativo" : ""),
        "data-marco": m.passo, style: "left:" + pctDe(m.t, limite), title: relogioEm(m.t) + (m.titulo ? " · " + m.titulo : ""),
        "aria-label": "Passo " + (k + 1) + (m.titulo ? " · " + m.titulo : "") + ", " + relogioEm(m.t),
        texto: String(k + 1) }));
    });
    // marco nomeado (rótulo, não botão: pular para ele é pelo roteiro): losango + nome + horário, em cima do trilho
    if (plant !== null) trilho.appendChild(el("span", { class: "pr-marco-nomeado", style: "left:" + pctDe(plant, limite) }, [
      el("i", { class: "pr-losango", "aria-hidden": "true" }), el("span", { texto: "plant " + relogioEm(plant) })]));
    marcos.appendChild(trilho);
    faixas.appendChild(marcos);
    // uma faixa por jogador, na ordem do banco (lado, rótulo)
    var porJogador = {};
    Object.keys(e3.granadas).forEach(function (gid) {
      var j = e3.granadas[gid].jogador || "";
      (porJogador[j] = porJogador[j] || []).push(gid);
    });
    var ids = Object.keys(e3.pecas).sort(function (a, b) {
      var pa = e3.pecas[a], pb = e3.pecas[b];
      return pa.lado.localeCompare(pb.lado) || rotuloDaPeca(pa).localeCompare(rotuloDaPeca(pb));
    });
    var atrasos = atrasosDosPontos(e3, S.doc);
    var linhas = ids.map(function (pid) { return [pid, rotuloDaPeca(e3.pecas[pid]), e3.pecas[pid].lado]; });
    if (porJogador[""]) linhas.push(["", "Sem jogador", ""]);
    // sem jogador nenhum, o lugar reservado da primeira faixa diz o que vai aparecer ali (v2-5b)
    if (!linhas.length && TEXTOS.linha_vazia) faixas.appendChild(el("p", { class: "pr-faixas-vazio", texto: TEXTOS.linha_vazia }));
    linhas.forEach(function (l) {
      var pid = l[0], funcao = pid && e3.pecas[pid].funcao ? e3.pecas[pid].funcao : "";
      var faixa = el("div", { class: "pr-faixa pr-faixa-jogador", "data-faixa": pid },
        [el("span", { class: "pr-faixa-nome " + l[2], title: l[1] + (funcao ? " · " + funcao : "") }, [
          el("b", { texto: l[1] }), funcao ? el("small", { texto: funcao }) : null].filter(Boolean))]);
      var tr = el("div", { class: "pr-trilho" });
      if (pid) {
        // vida na cor do lado até a morte (✕); sem morte, até o fim
        var morreu = e3.pecas[pid].pontos.filter(function (pt) { return pt.morte; })[0];
        tr.appendChild(el("span", { class: "pr-vida " + l[2], style: "width:" + (morreu ? pctDe(morreu.t, limite) : "100%") }));
        if (morreu) tr.appendChild(el("span", { class: "pr-morte", style: "left:" + pctDe(morreu.t, limite), "aria-hidden": "true", texto: "✕" }));
      }
      if (pid) e3.pecas[pid].pontos.forEach(function (pt) {
        if (pt.fora) return;
        // atrasado: preenchido em --aviso, com "+2,3 s" ao lado e o mesmo dito em texto (nunca só cor)
        var atraso = tem(atrasos, pt.id) ? atrasos[pt.id] : null;
        var dito = atraso === null ? "" : ", chega " + segundosEmTexto(atraso) + " s atrasado";
        tr.appendChild(el("button", { class: "pr-marca " + l[2] + (atraso === null ? "" : " atrasado"), "data-peca": pid, "data-ponto": pt.id,
          style: "left:" + pctDe(pt.t, limite), title: l[1] + " · " + relogioEm(pt.t) + dito,
          "aria-label": l[1] + " " + relogioEm(pt.t) + dito }));
        if (atraso !== null) tr.appendChild(el("span", { class: "pr-atraso", "data-atraso-de": pt.id,
          style: "left:" + pctDe(pt.t, limite), "aria-hidden": "true", texto: "+" + segundosEmTexto(atraso) + " s" }));
      });
      (porJogador[pid] || []).forEach(function (gid) {
        var g = e3.granadas[gid];
        // duração listrada na cor da granada (smoke e molotov): do horário da soltura até o fim do efeito
        var dur = g.arma === "smoke" ? DURACAO_SMOKE_S : g.arma === "molotov" ? DURACAO_MOLOTOV_S : 0;
        if (dur) tr.appendChild(el("span", { class: "pr-duracao", style: "left:" + pctDe(g.t, limite) + ";width:" +
          (Math.min(dur, Math.max(0, limite - g.t)) / limite * 100) + "%;--cor:" + MapCore.NADE_COLOR[g.arma] }));
        var bg = el("button", { class: "pr-marca granada", "data-granada": gid, "data-arma": g.arma,
          style: "left:" + pctDe(g.t, limite) + ";--cor:" + MapCore.NADE_COLOR[g.arma],
          title: NOME_ARMA[g.arma] + " · " + relogioEm(g.t), "aria-label": NOME_ARMA[g.arma] + " " + relogioEm(g.t) });
        var cg = el("canvas", { width: "52", height: "52", class: "pr-marca-glifo", "aria-hidden": "true" });
        var gx = cg.getContext && cg.getContext("2d");
        if (gx) MapCore.nadeGlyph(gx, g.arma, 26, 26, 11, MapCore.NADE_COLOR[g.arma], 0);
        bg.appendChild(cg);
        tr.appendChild(bg);
      });
      faixa.appendChild(tr);
      faixas.appendChild(faixa);
    });
    atualizaReal();
    var cab = $("pr-linha-cabecote");
    cab.style.left = pctDe(t, limite);
    cab.setAttribute("data-relogio", relogioEm(t));
    // slider (§14): valor em segundos desde o começo do round e o relógio como texto
    cab.setAttribute("aria-valuemax", String(Math.round(limite * 100) / 100));
    cab.setAttribute("aria-valuenow", String(Math.round(t * 100) / 100));
    cab.setAttribute("aria-valuetext", relogioEm(t));
    atualizaRoteiro();
    // mudou a altura (apareceu, ganhou ou perdeu faixa): o mapa se ajusta
    if (caixa.offsetHeight !== antes) reprojeta();
  }

  function atualizaRoteiro() {
    var lista = $("pr-roteiro");
    if (!lista) return;
    var t = tempoMostrado();
    if (t === null || !S.e3) { limpa(lista); return; }
    var ev = eventosDe(S.e3), aceso = eventoEm(ev, t), editando = !S.reproducao;
    // a nota que está sendo digitada não é refeita embaixo do dedo
    var foco = document.activeElement && document.activeElement.getAttribute && document.activeElement.getAttribute("data-nota");
    if (foco && lista.contains(document.activeElement)) return;
    limpa(lista);
    ev.forEach(function (e) {
      var li = el("li", { class: "pr-evento" + (e === aceso ? " aceso" : ""), "data-evento": e.alvo }, [
        el("button", { class: "pr-evento-hora", texto: relogioEm(e.t), title: "Ir para " + relogioEm(e.t),
          onclick: function () { irPara(e.t); } }),
        el("span", { class: "pr-evento-texto", texto: e.texto })]);
      if (editando) {
        var nota = el("input", { type: "text", class: "pr-evento-nota", "data-nota": e.alvo, placeholder: "nota",
                                 "aria-label": "Nota: " + e.texto, maxlength: "140" });
        nota.value = e.nota;
        nota.addEventListener("change", function () {
          if ((nota.value || "") !== e.nota) emite("nota_de_evento", { alvo: e.alvo, texto: nota.value.trim() });
        });
        li.appendChild(nota);
      } else if (e.nota) li.appendChild(el("span", { class: "pr-evento-nota-texto", texto: e.nota }));
      lista.appendChild(li);
    });
    var vivo = lista.querySelector(".aceso");
    if (vivo && !editando && vivo.scrollIntoView) vivo.scrollIntoView({ block: "nearest" });
  }

  /** Leva o horário mostrado a t: no editor, o cabeçote; tocando, a reprodução. */
  function irPara(t) {
    if (S.reproducao) { if (S.reproducao.modo === "relogio") { toca(false); reproduzAte(t); } return; }
    defineTempo(t);
  }

  /** O balão do evento aceso, no mapa, durante a reprodução no relógio. */
  function desenhaBalao() {
    S.ultimoBalao = null;
    var r = S.reproducao;
    if (!r || r.modo !== "relogio") return;
    var e = eventoEm(eventosDe(S.e3), r.t);
    if (!e || e.x === null) return;
    var c = jogoParaPixel(e.x, e.y), texto = e.texto + (e.nota ? " — " + e.nota : "");
    ctx.save();
    ctx.font = "600 13px " + MapCore.token("f-texto");
    var w = ctx.measureText(texto).width + 16, h = 24, x = c[0] - w / 2, y = c[1] - RAIO_PECA - h - 10;
    ctx.globalAlpha = alfaDoAndar(e.nivel);
    ctx.fillStyle = MapCore.corComAlfa("contorno", 0.92); ctx.strokeStyle = MapCore.token("tinta-mapa"); ctx.lineWidth = 1;
    ctx.beginPath(); ctx.rect(x, y, w, h); ctx.fill(); ctx.stroke();
    ctx.beginPath(); ctx.moveTo(c[0] - 6, y + h); ctx.lineTo(c[0], y + h + 7); ctx.lineTo(c[0] + 6, y + h); ctx.fill();
    ctx.fillStyle = MapCore.token("tinta-mapa"); ctx.textAlign = "center"; ctx.textBaseline = "middle";
    ctx.fillText(texto, c[0], y + h / 2);
    ctx.restore();
    S.ultimoBalao = { alvo: e.alvo, texto: texto };
  }

  /* --- arrastar na linha do tempo ----------------------------------------- */
  function tempoDoPonteiro(e) {
    var tr = $("pr-linha").querySelector(".pr-trilho") || $("pr-regua");
    var r = tr.getBoundingClientRect();
    return Math.round(limiteDoTempo() * Math.max(0, Math.min(1, (e.clientX - r.left) / r.width)) * 100) / 100;
  }

  function linhaPointerDown(e) {
    if (e.button !== 0) return;
    if (e.target.closest && e.target.closest(".pr-real")) return;
    var alvo = e.target, editando = !S.reproducao;
    var marca = alvo.closest && alvo.closest(".pr-marca");
    var marco = alvo.closest && alvo.closest(".pr-marco");
    e.preventDefault();
    if (marca && editando) {
      S.arrastoLinha = { marca: marca, x0: e.clientX, moveu: false,
        peca: marca.getAttribute("data-peca"), ponto: marca.getAttribute("data-ponto"),
        granada: marca.getAttribute("data-granada") };
    } else if (marco && editando) {
      var k = S.e3.marcos.map(function (m) { return m.passo; }).indexOf(marco.getAttribute("data-marco"));
      if (k >= 0) defineTempo(S.e3.marcos[k].t);
      return;
    } else {
      S.arrastoLinha = { cabecote: true };
      irPara(tempoDoPonteiro(e));
    }
    if ($("pr-linha").setPointerCapture) { try { $("pr-linha").setPointerCapture(e.pointerId); } catch (_) {} }
  }

  function linhaPointerMove(e) {
    var a = S.arrastoLinha;
    if (!a) return;
    if (a.cabecote) { irPara(tempoDoPonteiro(e)); return; }
    if (!a.moveu && Math.abs(e.clientX - a.x0) < LIMIAR_ARRASTO_PX) return;
    a.moveu = true;
    a.t = tempoDoPonteiro(e);
    a.marca.style.left = pctDe(a.t, limiteDoTempo());
    a.marca.classList.add("arrastando");
    a.marca.setAttribute("data-relogio", relogioEm(a.t));
  }

  /** Solta a marca: o novo horário vira UMA ação (move_ponto para o ponto-chave;
      a troca da granada, em lote, para a granada). Sem arrastar, é um clique:
      o cabeçote vai até a marca. */
  function linhaPointerUp(e) {
    var a = S.arrastoLinha;
    S.arrastoLinha = null;
    if (!a || a.cabecote) return;
    if (!a.moveu) {
      var t0 = a.granada ? S.e3.granadas[a.granada].t
        : S.e3.pecas[a.peca].pontos.filter(function (pt) { return pt.id === a.ponto; })[0].t;
      defineTempo(t0);
      return;
    }
    var t = tempoDoPonteiro(e);
    if (a.granada) { mudaHorarioDaGranada(a.granada, t); return; }
    var pt = S.e3.pecas[a.peca].pontos.filter(function (x) { return x.id === a.ponto; })[0];
    if (!pt || Math.abs(pt.t - t) < EPS_T) { atualizaTudo(); return; }
    emite("move_ponto", { peca: a.peca, ponto: a.ponto, t: t, x: pt.x, y: pt.y, nivel: pt.nivel });
  }

  function montaLinhaDoTempo() {
    var linha = el("div", { id: "pr-linha", class: "pr-linha", role: "group", "aria-label": "Linha do tempo do round" }, [
      el("div", { class: "pr-linha-corpo" }, [
        el("div", { id: "pr-real", class: "pr-real", hidden: "" }, [
          el("button", { type: "button", id: "pr-fantasma", class: "pr-b", "aria-pressed": "false",
                         title: "Mostra, esmaecido, o que aconteceu de verdade neste round, junto da versão editada",
                         onclick: function () { alternaFantasma(); } }),
          el("button", { type: "button", id: "pr-volta-real", class: "pr-b", texto: "Voltar ao real",
                         title: "Desfaz todas as suas mudanças e volta ao round como aconteceu (uma ação: refazer devolve)",
                         onclick: function () { voltaAoReal(); } })]),
        el("div", { class: "pr-faixa pr-faixa-regua" }, [el("span", { class: "pr-faixa-nome", texto: "Relógio" }),
          el("div", { class: "pr-trilho pr-regua", id: "pr-regua" })]),
        el("div", { id: "pr-faixas" }),
        el("div", { class: "pr-linha-cabecote-trilho" }, [el("div", { id: "pr-linha-cabecote", class: "pr-linha-cabecote",
          role: "slider", tabindex: "0", "aria-label": "Horário do round", "aria-valuemin": "0" }, [
          el("span", { class: "pr-cabecote-alca", "aria-hidden": "true" })])])]),
      el("ol", { id: "pr-roteiro", class: "pr-roteiro", "aria-label": "Roteiro da tática" })]);
    linha.hidden = true;
    // teclado no cabeçote: setas (1 s; com Shift, 5 s), Home e End
    linha.querySelector("#pr-linha-cabecote").addEventListener("keydown", function (e) {
      var t = tempoMostrado(), passo = e.shiftKey ? 5 : 1, novo = null;
      if (t === null) return;
      if (e.key === "ArrowRight" || e.key === "ArrowUp") novo = t + passo;
      else if (e.key === "ArrowLeft" || e.key === "ArrowDown") novo = t - passo;
      else if (e.key === "Home") novo = 0;
      else if (e.key === "End") novo = limiteDoTempo();
      if (novo === null) return;
      e.preventDefault(); e.stopPropagation();
      irPara(Math.max(0, Math.min(limiteDoTempo(), novo)));
    });
    linha.addEventListener("pointerdown", function (e) {
      if (e.target.closest && e.target.closest(".pr-roteiro")) return;
      linhaPointerDown(e);
    });
    linha.addEventListener("pointermove", linhaPointerMove);
    linha.addEventListener("pointerup", linhaPointerUp);
    linha.addEventListener("pointercancel", function () { S.arrastoLinha = null; atualizaLinhaDoTempo(); });
    $("pr-palco").appendChild(linha);
    $("pr-tela").appendChild(el("div", { id: "pr-relogio-grande", class: "pr-relogio-grande", role: "timer",
                                         "aria-label": "Relógio do round", hidden: "" }));
  }

