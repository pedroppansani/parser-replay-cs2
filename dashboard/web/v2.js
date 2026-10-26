/* GOAT.demo (decisão 48): comportamento comum da v2, inline na página (v2-3: a landing). Adaptado do base.js do
   protótipo: só a navbar (C2) e o diálogo "Adicionar demo" (§5.7). Nenhum texto aqui: os textos vêm do Python. */
(function () {
  'use strict';
  var html = document.documentElement;
  var nav = document.querySelector('.site-topo');

  /* C2: a altura real da navbar (com a folga do topo) vira --nav-h; scroll-padding-top = --nav-h + 16 px */
  function medeNav() {
    if (!nav) return;
    var topo = parseFloat(getComputedStyle(nav).top) || 0;
    html.style.setProperty('--nav-h', Math.ceil(nav.getBoundingClientRect().height + topo) + 'px');
  }
  medeNav();
  if (window.ResizeObserver && nav) new ResizeObserver(medeNav).observe(nav);
  /* C2: o foco por Tab nunca fica embaixo da navbar (o scroll-padding cobre âncoras; isto cobre o foco em qualquer rolagem) */
  document.addEventListener('focusin', function (e) {
    if (!nav || !e.target.getBoundingClientRect || nav.contains(e.target)) return;
    var r = e.target.getBoundingClientRect(), n = nav.getBoundingClientRect();
    if (n.bottom > 0 && r.top < n.bottom + 8 && r.bottom > 0) window.scrollBy({ top: r.top - n.bottom - 16, behavior: 'instant' });
  });

  /* "Adicionar demo" (§5.7): <dialog> com foco no "Fechar"; Esc e clique fora fecham; o foco volta ao botão */
  var dlg = document.getElementById('dlg-demo'), gatilho = null;
  if (dlg && dlg.showModal) {
    document.querySelectorAll('[data-abre-demo]').forEach(function (b) {
      b.addEventListener('click', function () { gatilho = b; dlg.showModal(); dlg.querySelector('.fechar').focus(); });
    });
    dlg.querySelectorAll('.fechar, [data-fecha]').forEach(function (b) {
      b.addEventListener('click', function () { dlg.close(); });
    });
    dlg.addEventListener('close', function () { if (gatilho) gatilho.focus(); });
    dlg.addEventListener('click', function (e) { if (e.target === dlg) dlg.close(); });
  }
})();
