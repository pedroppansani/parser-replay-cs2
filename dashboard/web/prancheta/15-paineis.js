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

  function tempo(seg) {
    if (seg == null) return "";
    var s = Math.max(0, Math.round(seg));
    return Math.floor(s / 60) + ":" + String(s % 60).padStart(2, "0");
  }

  function descreveArremesso(r) {
    var partes = [];
    // força AFIRMADA só com botão (rotina do jogo, decisão 21a); sem ele, a
    // velocidade é estimativa do modelo e aparece como tal
    if (r.forca && r.botao) partes.push(r.forca + " (" + r.botao + ")");
    else if (r.velocidade !== null && r.velocidade !== undefined) partes.push("força não afirmada (estimativa: " + r.velocidade + " u/s)");
    if (r.postura) partes.push(r.postura);
    if (r.movimento) partes.push(r.movimento);
    if (r.no_ar) partes.push("no ar (pulo)");
    return partes.join(" · ");
  }

  /** De onde veio cada afirmação da ficha (rota B, decisão 21a): "lido" da
      demo ou "inferido" pela rotina do jogo. Discreto, mas nunca omitido. */
  var NOME_DA_FONTE = { botao: "botão", postura: "postura", no_ar: "no ar", origem: "saída" };
  function descreveFontes(fontes) {
    if (!fontes) return "";
    var por = { lido: [], inferido: [] };
    Object.keys(NOME_DA_FONTE).forEach(function (k) {
      if (por[fontes[k]]) por[fontes[k]].push(NOME_DA_FONTE[k]);
    });
    var partes = [];
    if (por.lido.length) partes.push("lido da demo: " + por.lido.join(", "));
    if (por.inferido.length) partes.push("inferido pela rotina do jogo: " + por.inferido.join(", "));
    return partes.join(" · ");
  }

  // Uma tática no meio da criação (antes do primeiro passo) não tem quadro.
  function temQuadro() { return !!(S.estado && S.estado.passos.length); }

  var bancoDe = null;   // de que tática o banco foi montado

  function atualizaTudo() {
    if (!temQuadro()) return;
    if (bancoDe !== S.doc.id) { bancoDe = S.doc.id; montaBanco(); }
    atualizaBiblioteca(); atualizaPassos(); atualizaPainel(); atualizaBusca(); atualizaFerramentas();
    atualizaBanco(); atualizaBarra(); atualizaAviso(); atualizaContexto(); atualizaDica(); desenha();
    atualizaRelogioGrande(); atualizaLinhaDoTempo();
    if (ganchos.aoAtualizar) ganchos.aoAtualizar();
  }

  function atualizaAviso() { $("pr-aviso").textContent = S.aviso; $("pr-aviso").hidden = !S.aviso; }

  function atualizaBiblioteca() {
    var sel = limpa($("pr-taticas"));
    var lista = Armazem.lista(cfg.mapa), atual = false;
    lista.forEach(function (r) {
      var o = el("option", { value: r.id, texto: r.titulo + (r.autores.length > 1 ? " · " + r.autores.length + " autores" : "") });
      if (S.doc && r.id === S.doc.id) { o.selected = true; atual = true; }
      sel.appendChild(o);
    });
    if (S.doc && !atual) {
      // fora da lista: ou está vazia (não é gravada) ou a gravação ainda está no atraso
      sel.insertBefore(el("option", { value: S.doc.id, texto: (S.estado.titulo || "Nova tática") + (vazia(S.doc) ? " (vazia)" : "") }), sel.firstChild);
      sel.value = S.doc.id;
    }
    if (document.activeElement !== $("pr-titulo")) $("pr-titulo").value = S.estado ? S.estado.titulo : "";
    // o "N operações · contador N" é depuração (auditoria 5.3): só dentro de "Detalhes técnicos", fechado
    // por padrão; continua inteiro no JSON exportado (`operacoes`, `contador`)
    $("pr-contador").textContent = S.doc ? textoDoContador(S.doc) : "";
    var desc = $("pr-origem");
    desc.textContent = S.doc && S.doc.origem ? textoDaOrigem(S.doc.origem) : "";
    desc.hidden = !(S.doc && S.doc.origem);
  }

  /** "12 operações · contador 12" (singular com uma só). */
  function textoDoContador(doc) {
    var n = doc.operacoes.length;
    return n + (n === 1 ? " operação" : " operações") + " · contador " + doc.contador;
  }

  function atualizaPassos() {
    var barra = limpa($("pr-passos"));
    S.estado.passos.forEach(function (p, i) {
      barra.appendChild(el("button", {
        class: "pr-passo" + (i === S.passo ? " ativo" : ""), "data-passo": String(i + 1),
        title: p.titulo || "Passo " + (i + 1), texto: String(i + 1),
        onclick: function () { mudaPasso(i); }
      }));
    });
    barra.appendChild(el("button", { class: "pr-passo novo", id: "pr-novo-passo", title: comAtalho("Novo passo", "Novo passo"),
      texto: "+", onclick: novoPasso }));
    var atual = S.estado.passos[S.passo];
    if (document.activeElement !== $("pr-passo-titulo")) $("pr-passo-titulo").value = atual ? atual.titulo : "";
    if (document.activeElement !== $("pr-passo-duracao")) $("pr-passo-duracao").value = atual ? String(atual.duracao_s) : "";
    $("pr-remove-passo").disabled = S.estado.passos.length <= 1;
    var cab = $("pr-cabecote");
    if (cab && M3) {
      cab.max = String(limiteDoTempo());
      if (document.activeElement !== cab) cab.value = String(S.t);
      $("pr-cabecote-relogio").textContent = MapCore.relogio(S.t, S.e3 && S.e3.bomba ? S.e3.bomba.t : null, null,
        M3.SEGUNDOS_DO_ROUND, M3.SEGUNDOS_DA_BOMBA) + " · " + String(S.t).replace(".", ",") + " s";
    }
  }

  function atualizaFerramentas() {
    var estado = estadoDaInteracao();
    Array.prototype.forEach.call(document.querySelectorAll("[data-ferramenta]"), function (b) {
      var f = b.getAttribute("data-ferramenta");
      var ativo = f === "mover" ? (S.ferramenta === "mover" && !S.acao)
                : f === "buscar" ? estado === "buscando"
                : f === "granada" ? !!(S.acao && S.acao.legado)
                : f === S.ferramenta;
      b.classList.toggle("ativo", ativo);
    });
    Array.prototype.forEach.call(document.querySelectorAll("[data-arma]"), function (b) {
      b.classList.toggle("ativo", !!(S.acao && (S.acao.tipo === "granada" || S.acao.tipo === "busca") &&
                                     b.getAttribute("data-arma") === S.acao.arma));
    });
    Array.prototype.forEach.call(document.querySelectorAll("[data-espessura]"), function (b) {
      b.classList.toggle("ativo", b.getAttribute("data-espessura") === String(S.espessura));
    });
  }

  /** Controles de contexto: só aparecem quando servem. Cor e espessura com uma
      ferramenta de desenho; raio e "só parados" com as sugestões (ou a busca). */
  function atualizaContexto() {
    var desenho = !!(ROTULO_FERRAMENTA[S.ferramenta]) && S.ferramenta !== "borracha" && S.ferramenta !== "granada_desenho";
    var ctxDesenho = $("pr-contexto-desenho");
    if (ctxDesenho) ctxDesenho.hidden = !desenho;
    var ctxGranada = $("pr-contexto-granada");
    if (ctxGranada) ctxGranada.hidden = S.ferramenta !== "granada_desenho";
    // a coluna continua no lugar (a folga do mapa é medida nela), só fica invisível sem opção nenhuma
    var opcoes = $("pr-opcoes");
    if (opcoes) opcoes.classList.toggle("vazia", !desenho && S.ferramenta !== "granada_desenho");
    Array.prototype.forEach.call(document.querySelectorAll("[data-arma-desenho]"), function (b) {
      var on = b.getAttribute("data-arma-desenho") === S.armaDesenho;
      b.classList.toggle("ativo", on); b.setAttribute("aria-pressed", String(on));
    });
    var comBusca = !!(S.busca || (S.acao && S.acao.tipo === "busca"));
    var filtros = $("pr-filtros-busca");
    if (filtros) filtros.hidden = !comBusca;
  }

  function atualizaBanco() {
    var q = quadro();
    var lista = $("pr-funcoes-banco");
    if (lista && M3) {
      limpa(lista);
      Object.keys(S.estado.pecas).sort(function (a, b) {
        var pa = S.estado.pecas[a], pb = S.estado.pecas[b];
        return pa.lado.localeCompare(pb.lado) || rotuloDaPeca(pa).localeCompare(rotuloDaPeca(pb));
      }).forEach(function (pid) {
        lista.appendChild(el("div", { class: "linha pr-funcao-linha" }, [
          el("span", { class: "pr-funcao-nome " + S.estado.pecas[pid].lado, texto: nomePeca(pid) }), campoDeFuncao(pid)]));
      });
    }
    Array.prototype.forEach.call(document.querySelectorAll(".pr-ficha"), function (f) {
      var noMapa = Object.keys(q.pecas).some(function (id) {
        return q.pecas[id].lado === f.getAttribute("data-lado") && q.pecas[id].rotulo === f.getAttribute("data-rotulo");
      });
      f.classList.toggle("no-mapa", noMapa);
      f.title = noMapa ? "No mapa neste passo: clique para selecionar, ou arraste para mover"
                       : "Clique e depois clique no mapa para colocar, ou arraste para o mapa";
      var armada = !!(S.acao && S.acao.tipo === "colocar" && S.acao.lado === f.getAttribute("data-lado") &&
                      S.acao.rotulo === f.getAttribute("data-rotulo"));
      f.classList.toggle("armada", armada);
      f.setAttribute("aria-pressed", String(armada));
      var nomeDaFicha = (f.getAttribute("data-lado") === "ct" ? "CT " : "TR ") + f.getAttribute("data-rotulo");
      f.setAttribute("aria-label", nomeDaFicha + (noMapa ? ", no mapa: selecionar"
        : armada ? ", pronta: clique no mapa, ou Enter de novo para pôr no centro" : ": colocar no mapa"));
    });
  }

  function atualizaBarra() {
    var z = $("pr-zoom");
    if (z) z.textContent = Math.round(S.view.zoom * 100) + "%";
    var d = $("pr-desfaz"), r = $("pr-refaz");
    if (d) d.disabled = !S.pilhaDesfazer.length;
    if (r) r.disabled = !S.pilhaRefazer.length;
    Array.prototype.forEach.call(document.querySelectorAll("[data-andar]"), function (b) {
      b.classList.toggle("ativo", Number(b.getAttribute("data-andar")) === S.andar);
    });
    var fs = $("pr-tela-cheia");
    if (fs) fs.textContent = emTelaCheia() ? "Sair" : "Tela cheia";
    if (cores) cores.atualizaCores();
  }

  function controleDeVida(alvo, dura) {
    var fim = dura === null || dura === undefined;
    var n = el("input", { type: "number", id: "pr-vida", min: "1", step: "1", value: fim ? "1" : String(dura) });
    var ate = el("input", { type: "checkbox", id: "pr-vida-fim" });
    ate.checked = fim; n.disabled = fim;
    function aplicaVida() {
      var v = ate.checked ? null : Math.max(1, Math.round(+n.value || 1));
      emite("define_vida", { alvo: alvo, dura_passos: v });
    }
    n.addEventListener("change", aplicaVida);
    ate.addEventListener("change", aplicaVida);
    return el("div", { class: "linha" }, [el("label", { for: "pr-vida", texto: "Fica por" }), n,
      el("span", { texto: "passo(s)" }), el("label", {}, [ate, el("span", { texto: " até o fim" })])]);
  }

  function atualizaPainel() {
    // o último jogador selecionado é o arremessador de "Converter em granada com horário"
    if (S.sel && S.sel.tipo === "peca") S.ultimaPeca = S.sel.id;
    var box = limpa($("pr-selecao"));
    if (!S.sel) {
      box.appendChild(el("p", { class: "pr-dica", texto: "Nada selecionado. Clique num jogador no mapa ou no banco; com ele selecionado, 1 a 4 joga uma granada a partir dele." }));
      return;
    }
    var q = quadro();
    if (S.sel.tipo === "peca") {
      var p = S.estado.pecas[S.sel.id];
      var noQuadro = q.pecas[S.sel.id];
      box.appendChild(el("h3", { texto: rotuloDaPeca(p) }));
      if (noQuadro) {
        var yaw = yawDaPeca(S.sel.id, noQuadro);
        box.appendChild(el("p", { class: "pr-meta", id: "pr-peca-direcao",
          texto: (noQuadro.direcao_padrao && !S.giro ? "Olhando para o centro do mapa (" : "Olhando para ") + Math.round(yaw) + "°" + (noQuadro.direcao_padrao && !S.giro ? ", direção padrão)" : "") }));
        box.appendChild(el("div", { class: "linha" }, [
          el("button", { class: "pr-b", id: "pr-gira-anti", texto: "\u21ba 15\u00b0", title: comAtalho("Girar 15\u00b0 no sentido anti-horário", ATALHOS[10].acao),
            onclick: function () { giraSelecionada(PASSO_GIRO); } }),
          el("button", { class: "pr-b", id: "pr-gira-hor", texto: "\u21bb 15\u00b0", title: comAtalho("Girar 15\u00b0 no sentido horário", ATALHOS[11].acao),
            onclick: function () { giraSelecionada(-PASSO_GIRO); } })]));
        box.appendChild(el("button", { class: "pr-b", id: "pr-tira-peca", texto: "Tirar do mapa neste passo",
          onclick: function () { emite("tira_peca", { peca: S.sel.id, passo: passoAtual() }); } }));
      } else {
        box.appendChild(el("p", { class: "pr-meta", texto: "Fora do mapa neste passo: arraste do banco para recolocar." }));
      }
      if (M3) {
        box.appendChild(el("div", { class: "linha" }, [el("label", { for: "pr-funcao", texto: "Função" }),
                                                       campoDeFuncao(S.sel.id, "pr-funcao")]));
        box.appendChild(painelDoCaminho(S.sel.id));
      }
      box.appendChild(el("button", { class: "pr-b", id: "pr-apaga-peca", texto: "Apagar peça da tática", onclick: removeSelecionado }));
      return;
    }
    if (S.sel.tipo === "traco") {
      var t = S.estado.tracos[S.sel.id];
      if (t.ferramenta === "granada") {
        var tid = S.sel.id;
        box.appendChild(el("h3", { texto: NOME_ARMA[t.arma] + " desenhada · passo " + (indiceDoPasso(t.passo) + 1) }));
        box.appendChild(el("p", { class: "pr-meta", texto: "Desenho, sem horário: não entra na linha do tempo nem no roteiro." }));
        if (t.arma === "smoke" || t.arma === "molotov") {
          box.appendChild(el("button", { class: "pr-b", id: "pr-area-desenho", "aria-pressed": String(!!t.area),
            texto: t.area ? "Esconder a área" : "Mostrar a área", onclick: function () { alternaAreaDesenho(tid); } }));
        }
        if (M3) {
          var pe = S.ultimaPeca && S.e3 ? quadroNoTempo(S.e3, S.t, CENTRO).pecas[S.ultimaPeca] : null;
          var conv = el("button", { class: "pr-b", id: "pr-converte-desenho", texto: "Converter em granada com horário",
            onclick: function () { converteDesenho(tid); } });
          if (pe) conv.title = "Sai de " + nomePeca(S.ultimaPeca) + " às " + relogioEm(S.t) + " e cai neste ponto";
          else { conv.disabled = true; conv.title = "Selecione antes o jogador que joga a granada (ele precisa estar no mapa no horário do cabeçote)"; }
          box.appendChild(conv);
        }
        box.appendChild(controleDeVida(tid, t.dura_passos));
        box.appendChild(el("button", { class: "pr-b", texto: "Apagar desenho", onclick: removeSelecionado }));
        return;
      }
      box.appendChild(el("h3", { texto: ROTULO_FERRAMENTA[t.ferramenta] + " · passo " + (indiceDoPasso(t.passo) + 1) }));
      box.appendChild(controleDeVida(S.sel.id, t.dura_passos));
      box.appendChild(el("button", { class: "pr-b", texto: "Apagar desenho", onclick: removeSelecionado }));
      return;
    }
    var g = S.estado.granadas[S.sel.id];
    box.appendChild(el("h3", { texto: NOME_ARMA[g.arma] + " · passo " + (indiceDoPasso(g.passo) + 1) }));
    var g3 = S.e3 && S.e3.granadas[S.sel.id];
    if (g3) {
      var gid = S.sel.id;
      var hora = el("input", { type: "number", id: "pr-granada-t", step: "0.1", min: "0", value: String(g3.t),
                               "aria-label": "Horário do arremesso (s)" });
      hora.addEventListener("change", function () { var v = parseFloat(hora.value); if (isFinite(v)) mudaHorarioDaGranada(gid, v); });
      box.appendChild(el("div", { class: "linha" }, [el("label", { for: "pr-granada-t", texto: "Jogada às" }), hora,
        el("span", { class: "pr-meta", texto: MapCore.relogio(g3.t, S.e3.bomba ? S.e3.bomba.t : null, null, M3.SEGUNDOS_DO_ROUND, M3.SEGUNDOS_DA_BOMBA) +
          (g3.jogador && S.estado.pecas[g3.jogador] ? " · " + nomePeca(g3.jogador) : "") })]));
    }
    if (S.atraso && S.atraso.granada === S.sel.id) {
      var at = S.atraso;
      box.appendChild(el("p", { class: "pr-alerta", id: "pr-atraso",
        texto: nomePeca(at.peca) + " chega " + at.segundos.toFixed(1).replace(".", ",") + " s depois do arremesso." }));
      box.appendChild(el("button", { class: "pr-b", id: "pr-adiar", onclick: adiaArremesso,
        texto: "Adiar o arremesso para " + MapCore.relogio(at.t, S.e3.bomba ? S.e3.bomba.t : null, null, M3.SEGUNDOS_DO_ROUND, M3.SEGUNDOS_DA_BOMBA) }));
    }
    if (g.arremesso) {
      var r = g.arremesso;
      box.appendChild(el("p", { class: "pr-meta", texto: r.jogador + " · " + r.partida + " round " + r.round + " (" + tempo(r.segundos_no_round) + ")" }));
      box.appendChild(el("p", { class: "pr-meta", texto: descreveArremesso(r) }));
      var fonte = descreveFontes(r.fontes);
      if (fonte) box.appendChild(el("p", { class: "pr-fonte", id: "pr-fonte", texto: fonte }));
      var cmd = el("code", { id: "pr-comando", texto: r.comando });
      box.appendChild(el("div", { class: "pr-cmd" }, [cmd, el("button", { class: "pr-b", id: "pr-copia", texto: "Copiar",
        onclick: function () { copiaTexto(r.comando); } })]));
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
    } else if (g.origem_desconhecida) {
      box.appendChild(el("p", { class: "pr-meta", texto: "Veio do replay sem ligação com o arremesso: só o efeito é conhecido, e a origem fica em branco." }));
    } else {
      box.appendChild(el("p", { class: "pr-meta", texto: "Desenhada à mão: mostra onde cai, não como chegar lá." }));
    }
    box.appendChild(controleDeVida(S.sel.id, g.dura_passos));
    box.appendChild(el("button", { class: "pr-b", texto: "Apagar granada", onclick: removeSelecionado }));
  }

  /** A função que o round do replay deu à peça (operação da base real), ou null. */
  function funcaoDoReplay(pid) {
    var b = baseReal();
    if (b === null) return null;
    var op = S.doc.operacoes.filter(function (o) { return o.seq <= b && o.tipo === "define_funcao" && o.peca === pid; }).pop();
    return op ? op.funcao : null;
  }

  /** O campo de função de uma peça: o vocabulário do projeto (player_roles +
      structural_roles + IGL), injetado no build -- nada digitado aqui. */
  function campoDeFuncao(pid, id) {
    var atual = S.e3 && S.e3.pecas[pid] ? S.e3.pecas[pid].funcao : null;
    var s = el("select", { class: "pr-funcao", "data-peca": pid, "aria-label": "Função de " + nomePeca(pid) });
    if (id) s.id = id;
    s.appendChild(el("option", { value: "", texto: "sem função" }));
    // num round do replay, a função que veio dos rótulos estruturais aparece
    // marcada "do replay" enquanto o usuário não a trocar
    var doReplay = funcaoDoReplay(pid);
    M3.FUNCOES.forEach(function (f) {
      s.appendChild(el("option", { value: f, texto: f + (f === doReplay && f === atual ? " (do replay)" : "") }));
    });
    if (doReplay && doReplay === atual) s.setAttribute("data-do-replay", "");
    s.value = atual || "";
    s.addEventListener("change", function () { emite("define_funcao", { peca: pid, funcao: s.value || null }); });
    return s;
  }

  /** Modo do próximo trecho e a lista de pontos-chave, com o horário editável e
      o "esperar aqui", que empurra os pontos seguintes (uma ação no desfazer). */
  function painelDoCaminho(pid) {
    var caixaC = el("div", { class: "pr-caminho", id: "pr-caminho" });
    var modos = el("div", { class: "linha", id: "pr-modos-caminho" });
    M3.MODOS_DE_ANDAR.forEach(function (m) {
      modos.appendChild(el("button", { class: "pr-b" + (S.modoCaminho === m ? " on" : ""), "data-modo": m,
        texto: m.charAt(0).toUpperCase() + m.slice(1), "aria-pressed": S.modoCaminho === m ? "true" : "false",
        onclick: function () { S.modoCaminho = m; atualizaPainel(); } }));
    });
    caixaC.appendChild(modos);
    var pontos = (S.e3.pecas[pid] || { pontos: [] }).pontos.filter(function (pt) { return !pt.fora; });
    var lista = el("ol", { class: "pr-pontos", id: "pr-pontos" });
    pontos.forEach(function (pt) {
      var hora = el("input", { type: "number", step: "0.1", min: "0", value: String(pt.t), "data-ponto": pt.id,
                               class: "pr-ponto-t", "aria-label": "Horário do ponto (s)" });
      hora.addEventListener("change", function () {
        var v = parseFloat(hora.value);
        if (isFinite(v)) emite("move_ponto", { peca: pid, ponto: pt.id, t: v, x: pt.x, y: pt.y, nivel: pt.nivel });
      });
      var espera = el("input", { type: "number", step: "0.5", min: "0", placeholder: "0", "data-espera": pt.id,
                                 class: "pr-ponto-espera", "aria-label": "Esperar aqui (s)" });
      espera.addEventListener("change", function () {
        var w = parseFloat(espera.value);
        if (!(isFinite(w) && w > 0)) return;
        var seguintes = pontos.filter(function (q) { return q.t > pt.t + EPS_T; });
        emiteLote(seguintes.map(function (q) {
          return ["move_ponto", { peca: pid, ponto: q.id, t: Math.round((q.t + w) * 100) / 100, x: q.x, y: q.y, nivel: q.nivel }];
        }));
      });
      lista.appendChild(el("li", {}, [
        el("span", { texto: MapCore.relogio(pt.t, S.e3.bomba ? S.e3.bomba.t : null, null, M3.SEGUNDOS_DO_ROUND, M3.SEGUNDOS_DA_BOMBA) }),
        hora, el("label", { texto: "esperar aqui (s)" }), espera]));
    });
    caixaC.appendChild(lista);
    return caixaC;
  }

  function atualizaBusca() {
    var box = limpa($("pr-resultados"));
    if (!S.busca) return;
    var b = S.busca;
    if (S.sugestao) {
      box.appendChild(el("button", { class: "pr-b pr-manter", id: "pr-manter-mao",
        texto: "Desenhar à mão, saindo de " + S.sugestao.de + " (já está no mapa)",
        onclick: function () { S.busca = null; S.sugestao = null; atualizaTudo(); } }));
    }
    box.appendChild(el("p", { class: "pr-meta", texto: b.total === 0
      ? "Nenhum arremesso real de " + NOME_ARMA[b.arma] + " cai a menos de " + b.raio + "u daqui no corpus."
      : b.total + " arremessos reais de " + NOME_ARMA[b.arma] + " caem a menos de " + b.raio + "u daqui" +
        (b.total > b.resultados.length ? " (os " + b.resultados.length + " mais perto)" : "") + "." }));
    var lista = el("ol", { class: "pr-lista" });
    b.resultados.forEach(function (r, n) {
      lista.appendChild(el("li", {
        "data-arremesso": r.id,
        onmouseenter: function () { S.busca.foco = n; desenha(); },
        onmouseleave: function () { S.busca.foco = null; desenha(); },
        onclick: function () { if (S.sugestao) trocaPorArremesso(r); else usaArremesso(r); }
      }, [el("strong", { texto: r.jogador }), el("span", { texto: " " + r.partida + " r" + r.round + " · " + descreveArremesso(r) })]));
    });
    box.appendChild(lista);
  }

  function copiaTexto(texto) {
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

