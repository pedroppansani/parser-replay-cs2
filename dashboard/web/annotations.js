/* =========================================================================
   Camada de desenho sobre o mapa, seletor de cor, tela cheia e zoom.

   A DECISÃO QUE SUSTENTA TUDO: todo traço é guardado em COORDENADAS DE JOGO,
   nunca em pixels de tela. O tamanho da tela muda o tempo inteiro -- janela
   redimensionada, tela cheia, zoom, outro monitor -- e pixel guardado deixa de
   apontar para o lugar certo no instante em que qualquer uma dessas coisas
   acontece. Guardando unidade de jogo, uma seta apontando para o fundo do bomb
   continua apontando para o fundo do bomb em qualquer tamanho. A conta é a
   mesma de scripts/prepare_radar.py e de metrics/annotations.py, nos dois
   sentidos.

   TODO REDESENHO PARTE DO MODELO, nunca do que está pintado. Mudar o tamanho de
   um canvas (atribuir width/height) APAGA o conteúdo dele sem aviso. Por isso
   existe um único ponto que muda tamanho -- reprojetaTudo() -- e ele sempre
   redesenha TODAS as camadas: o mapa (pelo template) e as anotações (daqui).
   Carga inicial, janela redimensionada, entrada e saída de tela cheia e
   mudança de densidade de pixel passam todas por ele.

   PERSISTÊNCIA EM TRÊS CAMADAS:
     1. memória: os traços vivem em S.rounds, por round;
     2. navegador: cada round é gravado no localStorage com chave por partida e
        round, com um pequeno atraso para não gravar a cada ponto do traço. A
        página é aberta como arquivo local ou pelo GitHub Pages -- nos dois
        casos não há servidor que aceite escrita, então é aqui que ela fica;
     3. arquivo: exportar e importar JSON, no formato de metrics/annotations.py.
        Sem isso a anotação fica presa num navegador só, e o objetivo é poder
        mandar para outra pessoa.
   Falha do armazenamento (aba anônima, cota cheia, acesso bloqueado) nunca
   derruba a página: o desenho continua na memória e o aviso aparece na barra.

   Este arquivo é separado do template de propósito: o template já está grande
   demais, e a camada de desenho não tem nada a ver com o resto da página. O CSS
   dela está em annotations.css.
   ========================================================================= */
window.MapAnnotations = (function () {
  "use strict";

  // Formato do arquivo -- o mesmo de metrics/annotations.py. Se os dois
  // divergirem, um arquivo exportado aqui não abre lá.
  var FORMATO = 1;

  // Três níveis. Mais que isso vira menu e ninguém usa.
  var ESPESSURAS = [2, 4, 7];
  var ROTULOS_ESPESSURA = ["fina", "média", "grossa"];

  var FERRAMENTAS = [
    { id: "caneta", rotulo: "Caneta", tecla: "1" },
    { id: "seta", rotulo: "Seta", tecla: "2" },
    { id: "linha", rotulo: "Linha", tecla: "3" },
    { id: "retangulo", rotulo: "Retângulo", tecla: "4" },
    { id: "elipse", rotulo: "Elipse", tecla: "5" },
    { id: "texto", rotulo: "Texto", tecla: "6" },
    { id: "borracha", rotulo: "Borracha", tecla: "7" }
  ];

  // Ligar o desenho tem que já desenhar, à mão livre. A reta é ferramenta
  // separada, escolhida de propósito.
  var FERRAMENTA_PADRAO = "caneta";

  // Cor inicial, antes de qualquer escolha: o laranja do TR, que já tem
  // contraste validado sobre o radar claro (decisão 10).
  var COR_PADRAO = "#eb6834";
  var MAX_RECENTES = 6;

  // Atraso da gravação no navegador. Curto o bastante para um recarregar logo
  // depois de desenhar não perder nada (e a saída da página grava na hora),
  // longo o bastante para não gravar a cada ponto do traço.
  var MS_ATE_GRAVAR = 400;

  // Distância mínima entre dois pontos da caneta, em pixels do radar. Abaixo
  // disso o ponto novo não acrescenta forma, só tamanho de arquivo.
  var PASSO_MIN_CANETA = 1.5;

  // Raio de acerto da borracha, em pixels do radar. Ela apaga o TRAÇO INTEIRO
  // sob o cursor, não pixel a pixel: apagar pedaço de seta deixa meia seta, que
  // é pior que não apagar.
  var RAIO_BORRACHA = 10;

  // Quanto tempo os controles ficam na tela depois do último movimento, em tela
  // cheia. Curto o bastante para não tampar o mapa, longo o bastante para dar
  // tempo de mirar um botão.
  var MS_ATE_RECUAR = 2600;

  // Teto da resolução interna do canvas. Numa tela 4K com densidade 2, o mapa
  // em tela cheia passaria de 4000px de lado, e redesenhar isso a cada quadro
  // custa mais do que a nitidez extra devolve.
  var MAX_LADO_INTERNO = 4096;

  var ZOOM_MIN = 1, ZOOM_MAX = 6, ZOOM_PASSO = 1.18;

  var PREFIXO = "anot:v" + FORMATO + ":";
  var CHAVE_RECENTES = "anot:cores-recentes";
  var CHAVE_FERRAMENTA = "anot:ultima-ferramenta";

  var S = {
    pronto: false,
    ligado: false,          // modo de desenho
    ferramenta: FERRAMENTA_PADRAO,
    cor: COR_PADRAO,
    recentes: [],
    corPendente: null,      // cor em edição no seletor; só vale ao fechar
    hsv: { h: 0, s: 1, v: 1 },   // posição do seletor visual
    espessura: ESPESSURAS[1],
    soDepois: false,        // o traço aparece só a partir do instante em que foi feito
    round: null,
    pos: 0,
    rounds: {},             // o modelo: round -> lista de traços em coordenada de jogo
    refazer: [],
    tracando: null,
    view: { zoom: 1, panX: 0, panY: 0 },   // pan em pixels do radar
    espaco: false,          // barra de espaço segurada: o arrasto vira pan
    sobreMapa: false,       // ponteiro sobre o palco (só aí o espaço é nosso)
    visiveisAntes: -1,
    armazemOk: true,
    aviso: "",
    reprojecoes: 0
  };

  var opts = null, cv = null, camada = null, rascunho = null, ctxC = null, ctxR = null;

  /* ---------------------------------------------------------------------
     Armazenamento do navegador. TODO acesso passa por aqui, dentro de
     try/catch: até ler `window.localStorage` pode lançar erro (arquivo local
     com cookies bloqueados, aba anônima de alguns navegadores).
     --------------------------------------------------------------------- */
  function armazem(qual) {
    try { return window[qual] || null; } catch (err) { falhouArmazem(); return null; }
  }
  function le(qual, chave) {
    try { var a = armazem(qual); return a ? a.getItem(chave) : null; }
    catch (err) { falhouArmazem(); return null; }
  }
  function grava(qual, chave, valor) {
    try { var a = armazem(qual); if (!a) return false; a.setItem(chave, valor); return true; }
    catch (err) { falhouArmazem(); return false; }
  }
  function remove(qual, chave) {
    try { var a = armazem(qual); if (a) a.removeItem(chave); }
    catch (err) { falhouArmazem(); }
  }
  function chaves(qual) {
    try {
      var a = armazem(qual), out = [];
      if (!a) return out;
      for (var i = 0; i < a.length; i++) out.push(a.key(i));
      return out;
    } catch (err) { falhouArmazem(); return []; }
  }
  function falhouArmazem() {
    if (!S.armazemOk) return;
    S.armazemOk = false;
    avisa("Este navegador não deixou salvar as anotações: use Exportar para guardá-las.");
  }

  function lerJson(texto) {
    if (!texto) return null;
    try { return JSON.parse(texto); } catch (err) { return null; }
  }

  /* ---------------------------------------------------------------------
     Projeção. A mesma conta do resto do projeto, nos dois sentidos.
     --------------------------------------------------------------------- */
  function jogoParaPixel(x, y) {
    var r = opts.radar;
    return [(x - r.origin_x) * r.scale_px_per_unit, (r.origin_y - y) * r.scale_px_per_unit];
  }
  function pixelParaJogo(px, py) {
    var r = opts.radar;
    return [px / r.scale_px_per_unit + r.origin_x, r.origin_y - py / r.scale_px_per_unit];
  }

  /** Ponteiro na tela -> pixel do radar, desfazendo o tamanho na tela, o zoom e
      o pan. A caixa é a do MAPA: a camada é posicionada exatamente sobre ela. */
  function eventoParaPixel(e) {
    var caixa = cv.getBoundingClientRect();
    var k = opts.radar.width / caixa.width;
    var px = (e.clientX - caixa.left) * k;
    var py = (e.clientY - caixa.top) * k;
    return [(px - S.view.panX) / S.view.zoom, (py - S.view.panY) / S.view.zoom];
  }

  // Uma casa decimal de unidade de jogo: 0,1u é muito abaixo de um pixel do
  // radar, e o arquivo exportado fica com metade do tamanho.
  function arredonda(v) { return Math.round(v * 10) / 10; }

  function eventoParaJogo(e) {
    var p = eventoParaPixel(e);
    var g = pixelParaJogo(p[0], p[1]);
    return [arredonda(g[0]), arredonda(g[1])];
  }

  /** Aplica tamanho interno, zoom e pan a um contexto. O mapa usa a MESMA
      transformação (o template chama esta função), senão os dois se descolam e
      a seta aponta para o lugar errado.

      O desenho acontece sempre em pixels do RADAR; a escala até a resolução
      interna do canvas entra aqui. É isso que deixa a resolução do canvas
      acompanhar a tela sem que nada no template precise saber disso. */
  function applyView(ctx) {
    var base = opts ? ctx.canvas.width / opts.radar.width : 1;
    var z = base * S.view.zoom;
    ctx.setTransform(z, 0, 0, z, base * S.view.panX, base * S.view.panY);
  }

  /* ---------------------------------------------------------------------
     Modelo e persistência
     --------------------------------------------------------------------- */
  function prefixoDaPartida() { return PREFIXO + opts.matchId + ":"; }
  function chaveDoRound(rn) { return prefixoDaPartida() + rn; }

  function tracosDe(rn) { return S.rounds[String(rn)] || []; }
  function tracosDoRound() { return S.round == null ? [] : tracosDe(S.round); }

  function gravaTracos(lista) {
    S.rounds[String(S.round)] = lista;
    agendaGravacao(S.round);
  }

  var IDS_FERRAMENTA = FERRAMENTAS.map(function (f) { return f.id; })
    .filter(function (id) { return id !== "borracha"; });

  /** Um traço vindo de fora (armazenamento ou arquivo) só entra se fizer
      sentido: ferramenta conhecida e pontos numéricos. Um traço corrompido
      derrubaria o redesenho de todos os outros. */
  function tracoValido(t) {
    if (!t || IDS_FERRAMENTA.indexOf(t.ferramenta) < 0) return false;
    if (!Array.isArray(t.pontos) || !t.pontos.length) return false;
    return t.pontos.every(function (p) {
      return Array.isArray(p) && p.length === 2 && isFinite(p[0]) && isFinite(p[1]);
    });
  }

  function novoId() {
    return Date.now().toString(36) + Math.random().toString(36).slice(2, 8);
  }

  /** Todo traço carrega a própria procedência: mapa e versão da calibração do
      radar. Um arquivo que mistura traços de antes e depois de uma
      recalibração continua dizendo qual é qual. */
  function carimba(t) {
    t.id = t.id || novoId();
    t.mapa = opts.mapa;
    t.calibracao = opts.calibracao;
    return t;
  }

  function carregaDoNavegador() {
    var prefixo = prefixoDaPartida();
    var rounds = {};
    chaves("localStorage").forEach(function (k) {
      if (!k || k.indexOf(prefixo) !== 0) return;
      var reg = lerJson(le("localStorage", k));
      if (!reg || reg.formato !== FORMATO || !Array.isArray(reg.tracos)) return;
      var lista = reg.tracos.filter(tracoValido);
      if (lista.length) rounds[k.slice(prefixo.length)] = lista;
    });
    return rounds;
  }

  var pendentes = {}, timerGravar = null;

  function agendaGravacao(rn) {
    pendentes[String(rn)] = true;
    clearTimeout(timerGravar);
    timerGravar = setTimeout(gravaPendentes, MS_ATE_GRAVAR);
  }

  function gravaPendentes() {
    clearTimeout(timerGravar);
    timerGravar = null;
    Object.keys(pendentes).forEach(function (rn) {
      var lista = tracosDe(rn);
      if (!lista.length) { remove("localStorage", chaveDoRound(rn)); return; }
      grava("localStorage", chaveDoRound(rn), JSON.stringify({
        formato: FORMATO,
        match_id: opts.matchId,
        mapa: opts.mapa,
        calibracao: opts.calibracao,
        round: Number(rn),
        tracos: lista
      }));
    });
    pendentes = {};
  }

  /** O documento inteiro da partida, no formato de metrics/annotations.py. */
  function documento() {
    var rounds = {};
    Object.keys(S.rounds).sort(function (a, b) { return Number(a) - Number(b); })
      .forEach(function (rn) { if (S.rounds[rn].length) rounds[rn] = S.rounds[rn]; });
    return {
      formato: FORMATO,
      match_id: opts.matchId,
      mapa: opts.mapa,
      calibracao: opts.calibracao,
      rounds: rounds
    };
  }

  /** Junta um documento importado ao modelo. Devolve a mensagem para a barra.

      Junta em vez de substituir, e sem duplicar: importar o mesmo arquivo duas
      vezes não dobra os traços (o id de cada um é a identidade). Arquivo de
      outra partida é recusado -- round 3 de uma partida não é o round 3 de
      outra, e a anotação cairia sobre uma jogada diferente. */
  function importaTexto(texto) {
    var doc = lerJson(texto);
    if (!doc || typeof doc.rounds !== "object" || doc.rounds === null) {
      return { ok: false, msg: "O arquivo não é de anotações." };
    }
    if (doc.formato !== FORMATO) {
      return { ok: false, msg: "Formato de anotação " + doc.formato + " desconhecido." };
    }
    if (doc.match_id && doc.match_id !== opts.matchId) {
      return { ok: false, msg: "Estas anotações são de outra partida (" + doc.match_id + ")." };
    }
    var novos = 0;
    Object.keys(doc.rounds).forEach(function (rn) {
      var atuais = tracosDe(rn).slice();
      var ids = {};
      atuais.forEach(function (t) { ids[t.id] = true; });
      (doc.rounds[rn] || []).forEach(function (t) {
        if (!tracoValido(t)) return;
        var copia = JSON.parse(JSON.stringify(t));
        copia.id = copia.id || novoId();
        if (ids[copia.id]) return;
        // a procedência do arquivo é preservada: é ela que diz com que
        // calibração o traço foi feito
        copia.mapa = copia.mapa || doc.mapa || opts.mapa;
        copia.calibracao = copia.calibracao || doc.calibracao || opts.calibracao;
        ids[copia.id] = true;
        atuais.push(copia);
        novos++;
      });
      S.rounds[String(rn)] = atuais;
      agendaGravacao(rn);
    });
    gravaPendentes();
    S.visiveisAntes = -1;
    repinta();
    atualizaBotoes();
    return { ok: true, n: novos, msg: novos === 1 ? "1 traço importado." : novos + " traços importados." };
  }

  function baixa(blob, nome) {
    var a = document.createElement("a");
    a.download = nome;
    a.href = URL.createObjectURL(blob);
    document.body.appendChild(a);
    a.click();
    a.remove();
    setTimeout(function () { URL.revokeObjectURL(a.href); }, 1000);
  }

  function exportaAnotacoes() {
    gravaPendentes();
    var json = JSON.stringify(documento(), null, 2);
    baixa(new Blob([json], { type: "application/json" }), (opts.matchId || "partida") + "-anotacoes.json");
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

    var a = p[0], b = p[p.length - 1];
    ctx.beginPath();
    if (t.ferramenta === "caneta") {
      if (p.length === 1) {
        // clique seco com a caneta é um ponto, e ponto também é anotação
        ctx.arc(a[0], a[1], t.espessura / 2, 0, Math.PI * 2);
        ctx.fill();
        return;
      }
      // Curva pelos pontos médios: a mão livre sai lisa, sem o serrilhado de
      // ligar amostra com amostra em linha reta.
      ctx.moveTo(p[0][0], p[0][1]);
      for (var i = 1; i < p.length - 1; i++) {
        var mx = (p[i][0] + p[i + 1][0]) / 2, my = (p[i][1] + p[i + 1][1]) / 2;
        ctx.quadraticCurveTo(p[i][0], p[i][1], mx, my);
      }
      ctx.lineTo(b[0], b[1]);
      ctx.stroke();
      return;
    }
    if (p.length < 2) return;
    if (t.ferramenta === "linha") {
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

  /** A seta é ferramenta de primeira classe, não linha com enfeite: a cabeça
      cresce com a espessura e fica sólida, para a leitura funcionar de longe. */
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

  /** Redesenha a camada consolidada A PARTIR DO MODELO. Chamada só quando o
      conjunto visível ou o tamanho muda, não a cada quadro -- o mapa se movendo
      não pode forçar redesenho dos traços. A camada nunca recebe fundo: só
      clearRect, nada de fillRect. */
  function repinta() {
    if (!S.pronto) return;
    ctxC.setTransform(1, 0, 0, 1, 0, 0);
    ctxC.clearRect(0, 0, camada.width, camada.height);
    applyView(ctxC);
    visiveis().forEach(function (t) { caminhoDoTraco(ctxC, t); });
  }

  function repintaRascunho() {
    if (!S.pronto) return;
    ctxR.setTransform(1, 0, 0, 1, 0, 0);
    ctxR.clearRect(0, 0, rascunho.width, rascunho.height);
    if (!S.tracando) return;
    applyView(ctxR);
    caminhoDoTraco(ctxR, S.tracando);
  }

  /* ---------------------------------------------------------------------
     Entrada por ponteiro (mouse, toque e caneta com o mesmo código)
     --------------------------------------------------------------------- */
  function comecou(e) {
    // Com o espaço segurado o arrasto é PAN, nunca traço -- o mesmo gesto dos
    // editores de imagem, e o único jeito de mover o mapa sem sair do desenho.
    if (!S.ligado || e.button !== 0 || S.espaco) return;
    camada.setPointerCapture(e.pointerId);
    // Ninguém consegue desenhar em cima de boneco andando.
    if (opts.pause) opts.pause();

    var g = eventoParaJogo(e);

    if (S.ferramenta === "borracha") { apaga(g); return; }

    if (S.ferramenta === "texto") {
      var txt = window.prompt("Texto da anotação:");
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
      ferramenta: S.ferramenta,
      // a caneta começa com UM ponto e acumula o caminho da mão; as de duas
      // pontas guardam início e fim
      pontos: S.ferramenta === "caneta" ? [g] : [g, g],
      cor: S.cor, espessura: S.espessura,
      so_depois: S.soDepois, pos: S.pos
    };
    repintaRascunho();
  }

  function moveu(e) {
    if (!S.ligado || !S.tracando) return;
    var eventos = (S.tracando.ferramenta === "caneta" && e.getCoalescedEvents)
      ? e.getCoalescedEvents() : [e];
    if (!eventos.length) eventos = [e];
    eventos.forEach(function (ev) {
      var g = eventoParaJogo(ev);
      var pts = S.tracando.pontos;
      if (S.tracando.ferramenta !== "caneta") { pts[1] = g; return; }
      var ult = jogoParaPixel(pts[pts.length - 1][0], pts[pts.length - 1][1]);
      var novo = jogoParaPixel(g[0], g[1]);
      if (Math.hypot(novo[0] - ult[0], novo[1] - ult[1]) * S.view.zoom >= PASSO_MIN_CANETA) pts.push(g);
    });
    // O traço em andamento vive na camada de rascunho; só ao soltar ele é
    // consolidado. Assim um traço longo não repinta o desenho inteiro a cada
    // movimento do ponteiro.
    repintaRascunho();
  }

  function soltou() {
    if (!S.ligado || !S.tracando) return;
    var t = S.tracando;
    S.tracando = null;
    repintaRascunho();
    // clique seco com ferramenta de duas pontas não vira traço
    var a = jogoParaPixel(t.pontos[0][0], t.pontos[0][1]);
    var b = jogoParaPixel(t.pontos[t.pontos.length - 1][0], t.pontos[t.pontos.length - 1][1]);
    if (t.ferramenta !== "caneta" && Math.abs(a[0] - b[0]) < 8 && Math.abs(a[1] - b[1]) < 8) return;
    empilha(t);
  }

  function empilha(t) {
    var lista = tracosDoRound().slice();
    lista.push(carimba(t));
    gravaTracos(lista);
    S.refazer = [];   // ramo novo: o que foi desfeito deixa de ser refazível
    S.visiveisAntes = -1;
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
    if (topo.round !== S.round) return;  // não ressuscita traço de outro round
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
     Dimensionamento: O ÚNICO lugar que muda tamanho de canvas.
     --------------------------------------------------------------------- */

  /** O mapa cresce até o limite da MENOR dimensão e fica centralizado; o
      excedente vira espaço vazio. Nunca esticado -- já houve bug de proporção
      neste projeto (dado em retrato num canvas em paisagem), e esticar é
      exatamente o que produz aquilo. Mesma conta de
      metrics/annotations.caixa_do_mapa. */
  function caixaDoMapa(dispW, dispH) {
    var w = opts.radar.width, h = opts.radar.height;
    var escala = Math.min(dispW / w, dispH / h);
    return { largura: w * escala, altura: h * escala, escala: escala };
  }

  /** Reprojeta e redesenha TUDO.

      Atribuir width/height a um canvas apaga o que está nele, sem aviso. Então
      toda mudança de tamanho termina redesenhando as três camadas a partir dos
      dados -- o mapa pelo template (opts.redraw), as anotações pelo modelo. Um
      redesenho que esquecesse uma delas deixaria aquela camada em branco até o
      próximo quadro que, com o replay pausado, não vem nunca. */
  function reprojetaTudo() {
    if (!S.pronto) return;
    var RW = opts.radar.width, RH = opts.radar.height;

    // Em tela cheia o tamanho na tela é decidido aqui, pela caixa que preserva
    // a proporção; fora dela, o CSS da página decide.
    if (emTelaCheia()) {
      var wrap = cv.parentNode;
      var cx = caixaDoMapa(wrap.clientWidth, wrap.clientHeight);
      cv.style.width = cx.largura + "px";
      cv.style.height = cx.altura + "px";
    } else {
      cv.style.width = "";
      cv.style.height = "";
    }

    var larguraCss = cv.clientWidth, alturaCss = cv.clientHeight;
    // Aba escondida: não há caixa para medir. O observador de tamanho chama de
    // novo quando ela aparecer.
    if (!larguraCss || !alturaCss) return;

    // Resolução INTERNA = tamanho na tela x densidade de pixels, senão mapa e
    // traços saem borrados em tela de alta densidade -- e o traço fino é o
    // primeiro a sofrer. A altura sai da largura para a proporção ser exata.
    var dpr = window.devicePixelRatio || 1;
    var w = Math.max(1, Math.min(MAX_LADO_INTERNO, Math.round(larguraCss * dpr)));
    var h = Math.max(1, Math.round(w * RH / RW));
    [cv, camada, rascunho].forEach(function (c) {
      if (c.width !== w || c.height !== h) { c.width = w; c.height = h; }
    });

    // As camadas ficam exatamente sobre o mapa, onde quer que ele esteja.
    [camada, rascunho].forEach(function (c) {
      c.style.left = cv.offsetLeft + "px";
      c.style.top = cv.offsetTop + "px";
      c.style.width = larguraCss + "px";
      c.style.height = alturaCss + "px";
    });

    // Em tela cheia a barra flutua sobre o mapa e pode quebrar em várias
    // linhas; o cabeçalho do round vai logo abaixo dela, não numa altura fixa.
    var barra = document.getElementById("anot-barra");
    if (barra) opts.palco.style.setProperty("--altura-barra", barra.offsetHeight + "px");

    S.reprojecoes++;
    if (opts.redraw) opts.redraw();
    repinta();
    repintaRascunho();
  }

  // Vários gatilhos podem disparar no mesmo quadro (resize + observador de
  // tamanho + tela cheia); junta todos numa reprojeção só, depois do layout.
  var reprojecaoPedida = false;
  function pedeReprojecao() {
    if (reprojecaoPedida) return;
    reprojecaoPedida = true;
    requestAnimationFrame(function () { reprojecaoPedida = false; reprojetaTudo(); });
  }

  /** Mudança de densidade de pixel (arrastar a janela para outro monitor, zoom
      do navegador) não dispara `resize` em todo navegador. A media query da
      densidade atual avisa quando ela deixa de valer; aí vigia a nova. */
  function vigiaDensidade() {
    if (!window.matchMedia) return;
    var mq = window.matchMedia("(resolution: " + (window.devicePixelRatio || 1) + "dppx)");
    var mudou = function () {
      if (mq.removeEventListener) mq.removeEventListener("change", mudou);
      else if (mq.removeListener) mq.removeListener(mudou);
      pedeReprojecao();
      vigiaDensidade();
    };
    if (mq.addEventListener) mq.addEventListener("change", mudou);
    else if (mq.addListener) mq.addListener(mudou);
  }

  /* ---------------------------------------------------------------------
     Zoom e pan
     --------------------------------------------------------------------- */
  function aplicaZoom(novo, centroX, centroY) {
    var z0 = S.view.zoom;
    var z = Math.min(ZOOM_MAX, Math.max(ZOOM_MIN, novo));
    if (z === z0) return;
    // mantém o ponto sob o cursor parado enquanto o zoom muda
    S.view.panX = centroX - (centroX - S.view.panX) * (z / z0);
    S.view.panY = centroY - (centroY - S.view.panY) * (z / z0);
    S.view.zoom = z;
    limitaPan();
    pedeRedesenho();
  }

  /** Impede que o mapa escape da área visível. Sem isso dá para arrastar o
      mapa para fora e ficar olhando para o vazio sem saber como voltar. */
  function limitaPan() {
    var W = opts.radar.width, H = opts.radar.height;
    S.view.panX = Math.min(0, Math.max(W - W * S.view.zoom, S.view.panX));
    S.view.panY = Math.min(0, Math.max(H - H * S.view.zoom, S.view.panY));
  }

  /** Zoom e pan não mudam tamanho de canvas, só a transformação: basta
      redesenhar, sem reprojetar. */
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
    // Com o modo de desenho LIGADO o ponteiro desenha; o pan fica no botão do
    // meio ou no espaço + arrastar, para não existir gesto que faz duas coisas.
    if (S.ligado && e.button !== 1 && !S.espaco) return;
    if (S.view.zoom <= 1) return;
    arrastando = { x: e.clientX, y: e.clientY, panX: S.view.panX, panY: S.view.panY };
    opts.palco.classList.add("anot-arrastando");
    e.currentTarget.setPointerCapture(e.pointerId);
  }
  function panMove(e) {
    if (!arrastando) return;
    var k = opts.radar.width / cv.getBoundingClientRect().width;
    S.view.panX = arrastando.panX + (e.clientX - arrastando.x) * k;
    S.view.panY = arrastando.panY + (e.clientY - arrastando.y) * k;
    limitaPan();
    pedeRedesenho();
  }
  function panTermina() {
    arrastando = null;
    if (opts) opts.palco.classList.remove("anot-arrastando");
  }

  /** Espaço segurado = modo de pan. Solto (ou a janela perde o foco no meio),
      o ponteiro volta a desenhar. */
  function modoPan(ligado) {
    S.espaco = ligado;
    opts.palco.classList.toggle("anot-pan", ligado);
    if (!ligado) panTermina();
  }

  function reseta() {
    S.view = { zoom: 1, panX: 0, panY: 0 };
    pedeRedesenho();
  }

  /* ---------------------------------------------------------------------
     Tela cheia
     --------------------------------------------------------------------- */
  function emTelaCheia() {
    return !!opts && (document.fullscreenElement === opts.palco ||
                      document.webkitFullscreenElement === opts.palco);
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
    // Recuo automático: os controles aparecem ao mover o ponteiro e somem
    // depois. Com o seletor de cor aberto eles ficam, senão o seletor some no
    // meio da escolha.
    timerRecuo = setTimeout(function () {
      if (emTelaCheia() && !seletorAberto()) opts.palco.classList.remove("mostra-controles");
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
    // Entrar e sair NÃO mexem em round, instante, pausa nem desenho: o único
    // efeito é o tamanho. Por isso aqui só se reprojeta.
    pedeReprojecao();
  }

  /* ---------------------------------------------------------------------
     Exportar imagem
     --------------------------------------------------------------------- */

  /** O mapa com os desenhos, com o CARIMBO do contexto. Uma imagem de rabisco
      sem contexto não serve para mandar para o time: quem recebe precisa saber
      de que partida, round e instante ela é. */
  function exportaImagem() {
    var W = opts.radar.width, H = opts.radar.height;
    var fora = document.createElement("canvas");
    fora.width = W;
    fora.height = H + 46;
    var c = fora.getContext("2d");
    c.fillStyle = "#0f1620";
    c.fillRect(0, 0, fora.width, fora.height);
    // Exporta o que está VISÍVEL agora -- inclusive o zoom e os traços que a
    // linha do tempo ainda não revelou. A resolução interna muda com a tela;
    // a imagem sai sempre no tamanho do radar.
    c.drawImage(cv, 0, 0, W, H);
    c.drawImage(camada, 0, 0, W, H);

    var ctx2 = opts.contexto ? opts.contexto() : {};
    c.fillStyle = "#eef1f5";
    c.font = "15px 'DM Mono', monospace";
    c.textBaseline = "middle";
    var carimbo = [ctx2.partida, ctx2.mapa, "Round " + (S.round == null ? "?" : S.round),
                   ctx2.placar, ctx2.instante].filter(Boolean).join("  ·  ");
    c.fillText(carimbo, 16, H + 23);

    fora.toBlob(function (blob) {
      if (blob) baixa(blob, (opts.matchId || "partida") + "-round-" + S.round + ".png");
    }, "image/png");
  }

  /* ---------------------------------------------------------------------
     Cor: bolinha com a cor atual, setinha que abre o seletor, recentes.
     --------------------------------------------------------------------- */

  /** Hex (#rgb, #rrggbb, com ou sem #) ou rgb(r, g, b) -> "#rrggbb", ou null. */
  function normalizaCor(texto) {
    var s = String(texto || "").trim().toLowerCase();
    var m = s.match(/^rgb\s*\(\s*(\d{1,3})\s*,\s*(\d{1,3})\s*,\s*(\d{1,3})\s*\)$/);
    if (m) return deRgb(Number(m[1]), Number(m[2]), Number(m[3]));
    if (s.charAt(0) === "#") s = s.slice(1);
    if (/^[0-9a-f]{3}$/.test(s)) s = s.charAt(0) + s.charAt(0) + s.charAt(1) + s.charAt(1) + s.charAt(2) + s.charAt(2);
    return /^[0-9a-f]{6}$/.test(s) ? "#" + s : null;
  }
  function deRgb(r, g, b) {
    if ([r, g, b].some(function (v) { return !isFinite(v) || v < 0 || v > 255 || v !== Math.floor(v); })) return null;
    return "#" + [r, g, b].map(function (v) { return (v < 16 ? "0" : "") + v.toString(16); }).join("");
  }
  function paraRgb(hex) {
    return [1, 3, 5].map(function (i) { return parseInt(hex.slice(i, i + 2), 16); });
  }

  /** HSV é o espaço do seletor visual: a matiz é a barra do arco-íris, e
      saturação x brilho é o quadrado. h em graus, s e v de 0 a 1. */
  function deHsv(h, sat, v) {
    var f = function (n) {
      var k = (n + h / 60) % 6;
      return v - v * sat * Math.max(0, Math.min(k, 4 - k, 1));
    };
    return deRgb(Math.round(f(5) * 255), Math.round(f(3) * 255), Math.round(f(1) * 255));
  }
  function paraHsv(hex) {
    var c = paraRgb(hex).map(function (x) { return x / 255; });
    var max = Math.max(c[0], c[1], c[2]), min = Math.min(c[0], c[1], c[2]), d = max - min;
    var h = 0;
    if (d) {
      if (max === c[0]) h = ((c[1] - c[2]) / d) % 6;
      else if (max === c[1]) h = (c[2] - c[0]) / d + 2;
      else h = (c[0] - c[1]) / d + 4;
      h = (h * 60 + 360) % 360;
    }
    return { h: h, s: max ? d / max : 0, v: max };
  }

  function aplicaCor(hex) {
    var cor = normalizaCor(hex);
    if (!cor) return;
    S.cor = cor;
    S.recentes = [cor].concat(S.recentes.filter(function (c) { return c !== cor; })).slice(0, MAX_RECENTES);
    grava("localStorage", CHAVE_RECENTES, JSON.stringify(S.recentes));
    atualizaBotoes();
  }

  function seletorAberto() {
    var pop = document.getElementById("anot-seletor");
    return !!pop && !pop.hidden;
  }

  function abreSeletor() {
    var pop = document.getElementById("anot-seletor");
    S.corPendente = S.cor;
    sincronizaSeletor(null);
    pop.hidden = false;
    posicionaSeletor(pop);
    document.getElementById("anot-cor-seta").setAttribute("aria-expanded", "true");
    // sem rolar: o painel tem overflow escondido, e focar algo que passa da
    // borda faria o navegador deslizar a barra inteira para o lado
    document.getElementById("anot-cor-sv").focus({ preventScroll: true });
  }

  /** O seletor abre para baixo da bolinha, mas nunca para fora do painel: a
      bolinha pode estar perto da borda direita dependendo da largura da tela. */
  function posicionaSeletor(pop) {
    var MARGEM = 8;
    pop.style.left = "0px";
    var r = pop.getBoundingClientRect(), lim = opts.palco.getBoundingClientRect();
    var desloca = 0;
    if (r.right > lim.right - MARGEM) desloca = lim.right - MARGEM - r.right;
    if (r.left + desloca < lim.left + MARGEM) desloca = lim.left + MARGEM - r.left;
    pop.style.left = desloca + "px";
  }

  /** Fechar o seletor APLICA a cor escolhida: à bolinha e aos PRÓXIMOS traços.
      Traço já feito guarda a própria cor e não muda. */
  function fechaSeletor() {
    if (!seletorAberto()) return;
    document.getElementById("anot-seletor").hidden = true;
    document.getElementById("anot-cor-seta").setAttribute("aria-expanded", "false");
    if (S.corPendente) aplicaCor(S.corPendente);
    S.corPendente = null;
  }

  /** Mantém o seletor igual à cor pendente. `origem` diz de onde veio a
      mudança: o campo que o usuário está digitando não é reescrito (senão o
      cursor pula), e a posição HSV não é recalculada a partir do hex quando foi
      ela que mudou -- num cinza a matiz não existe no hex, e a barra pularia
      para o vermelho. */
  function sincronizaSeletor(origem) {
    var cor = S.corPendente || S.cor;
    if (origem !== "sv" && origem !== "matiz") S.hsv = paraHsv(cor);
    var hsv = S.hsv;

    var sv = document.getElementById("anot-cor-sv");
    sv.style.backgroundColor = deHsv(hsv.h, 1, 1);
    var alca = document.getElementById("anot-cor-sv-alca");
    alca.style.left = (hsv.s * 100) + "%";
    alca.style.top = ((1 - hsv.v) * 100) + "%";
    alca.style.background = cor;
    sv.setAttribute("aria-valuetext", "saturação " + Math.round(hsv.s * 100) +
                    "%, brilho " + Math.round(hsv.v * 100) + "%");
    var matiz = document.getElementById("anot-cor-matiz");
    document.getElementById("anot-cor-matiz-alca").style.left = (hsv.h / 360 * 100) + "%";
    matiz.setAttribute("aria-valuenow", String(Math.round(hsv.h)));

    document.getElementById("anot-cor-amostra").style.background = cor;
    var hex = document.getElementById("anot-cor-hex");
    if (origem !== "hex") { hex.value = cor; hex.removeAttribute("aria-invalid"); }
  }

  /** Arrastar dentro de uma área (quadrado ou barra) com o mesmo código para
      mouse, toque e caneta. `aoMover` recebe a posição relativa, de 0 a 1. */
  function arrastavel(el, aoMover) {
    var ativo = false;
    function posicao(e) {
      var r = el.getBoundingClientRect();
      aoMover(Math.min(1, Math.max(0, (e.clientX - r.left) / r.width)),
              Math.min(1, Math.max(0, (e.clientY - r.top) / r.height)));
    }
    el.addEventListener("pointerdown", function (e) {
      ativo = true;
      el.setPointerCapture(e.pointerId);
      posicao(e);
      e.preventDefault();
    });
    el.addEventListener("pointermove", function (e) { if (ativo) posicao(e); });
    el.addEventListener("pointerup", function () { ativo = false; });
    el.addEventListener("pointercancel", function () { ativo = false; });
  }

  function montaCor() {
    var grupo = document.createElement("div");
    grupo.className = "anot-grupo anot-cor";
    grupo.id = "anot-cor";

    var bolinha = botao("", "Cor atual (clique para escolher outra)", function () {
      if (seletorAberto()) fechaSeletor(); else abreSeletor();
    }, "anot-bolinha");
    bolinha.className = "anot-bolinha";
    bolinha.id = "anot-cor-atual";
    grupo.appendChild(bolinha);

    var seta = botao("▾", "Escolher cor", function () {
      if (seletorAberto()) fechaSeletor(); else abreSeletor();
    }, "anot-seta");
    seta.id = "anot-cor-seta";
    seta.setAttribute("aria-haspopup", "dialog");
    seta.setAttribute("aria-expanded", "false");
    grupo.appendChild(seta);

    var recentes = document.createElement("div");
    recentes.className = "anot-recentes";
    recentes.id = "anot-recentes";
    recentes.setAttribute("role", "group");
    recentes.setAttribute("aria-label", "Cores usadas recentemente");
    grupo.appendChild(recentes);

    var pop = document.createElement("div");
    pop.className = "anot-seletor";
    pop.id = "anot-seletor";
    pop.hidden = true;
    pop.setAttribute("role", "dialog");
    pop.setAttribute("aria-label", "Escolher cor");

    function entrada(tipo, id) {
      var i = document.createElement("input");
      i.type = tipo;
      i.id = id;
      i.spellcheck = false;
      i.autocomplete = "off";
      return i;
    }

    // O ESPECTRO é o seletor: um quadrado de saturação x brilho sobre a matiz
    // escolhida na barra do arco-íris. Clicar ou arrastar escolhe a cor vendo a
    // cor -- o código hex fica embaixo, só para quem quiser colar um valor.
    function mudaHsv(origem) {
      S.corPendente = deHsv(S.hsv.h, S.hsv.s, S.hsv.v);
      sincronizaSeletor(origem);
    }

    var sv = document.createElement("div");
    sv.className = "anot-sv";
    sv.id = "anot-cor-sv";
    sv.tabIndex = 0;
    sv.setAttribute("role", "slider");
    sv.setAttribute("aria-label", "Saturação e brilho");
    var svAlca = document.createElement("div");
    svAlca.className = "anot-sv-alca";
    svAlca.id = "anot-cor-sv-alca";
    sv.appendChild(svAlca);
    arrastavel(sv, function (x, y) { S.hsv.s = x; S.hsv.v = 1 - y; mudaHsv("sv"); });
    sv.addEventListener("keydown", function (e) {
      var passo = e.shiftKey ? 0.1 : 0.02;
      var d = { ArrowLeft: [-passo, 0], ArrowRight: [passo, 0], ArrowUp: [0, passo], ArrowDown: [0, -passo] }[e.key];
      if (!d) return;
      e.preventDefault();
      S.hsv.s = Math.min(1, Math.max(0, S.hsv.s + d[0]));
      S.hsv.v = Math.min(1, Math.max(0, S.hsv.v + d[1]));
      mudaHsv("sv");
    });
    pop.appendChild(sv);

    var matiz = document.createElement("div");
    matiz.className = "anot-matiz";
    matiz.id = "anot-cor-matiz";
    matiz.tabIndex = 0;
    matiz.setAttribute("role", "slider");
    matiz.setAttribute("aria-label", "Matiz");
    matiz.setAttribute("aria-valuemin", "0");
    matiz.setAttribute("aria-valuemax", "360");
    var matizAlca = document.createElement("div");
    matizAlca.className = "anot-matiz-alca";
    matizAlca.id = "anot-cor-matiz-alca";
    matiz.appendChild(matizAlca);
    arrastavel(matiz, function (x) {
      S.hsv.h = Math.min(359.9, x * 360);
      // escolher a matiz num cinza não mostraria cor nenhuma: leva para a
      // cor cheia, que é o que quem clicou no arco-íris quer ver
      if (S.hsv.s < 0.05 || S.hsv.v < 0.05) { S.hsv.s = 1; S.hsv.v = 1; }
      mudaHsv("matiz");
    });
    matiz.addEventListener("keydown", function (e) {
      var d = { ArrowLeft: -1, ArrowRight: 1 }[e.key];
      if (!d) return;
      e.preventDefault();
      S.hsv.h = (S.hsv.h + d * (e.shiftKey ? 30 : 5) + 360) % 360;
      mudaHsv("matiz");
    });
    pop.appendChild(matiz);

    var linha = document.createElement("div");
    linha.className = "anot-cor-linha";
    var amostra = document.createElement("span");
    amostra.className = "anot-amostra";
    amostra.id = "anot-cor-amostra";
    amostra.setAttribute("aria-hidden", "true");
    linha.appendChild(amostra);
    var hex = entrada("text", "anot-cor-hex");
    hex.maxLength = 22;
    hex.setAttribute("aria-label", "Código da cor (hex ou rgb)");
    hex.placeholder = "#eb6834";
    hex.addEventListener("input", function () {
      var cor = normalizaCor(hex.value);
      if (!cor) { hex.setAttribute("aria-invalid", "true"); return; }
      hex.removeAttribute("aria-invalid");
      S.corPendente = cor;
      sincronizaSeletor("hex");
    });
    linha.appendChild(hex);
    pop.appendChild(linha);

    var ok = botao("Aplicar", "Aplicar a cor e fechar", fechaSeletor, "principal");
    pop.appendChild(ok);

    // Enter em qualquer campo fecha e aplica, como o botão
    pop.addEventListener("keydown", function (e) {
      if (e.key === "Enter") { e.preventDefault(); fechaSeletor(); }
    });
    grupo.appendChild(pop);

    // Clique fora do seletor fecha (e aplica). Em captura, para funcionar
    // mesmo quando o clique cai num elemento que interrompe a propagação.
    document.addEventListener("pointerdown", function (e) {
      if (seletorAberto() && !grupo.contains(e.target)) fechaSeletor();
    }, true);

    return grupo;
  }

  function atualizaCores() {
    var atual = document.getElementById("anot-cor-atual");
    if (atual) {
      atual.style.background = S.cor;
      atual.dataset.cor = S.cor;
      atual.setAttribute("aria-label", "Cor atual " + S.cor + " (clique para escolher outra)");
    }
    var host = document.getElementById("anot-recentes");
    if (!host) return;
    // só redesenha a fileira se ela mudou, para não perder o foco do teclado
    var assinatura = S.recentes.join(",");
    if (host.dataset.assinatura === assinatura) return;
    host.dataset.assinatura = assinatura;
    host.innerHTML = "";
    S.recentes.forEach(function (cor) {
      var b = botao("", "Usar " + cor, function () { aplicaCor(cor); }, "anot-recente");
      b.className = "anot-recente";
      b.style.background = cor;
      b.dataset.recente = cor;
      host.appendChild(b);
    });
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

  function grupo(id, sempre) {
    var g = document.createElement("div");
    g.className = "anot-grupo" + (sempre ? " sempre" : "");
    if (id) g.id = id;
    return g;
  }

  function escolheFerramenta(id) {
    S.ferramenta = id;
    // lembrada na sessão: o modo reabre com a última ferramenta usada
    grava("sessionStorage", CHAVE_FERRAMENTA, id);
    atualizaBotoes();
  }

  function montaBarra() {
    var barra = document.createElement("div");
    barra.className = "anot-barra";
    barra.id = "anot-barra";

    var liga = grupo(null, true);
    var alterna = botao("Desenhar", "Ligar o modo de desenho (D)", function () {
      ligaDesenho(!S.ligado);
    }, "principal");
    alterna.id = "anot-toggle";
    liga.appendChild(alterna);
    barra.appendChild(liga);

    var ferr = grupo("anot-ferramentas");
    FERRAMENTAS.forEach(function (f) {
      var b = botao(f.rotulo, f.rotulo + " (" + f.tecla + ")", function () { escolheFerramenta(f.id); });
      b.dataset.ferramenta = f.id;
      ferr.appendChild(b);
    });
    barra.appendChild(ferr);

    barra.appendChild(montaCor());

    var esp = grupo("anot-espessuras");
    ESPESSURAS.forEach(function (e, i) {
      var b = botao(ROTULOS_ESPESSURA[i], "Espessura " + ROTULOS_ESPESSURA[i],
        function () { S.espessura = e; atualizaBotoes(); });
      b.dataset.espessura = String(e);
      esp.appendChild(b);
    });
    barra.appendChild(esp);

    var acoes = grupo();
    var bDepois = botao("Só a partir daqui", "O traço aparece só do instante em que foi desenhado",
      function () { S.soDepois = !S.soDepois; atualizaBotoes(); });
    bDepois.id = "anot-sodepois";
    acoes.appendChild(bDepois);
    acoes.appendChild(botao("Desfazer", "Desfazer (Ctrl+Z)", desfaz)).id = "anot-desfazer";
    acoes.appendChild(botao("Refazer", "Refazer (Ctrl+Shift+Z)", refaz)).id = "anot-refazer";
    acoes.appendChild(botao("Limpar", "Apagar todos os desenhos deste round", limpa));
    barra.appendChild(acoes);

    // Arquivo funciona com o desenho desligado: quem recebe um arquivo quer
    // abrir e ver, não desenhar.
    var arquivo = grupo(null, true);
    arquivo.appendChild(botao("Imagem", "Baixar a imagem do mapa com o carimbo do contexto", exportaImagem))
      .id = "anot-imagem";
    arquivo.appendChild(botao("Exportar", "Salvar as anotações desta partida num arquivo JSON", exportaAnotacoes))
      .id = "anot-exportar";
    var escolhe = document.createElement("input");
    escolhe.type = "file";
    escolhe.accept = ".json,application/json";
    escolhe.hidden = true;
    escolhe.id = "anot-arquivo";
    escolhe.addEventListener("change", function () {
      var f = escolhe.files && escolhe.files[0];
      if (!f) return;
      f.text().then(function (texto) {
        avisa(importaTexto(texto).msg);
      }).catch(function () { avisa("Não foi possível ler o arquivo."); });
      escolhe.value = "";   // escolher o mesmo arquivo de novo dispara de novo
    });
    arquivo.appendChild(escolhe);
    arquivo.appendChild(botao("Importar", "Carregar anotações de um arquivo JSON", function () { escolhe.click(); }))
      .id = "anot-importar";
    barra.appendChild(arquivo);

    var vista = grupo(null, true);
    vista.appendChild(botao("−", "Diminuir o zoom", function () {
      aplicaZoom(S.view.zoom / ZOOM_PASSO, opts.radar.width / 2, opts.radar.height / 2);
    }));
    var lupa = botao("100%", "Voltar ao tamanho original (0). Com zoom, segure espaço e arraste para mover o mapa", reseta);
    lupa.id = "anot-zoom";
    vista.appendChild(lupa);
    vista.appendChild(botao("+", "Aumentar o zoom", function () {
      aplicaZoom(S.view.zoom * ZOOM_PASSO, opts.radar.width / 2, opts.radar.height / 2);
    }));
    var fs = botao("Tela cheia", "Mapa em tela cheia (F)", alternaTelaCheia);
    fs.id = "anot-fs";
    vista.appendChild(fs);
    barra.appendChild(vista);

    var status = document.createElement("span");
    status.className = "anot-status";
    status.id = "anot-status";
    status.setAttribute("role", "status");
    status.textContent = S.aviso;
    barra.appendChild(status);

    return barra;
  }

  function avisa(msg) {
    S.aviso = msg || "";
    var el = document.getElementById("anot-status");
    if (el) el.textContent = S.aviso;
  }

  function atualizaBotoes() {
    var t = document.getElementById("anot-toggle");
    if (t) {
      t.classList.toggle("on", S.ligado);
      t.textContent = S.ligado ? "Desenhando" : "Desenhar";
      t.setAttribute("aria-pressed", S.ligado ? "true" : "false");
      t.title = S.ligado ? "Sair do modo de desenho (D ou Esc)" : "Ligar o modo de desenho (D)";
    }
    var barra = document.getElementById("anot-barra");
    if (barra) barra.classList.toggle("ativo", S.ligado);

    Array.prototype.forEach.call(document.querySelectorAll("[data-ferramenta]"), function (b) {
      b.classList.toggle("on", b.dataset.ferramenta === S.ferramenta);
    });
    Array.prototype.forEach.call(document.querySelectorAll("[data-espessura]"), function (b) {
      b.classList.toggle("on", b.dataset.espessura === String(S.espessura));
    });
    atualizaCores();

    var sd = document.getElementById("anot-sodepois");
    if (sd) sd.classList.toggle("on", S.soDepois);
    var z = document.getElementById("anot-zoom");
    if (z) z.textContent = Math.round(S.view.zoom * 100) + "%";
    var d = document.getElementById("anot-desfazer");
    if (d) d.disabled = !tracosDoRound().length;
    var r = document.getElementById("anot-refazer");
    if (r) r.disabled = !S.refazer.length;
  }

  /** Um clique liga E já deixa desenhar: a ferramenta ativa é a última usada
      na sessão, ou a caneta quando não houve escolha. Desligar devolve o clique
      ao que está embaixo -- jogador, ícone de granada, o próprio mapa. */
  function ligaDesenho(on) {
    S.ligado = !!on;
    if (!S.ferramenta) S.ferramenta = FERRAMENTA_PADRAO;
    camada.style.pointerEvents = S.ligado ? "auto" : "none";
    camada.style.cursor = S.ligado ? "crosshair" : "";
    rascunho.style.pointerEvents = "none";
    if (!S.ligado) {
      S.tracando = null;
      repintaRascunho();
      fechaSeletor();
    }
    atualizaBotoes();
  }

  /* ---------------------------------------------------------------------
     Init
     --------------------------------------------------------------------- */
  function init(o) {
    opts = o;
    cv = opts.mapCanvas;

    camada = document.createElement("canvas");
    rascunho = document.createElement("canvas");
    camada.className = "anot-camada";
    rascunho.className = "anot-camada anot-rascunho";
    camada.setAttribute("aria-hidden", "true");
    rascunho.setAttribute("aria-hidden", "true");
    cv.parentNode.insertBefore(camada, cv.nextSibling);
    cv.parentNode.insertBefore(rascunho, camada.nextSibling);
    ctxC = camada.getContext("2d");
    ctxR = rascunho.getContext("2d");

    var ferramenta = le("sessionStorage", CHAVE_FERRAMENTA);
    if (ferramenta && FERRAMENTAS.some(function (f) { return f.id === ferramenta; })) S.ferramenta = ferramenta;
    var recentes = lerJson(le("localStorage", CHAVE_RECENTES));
    if (Array.isArray(recentes)) S.recentes = recentes.map(normalizaCor).filter(Boolean).slice(0, MAX_RECENTES);
    if (S.recentes.length) S.cor = S.recentes[0];

    opts.palco.insertBefore(montaBarra(), opts.palco.firstChild);

    S.rounds = carregaDoNavegador();
    S.pronto = true;
    ligaDesenho(false);
    reprojetaTudo();

    // Eventos de PONTEIRO, não de mouse: o mesmo código atende mouse, toque e
    // caneta de tablet, sem um caminho separado por dispositivo.
    camada.addEventListener("pointerdown", function (e) { comecou(e); panComeca(e); });
    camada.addEventListener("pointermove", function (e) { moveu(e); panMove(e); });
    camada.addEventListener("pointerup", function (e) { soltou(e); panTermina(); });
    camada.addEventListener("pointercancel", function (e) { soltou(e); panTermina(); });
    // Com o desenho desligado a camada deixa o ponteiro passar, e o pan com
    // zoom acontece no próprio mapa.
    cv.addEventListener("pointerdown", panComeca);
    cv.addEventListener("pointermove", panMove);
    cv.addEventListener("pointerup", panTermina);
    cv.addEventListener("pointercancel", panTermina);
    camada.addEventListener("wheel", zoomDaRoda, { passive: false });
    cv.addEventListener("wheel", zoomDaRoda, { passive: false });

    // Todos os gatilhos de mudança de tamanho caem na mesma função.
    window.addEventListener("resize", pedeReprojecao);
    document.addEventListener("fullscreenchange", mudouTelaCheia);
    document.addEventListener("webkitfullscreenchange", mudouTelaCheia);
    vigiaDensidade();
    // O observador pega o que não dispara `resize`: a aba do replay aparecendo
    // depois de escondida, a coluna mudando de largura com o layout.
    if (window.ResizeObserver) new ResizeObserver(pedeReprojecao).observe(cv.parentNode);

    // Saindo da página, grava na hora o que ainda estava no atraso.
    window.addEventListener("pagehide", gravaPendentes);
    document.addEventListener("visibilitychange", function () {
      if (document.visibilityState === "hidden") gravaPendentes();
    });

    opts.palco.addEventListener("pointermove", function () {
      if (emTelaCheia()) acordaControles();
    });
    opts.palco.addEventListener("pointerenter", function () { S.sobreMapa = true; });
    opts.palco.addEventListener("pointerleave", function () { S.sobreMapa = false; });
    document.addEventListener("keyup", function (e) {
      if (e.code === "Space" && S.espaco) modoPan(false);
    });
    window.addEventListener("blur", function () { if (S.espaco) modoPan(false); });

    document.addEventListener("keydown", function (e) {
      var editando = /^(INPUT|TEXTAREA|SELECT)$/.test((e.target || {}).tagName || "");
      if (e.key === "Escape") {
        if (seletorAberto()) { e.preventDefault(); fechaSeletor(); return; }
        if (S.ligado && !editando) { e.preventDefault(); ligaDesenho(false); }
        return;
      }
      if (editando) return;
      // Espaço só é nosso com o ponteiro sobre o mapa; fora dele continua
      // rolando a página, como o navegador faz.
      if (e.code === "Space" && (S.sobreMapa || S.espaco)) {
        e.preventDefault();
        if (!S.espaco) modoPan(true);
        return;
      }
      var k = e.key.toLowerCase();
      if ((e.ctrlKey || e.metaKey) && k === "z") {
        e.preventDefault();
        if (e.shiftKey) refaz(); else desfaz();
        return;
      }
      if (e.ctrlKey || e.metaKey || e.altKey) return;
      if (k === "f") { e.preventDefault(); alternaTelaCheia(); return; }
      if (k === "d") { e.preventDefault(); ligaDesenho(!S.ligado); return; }
      if (k === "0") { e.preventDefault(); reseta(); return; }
      FERRAMENTAS.forEach(function (f) {
        if (e.key === f.tecla) escolheFerramenta(f.id);
      });
    });

    atualizaBotoes();
  }

  return {
    init: init,
    applyView: applyView,
    /** O template chama a cada quadro. Só repinta quando o conjunto VISÍVEL
        muda -- o mapa se movendo não pode forçar redesenho dos traços. */
    onFrame: function (pos) {
      S.pos = pos;
      var n = visiveis().length;
      if (n !== S.visiveisAntes) { S.visiveisAntes = n; repinta(); }
    },
    /** Trocar de round troca o conjunto de desenhos. Nada de rabisco de um
        round vazando no outro -- e nada se perde: o modelo guarda todos. */
    setRound: function (n) {
      if (S.round === n) return;
      S.round = n;
      S.refazer = [];
      S.tracando = null;
      S.visiveisAntes = -1;
      repinta();
      repintaRascunho();
      atualizaBotoes();
    },
    emTelaCheia: emTelaCheia,
    exportaImagem: exportaImagem,
    _interno: {
      S: S, ESPESSURAS: ESPESSURAS, FERRAMENTAS: FERRAMENTAS, FORMATO: FORMATO,
      jogoParaPixel: jogoParaPixel, pixelParaJogo: pixelParaJogo,
      caixaDoMapa: caixaDoMapa, desfaz: desfaz, refaz: refaz,
      tracosDoRound: tracosDoRound, visiveis: visiveis,
      documento: documento, importaTexto: importaTexto,
      reprojetaTudo: reprojetaTudo, gravaPendentes: gravaPendentes,
      aplicaZoom: aplicaZoom, reseta: reseta,
      normalizaCor: normalizaCor,
      radar: function () { return opts.radar; }
    }
  };
})();
