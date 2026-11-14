  /* ================= REESCREVER · COMANDOS (CR2) ================= */
  // A seção "Comandos" do painel do Reescrever: uma frase ("ropz corre pro meio aos 1:10"), o cartão "O que entendi" e, só depois do Aplicar, a trilha da peça. Aqui fica só a
  // CASCA: o título, o campo, os botões e o espaço do cartão (de altura fixa: abrir, entender, perguntar, aplicar e desfazer não mexem em nada à volta, nem no mapa). O leitor, as regras
  // do round real, o plano e a tela do cartão (`comandos/*.js`) vêm por arquivos, carregados SÓ quando a seção abre (ou o campo recebe o foco): a página da partida não os pede antes.
  // Fala com o núcleo (10-reescrever.js) por `reescrever.nucleo` e `reescrever.comandos`; a tela do cartão está em `dashboard/web/comandos/reescrever.js`.
  (function () {
    var TX = PAGINA.reescrever, N = reescrever.nucleo;
    if (!TX || !N) return;
    var C = reescrever.comandos = reescrever.comandos || {};
    var carga = { estado: "nao", contexto: null };      // nao | carregando | pronta | erro
    var ctl = null, secao = null, corpo = null, abre = null, ui = null, quer = false;

    function novo(tag, cls, texto) { return N.novo(tag, cls, texto); }
    function carrega(depois) {
      if (carga.estado === "pronta") { depois(); return; }
      if (carga.estado === "carregando") return;
      carga.estado = "carregando"; mostra();
      var fila = TX.comandos.arquivos.concat([TX.comandos.contexto]), i = 0, antes = window.__recebeContextoDoReal;
      window.__recebeContextoDoReal = function (c) { carga.contexto = c; };      // o arquivo do mapa entrega o contexto por aqui
      function falhou() { window.__recebeContextoDoReal = antes; carga.estado = "erro"; mostra(); }
      (function proximo() {
        if (i >= fila.length) {
          window.__recebeContextoDoReal = antes;
          if (carga.contexto && window.ComandosNoReescrever) { carga.estado = "pronta"; depois(); } else falhou();
          return;
        }
        var s = document.createElement("script");
        s.onload = function () { if (s.parentNode) s.parentNode.removeChild(s); proximo(); };
        s.onerror = function () { if (s.parentNode) s.parentNode.removeChild(s); falhou(); };
        s.src = fila[i++];
        document.body.appendChild(s);
      })();
    }
    function mostra() {      // o estado do carregamento, dentro do espaço do cartão (que já existe: nada se mexe)
      if (!ui || ctl) return;
      ui.cartao.textContent = "";
      if (carga.estado === "carregando") { var c = novo("p", "rw-cmd-aviso", TX.cmd_carregando); c.setAttribute("role", "status"); ui.cartao.appendChild(c); }
      else if (carga.estado === "erro") { var e = novo("p", "rw-cmd-erro", TX.cmd_erro); e.setAttribute("role", "alert"); ui.cartao.appendChild(e); }
      else ui.cartao.appendChild(novo("p", "rw-cmd-vazio", TX.cmd_vazio));
    }
    function inicia() {
      if (ctl || !ui) return;
      ctl = window.ComandosNoReescrever.inicia({
        campo: ui.campo, entender: ui.entender, aplicar: ui.aplicar, corrigir: ui.corrigir, cartao: ui.cartao, TX: TX, N: N, C: C, G: reescrever.granada, trilha: reescrever.trilha,
        contexto: carga.contexto, round: cur, R: R, t0: N.t0(), andares: LEVELS.length, editando: function () { return !reescrever.sua; }
      });
      if (quer) { quer = false; ctl.entende(); }
    }
    function abrir() { if (carga.estado === "nao" || carga.estado === "erro") { carga.estado = "nao"; carrega(inicia); } else if (carga.estado === "pronta") inicia(); }

    C.monta = function (host) {
      ctl = null; ui = null;
      if (!TX.comandos) return;      // mapa sem contexto de comandos: a seção não aparece
      secao = novo("section", "rw-cmd"); secao.id = "rw-comandos";
      var h = novo("h4", null);
      abre = N.botao("", "rw-cmd-cab", function () {
        var aberta = abre.getAttribute("aria-expanded") === "true";
        abre.setAttribute("aria-expanded", String(!aberta)); corpo.hidden = aberta;
        if (!aberta) abrir();
      });
      abre.id = "rw-cmd-abre"; abre.setAttribute("aria-expanded", "false"); abre.setAttribute("aria-controls", "rw-cmd-corpo");
      abre.appendChild(novo("span", null, TX.cmd_titulo)); abre.appendChild(novo("span", "rw-cmd-seta"));
      h.appendChild(abre); secao.appendChild(h);
      corpo = novo("div", "rw-cmd-corpo"); corpo.id = "rw-cmd-corpo"; corpo.hidden = true;
      var dica = novo("p", null, TX.cmd_dica); dica.id = "rw-cmd-dica"; corpo.appendChild(dica);
      var rot = novo("label", "rw-cmd-rot", TX.cmd_rotulo); rot.setAttribute("for", "rw-cmd-texto"); rot.className = "rw-cmd-rot sr";
      var campo = novo("textarea", "rw-cmd-texto"); campo.id = "rw-cmd-texto"; campo.rows = 2; campo.maxLength = 300; campo.placeholder = TX.cmd_exemplo; campo.setAttribute("aria-describedby", "rw-cmd-dica");
      campo.addEventListener("focus", abrir);      // o campo recebe o foco: o leitor carrega
      var entender = N.botao(TX.cmd_entender, "rw-btn prim", function () { if (ctl) ctl.entende(); else { quer = true; abrir(); } });
      entender.id = "rw-cmd-entender";
      campo.addEventListener("keydown", function (e) { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); entender.click(); } });
      var cartao = novo("div", "rw-cmd-cartao"); cartao.id = "rw-cmd-cartao"; cartao.setAttribute("role", "region"); cartao.setAttribute("aria-label", TX.cmd_entendi);
      cartao.setAttribute("aria-live", "polite"); cartao.tabIndex = 0;
      var aplicar = N.botao(TX.cmd_aplicar, "rw-btn prim", function () {}); aplicar.id = "rw-cmd-aplicar"; aplicar.disabled = true;
      var corrigir = N.botao(TX.cmd_corrigir, "rw-btn", function () {}); corrigir.id = "rw-cmd-corrigir"; corrigir.disabled = true;
      var acoes = novo("div", "rw-cmd-acoes"); acoes.appendChild(aplicar); acoes.appendChild(corrigir);
      [rot, campo, entender, cartao, acoes].forEach(function (n) { corpo.appendChild(n); });
      secao.appendChild(corpo); host.appendChild(secao);
      ui = { campo: campo, entender: entender, aplicar: aplicar, corrigir: corrigir, cartao: cartao };
      mostra();
    };
    C.aoMudar = function () { if (ctl) ctl.aoMudar(); };
  })();
