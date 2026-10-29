/* O tema da página (Fase T): claro ou escuro, o que quem lê escolheu na landing; na primeira visita, o do aparelho
   (prefers-color-scheme). Carregado no <head> antes de qualquer pintura, como arquivo (nada de script inline, a CSP
   não muda). Sem armazenamento (navegação privada, bloqueio), vale o do aparelho. A prancheta é sempre violeta e
   não é tocada. O botão da landing e a troca na hora ficam no v2.js. */
(function () {
  var raiz = document.documentElement;
  if (raiz.getAttribute("data-tema") === "violeta") return;
  var tema = null;
  try { tema = localStorage.getItem("goatdemo:tema"); } catch (e) { tema = null; }
  if (tema !== "claro" && tema !== "escuro") {
    tema = window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches ? "escuro" : "claro";
  }
  raiz.setAttribute("data-tema", tema);
})();
