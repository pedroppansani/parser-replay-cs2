/* Aba Perfil do protótipo (§19): cabeçalho, pontos a melhorar, pontos fortes, comparar e Detalhes.
   No projeto todo texto sai de leitura/perfil_erros.py (decisão 18) e o JS só monta o HTML; aqui os textos
   estão no objeto DADOS só para o protótipo. `Perfil.monta(raiz, estado)` desenha a aba num contêiner. */
(function () {
  "use strict";
  var DUR_ROUND = 115;           // segundos do relógio do round (1:55 descendo), como em partida.js
  function esc(s) { return String(s).replace(/[&<>"']/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]; }); }
  function relogio(t) { var s = Math.max(0, Math.round(DUR_ROUND - t)); return Math.floor(s / 60) + ":" + String(s % 60).padStart(2, "0"); }

  var TEXTOS = {
    eyebrow: "Onde errou e como melhorar", titulo: "Perfil do jogador",
    melhorar: "Pontos a melhorar", fortes: "Pontos fortes", comparar: "Comparar com",
    comparar_texto: "Só jogadores desta partida, de qualquer time; ao lado de cada um, a contagem ou o valor dele nesta partida. A referência é a mediana anônima do corpus.",
    em_validacao: "Em validação: os tipos de erro aparecem depois de conferidos", como_e_conferido: "como é conferido",
    aviso_preview: "Pré-visualização: nenhum destes tipos de erro foi conferido ainda. Esta página não é publicada.",
    melhorar_vazio: "Nenhum ponto a melhorar com dado suficiente nesta partida.", fortes_vazio: "Nenhum ponto forte acima da régua com dado suficiente nesta partida.",
    rot_como_melhorar: "Como melhorar", rot_conferir: "Antes de mudar algo", rot_rounds: "Rounds (abrem o Replay)",
    nivel_explicito: "explícito", nivel_depende: "depende da tática", em_val: "em validação",
    detalhes: "Detalhes", detalhes_resumo: "o perfil completo desta partida: taxas, função por round, jeito de jogar e quem joga em cada grupo",
    detalhes_erros: "Tipos de erro com uma só ocorrência não viram ponto a melhorar; ficam aqui.",
    degradado: "Dado degradado: o modelo de round não carregou; os custos e os pontos fortes ficam escondidos até o rebuild.",
    erro_carga: "Os dados do Perfil não abriram. Recarregue a página; se continuar, abra uma issue."
  };

  var JOGADORES = [
    { time: "Falcons", nomes: ["m0NESY", "NiKo", "kyousuke", "TeSeS", "kyxsan"] },
    { time: "MOUZ", nomes: ["xertioN", "Spinx", "Jimpphat", "torzsi", "Brollan"] }
  ];

  var DADOS = {
    "m0NESY": {
      time: "Falcons", comecou: "tr", comecou_rotulo: "começou TR",
      funcoes: [{ lado: "TR", texto: "AWPer", neutro: false }, { lado: "CT", texto: "AWPer (tendência)", neutro: true }],
      resumo: "m0NESY jogou 36 rounds nesta partida; o que mais custou foi não trocou o aliado (4 vezes); o ponto mais forte foi troca a morte do companheiro (30%, a mediana de quem joga AWPer é 14%).",
      melhorar: [
        { tipo: "nao_trocou", titulo: "Não trocou o aliado", lado: "tr", lado_rotulo: "no TR", contagem: "4 vezes em 12 rounds", nivel: "explicito",
          referencia: "a mediana de quem joga AWPer no TR é 2", custo: "custou cerca de 7 pontos de chance de vitória, pela estimativa do modelo",
          motivo: "o aliado morreu perto dele e o matador saiu vivo da janela de troca",
          frase: "Jogue a uma distância de troca do parceiro e mirando o mesmo ponto que ele. Se ele cair, o matador está exposto por alguns segundos: é a sua janela.",
          chips: [{ round: 5, t: 41.5 }, { round: 8, t: 66 }, { round: 10, t: 23.5 }, { round: 12, t: 58 }] },
        { tipo: "bait", titulo: "Possível bait", lado: "ct", lado_rotulo: "no CT", contagem: "3 vezes em 12 rounds", nivel: "explicito",
          referencia: "a mediana de quem joga AWPer no CT é 1", custo: "custou cerca de 5 pontos de chance de vitória, pela estimativa do modelo",
          motivo: "estava atrás do aliado, não atirou no matador e sobreviveu à janela de troca; o dado mostra posição e tempo, não intenção",
          frase: "Se você é o segundo a entrar, entre logo atrás e ao lado, não atrás de parede. Combinem antes quem entra e quem troca.",
          chips: [{ round: 15, t: 52 }, { round: 19, t: 38.5 }, { round: 22, t: 71 }] },
        { tipo: "isolado", titulo: "Morreu isolado", lado: "tr", lado_rotulo: "no TR", contagem: "4 vezes em 12 rounds", nivel: "depende",
          referencia: "a mediana de quem joga AWPer no TR é 3", custo: "custou cerca de 8 pontos de chance de vitória, pela estimativa do modelo",
          motivo: "o dado mostra posição e tempo, não o que o time pediu",
          frase: "O dado mostra posição e tempo, não o que o time pediu. Vale conferir com o time se era o plano.",
          chips: [{ round: 2, t: 33 }, { round: 6, t: 48.5 }, { round: 9, t: 61 }, { round: 11, t: 27 }] }
      ],
      fortes: [
        { chave: "troca_morte", rotulo: "Troca a morte do companheiro", valor: "30%", bruto: "6 de 20 rounds", referencia: "a mediana de quem joga AWPer é 14%" },
        { chave: "kpr_cheia", rotulo: "Kills por round contra compra cheia", valor: "1,14", bruto: "em 10 rounds contra compra cheia", referencia: "a mediana de quem joga AWPer é 0,74" }
      ],
      uma_vez: [{ titulo: "Perdeu a troca", contagem: "1 vez", chips: [{ round: 17, t: 44 }] }],
      contagens: { "Não trocou o aliado": 4, "Possível bait": 3, "Morreu isolado": 4 },
      taxas: [["Abriu o round", "17%", "6 de 36", "11%"], ["Segurou ângulo", "58%", "21 de 36", "44%"], ["Primeira morte sem troca", "8%", "3 de 36", "9%", "dentro"]]
    },
    "xertioN": {
      time: "MOUZ", comecou: "ct", comecou_rotulo: "começou CT",
      funcoes: [{ lado: "TR", texto: "entry", neutro: false }, { lado: "CT", texto: "âncora (tendência)", neutro: true }],
      resumo: "xertioN jogou 36 rounds nesta partida; nenhum tipo de erro apareceu com dado suficiente.",
      melhorar: [], fortes: [], uma_vez: [], contagens: { "Não trocou o aliado": 1, "Possível bait": 0, "Morreu isolado": 2 }, taxas: []
    }
  };

  function chips(lista, visitados) {
    if (!lista || !lista.length) return "";
    return '<div class="pfchips" role="group" aria-label="' + esc(TEXTOS.rot_rounds) + '">' + lista.map(function (c) {
      var chave = c.round + "@" + c.t, vis = visitados[chave];
      var titulo = "Round " + c.round + ", " + relogio(c.t) + (vis ? " (já aberto)" : "") + ": abre o Replay 3 s antes";
      return '<button type="button" class="pfchip" data-round="' + c.round + '" data-t="' + c.t + '"' + (vis ? " data-visitado" : "") +
        ' title="' + esc(titulo) + '" aria-label="' + esc(titulo) + '"><span class="n">' + c.round + '</span><span class="h">' + relogio(c.t) + "</span></button>";
    }).join("") + "</div>";
  }

  function ladoTag(l) { return '<span class="tag ' + l.lado + '">' + esc(l.lado_rotulo) + "</span>"; }

  function pontoMelhorar(m, i, preview, visitados) {
    var explicito = m.nivel === "explicito";
    return '<li class="ponto melhorar ' + (explicito ? "explicito" : "depende") + '" data-tipo="' + esc(m.tipo) + '">' +
      '<span class="ordem" aria-hidden="true">' + (i + 1) + "</span>" +
      '<div class="topo"><span class="titulo">' + esc(m.titulo) + "</span>" +
      (explicito ? '<span class="tag explicito">' + esc(TEXTOS.nivel_explicito) + "</span>"
                 : '<span class="tag neutro">' + esc(TEXTOS.nivel_depende) + "</span>") +
      (preview ? '<span class="tag neutro validacao">' + esc(TEXTOS.em_val) + "</span>" : "") + "</div>" +
      '<div class="sub">' + ladoTag(m) + "<span>" + esc(m.contagem) + "</span></div>" +
      '<div class="ref">' + esc(m.referencia) + "</div>" +
      '<div class="custo">' + esc(m.custo) + "</div>" +
      (explicito ? '<div class="motivo">' + esc(m.motivo) + "</div>" : "") +
      '<div class="como"><span class="rot">' + esc(explicito ? TEXTOS.rot_como_melhorar : TEXTOS.rot_conferir) + "</span><p>" + esc(m.frase) + "</p></div>" +
      '<div class="rounds"><span class="rot">' + esc(TEXTOS.rot_rounds) + "</span>" + chips(m.chips, visitados) + "</div></li>";
  }

  function pontoForte(f) {
    return '<li class="ponto forte" data-chave="' + esc(f.chave) + '"><div class="topo"><span class="titulo">' + esc(f.rotulo) + '</span>' +
      '<span class="valor">' + esc(f.valor) + "</span>" + (f.bruto ? '<span class="bruto">' + esc(f.bruto) + "</span>" : "") + "</div>" +
      '<div class="ref">' + esc(f.referencia) + "</div></li>";
  }

  function esqueleto(n) {
    var h = "";
    for (var i = 0; i < n; i++) h += '<li class="ponto esqueleto" aria-hidden="true"><span class="ordem"></span><div class="esqueleto" style="height:20px;width:55%"></div><div class="esqueleto" style="height:14px;width:35%;margin-top:8px"></div><div class="esqueleto" style="height:14px;width:80%;margin-top:8px"></div><div class="esqueleto" style="height:44px;width:60%;margin-top:12px"></div></li>';
    return h;
  }

  function lerVisitados() { try { return JSON.parse(sessionStorage.getItem("parser-cs2:chips-visitados") || "{}") || {}; } catch (e) { return {}; } }
  function gravaVisitado(c) { var v = lerVisitados(); v[c] = true; try { sessionStorage.setItem("parser-cs2:chips-visitados", JSON.stringify(v)); } catch (e) { /* sem armazenamento: o chip só não fica marcado */ } }
  function lerDetalhes() { try { return localStorage.getItem("parser-cs2:perfil-detalhes") === "1"; } catch (e) { return false; } }
  function gravaDetalhes(a) { try { localStorage.setItem("parser-cs2:perfil-detalhes", a ? "1" : "0"); } catch (e) { /* abre fechado, funciona igual */ } }

  function monta(raiz, estado, jogador) {
    estado = estado || "publicado"; jogador = jogador || "m0NESY";
    var d = DADOS[jogador] || DADOS["m0NESY"], visitados = lerVisitados(), h = "";
    raiz.__perfil = { estado: estado, jogador: jogador };
    if (!raiz.__ouvindo) {
      raiz.__ouvindo = true;
      raiz.addEventListener("click", function (e) {
        var c = e.target.closest(".pfchip");
        if (c) { gravaVisitado(c.dataset.round + "@" + c.dataset.t); location.href = "partida.html#replay?round=" + c.dataset.round + "&t=" + c.dataset.t; return; }
        var j = e.target.closest("[data-jog]");
        if (j) { monta(raiz, raiz.__perfil.estado, j.dataset.jog); var nb = raiz.querySelector('[data-jog="' + j.dataset.jog + '"]'); if (nb) nb.focus(); }
      });
    }
    var selecao = JOGADORES.map(function (t) {
      return '<span class="rot time-rot">' + esc(t.time) + "</span>" + t.nomes.map(function (n) {
        return '<button type="button" class="chip" data-jog="' + esc(n) + '" aria-pressed="' + (n === jogador ? "true" : "false") + '">' + esc(n) + "</button>";
      }).join("");
    }).join("");
    h += '<p class="rot">' + esc(TEXTOS.eyebrow) + '</p><h2 style="margin:4px 0 0;font-stretch:85%">' + esc(TEXTOS.titulo) + "</h2>";
    h += '<div class="pfsel" role="group" aria-label="Jogador">' + selecao + "</div>";

    if (estado === "erro") {
      h += '<div class="aviso-bloco erro" role="alert" style="margin-top:14px"><span class="ico" aria-hidden="true">✕</span><p><b>Erro:</b> ' + esc(TEXTOS.erro_carga) + "</p></div>";
      raiz.innerHTML = h; return;
    }
    if (estado === "carregando") {
      h += '<div class="pfcab" aria-busy="true"><div class="esqueleto" style="height:28px;width:30%"></div><div class="esqueleto" style="height:16px;width:50%;margin-top:10px"></div></div>' +
           '<section class="pfsec"><h3>' + esc(TEXTOS.melhorar) + '</h3><ul class="pflista">' + esqueleto(2) + "</ul></section>";
      raiz.innerHTML = h; return;
    }

    h += '<div class="pfcab"><div class="nk">' + esc(jogador) + '</div><div class="time-do-jog">' + esc(d.time) + ' <span class="tag ' + d.comecou + '">' + esc(d.comecou_rotulo) + "</span></div>" +
      '<div class="funcs">' + d.funcoes.map(function (f) {
        return '<span class="tag ' + (f.neutro ? "neutro tendencia" : "decisivo") + '">' + esc(f.lado) + " · " + esc(f.texto) + "</span>";
      }).join("") + "</div><p>" + esc(d.resumo) + "</p></div>";
    if (estado === "degradado") h += '<div class="aviso-bloco" role="note" style="margin-top:14px"><span class="ico" aria-hidden="true">▲</span><p><b>Dado degradado.</b> ' + esc(TEXTOS.degradado.replace(/^Dado degradado: /, "")) + "</p></div>";

    // pontos a melhorar
    h += '<section class="pfsec" aria-labelledby="pf-mel"><h3 id="pf-mel">' + esc(TEXTOS.melhorar) + "</h3>";
    if (estado === "em-validacao") {
      h += '<div class="aviso-bloco neutro" role="note"><span class="ico" aria-hidden="true">–</span><p><span class="tag neutro validacao">' + esc(TEXTOS.em_val) + "</span> " + esc(TEXTOS.em_validacao) + ' · <a href="#">' + esc(TEXTOS.como_e_conferido) + "</a></p></div>";
    } else if (estado === "degradado") {
      h += '<p class="pfnota">Escondido: dado degradado.</p>';
    } else {
      var preview = estado === "preview", lista = estado === "vazio" ? [] : d.melhorar;
      if (preview) h += '<p class="pfnota">' + esc(TEXTOS.aviso_preview) + "</p>";
      h += lista.length ? '<ol class="pflista">' + lista.map(function (m, i) { return pontoMelhorar(m, i, preview, visitados); }).join("") + "</ol>" : '<p class="pfnota">' + esc(TEXTOS.melhorar_vazio) + "</p>";
    }
    h += "</section>";

    // pontos fortes
    h += '<section class="pfsec" aria-labelledby="pf-for"><h3 id="pf-for">' + esc(TEXTOS.fortes) + "</h3>";
    if (estado === "degradado") h += '<p class="pfnota">Escondido: dado degradado.</p>';
    else {
      var fortes = estado === "vazio" ? [] : d.fortes;
      h += fortes.length ? '<ul class="pflista">' + fortes.map(pontoForte).join("") + "</ul>" : '<p class="pfnota">' + esc(TEXTOS.fortes_vazio) + "</p>";
    }
    h += "</section>";

    // comparar com
    var outro = jogador === "m0NESY" ? "xertioN" : "m0NESY", o = DADOS[outro];
    h += '<section class="pfsec pf-comparar" aria-labelledby="pf-cmp"><h3 id="pf-cmp">' + esc(TEXTOS.comparar) + '</h3><p class="pfnota">' + esc(TEXTOS.comparar_texto) + "</p>" +
      '<label class="rot" for="pf-b">' + esc(TEXTOS.comparar) + '</label><select id="pf-b"><option>— ninguém —</option><option selected>' + esc(outro) + "</option></select>" +
      '<div class="tabela-rolagem"><table class="dados" style="min-width:320px"><thead><tr><th scope="col">Tipo de erro</th><th scope="col">' + esc(jogador) + '</th><th scope="col">' + esc(outro) + "</th></tr></thead><tbody>" +
      Object.keys(d.contagens).map(function (k) { return '<tr><td>' + esc(k) + '</td><td class="num">' + d.contagens[k] + '</td><td class="num">' + (o.contagens[k] || 0) + "</td></tr>"; }).join("") +
      "</tbody></table></div></section>";

    // detalhes (fechado por padrão; aberto/fechado lembrado em localStorage, em try/catch)
    var det = lerDetalhes();
    h += '<details class="grupo pf-detalhes" id="pf-detalhes"' + (det ? " open" : "") + '><summary><span class="g-nome">' + esc(TEXTOS.detalhes) + '</span><span class="g-resumo">' + esc(TEXTOS.detalhes_resumo) + "</span></summary>" +
      '<div class="pf-det-corpo">' +
      (d.taxas.length ? '<div><h4 class="rot">Taxas desta partida</h4><div class="tabela-rolagem"><table class="dados" style="min-width:420px"><thead><tr><th scope="col">Comportamento</th><th scope="col">Taxa</th><th scope="col">Bruto</th><th scope="col">Régua do corpus</th></tr></thead><tbody>' +
        d.taxas.map(function (t) { return "<tr><td>" + esc(t[0]) + '</td><td class="num"><b>' + esc(t[1]) + '</b></td><td class="num">' + esc(t[2]) + '</td><td class="num">' + esc(t[3]) + (t[4] ? ' <span class="tag neutro normal">dentro do normal para a função</span>' : "") + "</td></tr>"; }).join("") +
        "</tbody></table></div></div>" : '<p class="pfnota">Sem taxas com amostra suficiente nesta partida.</p>') +
      (d.uma_vez.length ? '<div><h4 class="rot">' + esc(TEXTOS.detalhes_erros) + "</h4>" + d.uma_vez.map(function (u) {
        return '<div class="ponto compacto depende" style="grid-template-columns:minmax(0,1fr)"><div class="topo"><span class="titulo">' + esc(u.titulo) + '</span><span class="sub">' + esc(u.contagem) + "</span></div>" + chips(u.chips, visitados) + "</div>";
      }).join("") + "</div>" : "") +
      "</div></details>";

    raiz.innerHTML = h;

    // comportamento
    var det2 = raiz.querySelector("#pf-detalhes");
    if (det2) det2.addEventListener("toggle", function () { gravaDetalhes(det2.open); });
    [].forEach.call(raiz.querySelectorAll(".pfchips"), function (c) {
      function atualiza() { var rola = c.scrollWidth > c.clientWidth + 2; c.classList.toggle("rola", rola); c.classList.toggle("fim", rola && c.scrollLeft + c.clientWidth >= c.scrollWidth - 2); }
      c.addEventListener("scroll", atualiza, { passive: true }); atualiza();
      window.addEventListener("resize", atualiza);
    });
  }

  window.Perfil = { monta: monta, TEXTOS: TEXTOS, relogio: relogio };
})();
