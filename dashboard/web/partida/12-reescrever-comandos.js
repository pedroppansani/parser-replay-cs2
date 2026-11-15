  /* ================= REESCREVER · COMANDOS (CR2): o ponto de entrada (P2b) ================= */
  // A seção "Comandos" do painel do Reescrever mora em `comandos/casca.js` (a seção, o CSS dela e o carregador do leitor, do plano e da tela do cartão): a página da partida só traz
  // este ponto de entrada e pede o arquivo quando alguém ENTRA no Reescrever. Até ele chegar a seção ocupa o seu lugar no painel (um invólucro sem caixa); se não vem, a seção diz
  // o motivo e o resto do Reescrever continua. Fala com o núcleo (10-reescrever.js) por `reescrever.nucleo` e `reescrever.comandos`.
  (function () {
    var TX = PAGINA.reescrever, N = reescrever.nucleo;
    if (!TX || !N) return;
    var C = reescrever.comandos = reescrever.comandos || {};
    var estado = "nao";      // nao | carregando | pronta | erro
    var fila = [];           // os invólucros que esperam o arquivo
    C.aoMudar = C.aoMudar || function () {};
    function entrega(ok) {
      var lugares = fila; fila = [];
      lugares.forEach(function (lugar) {
        if (!lugar.isConnected) return;      // saiu do Reescrever antes de o arquivo chegar
        if (ok) C.monta(lugar);
        else { var e = N.novo("p", "rw-cmd-erro", TX.cmd_erro); e.setAttribute("role", "alert"); lugar.appendChild(e); }
      });
    }
    C.monta = function (host) {
      if (!TX.comandos) return;      // mapa sem contexto de comandos: a seção não aparece
      var lugar = N.novo("div", "rw-cmd-lugar"); lugar.style.display = "contents"; host.appendChild(lugar); fila.push(lugar);
      if (estado === "carregando") return;
      estado = "carregando";
      var s = document.createElement("script");
      s.onload = function () {
        if (s.parentNode) s.parentNode.removeChild(s);
        if (!window.CascaDoReescrever) { estado = "erro"; entrega(false); return; }
        window.CascaDoReescrever({ TX: TX, N: N, C: C, reescrever: reescrever, cur: function () { return cur; }, R: R, andares: LEVELS.length });      // troca `C.monta` e `C.aoMudar` pelos de verdade
        estado = "pronta"; entrega(true);
      };
      s.onerror = function () { if (s.parentNode) s.parentNode.removeChild(s); estado = "erro"; entrega(false); };
      s.src = TX.comandos.casca;
      document.body.appendChild(s);
    };
  })();
