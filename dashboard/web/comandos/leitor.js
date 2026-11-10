/* O leitor de comandos da prancheta (C1): lê uma frase em português e devolve o que ENTENDEU, sem aplicar nada e sem chutar.
   Puro (sem DOM, sem rede): `LeitorDeComandos.le(frase, ctx)` -> { ok, acoes, perguntas, avisos, entendido, naoEntendido }.
   O contexto (`ctx`) vem do Python (`scripts/comandos_contexto.py`): os pontos do Pedro do mapa (alvo exato), os lugares da demo (pelo nome em inglês),
   os jogadores, as funções, o relógio e os TEXTOS das perguntas (frase da tela sai do Python, decisão 18).
   Regras: palavra desconhecida NUNCA é aproximada em silêncio (vira pergunta, com sugestões que a pessoa escolhe); campo que falta vira pergunta;
   nome repetido no mapa pergunta "qual?", a não ser que um qualificador ("default do A", "lixeira do CT") resolva sozinho; o tempo de corrida NÃO é
   calculado aqui (C3). Estilo ES5, como o resto do JS do site. */
(function (global) {
  "use strict";

  // ---------- texto: sem acento, minúsculo, mesmo tamanho (as posições valem na frase original) ----------
  function norm(s) {
    var o = "";
    for (var i = 0; i < s.length; i++) o += s.charAt(i).normalize("NFD").charAt(0).toLowerCase();
    return o;
  }
  function tokeniza(frase) {
    var n = norm(frase), re = /\d{1,2}:\d{2}|\d+s\b|\d+|[a-z]+|[,;]/g, m, t = [];
    while ((m = re.exec(n))) t.push({ t: m[0], i: m.index, f: m.index + m[0].length, uso: null });
    return t;
  }
  function chaveDe(texto) { return tokeniza(texto).map(function (k) { return k.t; }).join(" "); }

  // ---------- vocabulário ----------
  function lista(s) { var o = {}; s.split(" ").forEach(function (w) { o[w] = true; }); return o; }
  var LANCAR = lista("joga jogar jogam lanca lancar lancam solta soltar soltam manda mandar mandam usa usar usam arremessa arremessar arremessam");
  var MOVER = lista("vai ir vao roda rodar rodam corre correr correm anda andar andam caminha caminhar caminham agacha agachar agacham");
  var SEGURAR = lista("segura segurar seguram fica ficar ficam holda holdar holdam");
  var ESPERAR = lista("espera esperar esperam aguarda aguardar aguardam");
  var GRANADAS = { smoke: "smoke smokes fumaca fumacas", flash: "flash flashes flashbang flashbangs luz", molotov: "molotov molotovs molo molos incendiaria incendiarias fogo",
                   he: "he granada granadas frag", decoy: "decoy" };
  var GRANADA_DE = {}; Object.keys(GRANADAS).forEach(function (k) { GRANADAS[k].split(" ").forEach(function (w) { GRANADA_DE[w] = k; }); });
  var MODO_DE = { correndo: "correndo", corre: "correndo", correm: "correndo", andando: "andando", caminhando: "andando", agachado: "agachado", agachando: "agachado" };
  var MODO_DO_VERBO = { corre: "correndo", correm: "correndo", correr: "correndo", anda: "andando", andam: "andando", andar: "andando", caminha: "andando", caminham: "andando",
                        caminhar: "andando", agacha: "agachado", agacham: "agachado", agachar: "agachado" };
  var PREPS = lista("ate pra para pro em na no nos nas ao a de do da");
  var PARADAS = lista("o a os as um uma uns umas de do da dos das pra pro para ate em na no nos nas ao aos as com se que e ele ela eles elas depois seguida ai entao aos mesmo tempo junto juntos por");
  var UNIDADE_S = lista("s seg segs segundo segundos");
  var LADOS = { tr: "tr", t: "tr", ct: "ct" };

  var NUMEROS = { um: 1, dois: 2, duas: 2, tres: 3, quatro: 4, cinco: 5 };
  function numero(tok, ant) {   // 1 a 5, em algarismo ou por extenso; "um" só depois de jogador/TR/CT (senão é o artigo: "joga um smoke")
    if (!tok) return null;
    if (/^[1-5]$/.test(tok.t)) return parseInt(tok.t, 10);
    if (NUMEROS[tok.t] && (tok.t !== "um" || (ant && (LADOS[ant.t] || /^(jogador|player|numero|num)$/.test(ant.t))))) return NUMEROS[tok.t];
    return null;
  }
  function formata(tpl, vars) { return String(tpl).replace(/\{(\w+)\}/g, function (_, k) { return vars && vars[k] != null ? vars[k] : "{" + k + "}"; }); }
  function relogioTexto(restante) { return Math.floor(restante / 60) + ":" + (restante % 60 < 10 ? "0" : "") + (restante % 60); }

  // ---------- o índice dos nomes: pontos do Pedro (alvo exato) e lugares da demo (nome em inglês) ----------
  function monta(ctx) {
    var idx = {}, maxLen = 1;
    function poe(texto, entrada, semColar) {   // o nome com espaço e colado valem o mesmo ("Bombsite A" e "BombsiteA"); o ponto do Pedro ganha da área de mesmo nome
      var k = chaveDe(texto); if (!k) return;
      [k, k.replace(/ /g, "")].forEach(function (c, v) {
        if (v === 1 && (c === k || semColar)) return;
        if (entrada.tipo === "area" && idx[c] && idx[c][0].tipo === "ponto") return;
        maxLen = Math.max(maxLen, c.split(" ").length);
        (idx[c] = idx[c] || []).push(entrada);
      });
    }
    (ctx.pontos || []).forEach(function (p) {
      var e = { tipo: "ponto", p: p };
      if (p.tipo === "bombsite") {
        ["bombsite", "bomb", "site"].forEach(function (w) { poe(w + " " + p.nome, e, w !== "bombsite"); });   // "bomb a" colado é a palavra "bomba": não cola
        return;
      }
      poe(p.nome, e); (p.apelidos || []).forEach(function (n) { poe(n, e, true); });   // só o nome principal vale colado: apelido colado vira palavra solta
      if (p.qualificacao) {
        poe(p.nome + " " + p.qualificacao, e);
        if (!/^(d[aoe]s?)\b/i.test(norm(p.qualificacao))) poe(p.nome + " de " + p.qualificacao, e);
      }
    });
    (ctx.areas || []).forEach(function (a) {
      var e = { tipo: "area", a: a }, ks = [a.texto, a.nome].concat(a.apelidos || []);
      ks.forEach(function (n, j) { poe(n, e, j > 1); });
    });
    return { idx: idx, maxLen: Math.min(maxLen, 6) };
  }
  function unicos(lista_) {   // entradas distintas (o mesmo ponto pode entrar por dois apelidos)
    var vistos = {}, o = [];
    lista_.forEach(function (e) { var id = e.tipo === "ponto" ? "p" + e.p.id : "a" + e.a.nome; if (!vistos[id]) { vistos[id] = 1; o.push(e); } });
    return o;
  }
  function lev(a, b) {
    var d = [], i, j;
    for (i = 0; i <= a.length; i++) { d[i] = [i]; }
    for (j = 1; j <= b.length; j++) d[0][j] = j;
    for (i = 1; i <= a.length; i++) for (j = 1; j <= b.length; j++)
      d[i][j] = Math.min(d[i - 1][j] + 1, d[i][j - 1] + 1, d[i - 1][j - 1] + (a.charAt(i - 1) === b.charAt(j - 1) ? 0 : 1));
    return d[a.length][b.length];
  }
  function sugestoes(trecho, indice, quantas) {
    var t = chaveDe(trecho), pontos = [];
    if (!t) return [];
    Object.keys(indice.idx).forEach(function (k) {
      var sim = 1 - lev(t, k) / Math.max(t.length, k.length);
      if (Math.min(k.length, t.length) >= 3 && (k.indexOf(t) >= 0 || t.indexOf(k) >= 0)) sim = Math.max(sim, 0.7);
      if (sim >= 0.62) unicos(indice.idx[k]).forEach(function (e) { pontos.push({ e: e, sim: sim }); });
    });
    pontos.sort(function (x, y) { return y.sim - x.sim; });
    var vistos = {}, o = [];
    pontos.forEach(function (x) { var id = x.e.tipo === "ponto" ? "p" + x.e.p.id : "a" + x.e.a.nome; if (!vistos[id] && o.length < quantas) { vistos[id] = 1; o.push(x.e); } });
    return o;
  }
  function alvoDe(e) {
    if (e.tipo === "ponto") return { tipo: "ponto", id: e.p.id, nome: e.p.nome, qualificacao: e.p.qualificacao || "", x: e.p.x, y: e.p.y, andar: e.p.andar, vertical: e.p.vertical || "", lugar: e.p.lugar || "" };
    return { tipo: "area", nome: e.a.nome, texto: e.a.texto, x: e.a.x, y: e.a.y, andar: e.a.andar || "", lugar: e.a.nome };
  }
  function rotuloDe(e, outros) {   // como a opção se escreve: o nome e o que distingue (o andar, o lugar da demo; as coordenadas se nada distingue)
    if (e.tipo === "area") return e.a.texto;
    var p = e.p, r = p.nome + (p.qualificacao ? " (" + p.qualificacao + ")" : "") + (p.vertical ? (p.vertical === "cima" ? " ↑" : " ↓") : "");
    var parte = [];
    if (p.andar && p.andar !== "único") parte.push(p.andar);
    if (p.lugar) parte.push(p.lugar);
    var iguais = outros.filter(function (o) { return o.tipo === "ponto" && (o.p.lugar || "") === (p.lugar || "") && (o.p.andar || "") === (p.andar || ""); }).length;
    if (iguais > 1 || !parte.length) parte.push("x " + p.x + ", y " + p.y);
    return r + " · " + parte.join(" · ");
  }

  // ---------- o leitor ----------
  function le(frase, ctx) {
    var TX = ctx.textos || {}, SEG = ctx.segundos_do_round || 115, tk = tokeniza(frase), indice = monta(ctx);
    var jogadores = ctx.jogadores || [], funcoes = {}, perguntas = [], avisos = [], entendido = [], acoes = [];
    (ctx.funcoes || []).forEach(function (f) { funcoes[chaveDe(f)] = f; });
    var trechoDe = function (a, b) { return a > b ? "" : frase.slice(tk[a].i, tk[b].f); };
    var marca = function (a, b, campo) {
      for (var k = a; k <= b; k++) tk[k].uso = campo;
      entendido.push({ campo: campo, trecho: trechoDe(a, b), i: tk[a].i, f: tk[b].f });
    };

    // 1) os nomes de lugar (o mais longo, da esquerda para a direita), na frase toda
    var nomes = {};   // índice do 1º token -> { n, entradas }
    for (var i = 0; i < tk.length; i++) {
      if (LADOS[tk[i].t] && tk[i + 1] && numero(tk[i + 1], tk[i])) { i++; continue; }   // "ct 3" é o jogador, mesmo que exista um ponto chamado "CT"
      for (var L = Math.min(indice.maxLen, tk.length - i); L >= 1; L--) {
        var chave = tk.slice(i, i + L).map(function (k) { return k.t; }).join(" ");
        if (indice.idx[chave]) { nomes[i] = { n: L, entradas: unicos(indice.idx[chave]) }; for (var z = i; z < i + L; z++) tk[z].uso = "nome"; i += L - 1; break; }
      }
    }

    // 2) as orações: cortam em "e", vírgula, "depois", "em seguida", "aí", "então", "ao mesmo tempo"
    var oracoes = [], atual = { a: 0, rel: null, tk: [] };
    function fecha(proxRel) {
      if (atual.tk.length) oracoes.push(atual);
      atual = { a: 0, rel: proxRel || (atual.tk.length ? null : atual.rel), tk: [] };
    }
    for (i = 0; i < tk.length; i++) {
      var w = tk[i].t, livre = tk[i].uso !== "nome";
      if (livre && (w === "e" || w === "," || w === ";")) { fecha(null); continue; }
      if (livre && (w === "depois" || w === "ai" || w === "entao")) { fecha("depois"); continue; }
      if (livre && w === "em" && tk[i + 1] && tk[i + 1].t === "seguida" && tk[i + 1].uso !== "nome") { fecha("depois"); i++; continue; }
      if (livre && w === "ao" && tk[i + 1] && tk[i + 1].t === "mesmo" && tk[i + 2] && tk[i + 2].t === "tempo") { fecha("junto"); i += 2; continue; }
      atual.tk.push(i);
    }
    fecha(null);

    // 3) cada oração: quem, o quê, onde, quando
    var anterior = null, ultimosSujeitos = null, carregados = [];
    oracoes.forEach(function (o, n) {
      var ac = { indice: acoes.length, tipo: null, quem: [], granada: null, alvo: null, modo: null, modo_padrao: false, quando: null, duracao_s: null, espera_s: null,
                 trecho: trechoDe(o.tk[0], o.tk[o.tk.length - 1]), origem_do_alvo: null, depende_do_deslocamento: false };
      var pend = { quem: [], onde: null };   // perguntas desta ação
      var livres = function () { return o.tk.filter(function (k) { return tk[k].uso === null; }); };

      // quem
      var suj = [];
      for (var q = 0; q < o.tk.length; q++) {
        var k = o.tk[q], t = tk[k].t, prox = tk[o.tk[q + 1]], dig = function (x, ant) { return numero(x, ant || tk[k]); };
        if (tk[k].uso !== null) continue;
        if (LADOS[t] && dig(prox) && tk[o.tk[q + 1]].uso === null) { suj.push({ lado: LADOS[t], num: dig(prox), ref: trechoDe(k, o.tk[q + 1]) }); marca(k, o.tk[q + 1], "quem"); q++; continue; }
        if ((t === "jogador" || t === "player" || t === "numero" || t === "num") && prox) {
          var pos = q + 1, lado = null;
          if (LADOS[prox.t] && tk[o.tk[pos]].uso === null) { lado = LADOS[prox.t]; pos++; }
          var dn = dig(tk[o.tk[pos]], tk[o.tk[pos - 1]]);
          if (dn) { suj.push({ lado: lado, num: dn, ref: trechoDe(k, o.tk[pos]) }); marca(k, o.tk[pos], "quem"); q = pos; continue; }
        }
        if (t === "o" && dig(prox) && tk[o.tk[q + 1]].uso === null && !(tk[o.tk[q + 2]] && UNIDADE_S[tk[o.tk[q + 2]].t])) {
          suj.push({ lado: null, num: dig(prox), ref: trechoDe(k, o.tk[q + 1]) }); marca(k, o.tk[q + 1], "quem"); q++; continue;
        }
        for (var Lf = Math.min(3, o.tk.length - q); Lf >= 1; Lf--) {   // função: "o awper", "o lurker", "o entry fragger"
          var kf = o.tk.slice(q, q + Lf).map(function (x) { return tk[x].t; }).join(" ");
          if (funcoes[kf] && o.tk.slice(q, q + Lf).every(function (x) { return tk[x].uso === null; })) { suj.push({ lado: null, num: null, funcao: funcoes[kf], ref: trechoDe(k, o.tk[q + Lf - 1]) }); marca(k, o.tk[q + Lf - 1], "quem"); q += Lf - 1; break; }
        }
      }
      if (carregados.length) { suj = carregados.concat(suj); carregados = []; }
      var pronome = o.tk.filter(function (x) { return tk[x].uso === null && (tk[x].t === "ele" || tk[x].t === "ela"); });
      if (!suj.length && pronome.length && ultimosSujeitos) { suj = ultimosSujeitos.map(function (s) { return s; }); marca(pronome[0], pronome[0], "quem"); }
      var implicito = false;
      if (!suj.length && ultimosSujeitos) { suj = ultimosSujeitos.slice(); implicito = true; }
      ac.quem_herdado = implicito || (!!pronome.length && !suj.some(function (x) { return x.ref && !/^(ele|ela)$/.test(x.ref); }));
      ac.quem = suj.map(function (s) {
        var cand = jogadores.filter(function (j) { return (s.lado ? j.lado === s.lado : true) && (s.num ? j.num === s.num : true) && (s.funcao ? j.funcao === s.funcao : true); });
        var r = { lado: s.lado || null, num: s.num || null, funcao: s.funcao || null, ref: s.ref || "" };
        if (cand.length === 1) { r.lado = cand[0].lado; r.num = cand[0].num; r.funcao = cand[0].funcao || r.funcao; }
        else r.resolvido = false;
        if (cand.length === 1) r.resolvido = true;
        r.candidatos = cand.map(function (j) { return { lado: j.lado, num: j.num }; });
        return r;
      });
      // Se alguém foi nomeado e o resto da frase nada diz: só o sujeito, vai para a próxima oração (lista "tr 2 e tr 3 jogam ...")
      var temVerbo = o.tk.some(function (x) { var w = tk[x].t; return tk[x].uso === null && (LANCAR[w] || MOVER[w] || SEGURAR[w] || ESPERAR[w]); });
      var soSujeito = suj.length && !implicito && !temVerbo && livres().filter(function (x) { return !PARADAS[tk[x].t]; }).length === 0 && !o.tk.some(function (x) { return tk[x].uso === "nome"; });
      if (soSujeito) { carregados = suj; return; }

      // o quê
      o.tk.forEach(function (x) {
        var w = tk[x].t; if (tk[x].uso !== null) return;
        if (!ac.tipo && (LANCAR[w] || MOVER[w] || SEGURAR[w] || ESPERAR[w])) {
          ac.tipo = LANCAR[w] ? "lancar" : MOVER[w] ? "mover" : SEGURAR[w] ? "segurar" : "esperar";
          if (MODO_DO_VERBO[w]) { ac.modo = MODO_DO_VERBO[w]; }
          marca(x, x, "acao");
        }
      });
      o.tk.forEach(function (x) {
        var w = tk[x].t; if (tk[x].uso !== null) return;
        if (GRANADA_DE[w] && !ac.granada) { ac.granada = GRANADA_DE[w]; marca(x, x, "granada"); if (!ac.tipo) ac.tipo = "lancar"; }
        else if (MODO_DE[w] && !(MODO_DO_VERBO[w] && w === o.tk.map(function (y) { return tk[y].t; }).filter(function (v) { return MOVER[v]; })[0])) { ac.modo = MODO_DE[w]; marca(x, x, "modo"); }
      });
      if (ac.tipo === "mover" && !ac.modo) { ac.modo = "correndo"; ac.modo_padrao = true; }

      // onde: o nome de lugar da oração (depois: o qualificador "do A", "do CT", "do meio" se o nome for repetido)
      var nomeIx = o.tk.filter(function (x) { return nomes[x]; })[0], entradas = null, fimNome = null;
      if (nomeIx != null) { entradas = nomes[nomeIx].entradas; fimNome = nomeIx + nomes[nomeIx].n - 1; marca(nomeIx, fimNome, "onde"); }
      else {   // a letra do bombsite: "na b", "pra a", "site a" (o "a" artigo não conta: só depois de preposição e antes de nada ou de um horário/modo)
        o.tk.forEach(function (x) {
          if (entradas || tk[x].uso !== null || !/^[ab]$/.test(tk[x].t)) return;
          var ant = tk[x - 1], pro = tk[x + 1];
          var depoisDe = ant && (PREPS[ant.t] || ant.t === "site" || ant.t === "bomb" || ant.t === "bombsite");
          var fim = !pro || /^\d+:\d\d$/.test(pro.t) || pro.t === "aos" || MODO_DE[pro.t] || pro.t === "em" || pro.t === "no" || pro.t === "com";
          if (tk[x].t === "a" && !(ant && (ant.t === "site" || ant.t === "bomb" || ant.t === "bombsite")) && !(depoisDe && fim)) return;
          if (tk[x].t === "b" && !depoisDe && !fim) return;
          var sites = (ctx.pontos || []).filter(function (p) { return p.tipo === "bombsite" && p.nome.toLowerCase() === tk[x].t; });
          if (sites.length) { entradas = sites.map(function (p) { return { tipo: "ponto", p: p }; }); nomeIx = x; fimNome = (ant && (ant.t === "site" || ant.t === "bomb" || ant.t === "bombsite") ? x : x); marca(x, x, "onde"); }
        });
      }
      if (entradas && entradas.length > 1) {   // nome repetido: tenta o qualificador "do/da/de X"
        var prox2 = tk[fimNome + 1], resolvido = null;
        if (prox2 && /^(do|da|de|dos|das)$/.test(prox2.t) && tk[fimNome + 2]) {
          var refTk = tk[fimNome + 2], refPos = [], refTxt = refTk.t, consumiu = fimNome + 2;
          var nomeRef = nomes[fimNome + 2];
          if (refTxt === "ct") { refPos = (ctx.pontos || []).filter(function (p) { return /^base ct$/.test(chaveDe(p.nome)); }); if (!refPos.length) refPos = (ctx.areas || []).filter(function (a) { return /ct ?spawn/i.test(a.nome); }); }
          else if (refTxt === "tr" || refTxt === "t") { refPos = (ctx.pontos || []).filter(function (p) { return /^base tr$/.test(chaveDe(p.nome)); }); if (!refPos.length) refPos = (ctx.areas || []).filter(function (a) { return /^t ?spawn$/i.test(a.nome); }); }
          else if (refTxt === "a" || refTxt === "b") refPos = (ctx.pontos || []).filter(function (p) { return p.tipo === "bombsite" && p.nome.toLowerCase() === refTxt; });
          else if (nomeRef) { refPos = nomeRef.entradas.map(function (e) { return e.tipo === "ponto" ? e.p : e.a; }); consumiu = fimNome + 2 + nomeRef.n - 1; }
          if (refPos.length) {
            var dist = entradas.map(function (e) {
              var px = e.tipo === "ponto" ? e.p : e.a;
              return Math.min.apply(null, refPos.map(function (r) { return Math.hypot(px.x - r.x, px.y - r.y); }));
            });
            var ordem = dist.map(function (d, j) { return { d: d, j: j }; }).sort(function (x, y) { return x.d - y.d; });
            if (ordem.length >= 2 && ordem[0].d * 1.25 <= ordem[1].d) resolvido = entradas[ordem[0].j];
            if (resolvido) { marca(fimNome + 1, consumiu, "onde"); entradas = [resolvido]; }
          }
        }
      }
      if (entradas) {
        if (entradas.length === 1) { ac.alvo = alvoDe(entradas[0]); ac.origem_do_alvo = entradas[0].tipo; }
        else pend.onde = { codigo: "qual", entradas: entradas, nome: trechoDe(nomeIx, fimNome) };
      }

      // quando
      var tempos = o.tk.filter(function (x) { return tk[x].uso === null && (/^\d{1,2}:\d{2}$/.test(tk[x].t) || /^\d+$/.test(tk[x].t) || /^\d+s$/.test(tk[x].t)); });
      tempos.forEach(function (x) {
        var t = tk[x].t, ant = tk[x - 1], pro = tk[x + 1], mm;
        if ((mm = /^(\d{1,2}):(\d{2})$/.exec(t))) {
          var restante = parseInt(mm[1], 10) * 60 + parseInt(mm[2], 10);
          marca(x, x, "quando");
          if (ant && /^(aos?|as|com|no|na|ate)$/.test(ant.t) && ant.uso === null) marca(x - 1, x, "quando");
          if (ac.tipo === "esperar" && ant && ant.t === "ate") ac.quando = { tipo: "espera_ate", segundos_restantes: restante };
          else ac.quando = { tipo: "relogio", segundos_restantes: restante, t_decorrido: SEG - restante };
          if (restante > SEG) { ac.quando.invalido = true; }
          return;
        }
        var n_ = parseInt(t, 10), unidade = /s$/.test(t) && t !== String(n_), pos = x, fimU = x;
        if (!unidade && pro && UNIDADE_S[pro.t] && pro.uso === null) { unidade = true; fimU = x + 1; }
        if (!unidade) return;   // número solto que não é segundos: fica como "não entendido"
        marca(x, fimU, "quando");
        var doInicio = /^(do|depois|apos|desde)$/.test((tk[fimU + 1] || {}).t || "") && (/^(inicio|comeco|round)$/.test((tk[fimU + 2] || {}).t || "") || /^(inicio|comeco|round)$/.test((tk[fimU + 3] || {}).t || "") || /^(inicio|comeco)$/.test((tk[fimU + 4] || {}).t || ""));
        if (ant && ant.t === "em" && ant.uso === null) { ac.duracao_s = n_; marca(x - 1, fimU, "duracao"); return; }
        if (ac.tipo === "esperar") { ac.espera_s = n_; marca(x, fimU, "duracao"); return; }
        if (ant && /^(aos?|as|com|no)$/.test(ant.t) && ant.uso === null) marca(x - 1, fimU, "quando");
        if (doInicio) { var k2 = fimU + 1; while (tk[k2] && /^(do|depois|apos|desde|o|inicio|comeco|round)$/.test(tk[k2].t) && k2 <= fimU + 4) { tk[k2].uso = "quando"; k2++; } ac.quando = { tipo: "inicio", segundos: n_, t_decorrido: n_ }; }
        else ac.quando = { tipo: "segundos_ambiguo", segundos: n_ };
      });
      // sobrou "do início" colado ao número já tratado
      if (o.rel && !ac.quando) ac.quando = { tipo: o.rel };
      if (!ac.quando && anterior && ac.quem.length && !o.rel && implicito && anterior.quando) ac.quando = { tipo: "depois" };   // mesmo jogador, "e roda pra TV": vem depois
      if (ac.quando && ac.quando.tipo === "depois" && !anterior) ac.quando = null;

      // não entendido: palavras que sobraram (artigos e preposições não contam)
      var sobra = livres().filter(function (x) { return !PARADAS[tk[x].t] && !/^[ab]$/.test(tk[x].t); });
      var grupos = [];
      sobra.forEach(function (x) { var g = grupos[grupos.length - 1]; if (g && x === g.f + 1) g.f = x; else grupos.push({ a: x, f: x }); });
      ac.nao_entendido = grupos.map(function (g) { return { trecho: trechoDe(g.a, g.f), i: tk[g.a].i, f: tk[g.f].f }; });

      // perguntas desta ação (ordem fixa: quem, granada/ação, onde, quando)
      var P = [];
      if (!ac.quem.length) P.push({ codigo: "quem", campo: "quem", opcoes: jogadores.map(function (j) { return { rotulo: formata(TX["opcao_jogador"], { lado: j.lado.toUpperCase(), num: j.num }), valor: { lado: j.lado, num: j.num } }; }) });
      ac.quem.forEach(function (s, ix) {
        if (s.resolvido || ac.quem_herdado) return;
        if (s.funcao && !s.candidatos.length) P.push({ codigo: "quem_funcao", campo: "quem", ref: s.ref, indice_quem: ix, opcoes: jogadores.map(function (j) { return { rotulo: formata(TX["opcao_jogador"], { lado: j.lado.toUpperCase(), num: j.num }), valor: { lado: j.lado, num: j.num } }; }) });
        else if (s.candidatos.length > 1) P.push({ codigo: "quem_lado", campo: "quem", ref: s.ref, indice_quem: ix, opcoes: s.candidatos.map(function (j) { return { rotulo: formata(TX["opcao_jogador"], { lado: j.lado.toUpperCase(), num: j.num }), valor: { lado: j.lado, num: j.num } }; }) });
        else P.push({ codigo: "quem", campo: "quem", ref: s.ref, indice_quem: ix, opcoes: jogadores.map(function (j) { return { rotulo: formata(TX["opcao_jogador"], { lado: j.lado.toUpperCase(), num: j.num }), valor: { lado: j.lado, num: j.num } }; }) });
      });
      if (!ac.tipo) {
        var opc = [];
        if (ac.alvo || pend.onde) opc.push({ rotulo: formata(TX["opcao_mover"], { lugar: ac.alvo ? (ac.alvo.texto || ac.alvo.nome) : trechoDe(nomeIx, fimNome) }), valor: { tipo: "mover" } }, { rotulo: formata(TX["opcao_segurar"], { lugar: ac.alvo ? (ac.alvo.texto || ac.alvo.nome) : trechoDe(nomeIx, fimNome) }), valor: { tipo: "segurar" } });
        P.push({ codigo: "acao", campo: "acao", trecho: ac.trecho, opcoes: opc });
      }
      if (ac.tipo === "lancar" && !ac.granada) P.push({ codigo: "granada", campo: "granada", opcoes: ["smoke", "flash", "molotov", "he"].map(function (g) { return { rotulo: TX["granada_" + g], valor: { granada: g } }; }) });
      if (ac.tipo === "lancar" || ac.tipo === "mover" || ac.tipo === "segurar") {
        if (pend.onde) P.push({ codigo: "qual", campo: "onde", nome: pend.onde.nome, opcoes: pend.onde.entradas.map(function (e) { return { rotulo: rotuloDe(e, pend.onde.entradas), valor: { alvo: alvoDe(e) } }; }) });
        else if (!ac.alvo) {
          var desc = ac.nao_entendido.length ? ac.nao_entendido[ac.nao_entendido.length - 1].trecho : "";
          var sg = desc ? sugestoes(desc, indice, 5) : [];
          P.push({ codigo: desc ? "onde_desconhecido" : "onde", campo: "onde", trecho: desc, opcoes: sg.map(function (e) { return { rotulo: rotuloDe(e, sg), valor: { alvo: alvoDe(e) } }; }) });
        }
      }
      if (ac.tipo === "esperar" && ac.espera_s == null && !(ac.quando && ac.quando.tipo === "espera_ate")) P.push({ codigo: "espera", campo: "duracao", trecho: ac.trecho, opcoes: [] });
      if (ac.quando && ac.quando.invalido) P.push({ codigo: "horario_invalido", campo: "quando", horario: relogioTexto(ac.quando.segundos_restantes), opcoes: [] }), ac.quando = null;
      else if (ac.quando && ac.quando.tipo === "segundos_ambiguo") {
        var ns = ac.quando.segundos;
        P.push({ codigo: "quando_segundos", campo: "quando", n: ns, opcoes: [
          { rotulo: formata(TX["opcao_relogio_n"], { n: ns, h: relogioTexto(ns) }), valor: { quando: { tipo: "relogio", segundos_restantes: ns, t_decorrido: SEG - ns } } },
          { rotulo: formata(TX["opcao_inicio_n"], { n: ns }), valor: { quando: { tipo: "inicio", segundos: ns, t_decorrido: ns } } }] }); ac.quando = null;
      } else if (!ac.quando && ac.tipo) P.push({ codigo: "quando", campo: "quando", trecho: ac.trecho, opcoes: [] });
      P.forEach(function (p) { p.acao = ac.indice; p.texto = formata(TX["pergunta_" + p.codigo], { trecho: p.trecho || ac.trecho, nome: p.nome || "", n: p.n || "", ref: p.ref || "", horario: p.horario || "" }); perguntas.push(p); });
      if (ac.nao_entendido.length && !P.some(function (p) { return p.codigo === "onde_desconhecido" || p.codigo === "acao"; }))
        avisos.push({ codigo: "palavra_sobrando", acao: ac.indice, trechos: ac.nao_entendido.map(function (x) { return x.trecho; }) });

      // avisos
      if (ac.quando && (ac.quando.tipo === "relogio" || ac.quando.tipo === "inicio") && anterior && anterior.tipo === "mover" && sameQuem(anterior, ac)) ac.depende_do_deslocamento = true;
      if (ac.quando && ac.quando.t_decorrido != null && anterior && sameQuem(anterior, ac) && anterior.quando && anterior.quando.t_decorrido != null && o.rel === "depois" && ac.quando.t_decorrido < anterior.quando.t_decorrido)
        avisos.push({ codigo: "ordem_invertida", acao: ac.indice });
      if (ac.duracao_s != null) avisos.push({ codigo: "duracao_imposta", acao: ac.indice, segundos: ac.duracao_s });
      acoes.push(ac); anterior = ac;
      if (ac.quem.length) ultimosSujeitos = suj;
    });
    function sameQuem(a, b) { return a.quem.map(function (s) { return s.ref; }).join() === b.quem.map(function (s) { return s.ref; }).join() || (a.quem.length && b.quem.length && a.quem[0].num === b.quem[0].num && a.quem[0].lado === b.quem[0].lado); }

    var naoEntendido = [];
    acoes.forEach(function (a) { (a.nao_entendido || []).forEach(function (x) { naoEntendido.push(x); }); });
    return { ok: perguntas.length === 0 && acoes.length > 0 && !naoEntendido.length, acoes: acoes, perguntas: perguntas, avisos: avisos, entendido: entendido, naoEntendido: naoEntendido };
  }

  global.LeitorDeComandos = { le: le, norm: norm };
  if (typeof module !== "undefined" && module.exports) module.exports = global.LeitorDeComandos;
})(typeof window !== "undefined" ? window : this);
