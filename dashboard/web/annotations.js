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
   dela está em annotations.css. Projeção, zoom, tamanho interno, armazenamento,
   traço e seletor de cor vêm de map_core.js (MapCore), compartilhados com o
   replay e a prancheta.
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

  var ZOOM_PASSO = MapCore.ZOOM_PASSO;

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
  var armazenamento = MapCore.criaArmazem(function () { falhouArmazem(); });
  function le(qual, chave) { return armazenamento.le(qual, chave); }
  function grava(qual, chave, valor) { return armazenamento.grava(qual, chave, valor); }
  function remove(qual, chave) { armazenamento.remove(qual, chave); }
  function chaves(qual) { return armazenamento.chaves(qual); }
  function falhouArmazem() {
    if (!S.armazemOk) return;
    S.armazemOk = false;
    avisa("Este navegador não deixou salvar as anotações: use Exportar para guardá-las.");
  }

  var lerJson = MapCore.lerJson;

  /* ---------------------------------------------------------------------
     Projeção. A mesma conta do resto do projeto, nos dois sentidos.
     --------------------------------------------------------------------- */
  function jogoParaPixel(x, y) { return MapCore.jogoParaPixel(opts.radar, x, y); }
  function pixelParaJogo(px, py) { return MapCore.pixelParaJogo(opts.radar, px, py); }

  /** Ponteiro na tela -> pixel do radar, desfazendo o tamanho na tela, o zoom e
      o pan. A caixa é a do MAPA: a camada é posicionada exatamente sobre ela. */
  function eventoParaPixel(e) { return MapCore.eventoParaPixel(cv, opts.radar, e, S.view); }

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
  function applyView(ctx) { MapCore.applyView(ctx, opts ? opts.radar : null, S.view); }

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
  function caminhoDoTraco(ctx, t) { MapCore.caminhoDoTraco(ctx, t, opts.radar); }

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
  function caixaDoMapa(dispW, dispH) { return MapCore.caixaDoMapa(opts.radar, dispW, dispH); }

  /** Reprojeta e redesenha TUDO.

      Atribuir width/height a um canvas apaga o que está nele, sem aviso. Então
      toda mudança de tamanho termina redesenhando as três camadas a partir dos
      dados -- o mapa pelo template (opts.redraw), as anotações pelo modelo. Um
      redesenho que esquecesse uma delas deixaria aquela camada em branco até o
      próximo quadro que, com o replay pausado, não vem nunca. */
  function reprojetaTudo() {
    if (!S.pronto) return;

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

    // Resolução INTERNA = tamanho na tela x densidade de pixels, com teto
    // (MapCore.tamanhoInterno).
    var dpr = window.devicePixelRatio || 1;
    var tam = MapCore.tamanhoInterno(opts.radar, larguraCss, dpr);
    var w = tam.w, h = tam.h;
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
  var reprojecaoAgrupada = MapCore.agrupaPorQuadro(function () { reprojetaTudo(); });
  function pedeReprojecao() { reprojecaoAgrupada(); }

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
    if (MapCore.aplicaZoom(S.view, opts.radar, novo, centroX, centroY)) pedeRedesenho();
  }

  function limitaPan() { MapCore.limitaPan(S.view, opts.radar); }

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
  function emTelaCheia() { return !!opts && MapCore.emTelaCheia(opts.palco); }

  function alternaTelaCheia() { MapCore.alternaTelaCheia(opts.palco); }

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

  var normalizaCor = MapCore.normalizaCor;
  var botao = MapCore.botao;

  // O seletor escreve direto no S desta camada (cor, recentes, corPendente,
  // hsv): é o mesmo estado que a barra e os traços leem.
  var seletor = null;
  function cores() {
    if (!seletor) {
      seletor = MapCore.seletorDeCor({
        estado: S, armazem: armazenamento, chaveRecentes: CHAVE_RECENTES,
        maxRecentes: MAX_RECENTES, palco: function () { return opts.palco; },
        aoMudar: function () { atualizaBotoes(); }
      });
    }
    return seletor;
  }
  function seletorAberto() { return cores().seletorAberto(); }
  function fechaSeletor() { cores().fechaSeletor(); }
  function montaCor() { return cores().montaCor(); }
  function atualizaCores() { cores().atualizaCores(); }

  /* ---------------------------------------------------------------------
     Barra de ferramentas
     --------------------------------------------------------------------- */
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
