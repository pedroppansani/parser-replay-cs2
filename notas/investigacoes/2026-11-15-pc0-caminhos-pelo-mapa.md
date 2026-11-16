# PC0: a peça seguir um caminho de verdade, não a reta (investigação, 2026-11-15)

Só investigação: nenhuma mudança no site. Scripts em `scripts/pc0/` (leitura; rodam com por exemplo `py -3.12 -m scripts.pc0.exemplos`), logs em `notas/logs/pc0-*.log`, desenhos em `C:\Users\User\Desktop\Claude outputs\pc0-caminhos\`.
Os dados do jogo (`.nav`, extraídos do `.vpk` de cada mapa da CS2 instalada) ficaram FORA do repositório (`%TEMP%\pc0`).

## 1. As fontes de caminho

| fonte | o que é | cobertura | precisão (Mirage, 454 pares da C3) | peso (Mirage) |
|---|---|---|---|---|
| **A. malha `.nav` do jogo** | polígonos andáveis dos bots, com ligações dirigidas (quedas de uma mão só), escadas de mão e a altura de cada área | os 10 mapas, 1.969 a 3.938 áreas; qualquer ponto do mapa | erro mediano **9,5%** (reta: 17,4%); 65% dos pares a até 15% (reta: 42%); viés +0,02 s | centros + ligações: 78 KB cru, **26 KB gzip**; com polígonos (para "puxar o fio"): +27 KB gzip |
| **B. grafo das trajetórias do corpus** | células de 40 a 96 u que alguém pisou, ligadas só no sentido em que alguém passou (amostras seguidas) | só onde o corpus passou: 100% dos pares da tabela, mas **92%** com metade das partidas; 8 mapas com partidas (Vertigo e Cache: nenhuma; Train: 1; Overpass: 2) | erro mediano **9,3%** (célula 40 u), 9,8% (64 u), 10,3% (96 u); 65% a até 15%; viés −0,18 s | 40 u: 90 KB gzip; **64 u: 47 KB**; 96 u: 27 KB |
| **C. a grade da demo (pendência 32)** | `radar.lugares.grade`: células com o nome do lugar (`place`) da demo, 3 a 13 KB | só dá NOME de lugar, **sem ligações nem andar andável** | não serve a caminho | já está na página, sem uso |

Fatos que decidem:
- O awpy 2.0.2 (o do projeto) lê `.nav` até a versão 35 e o jogo hoje grava a **36** (o leitor falha); o espelho de dados do awpy (`awpycs.com`) responde 403 hoje, também para os `.tri`. Li os `.nav` com o awpy **3.3.0 num venv à parte** (o projeto não mudou) e exportei para JSON. Escadas de mão: o `.nav` as guarda por id (a área de baixo diz "escada acima: N", a de cima "escada abaixo: N"); liguei as duas.
- O `.nav` é a malha dos BOTS: **não tem os pulos de gente**. Exemplo na Mirage, "Janelão → L": o caminho da malha dá 2.419 u (9,7 s, uma volta enorme); o corpus mostra jogadores indo em **878 u (3,5 s)**, subindo numa borda a z −55 que não é área nenhuma da malha (as células ali ficam "sem área") e descendo do outro lado. É o "pular da janela pro L" que o Pedro disse.
- O corpus mostra **o que gente faz**, mas só onde alguém foi. A malha cobre o mapa inteiro mas só o que bot anda (e a maior componente fortemente conexa é 93 a 98% das áreas).
- Em 95,1% das visitas do corpus (Mirage) o jogador estava sobre uma área da malha; nenhuma queda de 60 u ou mais do corpus ficou sem ligação na malha.

## 2. Os andares

- **Nuke:** malha com z de −772 a −18 (dois andares empilhados), 3.040 áreas, 12 escadas de mão, 135 ligações verticais de 100 u ou mais (111 são quedas de uma mão só). Corpus (9 partidas): z de −776 a 10.
  Nos pares entre andares (os dois nós a 150 u ou mais de altura): **malha 24,9%** de erro, **corpus 36,8% a 43,6%**, reta 26,4% (23 pares). O corpus é pior que a reta aí: escadas, tubos e quedas têm pouca amostra.
- **Vertigo:** malha com z de 11.492 a 11.912 (um prédio), 2.105 áreas, 1 escada de mão, 111 ligações verticais (105 quedas). **Nenhuma partida no corpus e nenhuma tabela da C3**: só a malha existe, e **não dá para validar o tempo**.
- Mirage, entre andares (Underpass, rampas): malha 15,3%, corpus 18,2 a 19,9%, reta 18,8% (18 pares). Dust2: malha 7,5%, corpus 10,5 a 12,7%, reta 22,4% (38 pares).
- A malha trata o andar de graça (cada área tem a sua altura; achar a área de um ponto usa o z); o corpus separa andares por faixa de 48 u de altura e depende de gente ter passado pela escada.

## 3. O tempo pelo caminho contra a reta (pares com tempo real da C3, 250 u/s nos dois)

| mapa (pares) | reta: erro mediano / a até 15% | malha | corpus (todas / metade) |
|---|---|---|---|
| Mirage (454) | 17,4% / 42% | **9,5% / 65%** | 9,3% / 65% — 9,8% / 63% |
| Dust2 (276) | 21,4% / 18% | **10,3% / 65%** | 14,0% / 54% — 13,0% / 57% |
| Nuke (74, áreas) | 23,0% / 25% | 18,6% / 47% (p90 163%) | **16,0% / 46%** — 17,3% / 43% |
| Inferno (42, áreas) | 18,5% / 33% | 10,2% / 62% | **7,7% / 71%** — 9,4% / 71% |
| Anubis (43, áreas) | 11,1% / 67% | 6,2% / 77% | **3,0% / 88%** — 3,5% / 88% |
| Ancient (23, áreas) | 14,3% / 52% | **4,4% / 83%** | 5,6% / 90% — 5,4% / 89% |

- A reta a 250 u/s **subestima** (viés de −0,65 s na mediana, Mirage); o caminho a 250 u/s não tem viés (+0,02 s). A conta do caminho: centros das áreas, com o "fio puxado" (cada ponto vai direto ao mais longe que ainda cabe nas áreas da rota); sem puxar o fio o caminho fica 52% mais longo que a reta e o erro piora (25%).
- **Dá para trocar o "não antes de" (o piso da C3, hoje distância/250) por "estimado pelo caminho"**, com erro mediano de ~10% (p90 31 a 37%) onde há malha ou corpus; a tabela do corpus (tempo real) continua sendo a primeira fonte, o caminho entra nos pares sem amostra.
- **Base TR → Meio** (Mirage): reta 1.685 u = **6,7 s**; caminho da malha 2.906 u = **11,6 s**; corpus 2.788 u = **11,2 s**; real da C3 **12,6 s** (p25 a p75: 12,05 a 13,47 s; 20 casos, 9 partidas). Os "12,0 s real contra 8,0 s da reta" da sua mensagem eu não reproduzo com os nós do Pedro; o par é este. A reta dá −47%, o caminho −8%.
- **CT → L**: reta 2.397 u = 9,6 s; malha 4.086 u = 16,3 s; corpus 2.866 u = 11,5 s; sem tempo real (o par não tem amostra). A malha faz a volta grande pela direita; o corpus vai pela esquerda, por onde gente vai.
- **Janela Mercado → L**: reta 1.164 u = 4,7 s; malha 6,2 s; corpus 5,8 s; real **5,56 s** (99 casos): as três fontes concordam com o real a 12% ou menos.
- **Janelão → L**: reta 710 u = 2,8 s; malha 9,7 s (com 1 queda de −128 u); corpus **3,5 s**; sem tempo real. É o caso em que só o corpus tem o pulo.

## 4. Peso e velocidade

- Peso por mapa, formato `{p: x,y,z int16 por nó, e: ligações com o de em delta}` mandado em `.js` como os tempos: malha (centros) **26 KB gzip na Mirage**; corpus **27 a 90 KB gzip** conforme a célula (96, 64 e 40 u); +27 KB se a malha levar polígonos para puxar o fio. Todos os mapas: cerca de 0,3 MB só com a malha e 0,6 MB com os dois (corpus a 64 u), carregados por mapa, só quando a aba Comandos (ou o Reescrever) abre.
- Calcular um caminho no navegador (A* com heap, achar as pontas incluído), Mirage, 300 consultas, **CPU 4x mais lenta**: malha **mediana 0,40 ms, p95 1,1 ms, máximo 2,8 ms**; corpus 64 u mediana 0,60 ms, p95 1,7 ms, máximo 3,2 ms; corpus 96 u mediana 0,30 ms. Montar o grafo ao carregar: 1,6 a 8,8 ms. A meta (50 ms) sobra por uma ordem de grandeza. O "fio puxado" com polígonos custa mais; não medi no navegador (calculado só no Python).

## 5. Imagens

`C:\Users\User\Desktop\Claude outputs\pc0-caminhos\`: `Base_TR_para_Meio.png`, `CT_para_L.png`, `Janela_Mercado_para_L.png`, `Janelão_para_L.png` e `exemplos.json`. Branco = a reta; laranja = o caminho da malha (círculo vermelho = queda); rosa = o caminho do corpus; no alto o tempo de cada opção.

## 6. O que muda na tela (proposta)

- A **peça anda pelo caminho** (a polilinha do grafo) na velocidade medida, no lugar da reta; a corrida do Reescrever e da prancheta usam o mesmo cálculo do `plano.js`.
- O **traço** desenhado (prancheta e Reescrever) é essa polilinha; onde há queda, um pequeno marcador "↓".
- O cartão "O que entendi" diz a **fonte** do tempo: "tempo real" (C3), "estimado pelo caminho" ou "estimado: linha reta" (sem dado), como hoje.

## 7. Fases propostas

PC1, o dado no build (`data/caminhos/<mapa>.json` -> `docs/caminhos/<mapa>.js`, carregado sob demanda como os tempos), com testes (nenhuma ligação atravessa parede; as quedas só descem; o formato; o tamanho); PC2, a prancheta (o plano usa o caminho; traço e cartão); PC3, o Reescrever (a trilha da peça segue a polilinha; o `empurra` e o fantasma). Cada uma com a prova byte a byte da prancheta onde a frase não muda.

## O que o dado NÃO sustenta

- **Vertigo**: sem partida no corpus e sem tabela de tempo; só há a malha, sem como validar o tempo. **Cache, Train, Overpass**: nenhuma ou quase nenhuma partida (Train 1, Overpass 2): o corpus não serve.
- **Pulos que ninguém fez no corpus** não existem no grafo B, e **pulos que o bot não faz não existem no A** (o exemplo da janela). Nenhuma das duas fontes sozinha tem "tudo que se pode fazer".
- O tempo é **estimado**: erro mediano ~10%, p90 31 a 37% (Mirage); 16 a 19% na Nuke e pior entre andares. Não vale como "o jogador chega às 1:11".
- Os pares usados para medir vêm da tabela da C3 (lugares muito visitados); para um ponto qualquer, longe de onde o corpus passa, o erro do corpus é desconhecido.
- A malha é **dado do jogo (Valve)**: pô-la no repositório e no site é uma decisão de licença/atribuição, como a dos radares (que já estão e têm aviso no rodapé). Não pus nada dela no repositório.
- O "fio puxado" é uma aproximação (a 16 u de amostragem), não o caminho mais curto exato.

## Decisões abertas para o Pedro

1. **Fonte do caminho:** (a) o corpus (só gente, pulos incluídos, 27 a 47 KB por mapa, sem licença, mas só nos 8 mapas com partidas e fraco entre andares na Nuke); (b) a malha (cobre os 10 mapas e os andares, sem os pulos de gente, dado da Valve); (c) **os dois, o corpus primeiro e a malha onde o corpus não passou** (cobertura e pulos; mais peso e mais código). **Recomendo (c)**, começando pelo corpus.
2. **A licença da malha:** aceitar derivar os centros e as ligações da malha da Valve para o site (a mesma lógica dos radares), ou ficar só com o corpus.
3. **O texto do tempo:** "estimado pelo caminho (±10%)" substitui "não antes de" nos pares sem amostra; **recomendo** manter o tempo real da C3 como primeira fonte e dizer a fonte no cartão.
4. **Onde não há caminho** (Vertigo, Cache, ponto sem célula): volta para a reta marcada "estimado: linha reta", como hoje. Confirmar.
5. **Célula do corpus:** 64 u (47 KB, erro 9,8%) ou 96 u (27 KB, 10,3%). **Recomendo 64 u.**
