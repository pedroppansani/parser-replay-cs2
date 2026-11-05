# Decisão 56: A navbar com Reescrever, a prancheta livre na landing e a página de escolha (Reescrever R1)

- **ID:** 56
- **Status:** vigente
- **Data:** 2026-11-05
- **Resumo:** A navbar passa a ser Partidas, Jogadores e Reescrever; a prancheta livre sai dela e vira o bloco "Monte uma tática do zero"
  da landing (o endereço `prancheta_de_<mapa>.html` não muda); a página `reescrever.html` mostra os rounds sugeridos (R0) e a busca.

## Texto

56. **Navbar e escolha do Reescrever** (R1; design do Iriun em `notas/design/reescrever/`, escolhas D1 a D7 do Pedro em 2026-11-04).

- **Navbar** (`design_head.topo_do_site(atual, repo)`): Partidas · Jogadores · Reescrever em toda página; a prancheta e a partida não marcam link.
  Mudaram junto os testes `test_prancheta_design_e` (a prancheta não tem mais link ativo) e `test_csp` (a página nova entra na lista).
- **Landing** (`build_site.build_index`): o bloco "Monte uma tática do zero" depois da grade: frase, um chip por mapa que tem prancheta (10 no
  corpus; o design falava em 8), "Abrir a prancheta da <mapa>" (o chip troca o mapa, o botão e o endereço mostrado), a miniatura no violeta (a
  cor da prancheta, decoração). Começa na Mirage. A frase vem do Python (decisão 18).
- **Página de escolha** (`scripts/build_reescrever.py`, `dashboard/web/reescrever.html`): a frase fixa de honestidade ("Não é uma
  previsão..."), os sugeridos (decisão 55: uma linha por round, com o motivo escrito, no máximo 12, os decisivos primeiro) e a busca (time, mapa ou
  evento, sem acento; escolher a partida abre a faixa de rounds e o botão "Reescrever o round N"). Os dados vão EMBUTIDOS (a página abre como
  arquivo local, sem baixar nada) e o texto dos dados só entra por `textContent`.
- **O botão ainda abre o Replay:** leva a `match_NN.html#replay?round=N&t=S` (o endereço da fase 12; `t` só nos sugeridos com instante). O modo
  Reescrever em si é o R2; até lá o botão é a porta para o round.
