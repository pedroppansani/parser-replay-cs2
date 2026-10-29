  /* ================= ABAS ================= */

  var tabs = document.querySelectorAll(".tabs [role=tab]");
  // O hash da URL abre a aba direto (`#replay`); os nomes do hash são os da tela, os de dentro são os data-tab.
  var HASH_DA_ABA = { resumo: "insights", replay: "replay", jogadores: "jogadores", placar: "rounds", perfil: "perfil", estilos: "estilos" };
  var ABA_NO_HASH = {};
  Object.keys(HASH_DA_ABA).forEach(function (k) { ABA_NO_HASH[HASH_DA_ABA[k]] = k; });

  // Nomeada (e não só um listener) porque o gráfico de vantagem também troca de
  // aba: clicar num round leva pro replay daquele round.
  function selectTab(name, semHash) {
    var jaEstava = document.querySelector(".tabs [role=tab][aria-selected=true]");
    jaEstava = jaEstava && jaEstava.dataset.tab === name;
    Array.prototype.forEach.call(tabs, function (o) {
      o.setAttribute("aria-selected", String(o.dataset.tab === name));
      // tabindex itinerante: Tab entra na aba ativa, as setas andam entre elas
      o.tabIndex = o.dataset.tab === name ? 0 : -1;
    });
    Array.prototype.forEach.call(document.querySelectorAll("[data-panel]"), function (p) {
      p.hidden = p.dataset.panel !== name;
    });
    if (!semHash && !jaEstava) {   // §19.3: só quando a aba muda de fato; `#replay?round=&t=` não é apagado
      try { history.replaceState(null, "", "#" + ABA_NO_HASH[name]); } catch (e) { /* arquivo local: sem hash */ }
    }
    if (name === "replay") draw();
  }

  Array.prototype.forEach.call(tabs, function (b, i) {
    b.addEventListener("click", function () { selectTab(b.dataset.tab); });
    // Setas, Home e End entre as abas (padrão de tablist da WAI-ARIA; auditoria 5.4)
    b.addEventListener("keydown", function (e) {
      var n = tabs.length, j = null;
      if (e.key === "ArrowRight") j = (i + 1) % n;
      else if (e.key === "ArrowLeft") j = (i - 1 + n) % n;
      else if (e.key === "Home") j = 0;
      else if (e.key === "End") j = n - 1;
      if (j === null) return;
      e.preventDefault();
      selectTab(tabs[j].dataset.tab);
      tabs[j].focus();
    });
  });

  // Sombra e "›" quando sobra aba fora da tela (375 px): o botão rola a lista até a próxima aba escondida.
  (function () {
    var moldura = document.getElementById("abas-moldura"), lista = document.querySelector(".tabs");
    function atualiza() {
      var max = lista.scrollWidth - lista.clientWidth;
      moldura.classList.toggle("sobra-dir", lista.scrollLeft < max - 2);
      moldura.classList.toggle("sobra-esq", lista.scrollLeft > 2);
    }
    document.getElementById("abas-mais").addEventListener("click", function () {
      lista.scrollBy({ left: Math.max(lista.clientWidth * 0.6, 120), behavior: reduced ? "auto" : "smooth" });
    });
    lista.addEventListener("scroll", atualiza, { passive: true });
    window.addEventListener("resize", atualiza);
    atualiza();
  })();

  // Estado inicial: a aba do hash, ou o Resumo. Sem redesenhar nada (o replay desenha ao ser aberto).
  // `#replay?round=12&t=34.5` abre o replay naquele round e tempo (fase 12); `#replay` sozinho, como antes.
  var hashInicial = (location.hash || "").replace("#", "").split("?");
  var inicial = HASH_DA_ABA[hashInicial[0]] || "insights";
  selectTab(inicial, true);
  if (inicial === "replay" && hashInicial[1]) {
    var q = {};
    hashInicial[1].split("&").forEach(function (par) { var kv = par.split("="); q[kv[0]] = decodeURIComponent(kv[1] || ""); });
    if (q.round) abreNoReplay(Number(q.round), q.t === undefined || q.t === "" ? null : Number(q.t), true);
  }
