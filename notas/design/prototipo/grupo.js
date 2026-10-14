/* Aba Grupo da prancheta (§19.6), protótipo. Os textos são os de dashboard/web/grupo.js do projeto (lidos em
   2026-10-13); aqui só a FORMA muda. `?grupo=<estado>` abre a aba já no estado; o seletor "Protótipo" troca. */
(function () {
  "use strict";
  var $ = function (id) { return document.getElementById(id); };
  function esc(s) { return String(s).replace(/[&<>"']/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]; }); }
  function iniciais(n) { return String(n || "?").trim().slice(0, 2).toUpperCase(); }

  var RECUSA = {
    permissao: ["neutro", "A líder não liberou desenho para você."],
    encerrada: ["neutro", "O grupo foi encerrado: a tática ficou só para leitura."],
    ritmo: ["desfeita", "Alterações rápidas demais: o servidor recusou (até 20 por segundo)."],
    tamanho: ["desfeita", "Alteração grande demais para o grupo (mais de 8 KB): ela foi desfeita."],
    duplicada: ["desfeita", "Outra aba sua alterou a tática ao mesmo tempo: a alteração foi desfeita."]
  };
  var O_QUE_GUARDA = "O servidor guarda só o nick que você escolher, quem está em cada grupo e as alterações da tática. O login é anônimo: sem e-mail, sem senha. Grupo parado há 30 dias é apagado.";
  var INDISPONIVEL = "Grupo indisponível agora. A tática continua salva neste navegador.";

  var MEMBROS = [
    { u: "a", nick: "nomad", on: true, pode: true, lider: true },
    { u: "b", nick: "spinx", on: true, pode: true },
    { u: "c", nick: "ztrike", on: true, pode: false },
    { u: "d", nick: "kyxsan", on: false, pode: false }
  ];

  /* estados da demonstração: papel (lider|membro), euSou (u), encerrada, seguir, todos, confirmando, fase */
  var ESTADOS = {
    "sem-grupo": { rot: "sem grupo (criar ou entrar)", fase: "fora" },
    "removido": { rot: "você foi removido", fase: "fora", info: "A líder tirou você deste grupo. A tática continua salva neste navegador." },
    "codigo-invalido": { rot: "sem grupo: código inválido", fase: "fora", codigo: "WAT99XYZ", erroCampo: "codigo", erro: "Nenhum grupo com esse código." },
    "nick-em-uso": { rot: "sem grupo: nick em uso", fase: "fora", nick: "spinx", codigo: "WAT99JVZ", erroCampo: "nick", erro: "Já tem alguém com esse nick no grupo." },
    "entrando": { rot: "entrando (carregando)", fase: "entrando", status: "Entrando no grupo…" },
    "indisponivel": { rot: "grupo indisponível", fase: "indisponivel" },
    "lider": { rot: "líder", fase: "dentro", papel: "lider", eu: "a", todos: false },
    "lider-todos": { rot: "líder: todos podem desenhar", fase: "dentro", papel: "lider", eu: "a", todos: true },
    "lider-transferir": { rot: "líder: confirmando transferir", fase: "dentro", papel: "lider", eu: "a", confirmando: "transferir" },
    "lider-encerrar": { rot: "líder: confirmando encerrar", fase: "dentro", papel: "lider", eu: "a", confirmando: "encerrar" },
    "lider-sozinha": { rot: "líder sozinha no grupo", fase: "dentro", papel: "lider", eu: "a", sozinha: true },
    "membro-permissao": { rot: "membro com permissão", fase: "dentro", papel: "membro", eu: "b", seguir: false },
    "membro-sem-permissao": { rot: "membro sem permissão, seguindo a líder", fase: "dentro", papel: "membro", eu: "c", seguir: true },
    "membro-sem-permissao-solto": { rot: "membro sem permissão, fora da líder", fase: "dentro", papel: "membro", eu: "c", seguir: false },
    "encerrada-lider": { rot: "sala encerrada (vista da líder)", fase: "dentro", papel: "lider", eu: "a", encerrada: true },
    "encerrada-membro": { rot: "sala encerrada (vista de membro)", fase: "dentro", papel: "membro", eu: "c", encerrada: true }
  };
  var S = { chave: "sem-grupo", etiqueta: null, recusa: null, tEtiqueta: null, tRecusa: null };

  function chave(acao, ligada, texto, extra, mini) {
    return '<button type="button" class="chave' + (mini ? " mini" : "") + '" role="switch" aria-checked="' + (ligada ? "true" : "false") + '" data-acao="' + acao + '"' + (extra || "") + ">" +
      "<span>" + esc(texto) + '</span><span class="estado">' + (ligada ? "Ligado" : "Desligado") + '</span><span class="pino" aria-hidden="true"></span></button>';
  }

  function podeDesenhar(st) { return st.fase === "dentro" && !st.encerrada && (st.papel === "lider" || st.todos || (MEMBROS.filter(function (m) { return m.u === st.eu; })[0] || {}).pode); }

  function membro(m, st) {
    var ehLider = !!m.lider, souEu = m.u === st.eu;
    var papel = ehLider ? "líder" : (st.todos || m.pode ? "pode desenhar" : "só assiste");
    var h = '<li class="gr-membro' + (m.on ? "" : " offline") + '"><span class="gr-ficha" aria-hidden="true">' + esc(iniciais(m.nick)) + "</span>" +
      '<span class="gr-nome"><span class="gr-quem"><b>' + esc(m.nick) + "</b>" + (souEu ? " (você)" : "") + "</span>" +
      '<small><span class="gr-online' + (m.on ? " on" : "") + '" aria-hidden="true"></span>' + (m.on ? "online" : "offline") + " · " + esc(papel) + "</small></span>";
    if (st.papel === "lider" && !ehLider) {
      h += '<span class="gr-controles">' + chave("permite", m.pode, "Pode desenhar", ' aria-label="' + esc(m.nick) + ' pode desenhar"' + (st.encerrada ? ' disabled title="O grupo foi encerrado: a tática ficou só para leitura."' : ""), true) +
        '<button type="button" class="btn" data-acao="expulsa" aria-label="Expulsar ' + esc(m.nick) + '"' + (st.encerrada ? " disabled" : "") + ">Expulsar</button></span>";
    }
    return h + "</li>";
  }

  function render() {
    var st = ESTADOS[S.chave], painel = $("pr-painel-grupo"); if (!painel) return;
    var membros = st.sozinha ? MEMBROS.slice(0, 1) : MEMBROS;
    var h = '<section class="caixa gr-caixa"><h2 class="rot">Grupo</h2>';
    if (st.fase === "indisponivel") {
      h += '<div class="aviso-bloco erro" role="alert"><span class="ico" aria-hidden="true">✕</span><p><b>Erro:</b> ' + esc(INDISPONIVEL) + "</p></div>" +
        '<button type="button" class="btn largo" data-acao="de-novo">Tentar de novo</button>' +
        '<p class="gr-texto apagado">Enquanto isso, a prancheta funciona como sempre, sozinho.</p>';
    } else if (st.fase !== "dentro") {
      var ocupado = st.fase === "entrando";
      if (st.info) h += '<div class="aviso-bloco info" role="status"><span class="ico" aria-hidden="true">i</span><p>' + esc(st.info) + "</p></div>";
      h += '<p class="gr-texto">Desenhe a tática junto, ao vivo: crie um grupo e mande o link, ou entre com o código.</p>' +
        '<label class="gr-campo">Seu nick<input type="text" id="gr-nick" maxlength="24" autocomplete="nickname" value="' + esc(st.nick || "") + '"' + (st.erroCampo === "nick" ? ' aria-invalid="true" aria-describedby="gr-e-nick"' : "") + ">" +
        (st.erroCampo === "nick" ? '<span class="erro-campo" id="gr-e-nick" role="alert">✕ Erro: ' + esc(st.erro) + "</span>" : "") + "</label>" +
        '<button type="button" class="btn principal largo" data-acao="criar"' + (ocupado ? " disabled" : "") + ">Criar grupo</button>" +
        '<div class="gr-ou" aria-hidden="true">ou</div>' +
        '<label class="gr-campo">Código do grupo<input type="text" class="codigo" id="gr-codigo" maxlength="8" autocomplete="off" spellcheck="false" value="' + esc(st.codigo || "") + '"' + (st.erroCampo === "codigo" ? ' aria-invalid="true" aria-describedby="gr-e-cod"' : "") + ">" +
        (st.erroCampo === "codigo" ? '<span class="erro-campo" id="gr-e-cod" role="alert">✕ Erro: ' + esc(st.erro) + "</span>" : "") + "</label>" +
        '<button type="button" class="btn largo" data-acao="entrar"' + (ocupado ? " disabled" : "") + ">Entrar num grupo</button>" +
        '<div class="aviso-bloco info gr-guarda"><span class="ico" aria-hidden="true">i</span><p>' + esc(O_QUE_GUARDA) + "</p></div>";
    } else {
      h += '<div class="gr-codigo-linha"><span class="rot">Código</span><span class="gr-codigo" id="gr-codigo-sala">WAT99JVZ</span>' +
        (st.papel === "lider" ? '<button type="button" class="btn" data-acao="copiar">Copiar link</button>' : "") + "</div>";
      if (st.encerrada) h += '<div class="aviso-bloco info" role="status"><span class="ico" aria-hidden="true">i</span><p>O grupo foi encerrado: a tática ficou só para leitura.</p></div>';
      if (st.papel === "lider") {
        h += chave("todos", st.todos, "Todos podem desenhar", st.encerrada ? ' disabled title="O grupo foi encerrado: a tática ficou só para leitura."' : "");
      } else {
        var pode = podeDesenhar(st);
        h += '<p class="gr-permissao" id="gr-permissao">' + (pode ? "✎ Você pode desenhar" : (st.encerrada ? "Só leitura" : "Só a líder desenha agora")) + "</p>" +
          chave("seguir", st.seguir, "Seguir a líder") +
          (st.seguir ? "" : '<button type="button" class="btn largo" data-acao="voltar">Voltar para a líder</button>');
      }
      h += '<h3 class="rot gr-sub">Membros (' + membros.length + ' de 10)</h3><ul class="gr-membros">' + membros.map(function (m) { return membro(m, st); }).join("") + "</ul>";
      if (st.papel === "lider" && !st.encerrada) {
        if (st.confirmando === "transferir") {
          h += '<div class="gr-confirma"><label class="gr-campo" for="gr-para">Transferir a liderança para</label><select id="gr-para">' + MEMBROS.filter(function (m) { return !m.lider; }).map(function (m) { return "<option>" + esc(m.nick) + "</option>"; }).join("") + "</select>" +
            '<div class="gr-linha"><button type="button" class="btn principal" data-acao="confirma">Transferir</button><button type="button" class="btn" data-acao="cancela">Cancelar</button></div>' +
            '<p class="gr-texto apagado">Você vira membro e só desenha se a nova líder liberar.</p></div>';
        } else if (st.confirmando === "encerrar") {
          h += '<div class="gr-confirma"><p class="gr-texto"><b>Encerrar o grupo?</b> A tática fica só para leitura para todos, e ninguém mais entra.</p>' +
            '<div class="gr-linha"><button type="button" class="btn principal" data-acao="confirma">Encerrar de vez</button><button type="button" class="btn" data-acao="cancela">Cancelar</button></div></div>';
        } else {
          h += '<div class="gr-linha"><button type="button" class="btn" data-acao="transferir"' + (st.sozinha ? ' disabled title="Ninguém mais no grupo."' : "") + ">Transferir liderança</button>" +
            '<button type="button" class="btn" data-acao="encerrar">Encerrar grupo</button></div>' + (st.sozinha ? '<p class="gr-texto apagado">Transferir fica desligado: ninguém mais no grupo.</p>' : "");
        }
      }
      if (st.papel !== "lider" || st.encerrada) h += '<button type="button" class="btn largo" data-acao="sair">Sair do grupo</button>';
    }
    h += '<p class="gr-status" id="gr-status" role="status" aria-live="polite">' + esc(st.status || "") + "</p></section>";
    painel.innerHTML = h;
    atualizaForaDoPainel(st);
  }

  /* o que o grupo liga e desliga fora do painel: contador na aba, ferramentas e a linha de dica */
  function atualizaForaDoPainel(st) {
    var c = $("aba-contador");
    if (c) { var dentro = st.fase === "dentro"; c.hidden = !dentro; if (dentro) { c.textContent = (st.sozinha ? 1 : 3); c.setAttribute("aria-label", (st.sozinha ? 1 : 3) + " online"); } }
    var soLeitura = st.fase === "dentro" && !podeDesenhar(st);
    var pr = document.querySelector(".pr"); if (pr) pr.classList.toggle("so-leitura", soLeitura);
    var motivo = st.encerrada ? "O grupo foi encerrado: a tática ficou só para leitura." : "A líder não liberou desenho para você.";
    [].forEach.call(document.querySelectorAll("[data-pincel], #b-desfazer, .banco button, .gr[data-gr], #b-buscar"), function (b) {
      b.classList.add("pr-bloqueavel");
      if (soLeitura) { b.disabled = true; b.title = motivo; } else if (b.dataset.demoBloq !== "0") { b.disabled = b.id === "b-buscar" && document.getElementById("pr-mapa-sel") && /cache|vertigo/.test(document.getElementById("pr-mapa-sel").value); b.removeAttribute("title"); }
    });
    if (window.PranchetaDica) window.PranchetaDica();
  }

  function dica() {
    var st = ESTADOS[S.chave], r = null;
    if (S.recusa) r = { html: "<b>" + esc(S.recusa[1]) + "</b>", classe: S.recusa[0] === "desfeita" ? "recusa-desfeita" : "recusa" };
    else if (st.fase === "dentro" && st.encerrada) r = { html: "<b>O grupo foi encerrado:</b> a tática ficou só para leitura.", classe: "bloqueado" };
    else if (st.fase === "dentro" && !podeDesenhar(st)) r = { html: "<b>Você acompanha a tática:</b> só a líder desenha agora. Você ainda pode mover o cabeçote e dar play.", classe: "bloqueado" };
    // a etiqueta temporária convive com qualquer texto: é justamente quem só assiste que mais a vê
    if (S.etiqueta) { r = r || { html: null }; r.etiqueta = '<span class="dica-etiqueta" role="status"><span class="gr-ficha" aria-hidden="true">' + esc(iniciais(S.etiqueta[0])) + "</span>" + esc(S.etiqueta[0] + " moveu " + S.etiqueta[1]) + "</span>"; }
    return r;
  }

  function mostra(chaveEstado) { S.chave = chaveEstado; render(); if ($("demo-grupo")) $("demo-grupo").value = chaveEstado; }

  function clique(e) {
    var b = e.target.closest("[data-acao]"); if (!b || b.disabled) return;
    var st = ESTADOS[S.chave], a = b.dataset.acao;
    if (a === "criar") { mostra("lider"); }
    else if (a === "entrar") { var cod = ($("gr-codigo") || {}).value || ""; mostra(/^[A-Z0-9]{8}$/i.test(cod) ? "membro-sem-permissao" : "codigo-invalido"); }
    else if (a === "todos") { st.todos = !st.todos; render(); }
    else if (a === "permite") { var m = MEMBROS[2]; m.pode = !m.pode; render(); }
    else if (a === "seguir") { st.seguir = !st.seguir; render(); }
    else if (a === "voltar") { st.seguir = true; render(); }
    else if (a === "transferir" || a === "encerrar") { st.confirmando = a; render(); }
    else if (a === "cancela") { st.confirmando = null; render(); }
    else if (a === "confirma") { var era = st.confirmando; st.confirmando = null; mostra(era === "encerrar" ? "encerrada-lider" : "membro-sem-permissao"); }
    else if (a === "sair" || a === "de-novo") { mostra("sem-grupo"); }
    else if (a === "copiar") { st.status = "Link copiado: https://pedroppansani.github.io/parser-replay-cs2/prancheta_de_mirage.html#g=WAT99JVZ"; render(); }
    else if (a === "expulsa") { st.status = "ztrike foi removido do grupo."; render(); }
  }

  function pisca(tipo, valor, ms) {
    clearTimeout(S["t" + tipo]); S[tipo.toLowerCase()] = valor; if (window.PranchetaDica) window.PranchetaDica();
    S["t" + tipo] = setTimeout(function () { S[tipo.toLowerCase()] = null; if (window.PranchetaDica) window.PranchetaDica(); }, ms);
  }

  window.GrupoDemo = { dica: dica, mostra: mostra, ESTADOS: ESTADOS };

  var sel = $("demo-grupo");
  if (sel) {
    sel.innerHTML = Object.keys(ESTADOS).map(function (k) { return '<option value="' + k + '">' + esc(ESTADOS[k].rot) + "</option>"; }).join("");
    sel.addEventListener("change", function () { S.etiqueta = S.recusa = null; mostra(sel.value); });
    $("demo-etiqueta").addEventListener("click", function () { pisca("Etiqueta", ["nomad", "ztrike"], 3000); });
    $("demo-recusa").addEventListener("click", function () {
      var st = ESTADOS[S.chave]; var k = st.fase === "dentro" && !podeDesenhar(st) ? "permissao" : "ritmo";
      pisca("Recusa", RECUSA[k], 6000);
    });
  }
  var painel = $("pr-painel-grupo"); if (painel) painel.addEventListener("click", clique);
  var q = new URLSearchParams(location.search).get("grupo");
  mostra(q && ESTADOS[q] ? q : "sem-grupo");
  if (q && ESTADOS[q]) { var aba = $("pt-grp"); if (aba) aba.click(); }
})();
