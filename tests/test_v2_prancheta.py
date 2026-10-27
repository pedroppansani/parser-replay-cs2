"""v2-5 (decisão 48): a prancheta no escuro violeta, com a navbar, o "Reproduzir" quente e as abas do painel com gooey."""
from __future__ import annotations

import pytest

MAPA = "de_mirage"


def test_a_prancheta_sai_no_escuro_com_a_navbar_e_sem_marcador():
    from scripts.build_tactics_page import build_html
    html = build_html(MAPA)
    assert '<html lang="pt-BR" data-tema="escuro">' in html and '<header class="site-topo">' in html
    assert '<filter id="goo">' in html
    for marcador in ("/*__V2__*/", "/*__V2_JS__*/", "<!--__TOPO__-->"):
        assert marcador not in html, marcador


sync_api = pytest.importorskip("playwright.sync_api")

from tests.test_tactics_browser import navegador  # noqa: E402,F401  (fixture)


def test_reproduzir_quente_uma_vez_e_gooey_so_na_troca(navegador, tmp_path):
    from scripts.build_tactics_page import arquivo_da_pagina, build_html
    arq = tmp_path / arquivo_da_pagina(MAPA)
    arq.write_text(build_html(MAPA), encoding="utf-8")
    ctx = navegador.new_context(viewport={"width": 1440, "height": 900})
    pg = ctx.new_page()
    erros = []
    pg.on("pageerror", lambda e: erros.append(str(e)))
    try:
        pg.goto(arq.as_uri())
        pg.wait_for_function("() => Prancheta._interno.S.estado !== null")
        pg.wait_for_timeout(300)
        # o degradê quente (--quente-2 #ff3a63) só no "Reproduzir", uma vez na tela
        quentes = pg.evaluate("""() => [...document.querySelectorAll('body *')]
            .filter(e => getComputedStyle(e).backgroundImage.includes('rgb(255, 58, 99)')).map(e => e.id)""")
        assert quentes == ["pr-reproduzir"], quentes
        filtro = "() => getComputedStyle(document.querySelector('#pr-abas .goo')).filter"
        assert pg.evaluate(filtro) == "none"                         # em repouso a pílula é nítida
        pg.click("#pr-aba-tatica")
        assert "url" in pg.evaluate(filtro)                          # durante a troca, o filtro
        pg.wait_for_timeout(400)
        assert pg.evaluate(filtro) == "none"
        b = pg.evaluate("""() => { const a = document.getElementById('pr-aba-tatica').getBoundingClientRect(),
                                    b = document.querySelector('#pr-abas .bolha').getBoundingClientRect();
                                    return [Math.round(a.left - b.left), Math.round(a.width - b.width)]; }""")
        assert b == [0, 0], b
        assert erros == []
    finally:
        ctx.close()
