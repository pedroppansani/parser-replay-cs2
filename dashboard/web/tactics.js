/* =========================================================================
   Prancheta tática: peças com direção, granadas com origem e destino, desenho
   livre, passos numerados, andares, zoom, tela cheia e desfazer/refazer.

   O modelo é o de metrics/tactics.py (lá está o PORQUÊ, com calma): a tática é
   um LOG DE OPERAÇÕES com id estável, autor e número de ordem, e o estado é
   derivado aplicando o log em ordem (seq, autor, id). Este arquivo é o espelho
   daquele módulo -- há teste que aplica o mesmo log nos dois e compara o estado
   e o quadro de cada passo.

   Desfazer e refazer NÃO apagam nada: emitem `anula` e `reativa` sobre uma
   operação do próprio autor. Um mecanismo só para toda operação, e a mescla
   por união continua convergindo.

   Tudo em coordenada de JOGO. A tela só projeta, pelo MapCore (map_core.js),
   o mesmo núcleo do replay e da anotação: projeção, zoom, tamanho do canvas,
   desenho do jogador, símbolo e área das granadas, traço e seletor de cor.

   A persistência fica atrás de `Armazem` (lista / carrega / grava / apaga).
   Hoje é o navegador; um servidor entra implementando os mesmos quatro métodos.
   ========================================================================= */
var Prancheta = (function () {
  "use strict";

  /* ---------------------------------------------------------------------
     Constantes do modelo -- as mesmas de metrics/tactics.py
     --------------------------------------------------------------------- */
  var IDENTIFICADOR = "prancheta-cs2";
  var FORMATO = 2;
  var VERSOES_ACEITAS = [1, 2];
  var LADOS = ["ct", "t"];
  var PECAS_POR_LADO = 5;
  var ARMAS = ["smoke", "flash", "he", "molotov", "decoy"];
  var NOME_ARMA = { smoke: "Smoke", flash: "Flash", he: "HE", molotov: "Molotov", decoy: "Decoy" };
  // Padrões do formato 2 -- convenção de interface, não dado de jogo.
  var DURACAO_PADRAO_S = 2.0;
  var VIDA_PADRAO_GRANADA = { smoke: null, molotov: 1, flash: 1, he: 1, decoy: 1 };
  var VIDA_PADRAO_TRACO = 1;
  var CASAS_DIRECAO_PADRAO = 1;
  var DESFAZER = ["anula", "reativa"];
  var OPERACOES = {
    renomeia: ["titulo"], cria_passo: ["passo", "titulo"], renomeia_passo: ["passo", "titulo"],
    remove_passo: ["passo"], cria_peca: ["peca", "lado", "rotulo", "passo", "x", "y"],
    move_peca: ["peca", "passo", "x", "y"], remove_peca: ["peca"],
    cria_granada: ["granada", "arma", "passo", "origem", "destino"],
    move_granada: ["granada", "origem", "destino"], remove_granada: ["granada"],
    gira_peca: ["peca", "passo", "yaw"], tira_peca: ["peca", "passo"],
    cria_traco: ["traco", "passo", "ferramenta", "cor", "espessura", "pontos"],
    remove_traco: ["traco"], define_duracao: ["passo", "segundos"],
    define_vida: ["alvo", "dura_passos"], anula: ["alvo"], reativa: ["alvo"]
  };

  // Desenho livre: o formato e as regras do traço são os de
  // metrics/annotations.py (há teste conferindo estas duas listas contra ele).
  var FERRAMENTAS_TRACO = ["caneta", "seta", "linha", "retangulo", "elipse", "texto"];
  var ESPESSURAS = [2, 4, 7];
  var ROTULOS_ESPESSURA = ["fina", "média", "grossa"];
  var ROTULO_FERRAMENTA = { caneta: "Caneta", seta: "Seta", linha: "Linha", retangulo: "Retângulo",
                            elipse: "Elipse", texto: "Texto", borracha: "Borracha" };
  var COR_PADRAO = "#eb6834";
  var MAX_RECENTES = 6;
  var CHAVE_RECENTES = "anot:cores-recentes";   // as mesmas recentes da anotação

  // Tamanhos em PIXEL DO RADAR (1024 de lado): a peça cresce e encolhe junto com
  // o mapa. A peça é o jogador do replay (MapCore.desenhaJogador) em escala
  // maior, para dar para pegar com o mouse: halo de 8,2 no replay, 15 aqui.
  var RAIO_PECA = 15;
  var ESCALA_PECA = RAIO_PECA / 8.2;
  var RAIO_ALCA = 7;            // alça de girar, na ponta da direção
  var RAIO_GRANADA = 8;         // símbolo da granada no destino
  var RAIO_PONTA_GRANADA = 9;   // pegar a ponta da granada para arrastar
  var RAIO_BORRACHA = 10;       // o mesmo da anotação
  var PASSO_MIN_CANETA = 1.5;   // o mesmo da anotação
  var ALFA_OUTRO_ANDAR = 0.35;  // elemento de outro andar: esmaecido, como no replay
  var ALFA_RASTRO = 0.3;        // posição e direção do passo anterior

  // Giro pela roda do mouse: 15° por clique, 1° com Shift. Giros seguidos viram
  // UMA operação depois de 300 ms parado -- senão cada clique da roda seria uma
  // linha no log e um passo no desfazer.
  var PASSO_GIRO = 15, PASSO_GIRO_FINO = 1, MS_AGRUPA_GIRO = 300;

  // Raio da busca "quero a granada AQUI", em unidade de jogo. É parâmetro de
  // TELA, não de métrica: a pessoa ajusta no controle ao lado da busca.
  var RAIO_BUSCA_PADRAO = 200;
  var MAX_RESULTADOS = 40;

  // Reprodução -- convenção de interface. Dentro do passo, cada granada nova
  // usa a primeira FRACAO_LINHA da sua janela para riscar a linha do arremesso
  // e o resto para abrir o efeito; o que acaba de viver some na primeira
  // FRACAO_SAIDA do passo seguinte.
  var FRACAO_LINHA = 0.5;
  var FRACAO_SAIDA = 0.25;

  var ATRASO_GRAVACAO_MS = 400;
  // Uma tática nova nasce com duas operações (título e primeiro passo). Com só
  // elas, ela é VAZIA e não entra na biblioteca -- senão cada visita à página
  // deixaria uma "Nova tática" a mais na lista.
  var OPS_DA_CRIACAO = 2;

  /* ---------------------------------------------------------------------
     Modelo -- espelho de metrics/tactics.py
     --------------------------------------------------------------------- */
  function chaveDeOrdem(a, b) {
    if (a.seq !== b.seq) return a.seq - b.seq;
    if (a.autor !== b.autor) return a.autor < b.autor ? -1 : 1;
    if (a.id !== b.id) return a.id < b.id ? -1 : 1;
    return 0;
  }
  function ordemDe(op) { return [op.seq, String(op.autor), String(op.id)]; }
  function copia(v) { return JSON.parse(JSON.stringify(v)); }
  function tem(o, k) { return Object.prototype.hasOwnProperty.call(o, k); }

  /** Ids das operações desfeitas agora: para cada alvo vale a ÚLTIMA
      anula/reativa. Inválida (outro autor, alvo que é anula/reativa, alvo fora
      do log) não vale. */
  function anuladas(operacoes) {
    var porId = {}, ultima = {};
    operacoes.forEach(function (op) { porId[op.id] = op; });
    operacoes.slice().sort(chaveDeOrdem).forEach(function (op) {
      if (DESFAZER.indexOf(op.tipo) < 0) return;
      var alvo = porId[op.alvo];
      if (!alvo || DESFAZER.indexOf(alvo.tipo) >= 0 || alvo.autor !== op.autor) return;
      ultima[alvo.id] = op.tipo;
    });
    var fora = {};
    Object.keys(ultima).forEach(function (k) { if (ultima[k] === "anula") fora[k] = true; });
    return fora;
  }

  function aplica(operacoes) {
    var fora = anuladas(operacoes);
    var estado = { titulo: "", passos: [], pecas: {}, granadas: {}, tracos: {} };
    var passos = {}, ordem = [];
    operacoes.slice().sort(chaveDeOrdem).forEach(function (op) {
      if (fora[op.id]) return;
      var p, g, alvo;
      switch (op.tipo) {
        case "renomeia": estado.titulo = op.titulo; break;
        case "cria_passo":
          if (!passos[op.passo]) {
            passos[op.passo] = { passo: op.passo, titulo: op.titulo, duracao_s: DURACAO_PADRAO_S };
            ordem.push(op.passo);
          }
          break;
        case "renomeia_passo": if (passos[op.passo]) passos[op.passo].titulo = op.titulo; break;
        case "define_duracao": if (passos[op.passo]) passos[op.passo].duracao_s = +op.segundos; break;
        case "remove_passo":
          if (passos[op.passo]) { delete passos[op.passo]; ordem.splice(ordem.indexOf(op.passo), 1); }
          break;
        case "cria_peca":
          if (!estado.pecas[op.peca] && passos[op.passo]) {
            p = { lado: op.lado, rotulo: op.rotulo, criada_em_ordem: ordemDe(op),
                  posicoes: {}, niveis: {}, direcoes: {} };
            p.posicoes[op.passo] = [+op.x, +op.y];
            p.niveis[op.passo] = tem(op, "nivel") ? +op.nivel : 0;
            if (op.yaw !== undefined && op.yaw !== null) p.direcoes[op.passo] = +op.yaw;
            estado.pecas[op.peca] = p;
          }
          break;
        case "move_peca":
          p = estado.pecas[op.peca];
          if (p && passos[op.passo]) {
            p.posicoes[op.passo] = [+op.x, +op.y];
            p.niveis[op.passo] = tem(op, "nivel") ? +op.nivel : 0;
          }
          break;
        case "gira_peca":
          p = estado.pecas[op.peca];
          if (p && passos[op.passo]) p.direcoes[op.passo] = +op.yaw;
          break;
        case "tira_peca":
          p = estado.pecas[op.peca];
          if (p && passos[op.passo]) { p.posicoes[op.passo] = null; delete p.niveis[op.passo]; }
          break;
        case "remove_peca": delete estado.pecas[op.peca]; break;
        case "cria_granada":
          if (!estado.granadas[op.granada] && passos[op.passo]) {
            estado.granadas[op.granada] = {
              arma: op.arma, passo: op.passo,
              origem: op.origem.map(Number), destino: op.destino.map(Number),
              nivel: tem(op, "nivel") ? +op.nivel : 0,
              arremesso: op.arremesso === undefined ? null : op.arremesso,
              dura_passos: tem(op, "dura_passos") ? op.dura_passos : VIDA_PADRAO_GRANADA[op.arma],
              criada_em_ordem: ordemDe(op)
            };
            // o campo só existe quando é verdade (espelho do Python)
            if (op.origem_desconhecida === true) estado.granadas[op.granada].origem_desconhecida = true;
          }
          break;
        case "move_granada":
          g = estado.granadas[op.granada];
          if (g) {
            g.origem = op.origem.map(Number); g.destino = op.destino.map(Number);
            g.nivel = tem(op, "nivel") ? +op.nivel : 0;
            g.arremesso = null;   // arrastada à mão deixou de ser o arremesso real
            delete g.origem_desconhecida;
          }
          break;
        case "remove_granada": delete estado.granadas[op.granada]; break;
        case "cria_traco":
          if (!estado.tracos[op.traco] && passos[op.passo]) {
            estado.tracos[op.traco] = {
              passo: op.passo, ferramenta: op.ferramenta, cor: op.cor, espessura: op.espessura,
              pontos: op.pontos.map(function (q) { return [+q[0], +q[1]]; }),
              texto: op.texto === undefined ? null : op.texto,
              nivel: tem(op, "nivel") ? +op.nivel : 0,
              dura_passos: tem(op, "dura_passos") ? op.dura_passos : VIDA_PADRAO_TRACO,
              criada_em_ordem: ordemDe(op)
            };
          }
          break;
        case "remove_traco": delete estado.tracos[op.traco]; break;
        case "define_vida":
          alvo = estado.granadas[op.alvo] || estado.tracos[op.alvo];
          if (alvo) alvo.dura_passos = op.dura_passos;
          break;
      }
    });
    estado.passos = ordem.map(function (k) { return passos[k]; });
    Object.keys(estado.pecas).forEach(function (k) {
      ["posicoes", "niveis", "direcoes"].forEach(function (campo) {
        var m = estado.pecas[k][campo], limpo = {};
        Object.keys(m).forEach(function (s) { if (passos[s]) limpo[s] = m[s]; });
        estado.pecas[k][campo] = limpo;
      });
    });
    ["granadas", "tracos"].forEach(function (grupo) {
      Object.keys(estado[grupo]).forEach(function (k) {
        if (!passos[estado[grupo][k].passo]) delete estado[grupo][k];
      });
    });
    return estado;
  }

  function posicaoNoPasso(peca, passos, indice) {
    var pos = null;
    for (var i = 0; i <= indice && i < passos.length; i++) {
      if (tem(peca.posicoes, passos[i].passo)) pos = peca.posicoes[passos[i].passo];
    }
    return pos;
  }

  function centroDoRadar(r) {
    return [r.width / 2 / r.scale_px_per_unit + r.origin_x, r.origin_y - r.height / 2 / r.scale_px_per_unit];
  }

  /** Da peça para o centro do radar, em graus do CS2, em [0, 360), arredondado
      como no Python (meio para cima, CASAS_DIRECAO_PADRAO casas). */
  function direcaoPadrao(x, y, centro) {
    var ang = Math.atan2(centro[1] - y, centro[0] - x) * (180 / Math.PI);
    ang = ((ang % 360) + 360) % 360;
    var k = Math.pow(10, CASAS_DIRECAO_PADRAO);
    return (Math.floor(ang * k + 0.5) / k) % 360;
  }

  function visivel(nasce, dura, i) { return nasce <= i && (dura === null || dura === undefined || i < nasce + dura); }

  function quadroDoPasso(estado, i, centro) {
    var passos = estado.passos, indice = {};
    passos.forEach(function (p, k) { indice[p.passo] = k; });
    var pecas = {};
    Object.keys(estado.pecas).forEach(function (pid) {
      var p = estado.pecas[pid], pos = null, nivel = 0, yaw = null;
      for (var k = 0; k <= i && k < passos.length; k++) {
        var s = passos[k].passo;
        if (tem(p.posicoes, s)) { pos = p.posicoes[s]; nivel = tem(p.niveis, s) ? p.niveis[s] : 0; }
        if (tem(p.direcoes, s)) yaw = p.direcoes[s];
      }
      if (pos === null) return;
      var padrao = yaw === null;
      pecas[pid] = { lado: p.lado, rotulo: p.rotulo, x: pos[0], y: pos[1], nivel: nivel,
                     yaw: padrao ? direcaoPadrao(pos[0], pos[1], centro) : yaw, direcao_padrao: padrao };
    });
    function vivos(grupo) {
      var out = {};
      Object.keys(estado[grupo]).forEach(function (id) {
        var e = estado[grupo][id], nasce = indice[e.passo];
        if (visivel(nasce, e.dura_passos, i)) {
          out[id] = Object.assign({}, e, { nasceu_neste_passo: nasce === i });
        }
      });
      return out;
    }
    return { indice: i, passo: passos[i].passo, titulo: passos[i].titulo, duracao_s: passos[i].duracao_s,
             pecas: pecas, granadas: vivos("granadas"), tracos: vivos("tracos") };
  }

  /* ---------------------------------------------------------------------
     Reprodução -- FUNÇÃO PURA DO TEMPO
     O passo k ocupa o intervalo (início_k, início_k + duração_k] da linha do
     tempo (o primeiro inclui o 0). Durante ele as peças vão do passo k-1 ao k,
     e em t = fim do intervalo o quadro é exatamente quadro_do_passo(k). Não há
     estado de "onde a animação estava": arrastar a barra até t e tocar até t
     chamam a mesma função com o mesmo t.
     --------------------------------------------------------------------- */
  function linhaDoTempo(estado) {
    var inicios = [], total = 0;
    estado.passos.forEach(function (p) { inicios.push(total); total += p.duracao_s; });
    return { inicios: inicios, total: total };
  }

  // Entrada e saída suaves (smoothstep): começa e termina parado.
  function suave(u) { return u <= 0 ? 0 : u >= 1 ? 1 : u * u * (3 - 2 * u); }
  function entre(v) { return Math.max(0, Math.min(1, v)); }

  function tracoParcial(t, p) {
    var n = t.pontos.length, pontos;
    if (t.ferramenta === "caneta") pontos = t.pontos.slice(0, Math.max(1, Math.ceil(p * n)));
    else if (n >= 2) {
      var a = t.pontos[0], b = t.pontos[n - 1];
      pontos = p >= 1 ? t.pontos.slice() : [a, [a[0] + (b[0] - a[0]) * p, a[1] + (b[1] - a[1]) * p]];
    } else pontos = t.pontos.slice();
    return pontos;
  }

  function estadoNoTempo(estado, t, centro) {
    var lt = linhaDoTempo(estado), n = estado.passos.length;
    t = Math.max(0, Math.min(lt.total, t));
    var k = 0;
    while (k < n - 1 && t > lt.inicios[k] + estado.passos[k].duracao_s) k++;
    var dur = estado.passos[k].duracao_s;
    var u = dur > 0 ? entre((t - lt.inicios[k]) / dur) : 1;
    var qk = quadroDoPasso(estado, k, centro), qp = k > 0 ? quadroDoPasso(estado, k - 1, centro) : qk;
    var e = suave(u);

    var pecas = {};
    Object.keys(Object.assign({}, qp.pecas, qk.pecas)).forEach(function (id) {
      var a = qp.pecas[id], b = qk.pecas[id], p;
      if (a && b) {
        if (e >= 1) p = Object.assign({}, b);
        else if (e <= 0) p = Object.assign({}, a);
        else if (a.nivel !== b.nivel) p = Object.assign({}, u < 0.5 ? a : b);   // troca de andar não interpola
        else {
          p = Object.assign({}, b, { x: a.x + (b.x - a.x) * e, y: a.y + (b.y - a.y) * e,
                                     yaw: MapCore.interpolaAngulo(a.yaw, b.yaw, e) });
        }
        p.alfa = 1;
      } else if (b) { p = Object.assign({}, b, { alfa: e }); }        // entra aos poucos
      else { p = Object.assign({}, a, { alfa: 1 - e }); }             // sai aos poucos
      if (p.alfa > 0) pecas[id] = p;
    });

    // o que nasce neste passo aparece em ordem de criação, repartindo o passo
    var nascem = ordemDeCriacao(estado).filter(function (x) {
      var grupo = x.tipo === "granada" ? qk.granadas : qk.tracos;
      return grupo[x.id] && grupo[x.id].nasceu_neste_passo;
    });
    var janela = {};
    nascem.forEach(function (x, j) { janela[x.id] = entre((u - j / nascem.length) * nascem.length); });

    var granadas = {}, tracos = {};
    Object.keys(qk.granadas).forEach(function (id) {
      var g = qk.granadas[id];
      if (g.nasceu_neste_passo) {
        var p = janela[id];
        if (p <= 0) return;
        // sem origem conhecida não há linha: a janela inteira abre o efeito
        granadas[id] = g.origem_desconhecida
          ? Object.assign({}, g, { linha: 0, efeito: p, alfa: 1 })
          : Object.assign({}, g, { linha: entre(p / FRACAO_LINHA),
              efeito: entre((p - FRACAO_LINHA) / (1 - FRACAO_LINHA)), alfa: 1 });
      } else granadas[id] = Object.assign({}, g, { linha: 0, efeito: 1, alfa: 1 });
    });
    Object.keys(qk.tracos).forEach(function (id) {
      var tr = qk.tracos[id];
      if (tr.nasceu_neste_passo) {
        var p = janela[id];
        if (p <= 0) return;
        tracos[id] = Object.assign({}, tr, { pontos: tracoParcial(tr, p), progresso: p, alfa: 1 });
      } else tracos[id] = Object.assign({}, tr, { progresso: 1, alfa: 1 });
    });
    // o que acabou de viver some no começo do passo
    var saida = 1 - entre(u / FRACAO_SAIDA);
    if (k > 0 && saida > 0) {
      Object.keys(qp.granadas).forEach(function (id) {
        if (!qk.granadas[id]) granadas[id] = Object.assign({}, qp.granadas[id], { linha: 0, efeito: 1, alfa: saida });
      });
      Object.keys(qp.tracos).forEach(function (id) {
        if (!qk.tracos[id]) tracos[id] = Object.assign({}, qp.tracos[id], { progresso: 1, alfa: saida });
      });
    }
    return { t: t, total: lt.total, indice: k, u: u, passo: qk.passo, titulo: qk.titulo,
             pecas: pecas, granadas: granadas, tracos: tracos };
  }

  function ordemDeCriacao(estado) {
    var itens = [];
    Object.keys(estado.granadas).forEach(function (k) { itens.push(["granada", k, estado.granadas[k]]); });
    Object.keys(estado.tracos).forEach(function (k) { itens.push(["traco", k, estado.tracos[k]]); });
    itens.sort(function (a, b) {
      var x = a[2].criada_em_ordem, y = b[2].criada_em_ordem;
      return chaveDeOrdem({ seq: x[0], autor: x[1], id: x[2] }, { seq: y[0], autor: y[1], id: y[2] });
    });
    return itens.map(function (t) { return { tipo: t[0], id: t[1], passo: t[2].passo }; });
  }

  function mescla(a, b) {
    if (a.id !== b.id) throw new Error("mesclar táticas diferentes: ids distintos");
    var porId = {};
    a.operacoes.forEach(function (op) { porId[op.id] = op; });
    b.operacoes.forEach(function (op) { if (!porId[op.id]) porId[op.id] = op; });
    var saida = copia(a);
    saida.operacoes = Object.keys(porId).map(function (k) { return porId[k]; }).sort(chaveDeOrdem);
    saida.contador = Math.max(a.contador, b.contador);
    saida.versao = FORMATO;
    return saida;
  }

  /** Formato 1 -> atual, em memória: só a versão muda. */
  function migra(doc) {
    var d = Object.assign({}, doc);
    d.versao = FORMATO;
    return d;
  }

  function ehInteiro(v) { return typeof v === "number" && isFinite(v) && Math.floor(v) === v; }
  function ehNumero(v) { return typeof v === "number" && isFinite(v); }

  /** Os problemas do arquivo, todos de uma vez -- as mesmas regras de
      metrics.tactics.problemas, para a importação recusar o que o Python
      recusaria. */
  function problemas(doc, andares) {
    if (!doc || doc.formato !== IDENTIFICADOR) return ["não é um arquivo de tática da prancheta"];
    if (VERSOES_ACEITAS.indexOf(doc.versao) < 0) {
      return ["versão " + doc.versao + " do formato; esta página lê as versões " + VERSOES_ACEITAS.join(", ")];
    }
    var erros = [];
    ["id", "mapa", "criada_por", "criada_em", "contador", "operacoes", "calibracao"].forEach(function (c) {
      if (!tem(doc, c)) erros.push("falta o campo '" + c + "'");
    });
    if (doc.origem !== undefined && doc.origem !== null) erros = erros.concat(problemasDaOrigem(doc.origem));
    if (!Array.isArray(doc.operacoes)) return erros;
    var porId = {}, vistos = {}, maior = 0;
    doc.operacoes.forEach(function (op) { if (op && op.id) porId[op.id] = op; });
    doc.operacoes.forEach(function (op, n) {
      var onde = "operação " + n + " (" + (op && op.tipo) + ")";
      if (!op || !op.id || !op.tipo || !op.autor || !tem(op, "seq") || !tem(op, "em")) {
        erros.push("operação " + n + " incompleta"); return;
      }
      if (!OPERACOES[op.tipo]) { erros.push("operação desconhecida: " + op.tipo); return; }
      var sem = OPERACOES[op.tipo].filter(function (c) { return !tem(op, c); });
      sem.forEach(function (c) { erros.push("'" + op.tipo + "' sem '" + c + "'"); });
      if (vistos[op.id]) erros.push("operação repetida: " + op.id);
      vistos[op.id] = true;
      if (!ehInteiro(op.seq) || op.seq < 1) erros.push(onde + ": número de ordem inválido");
      else maior = Math.max(maior, op.seq);
      if (sem.length) return;
      if (op.tipo === "cria_peca" && LADOS.indexOf(op.lado) < 0) erros.push(onde + ": lado desconhecido: " + op.lado);
      if ((op.tipo === "cria_peca" || op.tipo === "gira_peca") && op.yaw !== undefined && op.yaw !== null &&
          !(ehNumero(op.yaw) && op.yaw >= 0 && op.yaw < 360)) erros.push(onde + ": yaw fora de [0, 360)");
      if (tem(op, "nivel")) {
        if (!ehInteiro(op.nivel) || op.nivel < 0) erros.push(onde + ": nivel não é um andar");
        else if (op.nivel >= andares) erros.push(onde + ": nivel " + op.nivel + " num mapa de " + andares + " andar(es)");
      }
      if (tem(op, "dura_passos") && op.dura_passos !== null && !(ehInteiro(op.dura_passos) && op.dura_passos >= 1)) {
        erros.push(onde + ": dura_passos não é inteiro >= 1 nem null");
      }
      if (op.tipo === "define_duracao" && !(ehNumero(op.segundos) && op.segundos > 0)) erros.push(onde + ": duração não é positiva");
      if (op.tipo === "cria_granada" && ARMAS.indexOf(op.arma) < 0) erros.push(onde + ": granada desconhecida: " + op.arma);
      if (op.tipo === "cria_granada" && tem(op, "origem_desconhecida")) {
        if (typeof op.origem_desconhecida !== "boolean") erros.push(onde + ": origem_desconhecida não é verdadeiro/falso");
        else if (op.origem_desconhecida) {
          if (op.origem[0] !== op.destino[0] || op.origem[1] !== op.destino[1]) erros.push(onde + ": origem desconhecida exige origem igual ao destino");
          if (op.arremesso) erros.push(onde + ": origem desconhecida não combina com arremesso real");
        }
      }
      if (op.tipo === "cria_traco") {
        if (FERRAMENTAS_TRACO.indexOf(op.ferramenta) < 0) erros.push(onde + ": ferramenta desconhecida");
        if (!/^#[0-9a-f]{6}$/.test(String(op.cor))) erros.push(onde + ": cor fora do formato #rrggbb");
        if (ESPESSURAS.indexOf(op.espessura) < 0) erros.push(onde + ": espessura fora de " + ESPESSURAS.join("/"));
        if (!Array.isArray(op.pontos) || !op.pontos.length) erros.push(onde + ": sem pontos");
      }
      if (DESFAZER.indexOf(op.tipo) >= 0) {
        var alvo = porId[op.alvo];
        if (!alvo) erros.push(onde + ": mira operação que não está no log");
        else if (DESFAZER.indexOf(alvo.tipo) >= 0) erros.push(onde + ": mira outra " + alvo.tipo);
        else if (alvo.autor !== op.autor) erros.push(onde + ": cada um só desfaz o que é seu");
      }
    });
    if (ehInteiro(doc.contador) && doc.contador < maior) erros.push("o contador está abaixo do maior número de ordem do log");
    return erros;
  }

  /** Espelho de metrics.tactics.problemas_da_origem. */
  function problemasDaOrigem(o) {
    if (!o || typeof o !== "object" || Array.isArray(o)) return ["origem: não é um objeto"];
    var erros = [];
    if (typeof o.partida !== "string") erros.push("origem: partida ausente");
    if (!ehInteiro(o.round) || o.round < 1) erros.push("origem: round inválido");
    if (!ehInteiro(o.quadro) || o.quadro < 0) erros.push("origem: quadro inválido");
    if (typeof o.relogio !== "string") erros.push("origem: relógio ausente");
    if (!Array.isArray(o.elenco) || !o.elenco.length) return erros.concat(["origem: elenco ausente"]);
    var nomes = {};
    o.elenco.forEach(function (j) {
      if (!j || typeof j.nome !== "string" || !j.nome || LADOS.indexOf(j.lado) < 0) {
        erros.push("origem: jogador do elenco inválido"); return;
      }
      if (tem(nomes, j.nome)) erros.push("origem: " + j.nome + " repetido no elenco");
      nomes[j.nome] = j.lado;
    });
    LADOS.forEach(function (lado) {
      var n = Object.keys(nomes).filter(function (k) { return nomes[k] === lado; }).length;
      if (n > PECAS_POR_LADO) erros.push("origem: mais de " + PECAS_POR_LADO + " jogadores de " + lado + " no elenco");
    });
    var mortos = o.mortos === undefined ? [] : o.mortos;
    if (!Array.isArray(mortos)) return erros.concat(["origem: mortos não é uma lista"]);
    var ordens = {};
    mortos.forEach(function (m) {
      if (!m || !tem(nomes, m.nome) || nomes[m.nome] !== m.lado) { erros.push("origem: morto fora do elenco"); return; }
      if (!ehInteiro(m.ordem) || m.ordem < 1 || ordens[m.ordem]) erros.push("origem: ordem de morte inválida para " + m.nome);
      else ordens[m.ordem] = true;
    });
    return erros;
  }

  /** Placar de vivos no instante, sempre TR antes de CT ("4v3"). */
  function placarDeVivos(origem) {
    var vivos = { t: 0, ct: 0 }, mortos = {};
    (origem.mortos || []).forEach(function (m) { mortos[m.nome] = true; });
    origem.elenco.forEach(function (j) { if (!mortos[j.nome]) vivos[j.lado]++; });
    return vivos;
  }

  /** Texto do instante de origem, montado aqui a partir do metadado. */
  function textoDaOrigem(origem) {
    var v = placarDeVivos(origem);
    var linhas = ["Instante do replay: " + origem.partida + ", round " + origem.round + ", " + origem.relogio +
                  " (quadro " + origem.quadro + "). Vivos: " + v.t + " TR contra " + v.ct + " CT."];
    var mortos = (origem.mortos || []).slice().sort(function (a, b) { return a.ordem - b.ordem; });
    if (mortos.length) {
      [["t", "TR"], ["ct", "CT"]].forEach(function (par) {
        var doLado = mortos.filter(function (m) { return m.lado === par[0]; });
        if (doLado.length) {
          linhas.push("Mortos " + par[1] + ": " + doLado.map(function (m) { return m.nome + " (" + m.ordem + "ª morte)"; }).join(", ") + ".");
        }
      });
    } else linhas.push("Ninguém tinha morrido ainda.");
    return linhas.join(" ");
  }

  function novoId() {
    if (window.crypto && crypto.randomUUID) return crypto.randomUUID().replace(/-/g, "");
    var s = "";
    for (var i = 0; i < 32; i++) s += Math.floor(Math.random() * 16).toString(16);
    return s;
  }
  function agora() { return new Date().toISOString(); }

  /* ---------------------------------------------------------------------
     Armazem -- a interface de persistência. A página só fala com isto.
     Contrato:
       lista(mapa)  -> [{id, titulo, atualizada_em, autores}]  (mais recente primeiro)
       carrega(id)  -> documento ou null
       grava(doc)   -> true se gravou
       apaga(id)    -> true se apagou
     --------------------------------------------------------------------- */
  function ArmazemDoNavegador(prefixo) {
    // o acesso seguro (try/catch em tudo) é o do MapCore, o mesmo da anotação
    var A = MapCore.criaArmazem();
    function le(chave) { return MapCore.lerJson(A.le("localStorage", prefixo + chave)); }
    function escreve(chave, valor) { return A.grava("localStorage", prefixo + chave, JSON.stringify(valor)); }
    function indice() { return le("indice") || {}; }
    return {
      tipo: "navegador",
      lista: function (mapa) {
        var ind = indice();
        return Object.keys(ind).map(function (id) { return ind[id]; })
          .filter(function (r) { return r.mapa === mapa; })
          .sort(function (a, b) { return a.atualizada_em < b.atualizada_em ? 1 : -1; });
      },
      carrega: function (id) { return le("tatica:" + id); },
      grava: function (doc) {
        if (!escreve("tatica:" + doc.id, doc)) return false;
        var ind = indice(), est = aplica(doc.operacoes);
        var autores = {};
        doc.operacoes.forEach(function (op) { autores[op.autor] = true; });
        ind[doc.id] = { id: doc.id, mapa: doc.mapa, titulo: est.titulo || "(sem título)",
                        atualizada_em: agora(), autores: Object.keys(autores).sort() };
        return escreve("indice", ind);
      },
      apaga: function (id) {
        if (!A.remove("localStorage", prefixo + "tatica:" + id)) return false;
        var ind = indice(); delete ind[id];
        return escreve("indice", ind);
      },
      autor: function (novo) {
        if (novo !== undefined) escreve("autor", novo);
        return le("autor");
      },
      // a tática ABERTA nesta aba (sessão): recarregar volta nela; outra aba
      // ou "Criar tática" começam limpas
      aberta: function (mapa, id) {
        if (id !== undefined) A.grava("sessionStorage", prefixo + "aberta:" + mapa, id);
        return A.le("sessionStorage", prefixo + "aberta:" + mapa);
      }
    };
  }

  /* ---------------------------------------------------------------------
     Estado da página
     --------------------------------------------------------------------- */
  var cfg = null;             // {radar, biblioteca, mapa, mapas}
  var Armazem = null;
  var ANDARES = [];           // nomes das camadas do radar: "default" primeiro
  var CENTRO = null;
  var S = {
    doc: null, estado: null, passo: 0,     // índice do passo na lista
    ferramenta: "mover", arma: "smoke",
    sel: null,                              // {tipo: "peca"|"granada"|"traco", id}
    arrasto: null, tracando: null,
    origemPendente: null,                   // (legado) sem uso desde a máquina de estados
    acao: null,                             // ação pendente: colocar peça, granada, busca
    toque: null,                            // apertou no mapa: vira clique ou arrasto ao soltar
    sugestao: null,                         // granada recém-criada à mão com sugestões abertas
    editor: null, ajuda: false, sobrePeca: false,
    busca: null,                            // {ponto, raio, total, resultados, foco}
    raioBusca: RAIO_BUSCA_PADRAO,
    soParado: false,
    view: { zoom: 1, panX: 0, panY: 0 },
    andar: 0,
    cor: COR_PADRAO, recentes: [], corPendente: null, hsv: { h: 0, s: 1, v: 1 },
    espessura: ESPESSURAS[1],
    pilhaDesfazer: [], pilhaRefazer: [],    // ids das operações DESTE autor, nesta sessão
    giro: null,                             // giro da roda ainda não emitido
    espaco: false, sobreMapa: false, pan: null,
    ultimoDesenho: [],                      // o que foi desenhado no último quadro (testes)
    reproducao: null,                       // {t, tocando, velocidade, cena} enquanto reproduz
    reprojecoes: 0,
    aviso: "",
    gravacoes: 0
  };
  var cv = null, ctx = null, imgs = [], timerGravar = null, cores = null;

  function autor() { return (Armazem.autor() || "").trim() || "anônimo"; }
  function $(id) { return document.getElementById(id); }

  /** Toda mudança passa por aqui: uma operação nova no log. `desfazivel` põe o
      id na pilha de desfazer desta sessão (e limpa o refazer: ramo novo). */
  function emite(tipo, dados, desfazivel) {
    if (S.giro && tipo !== "gira_peca") confirmaGiro();
    var op = { id: novoId(), seq: S.doc.contador + 1, autor: autor(), em: agora(), tipo: tipo };
    Object.keys(dados).forEach(function (k) { op[k] = dados[k]; });
    S.doc.contador = op.seq;
    S.doc.operacoes.push(op);
    if (desfazivel !== false && DESFAZER.indexOf(tipo) < 0) {
      S.pilhaDesfazer.push(op.id);
      S.pilhaRefazer = [];
    }
    reaplica();
    agendaGravacao();
    return op;
  }

  function reaplica() {
    S.estado = aplica(S.doc.operacoes);
    S.passo = Math.max(0, Math.min(S.passo, S.estado.passos.length - 1));
    if (S.sel) {
      var grupo = { peca: "pecas", granada: "granadas", traco: "tracos" }[S.sel.tipo];
      if (!S.estado[grupo][S.sel.id]) S.sel = null;
    }
    atualizaTudo();
  }

  function desfaz() {
    confirmaGiro();
    var fora = anuladas(S.doc.operacoes);
    while (S.pilhaDesfazer.length) {
      var id = S.pilhaDesfazer.pop();
      if (fora[id]) continue;
      emite("anula", { alvo: id });
      S.pilhaRefazer.push(id);
      return true;
    }
    return false;
  }

  function refaz() {
    confirmaGiro();
    if (!S.pilhaRefazer.length) return false;
    var id = S.pilhaRefazer.pop();
    emite("reativa", { alvo: id });
    S.pilhaDesfazer.push(id);
    return true;
  }

  function vazia(doc) { return doc.operacoes.length <= OPS_DA_CRIACAO; }

  function agendaGravacao() {
    clearTimeout(timerGravar);
    timerGravar = setTimeout(gravaAgora, ATRASO_GRAVACAO_MS);
  }
  function gravaAgora() {
    clearTimeout(timerGravar);
    if (!S.doc) return;
    Armazem.aberta(cfg.mapa, S.doc.id);
    if (!vazia(S.doc)) {
      S.aviso = Armazem.grava(S.doc) ? "" : "Não foi possível gravar neste navegador: exporte o arquivo para não perder.";
    }
    S.gravacoes++;
    atualizaBiblioteca();
    atualizaAviso();
  }

  function novaTatica() {
    S.doc = {
      formato: IDENTIFICADOR, versao: FORMATO, id: novoId(), mapa: cfg.mapa,
      criada_por: autor(), criada_em: agora(), calibracao: cfg.radar.calibracao,
      contador: 0, operacoes: []
    };
    S.passo = 0; S.sel = null; S.busca = null;
    S.pilhaDesfazer = []; S.pilhaRefazer = [];
    emite("renomeia", { titulo: "Nova tática" }, false);
    emite("cria_passo", { passo: novoId(), titulo: "" }, false);
    gravaAgora();
  }

  function abre(id) {
    var doc = Armazem.carrega(id);
    if (!doc || VERSOES_ACEITAS.indexOf(doc.versao) < 0) return false;
    S.doc = migra(doc);
    S.passo = 0; S.sel = null; S.busca = null;
    S.pilhaDesfazer = []; S.pilhaRefazer = [];
    Armazem.aberta(cfg.mapa, S.doc.id);
    reaplica();
    return true;
  }

  function passoAtual() { return S.estado.passos[S.passo].passo; }
  function indiceDoPasso(passo) {
    for (var i = 0; i < S.estado.passos.length; i++) if (S.estado.passos[i].passo === passo) return i;
    return -1;
  }
  function quadro(i) { return quadroDoPasso(S.estado, i === undefined ? S.passo : i, CENTRO); }

  /* ---------------------------------------------------------------------
     Projeção e andares
     --------------------------------------------------------------------- */
  function jogoParaPixel(x, y) { return MapCore.jogoParaPixel(cfg.radar, x, y); }
  function pixelParaJogo(px, py) { return MapCore.pixelParaJogo(cfg.radar, px, py); }
  function eventoParaPixel(e) { return MapCore.eventoParaPixel(cv, cfg.radar, e, S.view); }
  function arredonda(v) { return Math.round(v * 10) / 10; }   // 0,1u, como a anotação
  function eventoParaJogo(e) {
    var p = eventoParaPixel(e), g = pixelParaJogo(p[0], p[1]);
    return [arredonda(g[0]), arredonda(g[1])];
  }

  /** Andares do radar, na ordem do replay (scripts/export_replay.map_levels):
      "default" primeiro, depois de cima para baixo. */
  function andaresDoRadar(r) {
    var sec = r.vertical_sections;
    if (!sec) return [{ nome: "default", min: -1e9, max: 1e9 }];
    return Object.keys(sec).map(function (k) { return { nome: k, min: sec[k].min, max: sec[k].max }; })
      .sort(function (a, b) {
        if ((a.nome !== "default") !== (b.nome !== "default")) return a.nome === "default" ? -1 : 1;
        return b.max - a.max;
      });
  }
  function nivelDoZ(z) {
    if (ANDARES.length < 2 || z === undefined || z === null) return 0;
    for (var i = 0; i < ANDARES.length; i++) if (z >= ANDARES[i].min && z < ANDARES[i].max) return i;
    return 0;
  }

  /* ---------------------------------------------------------------------
     Tamanho: O ÚNICO lugar que muda o tamanho do canvas
     --------------------------------------------------------------------- */
  function emTelaCheia() { return MapCore.emTelaCheia($("pr-palco")); }

  function reprojeta() {
    var tela = $("pr-tela"), est = getComputedStyle(tela);
    var util = tela.clientWidth - parseFloat(est.paddingLeft) - parseFloat(est.paddingRight);
    var alto = emTelaCheia()
      ? tela.clientHeight - parseFloat(est.paddingTop) - parseFloat(est.paddingBottom)
      : window.innerHeight - 40;
    if (util <= 0 || alto <= 0) return;
    // a proporção é a do radar, nunca a do espaço disponível: nada de mapa esticado
    var cx = MapCore.caixaDoMapa(cfg.radar, util, Math.max(200, alto));
    var largura = Math.max(200, Math.floor(cx.largura));
    var altura = Math.round(largura * cfg.radar.height / cfg.radar.width);
    cv.style.width = largura + "px"; cv.style.height = altura + "px";
    var tam = MapCore.tamanhoInterno(cfg.radar, largura, window.devicePixelRatio || 1);
    if (cv.width !== tam.w || cv.height !== tam.h) { cv.width = tam.w; cv.height = tam.h; }
    S.reprojecoes++;
    desenha();
  }
  var pedeReprojecao = null;

  function aplicaZoom(novo, cx, cy) {
    if (MapCore.aplicaZoom(S.view, cfg.radar, novo,
        cx === undefined ? cfg.radar.width / 2 : cx, cy === undefined ? cfg.radar.height / 2 : cy)) {
      desenha(); atualizaBarra();
    }
  }
  function resetaZoom() { S.view = { zoom: 1, panX: 0, panY: 0 }; desenha(); atualizaBarra(); }

  /* ---------------------------------------------------------------------
     Desenho
     --------------------------------------------------------------------- */
  function cssVar(nome) { return getComputedStyle(document.documentElement).getPropertyValue(nome).trim(); }
  function escalaUnidade() { return cfg.radar.scale_px_per_unit; }

  function desenha() {
    if (!ctx || !temQuadro()) return;
    S.ultimoDesenho = [];
    ctx.setTransform(1, 0, 0, 1, 0, 0);
    ctx.clearRect(0, 0, cv.width, cv.height);
    MapCore.applyView(ctx, cfg.radar, S.view);
    var im = imgs[S.andar] || imgs[0];
    if (im && im.complete && im.naturalWidth) ctx.drawImage(im, 0, 0, cfg.radar.width, cfg.radar.height);

    // O editor e a reprodução desenham a mesma CENA; só o editor põe por cima
    // busca, rascunho, rastro do passo anterior e seleção.
    var editando = !S.reproducao;
    var cena = editando ? cenaDoEditor() : S.reproducao.cena;
    if (editando) desenhaBusca();
    Object.keys(cena.granadas).forEach(function (id) { desenhaGranada(id, cena.granadas[id], editando); });
    Object.keys(cena.tracos).forEach(function (id) { desenhaTraco(id, cena.tracos[id]); });
    if (editando && S.tracando) MapCore.caminhoDoTraco(ctx, S.tracando, cfg.radar);
    if (editando && S.origemPendente) {
      var o = jogoParaPixel(S.origemPendente[0], S.origemPendente[1]);
      ctx.fillStyle = MapCore.NADE_COLOR[S.arma];
      ctx.beginPath(); ctx.arc(o[0], o[1], 5, 0, 2 * Math.PI); ctx.fill();
    }
    var ant = editando && S.passo > 0 ? quadro(S.passo - 1) : null;
    Object.keys(cena.pecas).forEach(function (id) { desenhaPeca(id, cena.pecas[id], ant && ant.pecas[id], editando); });
  }

  /** O passo aberto no editor, no mesmo formato da cena da reprodução: a
      linha do arremesso só no passo em que a granada nasceu. */
  function cenaDoEditor() {
    var q = quadro(), c = { pecas: {}, granadas: {}, tracos: {} };
    Object.keys(q.pecas).forEach(function (id) { c.pecas[id] = Object.assign({}, q.pecas[id], { alfa: 1 }); });
    Object.keys(q.granadas).forEach(function (id) {
      var g = q.granadas[id];
      c.granadas[id] = Object.assign({}, g, { linha: g.nasceu_neste_passo && !g.origem_desconhecida ? 1 : 0, efeito: 1, alfa: 1 });
    });
    Object.keys(q.tracos).forEach(function (id) { c.tracos[id] = Object.assign({}, q.tracos[id], { alfa: 1 }); });
    return c;
  }

  function alfaDoAndar(nivel) { return nivel === S.andar ? 1 : ALFA_OUTRO_ANDAR; }

  /** `g.linha` (0 a 1) é quanto da linha do arremesso está riscada e
      `g.efeito` (0 a 1) o quanto o efeito já abriu: no editor, 1 e 1 no passo
      de criação e 0 e 1 depois; na reprodução, o que o tempo disser. */
  function desenhaGranada(id, g, editando) {
    var o = g.origem, d = g.destino;
    if (editando && S.arrasto && S.arrasto.tipo === "granada" && S.arrasto.id === id) { o = S.arrasto.origem; d = S.arrasto.destino; }
    var a = jogoParaPixel(o[0], o[1]), b = jogoParaPixel(d[0], d[1]);
    var alfa = alfaDoAndar(g.nivel) * g.alfa, cor = MapCore.NADE_COLOR[g.arma];
    var area = g.arma === "smoke" || g.arma === "molotov";
    ctx.save();
    ctx.globalAlpha = alfa;
    if (area && g.efeito > 0) {
      var r = (g.arma === "smoke" ? MapCore.RAIO_SMOKE_UNIDADES : MapCore.RAIO_MOLOTOV_UNIDADES) * escalaUnidade();
      MapCore.desenhaArea(ctx, g.arma, b[0], b[1], r * g.efeito);
    }
    if (g.linha > 0) {
      var fim = [a[0] + (b[0] - a[0]) * g.linha, a[1] + (b[1] - a[1]) * g.linha];
      ctx.strokeStyle = cor; ctx.lineWidth = 2.5;
      if (!g.arremesso) ctx.setLineDash([6, 5]);   // desenhada à mão: tracejada
      ctx.beginPath(); ctx.moveTo(a[0], a[1]); ctx.lineTo(fim[0], fim[1]); ctx.stroke();
      ctx.setLineDash([]);
      ctx.fillStyle = cor;
      ctx.beginPath(); ctx.arc(a[0], a[1], 4, 0, 2 * Math.PI); ctx.fill();
    }
    if (g.efeito > 0) {
      MapCore.nadeGlyph(ctx, g.arma, b[0], b[1], RAIO_GRANADA * g.efeito, cor, Math.atan2(b[1] - a[1], b[0] - a[0]));
    }
    if (editando && S.sel && S.sel.id === id) {
      ctx.strokeStyle = "#ffffff"; ctx.lineWidth = 2;
      ctx.beginPath(); ctx.arc(b[0], b[1], RAIO_GRANADA * 1.9, 0, 2 * Math.PI); ctx.stroke();
    }
    ctx.restore();
    S.ultimoDesenho.push({ tipo: "granada", id: id, linha: g.linha > 0, area: area && g.efeito > 0, alfa: alfa });
  }

  function desenhaTraco(id, t) {
    var alfa = alfaDoAndar(t.nivel) * t.alfa;
    ctx.save();
    ctx.globalAlpha = alfa;
    MapCore.caminhoDoTraco(ctx, t, cfg.radar);
    ctx.restore();
    S.ultimoDesenho.push({ tipo: "traco", id: id, alfa: alfa, pontos: t.pontos.length });
  }

  function yawDaPeca(id, p) {
    if (S.giro && S.giro.peca === id) return S.giro.yaw;
    if (S.arrasto && S.arrasto.tipo === "giro" && S.arrasto.id === id && S.arrasto.yaw !== null) return S.arrasto.yaw;
    return p.yaw;
  }

  function desenhaPeca(id, p, anterior, editando) {
    var pos = [p.x, p.y];
    if (editando && S.arrasto && S.arrasto.tipo === "peca" && S.arrasto.id === id) pos = S.arrasto.jogo;
    var c = jogoParaPixel(pos[0], pos[1]);
    var cor = cssVar(p.lado === "ct" ? "--ct" : "--t");
    var alfa = alfaDoAndar(p.nivel) * p.alfa, yaw = editando ? yawDaPeca(id, p) : p.yaw;
    // rastro do passo anterior: onde estava e para onde olhava
    if (anterior && (anterior.x !== pos[0] || anterior.y !== pos[1] || anterior.yaw !== yaw)) {
      var a = jogoParaPixel(anterior.x, anterior.y);
      ctx.save();
      ctx.globalAlpha = ALFA_RASTRO * alfa;
      if (anterior.x !== pos[0] || anterior.y !== pos[1]) {
        ctx.strokeStyle = cor; ctx.lineWidth = 2; ctx.setLineDash([8, 6]);
        ctx.beginPath(); ctx.moveTo(a[0], a[1]); ctx.lineTo(c[0], c[1]); ctx.stroke();
        ctx.setLineDash([]);
      }
      MapCore.desenhaJogador(ctx, a[0], a[1], { cor: cor, estado: "vivo", hp: 100, cego: false,
                                                nome: "", yaw: anterior.yaw, escala: ESCALA_PECA });
      ctx.restore();
    }
    ctx.save();
    ctx.globalAlpha = alfa;
    MapCore.desenhaJogador(ctx, c[0], c[1], { cor: cor, estado: "vivo", hp: 100, cego: false,
                                              nome: rotuloDaPeca(p), yaw: yaw, escala: ESCALA_PECA });
    if (editando && S.sel && S.sel.id === id) {
      var h = alca(c, yaw);
      ctx.globalAlpha = 1;
      ctx.fillStyle = "#ffffff"; ctx.strokeStyle = "#0f1620"; ctx.lineWidth = 2;
      ctx.beginPath(); ctx.arc(h[0], h[1], RAIO_ALCA, 0, 2 * Math.PI); ctx.fill(); ctx.stroke();
    }
    ctx.restore();
    S.ultimoDesenho.push({ tipo: "peca", id: id, x: c[0], y: c[1], yaw: yaw, alfa: alfa });
  }

  /** Peça do banco tem rótulo 1 a 5 e aparece como "CT 1"; peça que veio de um
      instante do replay tem o NOME do jogador, que já diz quem é. */
  function rotuloDaPeca(p) {
    return /^[1-9]$/.test(p.rotulo) ? (p.lado === "ct" ? "CT " : "TR ") + p.rotulo : p.rotulo;
  }

  /** Onde fica a alça de girar: na ponta da gota. */
  function alca(c, yaw) {
    var t = MapCore.anguloDeTela(yaw), d = MapCore.PONTA_DISTANCIA * ESCALA_PECA;
    return [c[0] + Math.cos(t) * d, c[1] + Math.sin(t) * d];
  }

  function desenhaBusca() {
    if (!S.busca) return;
    var c = jogoParaPixel(S.busca.ponto[0], S.busca.ponto[1]);
    ctx.save();
    ctx.strokeStyle = "rgba(255,255,255,0.8)"; ctx.setLineDash([6, 5]); ctx.lineWidth = 2;
    ctx.beginPath(); ctx.arc(c[0], c[1], S.busca.raio * escalaUnidade(), 0, 2 * Math.PI); ctx.stroke();
    ctx.setLineDash([]);
    S.busca.resultados.forEach(function (r, n) {
      var a = jogoParaPixel(r.origem[0], r.origem[1]), b = jogoParaPixel(r.destino[0], r.destino[1]);
      var foco = S.busca.foco === n;
      ctx.globalAlpha = foco ? 1 : 0.45;
      ctx.strokeStyle = MapCore.NADE_COLOR[r.arma]; ctx.lineWidth = foco ? 3 : 1.2;
      ctx.beginPath(); ctx.moveTo(a[0], a[1]); ctx.lineTo(b[0], b[1]); ctx.stroke();
      ctx.fillStyle = MapCore.NADE_COLOR[r.arma];
      ctx.beginPath(); ctx.arc(a[0], a[1], foco ? 6 : 3.5, 0, 2 * Math.PI); ctx.fill();
    });
    ctx.restore();
  }

  /* ---------------------------------------------------------------------
     Ponteiro
     --------------------------------------------------------------------- */
  /** O que está sob o ponteiro (pixel do radar). Só o andar ativo é tocável:
      o que está esmaecido não se mexe sem querer. */
  function acha(px) {
    var q = quadro(), achado = null, melhor = Infinity;
    function perto(c, raio, qual) {
      var d = Math.hypot(c[0] - px[0], c[1] - px[1]);
      if (d <= raio && d < melhor) { melhor = d; achado = qual; }
    }
    if (S.sel && S.sel.tipo === "peca" && q.pecas[S.sel.id] && q.pecas[S.sel.id].nivel === S.andar) {
      var ps = q.pecas[S.sel.id];
      perto(alca(jogoParaPixel(ps.x, ps.y), ps.yaw), RAIO_ALCA + 3, { tipo: "giro", id: S.sel.id });
      if (achado) return achado;
    }
    Object.keys(q.pecas).forEach(function (id) {
      var p = q.pecas[id];
      if (p.nivel === S.andar) perto(jogoParaPixel(p.x, p.y), RAIO_PECA + 3, { tipo: "peca", id: id });
    });
    Object.keys(q.granadas).forEach(function (id) {
      var g = q.granadas[id];
      if (g.nivel !== S.andar || !g.nasceu_neste_passo) return;   // só se mexe no passo em que nasceu
      perto(jogoParaPixel(g.destino[0], g.destino[1]), RAIO_PONTA_GRANADA + 3, { tipo: "granada", id: id, ponta: "destino" });
      if (!g.origem_desconhecida) perto(jogoParaPixel(g.origem[0], g.origem[1]), RAIO_PONTA_GRANADA, { tipo: "granada", id: id, ponta: "origem" });
    });
    return achado;
  }

  function comecaPan(e) {
    if (S.view.zoom <= 1) return false;
    S.pan = { x: e.clientX, y: e.clientY, panX: S.view.panX, panY: S.view.panY };
    cv.setPointerCapture(e.pointerId);
    return true;
  }

  /* ---------------------------------------------------------------------
     Interação: UMA máquina de estados (prancheta fluida, 2026-09-27)

     Cada clique faz uma coisa previsível, e a linha de dica diz qual é ANTES
     do clique. O estado sai de três campos -- a ferramenta de desenho, a ação
     pendente e a seleção -- e nunca de condições espalhadas pelos handlers.
     Nada aqui cria operação nova: mover por clique emite o mesmo move_peca,
     virar emite o mesmo gira_peca, granada o mesmo cria_granada.
     --------------------------------------------------------------------- */
  // Ponteiro que anda menos que isto (px de tela) entre apertar e soltar é
  // CLIQUE; acima, ARRASTO. É a única distinção entre os dois no editor.
  var LIMIAR_ARRASTO_PX = 4;

  function nomePeca(id) { var p = S.estado.pecas[id]; return p ? rotuloDaPeca(p) : ""; }

  /** O estado atual da interação, pelo nome da tabela. */
  function estadoDaInteracao() {
    if (ROTULO_FERRAMENTA[S.ferramenta] || S.ferramenta === "borracha") return "desenhando";
    var a = S.acao;
    if (a && a.tipo === "colocar") return "colocando_peca";
    if (a && a.tipo === "busca") return "buscando";
    if (a && a.tipo === "granada") return a.origem ? "granada_destino" : "granada_origem";
    if (S.sel && S.sel.tipo === "peca") return "peca_selecionada";
    if (S.sel && S.sel.tipo === "granada") return "granada_selecionada";
    return "livre";
  }

  /** A tabela da máquina: como se entra, o que o próximo clique faz e a dica.
      A dica recebe o contexto (nomes, arma) e é a MESMA função que a tela usa. */
  var ESTADOS = {
    livre: { entra: "padrão; Esc", clique: "seleciona peça, granada ou traço; no vazio, nada",
      dica: function () { return "Clique num jogador para selecionar, ou escolha uma ferramenta"; } },
    peca_selecionada: { entra: "clique numa peça, ou no nome dela no banco",
      clique: "no vazio: a peça vai para lá (move_peca); em outra peça: seleciona a outra; botão direito: vira para o ponto (gira_peca)",
      dica: function (c) { return c.peca + " selecionado · clique no mapa para mover · botão direito para virar · 1–4 joga granada"; } },
    colocando_peca: { entra: "clique numa ficha do banco fora do mapa neste passo",
      clique: "cria (ou recoloca) a peça ali e a seleciona",
      dica: function (c) { return "Clique no mapa para colocar " + c.ficha + " · Esc cancela"; } },
    granada_destino: { entra: "tipo de granada com uma peça selecionada (ou origem já escolhida)",
      clique: "o destino: cria a granada e mostra os arremessos reais que caem ali",
      dica: function (c) { return c.arma + " de " + c.origem + " · clique onde ela deve cair"; } },
    granada_origem: { entra: "tipo de granada sem peça selecionada",
      clique: "numa peça: ela é a origem; no vazio: o ponto é a origem",
      dica: function (c) { return c.arma + " · clique em quem joga (ou no ponto de onde sai)"; } },
    granada_selecionada: { entra: "clique numa granada nascida neste passo",
      clique: "no vazio: muda onde ela cai (move_granada)",
      dica: function (c) { return c.arma + " selecionada · clique para mudar onde cai" + (c.real ? " (desfaz o arremesso real)" : ""); } },
    desenhando: { entra: "uma ferramenta de desenho",
      clique: "arrastar desenha; a borracha apaga o traço sob o clique",
      dica: function (c) { return c.ferramenta + " · arraste para desenhar · V volta a selecionar"; } },
    buscando: { entra: "“Buscar arremesso” no painel",
      clique: "lista os arremessos reais que caem perto do ponto",
      dica: function (c) { return "Buscar " + c.arma + " · clique onde ela deve cair"; } }
  };

  function contextoDaDica() {
    var a = S.acao || {}, g = S.sel && S.sel.tipo === "granada" ? S.estado.granadas[S.sel.id] : null;
    var origem = a.de ? nomePeca(a.de) : "um ponto";
    return {
      peca: S.sel && S.sel.tipo === "peca" ? nomePeca(S.sel.id) : "",
      ficha: a.rotulo ? (a.lado === "ct" ? "CT " : "TR ") + a.rotulo : "",
      arma: NOME_ARMA[a.arma || (g && g.arma) || S.arma],
      origem: origem,
      real: !!(g && g.arremesso),
      ferramenta: ROTULO_FERRAMENTA[S.ferramenta] || (S.ferramenta === "borracha" ? "Borracha" : "")
    };
  }

  function dicaAtual() { return ESTADOS[estadoDaInteracao()].dica(contextoDaDica()); }

  function atualizaDica() {
    var d = $("pr-dica-estado");
    if (d) d.textContent = dicaAtual();
    if (!cv) return;
    var e = estadoDaInteracao();
    cv.style.cursor = (e === "colocando_peca" || e === "granada_origem" || e === "granada_destino" ||
                       e === "buscando" || e === "desenhando") ? "crosshair" : (S.sobrePeca ? "pointer" : "default");
  }

  /* --- ações pendentes --------------------------------------------------------- */
  /** Escolher um tipo de granada: com peça selecionada, a origem é ela. */
  function escolheArma(arma) {
    confirmaGiro();
    S.arma = arma;
    if (S.acao && S.acao.tipo === "busca") { S.acao.arma = arma; if (S.busca) busca(S.busca.ponto); atualizaTudo(); return; }
    if (ROTULO_FERRAMENTA[S.ferramenta] || S.ferramenta === "borracha") S.ferramenta = "mover";
    var q = quadro();
    if (S.sel && S.sel.tipo === "peca" && q.pecas[S.sel.id]) {
      var p = q.pecas[S.sel.id];
      S.acao = { tipo: "granada", arma: arma, de: S.sel.id, origem: [p.x, p.y], nivel: p.nivel };
    } else {
      S.acao = { tipo: "granada", arma: arma, de: null, origem: null };
    }
    S.busca = null;
    atualizaTudo();
  }

  /** Cria a granada à mão e, se o mapa tem biblioteca, abre as sugestões de
      arremesso real para o destino -- a primeira opção é manter a desenhada. */
  function criaGranadaDaAcao(destino) {
    var a = S.acao;
    var op = emite("cria_granada", { granada: novoId(), arma: a.arma, passo: passoAtual(),
                                     nivel: a.nivel === undefined ? S.andar : a.nivel,
                                     origem: [a.origem[0], a.origem[1]], destino: [destino[0], destino[1]], arremesso: null });
    if (a.legado) {
      // "Desenhar à mão" do painel: a ferramenta fica, como sempre foi
      S.acao = { tipo: "granada", arma: a.arma, de: null, origem: null, legado: true };
      S.sel = { tipo: "granada", id: op.granada };
    } else if (a.de && S.estado.pecas[a.de]) {
      S.acao = null; S.sel = { tipo: "peca", id: a.de };
    } else {
      S.acao = null; S.sel = { tipo: "granada", id: op.granada };
    }
    if (cfg.biblioteca && !a.legado) {
      S.sugestao = { granada: op.granada, de: a.de ? nomePeca(a.de) : "o ponto escolhido" };
      busca(destino, a.arma);
    } else if (!cfg.biblioteca && !a.legado) {
      S.aviso = "Sem arremessos reais neste mapa: não há partidas dele no corpus, então a granada fica desenhada à mão.";
    }
    atualizaTudo();
  }

  /** Trocar a granada desenhada pelo arremesso real escolhido na lista. */
  function trocaPorArremesso(r) {
    var s = S.sugestao;
    if (s && S.estado.granadas[s.granada]) emite("remove_granada", { granada: s.granada });
    S.sugestao = null;
    usaArremesso(r);
  }

  /** Um nível para trás: ação pendente -> ferramenta de desenho -> seleção. */
  function volta() {
    if (S.editor) { fechaEditorTexto(false); return; }
    if (S.ajuda) { alternaAjuda(false); return; }
    if (S.busca || S.sugestao) { S.busca = null; S.sugestao = null; atualizaTudo(); return; }
    if (S.acao) { S.acao = null; atualizaTudo(); return; }
    if (ROTULO_FERRAMENTA[S.ferramenta] || S.ferramenta === "borracha") { S.ferramenta = "mover"; atualizaTudo(); return; }
    S.sel = null; atualizaTudo();
  }

  /* --- ponteiro ------------------------------------------------------------------ */
  function pointerDown(e) {
    if (!S.doc) return;
    if (S.reproducao) { if (S.espaco || e.button === 1) comecaPan(e); return; }
    if (S.espaco || e.button === 1) { comecaPan(e); e.preventDefault(); return; }
    var px = eventoParaPixel(e), g = eventoParaJogo(e);
    if (e.button === 2) {
      // botão direito: a peça selecionada passa a olhar para o ponto
      e.preventDefault();
      var q = quadro();
      if (S.sel && S.sel.tipo === "peca" && q.pecas[S.sel.id]) {
        var p = q.pecas[S.sel.id];
        confirmaGiro();
        emite("gira_peca", { peca: S.sel.id, passo: passoAtual(),
                             yaw: yawInteiro(Math.atan2(g[1] - p.y, g[0] - p.x) * (180 / Math.PI)) });
      }
      return;
    }
    if (e.button !== 0) return;
    if (S.editor) fechaEditorTexto(true);
    var estado = estadoDaInteracao();
    if (estado === "desenhando") { comecaTraco(e, px, g); return; }
    cv.setPointerCapture(e.pointerId);
    var alvo = acha(px);
    S.toque = { x: e.clientX, y: e.clientY, px: px, g: g, alvo: alvo, estado: estado, arrastou: false };
    // arrastar peça, alça ou ponta de granada continua como sempre (quando não
    // há ação pendente): o arrasto é armado aqui e só vira operação se andar
    if (alvo && (estado === "livre" || estado === "peca_selecionada" || estado === "granada_selecionada")) {
      S.sel = { tipo: alvo.tipo === "giro" ? "peca" : alvo.tipo, id: alvo.id };
      var q2 = quadro();
      if (alvo.tipo === "giro") S.arrasto = { tipo: "giro", id: alvo.id, yaw: null, mexeu: false };
      else if (alvo.tipo === "peca") S.arrasto = { tipo: "peca", id: alvo.id, jogo: [q2.pecas[alvo.id].x, q2.pecas[alvo.id].y], mexeu: false };
      else {
        var gr = S.estado.granadas[alvo.id];
        S.arrasto = { tipo: "granada", id: alvo.id, ponta: alvo.ponta, origem: gr.origem.slice(), destino: gr.destino.slice(), mexeu: false };
      }
      atualizaPainel(); atualizaDica();
    }
    desenha();
  }

  function pointerMove(e) {
    if (S.pan) {
      var k = cfg.radar.width / cv.getBoundingClientRect().width;
      S.view.panX = S.pan.panX + (e.clientX - S.pan.x) * k;
      S.view.panY = S.pan.panY + (e.clientY - S.pan.y) * k;
      MapCore.limitaPan(S.view, cfg.radar);
      desenha();
      return;
    }
    if (S.tracando) { continuaTraco(e); return; }
    if (S.toque && !S.toque.arrastou &&
        Math.hypot(e.clientX - S.toque.x, e.clientY - S.toque.y) >= LIMIAR_ARRASTO_PX) S.toque.arrastou = true;
    if (!S.arrasto) {
      if (!S.toque && S.doc && !S.reproducao) {
        var sobre = !!acha(eventoParaPixel(e));
        if (sobre !== !!S.sobrePeca) { S.sobrePeca = sobre; atualizaDica(); }
      }
      return;
    }
    if (!S.toque || !S.toque.arrastou) return;
    var g = eventoParaJogo(e);
    S.arrasto.mexeu = true;
    if (S.arrasto.tipo === "peca") S.arrasto.jogo = g;
    else if (S.arrasto.tipo === "giro") {
      var p = quadro().pecas[S.arrasto.id];
      S.arrasto.yaw = yawInteiro(Math.atan2(g[1] - p.y, g[0] - p.x) * (180 / Math.PI));
    } else S.arrasto[S.arrasto.ponta] = [g[0], g[1]];
    desenha();
  }

  function yawInteiro(v) { return ((Math.round(v) % 360) + 360) % 360; }

  function pointerUp() {
    if (S.pan) { S.pan = null; return; }
    if (S.tracando) { terminaTraco(); return; }
    var a = S.arrasto, t = S.toque;
    S.arrasto = null; S.toque = null;
    if (a && a.mexeu) {
      if (a.tipo === "peca") emite("move_peca", { peca: a.id, passo: passoAtual(), x: a.jogo[0], y: a.jogo[1], nivel: S.andar });
      else if (a.tipo === "giro") { if (a.yaw !== null) emite("gira_peca", { peca: a.id, passo: passoAtual(), yaw: a.yaw }); }
      else emite("move_granada", { granada: a.id, origem: a.origem, destino: a.destino, nivel: S.estado.granadas[a.id].nivel });
      return;
    }
    if (t && !t.arrastou) clique(t);
    else desenha();
  }

  /** O clique (ponteiro que não andou), resolvido pelo estado em que começou. */
  function clique(t) {
    var g = t.g, alvo = t.alvo, q = quadro();
    switch (t.estado) {
      case "colocando_peca": {
        var ac = S.acao;
        S.acao = null;
        colocaPeca(ac.lado, ac.rotulo, g);
        return;
      }
      case "buscando":
        if (cfg.biblioteca) busca(g, S.acao.arma);
        return;
      case "granada_origem":
        if (alvo && alvo.tipo === "peca" && q.pecas[alvo.id]) {
          var p = q.pecas[alvo.id];
          S.acao.de = alvo.id; S.acao.origem = [p.x, p.y]; S.acao.nivel = p.nivel;
        } else {
          S.acao.origem = [g[0], g[1]];
        }
        atualizaTudo();
        return;
      case "granada_destino":
        criaGranadaDaAcao(g);
        return;
      case "peca_selecionada":
        if (!alvo) {
          // no vazio: a peça selecionada vai para lá, no andar ativo
          emite("move_peca", { peca: S.sel.id, passo: passoAtual(), x: g[0], y: g[1], nivel: S.andar });
          return;
        }
        break;
      case "granada_selecionada":
        if (!alvo) {
          var gr = S.estado.granadas[S.sel.id];
          emite("move_granada", { granada: S.sel.id, origem: gr.origem.slice(), destino: [g[0], g[1]], nivel: gr.nivel });
          return;
        }
        break;
      default:
        break;
    }
    // livre, ou clique num item: seleciona o que está sob o ponteiro
    S.sel = alvo ? { tipo: alvo.tipo === "giro" ? "peca" : alvo.tipo, id: alvo.id } : (t.estado === "livre" ? null : S.sel);
    if (!alvo && t.estado === "livre") {
      var tr = tracoSob(t.px);
      if (tr) S.sel = { tipo: "traco", id: tr };
    }
    atualizaTudo();
  }

  /** O traço mais recente sob o ponto, no andar ativo. */
  function tracoSob(px) {
    var q = quadro();
    var alvos = ordemDeCriacao(S.estado).filter(function (x) {
      return x.tipo === "traco" && q.tracos[x.id] && q.tracos[x.id].nivel === S.andar &&
             MapCore.tracoEncosta(q.tracos[x.id], px, cfg.radar, RAIO_BORRACHA);
    });
    return alvos.length ? alvos[alvos.length - 1].id : null;
  }

  /** Põe a ficha do banco no mapa: a peça existente volta (move_peca) ou uma
      nova nasce (cria_peca) -- o mesmo que soltar o arrasto do banco. */
  function colocaPeca(lado, rotulo, g) {
    var existente = Object.keys(S.estado.pecas).filter(function (id) {
      return S.estado.pecas[id].lado === lado && S.estado.pecas[id].rotulo === rotulo;
    })[0];
    if (existente) {
      emite("move_peca", { peca: existente, passo: passoAtual(), x: g[0], y: g[1], nivel: S.andar });
      S.sel = { tipo: "peca", id: existente };
    } else {
      var op = emite("cria_peca", { peca: novoId(), lado: lado, rotulo: rotulo, passo: passoAtual(),
                                    x: g[0], y: g[1], nivel: S.andar });
      S.sel = { tipo: "peca", id: op.peca };
    }
    atualizaTudo();
  }

  /** Clique numa ficha do banco: seleciona a peça se ela está no mapa neste
      passo; senão arma a colocação. */
  function cliqueNaFicha(lado, rotulo) {
    confirmaGiro();
    var q = quadro();
    var noMapa = Object.keys(q.pecas).filter(function (id) {
      return q.pecas[id].lado === lado && q.pecas[id].rotulo === rotulo;
    })[0];
    if (ROTULO_FERRAMENTA[S.ferramenta] || S.ferramenta === "borracha") S.ferramenta = "mover";
    S.busca = null; S.sugestao = null;
    if (noMapa) { S.acao = null; S.sel = { tipo: "peca", id: noMapa }; }
    else S.acao = { tipo: "colocar", lado: lado, rotulo: rotulo };
    atualizaTudo();
  }

  /** Gira a peça selecionada no passo atual (Q/E e os botões do painel). */
  function giraSelecionada(delta) {
    var q = quadro();
    if (!S.sel || S.sel.tipo !== "peca" || !q.pecas[S.sel.id]) return;
    var base = yawDaPeca(S.sel.id, q.pecas[S.sel.id]);
    confirmaGiro();
    emite("gira_peca", { peca: S.sel.id, passo: passoAtual(), yaw: yawInteiro(base + delta) });
  }

  /** Muda de passo mantendo a seleção quando a peça existe no passo novo. */
  function mudaPasso(i) {
    confirmaGiro();
    S.passo = Math.max(0, Math.min(i, S.estado.passos.length - 1));
    if (S.sel) {
      var q = quadro();
      var grupo = { peca: "pecas", granada: "granadas", traco: "tracos" }[S.sel.tipo];
      if (!q[grupo][S.sel.id]) S.sel = null;
    }
    if (S.acao && S.acao.tipo === "granada" && S.acao.de) {
      var pq = quadro().pecas[S.acao.de];
      if (pq) { S.acao.origem = [pq.x, pq.y]; S.acao.nivel = pq.nivel; } else S.acao = null;
    }
    atualizaTudo();
  }

  /* --- texto no próprio mapa (sem window.prompt) --------------------------------- */
  function abreEditorTexto(g) {
    fechaEditorTexto(false);
    var px = jogoParaPixel(g[0], g[1]);
    var r = cv.getBoundingClientRect(), k = r.width / cfg.radar.width;
    var x = (px[0] * S.view.zoom + S.view.panX) * k, y = (px[1] * S.view.zoom + S.view.panY) * k;
    var campo = el("input", { type: "text", id: "pr-editor-texto", class: "pr-editor-texto",
                              "aria-label": "Texto da anotação (Enter confirma, Esc cancela)",
                              placeholder: "texto · Enter confirma · Esc cancela" });
    campo.style.left = (cv.offsetLeft + x) + "px";
    campo.style.top = (cv.offsetTop + y) + "px";
    campo.addEventListener("keydown", function (e) {
      if (e.key === "Enter") { e.preventDefault(); fechaEditorTexto(true); }
      else if (e.key === "Escape") { e.preventDefault(); e.stopPropagation(); fechaEditorTexto(false); }
    });
    $("pr-tela").appendChild(campo);
    S.editor = { g: g, campo: campo };
    setTimeout(function () { campo.focus(); }, 0);
  }

  function fechaEditorTexto(confirma) {
    var ed = S.editor;
    if (!ed) return;
    S.editor = null;
    var txt = ed.campo.value.trim();
    if (ed.campo.parentNode) ed.campo.parentNode.removeChild(ed.campo);
    if (confirma && txt) {
      var op = emite("cria_traco", { traco: novoId(), passo: passoAtual(), ferramenta: "texto", texto: txt,
                                     cor: S.cor, espessura: S.espessura, pontos: [ed.g], nivel: S.andar });
      S.sel = { tipo: "traco", id: op.traco };
    }
    atualizaTudo();
  }

  /* --- atalhos: UM mapa, sem tecla repetida (há teste) ----------------------------- */
  var ATALHOS = [
    { tecla: "v", rotulo: "V", acao: "Selecionar", fn: function () { escolheFerramenta("mover"); } },
    { tecla: "1", rotulo: "1", acao: "Smoke", fn: function () { escolheArma("smoke"); } },
    { tecla: "2", rotulo: "2", acao: "Flash", fn: function () { escolheArma("flash"); } },
    { tecla: "3", rotulo: "3", acao: "HE", fn: function () { escolheArma("he"); } },
    { tecla: "4", rotulo: "4", acao: "Molotov", fn: function () { escolheArma("molotov"); } },
    { tecla: "c", rotulo: "C", acao: "Caneta", fn: function () { escolheFerramenta("caneta"); } },
    { tecla: "a", rotulo: "A", acao: "Seta", fn: function () { escolheFerramenta("seta"); } },
    { tecla: "l", rotulo: "L", acao: "Linha", fn: function () { escolheFerramenta("linha"); } },
    { tecla: "t", rotulo: "T", acao: "Texto", fn: function () { escolheFerramenta("texto"); } },
    { tecla: "x", rotulo: "X", acao: "Borracha", fn: function () { escolheFerramenta("borracha"); } },
    { tecla: "q", rotulo: "Q", acao: "Girar a peça 15° (Shift: 1°) no sentido anti-horário",
      fn: function (e) { giraSelecionada(e.shiftKey ? PASSO_GIRO_FINO : PASSO_GIRO); } },
    { tecla: "e", rotulo: "E", acao: "Girar a peça 15° (Shift: 1°) no sentido horário",
      fn: function (e) { giraSelecionada(-(e.shiftKey ? PASSO_GIRO_FINO : PASSO_GIRO)); } },
    { tecla: ",", rotulo: ",", acao: "Passo anterior", fn: function () { mudaPasso(S.passo - 1); } },
    { tecla: ".", rotulo: ".", acao: "Próximo passo", fn: function () { mudaPasso(S.passo + 1); } },
    { tecla: "n", rotulo: "N", acao: "Novo passo", fn: function () { novoPasso(); } },
    { tecla: "delete", rotulo: "Delete", acao: "Remover o selecionado", fn: function () { removeSelecionado(); } },
    { tecla: "escape", rotulo: "Esc", acao: "Um nível para trás", fn: function () { volta(); } },
    { tecla: "f", rotulo: "F", acao: "Tela cheia", fn: function () { MapCore.alternaTelaCheia($("pr-palco")); } },
    { tecla: "0", rotulo: "0", acao: "Zoom original", fn: function () { resetaZoom(); } },
    { tecla: "?", rotulo: "?", acao: "Ajuda: esta lista", fn: function () { alternaAjuda(); } },
    { tecla: "ctrl+z", rotulo: "Ctrl+Z", acao: "Desfazer", fn: function () { desfaz(); } },
    { tecla: "ctrl+y", rotulo: "Ctrl+Y", acao: "Refazer (também Ctrl+Shift+Z)", fn: function () { refaz(); } },
    { tecla: "espaço", rotulo: "Espaço + arrastar", acao: "Mover o mapa (com zoom)", fn: null }
  ];
  var ATALHO_DE = {};
  ATALHOS.forEach(function (a) { ATALHO_DE[a.acao] = a.rotulo; });
  function comAtalho(texto, acao) { var r = ATALHO_DE[acao]; return r ? texto + " (" + r + ")" : texto; }

  function teclaDoEvento(e) {
    var k = e.key === "Del" ? "delete" : e.key.toLowerCase();
    if (e.ctrlKey || e.metaKey) {
      if (k === "z" && e.shiftKey) return "ctrl+y";
      return "ctrl+" + k;
    }
    if (k === "backspace") return "delete";
    return k;
  }

  function alternaAjuda(abrir) {
    var ja = $("pr-ajuda");
    var abre = abrir === undefined ? !ja : abrir;
    if (ja) ja.parentNode.removeChild(ja);
    S.ajuda = false;
    if (!abre) return;
    var lista = el("dl", { class: "pr-atalhos" });
    ATALHOS.forEach(function (a) {
      lista.appendChild(el("dt", { texto: a.rotulo }));
      lista.appendChild(el("dd", { texto: a.acao }));
    });
    var painel = el("div", { id: "pr-ajuda", class: "pr-ajuda", role: "dialog", "aria-label": "Atalhos da prancheta" },
      [el("h3", { texto: "Atalhos" }), lista,
       el("button", { class: "pr-b", texto: "Fechar (Esc)", onclick: function () { alternaAjuda(false); } })]);
    $("pr-palco").appendChild(painel);
    S.ajuda = true;
  }

  function novoPasso() {
    emite("cria_passo", { passo: novoId(), titulo: "" });
    mudaPasso(S.estado.passos.length - 1);
  }

  /* --- roda: gira a peça selecionada sob o ponteiro, ou dá zoom ------------ */
  function roda(e) {
    e.preventDefault();
    if (S.reproducao) {
      var pz = eventoParaPixel(e);
      aplicaZoom(S.view.zoom * (e.deltaY < 0 ? MapCore.ZOOM_PASSO : 1 / MapCore.ZOOM_PASSO),
                 pz[0] * S.view.zoom + S.view.panX, pz[1] * S.view.zoom + S.view.panY);
      return;
    }
    var px = eventoParaPixel(e);
    var q = quadro();
    if (S.sel && S.sel.tipo === "peca" && q.pecas[S.sel.id]) {
      var p = q.pecas[S.sel.id], c = jogoParaPixel(p.x, p.y);
      if (Math.hypot(c[0] - px[0], c[1] - px[1]) <= RAIO_PECA + 3) {
        var base = S.giro && S.giro.peca === S.sel.id ? S.giro.yaw : p.yaw;
        var passo = e.shiftKey ? PASSO_GIRO_FINO : PASSO_GIRO;
        // roda para cima gira no sentido anti-horário da tela = yaw crescente
        var novo = yawInteiro(base + (e.deltaY < 0 ? passo : -passo));
        if (!S.giro) S.giro = { peca: S.sel.id, yaw: novo, timer: null };
        S.giro.yaw = novo;
        clearTimeout(S.giro.timer);
        S.giro.timer = setTimeout(confirmaGiro, MS_AGRUPA_GIRO);
        desenha(); atualizaPainel();
        return;
      }
    }
    var z = px[0] * S.view.zoom + S.view.panX, w = px[1] * S.view.zoom + S.view.panY;
    aplicaZoom(S.view.zoom * (e.deltaY < 0 ? MapCore.ZOOM_PASSO : 1 / MapCore.ZOOM_PASSO), z, w);
  }

  function confirmaGiro() {
    var g = S.giro;
    if (!g) return;
    clearTimeout(g.timer);
    S.giro = null;
    if (S.estado.pecas[g.peca]) emite("gira_peca", { peca: g.peca, passo: passoAtual(), yaw: g.yaw });
  }

  /* --- desenho livre --------------------------------------------------------- */
  function comecaTraco(e, px, g) {
    cv.setPointerCapture(e.pointerId);
    if (S.ferramenta === "borracha") { apagaTraco(px); return; }
    if (S.ferramenta === "texto") { abreEditorTexto(g); return; }
    S.tracando = { ferramenta: S.ferramenta, pontos: S.ferramenta === "caneta" ? [g] : [g, g],
                   cor: S.cor, espessura: S.espessura };
    desenha();
  }

  function continuaTraco(e) {
    var eventos = (S.tracando.ferramenta === "caneta" && e.getCoalescedEvents) ? e.getCoalescedEvents() : [e];
    if (!eventos.length) eventos = [e];
    eventos.forEach(function (ev) {
      var g = eventoParaJogo(ev), pts = S.tracando.pontos;
      if (S.tracando.ferramenta !== "caneta") { pts[1] = g; return; }
      var ult = jogoParaPixel(pts[pts.length - 1][0], pts[pts.length - 1][1]), novo = jogoParaPixel(g[0], g[1]);
      if (Math.hypot(novo[0] - ult[0], novo[1] - ult[1]) * S.view.zoom >= PASSO_MIN_CANETA) pts.push(g);
    });
    desenha();
  }

  function terminaTraco() {
    var t = S.tracando; S.tracando = null;
    if (MapCore.tracoCurtoDemais(t, cfg.radar)) { desenha(); return; }
    var op = emite("cria_traco", { traco: novoId(), passo: passoAtual(), ferramenta: t.ferramenta,
                                   cor: t.cor, espessura: t.espessura, pontos: t.pontos, nivel: S.andar });
    S.sel = { tipo: "traco", id: op.traco }; atualizaTudo();
  }

  function apagaTraco(px) {
    var q = quadro();
    var alvos = ordemDeCriacao(S.estado).filter(function (x) {
      return x.tipo === "traco" && q.tracos[x.id] && q.tracos[x.id].nivel === S.andar &&
             MapCore.tracoEncosta(q.tracos[x.id], px, cfg.radar, RAIO_BORRACHA);
    });
    if (alvos.length) emite("remove_traco", { traco: alvos[alvos.length - 1].id });
  }

  /* --- banco de peças -------------------------------------------------------- */
  /** Arrastar do banco para o mapa: peça nova, ou -- se esse jogador já existe
      na tática e só não está no mapa neste passo -- a mesma peça de volta. */
  function soltaDoBanco(e, lado, rotulo) {
    if (S.reproducao) return;
    var c = cv.getBoundingClientRect();
    if (e.clientX < c.left || e.clientX > c.right || e.clientY < c.top || e.clientY > c.bottom) return;
    var g = eventoParaJogo(e);
    var existente = Object.keys(S.estado.pecas).filter(function (id) {
      return S.estado.pecas[id].lado === lado && S.estado.pecas[id].rotulo === rotulo;
    })[0];
    if (existente) {
      emite("move_peca", { peca: existente, passo: passoAtual(), x: g[0], y: g[1], nivel: S.andar });
      S.sel = { tipo: "peca", id: existente };
    } else {
      var op = emite("cria_peca", { peca: novoId(), lado: lado, rotulo: rotulo, passo: passoAtual(),
                                    x: g[0], y: g[1], nivel: S.andar });
      S.sel = { tipo: "peca", id: op.peca };
    }
    atualizaTudo();
  }

  function removeSelecionado() {
    if (!S.sel) return;
    if (S.sel.tipo === "peca") emite("remove_peca", { peca: S.sel.id });
    else if (S.sel.tipo === "granada") emite("remove_granada", { granada: S.sel.id });
    else emite("remove_traco", { traco: S.sel.id });
    S.sel = null; atualizaTudo();
  }

  /* ---------------------------------------------------------------------
     Arremessos reais: "quero a granada AQUI"
     --------------------------------------------------------------------- */
  function busca(ponto, arma) {
    var arr = (cfg.biblioteca && cfg.biblioteca.arremessos) || [];
    var raio = S.raioBusca, res = [];
    arma = arma || S.arma;
    arr.forEach(function (r) {
      if (r.arma !== arma) return;
      if (S.soParado && (r.movimento !== "parado" || r.no_ar)) return;
      var d = Math.hypot(r.destino[0] - ponto[0], r.destino[1] - ponto[1]);
      if (d <= raio) res.push({ r: r, d: d });
    });
    res.sort(function (a, b) { return a.d - b.d || (a.r.id < b.r.id ? -1 : 1); });
    S.busca = { ponto: ponto, raio: raio, total: res.length, arma: arma,
                resultados: res.slice(0, MAX_RESULTADOS).map(function (x) { return x.r; }), foco: null };
    desenha(); atualizaBusca();
  }

  function usaArremesso(r) {
    var op = emite("cria_granada", {
      granada: novoId(), arma: r.arma, passo: passoAtual(), nivel: nivelDoZ(r.origem[2]),
      origem: r.origem.slice(0, 2), destino: r.destino.slice(0, 2), arremesso: r
    });
    S.sel = { tipo: "granada", id: op.granada };
    S.busca = null; S.sugestao = null; S.acao = null; S.ferramenta = "mover";
    atualizaTudo();
  }

  /* ---------------------------------------------------------------------
     Painéis. Todo texto sai daqui, a partir do dado.
     --------------------------------------------------------------------- */
  function el(tag, attrs, filhos) {
    var n = document.createElement(tag);
    Object.keys(attrs || {}).forEach(function (k) {
      if (k === "texto") n.textContent = attrs[k];
      else if (k.indexOf("on") === 0) n.addEventListener(k.slice(2), attrs[k]);
      else n.setAttribute(k, attrs[k]);
    });
    (filhos || []).forEach(function (f) { if (f) n.appendChild(f); });
    return n;
  }
  function limpa(n) { while (n.firstChild) n.removeChild(n.firstChild); return n; }

  function tempo(seg) {
    if (seg == null) return "";
    var s = Math.max(0, Math.round(seg));
    return Math.floor(s / 60) + ":" + String(s % 60).padStart(2, "0");
  }

  function descreveArremesso(r) {
    var partes = [];
    // força AFIRMADA só com botão (rotina do jogo, decisão 21a); sem ele, a
    // velocidade é estimativa do modelo e aparece como tal
    if (r.forca && r.botao) partes.push(r.forca + " (" + r.botao + ")");
    else if (r.velocidade !== null && r.velocidade !== undefined) partes.push("força não afirmada (estimativa: " + r.velocidade + " u/s)");
    if (r.postura) partes.push(r.postura);
    if (r.movimento) partes.push(r.movimento);
    if (r.no_ar) partes.push("no ar (pulo)");
    return partes.join(" · ");
  }

  /** De onde veio cada afirmação da ficha (rota B, decisão 21a): "lido" da
      demo ou "inferido" pela rotina do jogo. Discreto, mas nunca omitido. */
  var NOME_DA_FONTE = { botao: "botão", postura: "postura", no_ar: "no ar", origem: "saída" };
  function descreveFontes(fontes) {
    if (!fontes) return "";
    var por = { lido: [], inferido: [] };
    Object.keys(NOME_DA_FONTE).forEach(function (k) {
      if (por[fontes[k]]) por[fontes[k]].push(NOME_DA_FONTE[k]);
    });
    var partes = [];
    if (por.lido.length) partes.push("lido da demo: " + por.lido.join(", "));
    if (por.inferido.length) partes.push("inferido pela rotina do jogo: " + por.inferido.join(", "));
    return partes.join(" · ");
  }

  // Uma tática no meio da criação (antes do primeiro passo) não tem quadro.
  function temQuadro() { return !!(S.estado && S.estado.passos.length); }

  var bancoDe = null;   // de que tática o banco foi montado

  function atualizaTudo() {
    if (!temQuadro()) return;
    if (bancoDe !== S.doc.id) { bancoDe = S.doc.id; montaBanco(); }
    atualizaBiblioteca(); atualizaPassos(); atualizaPainel(); atualizaBusca(); atualizaFerramentas();
    atualizaBanco(); atualizaBarra(); atualizaAviso(); atualizaContexto(); atualizaDica(); desenha();
  }

  function atualizaAviso() { $("pr-aviso").textContent = S.aviso; $("pr-aviso").hidden = !S.aviso; }

  function atualizaBiblioteca() {
    var sel = limpa($("pr-taticas"));
    var lista = Armazem.lista(cfg.mapa), atual = false;
    lista.forEach(function (r) {
      var o = el("option", { value: r.id, texto: r.titulo + (r.autores.length > 1 ? " · " + r.autores.length + " autores" : "") });
      if (S.doc && r.id === S.doc.id) { o.selected = true; atual = true; }
      sel.appendChild(o);
    });
    if (S.doc && !atual) {
      // fora da lista: ou está vazia (não é gravada) ou a gravação ainda está no atraso
      sel.insertBefore(el("option", { value: S.doc.id, texto: (S.estado.titulo || "Nova tática") + (vazia(S.doc) ? " (vazia)" : "") }), sel.firstChild);
      sel.value = S.doc.id;
    }
    if (document.activeElement !== $("pr-titulo")) $("pr-titulo").value = S.estado ? S.estado.titulo : "";
    $("pr-historico").textContent = S.doc ? S.doc.operacoes.length + " operações · contador " + S.doc.contador : "";
    var desc = $("pr-origem");
    desc.textContent = S.doc && S.doc.origem ? textoDaOrigem(S.doc.origem) : "";
    desc.hidden = !(S.doc && S.doc.origem);
  }

  function atualizaPassos() {
    var barra = limpa($("pr-passos"));
    S.estado.passos.forEach(function (p, i) {
      barra.appendChild(el("button", {
        class: "pr-passo" + (i === S.passo ? " ativo" : ""), "data-passo": String(i + 1),
        title: p.titulo || "Passo " + (i + 1), texto: String(i + 1),
        onclick: function () { mudaPasso(i); }
      }));
    });
    barra.appendChild(el("button", { class: "pr-passo novo", id: "pr-novo-passo", title: comAtalho("Novo passo", "Novo passo"),
      texto: "+", onclick: novoPasso }));
    var atual = S.estado.passos[S.passo];
    if (document.activeElement !== $("pr-passo-titulo")) $("pr-passo-titulo").value = atual ? atual.titulo : "";
    if (document.activeElement !== $("pr-passo-duracao")) $("pr-passo-duracao").value = atual ? String(atual.duracao_s) : "";
    $("pr-remove-passo").disabled = S.estado.passos.length <= 1;
  }

  function atualizaFerramentas() {
    var estado = estadoDaInteracao();
    Array.prototype.forEach.call(document.querySelectorAll("[data-ferramenta]"), function (b) {
      var f = b.getAttribute("data-ferramenta");
      var ativo = f === "mover" ? (S.ferramenta === "mover" && !S.acao)
                : f === "buscar" ? estado === "buscando"
                : f === "granada" ? !!(S.acao && S.acao.legado)
                : f === S.ferramenta;
      b.classList.toggle("ativo", ativo);
    });
    Array.prototype.forEach.call(document.querySelectorAll("[data-arma]"), function (b) {
      b.classList.toggle("ativo", !!(S.acao && (S.acao.tipo === "granada" || S.acao.tipo === "busca") &&
                                     b.getAttribute("data-arma") === S.acao.arma));
    });
    Array.prototype.forEach.call(document.querySelectorAll("[data-espessura]"), function (b) {
      b.classList.toggle("ativo", b.getAttribute("data-espessura") === String(S.espessura));
    });
  }

  /** Controles de contexto: só aparecem quando servem. Cor e espessura com uma
      ferramenta de desenho; raio e "só parados" com as sugestões (ou a busca). */
  function atualizaContexto() {
    var desenho = !!(ROTULO_FERRAMENTA[S.ferramenta]) && S.ferramenta !== "borracha";
    var ctxDesenho = $("pr-contexto-desenho");
    if (ctxDesenho) ctxDesenho.hidden = !desenho;
    var comBusca = !!(S.busca || (S.acao && S.acao.tipo === "busca"));
    var filtros = $("pr-filtros-busca");
    if (filtros) filtros.hidden = !comBusca;
  }

  function atualizaBanco() {
    var q = quadro();
    Array.prototype.forEach.call(document.querySelectorAll(".pr-ficha"), function (f) {
      var noMapa = Object.keys(q.pecas).some(function (id) {
        return q.pecas[id].lado === f.getAttribute("data-lado") && q.pecas[id].rotulo === f.getAttribute("data-rotulo");
      });
      f.classList.toggle("no-mapa", noMapa);
      f.title = noMapa ? "No mapa neste passo: clique para selecionar, ou arraste para mover"
                       : "Clique e depois clique no mapa para colocar, ou arraste para o mapa";
      f.classList.toggle("armada", !!(S.acao && S.acao.tipo === "colocar" && S.acao.lado === f.getAttribute("data-lado") &&
                                      S.acao.rotulo === f.getAttribute("data-rotulo")));
    });
  }

  function atualizaBarra() {
    var z = $("pr-zoom");
    if (z) z.textContent = Math.round(S.view.zoom * 100) + "%";
    var d = $("pr-desfaz"), r = $("pr-refaz");
    if (d) d.disabled = !S.pilhaDesfazer.length;
    if (r) r.disabled = !S.pilhaRefazer.length;
    Array.prototype.forEach.call(document.querySelectorAll("[data-andar]"), function (b) {
      b.classList.toggle("ativo", Number(b.getAttribute("data-andar")) === S.andar);
    });
    var fs = $("pr-tela-cheia");
    if (fs) fs.textContent = emTelaCheia() ? "Sair" : "Tela cheia";
    if (cores) cores.atualizaCores();
  }

  function controleDeVida(alvo, dura) {
    var fim = dura === null || dura === undefined;
    var n = el("input", { type: "number", id: "pr-vida", min: "1", step: "1", value: fim ? "1" : String(dura) });
    var ate = el("input", { type: "checkbox", id: "pr-vida-fim" });
    ate.checked = fim; n.disabled = fim;
    function aplicaVida() {
      var v = ate.checked ? null : Math.max(1, Math.round(+n.value || 1));
      emite("define_vida", { alvo: alvo, dura_passos: v });
    }
    n.addEventListener("change", aplicaVida);
    ate.addEventListener("change", aplicaVida);
    return el("div", { class: "linha" }, [el("label", { for: "pr-vida", texto: "Fica por" }), n,
      el("span", { texto: "passo(s)" }), el("label", {}, [ate, el("span", { texto: " até o fim" })])]);
  }

  function atualizaPainel() {
    var box = limpa($("pr-selecao"));
    if (!S.sel) {
      box.appendChild(el("p", { class: "pr-dica", texto: "Nada selecionado. Clique num jogador no mapa ou no banco; com ele selecionado, 1 a 4 joga uma granada a partir dele." }));
      return;
    }
    var q = quadro();
    if (S.sel.tipo === "peca") {
      var p = S.estado.pecas[S.sel.id];
      var noQuadro = q.pecas[S.sel.id];
      box.appendChild(el("h3", { texto: rotuloDaPeca(p) }));
      if (noQuadro) {
        var yaw = yawDaPeca(S.sel.id, noQuadro);
        box.appendChild(el("p", { class: "pr-meta", id: "pr-peca-direcao",
          texto: (noQuadro.direcao_padrao && !S.giro ? "Olhando para o centro do mapa (" : "Olhando para ") + Math.round(yaw) + "°" + (noQuadro.direcao_padrao && !S.giro ? ", direção padrão)" : "") }));
        box.appendChild(el("div", { class: "linha" }, [
          el("button", { class: "pr-b", id: "pr-gira-anti", texto: "\u21ba 15\u00b0", title: comAtalho("Girar 15\u00b0 no sentido anti-horário", ATALHOS[10].acao),
            onclick: function () { giraSelecionada(PASSO_GIRO); } }),
          el("button", { class: "pr-b", id: "pr-gira-hor", texto: "\u21bb 15\u00b0", title: comAtalho("Girar 15\u00b0 no sentido horário", ATALHOS[11].acao),
            onclick: function () { giraSelecionada(-PASSO_GIRO); } })]));
        box.appendChild(el("button", { class: "pr-b", id: "pr-tira-peca", texto: "Tirar do mapa neste passo",
          onclick: function () { emite("tira_peca", { peca: S.sel.id, passo: passoAtual() }); } }));
      } else {
        box.appendChild(el("p", { class: "pr-meta", texto: "Fora do mapa neste passo: arraste do banco para recolocar." }));
      }
      box.appendChild(el("button", { class: "pr-b", id: "pr-apaga-peca", texto: "Apagar peça da tática", onclick: removeSelecionado }));
      return;
    }
    if (S.sel.tipo === "traco") {
      var t = S.estado.tracos[S.sel.id];
      box.appendChild(el("h3", { texto: ROTULO_FERRAMENTA[t.ferramenta] + " · passo " + (indiceDoPasso(t.passo) + 1) }));
      box.appendChild(controleDeVida(S.sel.id, t.dura_passos));
      box.appendChild(el("button", { class: "pr-b", texto: "Apagar desenho", onclick: removeSelecionado }));
      return;
    }
    var g = S.estado.granadas[S.sel.id];
    box.appendChild(el("h3", { texto: NOME_ARMA[g.arma] + " · passo " + (indiceDoPasso(g.passo) + 1) }));
    if (g.arremesso) {
      var r = g.arremesso;
      box.appendChild(el("p", { class: "pr-meta", texto: r.jogador + " · " + r.partida + " round " + r.round + " (" + tempo(r.segundos_no_round) + ")" }));
      box.appendChild(el("p", { class: "pr-meta", texto: descreveArremesso(r) }));
      var fonte = descreveFontes(r.fontes);
      if (fonte) box.appendChild(el("p", { class: "pr-fonte", id: "pr-fonte", texto: fonte }));
      var cmd = el("code", { id: "pr-comando", texto: r.comando });
      box.appendChild(el("div", { class: "pr-cmd" }, [cmd, el("button", { class: "pr-b", id: "pr-copia", texto: "Copiar",
        onclick: function () { copiaTexto(r.comando); } })]));
      if (r.movimento && r.movimento !== "parado") {
        box.appendChild(el("p", { class: "pr-alerta", texto: "O arremesso original foi " + r.movimento +
          ": o comando põe você na posição e no ângulo da soltura, mas repetir exige o mesmo movimento." }));
      }
      if (r.no_ar) {
        box.appendChild(el("p", { class: "pr-alerta", texto: "O arremesso original saiu no ar: o comando dá a posição do chão, e repetir exige o pulo." }));
      }
      if (!(cfg.biblioteca && cfg.biblioteca.comando_conferido_no_jogo)) {
        box.appendChild(el("p", { class: "pr-alerta", texto: "Comando ainda não conferido no jogo: confira onde a granada cai antes de treinar." }));
      }
    } else if (g.origem_desconhecida) {
      box.appendChild(el("p", { class: "pr-meta", texto: "Veio do replay sem ligação com o arremesso: só o efeito é conhecido, e a origem fica em branco." }));
    } else {
      box.appendChild(el("p", { class: "pr-meta", texto: "Desenhada à mão: mostra onde cai, não como chegar lá." }));
    }
    box.appendChild(controleDeVida(S.sel.id, g.dura_passos));
    box.appendChild(el("button", { class: "pr-b", texto: "Apagar granada", onclick: removeSelecionado }));
  }

  function atualizaBusca() {
    var box = limpa($("pr-resultados"));
    if (!S.busca) return;
    var b = S.busca;
    if (S.sugestao) {
      box.appendChild(el("button", { class: "pr-b pr-manter", id: "pr-manter-mao",
        texto: "Desenhar à mão, saindo de " + S.sugestao.de + " (já está no mapa)",
        onclick: function () { S.busca = null; S.sugestao = null; atualizaTudo(); } }));
    }
    box.appendChild(el("p", { class: "pr-meta", texto: b.total === 0
      ? "Nenhum arremesso real de " + NOME_ARMA[b.arma] + " cai a menos de " + b.raio + "u daqui no corpus."
      : b.total + " arremessos reais de " + NOME_ARMA[b.arma] + " caem a menos de " + b.raio + "u daqui" +
        (b.total > b.resultados.length ? " (os " + b.resultados.length + " mais perto)" : "") + "." }));
    var lista = el("ol", { class: "pr-lista" });
    b.resultados.forEach(function (r, n) {
      lista.appendChild(el("li", {
        "data-arremesso": r.id,
        onmouseenter: function () { S.busca.foco = n; desenha(); },
        onmouseleave: function () { S.busca.foco = null; desenha(); },
        onclick: function () { if (S.sugestao) trocaPorArremesso(r); else usaArremesso(r); }
      }, [el("strong", { texto: r.jogador }), el("span", { texto: " " + r.partida + " r" + r.round + " · " + descreveArremesso(r) })]));
    });
    box.appendChild(lista);
  }

  function copiaTexto(texto) {
    var feito = function () { $("pr-copia").textContent = "Copiado"; };
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(texto).then(feito, function () { copiaAntigo(texto); feito(); });
    } else { copiaAntigo(texto); feito(); }
  }
  function copiaAntigo(texto) {
    var t = el("textarea", {}); t.value = texto; document.body.appendChild(t); t.select();
    try { document.execCommand("copy"); } catch (e) { /* sem área de transferência */ }
    document.body.removeChild(t);
  }

  /* ---------------------------------------------------------------------
     Arquivo: exportar e importar (importar a MESMA tática mescla)
     --------------------------------------------------------------------- */
  function exporta() {
    confirmaGiro();
    gravaAgora();
    var doc = Object.assign({}, S.doc, { versao: FORMATO });
    var blob = new Blob([JSON.stringify(doc, null, 1)], { type: "application/json" });
    var a = el("a", { href: URL.createObjectURL(blob),
                      download: (S.estado.titulo || "tatica").replace(/[^\w\-]+/g, "_") + "." + cfg.mapa + ".json" });
    document.body.appendChild(a); a.click(); document.body.removeChild(a);
  }

  /** Motivo da recusa, ou "" -- nunca carrega pela metade. */
  function motivoDaRecusa(doc) {
    var erros = problemas(doc, ANDARES.length);
    if (erros.length) return erros.slice(0, 3).join("; ") + (erros.length > 3 ? " (e mais " + (erros.length - 3) + ")" : "");
    if (doc.mapa !== cfg.mapa) return "a tática é de " + doc.mapa + ", e esta prancheta é de " + cfg.mapa;
    if (doc.calibracao !== cfg.radar.calibracao) return "a tática foi feita sobre outra calibração do radar e precisa ser reprojetada";
    return "";
  }

  function importaTexto(texto) {
    var doc;
    try { doc = JSON.parse(texto); } catch (e) { S.aviso = "Arquivo não é JSON."; atualizaAviso(); return false; }
    var erro = motivoDaRecusa(doc);
    if (erro) { S.aviso = "Importação recusada: " + erro + "."; atualizaAviso(); return false; }
    confirmaGiro();
    doc = migra(doc);
    // A cópia local é a da MEMÓRIA quando é a tática aberta: a gravação tem
    // atraso, e mesclar com a do armazém perderia o que acabou de ser feito.
    var local = (S.doc && S.doc.id === doc.id) ? S.doc : Armazem.carrega(doc.id);
    var mesma = S.doc && S.doc.id === doc.id;
    S.doc = local ? mescla(migra(local), doc) : doc;
    if (!mesma) { S.passo = 0; S.pilhaDesfazer = []; S.pilhaRefazer = []; }
    S.sel = null; S.busca = null;
    S.aviso = "";
    reaplica();
    gravaAgora();
    return true;
  }

  /* ---------------------------------------------------------------------
     Montagem
     --------------------------------------------------------------------- */
  /** O banco: "TR 1..5" e "CT 1..5", ou -- em tática que veio de um instante do
      replay -- os jogadores REAIS do round, vivos e mortos, lidos do metadado
      `origem` (nunca inferidos dos rótulos). */
  function montaBanco() {
    var banco = limpa($("pr-banco"));
    var elenco = S.doc && S.doc.origem && S.doc.origem.elenco;
    banco.classList.toggle("nomes", !!elenco);
    LADOS.forEach(function (lado) {
      var rotulos = elenco
        ? elenco.filter(function (j) { return j.lado === lado; }).map(function (j) { return j.nome; })
        : [1, 2, 3, 4, 5].slice(0, PECAS_POR_LADO).map(String);
      rotulos.forEach(function (rotulo) {
        (function (rotulo) {
          var b = el("div", { class: "pr-ficha " + lado + (elenco ? " nome" : ""), "data-lado": lado,
                              "data-rotulo": rotulo, title: "Arraste para o mapa", texto: rotulo });
          var inicio = null;
          b.addEventListener("pointerdown", function (e) {
            e.preventDefault();
            b.setPointerCapture(e.pointerId);
            b.classList.add("arrastando");
            inicio = { x: e.clientX, y: e.clientY };
          });
          b.addEventListener("pointerup", function (e) {
            b.classList.remove("arrastando");
            if (!S.doc || S.reproducao) return;
            var andou = inicio && Math.hypot(e.clientX - inicio.x, e.clientY - inicio.y) >= LIMIAR_ARRASTO_PX;
            inicio = null;
            if (andou) soltaDoBanco(e, lado, rotulo);      // arrasto: como sempre
            else cliqueNaFicha(lado, rotulo);              // clique: seleciona ou arma a colocação
          });
          banco.appendChild(b);
        })(rotulo);
      });
    });
  }

  /** A barra única, na ordem de "o que eu quero fazer agora": selecionar,
      granadas, desenho | desfazer, reproduzir, vista, andares. Cor e espessura
      ficam num grupo de CONTEXTO que só aparece com uma ferramenta de desenho.
      Todo botão mostra o atalho na dica. */
  var ATALHO_DA_ARMA = { smoke: "Smoke", flash: "Flash", he: "HE", molotov: "Molotov" };
  var DICA_DA_FERRAMENTA = { caneta: "Caneta", seta: "Seta", linha: "Linha", texto: "Texto", borracha: "Borracha" };

  function montaBarra() {
    var barra = limpa($("pr-barra"));
    var botaoF = function (id, texto, dica) {
      return el("button", { "data-ferramenta": id, texto: texto, title: dica,
                            onclick: function () { escolheFerramenta(id); } });
    };

    var ferramentas = el("div", { class: "anot-grupo sempre", id: "pr-ferramentas" });
    var sel = botaoF("mover", "Selecionar", comAtalho("Selecionar e mover", "Selecionar"));
    sel.id = "pr-selecionar";
    ferramentas.appendChild(sel);
    barra.appendChild(ferramentas);

    var granadas = el("div", { class: "anot-grupo sempre", id: "pr-granadas" });
    ["smoke", "flash", "he", "molotov"].forEach(function (a) {
      granadas.appendChild(el("button", { "data-arma": a, texto: NOME_ARMA[a],
        title: comAtalho(NOME_ARMA[a] + ": com um jogador selecionado sai dele; senão, clique em quem joga", ATALHO_DA_ARMA[a]),
        onclick: function () { escolheArma(a); } }));
    });
    barra.appendChild(granadas);

    var desenho = el("div", { class: "anot-grupo sempre", id: "pr-desenho" });
    Object.keys(ROTULO_FERRAMENTA).forEach(function (id) {
      var nome = id === "borracha" ? "Borracha" : ROTULO_FERRAMENTA[id];
      desenho.appendChild(botaoF(id, nome, DICA_DA_FERRAMENTA[id] ? comAtalho(nome, DICA_DA_FERRAMENTA[id]) : nome));
    });
    barra.appendChild(desenho);

    var contexto = el("div", { class: "anot-grupo sempre", id: "pr-contexto-desenho" });
    cores = MapCore.seletorDeCor({
      estado: S, armazem: MapCore.criaArmazem(), chaveRecentes: CHAVE_RECENTES, maxRecentes: MAX_RECENTES,
      palco: function () { return $("pr-palco"); }, aoMudar: function () { atualizaBarra(); }
    });
    contexto.appendChild(cores.montaCor());
    ESPESSURAS.forEach(function (v, i) {
      contexto.appendChild(el("button", { "data-espessura": String(v), class: "pr-b", texto: ROTULOS_ESPESSURA[i],
        title: "Espessura " + ROTULOS_ESPESSURA[i], onclick: function () { S.espessura = v; atualizaFerramentas(); } }));
    });
    contexto.hidden = true;
    barra.appendChild(contexto);

    barra.appendChild(el("span", { class: "pr-separador", "aria-hidden": "true" }));

    var historico = el("div", { class: "anot-grupo sempre" });
    var d = MapCore.botao("Desfazer", comAtalho("Desfazer", "Desfazer"), desfaz); d.id = "pr-desfaz";
    var r = MapCore.botao("Refazer", comAtalho("Refazer", "Refazer (também Ctrl+Shift+Z)"), refaz); r.id = "pr-refaz";
    historico.appendChild(d); historico.appendChild(r);
    barra.appendChild(historico);

    var vista = el("div", { class: "anot-grupo sempre" });
    var reproduzir = MapCore.botao("Reproduzir", "Reproduzir a tática passo a passo", comecaReproducao, "principal");
    reproduzir.id = "pr-reproduzir";
    vista.appendChild(reproduzir);
    vista.appendChild(MapCore.botao("\u2212", "Diminuir o zoom", function () { aplicaZoom(S.view.zoom / MapCore.ZOOM_PASSO); }));
    var lupa = MapCore.botao("100%", comAtalho("Voltar ao tamanho original", "Zoom original") +
                             ". Com zoom, segure espaço e arraste para mover o mapa", resetaZoom);
    lupa.id = "pr-zoom";
    vista.appendChild(lupa);
    vista.appendChild(MapCore.botao("+", "Aumentar o zoom", function () { aplicaZoom(S.view.zoom * MapCore.ZOOM_PASSO); }));
    var fs = MapCore.botao("Tela cheia", comAtalho("Mapa em tela cheia", "Tela cheia"), function () { MapCore.alternaTelaCheia($("pr-palco")); });
    fs.id = "pr-tela-cheia";
    vista.appendChild(fs);
    vista.appendChild(MapCore.botao("?", comAtalho("Atalhos", "Ajuda: esta lista"), function () { alternaAjuda(); }));
    barra.appendChild(vista);

    if (ANDARES.length > 1) {
      var andares = el("div", { class: "anot-grupo sempre", id: "pr-andares" });
      ANDARES.forEach(function (a, i) {
        andares.appendChild(el("button", { "data-andar": String(i),
          texto: i === 0 ? "Andar de cima" : (ANDARES.length === 2 ? "Andar de baixo" : "Andar " + (i + 1)),
          onclick: function () { S.andar = i; S.sel = null; S.acao = null; atualizaTudo(); } }));
      });
      barra.appendChild(andares);
    }

    // a linha de dica: sempre com o que o PRÓXIMO clique faz
    if (!$("pr-dica-estado")) {
      var dica = el("p", { id: "pr-dica-estado", class: "pr-dica-estado", role: "status", "aria-live": "polite" });
      $("pr-palco").insertBefore(dica, $("pr-tela"));
    }
  }

  /** O painel lateral, montado aqui (o HTML só tem a estrutura): Jogadores,
      Selecionado, Passos e Tática, mais a busca de arremessos reais. */
  function montaLateral() {
    var lado = limpa(document.querySelector("aside"));
    var caixa = function (titulo, filhos, id) {
      var s = el("section", { class: "caixa" }, [el("h2", { texto: titulo })].concat(filhos));
      if (id) s.id = id;
      lado.appendChild(s);
      return s;
    };
    caixa("Jogadores", [el("div", { id: "pr-banco" }),
      el("p", { class: "pr-dica", texto: "Clique numa ficha e depois no mapa, ou arraste." })]);
    caixa("Selecionado", [el("div", { id: "pr-selecao" })]);
    caixa("Arremessos reais", [
      el("div", { class: "linha", id: "pr-modos" }, [
        el("button", { "data-ferramenta": "mover", texto: "Selecionar", title: comAtalho("Selecionar e mover", "Selecionar"),
          onclick: function () { escolheFerramenta("mover"); } }),
        el("button", { "data-ferramenta": "buscar", texto: "Buscar arremesso",
          title: "Clique onde a granada deve cair e veja os arremessos reais (o mesmo que escolher a granada na barra)",
          onclick: function () { escolheFerramenta("buscar"); } }),
        el("button", { "data-ferramenta": "granada", texto: "Desenhar à mão",
          title: "Clique na origem e depois no destino, sem sugestões",
          onclick: function () { escolheFerramenta("granada"); } })]),
      el("p", { class: "pr-dica", id: "pr-sem-biblioteca", hidden: "" }),
      el("div", { id: "pr-filtros-busca", hidden: "" }, [
        el("div", { class: "linha" }, [el("label", { for: "pr-raio", texto: "Raio da busca" }),
          el("input", { type: "range", id: "pr-raio", min: "50", max: "600", step: "25" }), el("span", { id: "pr-raio-valor" })]),
        el("div", { class: "linha" }, [el("label", {}, [el("input", { type: "checkbox", id: "pr-so-parado" }),
          el("span", { texto: " só arremessos parados (o comando reproduz sozinho)" })])])]),
      el("div", { id: "pr-resultados" })]);
    caixa("Passos", [
      el("div", { class: "linha", id: "pr-passos" }),
      el("div", { class: "linha" }, [el("input", { type: "text", id: "pr-passo-titulo", "aria-label": "Título do passo",
                                                   placeholder: "o que acontece neste passo" })]),
      el("div", { class: "linha" }, [el("label", { for: "pr-passo-duracao", texto: "Duração (s)" }),
        el("input", { type: "number", id: "pr-passo-duracao", min: "0.5", step: "0.5" }),
        el("button", { class: "pr-b", id: "pr-remove-passo", texto: "Remover passo" })])]);
    caixa("Tática", [
      el("div", { class: "linha" }, [el("select", { id: "pr-taticas", "aria-label": "Táticas deste mapa" }),
        el("button", { class: "pr-b", id: "pr-nova", texto: "Nova" })]),
      el("div", { class: "linha" }, [el("input", { type: "text", id: "pr-titulo", "aria-label": "Título da tática" })]),
      el("div", { class: "linha" }, [el("button", { class: "pr-b", id: "pr-exporta", texto: "Exportar" }),
        el("button", { class: "pr-b", id: "pr-importa", texto: "Importar" }),
        el("button", { class: "pr-b", id: "pr-apaga", texto: "Apagar" }),
        el("input", { type: "file", id: "pr-arquivo", accept: ".json,application/json", hidden: "" })]),
      el("div", { class: "linha" }, [el("label", { for: "pr-autor", texto: "Autor" }),
        el("input", { type: "text", id: "pr-autor", placeholder: "seu nome" })]),
      el("p", { class: "pr-meta", id: "pr-origem", hidden: "" }),
      el("p", { id: "pr-historico" }),
      el("p", { id: "pr-aviso", hidden: "" })]);
  }

  /* ---------------------------------------------------------------------
     Reprodução: tocar, pausar, velocidade, barra de tempo, passos, Editar
     --------------------------------------------------------------------- */
  var quadroPedido = null;

  function reproduzAte(t) {
    S.reproducao.t = t;
    S.reproducao.cena = estadoNoTempo(S.estado, t, CENTRO);
    desenha();
    atualizaPlayer();
  }

  function comecaReproducao() {
    if (S.reproducao) return;
    confirmaGiro();
    S.sel = null; S.arrasto = null; S.tracando = null; S.origemPendente = null; S.busca = null;
    S.reproducao = { t: 0, tocando: false, velocidade: 1, cena: null, ultimo: 0 };
    $("pr-barra").hidden = true; $("pr-player").hidden = false;
    if ($("pr-dica-estado")) $("pr-dica-estado").hidden = true;
    // durante a reprodução nada é editável
    document.querySelector("aside").setAttribute("inert", "");
    reproduzAte(0);
    toca(true);
  }

  function editaAqui() {
    if (!S.reproducao) return;
    toca(false);
    S.passo = S.reproducao.cena.indice;
    S.reproducao = null;
    $("pr-barra").hidden = false; $("pr-player").hidden = true;
    if ($("pr-dica-estado")) $("pr-dica-estado").hidden = false;
    document.querySelector("aside").removeAttribute("inert");
    atualizaTudo();
  }

  function toca(sim) {
    var r = S.reproducao;
    if (!r) return;
    if (sim && r.t >= r.cena.total) reproduzAte(0);   // no fim, tocar recomeça
    r.tocando = sim;
    r.ultimo = performance.now();
    cancelAnimationFrame(quadroPedido);
    if (sim) quadroPedido = requestAnimationFrame(avanca);
    atualizaPlayer();
  }

  function avanca(agoraMs) {
    var r = S.reproducao;
    if (!r || !r.tocando) return;
    var dt = Math.max(0, agoraMs - r.ultimo) / 1000;
    r.ultimo = agoraMs;
    var t = Math.min(r.cena.total, r.t + dt * r.velocidade);
    reproduzAte(t);
    if (t >= r.cena.total) { r.tocando = false; atualizaPlayer(); return; }
    quadroPedido = requestAnimationFrame(avanca);
  }

  /** Próximo: o primeiro fim de passo depois de t (é onde o passo fica
      completo). Anterior: o último fim de passo antes de t, ou o começo. */
  function vaiParaPasso(delta) {
    var r = S.reproducao;
    if (!r) return;
    var lt = linhaDoTempo(S.estado), EPS = 1e-9;
    var fins = S.estado.passos.map(function (p, k) { return lt.inicios[k] + p.duracao_s; });
    var alvo;
    if (delta > 0) alvo = fins.filter(function (f) { return f > r.t + EPS; })[0];
    else alvo = fins.filter(function (f) { return f < r.t - EPS; }).pop();
    reproduzAte(alvo === undefined ? (delta > 0 ? lt.total : 0) : alvo);
  }

  function mudaVelocidade(dir) {
    var r = S.reproducao, v = MapCore.VELOCIDADES;
    if (!r) return;
    var i = v.indexOf(r.velocidade);
    r.velocidade = dir === 0 ? v[(i + 1) % v.length] : v[Math.max(0, Math.min(v.length - 1, i + dir))];
    atualizaPlayer();
  }

  function atualizaPlayer() {
    var r = S.reproducao;
    if (!r || !r.cena) return;
    var barra = $("pr-tempo");
    barra.max = String(Math.round(r.cena.total * 1000));
    if (document.activeElement !== barra) barra.value = String(Math.round(r.t * 1000));
    $("pr-toca").textContent = r.tocando ? "Pausar" : "Tocar";
    $("pr-velocidade").textContent = String(r.velocidade).replace(".", ",") + "x";
    var c = r.cena;
    $("pr-rotulo-passo").textContent = "Passo " + (c.indice + 1) + " de " + S.estado.passos.length +
      (c.titulo ? " · " + c.titulo : "") + "  (" + r.t.toFixed(1).replace(".", ",") + " de " +
      c.total.toFixed(1).replace(".", ",") + " s)";
  }

  function montaPlayer() {
    var player = el("div", { class: "pr-barra", id: "pr-player" });
    player.hidden = true;
    var grupo = el("div", { class: "anot-grupo sempre" });
    var b = function (texto, titulo, fn, id) { var x = MapCore.botao(texto, titulo, fn); x.id = id; grupo.appendChild(x); };
    b("◀", "Passo anterior (seta para a esquerda)", function () { vaiParaPasso(-1); }, "pr-passo-anterior");
    b("Tocar", "Tocar ou pausar (espaço)", function () { toca(!S.reproducao.tocando); }, "pr-toca");
    b("▶", "Próximo passo (seta para a direita)", function () { vaiParaPasso(1); }, "pr-passo-seguinte");
    b("1x", "Velocidade ([ e ])", function () { mudaVelocidade(0); }, "pr-velocidade");
    player.appendChild(grupo);
    var tempo = el("input", { type: "range", id: "pr-tempo", min: "0", step: "1", "aria-label": "Linha do tempo da tática" });
    tempo.style.flex = "1";
    tempo.addEventListener("input", function () {
      // lê ANTES de pausar: pausar atualiza a barra com o t atual
      var t = +this.value / 1000;
      toca(false);
      reproduzAte(t);
    });
    player.appendChild(tempo);
    player.appendChild(el("span", { id: "pr-rotulo-passo", class: "pr-meta" }));
    var editar = MapCore.botao("Editar", "Voltar ao editor no passo em que parou", editaAqui);
    editar.id = "pr-editar";
    player.appendChild(editar);
    $("pr-palco").insertBefore(player, $("pr-tela"));
  }

  /** A tática nova a partir de um instante do replay (#instante=...). O
      retrato vem de fora da página: cada jogador é conferido antes de virar
      peça, e o que não fecha fica de fora com aviso -- nunca pela metade
      calado. */
  function criaDoInstante(retrato) {
    var jogadores = (retrato && Array.isArray(retrato.jogadores)) ? retrato.jogadores : [];
    var validos = jogadores.filter(function (j) {
      return j && LADOS.indexOf(j.lado) >= 0 && ehNumero(j.x) && ehNumero(j.y) && typeof j.nome === "string" &&
        (j.yaw === null || j.yaw === undefined || (ehNumero(j.yaw) && j.yaw >= 0 && j.yaw < 360)) &&
        (ehInteiro(j.nivel) && j.nivel >= 0 && j.nivel < ANDARES.length);
    });
    novaTatica();
    // metadado da criação: não é operação e não muda depois (como mapa e calibração)
    var elenco = Array.isArray(retrato.elenco) ? retrato.elenco.filter(function (j) {
      return j && typeof j.nome === "string" && j.nome && LADOS.indexOf(j.lado) >= 0;
    }).map(function (j) { return { nome: j.nome.slice(0, 32), lado: j.lado }; }) : [];
    var nomesDoElenco = {};
    elenco.forEach(function (j) { nomesDoElenco[j.nome] = j.lado; });
    var mortos = Array.isArray(retrato.mortos) ? retrato.mortos.filter(function (m) {
      return m && nomesDoElenco[m.nome] === m.lado && ehInteiro(m.ordem) && m.ordem >= 1;
    }).map(function (m) { return { nome: m.nome, lado: m.lado, ordem: m.ordem }; }) : [];
    var origem = { partida: String(retrato.partida || ""), round: retrato.round, quadro: retrato.quadro,
                   relogio: String(retrato.relogio || ""), elenco: elenco, mortos: mortos };
    if (!problemasDaOrigem(origem).length) S.doc.origem = origem;
    bancoDe = null;   // o banco da tática nova passa a ser o elenco do round
    var passo = passoAtual();
    validos.forEach(function (j) {
      var dados = { peca: novoId(), lado: j.lado, rotulo: j.nome.slice(0, 32), passo: passo,
                    x: j.x, y: j.y, nivel: j.nivel };
      if (j.yaw !== null && j.yaw !== undefined) dados.yaw = j.yaw;
      emite("cria_peca", dados, false);
    });
    // Granadas ativas no instante: com o arremesso real quando ele está na
    // biblioteca, com a posição da soltura quando não está, e só com o efeito
    // (origem_desconhecida) quando o replay não ligou o efeito a arremesso nenhum.
    var granadas = Array.isArray(retrato.granadas) ? retrato.granadas : [];
    var bib = {};
    ((cfg.biblioteca && cfg.biblioteca.arremessos) || []).forEach(function (a) { bib[a.id] = a; });
    var foraGranadas = 0;
    granadas.forEach(function (g) {
      var lance = g && g.lance;
      var ok = g && ARMAS.indexOf(g.arma) >= 0 && Array.isArray(g.destino) && ehNumero(g.destino[0]) && ehNumero(g.destino[1]) &&
        (lance === null || lance === undefined || (typeof lance.id === "string" &&
          (lance.o === null || (Array.isArray(lance.o) && lance.o.length === 3 && lance.o.every(ehNumero)))));
      if (!ok) { foraGranadas++; return; }
      var real = lance && bib[lance.id];
      var dados = { granada: novoId(), arma: g.arma, passo: passo };
      if (real) {
        dados.origem = real.origem.slice(0, 2); dados.destino = real.destino.slice(0, 2);
        dados.nivel = nivelDoZ(real.origem[2]); dados.arremesso = real;
      } else if (lance && lance.o) {
        dados.origem = lance.o.slice(0, 2); dados.destino = [g.destino[0], g.destino[1]];
        dados.nivel = nivelDoZ(lance.o[2]); dados.arremesso = null;
      } else {
        dados.origem = [g.destino[0], g.destino[1]]; dados.destino = [g.destino[0], g.destino[1]];
        dados.nivel = 0; dados.arremesso = null; dados.origem_desconhecida = true;
      }
      emite("cria_granada", dados, false);
    });

    if (retrato && retrato.round !== undefined) {
      // "match_05 · round 9 · 1:12 · 4v3" -- o placar de vivos é TR v CT
      var titulo = (retrato.partida ? retrato.partida + " · " : "") + "round " + retrato.round +
        (retrato.relogio ? " · " + retrato.relogio : "");
      if (S.doc.origem) { var v = placarDeVivos(S.doc.origem); titulo += " · " + v.t + "v" + v.ct; }
      emite("renomeia", { titulo: titulo }, false);
    }
    gravaAgora();   // grava ANTES do aviso: gravar com sucesso limpa o aviso
    var avisos = [];
    if (validos.length !== jogadores.length) {
      avisos.push((jogadores.length - validos.length) + " jogador(es) do instante não puderam ser lidos e ficaram de fora.");
    }
    if (foraGranadas) avisos.push(foraGranadas + " granada(s) do instante não puderam ser lidas e ficaram de fora.");
    if (avisos.length) S.aviso = avisos.join(" ");
    atualizaTudo();
  }

  function escolheFerramenta(id) {
    confirmaGiro();
    if (S.editor) fechaEditorTexto(true);
    S.acao = null; S.busca = null; S.sugestao = null;
    if (id === "buscar") { S.ferramenta = "mover"; S.acao = { tipo: "busca", arma: S.arma }; }
    else if (id === "granada") { S.ferramenta = "mover"; S.acao = { tipo: "granada", arma: S.arma, de: null, origem: null, legado: true }; }
    else S.ferramenta = id;
    atualizaTudo();
  }

  function init(opcoes) {
    cfg = opcoes;
    Armazem = opcoes.armazem || ArmazemDoNavegador("prancheta:");
    ANDARES = andaresDoRadar(cfg.radar);
    CENTRO = centroDoRadar(cfg.radar);
    cv = $("pr-mapa"); ctx = cv.getContext("2d");
    imgs = ANDARES.map(function (a, i) {
      var src = i === 0 ? cfg.radar.image : (cfg.radar.layers || {})[a.nome];
      var im = new Image();
      im.onload = function () { desenha(); };
      if (src) im.src = src;
      return im;
    });
    var armazemCores = MapCore.criaArmazem();
    var rec = MapCore.lerJson(armazemCores.le("localStorage", CHAVE_RECENTES));
    if (Array.isArray(rec)) S.recentes = rec.map(MapCore.normalizaCor).filter(Boolean).slice(0, MAX_RECENTES);
    if (S.recentes.length) S.cor = S.recentes[0];

    montaLateral();
    montaBarra();
    montaPlayer();
    montaBanco();
    cv.addEventListener("pointerdown", pointerDown);
    // o botão direito no mapa é "virar para lá": sem o menu do navegador
    cv.addEventListener("contextmenu", function (e) { e.preventDefault(); });
    cv.addEventListener("pointermove", pointerMove);
    cv.addEventListener("pointerup", pointerUp);
    cv.addEventListener("pointercancel", function () { S.arrasto = null; S.tracando = null; S.pan = null; S.toque = null; desenha(); });
    cv.addEventListener("wheel", roda, { passive: false });

    if (!cfg.biblioteca) {
      // sem partida deste mapa no corpus, não há arremesso real para buscar
      var buscar = document.querySelector('aside [data-ferramenta="buscar"]');
      buscar.disabled = true;
      var motivo = "Sem arremessos reais neste mapa: não há partidas dele no corpus.";
      buscar.title = motivo;
      $("pr-sem-biblioteca").textContent = motivo;
      $("pr-sem-biblioteca").hidden = false;
      $("pr-raio").disabled = true; $("pr-so-parado").disabled = true;
    }
    $("pr-raio").value = String(S.raioBusca);
    $("pr-raio").addEventListener("input", function () {
      S.raioBusca = +this.value; $("pr-raio-valor").textContent = this.value + "u";
      if (S.busca) busca(S.busca.ponto, S.busca.arma);
    });
    $("pr-raio-valor").textContent = S.raioBusca + "u";
    $("pr-so-parado").addEventListener("change", function () {
      S.soParado = this.checked;
      if (S.busca) busca(S.busca.ponto, S.busca.arma);
    });

    $("pr-nova").addEventListener("click", function () { gravaAgora(); novaTatica(); });
    $("pr-taticas").addEventListener("change", function () {
      // lê a escolha ANTES de gravar: gravar reconstrói a lista com a atual marcada
      var escolhida = this.value;
      if (escolhida !== S.doc.id) { gravaAgora(); abre(escolhida); }
    });
    $("pr-titulo").addEventListener("change", function () { emite("renomeia", { titulo: this.value.trim() }); });
    $("pr-passo-titulo").addEventListener("change", function () {
      emite("renomeia_passo", { passo: passoAtual(), titulo: this.value.trim() });
    });
    $("pr-passo-duracao").addEventListener("change", function () {
      var s = +this.value;
      if (s > 0) emite("define_duracao", { passo: passoAtual(), segundos: s });
      else atualizaPassos();
    });
    $("pr-remove-passo").addEventListener("click", function () {
      if (S.estado.passos.length <= 1) return;
      emite("remove_passo", { passo: passoAtual() });
      S.passo = Math.max(0, S.passo - 1); atualizaTudo();
    });
    $("pr-apaga").addEventListener("click", function () {
      if (!S.doc || !window.confirm("Apagar esta tática deste navegador?")) return;
      Armazem.apaga(S.doc.id);
      var resto = Armazem.lista(cfg.mapa);
      if (!(resto.length && abre(resto[0].id))) novaTatica();
    });
    $("pr-exporta").addEventListener("click", exporta);
    var arquivo = $("pr-arquivo");
    $("pr-importa").addEventListener("click", function () { arquivo.click(); });
    arquivo.addEventListener("change", function () {
      var f = arquivo.files && arquivo.files[0]; if (!f) return;
      var leitor = new FileReader();
      leitor.onload = function () { importaTexto(String(leitor.result)); arquivo.value = ""; };
      leitor.readAsText(f);
    });
    $("pr-autor").value = Armazem.autor() || "";
    $("pr-autor").addEventListener("change", function () { Armazem.autor(this.value.trim()); });

    var palco = $("pr-palco");
    palco.addEventListener("pointerenter", function () { S.sobreMapa = true; });
    palco.addEventListener("pointerleave", function () { S.sobreMapa = false; });
    document.addEventListener("keydown", function (e) {
      if (S.reproducao) {
        // os atalhos do replay, com a mesma guarda de foco
        if (e.ctrlKey || e.metaKey || e.altKey) return;
        var foco = document.activeElement;
        if (foco && (/^(INPUT|SELECT|TEXTAREA|BUTTON)$/.test(foco.tagName) || foco.isContentEditable)) return;
        if (e.key === " " || e.key === "Spacebar") { e.preventDefault(); toca(!S.reproducao.tocando); }
        else if (e.key === "ArrowRight") { e.preventDefault(); vaiParaPasso(1); }
        else if (e.key === "ArrowLeft") { e.preventDefault(); vaiParaPasso(-1); }
        else if (e.key === "]") { e.preventDefault(); mudaVelocidade(1); }
        else if (e.key === "[") { e.preventDefault(); mudaVelocidade(-1); }
        else if (e.key === "Escape") { e.preventDefault(); editaAqui(); }
        return;
      }
      if (/^(INPUT|TEXTAREA|SELECT)$/.test((e.target || {}).tagName || "") || (e.target || {}).isContentEditable) return;
      if (e.code === "Space" && (S.sobreMapa || S.espaco) && !e.ctrlKey && !e.metaKey) {
        e.preventDefault();
        if (!S.espaco) { S.espaco = true; palco.classList.add("pr-pan"); }
        return;
      }
      if (e.altKey) return;
      var tecla = teclaDoEvento(e);
      var atalho = ATALHOS.filter(function (a) { return a.tecla === tecla && a.fn; })[0];
      if (!atalho) return;
      e.preventDefault();
      atalho.fn(e);
    });
    document.addEventListener("keyup", function (e) {
      if (e.code === "Space" && S.espaco) { S.espaco = false; palco.classList.remove("pr-pan"); S.pan = null; }
    });
    window.addEventListener("blur", function () { S.espaco = false; palco.classList.remove("pr-pan"); });

    // Todos os gatilhos de tamanho caem na mesma função.
    pedeReprojecao = MapCore.agrupaPorQuadro(reprojeta);
    window.addEventListener("resize", pedeReprojecao);
    document.addEventListener("fullscreenchange", function () { pedeReprojecao(); atualizaBarra(); });
    document.addEventListener("webkitfullscreenchange", function () { pedeReprojecao(); atualizaBarra(); });
    MapCore.vigiaDensidade(pedeReprojecao);
    if (window.ResizeObserver) new ResizeObserver(pedeReprojecao).observe($("pr-tela"));
    window.addEventListener("pagehide", function () { confirmaGiro(); gravaAgora(); });

    // Abre LIMPA ("Criar tática" chega com ?nova), ou a tática aberta nesta aba.
    var nova = /[?&]nova\b/.test(location.search);
    if (nova && window.history && history.replaceState) history.replaceState(null, "", location.pathname);
    var aberta = Armazem.aberta(cfg.mapa);
    var instante = /^#instante=/.test(location.hash) ? location.hash.slice("#instante=".length) : null;
    if (instante !== null && window.history && history.replaceState) history.replaceState(null, "", location.pathname);
    var retrato = null;
    if (instante !== null) {
      try { retrato = JSON.parse(decodeURIComponent(instante)); } catch (e) { retrato = null; }
    }
    if (instante !== null) {
      if (retrato) criaDoInstante(retrato);
      else { novaTatica(); S.aviso = "O instante do replay não pôde ser lido."; atualizaAviso(); }
    } else if (nova || !(aberta && abre(aberta))) novaTatica();
    reprojeta();
  }

  return {
    init: init,
    _interno: {
      S: S, aplica: aplica, mescla: mescla, posicaoNoPasso: posicaoNoPasso, migra: migra,
      quadroDoPasso: quadroDoPasso, ordemDeCriacao: ordemDeCriacao, anuladas: anuladas,
      estadoNoTempo: estadoNoTempo, linhaDoTempo: linhaDoTempo, reproduzAte: function (t) { reproduzAte(t); },
      comecaReproducao: comecaReproducao, editaAqui: editaAqui, toca: function (s) { toca(s); },
      problemas: problemas, problemasDaOrigem: problemasDaOrigem, textoDaOrigem: textoDaOrigem,
      centro: function () { return CENTRO; },
      jogoParaPixel: jogoParaPixel, pixelParaJogo: pixelParaJogo,
      importaTexto: importaTexto, gravaAgora: gravaAgora, busca: busca, usaArremesso: usaArremesso,
      desfaz: desfaz, refaz: refaz, aplicaZoom: aplicaZoom, reprojeta: reprojeta,
      alca: function (id) { var p = quadro().pecas[id]; return alca(jogoParaPixel(p.x, p.y), yawDaPeca(id, p)); },
      FERRAMENTAS_TRACO: FERRAMENTAS_TRACO, ESPESSURAS: ESPESSURAS, FORMATO: FORMATO,
      ESTADOS: ESTADOS, estadoDaInteracao: estadoDaInteracao, dicaAtual: dicaAtual,
      descreveFontes: descreveFontes,
      ATALHOS: ATALHOS.map(function (x) { return { tecla: x.tecla, rotulo: x.rotulo, acao: x.acao }; }),
      LIMIAR_ARRASTO_PX: LIMIAR_ARRASTO_PX,
      armazem: function () { return Armazem; },
      radar: function () { return cfg.radar; }
    }
  };
})();
