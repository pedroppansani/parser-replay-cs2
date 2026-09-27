# Pendências que só se resolvem dentro do jogo

Regra do Pedro (2026-09-27): tudo o que depende de estar dentro do CS2 fica
para o final do projeto e só acontece quando for muito necessário. Enquanto
houver outro caminho -- investigar os dados, cruzar com outra fonte do corpus,
deixar o rótulo neutro --, é esse caminho que se usa. O projeto segue sem estes
resultados e sem inventá-los. O roteiro de comandos só é escrito quando o Pedro
decidir fazer a sessão.

---

## 1. Teste de console na Mirage

- **O que precisa ser feito:** reproduzir no jogo um arremesso da biblioteca
  pelo comando `setpos`/`setang` da ficha e conferir se a smoke cai no ponto
  registrado no replay.
- **O que destrava:**
  - `COMANDO_CONFERIDO_NO_JOGO = True` (decisão 21b): as fichas de arremesso,
    no replay e na prancheta, deixam de avisar que o comando não foi
    conferido;
  - a decisão sobre a postura real no parser (`ducked`/`duck_amount`,
    decisão 21c): se a smoke cair no lugar, a diferença de 0,2 a 0,9u na
    altura dos olhos não importa na prática e o parser fica como está; se
    errar em distância, grava-se a postura real e reprocessa-se o corpus.
- **Por que não existe outro caminho:** a origem do `setpos` (pés ou olhos), o
  sinal do `setang` e os pré-requisitos do servidor só se confirmam rodando no
  jogo; a demo registra o resultado do arremesso, não o que o console faz.
- **Custo de nunca fazer:** os ~42 mil arremessos da biblioteca continuam
  sendo oferecidos com o aviso de "comando não conferido", e a postura do
  arremesso continua inferida da altura (limiar de 55u), com os falsos
  agachados medidos na match_23.

## 2. Revisão dos 38 ângulos de entrada da Nuke

- **O que precisa ser feito:** para cada uma das 38 linhas do material de
  calibração (seção 5), confirmar, descartar ou corrigir o yaw olhando o
  ângulo no mapa.
- **O que destrava:** preencher `MANUAL_ENTRY_ANGLES` na Nuke, que tem
  prioridade sobre o derivado, e tirar a marca de baixa confiança das 19
  linhas vistas numa partida só.
- **Por que não existe outro caminho:** o derivado já é o que os dados dão
  (moda do yaw do matador por região); saber se um ângulo é "do mapa" ou
  hábito de um time naquele dia é julgamento de quem conhece o ângulo, e as
  19 linhas de partida única não têm segunda partida para cruzar.
- **Custo de nunca fazer:** o crosshair placement na Nuke continua usando os
  ângulos derivados, com as 19 de partida única marcadas como baixa confiança.
  Nada é gravado em `MANUAL_ENTRY_ANGLES`.

## 3. Medição controlada da força do arremesso no ar

- **O que precisa ser feito:** arremessar no jogo, com velocidade conhecida,
  granadas pulando em pé e pulando agachado (e agachando em momentos
  diferentes do pulo), e gravar a demo, para comparar a velocidade do
  projétil com a do jogador medida pela posição da origem.
- **O que destrava:** o item 7 -- rotular pelo botão os arremessos "no ar" que
  hoje caem fora dos três grupos confirmados (91,9% caem neles; a meta é 95%
  por causa explicada). A investigação (b) mostrou que o excesso de
  velocidade acompanha o arremesso AGACHADO no ar (mediana 714 u/s contra 681
  do controle; o grupo de 784 u/s é a cauda disso), e a hipótese é que agachar
  no pulo desloca a origem do jogador, de modo que a velocidade medida pela
  posição não é a velocidade física que o jogo herda.
- **Por que não existe outro caminho:** a demo não grava a velocidade física
  do jogador (`m_vecVelocity`) nem o instante do agachamento no ar nas tabelas
  que o projeto tem; só com posição não dá para separar o deslocamento da
  origem da velocidade de verdade. Um fator vertical encaixado nos grupos foi
  recusado (sem causa física).
- **Custo de nunca fazer:** os arremessos no ar fora dos três grupos continuam
  com rótulo de força neutro, e a prancheta não diz o botão nesses casos.
