  /* ---------------------------------------------------------------------
     Constantes do modelo -- as mesmas de metrics/tactics.py
     --------------------------------------------------------------------- */
  var IDENTIFICADOR = "prancheta-cs2";
  var FORMATO = 3;
  var VERSOES_ACEITAS = [1, 2, 3];
  var LADOS = ["ct", "t"];
  var PECAS_POR_LADO = 5;
  var ARMAS = ["smoke", "flash", "he", "molotov", "decoy"];
  var NOME_ARMA = { smoke: "Smoke", flash: "Flash", he: "HE", molotov: "Molotov", decoy: "Decoy" };
  // Padrões do formato 2 -- convenção de interface, não dado de jogo.
  var DURACAO_PADRAO_S = 2.0;
  var VIDA_PADRAO_GRANADA = { smoke: null, molotov: 1, flash: 1, he: 1, decoy: 1 };
  var VIDA_PADRAO_TRACO = 1;
  // Espessura guardada na granada desenhada: não muda o desenho (o glifo tem tamanho próprio); serve à borracha,
  // que soma a espessura ao raio de acerto. O mesmo valor em metrics/tactics.py. (Convenção.)
  var ESPESSURA_DA_GRANADA_DESENHADA = 4;
  // Passo do cursor de teclado do carimbo, em px do radar (com Shift, 4x). (Convenção de interface.)
  var PASSO_CURSOR_PX = 8;
  var ARMAS_DESENHADAS = ["smoke", "flash", "he", "molotov"];
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
    define_vida: ["alvo", "dura_passos"], anula: ["alvo"], reativa: ["alvo"],
    // formato 3: o tempo do round é o eixo
    cria_caminho: ["peca", "pontos"], move_ponto: ["peca", "ponto", "t", "x", "y"],
    remove_ponto: ["peca", "ponto"], define_funcao: ["peca", "funcao"],
    planta_bomba: ["t", "x", "y"], nota_de_evento: ["alvo", "texto"],
    // fase 11: granada DESENHADA (sem horário e sem física). Fica na camada de desenho, junto dos traços (vida por
    // passo, borracha, "Apagar desenho"), mas é operação própria: não é a granada com horário (cria_granada) e não
    // aparece na linha do tempo nem no roteiro
    desenha_granada: ["traco", "passo", "arma", "x", "y"], define_area_desenho: ["traco", "area"]
  };
  var OPERACOES_DO_FORMATO_3 = ["cria_caminho", "move_ponto", "remove_ponto", "define_funcao", "planta_bomba",
                                "nota_de_evento", "desenha_granada", "define_area_desenho"];

  // Desenho livre: o formato e as regras do traço são os de
  // metrics/annotations.py (há teste conferindo estas duas listas contra ele).
  var FERRAMENTAS_TRACO = ["caneta", "seta", "linha", "retangulo", "elipse", "texto"];
  var ESPESSURAS = [2, 4, 7];
  var ROTULOS_ESPESSURA = ["fina", "média", "grossa"];
  var ROTULO_FERRAMENTA = { caneta: "Caneta", seta: "Seta", linha: "Linha", retangulo: "Retângulo",
                            elipse: "Elipse", texto: "Texto", granada_desenho: "Granada (desenho)", borracha: "Borracha" };
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
  // duração do efeito, para a faixa listrada da linha do tempo (§14: smoke 18 s, molotov 7 s; convenção do jogo)
  var LARGURA_DO_CELULAR_PX = 640;   // fonte: entrega-sala-de-demo §14 ("Celular (≤ 640 px)")
  var FOLGA_DAS_OPCOES_PX = 8;       // entre o mapa e a coluna de opções do pincel (v2-5b): o mesmo padding da tela
  var DURACAO_SMOKE_S = 18, DURACAO_MOLOTOV_S = 7;
  var ALFA_FANTASMA = 0.9;      // o fantasma do round real é só o anel tracejado: precisa ler (entrega-sala-de-demo §14)
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

