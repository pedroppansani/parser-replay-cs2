  /* ---------------------------------------------------------------------
     Montagem
     --------------------------------------------------------------------- */
  /** O banco: "TR 1..5" e "CT 1..5", ou -- em tática que veio de um instante do
      replay -- os jogadores REAIS do round, vivos e mortos, lidos do metadado
      `origem` (nunca inferidos dos rótulos). */
  function montaBanco() {
    var banco = limpa($("pr-banco"));
    var elenco = S.doc && S.doc.origem && S.doc.origem.elenco;
    banco.classList.toggle("nomes", !!elenco);
    LADOS.forEach(function (lado) {
      banco.appendChild(el("div", { class: "pr-lado-rotulo " + lado, texto: lado === "ct" ? "CT" : "TR" }));
      var rotulos = elenco
        ? elenco.filter(function (j) { return j.lado === lado; }).map(function (j) { return j.nome; })
        : [1, 2, 3, 4, 5].slice(0, PECAS_POR_LADO).map(String);
      rotulos.forEach(function (rotulo) {
        (function (rotulo) {
          // botão (e não div): o leitor de tela anuncia e o teclado alcança. Enter/Espaço = o clique; com a ficha
          // já armada, Enter de novo põe a peça no centro do mapa (o teclado não tem como apontar um lugar no canvas)
          var b = el("button", { type: "button", class: "pr-ficha " + lado + (elenco ? " nome" : ""), "data-lado": lado,
                                 "data-rotulo": rotulo, title: "Arraste para o mapa", texto: rotulo, "aria-pressed": "false" });
          b.addEventListener("keydown", function (e) {
            if (e.key !== "Enter" && e.key !== " ") return;
            e.preventDefault();
            if (!S.doc || S.reproducao) return;
            var armada = S.acao && S.acao.tipo === "colocar" && S.acao.lado === lado && S.acao.rotulo === rotulo;
            if (armada) { S.acao = null; colocaPeca(lado, rotulo, centroDoRadar(cfg.radar)); }
            else cliqueNaFicha(lado, rotulo);
          });
          var inicio = null;
          b.addEventListener("pointerdown", function (e) {
            e.preventDefault();
            b.setPointerCapture(e.pointerId);
            b.classList.add("arrastando");
            inicio = { x: e.clientX, y: e.clientY };
          });
          b.addEventListener("pointerup", function (e) {
            b.classList.remove("arrastando");
            if (!S.doc || S.reproducao) return;
            var andou = inicio && Math.hypot(e.clientX - inicio.x, e.clientY - inicio.y) >= LIMIAR_ARRASTO_PX;
            inicio = null;
            if (andou) soltaDoBanco(e, lado, rotulo);      // arrasto: como sempre
            else cliqueNaFicha(lado, rotulo);              // clique: seleciona ou arma a colocação
          });
          banco.appendChild(b);
        })(rotulo);
      });
    });
  }

  /** A barra única, na ordem de "o que eu quero fazer agora": selecionar,
      granadas, desenho | desfazer, reproduzir, vista, andares. Cor e espessura
      ficam num grupo de CONTEXTO que só aparece com uma ferramenta de desenho.
      Todo botão mostra o atalho na dica. */
  var ATALHO_DA_ARMA = { smoke: "Smoke", flash: "Flash", he: "HE", molotov: "Molotov" };
  var DICA_DA_FERRAMENTA = { caneta: "Caneta", seta: "Seta", linha: "Linha", texto: "Texto", borracha: "Borracha",
                            granada_desenho: "Granada (desenho)" };

  function montaBarra() {
    var barra = limpa($("pr-barra"));
    var botaoF = function (id, texto, dica) {
      return el("button", { "data-ferramenta": id, texto: texto, title: dica,
                            onclick: function () { escolheFerramenta(id); } });
    };

    var ferramentas = el("div", { class: "anot-grupo sempre", id: "pr-ferramentas" });
    var sel = botaoF("mover", "Selecionar", comAtalho("Selecionar e mover", "Selecionar"));
    sel.id = "pr-selecionar";
    ferramentas.appendChild(sel);
    barra.appendChild(ferramentas);

    // As granadas moram no painel da direita (seção Granadas, item 8.4): a barra
    // de cima fica com vista, andares, pincéis, desfazer/refazer e Reproduzir.

    var desenho = el("div", { class: "anot-grupo sempre", id: "pr-desenho" });
    Object.keys(ROTULO_FERRAMENTA).forEach(function (id) {
      var nome = id === "borracha" ? "Borracha" : ROTULO_FERRAMENTA[id];
      desenho.appendChild(botaoF(id, nome, DICA_DA_FERRAMENTA[id] ? comAtalho(nome, DICA_DA_FERRAMENTA[id]) : nome));
    });
    barra.appendChild(desenho);

    // As opções do pincel (cor e espessura) e da granada desenhada (o tipo) não ficam na barra: aparecer e sumir com a
    // ferramenta mudava a altura dela e empurrava o mapa. Ficam numa coluna na borda direita da tela, ao lado do mapa
    // (espelho do relógio grande, à esquerda); reprojeta() deixa a folga dela, e o mapa nunca passa por baixo (v2-5b,
    // decisão 2 do Pedro). Vem antes do canvas: no Tab, logo depois da barra.
    var opcoes = $("pr-opcoes") || el("div", { id: "pr-opcoes", class: "pr-opcoes vazia" });
    if (!opcoes.parentNode) $("pr-tela").insertBefore(opcoes, $("pr-mapa"));
    limpa(opcoes);
    var contexto = el("div", { class: "anot-grupo sempre", id: "pr-contexto-desenho", role: "group", "aria-label": "Cor e espessura" });
    cores = MapCore.seletorDeCor({
      estado: S, armazem: MapCore.criaArmazem(), chaveRecentes: CHAVE_RECENTES, maxRecentes: MAX_RECENTES,
      palco: function () { return $("pr-palco"); }, aoMudar: function () { atualizaBarra(); }
    });
    contexto.appendChild(cores.montaCor());
    ESPESSURAS.forEach(function (v, i) {
      contexto.appendChild(el("button", { "data-espessura": String(v), class: "pr-b", texto: ROTULOS_ESPESSURA[i],
        title: "Espessura " + ROTULOS_ESPESSURA[i], onclick: function () { S.espessura = v; atualizaFerramentas(); } }));
    });
    contexto.hidden = true;
    opcoes.appendChild(contexto);
    var contextoGranada = el("div", { class: "anot-grupo sempre", id: "pr-contexto-granada", role: "group",
                                      "aria-label": "Tipo da granada desenhada" });
    ARMAS_DESENHADAS.forEach(function (a, i) {
      contextoGranada.appendChild(el("button", { "data-arma-desenho": a, class: "pr-b", texto: NOME_ARMA[a],
        title: NOME_ARMA[a] + " desenhada (" + (i + 1) + ")", "aria-pressed": "false",
        onclick: function () { S.armaDesenho = a; atualizaTudo(); } }));
    });
    contextoGranada.hidden = true;
    opcoes.appendChild(contextoGranada);

    barra.appendChild(el("span", { class: "pr-separador", "aria-hidden": "true" }));

    var historico = el("div", { class: "anot-grupo sempre" });
    var d = MapCore.botao("Desfazer", comAtalho("Desfazer", "Desfazer"), desfaz); d.id = "pr-desfaz";
    var r = MapCore.botao("Refazer", comAtalho("Refazer", "Refazer (também Ctrl+Shift+Z)"), refaz); r.id = "pr-refaz";
    historico.appendChild(d); historico.appendChild(r);
    barra.appendChild(historico);

    var vista = el("div", { class: "anot-grupo sempre" });
    var reproduzir = MapCore.botao("Reproduzir", "Reproduzir a tática passo a passo", comecaReproducao, "principal");
    reproduzir.id = "pr-reproduzir";
    vista.appendChild(reproduzir);
    vista.appendChild(MapCore.botao("\u2212", "Diminuir o zoom", function () { aplicaZoom(S.view.zoom / MapCore.ZOOM_PASSO); }));
    var lupa = MapCore.botao("100%", comAtalho("Voltar ao tamanho original", "Zoom original") +
                             ". Com zoom, segure espaço e arraste para mover o mapa", resetaZoom);
    lupa.id = "pr-zoom";
    vista.appendChild(lupa);
    vista.appendChild(MapCore.botao("+", "Aumentar o zoom", function () { aplicaZoom(S.view.zoom * MapCore.ZOOM_PASSO); }));
    var fs = MapCore.botao("Tela cheia", comAtalho("Mapa em tela cheia", "Tela cheia"), function () { MapCore.alternaTelaCheia($("pr-palco")); });
    fs.id = "pr-tela-cheia";
    vista.appendChild(fs);
    vista.appendChild(MapCore.botao("?", comAtalho("Atalhos", "Ajuda: esta lista"), function () { alternaAjuda(); }));
    barra.appendChild(vista);

    if (ANDARES.length > 1) {
      var andares = el("div", { class: "anot-grupo sempre", id: "pr-andares" });
      ANDARES.forEach(function (a, i) {
        andares.appendChild(el("button", { "data-andar": String(i),
          texto: i === 0 ? "Andar de cima" : (ANDARES.length === 2 ? "Andar de baixo" : "Andar " + (i + 1)),
          onclick: function () { S.andar = i; S.sel = null; S.acao = null; atualizaTudo(); } }));
      });
      barra.appendChild(andares);
    }

    // a linha de dica: sempre com o que o PRÓXIMO clique faz
    if (!$("pr-dica-estado")) {
      var dica = el("p", { id: "pr-dica-estado", class: "pr-dica-estado", role: "status", "aria-live": "polite" });
      $("pr-palco").insertBefore(dica, $("pr-tela"));
    }
  }

  /** O painel lateral, montado aqui (o HTML só tem a estrutura): Jogadores,
      Selecionado, Passos e Tática, mais a busca de arremessos reais. */
  // Abas do painel da direita (entrega-sala-de-demo §14): Jogadores · Granadas · Tática. O painel fica no
  // `aside`; em telas estreitas ele desce para baixo do mapa e as abas continuam as mesmas.
  var ABAS_DO_PAINEL = [["jogadores", "Jogadores"], ["granadas", "Granadas"], ["tatica", "Tática"]];

  /** Mostra uma aba do painel (e esconde as outras). Devolve false para um nome que não existe. */
  function abaDoPainel(nome) {
    if (!ABAS_DO_PAINEL.some(function (a) { return a[0] === nome; })) return false;
    Array.prototype.forEach.call(document.querySelectorAll("#pr-abas [role=tab]"), function (b) {
      var on = b.dataset.aba === nome;
      b.setAttribute("aria-selected", String(on)); b.tabIndex = on ? 0 : -1;
    });
    Array.prototype.forEach.call(document.querySelectorAll("aside [role=tabpanel]"), function (p) { p.hidden = p.dataset.aba !== nome; });
    return true;
  }

  function montaLateral() {
    // abas de fora (a aba Grupo, quando o build tem grupo): entram depois das três de sempre
    (ganchos.abas || []).forEach(function (a) {
      if (!ABAS_DO_PAINEL.some(function (x) { return x[0] === a[0]; })) ABAS_DO_PAINEL.push(a);
    });
    var lado = limpa(document.querySelector("aside"));
    var abas = el("div", { class: "pr-abas" + (ABAS_DO_PAINEL.length > 3 ? " quatro" : ""), id: "pr-abas", role: "tablist", "aria-label": "Painel da prancheta" });
    ABAS_DO_PAINEL.forEach(function (a) {
      var b = el("button", { type: "button", role: "tab", id: "pr-aba-" + a[0], "data-aba": a[0], "aria-controls": "pr-painel-" + a[0],
        "aria-selected": "false", tabindex: "-1", texto: a[1], onclick: function () { abaDoPainel(a[0]); } });
      b.addEventListener("keydown", function (e) {
        var i = ABAS_DO_PAINEL.map(function (x) { return x[0]; }).indexOf(a[0]), n = ABAS_DO_PAINEL.length, j = null;
        if (e.key === "ArrowRight") j = (i + 1) % n; else if (e.key === "ArrowLeft") j = (i - 1 + n) % n;
        else if (e.key === "Home") j = 0; else if (e.key === "End") j = n - 1;
        if (j === null) return;
        e.preventDefault(); abaDoPainel(ABAS_DO_PAINEL[j][0]); $("pr-aba-" + ABAS_DO_PAINEL[j][0]).focus();
      });
      abas.appendChild(b);
    });
    // a bolha do gooey (entrega-v2 §7) por baixo das abas: só forma, quem a move é o v2.js pelo aria-selected
    abas.appendChild(el("span", { class: "goo", "aria-hidden": "true" }, [el("span", { class: "bolha" })]));
    lado.appendChild(abas);
    var paineis = {};
    ABAS_DO_PAINEL.forEach(function (a) {
      paineis[a[0]] = el("div", { id: "pr-painel-" + a[0], role: "tabpanel", "aria-labelledby": "pr-aba-" + a[0], "data-aba": a[0], class: "pr-painel" });
      lado.appendChild(paineis[a[0]]);
    });
    var alvo = paineis.jogadores;
    var caixa = function (titulo, filhos, id) {
      var s = el("section", { class: "caixa" }, [el("h2", { texto: titulo })].concat(filhos));
      if (id) s.id = id;
      alvo.appendChild(s);
      return s;
    };
    caixa("Jogadores", [el("div", { id: "pr-banco" }), el("div", { id: "pr-funcoes-banco", class: "pr-funcoes-banco" }),
      el("p", { class: "pr-dica", texto: "Clique numa ficha e depois no mapa, ou arraste." })]);
    caixa("Selecionado", [el("div", { id: "pr-selecao" })]);
    alvo = paineis.granadas;
    var botoesDeGranada = el("div", { class: "pr-granadas-grandes", id: "pr-granadas" });
    ["smoke", "flash", "he", "molotov"].forEach(function (a) {
      var simbolo = el("canvas", { width: "56", height: "56", class: "pr-glifo", "aria-hidden": "true" });
      var g2 = simbolo.getContext && simbolo.getContext("2d");
      if (g2) MapCore.nadeGlyph(g2, a, 28, 28, 18, MapCore.NADE_COLOR[a], 0);
      botoesDeGranada.appendChild(el("button", { "data-arma": a, class: "pr-granada-grande",
        title: comAtalho(NOME_ARMA[a] + ": com um jogador selecionado sai dele, no horário do cabeçote; senão, clique em quem joga",
                         ATALHO_DA_ARMA[a]),
        onclick: function () { escolheArma(a); } }, [simbolo, el("span", { texto: NOME_ARMA[a] })]));
    });
    caixa("Granadas", [botoesDeGranada,
      el("div", { class: "linha", id: "pr-modos" }, [
        el("button", { "data-ferramenta": "mover", texto: "Selecionar", title: comAtalho("Selecionar e mover", "Selecionar"),
          onclick: function () { escolheFerramenta("mover"); } }),
        el("button", { "data-ferramenta": "buscar", texto: "Buscar arremesso real",
          title: "Clique onde a granada deve cair e veja os arremessos reais (o mesmo que escolher a granada na barra)",
          onclick: function () { escolheFerramenta("buscar"); } }),
        el("button", { "data-ferramenta": "granada", texto: "Desenhar à mão",
          title: "Clique na origem e depois no destino, sem sugestões",
          onclick: function () { escolheFerramenta("granada"); } })]),
      el("p", { class: "pr-dica", id: "pr-sem-biblioteca", hidden: "" }),
      el("div", { id: "pr-filtros-busca", hidden: "" }, [
        el("div", { class: "linha" }, [el("label", { for: "pr-raio", texto: "Raio da busca" }),
          el("input", { type: "range", id: "pr-raio", min: "50", max: "600", step: "25" }), el("span", { id: "pr-raio-valor" })]),
        el("div", { class: "linha" }, [el("label", {}, [el("input", { type: "checkbox", id: "pr-so-parado" }),
          el("span", { texto: " só arremessos parados (o comando reproduz sozinho)" })])])]),
      el("div", { id: "pr-resultados" })]);
    alvo = paineis.tatica;
    caixa("Passos", [
      el("div", { class: "linha", id: "pr-passos" }),
      // o cabeçote: o horário do round que o editor mostra e edita (formato 3)
      el("div", { class: "linha" }, [el("label", { for: "pr-cabecote", texto: "Horário" }),
        el("input", { type: "range", id: "pr-cabecote", min: "0", step: "0.25", "aria-label": "Horário do round" }),
        el("output", { id: "pr-cabecote-relogio", for: "pr-cabecote" })]),
      el("div", { class: "linha" }, [el("input", { type: "text", id: "pr-passo-titulo", "aria-label": "Título do passo",
                                                   placeholder: "o que acontece neste passo" })]),
      el("div", { class: "linha" }, [el("label", { for: "pr-passo-duracao", texto: "Duração (s)" }),
        el("input", { type: "number", id: "pr-passo-duracao", min: "0.5", step: "0.5" }),
        el("button", { class: "pr-b", id: "pr-remove-passo", texto: "Remover passo" })])]);
    caixa("Tática", [
      el("div", { class: "linha" }, [el("select", { id: "pr-taticas", "aria-label": "Táticas deste mapa" }),
        el("button", { class: "pr-b", id: "pr-nova", texto: "Nova" })]),
      el("div", { class: "linha" }, [el("input", { type: "text", id: "pr-titulo", "aria-label": "Título da tática" })]),
      el("div", { class: "linha" }, [el("button", { class: "pr-b", id: "pr-exporta", texto: "Exportar" }),
        el("button", { class: "pr-b", id: "pr-importa", texto: "Importar" }),
        el("button", { class: "pr-b", id: "pr-apaga", texto: "Apagar" }),
        el("input", { type: "file", id: "pr-arquivo", accept: ".json,application/json", hidden: "" })]),
      el("div", { class: "linha" }, [el("label", { for: "pr-autor", texto: "Autor" }),
        el("input", { type: "text", id: "pr-autor", placeholder: "seu nome" })]),
      el("p", { class: "pr-meta", id: "pr-origem", hidden: "" }),
      // depuração: fechado por padrão, para quem usa a prancheta não ver o contador sem pedir (auditoria 5.3)
      el("details", { class: "pr-detalhes", id: "pr-detalhes" }, [
        el("summary", { texto: "Detalhes técnicos" }),
        el("p", { class: "pr-meta", id: "pr-contador" })]),
      el("p", { id: "pr-aviso", hidden: "" })]);
    abaDoPainel("jogadores");
  }


