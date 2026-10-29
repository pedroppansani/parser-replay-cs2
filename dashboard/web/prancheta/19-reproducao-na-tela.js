  /* ---------------------------------------------------------------------
     Reprodução: tocar, pausar, velocidade, barra de tempo, passos, Editar
     --------------------------------------------------------------------- */
  var quadroPedido = null;

  function reproduzAte(t) {
    var r = S.reproducao;
    if (r.modo === "relogio") {
      r.t = Math.max(0, Math.min(fimDaTatica(S.e3), t));
      r.cena = cenaNoRelogio(r.t);
    } else {
      r.t = t;
      r.cena = estadoNoTempo(S.estado, t, CENTRO);
    }
    desenha();
    atualizaPlayer();
    atualizaRelogioGrande();
    atualizaLinhaDoTempo();
  }

  function comecaReproducao() {
    if (S.reproducao) return;
    confirmaGiro();
    S.sel = null; S.arrasto = null; S.tracando = null; S.origemPendente = null; S.busca = null;
    // versão 3: no relógio do round, do começo; versões 1 e 2: passo a passo
    var relogio = tocaNoRelogio();
    S.reproducao = { t: 0, tocando: false, velocidade: 1, cena: null, ultimo: 0, modo: relogio ? "relogio" : "passos" };
    // a barra de edição e o painel ficam à vista a 45% e inertes (§14); o controle é o do player ("Pausar e editar")
    $("pr-barra").setAttribute("inert", ""); $("pr-player").hidden = false;
    if ($("pr-opcoes")) $("pr-opcoes").setAttribute("inert", "");   // as opções do pincel são parte da barra de edição
    if ($("pr-dica-estado")) $("pr-dica-estado").hidden = true;
    // durante a reprodução nada é editável
    document.querySelector("aside").setAttribute("inert", "");
    reproduzAte(relogio ? primeiroEvento() : 0);
    toca(true);
  }

  /** A reprodução no relógio começa no primeiro evento (round que começa no
      meio, como o que vem de um instante do replay, não toca segundos vazios). */
  function primeiroEvento() {
    var ev = eventosDe(S.e3);
    return ev.length ? ev[0].t : 0;
  }

  function editaAqui() {
    if (!S.reproducao) return;
    toca(false);
    var r = S.reproducao;
    S.passo = r.cena.indice;
    if (r.modo === "relogio") S.t = Math.round(r.t * 100) / 100;
    S.reproducao = null;
    $("pr-barra").removeAttribute("inert"); $("pr-player").hidden = true;
    if ($("pr-opcoes")) $("pr-opcoes").removeAttribute("inert");
    S.ultimoBalao = null;
    if ($("pr-dica-estado")) $("pr-dica-estado").hidden = false;
    document.querySelector("aside").removeAttribute("inert");
    atualizaTudo();
    avisaTempo();
  }

  function toca(sim) {
    var r = S.reproducao;
    if (!r) return;
    if (sim && r.t >= r.cena.total) reproduzAte(r.modo === "relogio" ? primeiroEvento() : 0);   // no fim, tocar recomeça
    r.tocando = sim;
    r.ultimo = performance.now();
    cancelAnimationFrame(quadroPedido);
    if (sim) quadroPedido = requestAnimationFrame(avanca);
    atualizaPlayer();
    avisaTempo();
  }

  function avanca(agoraMs) {
    var r = S.reproducao;
    if (!r || !r.tocando) return;
    var dt = Math.max(0, agoraMs - r.ultimo) / 1000;
    r.ultimo = agoraMs;
    var t = Math.min(r.cena.total, r.t + dt * r.velocidade);
    reproduzAte(t);
    if (t >= r.cena.total) { r.tocando = false; atualizaPlayer(); return; }
    quadroPedido = requestAnimationFrame(avanca);
  }

  /** Próximo: o primeiro fim de passo depois de t (é onde o passo fica
      completo). Anterior: o último fim de passo antes de t, ou o começo. */
  function vaiParaPasso(delta) {
    var r = S.reproducao;
    if (!r) return;
    if (r.modo === "relogio") {
      // no relógio, o próximo (ou o anterior) EVENTO do roteiro
      var hs = eventosDe(S.e3).map(function (e) { return e.t; });
      var vai = delta > 0 ? hs.filter(function (h) { return h > r.t + EPS_T; })[0]
                          : hs.filter(function (h) { return h < r.t - EPS_T; }).pop();
      reproduzAte(vai === undefined ? (delta > 0 ? r.cena.total : primeiroEvento()) : vai);
      avisaTempo();
      return;
    }
    var lt = linhaDoTempo(S.estado), EPS = 1e-9;
    var fins = S.estado.passos.map(function (p, k) { return lt.inicios[k] + p.duracao_s; });
    var alvo;
    if (delta > 0) alvo = fins.filter(function (f) { return f > r.t + EPS; })[0];
    else alvo = fins.filter(function (f) { return f < r.t - EPS; }).pop();
    reproduzAte(alvo === undefined ? (delta > 0 ? lt.total : 0) : alvo);
    avisaTempo();
  }

  function mudaVelocidade(dir) {
    var r = S.reproducao, v = MapCore.VELOCIDADES;
    if (!r) return;
    var i = v.indexOf(r.velocidade);
    r.velocidade = dir === 0 ? v[(i + 1) % v.length] : v[Math.max(0, Math.min(v.length - 1, i + dir))];
    atualizaPlayer();
    avisaTempo();
  }

  function atualizaPlayer() {
    var r = S.reproducao;
    if (!r || !r.cena) return;
    var barra = $("pr-tempo");
    barra.max = String(Math.round(r.cena.total * 1000));
    if (document.activeElement !== barra) barra.value = String(Math.round(r.t * 1000));
    $("pr-toca").textContent = r.tocando ? "Pausar" : "Tocar";
    $("pr-velocidade").textContent = String(r.velocidade).replace(".", ",") + "x";
    var c = r.cena;
    if (r.modo === "relogio") {
      $("pr-rotulo-passo").textContent = relogioEm(r.t) + "  (" + r.t.toFixed(1).replace(".", ",") + " s de " +
        c.total.toFixed(1).replace(".", ",") + " s)";
      return;
    }
    $("pr-rotulo-passo").textContent = "Passo " + (c.indice + 1) + " de " + S.estado.passos.length +
      (c.titulo ? " · " + c.titulo : "") + "  (" + r.t.toFixed(1).replace(".", ",") + " de " +
      c.total.toFixed(1).replace(".", ",") + " s)";
  }

  function montaPlayer() {
    var player = el("div", { class: "pr-barra", id: "pr-player" });
    player.hidden = true;
    var grupo = el("div", { class: "anot-grupo sempre" });
    var b = function (texto, titulo, fn, id) { var x = MapCore.botao(texto, titulo, fn); x.id = id; grupo.appendChild(x); };
    b("◀", "Passo anterior (seta para a esquerda)", function () { vaiParaPasso(-1); }, "pr-passo-anterior");
    b("Tocar", "Tocar ou pausar (espaço)", function () { toca(!S.reproducao.tocando); }, "pr-toca");
    b("▶", "Próximo passo (seta para a direita)", function () { vaiParaPasso(1); }, "pr-passo-seguinte");
    b("1x", "Velocidade ([ e ])", function () { mudaVelocidade(0); }, "pr-velocidade");
    player.appendChild(grupo);
    var tempo = el("input", { type: "range", id: "pr-tempo", min: "0", step: "1", "aria-label": "Linha do tempo da tática" });
    tempo.style.flex = "1";
    tempo.addEventListener("input", function () {
      // lê ANTES de pausar: pausar atualiza a barra com o t atual
      var t = +this.value / 1000;
      toca(false);
      reproduzAte(t);
      avisaTempo();
    });
    player.appendChild(tempo);
    player.appendChild(el("span", { id: "pr-rotulo-passo", class: "pr-meta" }));
    var editar = MapCore.botao("❚❚ Pausar e editar", "Pausar e voltar ao editor no passo em que parou", editaAqui);
    editar.id = "pr-editar";
    player.appendChild(editar);
    $("pr-palco").insertBefore(player, $("pr-tela"));
  }

  /** A tática nova a partir de um instante do replay (#instante=...). O
      retrato vem de fora da página: cada jogador é conferido antes de virar
      peça, e o que não fecha fica de fora com aviso -- nunca pela metade
      calado. */
  function criaDoInstante(retrato) {
    var jogadores = (retrato && Array.isArray(retrato.jogadores)) ? retrato.jogadores : [];
    var validos = jogadores.filter(function (j) {
      return j && LADOS.indexOf(j.lado) >= 0 && ehNumero(j.x) && ehNumero(j.y) && typeof j.nome === "string" &&
        (j.yaw === null || j.yaw === undefined || (ehNumero(j.yaw) && j.yaw >= 0 && j.yaw < 360)) &&
        (ehInteiro(j.nivel) && j.nivel >= 0 && j.nivel < ANDARES.length);
    });
    novaTatica();
    // metadado da criação: não é operação e não muda depois (como mapa e calibração)
    var elenco = Array.isArray(retrato.elenco) ? retrato.elenco.filter(function (j) {
      return j && typeof j.nome === "string" && j.nome && LADOS.indexOf(j.lado) >= 0;
    }).map(function (j) { return { nome: j.nome.slice(0, 32), lado: j.lado }; }) : [];
    var nomesDoElenco = {};
    elenco.forEach(function (j) { nomesDoElenco[j.nome] = j.lado; });
    var mortos = Array.isArray(retrato.mortos) ? retrato.mortos.filter(function (m) {
      return m && nomesDoElenco[m.nome] === m.lado && ehInteiro(m.ordem) && m.ordem >= 1;
    }).map(function (m) { return { nome: m.nome, lado: m.lado, ordem: m.ordem }; }) : [];
    var origem = { partida: String(retrato.partida || ""), round: retrato.round, quadro: retrato.quadro,
                   relogio: String(retrato.relogio || ""), elenco: elenco, mortos: mortos };
    if (!problemasDaOrigem(origem).length) S.doc.origem = origem;
    bancoDe = null;   // o banco da tática nova passa a ser o elenco do round
    var passo = passoAtual();
    validos.forEach(function (j) {
      var dados = { peca: novoId(), lado: j.lado, rotulo: j.nome.slice(0, 32), passo: passo,
                    x: j.x, y: j.y, nivel: j.nivel };
      if (j.yaw !== null && j.yaw !== undefined) dados.yaw = j.yaw;
      emite("cria_peca", dados, false);
    });
    // Granadas ativas no instante: com o arremesso real quando ele está na
    // biblioteca, com a posição da soltura quando não está, e só com o efeito
    // (origem_desconhecida) quando o replay não ligou o efeito a arremesso nenhum.
    var granadas = Array.isArray(retrato.granadas) ? retrato.granadas : [];
    var bib = {};
    ((cfg.biblioteca && cfg.biblioteca.arremessos) || []).forEach(function (a) { bib[a.id] = a; });
    var foraGranadas = 0;
    granadas.forEach(function (g) {
      var lance = g && g.lance;
      var ok = g && ARMAS.indexOf(g.arma) >= 0 && Array.isArray(g.destino) && ehNumero(g.destino[0]) && ehNumero(g.destino[1]) &&
        (lance === null || lance === undefined || (typeof lance.id === "string" &&
          (lance.o === null || (Array.isArray(lance.o) && lance.o.length === 3 && lance.o.every(ehNumero)))));
      if (!ok) { foraGranadas++; return; }
      var real = lance && bib[lance.id];
      var dados = { granada: novoId(), arma: g.arma, passo: passo };
      if (real) {
        dados.origem = real.origem.slice(0, 2); dados.destino = real.destino.slice(0, 2);
        dados.nivel = nivelDoZ(real.origem[2]); dados.arremesso = real;
      } else if (lance && lance.o) {
        dados.origem = lance.o.slice(0, 2); dados.destino = [g.destino[0], g.destino[1]];
        dados.nivel = nivelDoZ(lance.o[2]); dados.arremesso = null;
      } else {
        dados.origem = [g.destino[0], g.destino[1]]; dados.destino = [g.destino[0], g.destino[1]];
        dados.nivel = 0; dados.arremesso = null; dados.origem_desconhecida = true;
      }
      emite("cria_granada", dados, false);
    });

    if (retrato && retrato.round !== undefined) {
      // "match_05 · round 9 · 1:12 · 4v3" -- o placar de vivos é TR v CT
      var titulo = (retrato.partida ? retrato.partida + " · " : "") + "round " + retrato.round +
        (retrato.relogio ? " · " + retrato.relogio : "");
      if (S.doc.origem) { var v = placarDeVivos(S.doc.origem); titulo += " · " + v.t + "v" + v.ct; }
      emite("renomeia", { titulo: titulo }, false);
    }
    gravaAgora();   // grava ANTES do aviso: gravar com sucesso limpa o aviso
    var avisos = [];
    if (validos.length !== jogadores.length) {
      avisos.push((jogadores.length - validos.length) + " jogador(es) do instante não puderam ser lidos e ficaram de fora.");
    }
    if (foraGranadas) avisos.push(foraGranadas + " granada(s) do instante não puderam ser lidas e ficaram de fora.");
    if (avisos.length) S.aviso = avisos.join(" ");
    atualizaTudo();
  }

  /** A tática do ROUND INTEIRO do replay (#round=..., fase 9): o caminho real
      de cada jogador, a saída na morte, as granadas com horário, arremessador e
      a ligação ao arremesso real, e o plant. Tudo isso é a base real (não
      desfazível); a tática abre PARADA no instante em que o replay estava. Dado
      que não fecha fica de fora com aviso, como no instante. */
  function criaDoRound(r) {
    var hz = r && ehNumero(r.hz) && r.hz > 0 ? r.hz : null;
    var inst = r && r.instante && typeof r.instante === "object" ? r.instante : {};
    var jogadores = r && Array.isArray(r.jogadores) ? r.jogadores : [];
    function ponto(q) {
      return Array.isArray(q) && q.length === 5 && q.every(ehNumero) && ehInteiro(q[4]) && q[4] >= 0 && q[4] < ANDARES.length;
    }
    var validos = hz === null ? [] : jogadores.filter(function (j) {
      return j && typeof j.nome === "string" && j.nome && LADOS.indexOf(j.lado) >= 0 &&
        Array.isArray(j.pontos) && j.pontos.length && j.pontos.every(ponto) &&
        (j.morte === null || (ehNumero(j.morte) && j.morte > j.pontos[j.pontos.length - 1][0]));
    });
    novaTatica();
    var elenco = jogadores.filter(function (j) { return j && typeof j.nome === "string" && j.nome && LADOS.indexOf(j.lado) >= 0; })
      .map(function (j) { return { nome: j.nome.slice(0, 32), lado: j.lado }; });
    var nomes = {};
    elenco.forEach(function (j) { nomes[j.nome] = j.lado; });
    var mortos = Array.isArray(inst.mortos) ? inst.mortos.filter(function (m) {
      return m && nomes[m.nome] === m.lado && ehInteiro(m.ordem) && m.ordem >= 1;
    }).map(function (m) { return { nome: m.nome, lado: m.lado, ordem: m.ordem }; }) : [];
    var origem = { partida: String(r && r.partida || ""), round: r && r.round, quadro: inst.quadro,
                   relogio: String(inst.relogio || ""), elenco: elenco, mortos: mortos };
    bancoDe = null;
    var passo = passoAtual(), pecaDe = {}, funcoes = (r && r.funcoes) || {};
    function yawDe(d) { return ((d % 360) + 360) % 360; }
    function tDe(f) { return Math.round(f / hz * 1000) / 1000; }
    validos.forEach(function (j) {
      var pid = novoId(), p0 = j.pontos[0];
      pecaDe[j.nome] = { id: pid, pontos: j.pontos };
      emite("cria_peca", { peca: pid, lado: j.lado, rotulo: j.nome.slice(0, 32), passo: passo,
                           x: p0[1], y: p0[2], nivel: p0[4], yaw: yawDe(p0[3]) }, false);
      if (M3 && typeof funcoes[j.nome] === "string" && M3.FUNCOES.indexOf(funcoes[j.nome]) >= 0) {
        emite("define_funcao", { peca: pid, funcao: funcoes[j.nome] }, false);
      }
      var resto = j.pontos.slice(1).map(function (q) {
        return { t: tDe(q[0]), x: q[1], y: q[2], nivel: q[4], yaw: yawDe(q[3]) };
      });
      if (j.morte !== null) {
        var u = j.pontos[j.pontos.length - 1];
        resto.push({ t: tDe(j.morte), x: u[1], y: u[2], nivel: u[4], fora: true, morte: true });
      }
      if (resto.length) emite("cria_caminho", { peca: pid, pontos: resto }, false);
    });
    // onde o jogador estava num quadro (para o andar da granada e do plant)
    function nivelEm(nome, f) {
      var p = pecaDe[nome];
      if (!p) return 0;
      var n = p.pontos[0][4];
      p.pontos.forEach(function (q) { if (q[0] <= f) n = q[4]; });
      return n;
    }
    var bib = {};
    ((cfg.biblioteca && cfg.biblioteca.arremessos) || []).forEach(function (a) { bib[a.id] = a; });
    var granadas = r && Array.isArray(r.granadas) ? r.granadas : [], foraGranadas = 0;
    granadas.forEach(function (g) {
      var ok = g && ARMAS.indexOf(g.k) >= 0 && ehNumero(g.f) && g.f >= 0 && Array.isArray(g.o) && Array.isArray(g.d) &&
        g.o.length === 2 && g.d.length === 2 && g.o.concat(g.d).every(ehNumero);
      if (!ok || hz === null) { foraGranadas++; return; }
      var quem = pecaDe[g.by], real = (typeof g.l === "string" && bib[g.l]) || null;
      // a origem: o arremesso real da biblioteca; sem ele, a soltura gravada
      // pelo export; sem ela, o começo da trajetória (como no instante)
      var origem = real ? real.origem.slice(0, 2)
        : (Array.isArray(g.lo) && g.lo.length === 2 && g.lo.every(ehNumero) ? g.lo.slice() : g.o.slice());
      var dados = { granada: novoId(), arma: g.k, passo: passo, t: tDe(g.f), origem: origem, destino: g.d.slice(),
                    nivel: real ? nivelDoZ(real.origem[2]) : nivelEm(g.by, g.f), arremesso: real };
      if (quem) dados.jogador = quem.id;
      // voo e efeito medidos no replay: a granada fica ativa nos mesmos quadros
      if (ehNumero(g.v) && g.v >= 0) dados.voo_s = Math.round(g.v / hz * 1000) / 1000;
      if (ehNumero(g.e) && g.e >= 0) dados.efeito_s = Math.round(g.e / hz * 1000) / 1000;
      emite("cria_granada", dados, false);
    });
    if (r && r.bomba && hz !== null && ehNumero(r.bomba.f) && ehNumero(r.bomba.x) && ehNumero(r.bomba.y)) {
      emite("planta_bomba", { t: tDe(r.bomba.f), x: r.bomba.x, y: r.bomba.y, nivel: nivelEm(r.bomba.por, r.bomba.f) }, false);
    }
    var titulo = (origem.partida ? origem.partida + " · " : "") + "round " + origem.round +
      (origem.relogio ? " · " + origem.relogio : "");
    var v = placarDeVivos(origem);
    emite("renomeia", { titulo: titulo + " · " + v.t + "v" + v.ct }, false);
    // a base real termina aqui: o que vier depois é do usuário
    origem.base_real = S.doc.contador;
    if (!problemasDaOrigem(origem).length) S.doc.origem = origem;
    bancoDe = null;   // o banco é refeito com o elenco do round (os nomes reais)
    S.pilhaDesfazer = []; S.pilhaRefazer = [];
    reaplica();
    // abre parada no instante do replay
    S.t = hz !== null && ehInteiro(inst.quadro) ? Math.min(limiteDoTempo(), Math.round(inst.quadro / hz * 100) / 100) : 0;
    S.passo = marcoQueContem(S.t);
    gravaAgora();
    var avisos = [];
    if (validos.length !== jogadores.length) {
      avisos.push((jogadores.length - validos.length) + " jogador(es) do round não puderam ser lidos e ficaram de fora.");
    }
    if (foraGranadas) avisos.push(foraGranadas + " granada(s) do round não puderam ser lidas e ficaram de fora.");
    if (!S.doc.origem) avisos.push("A origem do round não pôde ser lida.");
    if (avisos.length) S.aviso = avisos.join(" ");
    atualizaTudo();
  }

  function escolheFerramenta(id) {
    confirmaGiro();
    if (S.editor) fechaEditorTexto(true);
    S.acao = null; S.busca = null; S.sugestao = null;
    if (id === "buscar") { S.ferramenta = "mover"; S.acao = { tipo: "busca", arma: S.arma }; }
    else if (id === "granada") { S.ferramenta = "mover"; S.acao = { tipo: "granada", arma: S.arma, de: null, origem: null, legado: true }; }
    else S.ferramenta = id;
    atualizaTudo();
  }

  function init(opcoes) {
    cfg = opcoes;
    M3 = cfg.modelo3;
    LUGARES = cfg.lugares || null;
    TEXTOS = cfg.textos || {};
    Armazem = opcoes.armazem || ArmazemDoNavegador("prancheta:");
    ANDARES = andaresDoRadar(cfg.radar);
    CENTRO = centroDoRadar(cfg.radar);
    cv = $("pr-mapa"); ctx = cv.getContext("2d");
    // anel duplo em peça e glifo (entrega-sala-de-demo §4.1), como no replay desde a design-B2
    MapCore.defineAnelDuplo(true);
    imgs = ANDARES.map(function (a, i) {
      var src = i === 0 ? cfg.radar.image : (cfg.radar.layers || {})[a.nome];
      var im = new Image();
      im.onload = function () { desenha(); };
      if (src) im.src = src;
      return im;
    });
    var armazemCores = MapCore.criaArmazem();
    var rec = MapCore.lerJson(armazemCores.le("localStorage", CHAVE_RECENTES));
    if (Array.isArray(rec)) S.recentes = rec.map(MapCore.normalizaCor).filter(Boolean).slice(0, MAX_RECENTES);
    if (S.recentes.length) S.cor = S.recentes[0];

    montaLateral();
    montaBarra();
    montaPlayer();
    if (M3) montaLinhaDoTempo();
    montaBanco();
    cv.addEventListener("pointerdown", pointerDown);
    // o botão direito no mapa é "virar para lá": sem o menu do navegador
    cv.addEventListener("contextmenu", function (e) { e.preventDefault(); });
    cv.addEventListener("pointermove", pointerMove);
    cv.addEventListener("pointerup", pointerUp);
    cv.addEventListener("pointercancel", function () { S.arrasto = null; S.tracando = null; S.pan = null; S.toque = null; desenha(); });
    cv.addEventListener("wheel", roda, { passive: false });

    if (!temBiblioteca()) {
      // sem partida deste mapa no corpus, não há arremesso real para buscar
      var buscar = document.querySelector('aside [data-ferramenta="buscar"]');
      buscar.disabled = true;
      var nomeDoMapa = ((cfg.mapas || []).filter(function (m) { return m.mapa === cfg.mapa; })[0] || {}).nome || cfg.mapa;
      var motivo = "Sem arremessos reais neste mapa: não há partidas dele no corpus.";
      buscar.title = motivo;
      $("pr-sem-biblioteca").textContent = motivo;
      $("pr-sem-biblioteca").hidden = false;
      // aviso info no cabeçalho (§14): dá para montar a tática; o que fica desligado e por quê
      var aviso = $("pr-aviso-mapa");
      if (aviso) {
        aviso.textContent = nomeDoMapa + " não tem partidas no corpus. Dá para montar a tática; \u201cBuscar arremesso " +
          "real\u201d e \u201cRound real\u201d ficam desligados porque não há arremesso nem round gravado deste mapa.";
        aviso.hidden = false;
      }
      $("pr-raio").disabled = true; $("pr-so-parado").disabled = true;
    } else if (!bibliotecaPronta()) {
      buscaEsperando(true);
    }
    $("pr-raio").value = String(S.raioBusca);
    $("pr-raio").addEventListener("input", function () {
      S.raioBusca = +this.value; $("pr-raio-valor").textContent = this.value + "u";
      if (S.busca) busca(S.busca.ponto, S.busca.arma);
    });
    $("pr-raio-valor").textContent = S.raioBusca + "u";
    $("pr-so-parado").addEventListener("change", function () {
      S.soParado = this.checked;
      if (S.busca) busca(S.busca.ponto, S.busca.arma);
    });

    $("pr-nova").addEventListener("click", function () { gravaAgora(); novaTatica(); });
    $("pr-taticas").addEventListener("change", function () {
      // lê a escolha ANTES de gravar: gravar reconstrói a lista com a atual marcada
      var escolhida = this.value;
      if (escolhida !== S.doc.id) { gravaAgora(); abre(escolhida); }
    });
    $("pr-titulo").addEventListener("change", function () { emite("renomeia", { titulo: this.value.trim() }); });
    $("pr-passo-titulo").addEventListener("change", function () {
      emite("renomeia_passo", { passo: passoAtual(), titulo: this.value.trim() });
    });
    $("pr-passo-duracao").addEventListener("change", function () {
      var s = +this.value;
      if (s > 0) emite("define_duracao", { passo: passoAtual(), segundos: s });
      else atualizaPassos();
    });
    $("pr-remove-passo").addEventListener("click", function () {
      if (S.estado.passos.length <= 1) return;
      emite("remove_passo", { passo: passoAtual() });
      S.passo = Math.max(0, S.passo - 1); atualizaTudo();
    });
    $("pr-apaga").addEventListener("click", function () {
      if (!S.doc || !window.confirm("Apagar esta tática deste navegador?")) return;
      Armazem.apaga(S.doc.id);
      var resto = Armazem.lista(cfg.mapa);
      if (!(resto.length && abre(resto[0].id))) novaTatica();
    });
    $("pr-exporta").addEventListener("click", exporta);
    var arquivo = $("pr-arquivo");
    $("pr-importa").addEventListener("click", function () { arquivo.click(); });
    arquivo.addEventListener("change", function () {
      var f = arquivo.files && arquivo.files[0]; if (!f) return;
      var leitor = new FileReader();
      leitor.onload = function () { importaTexto(String(leitor.result)); arquivo.value = ""; };
      leitor.readAsText(f);
    });
    $("pr-autor").value = Armazem.autor() || "";
    $("pr-autor").addEventListener("change", function () { Armazem.autor(this.value.trim()); });

    var palco = $("pr-palco");
    palco.addEventListener("pointerenter", function () { S.sobreMapa = true; });
    palco.addEventListener("pointerleave", function () { S.sobreMapa = false; });
    document.addEventListener("keydown", function (e) {
      if (S.reproducao) {
        // os atalhos do replay, com a mesma guarda de foco
        if (e.ctrlKey || e.metaKey || e.altKey) return;
        var foco = document.activeElement;
        if (foco && (/^(INPUT|SELECT|TEXTAREA|BUTTON)$/.test(foco.tagName) || foco.isContentEditable)) return;
        if (e.key === " " || e.key === "Spacebar") { e.preventDefault(); toca(!S.reproducao.tocando); }
        else if (e.key === "ArrowRight") { e.preventDefault(); vaiParaPasso(1); }
        else if (e.key === "ArrowLeft") { e.preventDefault(); vaiParaPasso(-1); }
        else if (e.key === "]") { e.preventDefault(); mudaVelocidade(1); }
        else if (e.key === "[") { e.preventDefault(); mudaVelocidade(-1); }
        else if (e.key === "Escape") { e.preventDefault(); editaAqui(); }
        return;
      }
      if (/^(INPUT|TEXTAREA|SELECT)$/.test((e.target || {}).tagName || "") || (e.target || {}).isContentEditable) return;
      if (S.ferramenta === "granada_desenho" && !e.ctrlKey && !e.metaKey && !e.altKey) {
        var passoC = PASSO_CURSOR_PX * (e.shiftKey ? 4 : 1), dC = null;
        if (e.key === "ArrowLeft") dC = [-passoC, 0]; else if (e.key === "ArrowRight") dC = [passoC, 0];
        else if (e.key === "ArrowUp") dC = [0, -passoC]; else if (e.key === "ArrowDown") dC = [0, passoC];
        if (dC || e.key === "Enter") {
          e.preventDefault();
          if (!S.cursorDesenho) S.cursorDesenho = [cfg.radar.width / 2, cfg.radar.height / 2];
          if (dC) {
            S.cursorDesenho = [Math.max(0, Math.min(cfg.radar.width, S.cursorDesenho[0] + dC[0])),
                               Math.max(0, Math.min(cfg.radar.height, S.cursorDesenho[1] + dC[1]))];
            desenha();
          } else carimbaGranada(S.cursorDesenho, pixelParaJogo(S.cursorDesenho[0], S.cursorDesenho[1]));
          return;
        }
      }
      if (S.caminho && !S.acao) {
        if (e.key === "Enter") { e.preventDefault(); concluiCaminho(); return; }
        if (e.key === "Backspace") {
          e.preventDefault();
          if (S.caminho.pontos.length) { S.caminho.pontos.pop(); atualizaDica(); desenha(); }
          return;
        }
      }
      if (e.code === "Space" && (S.sobreMapa || S.espaco) && !e.ctrlKey && !e.metaKey) {
        e.preventDefault();
        if (!S.espaco) { S.espaco = true; palco.classList.add("pr-pan"); }
        return;
      }
      if (e.altKey) return;
      var tecla = teclaDoEvento(e);
      var atalho = ATALHOS.filter(function (a) { return a.tecla === tecla && a.fn; })[0];
      if (!atalho) return;
      e.preventDefault();
      atalho.fn(e);
    });
    document.addEventListener("keyup", function (e) {
      if (e.code === "Space" && S.espaco) { S.espaco = false; palco.classList.remove("pr-pan"); S.pan = null; }
    });
    window.addEventListener("blur", function () { S.espaco = false; palco.classList.remove("pr-pan"); });
    // duplo clique conclui o caminho: o segundo clique já marcou um ponto em
    // cima do primeiro, e esse ponto repetido sai antes de concluir
    cv.addEventListener("dblclick", function () {
      var c = S.caminho;
      if (!c || S.acao) return;
      var n = c.pontos.length;
      if (n >= 2 && c.pontos[n - 1].x === c.pontos[n - 2].x && c.pontos[n - 1].y === c.pontos[n - 2].y) c.pontos.pop();
      concluiCaminho();
    });
    $("pr-cabecote").addEventListener("input", function () { defineTempo(parseFloat($("pr-cabecote").value) || 0); });

    // Todos os gatilhos de tamanho caem na mesma função.
    pedeReprojecao = MapCore.agrupaPorQuadro(reprojeta);
    window.addEventListener("resize", pedeReprojecao);
    document.addEventListener("fullscreenchange", function () { pedeReprojecao(); atualizaBarra(); });
    document.addEventListener("webkitfullscreenchange", function () { pedeReprojecao(); atualizaBarra(); });
    MapCore.vigiaDensidade(pedeReprojecao);
    // o que fica acima do mapa também é vigiado: se mudar de altura por outro motivo (fonte que chega tarde, o aviso do
    // mapa), o mapa se reajusta uma vez, no quadro seguinte
    if (window.ResizeObserver) {
      var vigia = new ResizeObserver(pedeReprojecao);
      ["pr-tela", "pr-barra", "pr-dica-estado"].forEach(function (id) { if ($(id)) vigia.observe($(id)); });
      [".pr-cab", ".site-topo"].forEach(function (s) { var n = document.querySelector(s); if (n) vigia.observe(n); });
    }
    if (document.fonts && document.fonts.ready) document.fonts.ready.then(function () { pedeReprojecao(); });
    window.addEventListener("pagehide", function () { confirmaGiro(); gravaAgora(); });

    // Abre LIMPA ("Criar tática" chega com ?nova), ou a tática aberta nesta aba.
    var nova = /[?&]nova\b/.test(location.search);
    if (nova && window.history && history.replaceState) history.replaceState(null, "", location.pathname);
    var aberta = Armazem.aberta(cfg.mapa);
    var instante = /^#instante=/.test(location.hash) ? location.hash.slice("#instante=".length) : null;
    // o round inteiro (fase 9): consumido como o instante, sem deixar rastro no endereço
    var round = /^#round=/.test(location.hash) ? location.hash.slice("#round=".length) : null;
    if (round !== null && window.history && history.replaceState) history.replaceState(null, "", location.pathname);
    if (instante !== null && window.history && history.replaceState) history.replaceState(null, "", location.pathname);
    var retrato = null;
    if (instante !== null) {
      try { retrato = JSON.parse(decodeURIComponent(instante)); } catch (e) { retrato = null; }
    }
    if (round !== null) {
      novaTatica();
      S.carregandoRound = true;
      // o round liga cada granada ao arremesso real: espera a biblioteca, se ela ainda não chegou (cartão 20)
      MapCore.descompactaDaUrl(round).then(function (r) {
        quandoBiblioteca(function () { S.carregandoRound = false; criaDoRound(r); reprojeta(); });
      }, function () { S.carregandoRound = false; S.aviso = "O round do replay não pôde ser lido."; atualizaAviso(); });
    } else if (instante !== null) {
      if (retrato && bibliotecaPronta()) criaDoInstante(retrato);
      else if (retrato) {
        // como o round: uma tática vazia (não é gravada) até a biblioteca chegar, e então a do instante
        novaTatica();
        quandoBiblioteca(function () { criaDoInstante(retrato); reprojeta(); });
      } else { novaTatica(); S.aviso = "O instante do replay não pôde ser lido."; atualizaAviso(); }
    } else if (nova || !(aberta && abre(aberta))) novaTatica();
    reprojeta();
    if (ganchos.aoIniciar) ganchos.aoIniciar();
    if (!bibliotecaPronta()) carregaBiblioteca();
  }

  /** Enquanto a biblioteca carrega, "Buscar arremesso real" e os filtros da busca ficam desligados, com o motivo. */
  function buscaEsperando(sim) {
    var buscar = document.querySelector('aside [data-ferramenta="buscar"]');
    if (buscar) {
      if (sim) { buscar.dataset.titulo = buscar.title; buscar.title = "Carregando os arremessos reais deste mapa\u2026"; }
      else if (buscar.dataset.titulo !== undefined) buscar.title = buscar.dataset.titulo;   // o title de sempre volta
      buscar.disabled = sim;
    }
    $("pr-raio").disabled = sim; $("pr-so-parado").disabled = sim;
  }

  /** O arquivo da biblioteca (cartão 20): um <script> próprio, que funciona também com a página aberta como arquivo
      (file://, onde fetch não funciona); ele chama Prancheta.recebeBiblioteca. Se não carregar, a prancheta segue sem
      arremesso real, como num mapa sem corpus, e diz por quê. */
  function carregaBiblioteca() {
    var s = document.createElement("script");
    s.src = cfg.bibliotecaArquivo;
    s.onerror = function () {
      cfg.bibliotecaArquivo = null;
      var motivo = "Os arremessos reais não carregaram: recarregue a página para buscar arremesso real.";
      var buscar = document.querySelector('aside [data-ferramenta="buscar"]');
      if (buscar) { buscar.disabled = true; buscar.title = motivo; }
      $("pr-sem-biblioteca").textContent = motivo;
      $("pr-sem-biblioteca").hidden = false;
      var fila = esperandoBiblioteca; esperandoBiblioteca = [];
      fila.forEach(function (fn) { fn(); });
    };
    document.body.appendChild(s);
  }

  /** A biblioteca chegou (o arquivo chama esta função): entra no cfg, a busca liga e o que esperava por ela roda. */
  function recebeBiblioteca(b) {
    if (!cfg || cfg.biblioteca || !b) return;
    cfg.biblioteca = b;
    buscaEsperando(false);
    var fila = esperandoBiblioteca; esperandoBiblioteca = [];
    fila.forEach(function (fn) { fn(); });
    atualizaTudo();
  }

