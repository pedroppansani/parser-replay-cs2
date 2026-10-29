  /* ================= JOGADORES ================= */

  (function players() {
    var wrap = document.getElementById("players");

    var ch = {}; D.crosshair.forEach(function (c) { ch[c.name] = c; });
    // kills/assists/mortes vêm do perfil: é lá que eles são contados, e contar
    // de novo aqui criaria duas fontes para o mesmo número.
    var kad = {}; (D.player_profile || []).forEach(function (r) { kad[r.name] = r; });
    var maxD = 0;
    Object.keys(D.damage_by_player).forEach(function (k) {
      D.damage_by_player[k].forEach(function (v) { if (v > maxD) maxD = v; });
    });
    // Rating calculado por caminho de reserva (sem modelo global, sem a tabela
    // de economia) não é mostrado: a página diz por quê, com o texto do Python.
    var ratingDegradado = (D.rating_info || {}).texto_degradado || "";
    var temRating = !ratingDegradado && D.players.some(function (p) { return p.rating != null; });

    // Colunas ordenáveis. A chave diz de onde sai o número de cada jogador.
    var ORDENS = {
      rating: function (p) { return p.rating != null ? p.rating : -1; },
      k: function (p) { return (kad[p.name] || {}).kills_totais || 0; },
      adr: function (p) { return p.adr || 0; },
      kast: function (p) { return p.kast_pct || 0; }
    };
    var ordem = temRating ? "rating" : "adr";

    function rotulo(chave, texto, titulo) {
      return "<th scope='col'><button type='button' data-ordem='" + esc(chave) + "' title='" + esc(titulo) + "'" +
        (ordem === chave ? " class='on' aria-sort='descending'" : "") + ">" + texto + "</button></th>";
    }

    function desenha() {
      wrap.innerHTML = "";
      var tab = document.createElement("table");
      // Rating primeiro (cabe em 375), depois ADR, KAST, K, A, M; o dano round a round e a mira vêm no fim
      var cab = "<thead><tr><th scope='col' class='fixa'>Jogador</th>" +
        (temRating ? rotulo("rating", "Rating*", (D.rating_info || {}).texto || "") : "<th scope='col'></th>") +
        rotulo("adr", "ADR", "Ordenar por ADR") + rotulo("kast", "KAST", "Ordenar por KAST") +
        rotulo("k", "K", "Ordenar por kills") + "<th scope='col'>A</th><th scope='col'>M</th>" +
        "<th scope='col'>Dano round a round</th><th scope='col' title='" + esc(D.dica_mira || "") + "'>Mira</th></tr></thead>";
      var corpo = "";
      D.players.slice().sort(function (a, b) { return ORDENS[ordem](b) - ORDENS[ordem](a); }).forEach(function (p) {
        var dmg = D.damage_by_player[p.name] || [], kast = D.kast_by_player[p.name] || [];
        var w = 240, hh = 28, bw = w / dmg.length, sp = "<svg viewBox='0 0 " + w + " " + hh + "' preserveAspectRatio='none' aria-hidden='true'>";
        dmg.forEach(function (v, i) {
          var bh = Math.max(1.5, (v / maxD) * (hh - 4));
          sp += "<rect x='" + (i * bw + 0.7) + "' y='" + (hh - bh) + "' width='" + (bw - 1.4) +
            "' height='" + bh + "' fill='" + (kast[i] === 1 ? C.ct : C.borda) + "' rx='1'></rect>";
        });
        sp += "</svg>";
        var kd = kad[p.name] || {};
        // Amostra fraca (poucos rounds) aparece apagada e com o motivo no title:
        // o número existe, mas não sustenta comparação.
        var rt = (p.rating == null || ratingDegradado) ? "<td class='n q'>—</td>" :
          "<td class='n rt" + (p.rating_amostra_fraca ? " fraca" : "") + "'" +
          (p.rating_amostra_fraca ? " title='amostra pequena: poucos rounds jogados'" : "") + ">" +
          p.rating.toFixed(2).replace(".", ",") + "</td>";
        corpo += "<tr><th scope='row' class='fixa'><span class='nk'>" + esc(p.name) + "</span>" +
          "<span class='time-do-jog'>" + esc(nomeLado(p.team)) + " " + etiquetaComecou(p.team) + "</span></th>" + rt +
          "<td class='n'>" + br(p.adr) + "</td><td class='n q'>" + fmt(p.kast_pct, 0) + "%</td>" +
          "<td class='n'>" + (kd.kills_totais != null ? kd.kills_totais : "—") + "</td>" +
          "<td class='n q'>" + (kd.assistencias != null ? kd.assistencias : "—") + "</td>" +
          "<td class='n q'>" + (kd.mortes != null ? kd.mortes : "—") + "</td>" +
          "<td class='sp'>" + sp + "</td>" +
          "<td class='n q'>" + fmt((ch[p.name] || {}).crosshair_score, 0) + "</td></tr>";
      });
      tab.innerHTML = cab + "<tbody>" + corpo + "</tbody>";
      wrap.appendChild(tab);
      Array.prototype.forEach.call(tab.querySelectorAll("thead button"), function (b) {
        b.addEventListener("click", function () { ordem = b.dataset.ordem; desenha(); wrap.querySelector("[data-ordem='" + ordem + "']").focus(); });
      });

      // Legenda da tabela: o rating (rótulo do Python: implementação própria, não o oficial) e a mira
      var leg = document.createElement("div");
      leg.className = "legenda-tabela";
      wrap.appendChild(leg);
      if (temRating && D.rating_info && D.rating_info.texto) {
        var nota = document.createElement("p");
        nota.className = "rnota";
        nota.textContent = "* " + D.rating_info.texto;
        leg.appendChild(nota);
      }
      if (D.dica_mira) {
        var mira = document.createElement("p");
        mira.className = "rnota";
        mira.id = "legenda-mira";
        mira.textContent = "Mira: " + D.dica_mira;
        leg.appendChild(mira);
      }
      if (ratingDegradado) {
        var aviso = document.createElement("p");
        aviso.className = "rnota";
        aviso.id = "rating-degradado";
        aviso.textContent = ratingDegradado;
        leg.appendChild(aviso);
      }
    }
    desenha();
  })();

