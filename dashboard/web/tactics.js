/* =========================================================================
   Prancheta tática: peças, granadas com origem e destino, passos numerados.

   O modelo é o de metrics/tactics.py (lá está o PORQUÊ, com calma): a tática é
   um LOG DE OPERAÇÕES com id estável, autor e número de ordem, e o estado é
   derivado aplicando o log em ordem (seq, autor, id). Este arquivo é o espelho
   daquele módulo -- há teste que aplica o mesmo log nos dois e compara.

   Tudo em coordenada de JOGO. A tela só projeta.

   A persistência fica atrás de `Armazem` (lista / carrega / grava / apaga).
   Hoje é o navegador; um servidor entra implementando os mesmos quatro métodos,
   sem a interface da página mudar.
   ========================================================================= */
var Prancheta = (function () {
  "use strict";

  var IDENTIFICADOR = "prancheta-cs2";
  var FORMATO = 1;
  var LADOS = ["ct", "t"];
  var PECAS_POR_LADO = 5;
  var ARMAS = ["smoke", "flash", "he", "molotov", "decoy"];
  var NOME_ARMA = { smoke: "Smoke", flash: "Flash", he: "HE", molotov: "Molotov", decoy: "Decoy" };

  // Tamanhos em PIXEL DO RADAR (1024 de lado nos radares do projeto): a peça
  // cresce e encolhe junto com o mapa.
  var RAIO_PECA = 15;
  var RAIO_GRANADA = 11;
  var RAIO_ALCA = 9;          // pegar a ponta da granada para arrastar

  // Raio da busca "quero a granada AQUI", em unidade de jogo. É parâmetro de
  // TELA, não de métrica: a pessoa ajusta no controle ao lado da busca.
  var RAIO_BUSCA_PADRAO = 200;
  var MAX_RESULTADOS = 40;

  var ATRASO_GRAVACAO_MS = 400;

  /* ---------------------------------------------------------------------
     Modelo -- espelho de metrics/tactics.py
     --------------------------------------------------------------------- */
  function chaveDeOrdem(a, b) {
    if (a.seq !== b.seq) return a.seq - b.seq;
    if (a.autor !== b.autor) return a.autor < b.autor ? -1 : 1;
    if (a.id !== b.id) return a.id < b.id ? -1 : 1;
    return 0;
  }

  function aplica(operacoes) {
    var estado = { titulo: "", passos: [], pecas: {}, granadas: {} };
    var passos = {}, ordem = [];
    operacoes.slice().sort(chaveDeOrdem).forEach(function (op) {
      var p, g;
      switch (op.tipo) {
        case "renomeia": estado.titulo = op.titulo; break;
        case "cria_passo":
          if (!passos[op.passo]) { passos[op.passo] = { passo: op.passo, titulo: op.titulo }; ordem.push(op.passo); }
          break;
        case "renomeia_passo": if (passos[op.passo]) passos[op.passo].titulo = op.titulo; break;
        case "remove_passo":
          if (passos[op.passo]) { delete passos[op.passo]; ordem.splice(ordem.indexOf(op.passo), 1); }
          break;
        case "cria_peca":
          if (!estado.pecas[op.peca] && passos[op.passo]) {
            estado.pecas[op.peca] = { lado: op.lado, rotulo: op.rotulo, posicoes: {} };
            estado.pecas[op.peca].posicoes[op.passo] = [+op.x, +op.y];
          }
          break;
        case "move_peca":
          p = estado.pecas[op.peca];
          if (p && passos[op.passo]) p.posicoes[op.passo] = [+op.x, +op.y];
          break;
        case "remove_peca": delete estado.pecas[op.peca]; break;
        case "cria_granada":
          if (!estado.granadas[op.granada] && passos[op.passo]) {
            estado.granadas[op.granada] = {
              arma: op.arma, passo: op.passo,
              origem: op.origem.map(Number), destino: op.destino.map(Number),
              arremesso: op.arremesso === undefined ? null : op.arremesso
            };
          }
          break;
        case "move_granada":
          g = estado.granadas[op.granada];
          if (g) {
            g.origem = op.origem.map(Number); g.destino = op.destino.map(Number);
            g.arremesso = null;   // arrastada à mão deixou de ser o arremesso real
          }
          break;
        case "remove_granada": delete estado.granadas[op.granada]; break;
      }
    });
    estado.passos = ordem.map(function (k) { return passos[k]; });
    Object.keys(estado.pecas).forEach(function (k) {
      var pos = estado.pecas[k].posicoes, limpo = {};
      Object.keys(pos).forEach(function (s) { if (passos[s]) limpo[s] = pos[s]; });
      estado.pecas[k].posicoes = limpo;
    });
    Object.keys(estado.granadas).forEach(function (k) {
      if (!passos[estado.granadas[k].passo]) delete estado.granadas[k];
    });
    return estado;
  }

  function posicaoNoPasso(peca, passos, indice) {
    var pos = null;
    for (var i = 0; i <= indice && i < passos.length; i++) {
      var p = peca.posicoes[passos[i].passo];
      if (p) pos = p;
    }
    return pos;
  }

  function mescla(a, b) {
    if (a.id !== b.id) throw new Error("mesclar táticas diferentes: ids distintos");
    var porId = {};
    a.operacoes.forEach(function (op) { porId[op.id] = op; });
    b.operacoes.forEach(function (op) { if (!porId[op.id]) porId[op.id] = op; });
    var unidas = Object.keys(porId).map(function (k) { return porId[k]; }).sort(chaveDeOrdem);
    var saida = JSON.parse(JSON.stringify(a));
    saida.operacoes = unidas;
    saida.contador = Math.max(a.contador, b.contador);
    return saida;
  }

  function novoId() {
    if (window.crypto && crypto.randomUUID) return crypto.randomUUID().replace(/-/g, "");
    var s = "";
    for (var i = 0; i < 32; i++) s += Math.floor(Math.random() * 16).toString(16);
    return s;
  }

  function agora() { return new Date().toISOString(); }

  /* ---------------------------------------------------------------------
     Armazem -- a interface de persistência. A página só fala com isto.
     Contrato:
       lista(mapa)  -> [{id, titulo, atualizada_em, autores}]  (mais recente primeiro)
       carrega(id)  -> documento ou null
       grava(doc)   -> true se gravou
       apaga(id)    -> true se apagou
     --------------------------------------------------------------------- */
  function ArmazemDoNavegador(prefixo) {
    // o acesso seguro (try/catch em tudo) é o do MapCore, o mesmo da anotação
    var A = MapCore.criaArmazem();
    function le(chave) { return MapCore.lerJson(A.le("localStorage", prefixo + chave)); }
    function escreve(chave, valor) { return A.grava("localStorage", prefixo + chave, JSON.stringify(valor)); }
    function indice() { return le("indice") || {}; }
    return {
      tipo: "navegador",
      lista: function (mapa) {
        var ind = indice();
        return Object.keys(ind).map(function (id) { return ind[id]; })
          .filter(function (r) { return r.mapa === mapa; })
          .sort(function (a, b) { return a.atualizada_em < b.atualizada_em ? 1 : -1; });
      },
      carrega: function (id) { return le("tatica:" + id); },
      grava: function (doc) {
        if (!escreve("tatica:" + doc.id, doc)) return false;
        var ind = indice(), est = aplica(doc.operacoes);
        var autores = {};
        doc.operacoes.forEach(function (op) { autores[op.autor] = true; });
        ind[doc.id] = { id: doc.id, mapa: doc.mapa, titulo: est.titulo || "(sem título)",
                        atualizada_em: agora(), autores: Object.keys(autores).sort() };
        return escreve("indice", ind);
      },
      apaga: function (id) {
        if (!A.remove("localStorage", prefixo + "tatica:" + id)) return false;
        var ind = indice(); delete ind[id];
        return escreve("indice", ind);
      },
      autor: function (novo) {
        if (novo !== undefined) escreve("autor", novo);
        return le("autor");
      }
    };
  }

  /* ---------------------------------------------------------------------
     Estado da página
     --------------------------------------------------------------------- */
  var cfg = null;             // {radar, biblioteca, mapa, mapas}
  var Armazem = null;
  var S = {
    doc: null, estado: null, passo: 0,     // índice do passo na lista
    ferramenta: "mover", arma: "smoke",
    sel: null,                              // {tipo: "peca"|"granada", id}
    arrasto: null,
    origemPendente: null,                   // granada à mão: origem já clicada
    busca: null,                            // {ponto: [x,y], raio, resultados: []}
    raioBusca: RAIO_BUSCA_PADRAO,
    soParado: false,                        // busca só com arremesso sem movimento
    aviso: "",
    gravacoes: 0
  };
  var cv = null, ctx = null, img = null, timerGravar = null;

  function autor() { return (Armazem.autor() || "").trim() || "anônimo"; }

  function emite(tipo, dados) {
    var op = { id: novoId(), seq: S.doc.contador + 1, autor: autor(), em: agora(), tipo: tipo };
    Object.keys(dados).forEach(function (k) { op[k] = dados[k]; });
    S.doc.contador = op.seq;
    S.doc.operacoes.push(op);
    S.estado = aplica(S.doc.operacoes);
    agendaGravacao();
    desenha();
    atualizaPainel();
    return op;
  }

  function agendaGravacao() {
    clearTimeout(timerGravar);
    timerGravar = setTimeout(gravaAgora, ATRASO_GRAVACAO_MS);
  }
  function gravaAgora() {
    clearTimeout(timerGravar);
    if (!S.doc) return;
    S.aviso = Armazem.grava(S.doc) ? "" : "Não foi possível gravar neste navegador: exporte o arquivo para não perder.";
    S.gravacoes++;
    atualizaBiblioteca();
    atualizaAviso();
  }

  function novaTatica() {
    var doc = {
      formato: IDENTIFICADOR, versao: FORMATO, id: novoId(), mapa: cfg.mapa,
      criada_por: autor(), criada_em: agora(), calibracao: cfg.radar.calibracao,
      contador: 0, operacoes: []
    };
    S.doc = doc;
    emite("renomeia", { titulo: "Nova tática" });
    emite("cria_passo", { passo: novoId(), titulo: "" });
    S.passo = 0; S.sel = null; S.busca = null;
    gravaAgora();
    atualizaTudo();
  }

  function abre(id) {
    var doc = Armazem.carrega(id);
    if (!doc) return false;
    S.doc = doc; S.estado = aplica(doc.operacoes);
    S.passo = 0; S.sel = null; S.busca = null;
    atualizaTudo();
    return true;
  }

  /* ---------------------------------------------------------------------
     Projeção -- a do MapCore (map_core.js), a mesma de metrics/annotations.py
     --------------------------------------------------------------------- */
  function jogoParaPixel(x, y) { return MapCore.jogoParaPixel(cfg.radar, x, y); }
  function pixelParaJogo(px, py) { return MapCore.pixelParaJogo(cfg.radar, px, py); }
  function eventoParaPixel(e) { return MapCore.eventoParaPixel(cv, cfg.radar, e, null); }

  /* ---------------------------------------------------------------------
     Desenho
     --------------------------------------------------------------------- */
  function cor(nome) { return getComputedStyle(document.documentElement).getPropertyValue(nome).trim(); }
  var COR_ARMA = { smoke: "#9aa5b1", flash: "#f2d34f", he: "#d94c4c", molotov: "#f08a24", decoy: "#8b7bd8" };

  function redimensiona() {
    // O lado sai da largura ÚTIL do palco (sem o padding): usar a caixa inteira
    // deixava o canvas mais largo que o espaço, o max-width cortava só a
    // largura, e o mapa aparecia esticado na vertical.
    var palco = cv.parentNode, est = getComputedStyle(palco);
    var util = palco.clientWidth - parseFloat(est.paddingLeft) - parseFloat(est.paddingRight);
    var lado = Math.max(200, Math.floor(Math.min(util, window.innerHeight - 40)));
    var tam = MapCore.tamanhoInterno(cfg.radar, lado, window.devicePixelRatio || 1);
    cv.style.width = lado + "px"; cv.style.height = lado + "px";
    cv.width = tam.w; cv.height = tam.h;
    desenha();
  }

  function desenha() {
    if (!ctx || !S.estado) return;
    var k = cv.width / cfg.radar.width;
    ctx.setTransform(1, 0, 0, 1, 0, 0);
    ctx.clearRect(0, 0, cv.width, cv.height);
    ctx.setTransform(k, 0, 0, k, 0, 0);
    if (img && img.complete) ctx.drawImage(img, 0, 0, cfg.radar.width, cfg.radar.height);

    desenhaBusca();
    var passos = S.estado.passos, i = S.passo;
    // granadas: dos passos anteriores apagadas, as do passo atual cheias
    Object.keys(S.estado.granadas).forEach(function (gid) {
      var g = S.estado.granadas[gid];
      var idx = indiceDoPasso(g.passo);
      if (idx > i) return;
      var arr = S.arrasto && S.arrasto.tipo === "granada" && S.arrasto.id === gid ? S.arrasto : null;
      desenhaGranada(g, idx === i ? 1 : 0.35, idx + 1, arr, S.sel && S.sel.id === gid);
    });
    if (S.origemPendente) {
      var o = jogoParaPixel(S.origemPendente[0], S.origemPendente[1]);
      ctx.fillStyle = COR_ARMA[S.arma]; ctx.beginPath(); ctx.arc(o[0], o[1], 5, 0, 2 * Math.PI); ctx.fill();
    }
    // peças: rastro do passo anterior, depois a peça
    Object.keys(S.estado.pecas).forEach(function (pid) {
      var p = S.estado.pecas[pid];
      var pos = posicaoNoPasso(p, passos, i);
      if (S.arrasto && S.arrasto.tipo === "peca" && S.arrasto.id === pid) pos = S.arrasto.jogo;
      if (!pos) return;
      var ant = i > 0 ? posicaoNoPasso(p, passos, i - 1) : null;
      if (ant && (ant[0] !== pos[0] || ant[1] !== pos[1])) desenhaMovimento(ant, pos, p.lado);
      desenhaPeca(p, pos, S.sel && S.sel.id === pid);
    });
  }

  function desenhaMovimento(de, para, lado) {
    var a = jogoParaPixel(de[0], de[1]), b = jogoParaPixel(para[0], para[1]);
    ctx.save();
    ctx.strokeStyle = cor(lado === "ct" ? "--ct" : "--t");
    ctx.globalAlpha = 0.7; ctx.lineWidth = 3; ctx.setLineDash([8, 6]);
    ctx.beginPath(); ctx.moveTo(a[0], a[1]); ctx.lineTo(b[0], b[1]); ctx.stroke();
    ctx.restore();
  }

  function desenhaPeca(p, pos, selecionada) {
    var c = jogoParaPixel(pos[0], pos[1]);
    ctx.save();
    ctx.fillStyle = cor(p.lado === "ct" ? "--ct" : "--t");
    ctx.strokeStyle = selecionada ? "#ffffff" : "rgba(0,0,0,0.55)";
    ctx.lineWidth = selecionada ? 4 : 2;
    ctx.beginPath(); ctx.arc(c[0], c[1], RAIO_PECA, 0, 2 * Math.PI); ctx.fill(); ctx.stroke();
    ctx.fillStyle = "#ffffff"; ctx.font = "600 15px Figtree, system-ui, sans-serif";
    ctx.textAlign = "center"; ctx.textBaseline = "middle";
    ctx.fillText(p.rotulo, c[0], c[1] + 1);
    ctx.restore();
  }

  function desenhaGranada(g, alfa, numeroPasso, arrasto, selecionada) {
    var o = g.origem, d = g.destino;
    if (arrasto) { o = arrasto.origem; d = arrasto.destino; }
    var a = jogoParaPixel(o[0], o[1]), b = jogoParaPixel(d[0], d[1]);
    ctx.save();
    ctx.globalAlpha = alfa;
    ctx.strokeStyle = COR_ARMA[g.arma]; ctx.lineWidth = selecionada ? 4 : 2.5;
    if (!g.arremesso) ctx.setLineDash([4, 4]);   // desenhada à mão: tracejada
    ctx.beginPath(); ctx.moveTo(a[0], a[1]); ctx.lineTo(b[0], b[1]); ctx.stroke();
    ctx.setLineDash([]);
    ctx.fillStyle = COR_ARMA[g.arma];
    ctx.beginPath(); ctx.arc(a[0], a[1], 4.5, 0, 2 * Math.PI); ctx.fill();
    ctx.beginPath(); ctx.arc(b[0], b[1], RAIO_GRANADA, 0, 2 * Math.PI); ctx.fill();
    ctx.strokeStyle = selecionada ? "#ffffff" : "rgba(0,0,0,0.6)"; ctx.lineWidth = 2; ctx.stroke();
    ctx.fillStyle = "#111"; ctx.font = "700 12px Figtree, system-ui, sans-serif";
    ctx.textAlign = "center"; ctx.textBaseline = "middle";
    ctx.fillText(String(numeroPasso), b[0], b[1] + 1);
    ctx.restore();
  }

  function desenhaBusca() {
    if (!S.busca) return;
    var c = jogoParaPixel(S.busca.ponto[0], S.busca.ponto[1]);
    ctx.save();
    ctx.strokeStyle = "rgba(255,255,255,0.8)"; ctx.setLineDash([6, 5]); ctx.lineWidth = 2;
    ctx.beginPath(); ctx.arc(c[0], c[1], S.busca.raio * cfg.radar.scale_px_per_unit, 0, 2 * Math.PI); ctx.stroke();
    ctx.setLineDash([]);
    S.busca.resultados.forEach(function (r, n) {
      var a = jogoParaPixel(r.origem[0], r.origem[1]), b = jogoParaPixel(r.destino[0], r.destino[1]);
      var foco = S.busca.foco === n;
      ctx.globalAlpha = foco ? 1 : 0.45;
      ctx.strokeStyle = COR_ARMA[r.arma]; ctx.lineWidth = foco ? 3 : 1.2;
      ctx.beginPath(); ctx.moveTo(a[0], a[1]); ctx.lineTo(b[0], b[1]); ctx.stroke();
      ctx.fillStyle = COR_ARMA[r.arma];
      ctx.beginPath(); ctx.arc(a[0], a[1], foco ? 6 : 3.5, 0, 2 * Math.PI); ctx.fill();
    });
    ctx.restore();
  }

  function indiceDoPasso(passo) {
    for (var i = 0; i < S.estado.passos.length; i++) if (S.estado.passos[i].passo === passo) return i;
    return -1;
  }
  function passoAtual() { return S.estado.passos[S.passo].passo; }

  /* ---------------------------------------------------------------------
     Ponteiro
     --------------------------------------------------------------------- */
  function acha(px) {
    var passos = S.estado.passos, i = S.passo, achado = null, melhor = Infinity;
    function perto(pos, raio, qual) {
      var c = jogoParaPixel(pos[0], pos[1]);
      var d = Math.hypot(c[0] - px[0], c[1] - px[1]);
      if (d <= raio && d < melhor) { melhor = d; achado = qual; }
    }
    Object.keys(S.estado.pecas).forEach(function (pid) {
      var pos = posicaoNoPasso(S.estado.pecas[pid], passos, i);
      if (pos) perto(pos, RAIO_PECA + 3, { tipo: "peca", id: pid });
    });
    Object.keys(S.estado.granadas).forEach(function (gid) {
      var g = S.estado.granadas[gid];
      if (indiceDoPasso(g.passo) !== i) return;   // só se mexe no passo em que ela está
      perto(g.destino, RAIO_GRANADA + 3, { tipo: "granada", id: gid, ponta: "destino" });
      perto(g.origem, RAIO_ALCA, { tipo: "granada", id: gid, ponta: "origem" });
    });
    return achado;
  }

  function pointerDown(e) {
    if (!S.doc || e.button !== 0) return;
    var px = eventoParaPixel(e), g = pixelParaJogo(px[0], px[1]);
    if (S.ferramenta === "buscar") { busca(g); return; }
    if (S.ferramenta === "granada") {
      if (!S.origemPendente) { S.origemPendente = g; desenha(); return; }
      var o = S.origemPendente; S.origemPendente = null;
      var op = emite("cria_granada", { granada: novoId(), arma: S.arma, passo: passoAtual(),
                                       origem: [o[0], o[1]], destino: [g[0], g[1]], arremesso: null });
      S.sel = { tipo: "granada", id: op.granada };
      atualizaPainel(); desenha();
      return;
    }
    var alvo = acha(px);
    S.sel = alvo ? { tipo: alvo.tipo, id: alvo.id } : null;
    if (alvo) {
      cv.setPointerCapture(e.pointerId);
      if (alvo.tipo === "peca") {
        S.arrasto = { tipo: "peca", id: alvo.id, jogo: posicaoNoPasso(S.estado.pecas[alvo.id], S.estado.passos, S.passo), mexeu: false };
      } else {
        var gr = S.estado.granadas[alvo.id];
        S.arrasto = { tipo: "granada", id: alvo.id, ponta: alvo.ponta,
                      origem: gr.origem.slice(), destino: gr.destino.slice(), mexeu: false };
      }
    }
    atualizaPainel(); desenha();
  }

  function pointerMove(e) {
    if (!S.arrasto) return;
    var px = eventoParaPixel(e), g = pixelParaJogo(px[0], px[1]);
    S.arrasto.mexeu = true;
    if (S.arrasto.tipo === "peca") S.arrasto.jogo = g;
    else S.arrasto[S.arrasto.ponta] = [g[0], g[1]].concat(S.arrasto[S.arrasto.ponta].slice(2));
    desenha();
  }

  function pointerUp() {
    var a = S.arrasto; S.arrasto = null;
    if (!a || !a.mexeu) { desenha(); return; }
    if (a.tipo === "peca") emite("move_peca", { peca: a.id, passo: passoAtual(), x: a.jogo[0], y: a.jogo[1] });
    else emite("move_granada", { granada: a.id, origem: a.origem, destino: a.destino });
  }

  /* Banco de peças: arrastar do banco para o mapa cria a peça no passo atual. */
  function soltaDoBanco(e, lado, rotulo) {
    var c = cv.getBoundingClientRect();
    if (e.clientX < c.left || e.clientX > c.right || e.clientY < c.top || e.clientY > c.bottom) return;
    var px = eventoParaPixel(e), g = pixelParaJogo(px[0], px[1]);
    var op = emite("cria_peca", { peca: novoId(), lado: lado, rotulo: rotulo, passo: passoAtual(), x: g[0], y: g[1] });
    S.sel = { tipo: "peca", id: op.peca };
    atualizaPainel(); desenha();
  }

  function removeSelecionado() {
    if (!S.sel) return;
    if (S.sel.tipo === "peca") emite("remove_peca", { peca: S.sel.id });
    else emite("remove_granada", { granada: S.sel.id });
    S.sel = null; atualizaPainel(); desenha();
  }

  /* ---------------------------------------------------------------------
     Arremessos reais: "quero a granada AQUI"
     --------------------------------------------------------------------- */
  function busca(ponto) {
    var arr = (cfg.biblioteca && cfg.biblioteca.arremessos) || [];
    var raio = S.raioBusca;
    var res = [];
    arr.forEach(function (r) {
      if (r.arma !== S.arma) return;
      if (S.soParado && (r.movimento !== "parado" || r.no_ar)) return;
      var d = Math.hypot(r.destino[0] - ponto[0], r.destino[1] - ponto[1]);
      if (d <= raio) res.push({ r: r, d: d });
    });
    res.sort(function (a, b) { return a.d - b.d || (a.r.id < b.r.id ? -1 : 1); });
    S.busca = { ponto: ponto, raio: raio, total: res.length,
                resultados: res.slice(0, MAX_RESULTADOS).map(function (x) { return x.r; }), foco: null };
    desenha(); atualizaBusca();
  }

  function usaArremesso(r) {
    var op = emite("cria_granada", {
      granada: novoId(), arma: r.arma, passo: passoAtual(),
      origem: r.origem.slice(0, 2), destino: r.destino.slice(0, 2), arremesso: r
    });
    S.sel = { tipo: "granada", id: op.granada };
    S.busca = null; S.ferramenta = "mover";
    atualizaTudo();
  }

  /* ---------------------------------------------------------------------
     Painéis. Todo texto sai daqui, a partir do dado.
     --------------------------------------------------------------------- */
  function el(tag, attrs, filhos) {
    var n = document.createElement(tag);
    Object.keys(attrs || {}).forEach(function (k) {
      if (k === "texto") n.textContent = attrs[k];
      else if (k.indexOf("on") === 0) n.addEventListener(k.slice(2), attrs[k]);
      else n.setAttribute(k, attrs[k]);
    });
    (filhos || []).forEach(function (f) { if (f) n.appendChild(f); });
    return n;
  }
  function limpa(n) { while (n.firstChild) n.removeChild(n.firstChild); return n; }
  function $(id) { return document.getElementById(id); }

  function tempo(seg) {
    if (seg == null) return "";
    var s = Math.max(0, Math.round(seg));
    return Math.floor(s / 60) + ":" + String(s % 60).padStart(2, "0");
  }

  function descreveArremesso(r) {
    var partes = [];
    if (r.forca) partes.push(r.botao ? r.forca + " (" + r.botao + ")" : r.forca + " (" + r.velocidade + " u/s)");
    if (r.postura) partes.push(r.postura);
    if (r.movimento) partes.push(r.movimento);
    if (r.no_ar) partes.push("no ar (pulo)");
    return partes.join(" · ");
  }

  function atualizaTudo() {
    atualizaBiblioteca(); atualizaPassos(); atualizaPainel(); atualizaBusca(); atualizaFerramentas();
    atualizaAviso(); desenha();
  }

  function atualizaAviso() { $("pr-aviso").textContent = S.aviso; $("pr-aviso").hidden = !S.aviso; }

  function atualizaBiblioteca() {
    var sel = limpa($("pr-taticas"));
    var lista = Armazem.lista(cfg.mapa);
    lista.forEach(function (r) {
      var o = el("option", { value: r.id, texto: r.titulo + (r.autores.length > 1 ? " · " + r.autores.length + " autores" : "") });
      if (S.doc && r.id === S.doc.id) o.selected = true;
      sel.appendChild(o);
    });
    $("pr-titulo").value = S.estado ? S.estado.titulo : "";
    var ops = S.doc ? S.doc.operacoes.length : 0;
    $("pr-historico").textContent = S.doc ? ops + " operações · contador " + S.doc.contador : "";
  }

  function atualizaPassos() {
    var barra = limpa($("pr-passos"));
    S.estado.passos.forEach(function (p, i) {
      barra.appendChild(el("button", {
        class: "pr-passo" + (i === S.passo ? " ativo" : ""), "data-passo": String(i + 1),
        title: p.titulo || "Passo " + (i + 1), texto: String(i + 1),
        onclick: function () { S.passo = i; S.sel = null; atualizaTudo(); }
      }));
    });
    barra.appendChild(el("button", { class: "pr-passo novo", id: "pr-novo-passo", title: "Novo passo", texto: "+",
      onclick: function () {
        emite("cria_passo", { passo: novoId(), titulo: "" });
        S.passo = S.estado.passos.length - 1; atualizaTudo();
      } }));
    var atual = S.estado.passos[S.passo];
    $("pr-passo-titulo").value = atual ? atual.titulo : "";
    $("pr-remove-passo").disabled = S.estado.passos.length <= 1;
  }

  function atualizaFerramentas() {
    Array.prototype.forEach.call(document.querySelectorAll("[data-ferramenta]"), function (b) {
      b.classList.toggle("ativo", b.getAttribute("data-ferramenta") === S.ferramenta);
    });
    Array.prototype.forEach.call(document.querySelectorAll("[data-arma]"), function (b) {
      b.classList.toggle("ativo", b.getAttribute("data-arma") === S.arma);
    });
    cv.style.cursor = S.ferramenta === "mover" ? "default" : "crosshair";
  }

  function atualizaPainel() {
    var box = limpa($("pr-selecao"));
    if (!S.sel) {
      box.appendChild(el("p", { class: "pr-dica", texto: "Arraste uma peça do banco para o mapa. Para uma granada de verdade, use “Buscar arremesso” e clique onde ela deve cair." }));
      return;
    }
    if (S.sel.tipo === "peca") {
      var p = S.estado.pecas[S.sel.id];
      if (!p) { S.sel = null; return atualizaPainel(); }
      box.appendChild(el("h3", { texto: (p.lado === "ct" ? "CT " : "TR ") + p.rotulo }));
      box.appendChild(el("button", { class: "pr-b", texto: "Tirar do mapa", onclick: removeSelecionado }));
      return;
    }
    var g = S.estado.granadas[S.sel.id];
    if (!g) { S.sel = null; return atualizaPainel(); }
    box.appendChild(el("h3", { texto: NOME_ARMA[g.arma] + " · passo " + (indiceDoPasso(g.passo) + 1) }));
    if (g.arremesso) {
      var r = g.arremesso;
      box.appendChild(el("p", { class: "pr-meta", texto: r.jogador + " · " + r.partida + " round " + r.round + " (" + tempo(r.segundos_no_round) + ")" }));
      box.appendChild(el("p", { class: "pr-meta", texto: descreveArremesso(r) }));
      var cmd = el("code", { id: "pr-comando", texto: r.comando });
      box.appendChild(el("div", { class: "pr-cmd" }, [cmd, el("button", { class: "pr-b", id: "pr-copia", texto: "Copiar",
        onclick: function () { copia(r.comando); } })]));
      if (r.movimento && r.movimento !== "parado") {
        box.appendChild(el("p", { class: "pr-alerta", texto: "O arremesso original foi " + r.movimento +
          ": o comando põe você na posição e no ângulo da soltura, mas repetir exige o mesmo movimento." }));
      }
      if (r.no_ar) {
        box.appendChild(el("p", { class: "pr-alerta", texto: "O arremesso original saiu no ar: o comando dá a posição do chão, e repetir exige o pulo." }));
      }
      if (!(cfg.biblioteca && cfg.biblioteca.comando_conferido_no_jogo)) {
        box.appendChild(el("p", { class: "pr-alerta", texto: "Comando ainda não conferido no jogo: confira onde a granada cai antes de treinar." }));
      }
    } else {
      box.appendChild(el("p", { class: "pr-meta", texto: "Desenhada à mão: mostra onde cai, não como chegar lá." }));
    }
    box.appendChild(el("button", { class: "pr-b", texto: "Apagar granada", onclick: removeSelecionado }));
  }

  function atualizaBusca() {
    var box = limpa($("pr-resultados"));
    if (!S.busca) return;
    var b = S.busca;
    box.appendChild(el("p", { class: "pr-meta", texto: b.total === 0
      ? "Nenhum arremesso real de " + NOME_ARMA[S.arma] + " cai a menos de " + b.raio + "u daqui no corpus."
      : b.total + " arremessos reais de " + NOME_ARMA[S.arma] + " caem a menos de " + b.raio + "u daqui" +
        (b.total > b.resultados.length ? " (os " + b.resultados.length + " mais perto)" : "") + "." }));
    var lista = el("ol", { class: "pr-lista" });
    b.resultados.forEach(function (r, n) {
      lista.appendChild(el("li", {
        "data-arremesso": r.id,
        onmouseenter: function () { S.busca.foco = n; desenha(); },
        onmouseleave: function () { S.busca.foco = null; desenha(); },
        onclick: function () { usaArremesso(r); }
      }, [el("strong", { texto: r.jogador }), el("span", { texto: " " + r.partida + " r" + r.round + " · " + descreveArremesso(r) })]));
    });
    box.appendChild(lista);
  }

  function copia(texto) {
    var feito = function () { $("pr-copia").textContent = "Copiado"; };
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(texto).then(feito, function () { copiaAntigo(texto); feito(); });
    } else { copiaAntigo(texto); feito(); }
  }
  function copiaAntigo(texto) {
    var t = el("textarea", {}); t.value = texto; document.body.appendChild(t); t.select();
    try { document.execCommand("copy"); } catch (e) { /* sem área de transferência */ }
    document.body.removeChild(t);
  }

  /* ---------------------------------------------------------------------
     Arquivo: exportar e importar (importar a MESMA tática mescla)
     --------------------------------------------------------------------- */
  function exporta() {
    gravaAgora();
    var blob = new Blob([JSON.stringify(S.doc, null, 1)], { type: "application/json" });
    var a = el("a", { href: URL.createObjectURL(blob),
                      download: (S.estado.titulo || "tatica").replace(/[^\w\-]+/g, "_") + "." + cfg.mapa + ".json" });
    document.body.appendChild(a); a.click(); document.body.removeChild(a);
  }

  function valida(doc) {
    if (!doc || doc.formato !== IDENTIFICADOR) return "não é um arquivo de tática da prancheta";
    if (doc.versao !== FORMATO) return "versão " + doc.versao + " do formato; esta página lê a " + FORMATO;
    if (doc.mapa !== cfg.mapa) return "a tática é de " + doc.mapa + ", e esta prancheta é de " + cfg.mapa;
    if (doc.calibracao !== cfg.radar.calibracao) return "a tática foi feita sobre outra calibração do radar";
    if (!Array.isArray(doc.operacoes)) return "arquivo sem operações";
    return "";
  }

  function importaTexto(texto) {
    var doc;
    try { doc = JSON.parse(texto); } catch (e) { S.aviso = "Arquivo não é JSON."; atualizaAviso(); return false; }
    var erro = valida(doc);
    if (erro) { S.aviso = "Importação recusada: " + erro + "."; atualizaAviso(); return false; }
    // A cópia local é a da MEMÓRIA quando é a tática aberta: a gravação tem
    // atraso, e mesclar com a do armazém perderia o que acabou de ser feito.
    var local = (S.doc && S.doc.id === doc.id) ? S.doc : Armazem.carrega(doc.id);
    S.doc = local ? mescla(local, doc) : doc;
    S.estado = aplica(S.doc.operacoes);
    S.passo = 0; S.sel = null; S.busca = null;
    gravaAgora(); atualizaTudo();
    return true;
  }

  /* ---------------------------------------------------------------------
     Montagem
     --------------------------------------------------------------------- */
  function montaBanco() {
    var banco = limpa($("pr-banco"));
    LADOS.forEach(function (lado) {
      for (var n = 1; n <= PECAS_POR_LADO; n++) {
        (function (rotulo) {
          var b = el("div", { class: "pr-ficha " + lado, "data-lado": lado, "data-rotulo": rotulo,
                              title: "Arraste para o mapa", texto: rotulo });
          b.addEventListener("pointerdown", function (e) {
            e.preventDefault();
            b.setPointerCapture(e.pointerId);
            b.classList.add("arrastando");
          });
          b.addEventListener("pointerup", function (e) {
            b.classList.remove("arrastando");
            if (S.doc) soltaDoBanco(e, lado, rotulo);
          });
          banco.appendChild(b);
        })(String(n));
      }
    });
  }

  function init(opcoes) {
    cfg = opcoes;
    Armazem = opcoes.armazem || ArmazemDoNavegador("prancheta:");
    cv = $("pr-mapa"); ctx = cv.getContext("2d");
    img = new Image(); img.onload = desenha; img.src = cfg.radar.image;

    montaBanco();
    cv.addEventListener("pointerdown", pointerDown);
    cv.addEventListener("pointermove", pointerMove);
    cv.addEventListener("pointerup", pointerUp);
    cv.addEventListener("pointercancel", function () { S.arrasto = null; desenha(); });

    Array.prototype.forEach.call(document.querySelectorAll("[data-ferramenta]"), function (b) {
      b.addEventListener("click", function () {
        S.ferramenta = b.getAttribute("data-ferramenta"); S.origemPendente = null;
        if (S.ferramenta !== "buscar") S.busca = null;
        atualizaTudo();
      });
    });
    Array.prototype.forEach.call(document.querySelectorAll("[data-arma]"), function (b) {
      b.addEventListener("click", function () {
        S.arma = b.getAttribute("data-arma");
        if (S.busca) busca(S.busca.ponto);
        atualizaFerramentas();
      });
    });
    $("pr-raio").value = String(S.raioBusca);
    $("pr-raio").addEventListener("input", function () {
      S.raioBusca = +this.value; $("pr-raio-valor").textContent = this.value + "u";
      if (S.busca) busca(S.busca.ponto);
    });
    $("pr-raio-valor").textContent = S.raioBusca + "u";
    $("pr-so-parado").addEventListener("change", function () {
      S.soParado = this.checked;
      if (S.busca) busca(S.busca.ponto);
    });

    $("pr-nova").addEventListener("click", novaTatica);
    $("pr-taticas").addEventListener("change", function () { abre(this.value); });
    $("pr-titulo").addEventListener("change", function () { emite("renomeia", { titulo: this.value.trim() }); });
    $("pr-passo-titulo").addEventListener("change", function () {
      emite("renomeia_passo", { passo: passoAtual(), titulo: this.value.trim() });
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
      if (resto.length) abre(resto[0].id); else novaTatica();
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

    document.addEventListener("keydown", function (e) {
      if (/^(INPUT|TEXTAREA|SELECT)$/.test((e.target || {}).tagName || "")) return;
      if (e.key === "Delete" || e.key === "Backspace") { e.preventDefault(); removeSelecionado(); }
      if (e.key === "Escape") { S.origemPendente = null; S.busca = null; S.sel = null; atualizaTudo(); }
    });
    window.addEventListener("resize", redimensiona);
    window.addEventListener("pagehide", gravaAgora);

    var lista = Armazem.lista(cfg.mapa);
    if (!(lista.length && abre(lista[0].id))) novaTatica();
    redimensiona();
  }

  return {
    init: init,
    _interno: {
      S: S, aplica: aplica, mescla: mescla, posicaoNoPasso: posicaoNoPasso,
      jogoParaPixel: jogoParaPixel, pixelParaJogo: pixelParaJogo,
      importaTexto: importaTexto, gravaAgora: gravaAgora, busca: busca, usaArremesso: usaArremesso,
      armazem: function () { return Armazem; },
      radar: function () { return cfg.radar; }
    }
  };
})();
