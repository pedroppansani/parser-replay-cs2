  /* ---------------------------------------------------------------------
     UMA validação de operação (B-1 da revisão de segurança dos grupos). Toda
     operação que entra de fora -- arquivo importado, tática guardada no
     navegador, documento e operações ao vivo do grupo -- passa por
     `problemaDaOperacao`, a espelhada de metrics.tactics.problemas_da_operacao
     (há teste de espelho com a lista de operações malformadas). `problemas`
     só soma o que depende do log inteiro (id repetido, alvo do desfazer).
     --------------------------------------------------------------------- */
  var SEQ_MAXIMO = 999999999999999;            // 15 dígitos: o mesmo teto do servidor do grupo
  var ID_DA_OPERACAO = /^[0-9A-Za-z_-]{1,64}$/;   // o formato que o servidor exige em op.id
  var TAMANHO_MAXIMO_DA_CHAVE = 128;
  // nomes que um objeto já tem: nunca são chave de peça, passo, traço... (estado.pecas[chave])
  var NOMES_RESERVADOS = ["__proto__", "constructor", "prototype", "hasOwnProperty", "isPrototypeOf",
                          "propertyIsEnumerable", "toLocaleString", "toString", "valueOf",
                          "__defineGetter__", "__defineSetter__", "__lookupGetter__", "__lookupSetter__"];
  var CAMPOS_COMUNS = ["id", "seq", "autor", "em", "tipo"];
  var CAMPOS_CHAVE = ["passo", "peca", "granada", "traco", "ponto", "alvo"];
  var CAMPOS_TEXTO = ["titulo", "rotulo"];

  function ehObjeto(v) { return v !== null && typeof v === "object" && !Array.isArray(v); }
  function tamanhoDoTexto(s) { return Array.from(s).length; }   // pontos de código, como o len do Python
  function seqValido(v) { return ehInteiro(v) && v >= 1 && v <= SEQ_MAXIMO; }
  function ehChave(v) {
    return typeof v === "string" && tamanhoDoTexto(v) >= 1 && tamanhoDoTexto(v) <= TAMANHO_MAXIMO_DA_CHAVE &&
      NOMES_RESERVADOS.indexOf(v) < 0;
  }
  /** Lista de 2 a 3 números finitos (um lugar do mapa). */
  function ehLugar(v) { return Array.isArray(v) && v.length >= 2 && v.length <= 3 && v.every(ehNumero); }

  /** O TIPO de cada campo (o que aplica e a tela supõem). */
  function problemasDeTipo(op, onde) {
    var erros = [], t = op.tipo;
    OPERACOES[t].forEach(function (c) {
      if (CAMPOS_CHAVE.indexOf(c) >= 0 && !ehChave(op[c])) erros.push(onde + ": '" + c + "' não é um identificador");
      else if (CAMPOS_TEXTO.indexOf(c) >= 0 && typeof op[c] !== "string") erros.push(onde + ": '" + c + "' não é texto");
    });
    if (t === "cria_peca" || t === "move_peca") {   // nos outros tipos, problemasDosCampos já diz "x e y precisam ser números"
      ["x", "y"].forEach(function (c) { if (!ehNumero(op[c])) erros.push(onde + ": '" + c + "' não é número"); });
    }
    if (t === "nota_de_evento" && typeof op.texto !== "string") erros.push(onde + ": 'texto' não é texto");
    if (t === "define_funcao" && op.funcao !== null && typeof op.funcao !== "string") erros.push(onde + ": 'funcao' não é texto nem null");
    if (t === "cria_granada" || t === "move_granada") {
      ["origem", "destino"].forEach(function (c) {
        if (!ehLugar(op[c])) erros.push(onde + ": '" + c + "' não é um lugar (2 ou 3 números)");
      });
    }
    if (t === "cria_granada") {
      if (op.jogador !== undefined && op.jogador !== null && !ehChave(op.jogador)) erros.push(onde + ": 'jogador' não é um identificador");
      var arr = op.arremesso;
      if (arr !== undefined && arr !== null) {
        if (!ehObjeto(arr)) erros.push(onde + ": arremesso não é um objeto");
        else {
          // só o TIPO do que existe; a falta de campo é de "arremesso real sem ..."
          if (["id", "comando"].some(function (c) { return tem(arr, c) && typeof arr[c] !== "string"; })) erros.push(onde + ": arremesso com id ou comando que não é texto");
          if (["origem", "destino"].some(function (c) { return tem(arr, c) && !ehLugar(arr[c]); })) erros.push(onde + ": arremesso com origem ou destino que não é lugar");
          if (["pitch", "yaw"].some(function (c) { return tem(arr, c) && !ehNumero(arr[c]); })) erros.push(onde + ": arremesso com pitch ou yaw que não é número");
          if (arr.fontes !== undefined && arr.fontes !== null && !ehObjeto(arr.fontes)) erros.push(onde + ": fontes do arremesso não é um objeto");
        }
      }
    }
    if (t === "cria_traco") {
      if (op.texto !== undefined && op.texto !== null && typeof op.texto !== "string") erros.push(onde + ": 'texto' não é texto");
      if (typeof op.cor !== "string") erros.push(onde + ": cor não é texto");
      if (!Array.isArray(op.pontos)) erros.push(onde + ": 'pontos' não é uma lista");
      else if (!op.pontos.every(ehLugar)) erros.push(onde + ": ponto do traço malformado");
    }
    if (t === "move_ponto" && op.yaw !== undefined && op.yaw !== null && !ehNumero(op.yaw)) erros.push(onde + ": 'yaw' não é número");
    if (t === "cria_caminho" && Array.isArray(op.pontos)) {
      var ruim = op.pontos.some(function (pt) {
        return ehObjeto(pt) && ((pt.yaw !== undefined && pt.yaw !== null && !ehNumero(pt.yaw)) ||
          (pt.nivel !== undefined && pt.nivel !== null && !(ehInteiro(pt.nivel) && pt.nivel >= 0)));
      });
      if (ruim) erros.push(onde + ": yaw ou nível do ponto do caminho inválido");
    }
    return erros;
  }

  /** Regras de VALOR de uma operação cujos campos já estão presentes e com o tipo certo. */
  function problemasDosCampos(op, onde, andares) {
    var erros = [];
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
    if (op.tipo === "cria_granada" && tem(op, "t") && !ehNumero(op.t)) erros.push(onde + ": horário da granada não é número");
    if (op.tipo === "cria_granada" && ["voo_s", "efeito_s"].some(function (k) { return tem(op, k) && !(ehNumero(op[k]) && op[k] >= 0); })) {
      erros.push(onde + ": voo e efeito da granada precisam ser números >= 0");
    }
    if (op.tipo === "cria_granada" && tem(op, "origem_desconhecida")) {
      if (typeof op.origem_desconhecida !== "boolean") erros.push(onde + ": origem_desconhecida não é verdadeiro/falso");
      else if (op.origem_desconhecida) {
        if (op.origem[0] !== op.destino[0] || op.origem[1] !== op.destino[1]) erros.push(onde + ": origem desconhecida exige origem igual ao destino");
        if (op.arremesso) erros.push(onde + ": origem desconhecida não combina com arremesso real");
      }
    }
    if (op.tipo === "cria_granada" && op.arremesso) {
      ["id", "comando", "origem", "destino", "pitch", "yaw"].forEach(function (c) {
        if (!tem(op.arremesso, c)) erros.push(onde + ": arremesso real sem '" + c + "'");
      });
    }
    if (op.tipo === "desenha_granada") {
      if (ARMAS_DESENHADAS.indexOf(op.arma) < 0) erros.push(onde + ": tipo de granada desenhada desconhecido: " + op.arma);
      if (!ehNumero(op.x) || !ehNumero(op.y)) erros.push(onde + ": x e y precisam ser números");
      if (tem(op, "area") && typeof op.area !== "boolean") erros.push(onde + ": área precisa ser verdadeiro ou falso");
    }
    if (op.tipo === "define_area_desenho" && typeof op.area !== "boolean") erros.push(onde + ": área precisa ser verdadeiro ou falso");
    if (op.tipo === "cria_traco") {
      if (FERRAMENTAS_TRACO.indexOf(op.ferramenta) < 0) erros.push(onde + ": ferramenta desconhecida");
      if (!/^#[0-9a-f]{6}$/.test(String(op.cor))) erros.push(onde + ": cor fora do formato #rrggbb");
      if (ESPESSURAS.indexOf(op.espessura) < 0) erros.push(onde + ": espessura fora de " + ESPESSURAS.join("/"));
      if (!op.pontos.length) erros.push(onde + ": sem pontos");
    }
    if (op.tipo === "cria_caminho") {
      // espelho de metrics/tactics.problemas (pontos do caminho)
      if (!Array.isArray(op.pontos) || !op.pontos.length) erros.push(onde + ": caminho sem pontos");
      else {
        var ruim = op.pontos.filter(function (pt) { return !pt || !ehNumero(pt.t) || !ehNumero(pt.x) || !ehNumero(pt.y); });
        if (ruim.length) erros.push(onde + ": ponto do caminho sem t, x ou y numéricos");
        op.pontos.forEach(function (pt) {
          if (!pt) return;
          if (M3 && pt.modo !== undefined && pt.modo !== null && M3.MODOS_DE_ANDAR.indexOf(pt.modo) < 0) erros.push(onde + ": modo fora da lista");
          if ((tem(pt, "fora") && typeof pt.fora !== "boolean") || (tem(pt, "morte") && typeof pt.morte !== "boolean")) {
            erros.push(onde + ": fora e morte do ponto precisam ser verdadeiro ou falso");
          }
          if (pt.morte && !pt.fora) erros.push(onde + ": ponto de morte sem sair do mapa (fora)");
        });
      }
    }
    if (["move_ponto", "planta_bomba"].indexOf(op.tipo) >= 0 && !(ehNumero(op.t) && ehNumero(op.x) && ehNumero(op.y))) {
      erros.push(onde + ": t, x e y precisam ser números");
    }
    return erros;
  }

  /** Problemas de UMA operação ("" de problemas = está boa); nunca lança. `n` é a posição no arquivo (opcional). */
  function problemaDaOperacao(op, andares, versao, n) {
    var base = n === undefined || n === null ? "operação" : "operação " + n;
    if (!ehObjeto(op)) return [base + " não é um objeto"];
    if (CAMPOS_COMUNS.some(function (c) { return !tem(op, c); })) return [base + " incompleta"];
    var erros = [];
    if (typeof op.id !== "string" || !ID_DA_OPERACAO.test(op.id) || NOMES_RESERVADOS.indexOf(op.id) >= 0) erros.push(base + ": id fora do formato");
    if (typeof op.autor !== "string" || tamanhoDoTexto(op.autor) < 1 || tamanhoDoTexto(op.autor) > 64) erros.push(base + ": autor fora do formato");
    if (typeof op.em !== "string") erros.push(base + ": 'em' não é texto");
    if (!seqValido(op.seq)) erros.push(base + ": número de ordem inválido");
    if (typeof op.tipo !== "string") return erros.concat([base + ": tipo fora do formato"]);
    if (!tem(OPERACOES, op.tipo)) return erros.concat(["operação desconhecida: " + op.tipo]);
    var onde = base + " (" + op.tipo + ")";
    var sem = OPERACOES[op.tipo].filter(function (c) { return !tem(op, c); });
    sem.forEach(function (c) { erros.push("'" + op.tipo + "' sem '" + c + "'"); });
    if (OPERACOES_DO_FORMATO_3.indexOf(op.tipo) >= 0 && (versao || FORMATO) < 3) {
      erros.push(onde + ": operação do formato 3 num arquivo do formato " + versao);
    }
    if (sem.length) return erros;
    var deTipo = problemasDeTipo(op, onde);
    if (deTipo.length) return erros.concat(deTipo);
    return erros.concat(problemasDosCampos(op, onde, andares));
  }

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
    doc.operacoes.forEach(function (op) { if (ehObjeto(op) && typeof op.id === "string") porId[op.id] = op; });
    doc.operacoes.forEach(function (op, n) {
      var deOp = problemaDaOperacao(op, andares, doc.versao, n);
      erros = erros.concat(deOp);
      if (!ehObjeto(op) || CAMPOS_COMUNS.some(function (c) { return !tem(op, c); })) return;
      var onde = "operação " + n + " (" + op.tipo + ")";
      // o que só se vê com o log inteiro: id repetido, maior número de ordem e a operação de desfazer
      if (typeof op.id === "string") {
        if (tem(vistos, op.id)) erros.push("operação repetida: " + op.id);
        vistos[op.id] = true;
      }
      if (seqValido(op.seq)) maior = Math.max(maior, op.seq);
      if (DESFAZER.indexOf(op.tipo) >= 0 && typeof op.alvo === "string" && !deOp.length) {
        var alvo = tem(porId, op.alvo) ? porId[op.alvo] : null;
        if (!alvo) erros.push(onde + ": mira operação que não está no log");
        else if (DESFAZER.indexOf(alvo.tipo) >= 0) erros.push(onde + ": mira outra " + alvo.tipo);
        else if (alvo.autor !== op.autor) erros.push(onde + ": cada um só desfaz o que é seu");
      }
    });
    if (ehInteiro(doc.contador) && doc.contador < maior) erros.push("o contador está abaixo do maior número de ordem do log");
    if (!erros.length && M3) erros = erros.concat(problemasNoTempo(taticaNoTempo(doc.operacoes)));
    return erros;
  }

  /** Espelho de metrics.tactics.problemas_no_tempo: o que só se vê no tempo. */
  function problemasNoTempo(e3) {
    var erros = [], plant = e3.bomba ? e3.bomba.t : null;
    var limite = plant === null ? M3.SEGUNDOS_DO_ROUND : plant + M3.SEGUNDOS_DA_BOMBA;
    function g(v) { return String(Math.round(v * 1e6) / 1e6); }
    Object.keys(e3.pecas).forEach(function (pid) {
      var p = e3.pecas[pid], vistos = {};
      p.pontos.forEach(function (pt) {
        if (pt.t < 0 || pt.t > limite) erros.push("ponto-chave de " + p.rotulo + " em t = " + g(pt.t) + " s, fora do round (0 a " + g(limite) + " s)");
        if (!pt.fora) {
          var lugar = pt.x + "," + pt.y;
          if (tem(vistos, pt.t) && vistos[pt.t] !== lugar) erros.push(p.rotulo + " tem dois pontos em t = " + g(pt.t) + " s em lugares diferentes");
          vistos[pt.t] = lugar;
        }
      });
      if (p.funcao !== null && M3.FUNCOES.indexOf(p.funcao) < 0) erros.push("função fora do vocabulário: " + p.funcao);
    });
    Object.keys(e3.granadas).forEach(function (gid) {
      var gr = e3.granadas[gid], j = gr.jogador;
      if (j === null || j === undefined) return;
      if (!e3.pecas[j]) { erros.push("granada " + gid + " com arremessador que não existe: " + j); return; }
      var pts = e3.pecas[j].pontos.filter(function (pt) { return !pt.fora; });
      if (pts.length && gr.t < pts[0].t) erros.push("granada " + gid + " jogada em t = " + g(gr.t) + " s, antes do primeiro ponto do arremessador");
    });
    if (plant !== null && (plant < 0 || plant > M3.SEGUNDOS_DO_ROUND)) erros.push("bomba plantada em t = " + g(plant) + " s, fora do round");
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
    // fase 9: `base_real` é o número de ordem da última operação do round real
    if (tem(o, "base_real") && !(ehInteiro(o.base_real) && o.base_real >= 1)) erros.push("origem: base_real não é um número de ordem");
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

