/* GOAT.demo (decisão 48): comportamento comum da v2, inline na página (a landing; na v2-4 a partida e jogadores; na v2-5 a prancheta).
   Adaptado do base.js do protótipo: a navbar (C2), as abas com gooey (§7) e o diálogo "Adicionar demo" (§5.7). Nenhum texto aqui: os textos vêm do Python. */
(function () {
  'use strict';
  var html = document.documentElement;
  var nav = document.querySelector('.site-topo');

  /* Tema (Fase T): o botão da landing troca claro e escuro na hora e guarda a escolha (o tema.js a aplica antes da
     primeira pintura em toda página). Sem armazenamento, a troca vale só nesta página. */
  var botaoTema = document.querySelector('.tema-botao');
  if (botaoTema) {
    var marcaTema = function () { botaoTema.setAttribute('aria-pressed', html.getAttribute('data-tema') === 'escuro' ? 'true' : 'false'); };
    marcaTema();
    botaoTema.addEventListener('click', function () {
      var novo = html.getAttribute('data-tema') === 'escuro' ? 'claro' : 'escuro';
      html.setAttribute('data-tema', novo);
      try { localStorage.setItem('goatdemo:tema', novo); } catch (e) { /* sem armazenamento: só nesta página */ }
      marcaTema();
    });
  }


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

  /* Abas com gooey (§7, C1): a bolha (.goo .bolha) segue a aba com aria-selected; o filtro SVG (#goo) só existe
     enquanto ela anda (.movendo, 220 ms) e em repouso a pílula é nítida. A troca de aba continua sendo do JS da
     página: aqui só se observa o aria-selected. Com reduzir movimento, troca seca e nada de filtro. */
  var reduz = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  document.querySelectorAll('[role=tablist]').forEach(function (lista) {
    var goo = lista.querySelector('.goo'), bolha = goo && goo.querySelector('.bolha');
    if (!bolha) return;
    var t = null;
    function posiciona(anima) {
      var sel = lista.querySelector('[role=tab][aria-selected=true]');
      if (!sel || !sel.offsetWidth) return;
      goo.style.width = lista.scrollWidth + 'px';
      if (anima && !reduz) {
        lista.classList.add('movendo');
        clearTimeout(t);
        t = setTimeout(function () { lista.classList.remove('movendo'); }, 220);
      }
      bolha.style.width = sel.offsetWidth + 'px';
      bolha.style.transform = 'translateX(' + sel.offsetLeft + 'px)';
    }
    // a aba já escolhida quando o v2.js roda (a prancheta monta as abas antes): a primeira troca também anda
    var antes = lista.querySelector('[role=tab][aria-selected=true]');
    new MutationObserver(function () {
      var sel = lista.querySelector('[role=tab][aria-selected=true]');
      if (sel !== antes) { posiciona(antes !== null); antes = sel; }
    }).observe(lista, { subtree: true, attributes: true, attributeFilter: ['aria-selected'] });
    posiciona(false);
    window.addEventListener('resize', function () { posiciona(false); });
    if (document.fonts && document.fonts.ready) document.fonts.ready.then(function () { posiciona(false); });
  });

  /* Carregando (v2-6, dúvida 5 B): o esqueleto do Replay (#carregando, posto pelo build na partida) some quando a página
     termina de carregar (os scripts montaram o Replay e o radar decodificou); sem porcentagem. `?estado=carregando`
     o deixa na tela (teste e captura). */
  var esqueleto = document.getElementById('carregando');
  if (esqueleto && !/[?&]estado=carregando(&|$)/.test(location.search)) {
    var some = function () { requestAnimationFrame(function () { esqueleto.hidden = true; }); };
    if (document.readyState === 'complete') some(); else window.addEventListener('load', some);
  }

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
