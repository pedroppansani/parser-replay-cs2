  /* ================= ESTILOS: FUNÇÃO POR JOGADOR ================= */

  /* ================= IMPACTO ALÉM DO PLACAR (fase 7) ================= */
  // Grupos recolhíveis com as métricas de metrics/impacto.py, lidas do perfil da
  // partida (D.player_profile): valor, bruto ("n de d") e a seta contra a régua
  // anônima do corpus. Amostra fraca fica esmaecida e sem seta.
  (function impacto() {
    var host = document.getElementById("impacto");
    var cfg = D.impacto;
    if (!host || !cfg || !(D.player_profile || []).length) return;
    var time = {}; (D.players || []).forEach(function (p) { time[p.name] = p.team; });
    var linhas = D.player_profile.slice().sort(function (a, b) {
      return (time[a.name] || "").localeCompare(time[b.name] || "") || a.name.localeCompare(b.name);
    });
    function num(v, formato) {
      if (v == null) return "—";
      if (formato === "pct") return Math.round(v * 100) + "%";
      return v.toFixed(formato === "num2" ? 2 : 1).replace(".", ",");
    }
    var h = document.createElement("h3");
    h.className = "sec"; h.textContent = cfg.titulo;
    var t = document.createElement("p"); t.textContent = cfg.texto;
    host.appendChild(h); host.appendChild(t);
    // Aberto/fechado lembrado por quem vê (uma chave para a página toda); leitura e escrita dentro de try/catch:
    // arquivo local, modo privado ou armazenamento bloqueado abrem tudo fechado e a página funciona igual.
    var CHAVE_GRUPOS = "parser-cs2:grupos-jogadores";
    var abertos = {};
    try {
      var lido = JSON.parse(window.localStorage.getItem(CHAVE_GRUPOS) || "{}");
      if (lido && typeof lido === "object") abertos = lido;
    } catch (e) { abertos = {}; }
    function lembra() {
      try { window.localStorage.setItem(CHAVE_GRUPOS, JSON.stringify(abertos)); } catch (e) { /* sem memória: segue */ }
    }
    var resumos = PAGINA.resumo_dos_grupos || {};
    cfg.grupos.forEach(function (g) {
      var det = document.createElement("details");
      det.className = "card imp-grupo";
      det.dataset.grupo = g.nome;
      if (abertos[g.nome] === true || (abertos[g.nome] === undefined && g.aberto)) det.open = true;
      det.addEventListener("toggle", function () { abertos[g.nome] = det.open; lembra(); });
      var cab = "<tr><th></th>" + g.metricas.map(function (m) { return "<th>" + esc(m.rotulo) + "</th>"; }).join("") + "</tr>";
      var corpo = linhas.map(function (r) {
        return "<tr><td>" + esc(r.name) + " <small>" + esc(nomeLado(time[r.name])) + "</small></td>" +
          g.metricas.map(function (m) {
            var v = r[m.chave], ref = r[m.chave + "_ref"], fraco = r[m.chave + "_fraco"];
            var n = m.bruto_so_denominador ? null : r[m.chave + "_n"], d = r[m.chave + "_d"];
            var seta = "";
            if (v != null && ref != null && !fraco && v !== ref) {
              var acima = v > ref, bom = m.pior_quanto_maior ? !acima : acima;
              seta = "<span class='seta " + (bom ? "bom" : "ruim") + "' title='régua do corpus: " +
                esc(num(ref, m.formato)) + "'>" + (acima ? "▲" : "▼") + "</span>";
            }
            var bruto = d == null ? "" : (n != null ? String(Math.round(n * 10) / 10).replace(".", ",") + " de " : "") + d + " " + m.unidade_do_bruto;
            return "<td class='" + (fraco ? "fraco" : "") + "'>" + esc(num(v, m.formato)) + seta +
              "<small>" + esc(bruto) + "</small></td>";
          }).join("") + "</tr>";
      }).join("");
      det.innerHTML = "<summary><span class='g-nome'>" + esc(g.nome) + "</span>" +
        (resumos[g.nome] ? "<span class='g-resumo'>· " + esc(resumos[g.nome]) + "</span>" : "") +
        "</summary><table>" + cab + corpo + "</table>";
      host.appendChild(det);
    });
  })();

  /* ================= COMPARAR DOIS (fase 7, 7.3) ================= */
  // Dois jogadores DESTA partida lado a lado, nas taxas do perfil e nas métricas
  // de impacto, com o bruto e a régua anônima do corpus de cada número. A
  // seleção é estado da tela (não vai para o endereço). Sem faixa desenhada.
  (function comparar() {
    var host = document.getElementById("comparar");
    var cfg = (D.impacto || {}).comparar;
    var linhas = D.player_profile || [];
    if (!host || !cfg || linhas.length < 2) return;
    var time = {}; (D.players || []).forEach(function (p) { time[p.name] = p.team; });
    var ordem = linhas.slice().sort(function (a, b) {
      return (time[a.name] || "").localeCompare(time[b.name] || "") || a.name.localeCompare(b.name);
    });
    var grupos = (D.perfil_categorias || []).map(function (g) {
      return { nome: g.nome, metricas: g.taxas.map(function (t) { return { chave: t[0], rotulo: t[1], formato: "pct", unidade: "" }; }) };
    }).concat(((D.impacto || {}).grupos || []).map(function (g) {
      return { nome: g.nome, metricas: g.metricas.map(function (m) {
        return { chave: m.chave, rotulo: m.rotulo, formato: m.formato, unidade: m.unidade_do_bruto,
                 so_denominador: m.bruto_so_denominador }; }) };
    }));
    function num(v, formato) {
      if (v === null || v === undefined) return "—";
      if (formato === "pct") return Math.round(v * 100) + "%";
      return v.toFixed(formato === "num2" ? 2 : 1).replace(".", ",");
    }
    var h = document.createElement("h3"); h.className = "sec"; h.textContent = cfg.titulo;
    var t = document.createElement("p"); t.textContent = cfg.texto;
    var escolha = document.createElement("div"); escolha.className = "cmp-escolha";
    function seletor(id, rotulo, inicial) {
      var l = document.createElement("label");
      l.appendChild(document.createTextNode(rotulo + " "));
      var s = document.createElement("select"); s.id = id;
      ordem.forEach(function (r) {
        var o = document.createElement("option"); o.value = r.name;
        o.textContent = r.name + " (" + nomeLado(time[r.name]) + ")";
        s.appendChild(o);
      });
      s.value = inicial;
      s.addEventListener("change", desenha);
      l.appendChild(s); escolha.appendChild(l);
      return s;
    }
    // o padrão: o primeiro de cada time (a comparação mais comum é entre times)
    var outroTime = ordem.filter(function (r) { return time[r.name] !== time[ordem[0].name]; })[0] || ordem[1];
    var sa = seletor("cmp-a", cfg.rotulo_a, ordem[0].name);
    var sb = seletor("cmp-b", cfg.rotulo_b, outroTime.name);
    var tab = document.createElement("div"); tab.className = "card cmp-tabela"; tab.id = "cmp-tabela";
    host.appendChild(h); host.appendChild(t); host.appendChild(escolha); host.appendChild(tab);
    function celula(r, m) {
      var v = r[m.chave], ref = r[m.chave + "_ref"], fraco = r[m.chave + "_fraco"];
      var n = m.so_denominador ? null : r[m.chave + "_n"], d = r[m.chave + "_d"];
      var bruto = d === null || d === undefined ? "" :
        (n === null || n === undefined ? "" : String(Math.round(n * 10) / 10).replace(".", ",") + " de ") +
        String(Math.round(d * 10) / 10).replace(".", ",") + (m.unidade ? " " + m.unidade : "");
      var regua = ref === null || ref === undefined ? "" : cfg.rotulo_regua + " " + num(ref, m.formato);
      return "<td class='" + (fraco ? "fraco" : "") + "' data-chave='" + esc(m.chave) + "'>" + esc(num(v, m.formato)) +
        "<small>" + esc(bruto) + "</small><small>" + esc(regua) + (fraco ? " · " + esc(cfg.amostra_fraca) : "") +
        "</small></td>";
    }
    function desenha() {
      var a = linhas.filter(function (r) { return r.name === sa.value; })[0];
      var b = linhas.filter(function (r) { return r.name === sb.value; })[0];
      if (!a || !b) return;
      var html = "<table><tr><th></th><th>" + esc(a.name) + "</th><th>" + esc(b.name) + "</th></tr>";
      // o rating lado a lado, com a frase do erro típico (sem faixa); escondido quando o rating é degradado
      var ra = (D.players || []).filter(function (p) { return p.name === a.name; })[0] || {};
      var rb = (D.players || []).filter(function (p) { return p.name === b.name; })[0] || {};
      if (!mvpDegradado && (ra.rating != null || rb.rating != null)) {
        var r2 = function (v) { return v == null ? "—" : v.toFixed(2).replace(".", ","); };
        html += "<tr class='grupo'><td colspan='3'>Rating</td></tr><tr><td>Rating*" +
          (PAGINA.erro_rating ? "<small>erro típico contra o rating oficial: " + esc(PAGINA.erro_rating) + "</small>" : "") +
          "</td><td data-chave='rating'>" + r2(ra.rating) + "</td><td data-chave='rating'>" + r2(rb.rating) + "</td></tr>";
      }
      grupos.forEach(function (g) {
        var ms = g.metricas.filter(function (m) { return a[m.chave + "_d"] !== undefined || b[m.chave + "_d"] !== undefined; });
        if (!ms.length) return;
        html += "<tr class='grupo'><td colspan='3'>" + esc(g.nome) + "</td></tr>";
        ms.forEach(function (m) { html += "<tr><td>" + esc(m.rotulo) + "</td>" + celula(a, m) + celula(b, m) + "</tr>"; });
      });
      tab.innerHTML = html + "</table>";
    }
    desenha();
  })();

  (function roles() {
    var host = document.getElementById("roles");
    if (!host || !D.roles) return;

    // Características qualificadas por jogador, indexadas pra montar os chips.
    var byPlayer = {};
    (D.traits || []).forEach(function (t) { (byPlayer[t.name] = byPlayer[t.name] || []).push(t); });

    ["A", "B"].forEach(function (team) {
      var mine = D.roles.filter(function (p) { return p.team === team; });
      if (!mine.length) return;

      var col = document.createElement("div");
      col.className = "roster";
      var named = mine.filter(function (p) { return p.role; }).length;
      col.innerHTML = "<h3><b>" + esc(nomeLado(team)) + "</b> " + named + " de " + mine.length +
        " com função dominante</h3>";

      mine.sort(function (a, b) { return b.adr - a.adr; }).forEach(function (p) {
        var card = document.createElement("div");
        card.className = "card pc";

        var roleCls = p.role ? (p.role_is_manual ? "role manual" : "role") : "role none";
        var roleTxt = p.role || "sem função dominante";

        var chips = (byPlayer[p.name] || [])
          // a ordem da tela vem do Python (player_roles.ordem_na_tela); sem ela, a prioridade
          .sort(function (a, b) { return a.ordem != null ? a.ordem - b.ordem : a.priority - b.priority; })
          .slice(1)  // a primeira já é o título do cartão
          .map(function (t) { return "<span class='chip'>" + esc(t.evidence) + "</span>"; })
          .join("");

        var ev = p.role_evidence
          ? "<div class='pc-ev'>" + esc(p.role_evidence) + "</div>"
          : "<div class='pc-ev'>Não lidera o time em nenhuma das métricas de função acima do piso — " +
            "joga distribuído.</div>";

        card.innerHTML =
          "<div class='top'><div class='who'>" + esc(p.name) + "</div>" +
          "<div class='" + roleCls + "'>" + esc(roleTxt) + "</div></div>" +
          ev +
          (chips ? "<div class='chips'>" + chips + "</div>" : "") +
          "<div class='nums'>" +
          "<div>" + br(p.adr) + "<span>ADR</span></div>" +
          "<div>" + fmt(p.kast_pct, 0) + "%<span>KAST</span></div>" +
          "<div>" + br(p.median_first_contact_s) + "s<span>1º contato</span></div>" +
          "<div>" + fmt(p.enemy_blind_seconds, 0) + "s<span>cegou</span></div>" +
          "<div>" + fmt(p.avg_distance_from_team, 0) + "u<span>dist. time</span></div>" +
          "<div>" + Math.round(p.trade_share * 100) + "%<span>trade</span></div>" +
          "</div>";

        col.appendChild(card);
      });

      host.appendChild(col);
    });

    document.getElementById("rolenote").innerHTML =
      "<b>Como ler.</b> O rótulo exige duas coisas: liderar o próprio time naquela métrica e passar " +
      "de um piso absoluto — sem o piso, o jogador que menos evita a AWP num time que não usa AWP " +
      "viraria “AWPer”. Os pisos vieram da distribuição real desta partida e são ponto de " +
      "calibração, não constante universal. <b>IGL não aparece aqui de propósito</b>: quem chama o " +
      "time não deixa rastro no demo, e deduzir isso seria chute com cara de métrica.";
  })();

