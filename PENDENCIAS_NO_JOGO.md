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
  - ~~a decisão sobre a postura real no parser~~: **já coberta sem o jogo**
    (2026-09-27). O ponto de nascimento gravado na demo mediu a altura por
    botão e por postura (62,4 / 55,1 / 50,6u em pé; 45,3u agachado; offset de
    agachar -18,00 exato) e explicou 57 dos 62 falsos agachados (decisão 21c).
    O risco de ALTURA está medido; o teste de console continua sendo o único
    que diz se `setpos`/`setang` reproduzem a jogada, e por isso fica, menos
    urgente.
- **Por que não existe outro caminho:** a origem do `setpos` (pés ou olhos), o
  sinal do `setang` e os pré-requisitos do servidor só se confirmam rodando no
  jogo; a demo registra o resultado do arremesso, não o que o console faz.
- **Custo de nunca fazer:** os ~42 mil arremessos da biblioteca continuam
  sendo oferecidos com o aviso de "comando não conferido". A postura NÃO
  depende mais deste teste (ver acima).

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

## Resolvidos sem o jogo

- **Medição controlada da força no ar (era o item 3), removida em
  2026-09-27.** As propriedades da demo explicaram o grupo de ~784 u/s: no ar
  depois de um pulo, o jogo herda a vz de decolagem menos 0,1 s de gravidade,
  não a vz do instante (decisão 21a; `scripts/investiga_props_arremesso.py`).
  A regra aplicada só com posição leva o "no ar" a 98,3% dentro dos três
  grupos. Os 1,7% que sobram ficam com rótulo neutro; só voltam para cá se
  passarem a bloquear algo importante.
