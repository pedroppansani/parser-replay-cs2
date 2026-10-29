  /* ================= REPLAY ================= */

  var cv = document.getElementById("map");
  var ctx = cv.getContext("2d");

  // Radar oficial do mapa. A correspondência entre coordenada de jogo e pixel
  // não vem com a imagem — ela foi calibrada ajustando a nuvem de posições da
  // partida contra a área caminhável do radar (ver scripts/prepare_radar.py).
  //
  // Nem todo mapa tem radar calibrado (os assets do awpy exigem rede liberada, e
  // o CDN nem sempre responde). Sem ele, a projeção é derivada dos próprios
  // limites da partida: o mapa fica sem imagem de fundo, mas posição, trajetória
  // e evento continuam corretos entre si — que é o que o replay precisa mostrar.
  // A alternativa seria a aba inteira quebrar em mapa sem asset.
  function fitBounds(b) {
    var W = 820, H = 950, pad = 40;
    var dx = Math.max(1, b.maxX - b.minX), dy = Math.max(1, b.maxY - b.minY);
    var scale = Math.min((W - pad * 2) / dx, (H - pad * 2) / dy);
    return {
      width: W,
      height: H,
      scale_px_per_unit: scale,
      // centraliza a nuvem de posições na área útil do canvas
      origin_x: b.minX - ((W - dx * scale) / 2) / scale,
      origin_y: b.maxY + ((H - dy * scale) / 2) / scale,
      image: null,
      synthetic: true
    };
  }

  var RAD = window.__RADAR__ || fitBounds(R.bounds);
  cv.width = RAD.width;
  cv.height = RAD.height;

  function mx(x) { return (x - RAD.origin_x) * RAD.scale_px_per_unit; }
  function my(y) { return (RAD.origin_y - y) * RAD.scale_px_per_unit; }

  // Um fundo por andar do mapa. Na Nuke o A fica em cima do B, e a Valve
  // distribui um radar separado pro nível de baixo justamente porque, num mapa
  // 2D, os dois sites se sobrepõem. As faixas de altura vêm do overview oficial
  // (ver scripts/extract_radars.py).
  var LEVELS = (R.levels && R.levels.length) ? R.levels : [{ name: "default" }];
  var plates = [];
  var plateReady = false;

  (function loadRadars() {
    var pending = 0;
    LEVELS.forEach(function (lv, i) {
      var c = document.createElement("canvas");
      c.width = cv.width; c.height = cv.height;
      var p = c.getContext("2d");
      p.fillStyle = C.radar;
      p.fillRect(0, 0, c.width, c.height);
      plates[i] = c;

      var src = lv.name === "default" ? RAD.image : (RAD.layers || {})[lv.name];
      if (!src) return;
      pending++;
      var im = new Image();
      im.onload = function () {
        p.drawImage(MapCore.radarProcessado(im, RAD.map), 0, 0, c.width, c.height);   // dessaturado por mapa (§4.1)
        if (--pending === 0) { plateReady = true; draw(); }
      };
      im.src = src;
    });
    if (pending === 0) plateReady = true;
  })();

  // Andar mostrado: segue onde está a maioria dos vivos, e o usuário pode
  // travar num andar específico.
  var levelLock = null;

  function activeLevel(f) {
    if (levelLock !== null) return levelLock;
    if (LEVELS.length < 2) return 0;
    var count = [];
    cur.players.forEach(function (p) {
      if (!p.alive[f] || !p.lv) return;
      var l = p.lv[f];
      count[l] = (count[l] || 0) + 1;
    });
    var best = 0;
    for (var i = 1; i < LEVELS.length; i++) {
      if ((count[i] || 0) > (count[best] || 0)) best = i;
    }
    return best;
  }

  if (RAD.synthetic) {
    var leg = document.querySelector(".maplegend");
    if (leg) {
      var warn = document.createElement("span");
      warn.style.cssText = "color:var(--apagado);font-style:italic";
      warn.textContent = "sem radar calibrado para este mapa — posições em coordenadas de jogo";
      leg.appendChild(warn);
    }
  }

  // Controle de andar: só aparece em mapa que tem mais de um (Nuke, Vertigo,
  // Train). "Auto" segue a maioria dos vivos, que é como o observador do jogo
  // se comporta; travar serve pra acompanhar o que acontece no outro andar.
  if (LEVELS.length > 1) {
    var lg = document.querySelector(".maplegend");
    if (lg) {
      var box = document.createElement("span");
      box.className = "levelpick";
      var opts = [["auto", "auto"]].concat(LEVELS.map(function (lv, i) {
        return [String(i), lv.name === "default" ? "superior" : "inferior"];
      }));
      box.innerHTML = "<b>andar</b>" + opts.map(function (o) {
        return "<button type='button' data-lv='" + o[0] + "'" +
          (o[0] === "auto" ? " class='on'" : "") + ">" + o[1] + "</button>";
      }).join("");
      lg.appendChild(box);

      box.addEventListener("click", function (e) {
        var b = e.target.closest("button");
        if (!b) return;
        levelLock = b.dataset.lv === "auto" ? null : Number(b.dataset.lv);
        Array.prototype.forEach.call(box.querySelectorAll("button"), function (o) {
          o.classList.toggle("on", o === b);
        });
        draw();
      });
    }
  }

  var NADE_COLOR = MapCore.NADE_COLOR;

  // Quadros que a marca de detonação leva pra abrir e sumir (4 Hz -> 1,5s).
  var POP_FRAMES = 6;
  // Quanto a marca do ponto de queda ainda fica visível depois do voo acabar.
  var LANDING_HOLD = 8;
  // Estouro (POP_FRAMES) + cicatriz, que fica depois pra você achar o lugar.
  var POP_TOTAL = POP_FRAMES + 12;

  // Símbolo de cada tipo de granada: vive em map_core.js, que a prancheta
  // também usa.
  var nadeGlyph = MapCore.nadeGlyph;
  // anel duplo em peça e glifo (entrega-sala-de-demo §4.1): o replay liga na design-B2
  MapCore.defineAnelDuplo(true);

  var rounds = R.rounds;
  var cur = rounds[0];
  var frame = 0;
  var pos = 0;
  var playing = false;
  var speed = 1;
  var lastT = 0;

  // Round decisivo, ou null quando a partida não teve um.
  var decRound = D.decisive_round ? D.decisive_round.round : null;

  var strip = document.getElementById("strip");
  rounds.forEach(function (r) {
    var b = document.createElement("button");
    b.className = "rchip" + (r.round === decRound ? " key" : "");
    b.textContent = r.round;
    b.dataset.w = r.winner_team;
    b.dataset.round = r.round;
    b.setAttribute("aria-pressed", String(r === cur));
    b.title = "Round " + r.round + " — " + nomeLado(r.winner_team);
    b.setAttribute("aria-label", "Round " + r.round + ", " + nomeLado(r.winner_team) + " venceu" +
                   (r.round === decRound ? ", round decisivo" : ""));
    b.addEventListener("click", function () { selectRound(r); });
    strip.appendChild(b);
    // separador no fim de cada meio-tempo (12, 24) e de cada metade da prorrogação (MR3: 27, 30, ...)
    var meio = M.halftime || 12, n = r.round;
    if (r !== rounds[rounds.length - 1] && (n === meio || n === 2 * meio || (n > 2 * meio && (n - 2 * meio) % 3 === 0))) {
      var s = document.createElement("span");
      s.className = "meio-tempo";
      s.setAttribute("aria-hidden", "true");
      strip.appendChild(s);
    }
  });

  // Legenda com os glifos REAIS: cada um desenhado pela mesma função do mapa (MapCore), num canvas pequeno.
  (function legenda() {
    var caixa = document.getElementById("maplegend");
    var ITENS = [["peca", CM.ct, "CT"], ["peca", CM.tr, "TR"], ["smoke", null, "Smoke"], ["flash", null, "Flash"],
                 ["he", null, "HE"], ["molotov", null, "Molotov"], ["morto", CM.apagado, "morto"],
                 ["desenhada", null, "granada desenhada"]];
    var dpr = window.devicePixelRatio || 1;
    ITENS.forEach(function (it) {
      var s = document.createElement("span"), c = document.createElement("canvas");
      // a granada desenhada leva o carimbo no canto superior direito: o canvas dela é maior (28 x 22 px de tela)
      var larg = it[0] === "desenhada" ? 28 : 18, alt = it[0] === "desenhada" ? 22 : 18;
      c.width = Math.round(larg * dpr); c.height = Math.round(alt * dpr);
      c.style.width = larg + "px"; c.style.height = alt + "px";
      c.setAttribute("aria-hidden", "true");
      var g = c.getContext("2d");
      g.scale(dpr, dpr);
      if (it[0] === "peca") MapCore.desenhaJogador(g, 9, 9, { cor: it[1], estado: "vivo", hp: 100, nome: "" });
      else if (it[0] === "morto") MapCore.desenhaJogador(g, 9, 9, { cor: CM.tinta2, estado: "morto", hp: 0, nome: "" });
      // a granada desenhada (fase 11, V3 da fase 15): o mesmo glifo, com o anel tracejado, o corpo a 100% e o carimbo
      else if (it[0] === "desenhada") MapCore.nadeGlyph(g, "smoke", 9, 13, 4, MapCore.NADE_COLOR.smoke, -Math.PI / 2, true);
      else MapCore.nadeGlyph(g, it[0], 9, 9, 4, MapCore.NADE_COLOR[it[0]], -Math.PI / 2);
      s.appendChild(c);
      s.appendChild(document.createTextNode(it[2]));
      caixa.appendChild(s);
    });
  })();

  var REASON = {
    t_killed: "todos os T eliminados",
    ct_killed: "todos os CT eliminados",
    bomb_defused: "bomba desarmada",
    bomb_exploded: "bomba explodiu",
    target_bombed: "bomba explodiu",
    time_ran_out: "tempo esgotado"
  };

  // Janelas de cegueira do round indexadas por jogador. O mapa precisa
  // responder "esse jogador está cego AGORA?" a cada quadro, e varrer a lista
  // inteira 10 vezes por quadro seria desperdício.
  var blindIndex = {};
  var logItems = [];

  function indexBlinds(r) {
    blindIndex = {};
    (r.blinds || []).forEach(function (b) {
      (blindIndex[b.n] = blindIndex[b.n] || []).push(b);
    });
  }

  // Ao clicar num evento, começa alguns segundos ANTES dele e dá play. Pular
  // exatamente para o instante da morte mostra o resultado e esconde a causa —
  // o que interessa numa revisão é a aproximação que levou até ali.
  var PREROLL_SECONDS = 3;

  // Converte o tick do evento no quadro do replay. O tick é o dado primário; o
  // tempo em segundos é só apresentação, e derivar a navegação dele foi o que
  // permitiu um clamp em zero mascarar um timestamp negativo.
  function frameDoTick(tick) {
    if (cur.t0 === undefined || !R.sample_every) return null;
    if (tick < cur.t0 || tick > cur.t1) return null;   // fora da janela exportada
    return (tick - cur.t0) / R.sample_every;
  }

  function seekToEvent(f) {
    // O preroll pode encostar no começo do round: aí ele encurta, e o replay
    // ainda começa no quadro 0. Isso NÃO é clamp de erro — o quadro de destino
    // já foi validado em frameDoTick, que devolve null quando o tick cai fora.
    var start = Math.min(cur.frames - 1, Math.max(0, f - PREROLL_SECONDS * R.sample_hz));
    pos = start;
    frame = Math.floor(start);
    document.getElementById("scrub").value = frame;
    draw();
    setPlaying(true);
  }

  // Abre o Replay num round e num tempo (segundos desde o fim do freeze): os chips da aba Perfil e o
  // endereço `#replay?round=12&t=34.5` (fase 12). Começa PREROLL_SECONDS antes, como ao clicar num
  // evento, e fica PARADO: quem abriu escolhe quando tocar. Sem `t`, o round abre no começo.
  function abreNoReplay(roundNum, t, semHash) {
    var alvo = null;
    for (var j = 0; j < rounds.length; j++) if (rounds[j].round === roundNum) { alvo = rounds[j]; break; }
    if (!alvo) return false;
    selectTab("replay", semHash);
    selectRound(alvo);
    if (t !== null && t !== undefined && !isNaN(t)) {
      var f = Math.min(cur.frames - 1, Math.max(0, (t - PREROLL_SECONDS) * R.sample_hz));
      pos = f;
      frame = Math.floor(f);
      document.getElementById("scrub").value = frame;
      draw();
    }
    if (!semHash) {
      try {
        history.replaceState(null, "", "#replay?round=" + roundNum + (t === null || t === undefined ? "" : "&t=" + t));
      } catch (e) { /* arquivo local: sem hash */ }
    }
    return true;
  }

  // Segundos de cegueira restantes do jogador no quadro atual (0 = enxergando).
  function blindLeft(name, f) {
    var list = blindIndex[name];
    if (!list) return 0;
    var worst = 0;
    for (var i = 0; i < list.length; i++) {
      var b = list[i];
      if (f >= b.f0 && f <= b.f1) {
        var left = (b.f1 - f) / R.sample_hz;
        if (left > worst) worst = left;
      }
    }
    return worst;
  }

  function selectRound(r) {
    cur = r;
    frame = 0;
    pos = 0;
    // Trocar de round troca o conjunto de desenhos: nada de rabisco de um
    // round vazando no outro.
    if (window.MapAnnotations && MapAnnotations.setRound) MapAnnotations.setRound(r.round);
    indexBlinds(r);
    setPlaying(false);
    // só os chips (a faixa também tem os separadores de meio-tempo)
    Array.prototype.forEach.call(strip.querySelectorAll(".rchip"), function (b) {
      b.setAttribute("aria-pressed", String(+b.dataset.round === r.round));
    });
    document.getElementById("scrub").max = r.frames - 1;
    document.getElementById("scrub").value = 0;
    document.getElementById("rh-round").textContent = "Round " + r.round;
    document.getElementById("rh-res").textContent =
      nomeLado(r.winner_team) + " · " + (REASON[r.reason] || r.reason) + " · " + br(r.seconds) + "s";
    buildLog();
    buildMarks();
    buildSquads();
    buildAutopsy();
    draw();
  }

  // Marcadores de evento sobre a barra de tempo: dá pra ver onde estão as
  // kills antes de arrastar, como num software de análise de demo.
  function buildMarks() {
    var host = document.getElementById("marks");
    host.innerHTML = cur.events.map(function (e) {
      var cls = e.type === "kill" ? (e.side === "ct" ? "ct" : "t") : "bomb";
      return "<i class='" + cls + "' style='left:" + (100 * e.f / (cur.frames - 1)) + "%'></i>";
    }).join("");
  }

  var MOMENT_ICON = {
    abertura_perdida: "◆",
    morte_isolada: "◇",
    virada_numerica: "▲",
    sem_utility: "○",
    sem_plant: "○",
    pos_plant: "▲"
  };

  function buildAutopsy() {
    var host = document.getElementById("autopsy");
    var b = BD[cur.round];
    if (!b) { host.innerHTML = ""; return; }

    var tags = b.tags.map(function (t) { return "<span class='tag'>" + esc(t) + "</span>"; }).join("");
    var moments = b.moments.map(function (m, i) {
      var extra = "";
      var title = "";
      // `causa` já vem pronta do Python e cobre o caso sem atacante (queda,
      // bomba): nunca cai no nome da vítima como matador.
      var causa = m.causa || (m.by ? "morreu para " + m.by : "");
      if (m.kind === "morte_isolada") {
        extra = "<small>" + esc(causa) + "</small>";
        title = " title='companheiro mais próximo a " + esc(m.distance) + " unidades'";
      } else if (m.kind === "abertura_perdida") {
        extra = "<small>" + esc(causa) + (m.traded ? " · trocado" : " · sem troca") + "</small>";
      } else if (m.kind === "virada_numerica") {
        extra = "<small>" + esc(m.victim) + " " + esc(causa) + "</small>";
      }

      // Tempo decorrido desde o fim do freeze time, no relógio. Segundos crus
      // com sinal não diziam de onde o tempo era contado.
      var quando = mmss(m.t) + (m.pos_round ? " <em>após o fim do round</em>" : "");

      var alvo = frameDoTick(m.tick);
      var podeClicar = alvo !== null;
      if (!podeClicar) {
        title = " title='tick " + esc(m.tick) + " fora da janela exportada do replay — " +
          "melhor não navegar do que navegar para o lugar errado'";
      }

      var who = m.who ? "<b>" + esc(m.who) + "</b> " : "";
      return "<button class='moment" + (podeClicar ? "" : " inerte") + "' data-i='" + i + "'" +
        (podeClicar ? "" : " disabled") + title + ">" +
        "<span class='mt'>" + quando + "</span>" +
        "<span class='ic'>" + (MOMENT_ICON[m.kind] || "•") + "</span>" +
        "<span class='mx'>" + who + esc(m.text) + extra + "</span></button>";
    }).join("");

    host.innerHTML =
      "<div class='ah'><h3>Por que " + esc(nomeLado(b.loser_team)) + " perdeu este round" +
      (b.ultimo_round ? " <span class='borda'>último round da partida</span>"
        : (b.fim_de_metade ? " <span class='borda'>último round da primeira metade</span>" : "")) +
      "</h3>" +
      "<div class='tags'>" + tags + "</div></div>" +
      // o texto de economia vem pronto do Python, com os dois lados e o dinheiro
      // formatado num único helper (ver metrics/formatting.format_money)
      (b.eco_text ? "<p class='why'>" + esc(b.eco_text) + "</p>" : "") +
      "<div class='mlist'>" + (moments || "<p class='why'>Nada fora do padrão: o round foi perdido no confronto direto, sem erro estrutural detectável.</p>") + "</div>" +
      "<p class='caveat'>São padrões observáveis que costumam custar rounds — morrer sem cobertura, " +
      "ficar em desvantagem que não se recupera, não usar utility. <b>Não é um veredito sobre a decisão " +
      "tomada</b>: por que o jogador estava ali depende do call e do que o adversário mostrou, e isso o " +
      "demo não registra. Clique num momento para assistir.</p>";

    Array.prototype.forEach.call(host.querySelectorAll(".moment"), function (btn) {
      btn.addEventListener("click", function () {
        var m = b.moments[Number(btn.dataset.i)];
        var alvo = frameDoTick(m.tick);
        if (alvo === null) return;
        seekToEvent(alvo);
        document.querySelector(".board").scrollIntoView({
          behavior: reduced ? "auto" : "smooth", block: "center"
        });
      });
    });
  }

  function buildSquads() {
    [["ct", "squad-ct"], ["t", "squad-t"]].forEach(function (pair) {
      var side = pair[0];
      var host = document.getElementById(pair[1]);
      host.className = "card squad " + side;
      var mine = cur.players.filter(function (p) { return p.side === side; });
      var team = mine.length ? mine[0].team : "?";
      host.innerHTML = "<h4>" + (side === "ct" ? "CT" : "TR") + " <b>" + esc(nomeLado(team)) + "</b></h4>" +
        mine.map(function (p, i) {
          return "<div class='plr' data-side='" + side + "' data-i='" + i + "'>" +
            "<div class='nm'>" + esc(p.name) + "</div><div class='hpn'>100</div>" +
            "<div class='hpbar'><i style='width:100%;background:" + (side === "ct" ? C.ct : C.tr) + "'></i></div>" +
            "<div class='wp'>—</div><div class='loc'></div></div>";
        }).join("");
    });
  }

  function updateSquads() {
    ["ct", "t"].forEach(function (side) {
      var host = document.getElementById(side === "ct" ? "squad-ct" : "squad-t");
      var mine = cur.players.filter(function (p) { return p.side === side; });
      Array.prototype.forEach.call(host.querySelectorAll(".plr"), function (row, i) {
        var p = mine[i];
        if (!p) return;
        var hp = p.alive[frame] ? p.hp[frame] : 0;
        row.classList.toggle("out", !p.alive[frame]);
        row.querySelector(".hpn").textContent = hp;
        row.querySelector(".hpbar > i").style.width = Math.max(0, hp) + "%";
        var w = p.w[frame];
        var bl = p.alive[frame] ? blindLeft(p.name, pos) : 0;
        row.classList.toggle("blind", bl > 0);
        row.querySelector(".wp").textContent = bl > 0
          ? "cego · " + br(bl) + "s"
          : (w >= 0 ? (cur.weapons[w] || "—") : "—");

        // Área do mapa (callout) e, em mapa de dois andares, qual deles. Vem do
        // próprio demo (`last_place_name`), com o nome que o jogo usa.
        var where = row.querySelector(".loc");
        if (where) {
          if (!p.alive[frame]) {
            where.textContent = "";
          } else {
            var pi = p.p ? p.p[frame] : -1;
            var nome = pi >= 0 ? (cur.places[pi] || "") : "";
            var lvl = p.lv ? LEVELS[p.lv[frame]] : null;
            where.textContent = nome + (lvl && lvl.name !== "default" ? " · inferior" : "");
          }
        }
      });
    });
  }

  // Linha do tempo = kills e bomba (sempre) + a utility que teve efeito. Flash
  // que não cegou inimigo e HE que não tirou dano ficam de fora: numa partida
  // profissional são ~9 granadas por round, e listar todas afogaria justamente
  // os eventos que decidiram o round. Elas continuam visíveis no mapa.
  function buildLogItems() {
    var items = cur.events.map(function (e) { return { e: e, f: e.f, t: e.t }; });

    (cur.pops || []).forEach(function (p) {
      if (p.k === "flash") {
        var hit = (p.hit || []).filter(function (v) { return v.e && v.s >= R.effective_blind_s; });
        if (hit.length) items.push({ pop: p, hit: hit, f: p.f, t: p.t });
      } else if (p.dmg > 0) {
        items.push({ pop: p, f: p.f, t: p.t });
      }
    });

    return items.sort(function (a, b) { return a.f - b.f; });
  }

  function logText(it) {
    if (it.pop) {
      if (it.pop.k === "flash") {
        var longest = it.hit.reduce(function (m, v) { return v.s > m ? v.s : m; }, 0);
        var who = it.hit.map(function (v) { return esc(v.n); }).join(", ");
        return "<span class='who'><b>" + esc(it.pop.by) + "</b> cegou " + who + "</span> " +
          "<span class='wpn'>flash · " + br(longest) + "s</span>";
      }
      return "<span class='who'><b>" + esc(it.pop.by) + "</b> acertou HE</span> " +
        "<span class='wpn'>" + esc(it.pop.dmg) + " de dano</span>";
    }
    var e = it.e;
    if (e.type === "kill") {
      // a frase vem pronta do Python (frase_da_morte): sem atacante, fogo amigo
      // e atacante igual à vítima têm cada um a sua
      return "<span class='who'><b>" + esc(e.quem) + "</b> " + esc(e.acao) + "</span> " +
        "<span class='wpn'>" + esc((e.weapon || "").replace(/_/g, " ")) + (e.headshot ? " · hs" : "") + "</span>";
    }
    if (e.type === "plant") {
      return "<span class='who'>" + esc(e.player || "T") + " plantou</span> <span class='wpn'>" +
        esc((e.site || "").replace("Bombsite", "bomb ")) + "</span>";
    }
    if (e.type === "defuse") return "<span class='who'>" + esc(e.player || "CT") + " desarmou</span>";
    return "<span class='who'>a bomba explodiu</span>";
  }

  function buildLog() {
    var log = document.getElementById("log");
    log.innerHTML = "";
    logItems = buildLogItems();
    logItems.forEach(function (it, i) {
      var e = it.e;
      var b = document.createElement("button");
      b.className = "ev" +
        (e && (e.type === "plant" || e.type === "explode") ? " bomb" : "") +
        (e && e.type === "defuse" ? " defuse" : "") +
        (it.pop ? " util " + it.pop.k : "");
      b.dataset.i = i;
      b.innerHTML = "<span class='tm'>" + br(it.t) + "s</span><span>" + logText(it) + "</span>";
      b.addEventListener("click", function () { seekToEvent(it.f); });
      log.appendChild(b);
    });
  }

  function lerp(a, b, t) { return a + (b - a) * t; }

  // --- Suavização da trajetória ------------------------------------------
  //
  // O replay é amostrado a 4 Hz. Interpolar linearmente entre amostras é
  // C0-contínuo: a velocidade muda de golpe a cada amostra e a trajetória faz
  // quina nas mudanças de direção. A 1× isso passa despercebido, mas a 0.25×
  // cada segmento dura 1 segundo de tempo real e a quina fica escancarada —
  // o movimento lê como degrau.
  //
  // Catmull-Rom é C1-contínua: a velocidade atravessa a amostra sem salto e a
  // quina some. Usamos a variante CENTRÍPETA (alfa = 0,5), que é livre de
  // cúspide e auto-interseção — a uniforme dá overshoot em curva fechada, e um
  // jogador aparentando atravessar parede seria pior que a quina original.
  //
  // IMPORTANTE: isto é reconstrução, não medição. A posição entre amostras
  // sempre foi inventada (antes por reta, agora por curva); a curva só erra de
  // forma mais plausível. Nenhuma métrica usa estes valores — são só desenho.
  var CR_ALPHA = 0.5;

  // A 64 tick com amostra a cada 16 ticks o intervalo é 0,25s. No limite físico
  // do jogo (~250 u/s, a mesma âncora que metrics/timing.py usa) isso dá ~62
  // unidades por amostra. Acima de 80 não é movimento: é morte, respawn ou
  // teleporte — e aí a curva viraria um arco inventado ligando dois pontos sem
  // relação. Nesses casos cai para linear.
  var MAX_STEP_UNITS = 80;

  function farApart(ax, ay, bx, by) {
    var dx = ax - bx, dy = ay - by;
    return dx * dx + dy * dy > MAX_STEP_UNITS * MAX_STEP_UNITS;
  }

  // Catmull-Rom centrípeta em uma dimensão, avaliada em t (0..1) entre p1 e p2.
  function crSpline(p0, p1, p2, p3, q0, q1, q2, q3, t) {
    function tj(ti, xa, ya, xb, yb) {
      var dx = xb - xa, dy = yb - ya;
      return ti + Math.pow(Math.sqrt(dx * dx + dy * dy), CR_ALPHA);
    }
    var t0 = 0;
    var t1 = tj(t0, p0, q0, p1, q1);
    var t2 = tj(t1, p1, q1, p2, q2);
    var t3 = tj(t2, p2, q2, p3, q3);
    // amostras coincidentes zeram o intervalo e a divisão explode
    if (t1 === t0 || t2 === t1 || t3 === t2) {
      return [lerp(p1, p2, t), lerp(q1, q2, t)];
    }
    var tt = lerp(t1, t2, t);

    function axis(v0, v1, v2, v3) {
      var a1 = (t1 - tt) / (t1 - t0) * v0 + (tt - t0) / (t1 - t0) * v1;
      var a2 = (t2 - tt) / (t2 - t1) * v1 + (tt - t1) / (t2 - t1) * v2;
      var a3 = (t3 - tt) / (t3 - t2) * v2 + (tt - t2) / (t3 - t2) * v3;
      var b1 = (t2 - tt) / (t2 - t0) * a1 + (tt - t0) / (t2 - t0) * a2;
      var b2 = (t3 - tt) / (t3 - t1) * a2 + (tt - t1) / (t3 - t1) * a3;
      return (t2 - tt) / (t2 - t1) * b1 + (tt - t1) / (t2 - t1) * b2;
    }
    return [axis(p0, p1, p2, p3), axis(q0, q1, q2, q3)];
  }

  // Posição suavizada do jogador entre os quadros i0 e i0+1.
  function smoothPos(p, i0, i1, t) {
    var x1 = p.x[i0], y1 = p.y[i0], x2 = p.x[i1], y2 = p.y[i1];

    // guardas: vizinhos ausentes (bordas do round), jogador morto no trecho, ou
    // salto implausível. Em qualquer um deles, reta.
    var a = i0 - 1, d = i1 + 1;
    if (a < 0 || d >= p.x.length ||
        !p.alive[a] || !p.alive[i0] || !p.alive[i1] || !p.alive[d] ||
        farApart(x1, y1, x2, y2) ||
        farApart(p.x[a], p.y[a], x1, y1) ||
        farApart(x2, y2, p.x[d], p.y[d])) {
      return [lerp(x1, x2, t), lerp(y1, y2, t)];
    }
    return crSpline(p.x[a], x1, x2, p.x[d], p.y[a], y1, y2, p.y[d], t);
  }

  function mmss(sec) {
    var m = Math.floor(sec / 60), r = Math.floor(sec % 60);
    return m + ":" + (r < 10 ? "0" : "") + r;
  }

  // --- Relógio no formato do jogo ----------------------------------------
  //
  // O jogador não lê tempo decorrido subindo: lê 1:55 descendo e, depois do
  // plant, os 40s da bomba. Mostrar "0:17 / 1:05" faz o round parecer curto
  // mesmo com a duração certa, porque não é a escala com que se joga.
  //
  // O quadro 0 vale 1:55 porque o replay começa no `freeze_end`, que é onde o
  // cronômetro do round começa a correr — o freeze (medido em
  // R.clock.freeze_seconds) fica inteiro fora do replay.
  var CLOCK = (R.clock || { round_seconds: 115, bomb_seconds: 40 });

  // Instante do plant e o que encerrou a bomba, por round.
  function bombState() {
    var plant = null, stop = null;
    cur.events.forEach(function (e) {
      if (e.type === "plant" && plant === null) plant = e.t;
      if ((e.type === "defuse" || e.type === "explode") && stop === null) stop = e.t;
    });
    return { plant: plant, stop: stop };
  }

  // O relógio de um instante (segundos desde o fim do freeze): o do round ou,
  // depois do plant, o da bomba. Função pura: a tela e a "Tática deste
  // instante" leem o mesmo número.
  function relogioDe(elapsed) {
    var b = bombState();
    var main, armed = false;

    // Depois do plant o relógio do round deixa de existir: o que importa é a
    // bomba, congelada no defuse/explosão. A conta é a do map_core.js, a mesma
    // que a prancheta usa (MapCore.relogio).
    main = MapCore.relogio(elapsed, b.plant, b.stop, CLOCK.round_seconds, CLOCK.bomb_seconds);
    armed = b.plant !== null && elapsed >= b.plant;
    return { main: main, armed: armed };
  }

  function updateClock(elapsed) {
    var host = document.getElementById("clock");
    var r = relogioDe(elapsed);
    host.className = "clock" + (r.armed ? " armed" : "");
    host.innerHTML = "<b>" + esc(r.main) + "</b><span>decorrido " + mmss(elapsed) + "</span>";
  }

  function draw() {
    var i0 = Math.floor(pos);
    var i1 = Math.min(cur.frames - 1, i0 + 1);
    var tt = pos - i0;
    frame = i0;

    var lvNow = activeLevel(i0);
    // O clear tem que acontecer em coordenada de tela; a transformacao de zoom
    // entra depois dele e vale para tudo que o round desenha. E a MESMA
    // transformacao da camada de anotacao -- se as duas divergirem, a seta
    // aponta pro lugar errado assim que alguem der zoom.
    ctx.setTransform(1, 0, 0, 1, 0, 0);
    ctx.clearRect(0, 0, cv.width, cv.height);
    if (window.MapAnnotations) MapAnnotations.applyView(ctx);
    ctx.drawImage(plates[lvNow] || plates[0], 0, 0);
    // nomes e etiquetas vão para a camada de rótulos (px de tela, por cima de tudo; §4.2)
    MapCore.rotulosInicia(ctx, cv, draw);

    // Smoke e Molotov ocupam área, então são desenhados como zona e não como
    // ponto. O raio segue o raio real de efeito no jogo (constantes do
    // map_core.js), convertido pela mesma escala do radar.
    var SMOKE_R = MapCore.RAIO_SMOKE_UNIDADES * RAD.scale_px_per_unit;
    var FIRE_R = MapCore.RAIO_MOLOTOV_UNIDADES * RAD.scale_px_per_unit;

    cur.smokes.forEach(function (z) {
      if (pos < z.f0 || pos > z.f1) return;
      MapCore.desenhaArea(ctx, "smoke", mx(z.x), my(z.y), SMOKE_R);
    });
    cur.fires.forEach(function (z) {
      if (pos < z.f0 || pos > z.f1) return;
      MapCore.desenhaArea(ctx, "molotov", mx(z.x), my(z.y), FIRE_R);
    });

    // Granadas em voo. O rastro é curto e some atrás da granada (segmentos com
    // alfa decrescente em vez de uma linha só): uma linha inteira e opaca
    // riscava o mapa e competia com o rastro dos jogadores.
    cur.nades.forEach(function (n) {
      // Índice CONTÍNUO, não o quadro inteiro. O replay é amostrado a 4 Hz e os
      // jogadores já eram interpolados; a granada não era, então ela andava aos
      // saltos de 250ms enquanto todo o resto deslizava — e granada é justamente
      // o objeto mais rápido da tela.
      var k = pos - n.f0;
      var last = n.x.length - 1;
      if (k < 0) return;

      var col = NADE_COLOR[n.k] || CM.apagado;
      var landed = k > last;
      // depois de cair, a marca do ponto de queda ainda fica um tempo: sem isso
      // a granada some e você perde onde ela foi parar
      var afterLanding = landed ? k - last : 0;
      if (afterLanding > LANDING_HOLD) return;

      var ki = Math.min(k, last);
      var ka = Math.floor(ki), kb = Math.min(last, ka + 1), kt = ki - ka;
      var gx = mx(lerp(n.x[ka], n.x[kb], kt));
      var gy = my(lerp(n.y[ka], n.y[kb], kt));

      // Direção do voo, em pixels de tela: é ela que orienta os símbolos que
      // têm frente. Usa o trecho anterior quando a granada já parou, senão o
      // glifo gira sozinho no último quadro.
      var da = Math.max(0, ka - 1), db = Math.min(last, da + 1);
      var ang = Math.atan2(my(n.y[db]) - my(n.y[da]), mx(n.x[db]) - mx(n.x[da]));

      // TRAJETÓRIA INTEIRA, esmaecendo na origem. O rastro curto de antes
      // mostrava "tem uma granada ali"; o traço inteiro responde DE ONDE ela
      // veio, que é metade da leitura de uma execução.
      ctx.lineCap = "round";
      for (var i = 1; i <= ka; i++) {
        ctx.globalAlpha = (0.10 + 0.32 * (i / Math.max(1, ki))) * (landed ? 0.5 : 1);
        ctx.strokeStyle = col;
        ctx.lineWidth = 0.7 + 1.2 * (i / Math.max(1, ki));
        ctx.beginPath();
        ctx.moveTo(mx(n.x[i - 1]), my(n.y[i - 1]));
        ctx.lineTo(mx(n.x[i]), my(n.y[i]));
        ctx.stroke();
      }
      // o pedaço entre a última amostra e a posição atual, senão o rastro fica
      // um quadro atrás da granada e ela parece descolada da própria trajetória
      if (ka >= 1 && kt > 0 && ka < last) {
        ctx.globalAlpha = 0.42 * (landed ? 0.5 : 1);
        ctx.strokeStyle = col;
        ctx.lineWidth = 1.9;
        ctx.beginPath();
        ctx.moveTo(mx(n.x[ka]), my(n.y[ka]));
        ctx.lineTo(gx, gy);
        ctx.stroke();
      }

      // ponto de arremesso, vazado
      ctx.globalAlpha = landed ? 0.28 : 0.5;
      ctx.strokeStyle = col;
      ctx.lineWidth = 1.2;
      ctx.beginPath(); ctx.arc(mx(n.x[0]), my(n.y[0]), 3, 0, Math.PI * 2); ctx.stroke();
      ctx.globalAlpha = 1;

      if (landed) {
        // marca de onde caiu, sumindo devagar
        ctx.globalAlpha = 0.5 * (1 - afterLanding / LANDING_HOLD);
        nadeGlyph(ctx, n.k, gx, gy, 5, col, ang);
        ctx.globalAlpha = 1;
        return;
      }

      // Em voo: o símbolo carrega o tipo. Cor sozinha não basta — a legenda
      // obrigava a desviar o olho do mapa, e quatro cores não sobrevivem a
      // daltonismo (a paleta foi validada para isso -- ver decisão 10 do CLAUDE.md).
      //
      // O halo existe porque o glifo dividia espaço com o rastro da própria
      // granada e com o dos jogadores: sem ele, o objeto em voo se confundia
      // com a linha que ele acabou de desenhar.
      ctx.save();
      ctx.globalAlpha = 0.22;
      ctx.fillStyle = col;
      ctx.beginPath(); ctx.arc(gx, gy, 9.5, 0, Math.PI * 2); ctx.fill();
      ctx.restore();
      nadeGlyph(ctx, n.k, gx, gy, 5.5, col, ang);
    });

    // Detonação de flash e HE. Diferente de smoke e fogo, elas não ocupam área:
    // acontecem num instante, e o que importa é o efeito. O anel abre e some em
    // ~1,5s. Uma flash que não cegou inimigo nenhum aparece apagada e sem
    // rótulo — a granada existiu, o efeito não, e o mapa mostra a diferença.
    // DETONAÇÃO COMO EVENTO.
    //
    // Flash e HE não ocupam área: acontecem num instante, e o que importa é o
    // efeito. A posição vem do evento de detonação do demo, não do último ponto
    // do voo — a 4 Hz aquele ponto pode estar metros antes de onde ela explodiu.
    //
    // A animação abre RÁPIDO e desacelera (ease-out cúbico). O anel linear de
    // antes lia como um ponto sumindo; um estouro que desacelera lê como
    // impacto. O raio cresce com a consequência: quantos inimigos cegaram,
    // quanto dano a HE tirou. Detonação sem efeito aparece apagada e sem
    // rótulo — a granada existiu, o efeito não, e o mapa mostra a diferença.
    (cur.pops || []).forEach(function (p) {
      var age = pos - p.f;
      if (age < 0 || age > POP_TOTAL) return;

      var X = mx(p.x), Y = my(p.y);
      var flash = p.k === "flash";
      var col = flash ? NADE_COLOR.flash : NADE_COLOR.he;

      var blinded = flash
        ? (p.hit || []).filter(function (v) { return v.e && v.s >= R.effective_blind_s; })
        : [];
      var strong = flash ? blinded.length > 0 : p.dmg > 0;

      // cicatriz: fica depois do estouro, pra você ainda achar onde foi
      if (age > POP_FRAMES) {
        var fade = 1 - (age - POP_FRAMES) / (POP_TOTAL - POP_FRAMES);
        ctx.globalAlpha = 0.3 * fade * (strong ? 1 : 0.5);
        ctx.strokeStyle = col;
        ctx.lineWidth = 1.2;
        ctx.setLineDash([2, 3]);
        ctx.beginPath(); ctx.arc(X, Y, 7, 0, Math.PI * 2); ctx.stroke();
        ctx.setLineDash([]);
        ctx.globalAlpha = 1;
        return;
      }

      var k = age / POP_FRAMES;
      var ease = 1 - Math.pow(1 - k, 3);  // abre rápido, desacelera
      var reach = strong
        ? (flash ? 26 + 9 * Math.min(3, blinded.length) : 24 + Math.min(34, p.dmg * 0.4))
        : 16;

      ctx.globalAlpha = (1 - ease) * (strong ? 0.9 : 0.3);
      ctx.strokeStyle = col;
      ctx.lineWidth = strong ? 3 : 1.2;
      ctx.beginPath();
      ctx.arc(X, Y, 5 + ease * reach, 0, Math.PI * 2);
      ctx.stroke();

      if (strong) {
        // núcleo claro que decai mais rápido que o anel: é o estouro
        ctx.globalAlpha = Math.max(0, 1 - k * 2.2);
        ctx.fillStyle = flash ? C.flash : col;
        ctx.beginPath(); ctx.arc(X, Y, 5 + ease * 5, 0, Math.PI * 2); ctx.fill();

        var tag = flash
          ? blinded.length + (blinded.length > 1 ? " cegos" : " cego")
          : p.dmg + " dano";
        // sem esmaecer: rótulo translúcido deixa o radar aparecer atrás da letra (A11); some quando o estouro acaba
        MapCore.rotulo(tag, X, Y, { cor: CM.tinta, prioridade: 5, dy: 16 + ease * 5 });
      }
      ctx.globalAlpha = 1;
    });

    // rastro percorrido até aqui
    cur.players.forEach(function (p) {
      var color = p.side === "ct" ? CM.ct : CM.tr;
      ctx.strokeStyle = color;
      ctx.globalAlpha = 0.22;
      ctx.lineWidth = 1.8;
      ctx.beginPath();
      var started = false;
      for (var i = Math.max(0, frame - 60); i <= frame; i++) {
        if (!p.alive[i]) break;
        var X = mx(p.x[i]), Y = my(p.y[i]);
        if (!started) { ctx.moveTo(X, Y); started = true; } else { ctx.lineTo(X, Y); }
      }
      ctx.stroke();
      ctx.globalAlpha = 1;
    });

    // Eventos já ocorridos. A comparação é com `pos` (contínuo) e não com o
    // quadro inteiro: o evento carrega quadro fracionário desde que o export
    // deixou de truncar, e comparar com o inteiro devolveria o mesmo atraso de
    // até 0,25s que o timeline denunciava.
    cur.events.forEach(function (e) {
      if (e.f > pos) return;
      var age = pos - e.f;
      if (e.type === "kill") {
        var a = Math.max(0.45, 1 - age / 90);
        ctx.globalAlpha = a;
        ctx.strokeStyle = e.side === "ct" ? CM.ct : CM.tr;
        ctx.lineWidth = 2.6;
        ctx.lineCap = "round";
        var X = mx(e.x), Y = my(e.y), s = 6.5;
        ctx.beginPath();
        ctx.moveTo(X - s, Y - s); ctx.lineTo(X + s, Y + s);
        ctx.moveTo(X + s, Y - s); ctx.lineTo(X - s, Y + s);
        ctx.stroke();
        ctx.globalAlpha = 1;
      } else if (e.type === "plant" && e.x != null) {
        ctx.fillStyle = CM.tr;
        ctx.globalAlpha = 0.9;
        ctx.beginPath();
        ctx.rect(mx(e.x) - 5, my(e.y) - 5, 10, 10);
        ctx.fill();
        ctx.globalAlpha = 0.25;
        ctx.beginPath();
        ctx.arc(mx(e.x), my(e.y), 12 + (age % 24), 0, Math.PI * 2);
        ctx.strokeStyle = CM.tr; ctx.lineWidth = 1.5; ctx.stroke();
        ctx.globalAlpha = 1;
      } else if (e.type === "defuse" && e.x != null) {
        ctx.fillStyle = CM.ct;
        ctx.beginPath();
        ctx.arc(mx(e.x), my(e.y), 6, 0, Math.PI * 2);
        ctx.fill();
      }
    });

    // jogadores — posição interpolada entre os quadros amostrados, senão o
    // movimento fica em saltos de 250ms
    var comDirecao = !window.MapAnnotations || !MapAnnotations.direcaoLigada ||
      MapAnnotations.direcaoLigada();
    cur.players.forEach(function (p) {
      var alive = p.alive[i0];
      // Suaviza em coordenada de JOGO e só depois converte pra pixel: a
      // conversão é linear, então tanto faz matematicamente, mas assim as
      // guardas de distância ficam em unidades do jogo (onde o limite de
      // velocidade faz sentido) em vez de pixels do radar.
      var canLerp = alive && p.alive[i1];
      var sp = canLerp ? smoothPos(p, i0, i1, tt) : [p.x[i0], p.y[i0]];
      var X = mx(sp[0]);
      var Y = my(sp[1]);
      var color = p.side === "ct" ? CM.ct : CM.tr;
      // Direção do olhar (array `d`, graus, no mesmo índice da posição).
      // Interpola pelo caminho mais curto entre i0 e i1 só quando o trecho é
      // interpolável: vivo nos dois quadros e sem salto (as guardas do
      // smoothPos para o par). Fora disso, o yaw do quadro atual. Sem Catmull-
      // Rom no ângulo: a mira muda aos saltos.
      var yaw = null;
      if (p.d && comDirecao) {
        yaw = (canLerp && !farApart(p.x[i0], p.y[i0], p.x[i1], p.y[i1]))
          ? MapCore.interpolaAngulo(p.d[i0], p.d[i1], tt) : p.d[i0];
      }
      // Morto, em outro andar ou vivo: o desenho de cada caso está em
      // MapCore.desenhaJogador (a prancheta usa o mesmo).
      var pLv = p.lv ? p.lv[i0] : 0;
      MapCore.desenhaJogador(ctx, X, Y, {
        cor: color,
        estado: !alive ? "morto" : (pLv !== lvNow ? "outro_andar" : "vivo"),
        acima: pLv > lvNow,
        cego: alive && pLv === lvNow && blindLeft(p.name, i0) > 0,
        hp: p.hp[i0],
        nome: p.name,
        yaw: yaw
      });
    });
    MapCore.rotulosDesenha();

    // estado da interface
    var el = pos / R.sample_hz, tot = (cur.frames - 1) / R.sample_hz;
    updateClock(el);
    var evs = document.querySelectorAll(".ev");
    var lastPast = -1;
    logItems.forEach(function (it, i) { if (it.f <= frame) lastPast = i; });
    Array.prototype.forEach.call(evs, function (b, i) {
      b.classList.toggle("past", i <= lastPast);
      b.classList.toggle("now", i === lastPast);
    });

    updateSquads();
  }

  function setPlaying(v) {
    playing = v;
    document.getElementById("play").textContent = v ? "❚❚" : "▶";
    document.getElementById("play").setAttribute("aria-label", v ? "Pausar" : "Reproduzir");
    if (v) { lastT = performance.now(); requestAnimationFrame(tick); }
  }

  // Avança em tempo contínuo e redesenha a cada quadro da tela: o replay foi
  // amostrado a 4 Hz, mas a interpolação em `draw` faz o movimento sair liso.
  function tick(now) {
    if (!playing) return;
    var dt = Math.min(0.1, (now - lastT) / 1000);
    lastT = now;
    pos = Math.min(cur.frames - 1, pos + dt * R.sample_hz * speed);
    document.getElementById("scrub").value = Math.floor(pos);
    draw();
    if (pos >= cur.frames - 1) { setPlaying(false); return; }
    if (window.MapAnnotations && MapAnnotations.onFrame) MapAnnotations.onFrame(pos);
    requestAnimationFrame(tick);
  }

  // Câmera lenta é o motivo desta lista: a 0.25× dá pra ler a ordem em que as
  // coisas acontecem numa troca de tiro, que a 1× passa batido.
  var SPEEDS = MapCore.VELOCIDADES;   // as mesmas da prancheta (map_core.js)

  function setSpeed(v) {
    speed = v;
    // "0.25×" em vez de "0,25×": é rótulo de controle, não número de leitura
    document.getElementById("speed").textContent = v + "×";
  }

  function stepSpeed(dir) {
    var i = SPEEDS.indexOf(speed);
    setSpeed(SPEEDS[Math.max(0, Math.min(SPEEDS.length - 1, i + dir))]);
  }

  function togglePlay() {
    if (pos >= cur.frames - 1) { pos = 0; document.getElementById("scrub").value = 0; }
    setPlaying(!playing);
  }

  // Avança/volta quadro a quadro, para revisar detalhe parado.
  function stepFrame(n) {
    setPlaying(false);
    pos = Math.max(0, Math.min(cur.frames - 1, Math.round(pos) + n));
    document.getElementById("scrub").value = Math.floor(pos);
    draw();
  }

  document.getElementById("play").addEventListener("click", togglePlay);
  document.getElementById("scrub").addEventListener("input", function (e) {
    pos = Number(e.target.value);
    setPlaying(false);
    draw();
  });

  // Atalhos de revisão. A guarda de foco existe porque a página tem controles
  // focáveis de verdade — botões de round, o seletor de partida, o slider — e
  // sem ela o espaço dispararia o botão focado E o play ao mesmo tempo, e as
  // setas mexeriam no slider e no replay juntas.
  document.addEventListener("keydown", function (e) {
    if (e.ctrlKey || e.metaKey || e.altKey) return;
    var el = document.activeElement;
    if (el && (el.tagName === "INPUT" || el.tagName === "SELECT" ||
               el.tagName === "TEXTAREA" || el.tagName === "BUTTON" ||
               el.isContentEditable)) return;
    // atalho de replay não faz sentido com a aba de replay escondida
    if (document.querySelector("[data-panel='replay']").hidden) return;

    var step = e.shiftKey ? Math.round(R.sample_hz) : 1;  // Shift = 1 segundo
    if (e.key === " " || e.key === "Spacebar") { e.preventDefault(); togglePlay(); }
    else if (e.key === "ArrowRight") { e.preventDefault(); stepFrame(step); }
    else if (e.key === "ArrowLeft") { e.preventDefault(); stepFrame(-step); }
    else if (e.key === "]") { e.preventDefault(); stepSpeed(1); }
    else if (e.key === "[") { e.preventDefault(); stepSpeed(-1); }
  });
  document.getElementById("speed").addEventListener("click", function () {
    setSpeed(SPEEDS[(SPEEDS.indexOf(speed) + 1) % SPEEDS.length]);
  });

  // Partida sem round decisivo abre no primeiro round. `decRound` é null nesse
  // caso, e todo lugar que destaca "o" round tem que aguentar isso -- não é
  // caso de borda, são 5 das 9 partidas do corpus.
  // A camada de desenho precisa existir ANTES do primeiro selectRound, senao o
  // round inicial nao chega nela.
  (function iniciaAnotacoes() {
    if (!window.MapAnnotations || !MapAnnotations.init) return;
    MapAnnotations.init({
      mapCanvas: cv,
      palco: document.getElementById("palco"),
      barraNoFim: true,
      radar: RAD,
      // Identidade da PARTIDA. Cair no nome do mapa faria duas partidas na
      // mesma Mirage dividirem a mesma chave de anotacao.
      matchId: (M && M.match_id) || "partida",
      mapa: RAD.map || (M && M.map) || null,
      // A impressao da calibracao acompanha cada traco: a correspondencia entre
      // unidade de jogo e pixel foi AJUSTADA, nao e constante do jogo. Ela vem
      // pronta do build (metrics/annotations.impressao_da_calibracao), a mesma
      // funcao que valida os arquivos exportados. Sem radar calibrado, a
      // projecao sai dos limites da partida e a impressao diz isso.
      calibracao: RAD.calibracao || ["sintetica", RAD.scale_px_per_unit,
                   RAD.origin_x, RAD.origin_y].join(":"),
      // página da prancheta do mesmo mapa, quando existe (vem do build)
      prancheta: window.__PRANCHETA__,
      // Retrato do quadro ATUAL para a prancheta: cada jogador vivo com a
      // posição, a direção e o andar da amostra do quadro (sem interpolar --
      // é o dado gravado, não o desenho entre dois quadros).
      // A peça sai do quadro i0 = floor(pos), o mesmo que draw() usa para
      // `alive`; o relógio é o DESSE quadro, não o da tela (que anda com o
      // pos fracionário entre dois quadros).
      amostrasPorSegundo: R.sample_hz,
      // O ROUND INTEIRO para a prancheta (fase 9): o caminho de cada jogador
      // (simplificado com a tolerância medida, metrics/round_na_prancheta.py),
      // as mortes, as granadas e o plant, mais o instante de agora (onde a
      // prancheta abre) e a função estrutural de cada jogador naquele lado.
      roundInteiro: function () {
        var cfgRound = PAGINA.round_na_prancheta;
        if (!cfgRound) return null;
        var inst = this.instante();
        var pl = MapCore.roundParaPrancheta(R.sample_hz, cur, cfgRound.tolerancia_u, (M && M.match_id) || "", inst.quadro);
        pl.instante = inst;
        var rotulos = D.structural_role_labels || {}, funcoes = {};
        (D.structural_roles || []).forEach(function (s) {
          cur.players.forEach(function (p) {
            if (p.name === s.name && p.side === s.side && rotulos[s.funcao]) funcoes[p.name] = rotulos[s.funcao];
          });
        });
        pl.funcoes = funcoes;
        return pl;
      },
      instante: function () {
        var i0 = Math.floor(pos);
        return {
          partida: (M && M.match_id) || "", round: cur.round, quadro: i0,
          relogio: relogioDe(i0 / R.sample_hz).main,
          tick: cur.t0 !== undefined && R.sample_every ? cur.t0 + i0 * R.sample_every : null,
          // o elenco do round inteiro, vivos e mortos: é o banco da prancheta
          elenco: cur.players.map(function (p) { return { nome: p.name, lado: p.side }; }),
          // os mortos até o quadro i0, na ordem das mortes: a ordem é o primeiro
          // quadro em que o jogador aparece morto (o mesmo `alive` que decide
          // quem vira peça), o que cobre também morte sem kill (bomba, queda)
          mortos: cur.players.filter(function (p) { return !p.alive[i0]; }).map(function (p) {
            var q = 0;
            while (q < i0 && p.alive[q]) q++;
            return { nome: p.name, lado: p.side, quadro: q };
          }).sort(function (a, b) { return a.quadro - b.quadro || (a.nome < b.nome ? -1 : 1); })
            .map(function (m, n) { return { nome: m.nome, lado: m.lado, ordem: n + 1 }; }),
          // granadas ativas no quadro: smoke e fogo com o efeito no ar, e
          // qualquer granada ainda voando (o destino é o fim da trajetória, que
          // está alguns quadros à frente -- é o que se quer ver). Flash e HE já
          // estouradas não entram. `lance` é a ligação ao arremesso que o
          // export fez (ou null, sem ligação).
          granadas: (function () {
            var out = [], vistos = {};
            [["smoke", cur.smokes], ["molotov", cur.fires]].forEach(function (par) {
              (par[1] || []).forEach(function (z) {
                if (z.f0 <= i0 && i0 <= z.f1) {
                  out.push({ arma: par[0], destino: [z.x, z.y], lance: z.l || null });
                  if (z.l) vistos[z.l.id] = true;
                }
              });
            });
            (cur.nades || []).forEach(function (n) {
              if (n.f0 <= i0 && i0 < n.f0 + n.x.length - 1 && !(n.l && vistos[n.l.id])) {
                out.push({ arma: n.k, destino: [n.x[n.x.length - 1], n.y[n.y.length - 1]], lance: n.l || null });
              }
            });
            return out;
          })(),
          jogadores: cur.players.filter(function (p) { return p.alive[i0]; }).map(function (p) {
            return { nome: p.name, lado: p.side, x: p.x[i0], y: p.y[i0],
                     yaw: p.d ? p.d[i0] : null, nivel: p.lv ? p.lv[i0] : 0 };
          })
        };
      },
      pause: function () { setPlaying(false); },
      redraw: function () { draw(); },
      contexto: function () {
        return {
          partida: (D.match && D.match.map) || "",
          mapa: RAD.map || "",
          placar: D.match ? (D.match.score_a + "-" + D.match.score_b) : "",
          instante: document.getElementById("clock").textContent
        };
      }
    });
  })();

  selectRound(rounds.find(function (r) { return r.round === decRound; }) || rounds[0]);

