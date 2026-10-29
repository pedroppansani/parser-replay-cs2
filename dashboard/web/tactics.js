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

//@inclui prancheta/01-constantes.js
//@inclui prancheta/02-modelo.js
//@inclui prancheta/03-reproducao-pura.js
//@inclui prancheta/04-formato-3.js
//@inclui prancheta/05-validacao.js
//@inclui prancheta/06-armazem.js
//@inclui prancheta/07-estado.js
//@inclui prancheta/08-ganchos-do-grupo.js
//@inclui prancheta/09-round-real.js
//@inclui prancheta/10-tracar-caminho.js
//@inclui prancheta/11-projecao-e-tamanho.js
//@inclui prancheta/12-desenho.js
//@inclui prancheta/13-ponteiro-e-interacao.js
//@inclui prancheta/14-arremessos-reais.js
//@inclui prancheta/15-paineis.js
//@inclui prancheta/16-arquivo.js
//@inclui prancheta/17-montagem.js
//@inclui prancheta/18-linha-do-tempo.js
//@inclui prancheta/19-reproducao-na-tela.js
//@inclui prancheta/20-api-do-grupo.js
})();
