# Decisão 66: A prancheta volta à navbar e os 10 mapas viram links (P2c)

- **ID:** 66
- **Status:** vigente
- **Data:** 2026-11-15
- **Resumo:** A navbar passa a ser Partidas · Jogadores · Reescrever · Prancheta ("Prancheta" abre a da Mirage, o endereço de sempre); no bloco "Monte uma
  tática do zero" da landing cada um dos 10 mapas é um link para a prancheta dele. Complementa a decisão 56, que tirou a prancheta da navbar.

## Texto

66. **Prancheta na navbar** (P2c; pedido do Pedro, que não conseguiu achá-la no site).

- **Navbar** (`design_head.topo_do_site`): quatro links; na página da prancheta o link dela marca a página (`aria-current`). A 375 px os quatro cabem na
  segunda linha da pílula sem rolagem lateral (`v2.css`: padding de 5 px por link até 640 px, com as fontes Geist carregadas); `tests/test_p2c_visual.py` confere em 5 páginas, a 375 e
  1440 px.
- **Landing** (`build_site.build_index`): um chip-LINK por mapa (`<a class="chip" href="prancheta_de_<mapa>.html">`), sem o botão "Abrir a prancheta da X"
  nem o endereço, que só repetiam o chip (o antigo chip só escolhia o mapa do botão: parecia texto).
- **Mudaram com o OK do Pedro:** `test_reescrever_r1` (navbar e bloco da landing) e `test_prancheta_design_e` (cabeçalho da prancheta).
