/* As regras do round REAL para os comandos do Reescrever (CR1c): o elenco (nick, lado, número, vivo, morte), o relógio da tela, a pergunta "bomba ou round?" e os vereditos.
   Puro (sem DOM, sem rede), em cima de `comandos/leitor.js` (que entende os nicks quando o contexto os traz). Sem tela: a CR2 desenha o que sai daqui.

   Uso:   ctx = ComandosDoReal.contexto(contextoDoMapa, round, t0, R)         // `round` e `R` são os do replay (round.players, round.events; R.sample_hz, R.clock); t0 = o quadro do instante
          l   = ComandosDoReal.le(frase, ctx)                                // a leitura: ações, perguntas (com os nicks e a vida nos rótulos), avisos
          l   = ComandosDoReal.responde(l, indice, valor, ctx)               // USE o valor devolvido (a resposta de "quem_ou_lugar" relê a frase)
          vs  = ComandosDoReal.veredictos(l, ctx, fins)                      // o que o round real diz de cada comando; `fins[acao]` = o fim (em s do início) que o plano calculou

   As regras (decisões do Pedro na CR0, 2026-11-13):
     - "o 4" sem lado sempre pergunta (o leitor); o nick vale (caixa, acento, parcial com 4 letras ou mais e sem ambiguidade); nick que também é lugar do mapa pergunta;
     - o relógio é o da tela: o do round e, depois do plant, o da bomba. O horário escrito que cai depois do plant (e cabe no relógio da bomba) pergunta "bomba ou round?";
     - comando que COMEÇA depois da morte real do jogador (ou de um jogador que já estava morto no instante): recusado, com [Escolher outro jogador] e [Corrigir];
     - comando que COMEÇA antes da morte e TERMINA depois: aplicado; a peça anda até a hora da morte e esmaece ali (o aviso diz isso);
     - comando que começa antes do instante do "Reescrever daqui": o real não muda; [Começar em {instante}] e [Corrigir].
   Estilo ES5. */
(function (global) {
  "use strict";

  function leitor() { return global.LeitorDeComandos || (typeof require !== "undefined" ? require("./leitor.js") : null); }      // no navegador é o global; no node, o módulo irmão
  function formata(tpl, v) { return String(tpl == null ? "" : tpl).replace(/\{(\w+)\}/g, function (_, k) { return v && v[k] != null ? v[k] : "{" + k + "}"; }); }
  function arredonda2(x) { return Math.round(x * 100) / 100; }
  function dec(x) { return String(Math.round(x * 10) / 10).replace(".", ","); }
  function mmss(s) { s = Math.max(0, s); var m = Math.floor(s / 60), r = Math.floor(s % 60); return m + ":" + (r < 10 ? "0" : "") + r; }

  /** O relógio da tela no instante `elapsed` (s do início): o do round e, depois do plant, o da bomba. É a conta de `MapCore.relogio` (um teste confere as duas). */
  function relogioNa(real, elapsed) {
    if (real.plant_s !== null && elapsed >= real.plant_s) return mmss(real.bomba_s - (elapsed - real.plant_s));
    return mmss(real.segundos_do_round - elapsed);
  }

  /** O contexto do leitor para um round real. `ctxMapa` vem do Python (`contexto_do_real`: os pontos do mapa e os textos); aqui entram o elenco e os dados do round. */
  function contexto(ctxMapa, round, t0, R) {
    var hz = R.sample_hz, kill = {}, cont = { tr: 0, ct: 0 }, jogadores = [];
    var plant = (round.events || []).filter(function (e) { return e.type === "plant"; })[0];
    (round.events || []).forEach(function (e) { if (e.type === "kill" && !kill[e.victim]) kill[e.victim] = e; });
    round.players.forEach(function (p) {        // a ordem do round é a das colunas do banco: o "TR 2" é o segundo TR da coluna
      var lado = p.side === "ct" ? "ct" : "tr", k = kill[p.name], morreuF = null;
      if (k) morreuF = k.f;
      else for (var q = 0; q < p.alive.length; q++) if (!p.alive[q]) { morreuF = q; break; }
      jogadores.push({ lado: lado, num: ++cont[lado], nick: p.name, vivo: !!p.alive[t0], morreu_s: morreuF === null ? null : morreuF / hz, matador: k && k.attacker ? k.attacker : null });
    });
    var c = {};
    Object.keys(ctxMapa).forEach(function (k) { c[k] = ctxMapa[k]; });
    c.jogadores = jogadores;
    c.segundos_do_round = R.clock.round_seconds;
    c.real = { t0_f: t0, t0_s: t0 / hz, hz: hz, segundos_do_round: R.clock.round_seconds, bomba_s: R.clock.bomb_seconds, plant_s: plant ? plant.f / hz : null };
    return c;
  }

  function jogadorDe(ctx, lado, num) {
    return ctx.jogadores.filter(function (j) { return j.lado === lado && j.num === num; })[0] || null;
  }
  function rotuloDoJogador(j, ctx) {
    var TX = ctx.textos || {}, real = ctx.real, v = { nick: j.nick, lado: j.lado.toUpperCase(), num: j.num };
    if (j.vivo) return formata(TX["opcao_jogador_do_real"], v);
    v.estado = formata(TX["estado_morto"], { h: relogioNa(real, j.morreu_s), inicio: relogioNa(real, real.t0_s) });
    return formata(TX["opcao_jogador_morto"], v);
  }
  function noInstante(ctx) {
    var real = ctx.real, TX = ctx.textos || {};
    return { rotulo: formata(TX["opcao_no_instante"], { h: relogioNa(real, real.t0_s) }),
             valor: { quando: { tipo: "relogio", segundos_restantes: arredonda2(real.segundos_do_round - real.t0_s), t_decorrido: real.t0_s, base: "instante" } } };
  }

  /** O horário escrito (em segundos que faltam no relógio) cai depois do plant? Só então a pergunta "bomba ou round?" faz sentido: com o plant, a tela mostra o relógio da
      bomba (que não passa de `bomba_s`); antes do plant o horário é o do round, sem pergunta. */
  function caiDepoisDoPlant(real, restante) {
    return !!real && real.plant_s !== null && (real.segundos_do_round - restante) > real.plant_s && restante <= real.bomba_s;
  }
  function perguntaDoRelogio(ctx, indiceDaAcao, trecho, restante) {
    var real = ctx.real, TX = ctx.textos || {}, h = mmss(restante), depois = real.bomba_s - restante, elBomba = arredonda2(real.plant_s + depois), elRound = arredonda2(real.segundos_do_round - restante);
    return { codigo: "quando", campo: "quando", acao: indiceDaAcao, trecho: trecho || "", horario: h, _real: true,
             texto: formata(TX["pergunta_quando_relogio"], { h: h }),
             opcoes: [{ rotulo: formata(TX["opcao_relogio_bomba"], { h: h, n: depois, s: dec(elBomba) }), valor: { quando: { tipo: "relogio", segundos_restantes: restante, t_decorrido: elBomba, base: "bomba" } } },
                      { rotulo: formata(TX["opcao_relogio_round"], { h: h, s: dec(elRound) }), valor: { quando: { tipo: "relogio", segundos_restantes: restante, t_decorrido: elRound, base: "round" } } }] };
  }

  /** O que o leitor devolve, com o que é do round real: os rótulos de "quem" com nick e vida, o botão "No instante" na pergunta do horário e a pergunta "bomba ou round?". */
  function posprocessa(leitura, ctx) {
    leitura.perguntas.forEach(function (p) {
      if (p._real) return;
      if ((p.codigo === "quem" || p.codigo === "quem_lado" || p.codigo === "quem_funcao") && p.opcoes) {
        p.opcoes.forEach(function (o) { var j = jogadorDe(ctx, o.valor.lado, o.valor.num); if (j) o.rotulo = rotuloDoJogador(j, ctx); });
      }
      if (p.codigo === "quando" && p.opcoes && !p.opcoes.length) p.opcoes.push(noInstante(ctx));
      p._real = true;
    });
    leitura.acoes.forEach(function (ac) {
      var q = ac.quando;
      if (q && q.tipo === "relogio" && q.base === undefined && caiDepoisDoPlant(ctx.real, q.segundos_restantes)) {
        ac.quando = null;
        leitura.perguntas.push(perguntaDoRelogio(ctx, ac.indice, ac.trecho, q.segundos_restantes));
      }
    });
    leitura.perguntas.sort(function (a, b) { return (a.acao === null ? -1 : a.acao) - (b.acao === null ? -1 : b.acao); });      // por ação (a ordem de dentro da ação fica)
    leitura.ok = leitura.perguntas.length === 0 && leitura.acoes.length > 0 && !leitura.naoEntendido.length;
    return leitura;
  }

  function le(frase, ctx) {
    var l = leitor().le(frase, ctx);
    l._frase = frase; l._decisoes = ctx.decisoes || {};
    return posprocessa(l, ctx);
  }

  /** A resposta a uma pergunta. Devolve a leitura (use o valor devolvido: a resposta de "quem_ou_lugar" relê a frase com a decisão). */
  function responde(leitura, indice, valor, ctx) {
    var p = leitura.perguntas[indice];
    if (p && p.codigo === "quem_ou_lugar") {
      var d = {};
      Object.keys(leitura._decisoes || {}).forEach(function (k) { d[k] = leitura._decisoes[k]; });
      d[valor.chave] = valor.decisao;
      var c2 = {};
      Object.keys(ctx).forEach(function (k) { c2[k] = ctx[k]; });
      c2.decisoes = d;
      var nova = leitor().le(leitura._frase, c2);
      nova._frase = leitura._frase; nova._decisoes = d;
      return posprocessa(nova, c2);
    }
    return posprocessa(leitor().responde(leitura, indice, valor, ctx), ctx);
  }

  /** O horário digitado sozinho (a resposta à pergunta "quando?"): como o do leitor, mais a pergunta "bomba ou round?" quando cai depois do plant. */
  function horario(texto, ctx) {
    var r = leitor().horario(texto, ctx);
    if (r && r.tipo === "relogio" && r.base === undefined && caiDepoisDoPlant(ctx.real, r.segundos_restantes))
      return { ambiguo_relogio: true, segundos_restantes: r.segundos_restantes, pergunta: perguntaDoRelogio(ctx, null, texto, r.segundos_restantes) };
    return r;
  }

  /** O fim do comando que o próprio comando diz: "em 8 s" (duração imposta) ou "espera 5 segundos". Os outros (mover, lançar) o plano calcula e entrega em `fins`. */
  function fimDoComando(ac, T, fins) {
    if (fins && typeof fins[ac.indice] === "number") return fins[ac.indice];
    if (ac.duracao_s != null) return T + ac.duracao_s;
    if (ac.tipo === "esperar" && ac.espera_s != null) return T + ac.espera_s;
    return null;
  }

  function veredictoDe(ac, j, T, fim, ctx) {
    var real = ctx.real, TX = ctx.textos || {}, ini = relogioNa(real, real.t0_s);
    var base = { acao: ac.indice, lado: j.lado, num: j.num, nick: j.nick };
    var v = { nick: j.nick, matador: j.matador, h_cmd: relogioNa(real, T), inicio: ini, h_morte: j.morreu_s === null ? "" : relogioNa(real, j.morreu_s) };
    var sufixo = j.matador ? "" : "_sem_matador";
    var botoesRecusa = [{ codigo: "outro_jogador", rotulo: TX["botao_outro_jogador"] }, { codigo: "corrigir", rotulo: TX["botao_corrigir"] }];
    function com(codigo, aplica, chaveDoTexto, botoes, extra) {
      var r = { acao: base.acao, lado: base.lado, num: base.num, nick: base.nick, codigo: codigo, aplica: aplica, texto: formata(TX[chaveDoTexto], v), botoes: botoes };
      Object.keys(extra || {}).forEach(function (k) { r[k] = extra[k]; });
      return r;
    }
    if (!j.vivo) return com("ja_morto", false, "veredicto_ja_morto" + sufixo, botoesRecusa, { morte: { s: j.morreu_s, h: v.h_morte, matador: j.matador } });
    if (T < real.t0_s - 1e-9) return com("antes_do_instante", false, "veredicto_antes_do_instante",
      [{ codigo: "comecar_em", rotulo: formata(TX["botao_comecar_em"], { inicio: ini }) }, { codigo: "corrigir", rotulo: TX["botao_corrigir"] }], { instante_s: real.t0_s });
    if (j.morreu_s !== null && T >= j.morreu_s) return com("comeca_depois_da_morte", false, "veredicto_comeca_depois_da_morte" + sufixo, botoesRecusa, { morte: { s: j.morreu_s, h: v.h_morte, matador: j.matador } });
    if (j.morreu_s !== null && fim !== null && fim > j.morreu_s) return com("termina_depois_da_morte", true, "veredicto_termina_depois_da_morte" + sufixo, [], { esmaece_em_s: j.morreu_s, fim_s: fim, morte: { s: j.morreu_s, h: v.h_morte, matador: j.matador } });
    return { acao: base.acao, lado: base.lado, num: base.num, nick: base.nick, codigo: "ok", aplica: true, texto: "", botoes: [] };
  }

  /** O que o round real diz de cada comando (por ação e jogador): `ok`, `termina_depois_da_morte` (aplicado, com aviso), ou recusado (`comeca_depois_da_morte`, `ja_morto`,
      `antes_do_instante`). `pendente`: ainda há pergunta nesta ação, ou o horário não é um relógio explícito ("depois", "junto": o plano o calcula e a CR2 repete a conta). */
  function veredictos(leitura, ctx, fins) {
    var out = [];
    leitura.acoes.forEach(function (ac) {
      var pendente = leitura.perguntas.some(function (p) { return p.acao === ac.indice; }), q = ac.quando;
      var T = q && (q.tipo === "relogio" || q.tipo === "inicio") ? q.t_decorrido : null;
      if (pendente || !ac.quem.length || T === null) { out.push({ acao: ac.indice, codigo: "pendente", aplica: false, texto: "", botoes: [] }); return; }
      ac.quem.forEach(function (s) {
        var j = s.resolvido ? jogadorDe(ctx, s.lado, s.num) : null;
        if (!j) { out.push({ acao: ac.indice, codigo: "pendente", aplica: false, texto: "", botoes: [] }); return; }
        out.push(veredictoDe(ac, j, T, fimDoComando(ac, T, fins), ctx));
      });
    });
    return out;
  }

  /** [Escolher outro jogador]: o jogador recusado sai do comando e a pergunta "quem?" volta, com todos os rótulos (nick, lado, número e vida). */
  function escolherOutro(leitura, indiceDaAcao, ref, ctx) {
    var ac = leitura.acoes[indiceDaAcao], TX = ctx.textos || {}, ix = -1;
    if (!ac) return leitura;
    ac.quem.forEach(function (s, i) { if (ix < 0 && s.lado === ref.lado && s.num === ref.num) ix = i; });
    if (ix < 0) return leitura;
    var antigo = ac.quem[ix];
    ac.quem[ix] = { lado: null, num: null, funcao: null, ref: antigo.ref, resolvido: false, candidatos: [] };
    leitura.perguntas.push({ codigo: "quem", campo: "quem", acao: indiceDaAcao, indice_quem: ix, ref: antigo.ref, _real: true, texto: formata(TX["pergunta_quem"], { trecho: ac.trecho }),
                             opcoes: ctx.jogadores.map(function (j) { return { rotulo: rotuloDoJogador(j, ctx), valor: { lado: j.lado, num: j.num } }; }) });
    return posprocessa(leitura, ctx);
  }

  /** [Começar em {instante}]: o comando que vinha antes do instante passa a começar nele. */
  function comecarNoInstante(leitura, indiceDaAcao, ctx) {
    var ac = leitura.acoes[indiceDaAcao];
    if (ac) ac.quando = noInstante(ctx).valor.quando;
    return posprocessa(leitura, ctx);
  }

  global.ComandosDoReal = { contexto: contexto, le: le, responde: responde, horario: horario, veredictos: veredictos, escolherOutro: escolherOutro, comecarNoInstante: comecarNoInstante, relogioNa: relogioNa };
  if (typeof module !== "undefined" && module.exports) module.exports = global.ComandosDoReal;
})(typeof window !== "undefined" ? window : this);
