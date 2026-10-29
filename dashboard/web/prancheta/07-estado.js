  /* ---------------------------------------------------------------------
     Estado da página
     --------------------------------------------------------------------- */
  var cfg = null;             // {radar, biblioteca, bibliotecaArquivo, mapa, mapas}

  /* A biblioteca de arremessos pode chegar DEPOIS de a tela montar (cartão 20): no site ela vem de um arquivo próprio ao
     lado da página (`cfg.bibliotecaArquivo`, 3,5 MB na Mirage), carregado ao fim do init (decisão 49). `temBiblioteca`: o mapa tem
     biblioteca (já chegou ou vai chegar); `quandoBiblioteca`: roda agora, ou quando ela chegar, o que precisa dela -- o
     round e o instante do replay ligam cada granada ao arremesso real, e sem esperar a tática nasceria diferente. */
  var esperandoBiblioteca = [];
  function temBiblioteca() { return !!(cfg.biblioteca || cfg.bibliotecaArquivo); }
  function bibliotecaPronta() { return !!cfg.biblioteca || !cfg.bibliotecaArquivo; }
  function quandoBiblioteca(fn) { if (bibliotecaPronta()) fn(); else esperandoBiblioteca.push(fn); }
  var Armazem = null;
  var ANDARES = [];           // nomes das camadas do radar: "default" primeiro
  var CENTRO = null;
  var S = {
    doc: null, estado: null, passo: 0,     // índice do passo na lista
    atraso: null,                           // arremesso real que o jogador não alcança a tempo
    t: 0,                                   // o CABEÇOTE: segundos desde o fim do freeze (formato 3)
    e3: null,                               // a tática no tempo (taticaNoTempo)
    caminho: null,                          // caminho sendo traçado: {peca, inicio, pontos, mao}
    modoCaminho: "correndo",                // correndo | andando | agachado (velocidade do próximo trecho)
    ferramenta: "mover", arma: "smoke",
    sel: null,                              // {tipo: "peca"|"granada"|"traco", id}
    arrasto: null, tracando: null,
    origemPendente: null,                   // (legado) sem uso desde a máquina de estados
    acao: null,                             // ação pendente: colocar peça, granada, busca
    armaDesenho: "smoke",                   // o tipo do carimbo do pincel "Granada (desenho)" (fase 11)
    ultimaPeca: null,                       // o último jogador selecionado: arremessador da conversão
    cursorDesenho: null,                    // cursor de teclado do carimbo, em px do radar
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

  function autor() {
    var doGrupo = ganchos.autor && ganchos.autor();   // num grupo, o autor é o nick da sala (grupo.js)
    return doGrupo || (Armazem.autor() || "").trim() || "anônimo";
  }
  function $(id) { return document.getElementById(id); }

