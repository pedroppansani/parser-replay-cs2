/* =========================================================================
   Camada de desenho sobre o mapa, tela cheia e zoom.

   A DECISAO QUE SUSTENTA TUDO: todo traco e guardado em COORDENADAS DE JOGO,
   nunca em pixels de tela. O tamanho da tela muda o tempo inteiro -- janela
   redimensionada, tela cheia, zoom, outro monitor -- e pixel guardado deixa de
   apontar para o lugar certo no instante em que qualquer uma dessas coisas
   acontece. Guardando unidade de jogo, uma seta apontando pro fundo do bomb
   continua apontando pro fundo do bomb em qualquer tamanho.

   Consequencia pratica, e ela e o contrario do que parece mais facil: ao entrar
   e sair de tela cheia NAO se escala a imagem pronta -- reprojetam-se as
   coordenadas. A conta e a mesma de scripts/prepare_radar.py e de
   metrics/annotations.py, nos dois sentidos.

   Este arquivo e separado do template de proposito: o template ja esta grande
   demais, e a camada de desenho nao tem nada a ver com o resto da pagina.
   ========================================================================= */
window.MapAnnotations = (function () {
  "use strict";

  // Formato do arquivo -- o mesmo de metrics/annotations.py. Se os dois
  // divergirem, um arquivo exportado aqui nao abre la.
  var FORMATO = 1;

  // Paleta ja validada do projeto (decisao 10). Nao e uma paleta nova: sao as
  // cores do dashboard que mantem contraste sobre o radar claro.
  var CORES = [
    { id: "t", hex: "#eb6834", nome: "laranja" },
    { id: "ct", hex: "#2a78d6", nome: "azul" },
    { id: "aqua", hex: "#1baf7a", nome: "verde" },
    { id: "tinta", hex: "#0f1620", nome: "preto" },
    { id: "papel", hex: "#ffffff", nome: "branco" }
  ];
  // Tres niveis. Mais que isso vira menu e ninguem usa.
  var ESPESSURAS = [2, 4, 7];

  var FERRAMENTAS = [
    { id: "caneta", rotulo: "Caneta", tecla: "1" },
    { id: "seta", rotulo: "Seta", tecla: "2" },
    { id: "linha", rotulo: "Linha", tecla: "3" },
    { id: "retangulo", rotulo: "Retangulo", tecla: "4" },
    { id: "elipse", rotulo: "Elipse", tecla: "5" },
    { id: "texto", rotulo: "Texto", tecla: "6" },
    { id: "borracha", rotulo: "Borracha", tecla: "7" }
  ];

  // Raio de acerto da borracha, em pixels do radar. Ela apaga o TRACO INTEIRO
  // sob o cursor, nao pixel a pixel: apagar pedaco de seta deixa meia seta, que
  // e pior que nao apagar.
  var RAIO_BORRACHA = 10;

  // Quanto tempo os controles ficam na tela depois do ultimo movimento, em tela
  // cheia. Curto o bastante pra nao tampar o mapa, longo o bastante pra dar
  // tempo de mirar um botao.
  var MS_ATE_RECUAR = 2600;

  var ZOOM_MIN = 1, ZOOM_MAX = 6, ZOOM_PASSO = 1.18;

  var S = {
    pronto: false,
    ligado: false,          // modo de desenho
    ferramenta: "seta",
    cor: CORES[0].hex,
    espessura: ESPESSURAS[1],
    soDepois: false,        // o traco aparece so a partir do instante em que foi feito
    round: null,
    pos: 0,
    doc: null,
    refazer: [],
    tracando: null,
    view: { zoom: 1, panX: 0, panY: 0 },
    visiveisAntes: -1
  };

  var opts = null, camada = null, rascunho = null, ctxC = null, ctxR = null;

  /* ---------------------------------------------------------------------
     Projecao. A mesma conta do resto do projeto, nos dois sentidos.
     --------------------------------------------------------------------- */
  function jogoParaPixel(x, y) {
    var r = opts.radar;
    return [(x - r.origin_x) * r.scale_px_per_unit, (r.origin_y - y) * r.scale_px_per_unit];
  }
  function pixelParaJogo(px, py) {
    var r = opts.radar;
    return [px / r.scale_px_per_unit + r.origin_x, r.origin_y - py / r.scale_px_per_unit];
  }

  /** Ponteiro na tela -> pixel do radar, desfazendo zoom, pan e o tamanho CSS. */
  function eventoParaPixel(e) {
    var caixa = camada.getBoundingClientRect();
    // O canvas tem resolucao interna fixa e e escalado por CSS; a razao entre as
    // duas e o que converte pixel de tela em pixel de radar.
    var k = camada.width / (caixa.width * (window.devicePixelRatio || 1));
    var px = (e.clientX - caixa.left) * (window.devicePixelRatio || 1) * k;
    var py = (e.clientY - caixa.top) * (window.devicePixelRatio || 1) * k;
    // desfaz a transformacao de visualizacao
    return [(px - S.view.panX) / S.view.zoom, (py - S.view.panY) / S.view.zoom];
  }

  function eventoParaJogo(e) {
    var p = eventoParaPixel(e);
    return pixelParaJogo(p[0], p[1]);
  }

  /** Aplica zoom e pan a um contexto. O mapa usa a MESMA, senao os dois se
      descolam e a seta aponta pro lugar errado. */
  function applyView(ctx) {
    ctx.setTransform(S.view.zoom, 0, 0, S.view.zoom, S.view.panX, S.view.panY);
  }

  /* ---------------------------------------------------------------------
     Documento
     --------------------------------------------------------------------- */
  function chaveLocal() { return "anot:" + opts.matchId + ":" + opts.calibracao; }

  function docVazio() {
    return {
      formato: FORMATO,
      match_id: opts.matchId,
      mapa: opts.radar.map || null,
      // A calibracao vai junto: ela foi AJUSTADA, nao e constante do jogo. Se
      // mudar depois, da pra saber que as anotacoes antigas precisam ser
      // reprojetadas em vez de saírem alguns pixels fora em silencio.
      calibracao: opts.calibracao,
      rounds: {}
    };
  }

  function carrega() {
    try {
      var cru = window.localStorage.getItem(chaveLocal());
      if (cru) {
        var d = JSON.parse(cru);
        if (d && d.formato === FORMATO && d.calibracao === opts.calibracao) return d;
      }
    } catch (err) { /* aba anonima, cookies bloqueados: segue sem persistir */ }
    return docVazio();
  }

  function salva() {
    try { window.localStorage.setItem(chaveLocal(), JSON.stringify(S.doc)); }
    catch (err) { /* sem espaco ou sem permissao: o desenho da sessao continua */ }
  }

  function tracosDoRound() {
    if (S.round == null) return [];
    return S.doc.rounds[String(S.round)] || [];
  }

  function gravaTracos(lista) {
    S.doc.rounds[String(S.round)] = lista;
    salva();
  }

  /* ---------------------------------------------------------------------
     Desenho
     --------------------------------------------------------------------- */
  function caminhoDoTraco(ctx, t) {
    var p = t.pontos.map(function (g) { return jogoParaPixel(g[0], g[1]); });
    ctx.lineWidth = t.espessura;
    ctx.strokeStyle = t.cor;
    ctx.fillStyle = t.cor;
    ctx.lineJoin = "round";
    ctx.lineCap = "round";

    if (t.ferramenta === "texto") {
      ctx.font = (t.espessura * 5 + 10) + "px 'DM Sans', system-ui, sans-serif";
      ctx.textBaseline = "middle";
      ctx.fillText(t.texto || "", p[0][0], p[0][1]);
      return;
    }
    if (p.length < 2) return;

    var a = p[0], b = p[p.length - 1];
    ctx.beginPath();
    if (t.ferramenta === "caneta") {
      ctx.moveTo(p[0][0], p[0][1]);
      for (var i = 1; i < p.length; i++) ctx.lineTo(p[i][0], p[i][1]);
      ctx.stroke();
    } else if (t.ferramenta === "linha") {
      ctx.moveTo(a[0], a[1]); ctx.lineTo(b[0], b[1]); ctx.stroke();
    } else if (t.ferramenta === "seta") {
      desenhaSeta(ctx, a, b, t.espessura);
    } else if (t.ferramenta === "retangulo") {
      ctx.rect(a[0], a[1], b[0] - a[0], b[1] - a[1]); ctx.stroke();
    } else if (t.ferramenta === "elipse") {
      var cx = (a[0] + b[0]) / 2, cy = (a[1] + b[1]) / 2;
      ctx.ellipse(cx, cy, Math.abs(b[0] - a[0]) / 2, Math.abs(b[1] - a[1]) / 2, 0, 0, Math.PI * 2);
      ctx.stroke();
    }
  }

  /** A seta e ferramenta de primeira classe, nao linha com enfeite: a cabeca
      cresce com a espessura e fica solida, pra leitura funcionar de longe. */
  function desenhaSeta(ctx, a, b, esp) {
    var ang = Math.atan2(b[1] - a[1], b[0] - a[0]);
    var cab = Math.max(11, esp * 3.4);
    var fim = [b[0] - Math.cos(ang) * cab * 0.55, b[1] - Math.sin(ang) * cab * 0.55];
    ctx.moveTo(a[0], a[1]); ctx.lineTo(fim[0], fim[1]); ctx.stroke();
    ctx.beginPath();
    ctx.moveTo(b[0], b[1]);
    ctx.lineTo(b[0] - Math.cos(ang - 0.42) * cab, b[1] - Math.sin(ang - 0.42) * cab);
    ctx.lineTo(b[0] - Math.cos(ang + 0.42) * cab, b[1] - Math.sin(ang + 0.42) * cab);
    ctx.closePath();
    ctx.fill();
  }

  function visiveis() {
    return tracosDoRound().filter(function (t) {
      return !t.so_depois || S.pos >= (t.pos || 0);
    });
  }

  /** Redesenha a camada consolidada. Chamada so quando o conjunto visivel muda,
      nao a cada quadro -- o mapa se movendo nao pode forcar redesenho dos
      tracos, e desenhar nao pode forcar redesenho do mapa. */
  function repinta() {
    if (!S.pronto) return;
    ctxC.setTransform(1, 0, 0, 1, 0, 0);
    ctxC.clearRect(0, 0, camada.width, camada.height);
    applyView(ctxC);
    visiveis().forEach(function (t) { caminhoDoTraco(ctxC, t); });
  }

  function repintaRascunho() {
    ctxR.setTransform(1, 0, 0, 1, 0, 0);
    ctxR.clearRect(0, 0, rascunho.width, rascunho.height);
    if (!S.tracando) return;
    applyView(ctxR);
    caminhoDoTraco(ctxR, S.tracando);
  }

  /* ---------------------------------------------------------------------
     Entrada por ponteiro (mouse, toque e caneta com o mesmo codigo)
     --------------------------------------------------------------------- */
  function comecou(e) {
    if (!S.ligado) return;
    camada.setPointerCapture(e.pointerId);
    // Ninguem consegue desenhar em cima de boneco andando.
    if (opts.pause) opts.pause();

    var g = eventoParaJogo(e);

    if (S.ferramenta === "borracha") { apaga(g); return; }

    if (S.ferramenta === "texto") {
      var txt = window.prompt("Texto da anotacao:");
      if (txt) {
        empilha({
          ferramenta: "texto", texto: txt, pontos: [g],
          cor: S.cor, espessura: S.espessura,
          so_depois: S.soDepois, pos: S.pos
        });
      }
      return;
    }

    S.tracando = {
      ferramenta: S.ferramenta, pontos: [g, g],
      cor: S.cor, espessura: S.espessura,
      so_depois: S.soDepois, pos: S.pos
    };
    repintaRascunho();
  }

  function moveu(e) {
    if (!S.ligado || !S.tracando) return;
    var g = eventoParaJogo(e);
    if (S.tracando.ferramenta === "caneta") S.tracando.pontos.push(g);
    else S.tracando.pontos[1] = g;
    // O traco em andamento vive na camada de rascunho; so ao soltar ele e
    // consolidado. Assim um traco longo nao repinta o desenho inteiro a cada
    // movimento do ponteiro.
    repintaRascunho();
  }

  function soltou(e) {
    if (!S.ligado || !S.tracando) return;
    var t = S.tracando;
    S.tracando = null;
    repintaRascunho();
    // clique seco com ferramenta de duas pontas nao vira traco
    var a = t.pontos[0], b = t.pontos[t.pontos.length - 1];
    if (t.ferramenta !== "caneta" && Math.abs(a[0] - b[0]) < 8 && Math.abs(a[1] - b[1]) < 8) return;
    empilha(t);
  }

  function empilha(t) {
    var lista = tracosDoRound().slice();
    lista.push(t);
    gravaTracos(lista);
    S.refazer = [];   // ramo novo: o que foi desfeito deixa de ser refazivel
    repinta();
    atualizaBotoes();
  }

  function apaga(g) {
    var alvo = jogoParaPixel(g[0], g[1]);
    var lista = tracosDoRound();
    for (var i = lista.length - 1; i >= 0; i--) {
      if (encosta(lista[i], alvo)) {
        var nova = lista.slice();
        nova.splice(i, 1);
        gravaTracos(nova);
        S.refazer = [];
        repinta();
        atualizaBotoes();
        return;
      }
    }
  }

  function encosta(t, alvo) {
    var pts = t.pontos.map(function (g) { return jogoParaPixel(g[0], g[1]); });
    var r = RAIO_BORRACHA + t.espessura;
    if (t.ferramenta === "texto" || pts.length === 1) {
      return Math.hypot(pts[0][0] - alvo[0], pts[0][1] - alvo[1]) <= r * 3;
    }
    if (t.ferramenta === "retangulo" || t.ferramenta === "elipse") {
      var x0 = Math.min(pts[0][0], pts[1][0]), x1 = Math.max(pts[0][0], pts[1][0]);
      var y0 = Math.min(pts[0][1], pts[1][1]), y1 = Math.max(pts[0][1], pts[1][1]);
      return alvo[0] >= x0 - r && alvo[0] <= x1 + r && alvo[1] >= y0 - r && alvo[1] <= y1 + r;
    }
    for (var i = 0; i < pts.length - 1; i++) {
      if (distanciaAoSegmento(alvo, pts[i], pts[i + 1]) <= r) return true;
    }
    return false;
  }

  function distanciaAoSegmento(p, a, b) {
    var dx = b[0] - a[0], dy = b[1] - a[1];
    var L = dx * dx + dy * dy;
    var t = L === 0 ? 0 : Math.max(0, Math.min(1, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / L));
    return Math.hypot(p[0] - (a[0] + t * dx), p[1] - (a[1] + t * dy));
  }

  /* ---------------------------------------------------------------------
     Desfazer / refazer
     --------------------------------------------------------------------- */
  function desfaz() {
    var lista = tracosDoRound();
    if (!lista.length) return;
    var nova = lista.slice();
    S.refazer.push({ round: S.round, traco: nova.pop() });
    gravaTracos(nova);
    repinta();
    atualizaBotoes();
  }

  function refaz() {
    if (!S.refazer.length) return;
    var topo = S.refazer[S.refazer.length - 1];
    if (topo.round !== S.round) return;  // nao ressuscita traco de outro round
    S.refazer.pop();
    var nova = tracosDoRound().slice();
    nova.push(topo.traco);
    gravaTracos(nova);
    repinta();
    atualizaBotoes();
  }

  function limpa() {
    if (!tracosDoRound().length) return;
    if (!window.confirm("Apagar todos os desenhos deste round?")) return;
    gravaTracos([]);
    S.refazer = [];
    repinta();
    atualizaBotoes();
  }

  /* ---------------------------------------------------------------------
     Dimensionamento. PROPORCAO preservada e devicePixelRatio respeitado.
     --------------------------------------------------------------------- */

  /** O mapa cresce ate o limite da MENOR dimensao e fica centralizado; o
      excedente vira espaco vazio. Nunca esticado -- ja houve bug de proporcao
      neste projeto (dado em retrato num canvas em paisagem), e esticar e
      exatamente o que produz aquilo. */
  function caixaDoMapa(dispW, dispH) {
    var w = opts.radar.width, h = opts.radar.height;
    var escala = Math.min(dispW / w, dispH / h);
    return { largura: w * escala, altura: h * escala, escala: escala };
  }

  /** Redimensiona os canvas. A resolucao INTERNA leva devicePixelRatio junto,
      senao o mapa e os tracos saem borrados em tela de alta densidade -- e o
      traco fino e o primeiro a sofrer. */
  function redimensiona() {
    var dpr = window.devicePixelRatio || 1;
    var alvo = opts.mapCanvas;
    var caixa = alvo.getBoundingClientRect();
    [camada, rascunho].forEach(function (c) {
      c.style.width = caixa.width + "px";
      c.style.height = caixa.height + "px";
      var w = Math.round(opts.radar.width), h = Math.round(opts.radar.height);
      if (c.width !== w || c.height !== h) { c.width = w; c.height = h; }
    });
    // Reprojeta UMA vez, e nao a cada quadro: mudanca de tamanho e evento raro.
    repinta();
    repintaRascunho();
  }

  /* ---------------------------------------------------------------------
     Zoom e pan
     --------------------------------------------------------------------- */
  function aplicaZoom(novo, centroX, centroY) {
    var z0 = S.view.zoom;
    var z = Math.min(ZOOM_MAX, Math.max(ZOOM_MIN, novo));
    if (z === z0) return;
    // mantem o ponto sob o cursor parado enquanto o zoom muda
    S.view.panX = centroX - (centroX - S.view.panX) * (z / z0);
    S.view.panY = centroY - (centroY - S.view.panY) * (z / z0);
    S.view.zoom = z;
    limitaPan();
    pedeRedesenho();
  }

  /** Impede que o mapa escape da area visivel. Sem isso da pra arrastar o mapa
      pra fora e ficar olhando pro vazio sem saber como voltar. */
  function limitaPan() {
    var W = opts.radar.width, H = opts.radar.height;
    var maxX = 0, minX = W - W * S.view.zoom;
    var maxY = 0, minY = H - H * S.view.zoom;
    S.view.panX = Math.min(maxX, Math.max(minX, S.view.panX));
    S.view.panY = Math.min(maxY, Math.max(minY, S.view.panY));
  }

  function pedeRedesenho() {
    repinta();
    repintaRascunho();
    if (opts.redraw) opts.redraw();
    atualizaBotoes();
  }

  function zoomDaRoda(e) {
    if (!e.ctrlKey && !S.ligado && S.view.zoom === 1 && Math.abs(e.deltaY) < 4) return;
    e.preventDefault();
    var p = eventoParaPixel(e);
    var px = p[0] * S.view.zoom + S.view.panX;
    var py = p[1] * S.view.zoom + S.view.panY;
    aplicaZoom(S.view.zoom * (e.deltaY < 0 ? ZOOM_PASSO : 1 / ZOOM_PASSO), px, py);
  }

  var arrastando = null;
  function panComeca(e) {
    // Com o modo de desenho LIGADO o ponteiro desenha; o pan fica no botao do
    // meio, pra nao existir gesto que faz duas coisas.
    if (S.ligado && e.button !== 1) return;
    if (S.view.zoom <= 1) return;
    arrastando = { x: e.clientX, y: e.clientY, panX: S.view.panX, panY: S.view.panY };
    camada.setPointerCapture(e.pointerId);
  }
  function panMove(e) {
    if (!arrastando) return;
    var k = camada.width / camada.getBoundingClientRect().width;
    S.view.panX = arrastando.panX + (e.clientX - arrastando.x) * k;
    S.view.panY = arrastando.panY + (e.clientY - arrastando.y) * k;
    limitaPan();
    pedeRedesenho();
  }
  function panTermina() { arrastando = null; }

  function reseta() {
    S.view = { zoom: 1, panX: 0, panY: 0 };
    pedeRedesenho();
  }

  /* ---------------------------------------------------------------------
     Tela cheia
     --------------------------------------------------------------------- */
  function emTelaCheia() {
    return document.fullscreenElement === opts.palco ||
           document.webkitFullscreenElement === opts.palco;
  }

  function alternaTelaCheia() {
    if (emTelaCheia()) {
      (document.exitFullscreen || document.webkitExitFullscreen).call(document);
    } else {
      var el = opts.palco;
      (el.requestFullscreen || el.webkitRequestFullscreen).call(el);
    }
  }

  var timerRecuo = null;
  function acordaControles() {
    opts.palco.classList.add("mostra-controles");
    clearTimeout(timerRecuo);
    // Recuo automatico: os controles aparecem ao mover o ponteiro e somem
    // depois. Em tela cheia o mapa e o conteudo; barra fixa em cima dele
    // desperdica justamente o espaco que a tela cheia foi buscar.
    timerRecuo = setTimeout(function () {
      if (emTelaCheia()) opts.palco.classList.remove("mostra-controles");
    }, MS_ATE_RECUAR);
  }

  function mudouTelaCheia() {
    var cheia = emTelaCheia();
    opts.palco.classList.toggle("tela-cheia", cheia);
    var b = document.getElementById("anot-fs");
    if (b) {
      b.textContent = cheia ? "Sair" : "Tela cheia";
      b.setAttribute("aria-label", cheia ? "Sair da tela cheia" : "Mapa em tela cheia");
    }
    if (cheia) acordaControles();
    else { clearTimeout(timerRecuo); opts.palco.classList.remove("mostra-controles"); }
    // Sair e entrar NAO mexem em round, instante, pausa nem desenho: o unico
    // efeito e o tamanho. Por isso aqui so se redimensiona e reprojeta.
    requestAnimationFrame(function () { redimensiona(); if (opts.redraw) opts.redraw(); });
  }

  /* ---------------------------------------------------------------------
     Exportar imagem
     --------------------------------------------------------------------- */

  /** O mapa com os desenhos, com o CARIMBO do contexto. Uma imagem de rabisco
      sem contexto nao serve pra mandar pro time: quem recebe precisa saber de
      que partida, round e instante ela e. */
  function exportaImagem() {
    var fora = document.createElement("canvas");
    fora.width = opts.radar.width;
    fora.height = opts.radar.height + 46;
    var c = fora.getContext("2d");
    c.fillStyle = "#0f1620";
    c.fillRect(0, 0, fora.width, fora.height);
    // Exporta o que esta VISIVEL agora -- inclusive o zoom e os tracos que a
    // linha do tempo ainda nao revelou.
    c.drawImage(opts.mapCanvas, 0, 0);
    c.drawImage(camada, 0, 0);

    var ctx2 = opts.contexto ? opts.contexto() : {};
    c.fillStyle = "#eef1f5";
    c.font = "15px 'DM Mono', monospace";
    c.textBaseline = "middle";
    var carimbo = [ctx2.partida, ctx2.mapa, "Round " + (S.round == null ? "?" : S.round),
                   ctx2.placar, ctx2.instante].filter(Boolean).join("  ·  ");
    c.fillText(carimbo, 16, opts.radar.height + 23);

    var a = document.createElement("a");
    a.download = (opts.matchId || "partida") + "-round-" + S.round + ".png";
    a.href = fora.toDataURL("image/png");
    a.click();
  }

  /* ---------------------------------------------------------------------
     Barra de ferramentas
     --------------------------------------------------------------------- */
  function botao(texto, titulo, aoClicar, classe) {
    var b = document.createElement("button");
    b.type = "button";
    b.className = "anot-b" + (classe ? " " + classe : "");
    b.textContent = texto;
    b.title = titulo;
    b.setAttribute("aria-label", titulo);
    b.addEventListener("click", aoClicar);
    return b;
  }

  function montaBarra() {
    var barra = document.createElement("div");
    barra.className = "anot-barra";
    barra.id = "anot-barra";

    var alterna = botao("Desenhar", "Ligar o modo de desenho (D)", function () {
      ligaDesenho(!S.ligado);
    }, "principal");
    alterna.id = "anot-toggle";
    barra.appendChild(alterna);

    var ferr = document.createElement("div");
    ferr.className = "anot-grupo";
    ferr.id = "anot-ferramentas";
    FERRAMENTAS.forEach(function (f) {
      var b = botao(f.rotulo, f.rotulo + " (" + f.tecla + ")", function () {
        S.ferramenta = f.id;
        atualizaBotoes();
      });
      b.dataset.ferramenta = f.id;
      ferr.appendChild(b);
    });
    barra.appendChild(ferr);

    var cores = document.createElement("div");
    cores.className = "anot-grupo";
    cores.id = "anot-cores";
    CORES.forEach(function (c) {
      var b = botao("", "Cor " + c.nome, function () { S.cor = c.hex; atualizaBotoes(); }, "cor");
      b.style.background = c.hex;
      b.dataset.cor = c.hex;
      cores.appendChild(b);
    });
    barra.appendChild(cores);

    var esp = document.createElement("div");
    esp.className = "anot-grupo";
    esp.id = "anot-espessuras";
    ESPESSURAS.forEach(function (e, i) {
      var b = botao(["fina", "media", "grossa"][i], "Espessura " + ["fina", "media", "grossa"][i],
        function () { S.espessura = e; atualizaBotoes(); });
      b.dataset.espessura = String(e);
      esp.appendChild(b);
    });
    barra.appendChild(esp);

    var acoes = document.createElement("div");
    acoes.className = "anot-grupo";
    var bDepois = botao("So a partir daqui", "O traco aparece so do instante em que foi desenhado",
      function () { S.soDepois = !S.soDepois; atualizaBotoes(); });
    bDepois.id = "anot-sodepois";
    acoes.appendChild(bDepois);
    acoes.appendChild(botao("Desfazer", "Desfazer (Ctrl+Z)", desfaz)).id = "anot-desfazer";
    acoes.appendChild(botao("Refazer", "Refazer (Ctrl+Shift+Z)", refaz)).id = "anot-refazer";
    acoes.appendChild(botao("Limpar", "Apagar todos os desenhos deste round", limpa));
    acoes.appendChild(botao("Exportar", "Baixar a imagem com o carimbo do contexto", exportaImagem));
    barra.appendChild(acoes);

    var vista = document.createElement("div");
    vista.className = "anot-grupo";
    vista.appendChild(botao("−", "Diminuir o zoom", function () {
      aplicaZoom(S.view.zoom / ZOOM_PASSO, opts.radar.width / 2, opts.radar.height / 2);
    }));
    var lupa = botao("100%", "Voltar ao tamanho original", reseta);
    lupa.id = "anot-zoom";
    vista.appendChild(lupa);
    vista.appendChild(botao("+", "Aumentar o zoom", function () {
      aplicaZoom(S.view.zoom * ZOOM_PASSO, opts.radar.width / 2, opts.radar.height / 2);
    }));
    var fs = botao("Tela cheia", "Mapa em tela cheia (F)", alternaTelaCheia);
    fs.id = "anot-fs";
    vista.appendChild(fs);
    barra.appendChild(vista);

    return barra;
  }

  function atualizaBotoes() {
    var t = document.getElementById("anot-toggle");
    if (t) {
      t.classList.toggle("on", S.ligado);
      t.textContent = S.ligado ? "Desenhando" : "Desenhar";
    }
    var barra = document.getElementById("anot-barra");
    if (barra) barra.classList.toggle("ativo", S.ligado);

    ["ferramenta", "cor", "espessura"].forEach(function (campo) {
      var atual = campo === "espessura" ? String(S.espessura) : S[campo];
      var alvo = document.querySelectorAll("[data-" + campo + "]");
      Array.prototype.forEach.call(alvo, function (b) {
        b.classList.toggle("on", b.dataset[campo] === atual);
      });
    });

    var sd = document.getElementById("anot-sodepois");
    if (sd) sd.classList.toggle("on", S.soDepois);
    var z = document.getElementById("anot-zoom");
    if (z) z.textContent = Math.round(S.view.zoom * 100) + "%";
    var d = document.getElementById("anot-desfazer");
    if (d) d.disabled = !tracosDoRound().length;
    var r = document.getElementById("anot-refazer");
    if (r) r.disabled = !S.refazer.length;
  }

  function ligaDesenho(on) {
    S.ligado = !!on;
    // Com o modo desligado a camada NAO pode capturar clique nenhum: clicar num
    // jogador ou num icone de granada tem que continuar funcionando.
    camada.style.pointerEvents = S.ligado ? "auto" : "none";
    rascunho.style.pointerEvents = "none";
    atualizaBotoes();
  }

  /* ---------------------------------------------------------------------
     Init
     --------------------------------------------------------------------- */
  function init(o) {
    opts = o;
    opts.calibracao = o.calibracao;

    var alvo = opts.mapCanvas;
    camada = document.createElement("canvas");
    rascunho = document.createElement("canvas");
    camada.className = "anot-camada";
    rascunho.className = "anot-camada anot-rascunho";
    camada.setAttribute("aria-hidden", "true");
    rascunho.setAttribute("aria-hidden", "true");
    alvo.parentNode.insertBefore(camada, alvo.nextSibling);
    alvo.parentNode.insertBefore(rascunho, camada.nextSibling);
    ctxC = camada.getContext("2d");
    ctxR = rascunho.getContext("2d");

    opts.palco.insertBefore(montaBarra(), opts.palco.firstChild);

    S.doc = carrega();
    S.pronto = true;
    ligaDesenho(false);
    redimensiona();

    // Eventos de PONTEIRO, nao de mouse: o mesmo codigo atende mouse, toque e
    // caneta de tablet, sem um caminho separado por dispositivo.
    camada.addEventListener("pointerdown", function (e) { comecou(e); panComeca(e); });
    camada.addEventListener("pointermove", function (e) { moveu(e); panMove(e); });
    camada.addEventListener("pointerup", function (e) { soltou(e); panTermina(); });
    camada.addEventListener("pointercancel", function (e) { soltou(e); panTermina(); });
    camada.addEventListener("wheel", zoomDaRoda, { passive: false });
    alvo.addEventListener("wheel", zoomDaRoda, { passive: false });

    window.addEventListener("resize", redimensiona);
    document.addEventListener("fullscreenchange", mudouTelaCheia);
    document.addEventListener("webkitfullscreenchange", mudouTelaCheia);
    opts.palco.addEventListener("pointermove", function () {
      if (emTelaCheia()) acordaControles();
    });

    document.addEventListener("keydown", function (e) {
      var editando = /^(INPUT|TEXTAREA|SELECT)$/.test((e.target || {}).tagName || "");
      if (editando) return;
      var k = e.key.toLowerCase();
      if ((e.ctrlKey || e.metaKey) && k === "z") {
        e.preventDefault();
        if (e.shiftKey) refaz(); else desfaz();
        return;
      }
      if (k === "f") { e.preventDefault(); alternaTelaCheia(); return; }
      if (k === "d") { e.preventDefault(); ligaDesenho(!S.ligado); return; }
      if (k === "0") { e.preventDefault(); reseta(); return; }
      FERRAMENTAS.forEach(function (f) {
        if (e.key === f.tecla) { S.ferramenta = f.id; atualizaBotoes(); }
      });
    });

    atualizaBotoes();
  }

  return {
    init: init,
    applyView: applyView,
    /** O template chama a cada quadro. So repinta quando o conjunto VISIVEL
        muda -- o mapa se movendo nao pode forcar redesenho dos tracos. */
    onFrame: function (pos) {
      S.pos = pos;
      var n = visiveis().length;
      if (n !== S.visiveisAntes) { S.visiveisAntes = n; repinta(); }
    },
    /** Trocar de round troca o conjunto de desenhos. Nada de rabisco de um
        round vazando no outro. */
    setRound: function (n) {
      if (S.round === n) return;
      S.round = n;
      S.refazer = [];
      S.visiveisAntes = -1;
      repinta();
      atualizaBotoes();
    },
    emTelaCheia: emTelaCheia,
    exportaImagem: exportaImagem,
    _interno: {
      S: S, CORES: CORES, ESPESSURAS: ESPESSURAS, FERRAMENTAS: FERRAMENTAS,
      jogoParaPixel: jogoParaPixel, pixelParaJogo: pixelParaJogo,
      caixaDoMapa: caixaDoMapa, desfaz: desfaz, refaz: refaz,
      tracosDoRound: tracosDoRound, visiveis: visiveis
    }
  };
})();
