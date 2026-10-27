/* Tocador do agente em listras, ESTILO GATO (rodada final, 2026-10-19). Só toca quadros prontos: os segmentos vêm de agente/agente-<lado>.js,
   gerados à mão por scripts/converte_agente.py (não roda no build) a partir da gravação do menu (conteúdo do jogo da
   Valve, sem fins comerciais). Cópia do js/agente.js do protótipo (v2-3, decisão 48), inline na landing; o build copia
   dashboard/web/agente/ para agente/ ao lado das páginas; o sha256 de cada .js está em dashboard/web/agentes.manifesto.json.
   - Formato: por quadro, por linha: n segmentos de 3 bytes (recuo, comprimento, código). Código = tom (bits 0-2: 0..3, 4 = arma fina)
     + 8 x (deslocamento vertical + 16), em 1/16 do passo. O tom é a opacidade da tinta (A.opac); a espessura é A.esp (fração do passo),
     com mínimo de 1,2 px de tela.
   - O lado (CT ou TR) é sorteado a cada visita por um script em linha logo depois do <figure> (?agente=ct|tr força); só o arquivo do lado
     sorteado é baixado. Sem JS: o quadro fixo do TR (o padrão, data-lado="tr"). Com JS: o arquivo do lado é baixado só depois do load.
   - Reduzir movimento: o sorteio continua, só o quadro 0. Começa depois do load e quando o navegador está ocioso; pausa fora da tela e com a aba escondida;
     caixa fixa (CLS 0). */
(function () {
  'use strict';
  var f = document.getElementById('agente');
  if (!f) return;
  var lado = f.dataset.lado || 'tr';
  var reduz = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  var cv = f.querySelector('canvas'), ctx = cv.getContext('2d');
  var med = window.__agenteMed = { quadros: 0, ms: 0, lado: lado, bytes: 0 };

  function decodifica(A) {
    var bin = atob(A.d), b = new Uint8Array(bin.length), i;
    for (i = 0; i < bin.length; i++) b[i] = bin.charCodeAt(i);
    med.bytes = b.length;
    var quadros = [], p = 0;
    for (var q = 0; q < A.quadros; q++) {
      var por = [[], [], [], [], []];                           // por tom: linha, x, comprimento, deslocamento
      for (var r = 0; r < A.linhas; r++) {
        var n = b[p++], fim = 0;
        for (var k = 0; k < n; k++) {
          var x = fim + b[p++], len = b[p++], cod = b[p++];
          por[cod & 7].push(r, x, len, (cod >> 3) - 16); fim = x + len;
        }
      }
      quadros.push(por);
    }
    return quadros;
  }

  function prepara(A) {
    var quadros = decodifica(A);
    var dpr = Math.min(window.devicePixelRatio || 1, 2);
    var w = f.clientWidth, h = f.clientHeight;
    cv.width = Math.round(w * dpr); cv.height = Math.round(h * dpr);
    var sx = cv.width / A.l, passo = cv.height / A.linhas, minimo = 1.2 * dpr;
    var cor = getComputedStyle(f).color;
    function desenha(i) {
      var t0 = performance.now(), por = quadros[i];
      ctx.clearRect(0, 0, cv.width, cv.height); ctx.fillStyle = cor;
      for (var t = 0; t < 5; t++) {
        var s = por[t]; if (!s.length) continue;
        var esp = Math.max(A.esp[t] * passo, minimo);
        ctx.globalAlpha = A.opac[Math.min(t, 3)];
        for (var k = 0; k < s.length; k += 4)
          ctx.fillRect(s[k + 1] * sx, (s[k] + 0.5 + s[k + 3] / 16) * passo - esp / 2, s[k + 2] * sx, esp);
      }
      ctx.globalAlpha = 1;
      med.quadros++; med.ms += performance.now() - t0;
    }
    desenha(0); f.classList.add('pronto');
    if (reduz) return;
    // ordem de toque: direta (0..n-1, fecha com a transição cruzada já gravada) ou vai-e-volta suave (0..n-1..1)
    var ordem = [], i;
    for (i = 0; i < quadros.length; i++) ordem.push(i);
    if (A.ordem === 'vai-e-volta') for (i = quadros.length - 2; i > 0; i--) ordem.push(i);
    var pos = 0, ultimo = 0, raf = 0, visivel = true, aba = !document.hidden, passoMs = 1000 / A.fps;
    function laco(agora) {
      raf = 0;
      if (!visivel || !aba) return;
      if (agora - ultimo >= passoMs - 1) { ultimo = agora; pos = (pos + 1) % ordem.length; desenha(ordem[pos]); }
      raf = requestAnimationFrame(laco);
    }
    function liga() { if (!raf && visivel && aba) raf = requestAnimationFrame(laco); }
    if ('IntersectionObserver' in window) new IntersectionObserver(function (e) { visivel = e[0].isIntersecting; liga(); }).observe(f);
    document.addEventListener('visibilitychange', function () { aba = !document.hidden; liga(); });
    liga();
  }

  var CHAVE = { tr: 'TR', ct: 'CT-A' };                     // nome do agente dentro do arquivo
  function baixa() {
    var s = document.createElement('script');
    s.src = f.dataset.base + 'agente-' + lado + '.js';
    s.onload = function () { if (window.AGENTES && window.AGENTES[CHAVE[lado]]) prepara(window.AGENTES[CHAVE[lado]]); };
    document.body.appendChild(s);
  }
  function depoisDoLoad() { (window.requestIdleCallback || function (fn) { setTimeout(fn, 200); })(baixa, { timeout: 1500 }); }
  if (document.readyState === 'complete') depoisDoLoad(); else window.addEventListener('load', depoisDoLoad);
})();
