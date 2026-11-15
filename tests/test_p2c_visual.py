"""P2c (visual): a prancheta volta à navbar e os 10 mapas viram links; arrastar várias vezes no Reescrever; "Ver no mapa ↑" no celular; o nome do time; a peça sob o relógio."""
from __future__ import annotations

import pytest

sync_api = pytest.importorskip("playwright.sync_api")

from tests.test_reescrever_r1 import paginas_html, partidas  # noqa: E402,F401  (as páginas geradas)
from tests.test_reescrever_modo import navegador  # noqa: E402,F401


@pytest.mark.parametrize("largura", [375, 1440])
@pytest.mark.parametrize("pagina", ["landing", "jogadores", "reescrever", "partida", "prancheta"])
def test_os_quatro_links_da_navbar_cabem_sem_rolagem_lateral_e_em_uma_linha(navegador, paginas_html, pagina, largura):
    pasta, _ = paginas_html
    ctx = navegador.new_context(viewport={"width": largura, "height": 812})
    pg = ctx.new_page()
    try:
        pg.goto((pasta / f"{pagina}.html").as_uri())
        r = pg.evaluate("""() => { const n = document.querySelector('.site-nav'), as = [...n.querySelectorAll('a')], nb = n.getBoundingClientRect();
          return { textos: as.map(a => a.textContent), sobra: n.scrollWidth - n.clientWidth, topos: [...new Set(as.map(a => Math.round(a.getBoundingClientRect().top)))].length,
                   dentro: as.every(a => { const b = a.getBoundingClientRect(); return b.left >= nb.left - 0.5 && b.right <= nb.right + 0.5; }),
                   pagina: document.documentElement.scrollWidth - document.documentElement.clientWidth }; }""")
        assert r["textos"] == ["Partidas", "Jogadores", "Reescrever", "Prancheta"]
        assert r["sobra"] <= 0 and r["dentro"] and r["topos"] == 1 and r["pagina"] <= 0        # nenhuma rolagem lateral (nem a da navbar nem a da página) e os 4 na mesma linha
    finally:
        ctx.close()
