# Decisão 70: A peça segue o caminho de gente pelo mapa, não a reta (PC1 em diante)

- **ID:** 70
- **Status:** vigente
- **Data:** 2026-11-15
- **Resumo:** O caminho vem de um grafo por mapa que une as trajetórias do corpus (células de 64 u) e a malha do jogo: o corpus primeiro, a malha onde o corpus não passou, e entre andares a malha primeiro. O
  tempo real da C3 continua sendo a primeira fonte; onde não há caminho, volta a reta "estimado: linha reta".

## Texto

70. **O caminho das peças** (PC0 = investigação, `notas/investigacoes/2026-11-15-pc0-caminhos-pelo-mapa.md`; PC1 = o dado e a busca; PC2 e PC3 = a prancheta e o Reescrever).

- **Fonte (decisão do Pedro):** o **corpus primeiro** (só ele tem os pulos que os jogadores fazem: "Janelão -> L" = 3,5 s pelo corpus contra 9,7 s pela malha dos bots) e a **malha onde o corpus não passou**.
  **Entre andares a malha vem primeiro** (24,9% de erro contra 37% a 44% do corpus na Nuke): em mapa de dois andares (`metrics.map_areas.floor_split_z`) o dado não traz as ligações do corpus que cruzam o andar.
  Na busca, a ligação área -> área custa a distância vezes 1,25 (o corpus ganha o empate); as pontes célula <-> área ligam os dois grafos onde o centro da célula está dentro da área, na mesma altura.
- **Célula do corpus:** 64 u por 48 u de altura, células com 3 visitas ou mais e ligações com 2 rastros ou mais (47 KB gzip na Mirage).
- **Nada inventado:** uma ligação só existe se alguém passou (corpus) ou se a malha a tem; uma queda só existe no sentido em que foi feita (a malha não ganha sentido que não tem); nenhum trecho passa fora das células
  e das áreas que existem (uma quina entre áreas ligadas pode ser cortada a até meia largura do jogador, 16 u).
- **O caminho:** a linha dos centros; nos trechos de áreas da malha o "fio é puxado" (de cada ponto vai direto ao mais longe que a reta ainda cabe nas áreas do trecho, olhando até 16 pontos adiante). O fio
  melhora a malha sozinha de 33,6% para 10,1% de erro na Mirage (25,7% para 12,8% na Dust2, 38,7% para 9,3% na Inferno).
- **Tempo:** comprimento / 250 u/s, o mesmo cálculo da C3; erro mediano contra o tempo real da C3: Mirage 9,3% (reta 17,5%), Dust2 12,0% (21,4%), Nuke 11,2% (23,4%), Inferno 7,1% (18,5%), Anubis 5,6% (11,1%),
  Ancient 4,7% (14,3%). O tempo real da C3 continua sendo a primeira fonte e o cartão diz qual foi usada: "tempo real", "estimado pelo caminho" ou "estimado: linha reta".
- **Sem caminho** (um ponto sem célula nem área, ou um mapa sem malha e sem partida): volta a reta, "estimado: linha reta".
- **Onde mora:** `data/caminhos/<mapa>.json` (`scripts/build_caminhos.py`; o site entrega `caminhos/<mapa>.js`), a busca em `dashboard/web/comandos/caminho.js` (pura, a mesma para a prancheta e o Reescrever) e a de
  referência em `scripts/caminhos/busca.py`; `tests/test_caminhos.py` prova que fazem o mesmo (diferença de 0,01 u) e que a consulta fica abaixo de 50 ms com a CPU 4x mais lenta.
