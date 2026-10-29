  /* ================= PERFIL DO JOGADOR ================= */

  (function perfil() {
    var CAT = {
      "Posicionamento": [
        ["pct_rounds_longe_do_time", "Joga longe do time"],
        ["pct_rounds_isolado", "Fica isolado"],
        ["pct_rounds_ancorado", "Ancora num lugar só"],
        ["pct_rounds_rotacionando", "Passa por muitas regiões"]
      ],
      "Arma e abertura": [
        ["pct_rounds_com_awp", "Pega a AWP"],
        ["pct_kills_de_awp", "Kills que saíram de AWP"],
        ["pct_rounds_abertura_awp", "Abre o round de AWP"],
        ["pct_rounds_smg_ou_pistola_com_time_de_rifle", "Fica com a arma pior que o time"]
      ],
      "Tempo e contato": [
        ["pct_rounds_contato_cedo", "Encosta cedo no adversário"],
        ["pct_rounds_contato_tarde", "Encosta depois do time"],
        ["pct_rounds_primeiro_contato_do_time", "É o primeiro do time a encostar"]
      ],
      "Resultado e trade": [
        ["pct_rounds_sobreviveu", "Sobrevive ao round"],
        ["pct_mortes_trocadas", "Mortes dele que o time trocou"],
        ["pct_rounds_trade_kill", "Troca a morte do companheiro"],
        ["pct_rounds_em_clutch", "Fica por último"],
        ["taxa_conversao_clutch", "Converte quando fica por último"]
      ],
      "Lurk": [
        ["pct_rounds_lurk", "Lurk: isolado, longe do time e encostando depois"]
      ]
    };
    // Quanto o jogador precisa se afastar da mediana dos outros para o número
    // ser destacado. Abaixo disso, destacar seria transformar ruido em achado.
    var MARGEM_DESTAQUE = 0.15;

    // Os números do jogador são SÓ desta partida (regra dos três níveis). Não
    // existe seletor de base: o que vem do corpus é a régua de comparação, e ela
    // é anônima. O texto do aviso é montado aqui porque o payload traz só os
    // números -- nenhuma frase fica escrita no template (decisão 18).
    var daPartida = D.player_profile || [];
    if (!daPartida.length) return;
    // Rótulo da régua, usado no card, na tabela e no aviso -- um lugar só, para
    // as três telas não contarem histórias diferentes sobre a mesma comparação.
    var REGUA = (D.perfil_regua || {});
    var REGUA_ROTULO = (REGUA.origem === "corpus" && REGUA.partidas > 1)
      ? "mediana do corpus" : "mediana dos outros desta partida";
    (function avisoDaRegua() {
      var r = D.perfil_regua || {};
      var el = document.getElementById("pf-regua");
      if (!el) return;
      if (r.origem === "corpus" && r.partidas > 1) {
        el.textContent = "comparado com " + r.jogador_partidas + " jogador-partidas de " +
          r.partidas + " partidas";
        el.className = "pfregua";
      } else {
        el.textContent = "comparado só com os outros jogadores desta partida — amostra fraca";
        el.className = "pfregua fraca";
      }
    })();

    var botoes = document.getElementById("pf-botoes");
    // o bloco novo da fase 12 (leitura/perfil_erros.py); sem ele, a aba mostra só os Detalhes
    var PF = PAGINA.perfil || null;
    var selB = document.getElementById("pf-b");
    var escolhido = null;

    function base() {
      return daPartida;
    }
    function acha(nome) {
      var b = base();
      for (var i = 0; i < b.length; i++) if (b[i].name === nome) return b[i];
      return null;
    }

    // Time de cada jogador, para os botões saírem agrupados por time em vez de
    // numa fila alfabética de dez nomes.
    var timeDoJogador = {};
    (D.roles || []).forEach(function (r) { timeDoJogador[r.name] = r.team; });

    function nomesDaBase() {
      return base().map(function (p) { return p.name; });
    }

    function montaBotoes() {
      var nomes = nomesDaBase();
      var porTime = { "A": [], "B": [], "": [] };
      nomes.forEach(function (n) { (porTime[timeDoJogador[n] || ""]).push(n); });

      var html = "";
      ["A", "B", ""].forEach(function (t) {
        var lista = porTime[t].sort();
        if (!lista.length) return;
        if (t) html += "<span class='timelab'>" + esc(nomeLado(t)) + "</span>";
        html += lista.map(function (n) {
          return "<button type='button' data-nome=\"" + esc(n) + "\" aria-pressed='" +
            (n === escolhido) + "'>" + esc(n) + "</button>";
        }).join("");
      });
      botoes.innerHTML = html;

      Array.prototype.forEach.call(botoes.querySelectorAll("button"), function (b) {
        b.addEventListener("click", function () {
          escolhido = b.getAttribute("data-nome");
          montaBotoes();
          preencheSelects();
          desenha();
        });
      });
    }

    // fase 12: o jogador aberto por padrão é o de maior rating (PF.padrao, decidido no build) e o
    // "Comparar com" oferece só os OUTROS jogadores desta partida (decisão 30)
    function preencheSelects() {
      var nomes = nomesDaBase().sort();
      if (escolhido === null && PF && nomes.indexOf(PF.padrao) >= 0) escolhido = PF.padrao;
      if (nomes.indexOf(escolhido) < 0) escolhido = nomes[0];
      var atual = selB.value;
      var outros = nomes.filter(function (n) { return n !== escolhido; });
      selB.innerHTML = "<option value=''>" + esc(PF ? PF.textos.ninguem : "—") + "</option>" +
        outros.map(function (n) { return "<option>" + esc(n) + "</option>"; }).join("");
      if (outros.indexOf(atual) >= 0) selB.value = atual;
    }

    function pct(v) { return v === null || v === undefined ? "—" : Math.round(v * 100) + "%"; }

    // "dentro do normal para a função": o booleano vem do Python (leitura/perfil_erros.dentro_do_normal)
    function dentroDoNormal(nome, chave) {
      if (!PF) return false;
      for (var i = 0; i < PF.jogadores.length; i++) {
        if (PF.jogadores[i].name === nome) return !!(PF.jogadores[i].dentro_do_normal || {})[chave];
      }
      return false;
    }

    function celula(p, chave) {
      var v = p[chave], n = p[chave + "_n"], d = p[chave + "_d"], ref = p[chave + "_ref"];
      if (d === null || d === undefined || d === 0) {
        return "<td class='num'>—<span class='bruto'>sem denominador</span></td>";
      }
      var fraco = p[chave + "_fraco"];
      var fora = !fraco && v !== null && ref !== null && ref !== undefined &&
                 Math.abs(v - ref) >= MARGEM_DESTAQUE;
      var largura = v === null ? 0 : Math.max(2, Math.min(100, v * 100));
      return "<td class='num'>" +
        "<span class='pfbarra'><i class='" + (fora ? "destaque" : "") +
        "' style='width:" + largura + "%'></i></span>" +
        "<b>" + pct(v) + "</b>" +
        "<span class='bruto'>" + n + " de " + d + "</span>" +
        (fraco ? "<span class='fraco'>amostra fraca</span>" : "") +
        (dentroDoNormal(p.name, chave) ? " <span class='tag neutro normal'>" + esc(PF.textos.rotulo_dentro_do_normal) + "</span>" : "") +
        "</td>";
    }

    function cabecalho(p) {
      if (!p) return "";
      var partidas = p.partidas || 1;
      var grupo = p.grupo_dominante === null || p.grupo_dominante === undefined
        ? "sem grupo dominante"
        : (nomeDoGrupoPerfil(p.grupo_dominante) + " · " + p.grupo_dominante_n +
           " de " + p.grupo_dominante_d + " rounds");
      // fase 12 (inventário 12.1): kills / assists / mortes saíram daqui; repetiam K, A e M da aba Jogadores
      return "<div><b>" + esc(p.name) + "</b><br>" + esc(p.rounds_jogados) + " rounds em " +
        partidas + (partidas > 1 ? " partidas" : " partida") + "</div>" +
        "<div>função no round<br>" + funcaoPorLado(p.name) + "</div>" +
        "<div>jeito de jogar mais frequente<br><b style='font-size:13px'>" + esc(grupo) + "</b></div>";
    }

    // Função ESTRUTURAL, por lado. É leitura diferente do perfil comportamental
    // logo abaixo: uma diz o que ele FAZ no round, a outra COMO ele faz. Um
    // âncora pode ser carrega piano ou baiter, e as duas coisas são verdade.
    var FUNC_LABELS = D.structural_role_labels || {};
    var funcPorJogador = {};
    (D.structural_roles || []).forEach(function (r) {
      (funcPorJogador[r.name] = funcPorJogador[r.name] || {})[r.side] = r;
    });

    function funcaoPorLado(nome) {
      var f = funcPorJogador[nome];
      if (!f) return "<b style='font-size:13px'>—</b>";
      return ["ct", "t"].map(function (lado) {
        var r = f[lado];
        var rot = lado === "ct" ? "CT" : "TR";
        if (r && r.texto_empate) {
          // empate na função dominante: o texto (com as concentrações lado a lado)
          // vem pronto do Python -- metrics/structural_roles.texto_empate
          return "<span class='fnlado'><i>" + rot + "</i> " + esc(r.texto_empate) + "</span>";
        }
        if (!r || !r.funcao) {
          return "<span class='fnlado'><i>" + rot + "</i> sem função definida</span>";
        }
        // A concentração anda SEMPRE junto: quem ancora em 9 de 12 rounds não é
        // a mesma coisa que quem ancora em 12, e é essa nuance que se perde num
        // rótulo seco.
        var conc = r.rounds_na_funcao + " de " + r.rounds_no_lado;
        var fraca = r.amostra_fraca ? " <em>amostra fraca</em>" : "";
        return "<span class='fnlado'><i>" + rot + "</i><b>" +
          esc(FUNC_LABELS[r.funcao] || r.funcao) + "</b> " + conc + fraca + "</span>";
      }).join("");
    }

    function nomeDoGrupoPerfil(c) {
      var dado = (D.cluster_names || {})[String(c)];
      if (dado) return dado;
      var desc = (D.cluster_descriptions || []).filter(function (x) { return x.cluster === c; })[0];
      return desc ? desc.titulo : "grupo " + c;
    }

    function leitura(p) {
      if (!p || !p.descricao) return "";
      var d = p.descricao;
      var tracos = (d.caracteristicas || []).map(function (c) {
        return "<div class='traco" + (c.acima ? "" : " abaixo") + "'>" +
          "<b>" + esc(c.texto) + "</b>" +
          "<span>" + Math.round(c.taxa * 100) + "% · " + c.n + " de " + c.d + " " +
          (c.unidade || "rounds") +
          " · " + REGUA_ROTULO + " " + Math.round(c.ref * 100) + "%</span></div>";
      }).join("");
      return "<div class='quem'>Como " + esc(p.name) + " joga</div>" +
        "<h3>" + esc(d.titulo) + "</h3>" +
        "<p>" + esc(d.resumo) + "</p>" +
        (tracos ? "<div class='pftracos'>" + tracos + "</div>" : "");
    }

    function desenha() {
      var a = acha(escolhido), b = selB.value ? acha(selB.value) : null;
      document.getElementById("pf-leitura").innerHTML = leitura(a);
      document.getElementById("pf-head").innerHTML = cabecalho(a) + cabecalho(b);

      var html = "";
      Object.keys(CAT).forEach(function (cat) {
        var linhas = CAT[cat].map(function (par) {
          var chave = par[0], rotulo = par[1];
          if (!a || a[chave + "_d"] === undefined) return "";
          var ref = a[chave + "_ref"];
          var destaque = a[chave] !== null && ref !== null && ref !== undefined &&
                         Math.abs(a[chave] - ref) >= MARGEM_DESTAQUE && !a[chave + "_fraco"];
          return "<tr class='" + (destaque ? "fora" : "") + "'>" +
            "<td>" + esc(rotulo) + "</td>" +
            celula(a, chave) +
            (b ? celula(b, chave) : "") +
            "<td class='refv'>" + pct(ref) + "</td></tr>";
        }).join("");

        html += "<div class='pfcat'><h3>" + esc(cat) + "</h3><table class='pf'>" +
          "<tr><th>Comportamento</th><th>" + esc(a ? a.name : "") + "</th>" +
          (b ? "<th>" + esc(b.name) + "</th>" : "") +
          "<th>" + REGUA_ROTULO + "</th></tr>" + linhas + "</table></div>";
      });

      // O tempo mediano não é taxa: entra como número solto, sem barra nem
      // denominador, porque fração de rounds não se aplica a ele.
      if (a && a.tempo_mediano_ate_contato_s !== null && a.tempo_mediano_ate_contato_s !== undefined) {
        html += "<p class='lead tight' style='margin-top:18px'>Tempo mediano até o primeiro " +
          "contato: <b>" + br(a.tempo_mediano_ate_contato_s) + "s</b>" +
          (b && b.tempo_mediano_ate_contato_s != null
            ? " · " + esc(b.name) + ": <b>" + br(b.tempo_mediano_ate_contato_s) + "s</b>" : "") +
          ". É mediana e não média: dois rounds sem contato distorcem a média.</p>";
      }
      document.getElementById("pf-tabela").innerHTML = html;
      desenhaNovo(a ? a.name : null, b ? b.name : null);
    }

    /* ---- fase 12: cabeçalho, pontos a melhorar, pontos fortes e comparar (frases do Python) ---- */
    function pfJogador(nome) {
      if (!PF) return null;
      for (var i = 0; i < PF.jogadores.length; i++) if (PF.jogadores[i].name === nome) return PF.jogadores[i];
      return null;
    }
    // §19.3: chips que levam ao Replay no round e no instante. "Visitado" vem do sessionStorage (try/catch: sem
    // armazenamento o chip só não fica marcado).
    var CHAVE_VISITADOS = "parser-cs2:chips-visitados";
    function lerVisitados() {
      try { return JSON.parse(sessionStorage.getItem(CHAVE_VISITADOS) || "{}") || {}; } catch (e) { return {}; }
    }
    function gravaVisitado(chave) {
      var v = lerVisitados();
      v[chave] = true;
      try { sessionStorage.setItem(CHAVE_VISITADOS, JSON.stringify(v)); } catch (e) { /* sem armazenamento */ }
    }
    function chipsDeRound(chips) {
      if (!chips || !chips.length) return "";
      var T = PF.textos, vis = lerVisitados();
      return "<div class='pfchips' role='group' aria-label='" + esc(T.rot_rounds) + "'>" + chips.map(function (c) {
        var jaAberto = !!vis[c.round + "@" + (c.t === null ? "" : c.t)];
        var titulo = c.titulo + (jaAberto ? " (" + T.ja_aberto + ")" : "");
        return "<button type='button' class='pfchip' data-round='" + esc(c.round) + "' data-t='" +
          esc(c.t === null ? "" : c.t) + "'" + (jaAberto ? " data-visitado" : "") + " title='" + esc(titulo) +
          "' aria-label='" + esc(titulo) + "'><span class='n'>" + esc(c.rotulo) + "</span>" +
          (c.relogio ? "<span class='h'>" + esc(c.relogio) + "</span>" : "") + "</button>";
      }).join("") + "</div>";
    }
    // a faixa rola numa linha; enquanto sobra chip fora da tela, sombra na borda direita (.rola); no fim, .fim
    function ligaRolagemDosChips(raiz) {
      Array.prototype.forEach.call(raiz.querySelectorAll(".pfchips"), function (c) {
        function atualiza() {
          var rola = c.scrollWidth > c.clientWidth + 2;
          c.classList.toggle("rola", rola);
          c.classList.toggle("fim", rola && c.scrollLeft + c.clientWidth >= c.scrollWidth - 2);
        }
        c.addEventListener("scroll", atualiza, { passive: true });
        window.addEventListener("resize", atualiza);
        atualiza();
      });
    }
    function etiquetaDeLado(lado, rotulo) {
      return rotulo ? "<span class='tag " + (lado === "t" ? "tr" : "ct") + "'>" + esc(rotulo) + "</span>" : "";
    }
    // §19.1: explícito = barra cheia + etiqueta invertida + título em 700; depende da tática = a versão tracejada
    function itemMelhorar(m, i) {
      var T = PF.textos, explicito = m.nivel === "explicito";
      return "<li class='ponto melhorar " + (explicito ? "explicito" : "depende") + "' data-tipo='" + esc(m.tipo) + "'>" +
        "<span class='ordem' aria-hidden='true'>" + (i + 1) + "</span><div class='topo'>" +
        "<span class='titulo'>" + esc(m.titulo) + "</span>" +
        (explicito ? "<span class='tag explicito'>" + esc(m.nivel_rotulo) + "</span>"
                   : "<span class='tag neutro'>" + esc(m.nivel_rotulo) + "</span>") +
        (m.em_validacao ? "<span class='tag neutro validacao'>" + esc(T.rotulo_em_validacao) + "</span>" : "") +
        "</div><div class='sub'>" + etiquetaDeLado(m.lado, m.lado_rotulo) + "<span>" + esc(m.contagem) + "</span></div>" +
        (m.referencia ? "<div class='ref'>" + esc(m.referencia) + "</div>" : "") +
        (m.custo ? "<div class='custo'>" + esc(m.custo) + "</div>" : "") +
        // no "depende da tática" a frase já é o motivo seguido de "vale conferir" (Python): não repete
        (explicito ? "<div class='motivo'>" + esc(m.motivo) + "</div>" : "") +
        "<div class='como'><span class='rot'>" + esc(explicito ? T.rot_como_melhorar : T.rot_conferir) + "</span><p>" +
        esc(m.frase) + "</p></div>" +
        (m.chips && m.chips.length ? "<div class='rounds'><span class='rot'>" + esc(T.rot_rounds) + "</span>" +
          chipsDeRound(m.chips) + "</div>" : "") + "</li>";
    }
    // §19.2: barra --decisivo ("afirmado e bom"), sem número de ordem; valor, bruto e referência juntos
    function itemForte(f) {
      return "<li class='ponto forte' data-chave='" + esc(f.chave) + "'><div class='topo'>" +
        "<span class='titulo'>" + esc(f.rotulo) + (f.lado_rotulo ? " " + esc(f.lado_rotulo) : "") + "</span><span class='valor'>" +
        esc(f.valor) + "</span>" + (f.bruto ? "<span class='bruto'>" + esc(f.bruto) + "</span>" : "") + "</div>" +
        "<div class='ref'>" + esc(f.referencia) + "</div></li>";
    }
    function desenhaNovo(nomeA, nomeB) {
      if (!PF) return;
      var T = PF.textos, j = pfJogador(nomeA), k = nomeB ? pfJogador(nomeB) : null;
      if (!j) return;
      var cab = "<div class='nk'>" + esc(j.name) + "</div><div class='time-do-jog'>" + esc(j.time_nome) +
        (j.comecou ? " <span class='tag comecou " + esc(j.comecou) + "'>" + esc(j.comecou_rotulo) + "</span>" : "") +
        "</div><div class='funcs'>" + j.funcoes.map(function (f) {
          return "<span class='tag" + (f.neutro ? " neutro" + (f.tendencia ? " tendencia" : "") : " decisivo") + "'" +
            (f.dica ? " title='" + esc(f.dica) + "'" : "") + ">" +
            esc(f.lado) + " · " + esc(f.texto) + "</span>";
        }).join("") + "</div><p>" + esc(j.resumo) + "</p>";
      document.getElementById("pf-cab").innerHTML = cab;

      var mel = "<h3>" + esc(T.melhorar) + "</h3>";
      if (PF.estado === "em_validacao") {
        mel += "<div class='aviso-bloco neutro' id='pf-em-validacao' role='note'><span class='ico' aria-hidden='true'>–</span><p>" +
          "<span class='tag neutro validacao'>" + esc(T.rotulo_em_validacao) + "</span> " + esc(T.em_validacao) +
          " <a href='" + esc(PF.link_como_e_conferido) + "'>" + esc(T.como_e_conferido) + "</a></p></div>";
      } else {
        if (PF.estado === "preview") mel += "<p class='pfnota'>" + esc(T.aviso_preview) + "</p>";
        mel += j.melhorar.length ? "<ol class='pflista'>" + j.melhorar.map(itemMelhorar).join("") + "</ol>"
          : "<p class='pfnota'>" + esc(j.melhorar_vazio) + "</p>";
      }
      document.getElementById("pf-melhorar").innerHTML = mel;

      document.getElementById("pf-fortes").innerHTML = "<h3>" + esc(T.fortes) + "</h3>" +
        (j.fortes.length ? "<ul class='pflista'>" + j.fortes.map(itemForte).join("") + "</ul>"
          : "<p class='pfnota'>" + esc(T.fortes_vazio) + "</p>");

      // comparar: os mesmos tipos de erro e os mesmos pontos fortes, lado a lado (sem faixa, sem radar)
      var cmp = "";
      if (k) {
        var linhas = PF.tipos.map(function (t) {
          return "<tr><td>" + esc(t.titulo) + "</td><td class='n'>" + esc(j.contagens[t.id]) + "</td><td class='n'>" +
            esc(k.contagens[t.id]) + "</td></tr>";
        });
        var chaves = [];
        j.fortes.concat(k.fortes).forEach(function (f) { if (chaves.indexOf(f.chave) < 0) chaves.push(f.chave); });
        PF.metricas.forEach(function (m) {
          if (chaves.indexOf(m.chave) < 0) return;
          var va = j.valores[m.chave] || {}, vb = k.valores[m.chave] || {};
          linhas.push("<tr><td>" + esc(m.rotulo) + "</td><td class='n'>" + esc(va.valor || "—") +
            (va.bruto ? "<small>" + esc(va.bruto) + "</small>" : "") + "</td><td class='n'>" + esc(vb.valor || "—") +
            (vb.bruto ? "<small>" + esc(vb.bruto) + "</small>" : "") + "</td></tr>");
        });
        if (linhas.length) {
          cmp = "<table><thead><tr><th>" + esc(T.col_ponto) + "</th><th>" + esc(j.name) + "</th><th>" + esc(k.name) +
            "</th></tr></thead><tbody>" + linhas.join("") + "</tbody></table>";
        }
      }
      document.getElementById("pf-cmp").innerHTML = cmp;

      document.getElementById("pf-uma-vez").innerHTML = j.uma_vez.length
        ? "<p class='pfnota'>" + esc(T.detalhes_erros) + "</p>" + j.uma_vez.map(function (u) {
            return "<div class='ponto compacto depende'><div class='topo'><span class='titulo'>" + esc(u.titulo) + "</span>" +
              "<span class='sub'>" + etiquetaDeLado(u.chips[0] && u.chips[0].lado, u.lado_rotulo) + "<span>" + esc(u.contagem) +
              "</span>" + (u.motivo ? "<span>" + esc(u.motivo) + "</span>" : "") + "</span></div>" + chipsDeRound(u.chips) + "</div>";
          }).join("") : "";
      ligaRolagemDosChips(document.querySelector('[data-panel="perfil"]'));
    }

    // textos fixos da aba nova (do Python) e os chips de round: abrem o Replay no round e no tempo
    if (PF) {
      document.getElementById("pf-eyebrow").textContent = PF.textos.eyebrow;
      document.getElementById("pf-comparar-t").textContent = PF.textos.comparar;
      document.getElementById("pf-comparar-texto").textContent = PF.textos.comparar_texto;
      document.getElementById("pf-b-rot").textContent = PF.textos.comparar;
      document.getElementById("pf-det-nome").textContent = PF.textos.detalhes;
      document.getElementById("pf-det-resumo").textContent = PF.textos.detalhes_resumo;
      // §19.4: fechado por padrão; aberto/fechado em localStorage ("1"/"0"), em try/catch (sem armazenamento: fechado)
      var detalhes = document.getElementById("pf-detalhes"), CHAVE_DETALHES = "parser-cs2:perfil-detalhes";
      try { if (localStorage.getItem(CHAVE_DETALHES) === "1") detalhes.open = true; } catch (e) { /* fechado */ }
      // grava quando o atributo `open` muda (MutationObserver: ainda na tarefa do clique), e não no evento `toggle`, que o
      // navegador dispara numa tarefa depois: quem lesse logo depois do clique podia achar o valor antigo (CI, 2026-10-28)
      new MutationObserver(function () {
        try { localStorage.setItem(CHAVE_DETALHES, detalhes.open ? "1" : "0"); } catch (e) { /* abre fechado, funciona igual */ }
      }).observe(detalhes, { attributes: true, attributeFilter: ["open"] });
      var aviso = document.getElementById("pf-aviso");
      if (PF.degradado) { aviso.textContent = PF.degradado; aviso.hidden = false; }
    }
    document.querySelector('[data-panel="perfil"]').addEventListener("click", function (e) {
      var c = e.target.closest(".pfchip");
      if (!c) return;
      var t = c.getAttribute("data-t");
      gravaVisitado(c.getAttribute("data-round") + "@" + t);
      c.setAttribute("data-visitado", "");
      var tit = c.getAttribute("title");
      if (tit.indexOf(" (" + PF.textos.ja_aberto + ")") < 0) {
        tit += " (" + PF.textos.ja_aberto + ")";
        c.setAttribute("title", tit);
        c.setAttribute("aria-label", tit);
      }
      abreNoReplay(Number(c.getAttribute("data-round")), t === "" ? null : Number(t));
    });

    document.getElementById("pf-nota").innerHTML =
      "<b>Como ler.</b> A porcentagem nunca aparece sozinha: ao lado dela está o bruto " +
      "(<i>9 de 22</i>), e na última coluna a mediana dos outros jogadores do mesmo recorte — " +
      "sem referência, “60% longe do time” não diz se é muito ou pouco. Só é destacado quem se " +
      "afasta da mediana em mais de " + Math.round(MARGEM_DESTAQUE * 100) + " pontos. " +
      "Onde o denominador é pequeno demais para sustentar uma taxa, a célula é marcada como " +
      "<i>amostra fraca</i> e o que vale é o bruto: 1 de 1 não é 100%. " +
      "O “jeito de jogar mais frequente” vem do agrupamento da aba Estilos, e a descrição dele " +
      "é <b>automática</b> — uma releitura das médias do grupo, não um nome de função.";

    // Quem joga em cada grupo. Todo o texto vem pronto do Python
    // (metrics.player_profile.cards_de_estilo); aqui só se monta o HTML.
    (function () {
      var E = D.cards_de_estilo, el = document.getElementById("pf-estilos");
      if (!el || !E || !E.grupos || !E.grupos.length) return;
      el.innerHTML = "<h3>" + esc(E.titulo) + "</h3><div class='estcards'>" +
        E.grupos.map(function (g) {
          return "<div class='estcard'><b>" + esc(nomeDoGrupoPerfil(g.cluster)) + "</b>" +
            "<span class='estsub'>" + esc(g.subtitulo) + "</span><ol>" +
            g.jogadores.map(function (j) {
              return "<li>" + esc(j.name) + (j.dominante ? "<em>" + esc(E.rotulo_dominante) + "</em>" : "") +
                "<span>" + esc(j.texto) + "</span></li>";
            }).join("") + "</ol></div>";
        }).join("") + "</div><p class='estnota'>" + esc(E.nota) + "</p>";
    })();

    preencheSelects();
    montaBotoes();
    selB.addEventListener("change", desenha);
    desenha();
  })();

  // o texto do rodapé vem pronto do build (scripts/build_web_page.rodape_html)
  document.getElementById("foot").innerHTML = PAGINA.rodape_html || "";

