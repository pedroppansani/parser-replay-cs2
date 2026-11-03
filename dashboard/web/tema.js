/* O tema da página (Fase T): claro ou escuro, o que quem lê escolheu na landing; na primeira visita, o do aparelho
   (prefers-color-scheme). Carregado no <head> antes de qualquer pintura, como arquivo (nada de script inline, a CSP
   não muda). Sem armazenamento (navegação privada, bloqueio), vale o do aparelho. A prancheta é sempre violeta e
   não é tocada. O botão da landing e a troca na hora ficam no v2.js. */
(function () {
  var raiz = document.documentElement;
  if (raiz.getAttribute("data-tema") === "violeta") return;
  function escolhido() {
    var tema = null;
    try { tema = localStorage.getItem("goatdemo:tema"); } catch (e) { tema = null; }
    if (tema !== "claro" && tema !== "escuro") {
      tema = window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches ? "escuro" : "claro";
    }
    return tema;
  }
  raiz.setAttribute("data-tema", escolhido());
  // a página que volta da memória do navegador (voltar e avançar) depois de a escolha mudar em outra página recarrega:
  // os gráficos leram as cores uma vez só
  window.addEventListener("pageshow", function (e) {
    if (e.persisted && escolhido() !== raiz.getAttribute("data-tema")) location.reload();
  });
})();
