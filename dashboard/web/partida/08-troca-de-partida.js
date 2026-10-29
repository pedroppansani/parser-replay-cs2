  /* ================= TROCA DE PARTIDA ================= */

  // Só aparece no site multi-partida. O build de arquivo único não injeta
  // __SITE__, e aí a barra fica escondida — a página continua sendo um HTML
  // solto que funciona sem servidor nenhum, que é o ponto dela.
  (function demobar() {
    var SITE = window.__SITE__;
    if (!SITE || !SITE.matches || !SITE.matches.length) return;

    var bar = document.getElementById("demobar");
    var sel = document.getElementById("demosel");
    bar.hidden = false;

    SITE.matches.forEach(function (m) {
      var o = document.createElement("option");
      o.value = m.file;
      o.textContent = m.label;
      if (m.id === SITE.current) o.selected = true;
      sel.appendChild(o);
    });

    sel.addEventListener("change", function () {
      if (sel.value) window.location.href = sel.value;
    });

    // Link para a visão agregada do corpus, separada da partida (decisão 30): o
    // aviso de que lá os números somam todas as partidas vai no título do link.
    if (SITE.jogadores) {
      var lj = document.getElementById("link-jogadores");
      lj.textContent = SITE.jogadores.texto;
      lj.title = SITE.jogadores.aviso;
      lj.hidden = false;
    }

    var btn = document.getElementById("addbtn");
    var box = document.getElementById("howto");
    box.innerHTML =
      "<b>Como adicionar uma demo nova.</b> O parsing não roda no navegador: um .dem tem 200-300MB " +
      "e o parser é nativo (Rust, via awpy). Então a demo é processada localmente e o que vai pro " +
      "site é só o resultado — alguns KB de métricas por partida." +
      "<pre>git clone " + (SITE.repo ? esc(SITE.repo) : "&lt;este repositório&gt;") + "\n" +
      "pip install -r requirements.txt\n\n" +
      "# jogue o .dem em demos/ e rode:\n" +
      "python -m scripts.process_all_demos\n" +
      "python -m scripts.build_site</pre>" +
      "<p class='why'>A partida nova entra sozinha neste seletor. É a mesma razão de o site ser " +
      "estático: processar .dem a cada acesso derrubaria qualquer hospedagem gratuita.</p>";

    btn.addEventListener("click", function () {
      var open = box.hidden;
      box.hidden = !open;
      btn.setAttribute("aria-expanded", String(open));
    });
  })();

