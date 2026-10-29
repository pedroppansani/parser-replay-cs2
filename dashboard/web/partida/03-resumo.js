  /* ================= INSIGHTS ================= */

  function pct(v) { return Math.round(v * 100) + "%"; }

  // --- Card do round decisivo -------------------------------------------
  // As frases vêm prontas de leitura/narrativa.py (decisão 18): o template só
  // imprime. Inclusive a frase do caso "não houve round decisivo", que não é
  // fallback nem erro -- é o resultado de uma partida de placar largo.
  var dr = D.decisive_round;
  var econ = D.narrative.economy ? "<div class='econ'>" + esc(D.narrative.economy) + "</div>" : "";
  document.getElementById("decisive").innerHTML = dr
    ? "<div class='stamp'><div class='k'>Round decisivo</div><div class='n'>" + esc(dr.round) + "</div>" +
      "<div class='s'>placar " + esc(dr.score_a) + "–" + esc(dr.score_b) + " · " + esc(nomeLado(dr.winner_team)) + "</div></div>" +
      "<div class='story'><p class='t'>" + esc(D.narrative.decisive) + "</p>" +
      barraWp(dr) + econ +
      "<p class='lead tight' style='margin-top:14px'>" + esc(D.narrative.criterion) + "</p></div>"
    : "<div class='stamp'><div class='k'>Round decisivo</div>" +
      "<div class='n' style='font-size:44px'>—</div>" +
      "<div class='s'>nenhum round passou do mínimo</div></div>" +
      "<div class='story'><p class='t'>" + esc(D.narrative.decisive) + "</p>" +
      "<p class='lead tight' style='margin-top:14px'>" + esc(D.narrative.criterion) + "</p></div>";

  function barraWp(d) {
    // Duas barras sobrepostas: a clara é onde o time estava, a laranja onde
    // ficou. O salto entre as duas É a decisividade do round.
    var a = d.wp_vencedor_antes, b = d.wp_vencedor_depois;
    return "<div class='wpbar'><div class='row'><span>" + pct(a) + "</span>" +
      "<span class='track'><i class='was' style='left:0;width:" + (a * 100) + "%'></i>" +
      "<i class='now' style='left:0;width:" + (b * 100) + "%;opacity:.82'></i></span>" +
      "<span>" + pct(b) + "</span></div>" +
      "<div class='cap'>chance de " + esc(nomeLado(d.winner_team)) + " vencer a partida, antes e depois deste round</div></div>";
  }

  // --- Card do round mais impressionante --------------------------------
  // Pergunta separada, card separado. Os componentes aparecem com a pontuação
  // de cada um justamente para dar pra recalibrar olhando o caso concreto.
  var sp = D.spectacle_round;
  document.getElementById("spectacle").innerHTML = sp
    ? "<div class='eyebrow'>Round mais impressionante</div>" +
      "<h3 style='margin:6px 0 0'>Round " + esc(sp.round) + "</h3>" +
      "<p style='margin-top:10px'>" + esc(D.narrative.spectacle) + "</p>" +
      "<div class='comps'>" + sp.componentes.map(function (c) {
        return "<div class='comp'><b>" + Math.round(c.pontos) + "</b><span>" + esc(c.texto) + "</span></div>";
      }).join("") + "</div>"
    : "<div class='eyebrow'>Round mais impressionante</div>" +
      "<p style='margin-top:10px'>Nenhum round desta partida teve clutch, multikill, virada em " +
      "desvantagem ou desarme no limite. Foi uma partida decidida no jogo padrão.</p>";

  function ring(pct, color, rotulo) {
    var r = 26, c = 2 * Math.PI * r;
    return "<svg width='68' height='68' viewBox='0 0 68 68' aria-hidden='true'>" +
      "<circle cx='34' cy='34' r='" + r + "' fill='none' stroke='" + C.linha + "' stroke-width='5'></circle>" +
      "<circle cx='34' cy='34' r='" + r + "' fill='none' stroke='" + color + "' stroke-width='5' " +
      "stroke-linecap='round' stroke-dasharray='" + (c * pct) + " " + c + "' transform='rotate(-90 34 34)'></circle>" +
      "<text x='34' y='39' text-anchor='middle' fill='" + C.tinta + "' font-family='" + C.fNum + "' " +
      "font-size='15' font-weight='500'>" + (rotulo != null ? esc(rotulo) : Math.round(pct * 100)) + "</text></svg>";
  }
  // --- Card da esquerda: MVP --------------------------------------------
  // Os COMPONENTES aparecem, não só o índice: quem lê tem que ver se ele venceu
  // por ADR, por abertura ou por clutch, e quanto foi acima do segundo. Escolha
  // e frases vêm de metrics/match_highlights.py + leitura/narrativa.py.
  var mvpc = D.mvp_card;

  function componentes(lista) {
    return "<div class='comp-list'>" + lista.map(function (c) {
      var teto = Math.max(c.valor || 0, c.melhor_dos_outros || 0) || 1;
      var ref = (c.melhor_dos_outros || 0) / teto * 100;
      return "<div class='cmp" + (c.lidera ? " win" : "") + "'>" +
        "<div class='k'>" + esc(c.rotulo) + "</div>" +
        "<div class='bar'><i style='width:" + Math.max(3, (c.valor || 0) / teto * 100) + "%;" +
        "background:" + (c.lidera ? C.ct : C.apagado) + "'></i>" +
        "<span class='ref' style='left:" + ref + "%'></span></div>" +
        "<div class='v'>" + esc(c.texto) +
        (c.melhor_dos_outros_texto ? " <em>/ " + esc(c.melhor_dos_outros_texto) + "</em>" : "") +
        "</div></div>";
    }).join("") + "</div>";
  }

  // Rating em modo degradado (economia estimada só nesta partida etc.): o card não mostra número nenhum, só o
  // rótulo e o motivo, que vêm prontos do Python (D.rating_info.texto_degradado).
  var mvpDegradado = ((D.rating_info || {}).modo_degradado || []).length > 0;
  function ratingDoMvp(c) {
    // o erro típico vem de numeros_citaveis.json pelo build (PAGINA.erro_rating); nunca escrito aqui
    return "<div class='rating-mvp'><span class='rt-num'>" + esc(c.rating_texto) + "</span>" +
      (PAGINA.erro_rating ? "<span class='rt-erro'>erro típico contra o rating oficial: <span class='num'>" +
        esc(PAGINA.erro_rating) + "</span> · <a href='" + esc(PAGINA.metodo_rating || "#") + "'>método</a></span>" : "") +
      "</div>";
  }
  function viceDoMvp(c) {
    if (!c.vice_nome) return "";
    var menor = PAGINA.vice_dentro_do_erro === true;     // decidido no build (scripts/build_web_page.py)
    return "<p class='vice'>2º maior rating: <b>" + esc(c.vice_nome) + "</b>, <span class='num'>" + esc(c.vice_rating_texto) +
      "</span>" + (menor ? " — a diferença é menor que o erro típico" : "") + "</p>";
  }
  var cabMvp = mvpc ? "<div><div class='role'>MVP da partida</div>" +
      "<div class='nm'>" + esc(mvpc.name) + "</div>" +
      "<div class='sub'>" + esc(nomeLado(mvpc.team)) +
      (mvpc.funcao ? " · " + esc(mvpc.funcao) : "") + "</div></div>" : "";
  document.getElementById("fig-mvp").innerHTML = mvpc && mvpDegradado
    ? "<div class='hd'>" + cabMvp + "</div>" +
      "<p class='degradado'><span class='tag aviso'>▲ degradado</span><span>" + esc((D.rating_info || {}).texto_degradado || "") + "</span></p>"
    : mvpc
    ? "<div class='hd'>" + cabMvp + ratingDoMvp(mvpc) + "</div>" + viceDoMvp(mvpc) +
      "<p>" + esc(D.narrative.mvp_card) + "</p>" +
      componentes(mvpc.componentes)
    : "<div class='hd'><div><div class='role'>MVP da partida</div>" +
      "<div class='nm'>sem dados</div></div></div>";

  // --- Card da direita: o outro destaque ---------------------------------
  // Pode ser positivo OU negativo, e nunca é o MVP. Todo card negativo mostra o
  // número que o sustenta e a referência com que foi comparado -- sem os dois,
  // metrics/match_highlights.py já descarta o candidato antes de chegar aqui.
  var dst = D.highlight_card;
  var alvo = document.getElementById("fig-destaque");
  if (!dst) {
    alvo.innerHTML =
      "<div class='hd'><div><div class='role'>Outro destaque</div>" +
      "<div class='nm'>sem destaque</div></div></div>" +
      "<p class='lead tight'>Nenhuma função desta partida se afastou do normal o " +
      "bastante para virar destaque. Preferimos dizer isso a eleger um jogador mediano.</p>";
  } else {
    var ev = dst.evidencia || {};
    var linhaEv = "";
    if (ev.valor) {
      linhaEv = "<div class='evid'><b>" + esc(ev.valor) + "</b> " + esc(ev.metrica) +
        (ev.referencia
          ? " · contra <b>" + esc(ev.referencia) + "</b> " +
            (ev.referencia_nome ? "de " + esc(ev.referencia_nome) : esc(ev.referencia_rotulo || ""))
          : "") + "</div>";
    }
    alvo.innerHTML =
      "<div class='hd'><div>" +
      (dst.negativo ? "<div class='tagneg'>destaque negativo</div>" : "") +
      "<div class='role'>" + esc(dst.label) + "</div>" +
      "<div class='nm'>" + esc(dst.name) + "</div>" +
      "<div class='sub'>" + (dst.team ? esc(nomeLado(dst.team)) + " · " : "") + esc(dst.meaning) + "</div>" +
      "</div>" + ring(dst.index, dst.negativo ? C.tinta2 : C.decisivo) + "</div>" +
      "<p>" + esc(D.narrative.highlight_card) + "</p>" + linhaEv;
  }

