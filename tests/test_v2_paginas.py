"""v2-4 (decisão 48): a página da partida no claro, com a navbar, as abas com gooey e o mapa escuro numa moldura."""
from __future__ import annotations

from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
PARTIDA = "match_02"


def test_a_partida_sai_no_claro_com_a_navbar_e_sem_marcador():
    if not (RAIZ / "data" / "processed" / PARTIDA / "web_payload.json").exists():
        pytest.skip("sem o processado")
    from scripts.build_web_page import build_html
    html = build_html(PARTIDA)
    assert '<html lang="pt-BR" data-tema="claro">' in html
    assert '<header class="site-topo">' in html and 'href="index.html#partidas"' in html
    assert 'id="palco" data-tema="escuro"' in html                # a moldura é uma ilha do escuro
    for marcador in ("/*__V2__*/", "/*__V2_JS__*/", "<!--__TOPO__-->"):
        assert marcador not in html, marcador


sync_api = pytest.importorskip("playwright.sync_api")

from tests.test_tactics_browser import navegador  # noqa: E402,F401  (fixture)


def test_gooey_so_na_troca_e_o_canvas_le_os_tokens_do_mapa(navegador, tmp_path):
    if not (RAIZ / "data" / "processed" / PARTIDA / "web_payload.json").exists():
        pytest.skip("sem o processado")
    from metrics.paleta import le_tokens
    from scripts.build_web_page import build_html
    arq = tmp_path / f"{PARTIDA}.html"
    arq.write_text(build_html(PARTIDA), encoding="utf-8")
    ctx = navegador.new_context(viewport={"width": 1440, "height": 900})
    pg = ctx.new_page()
    erros = []
    pg.on("pageerror", lambda e: erros.append(str(e)))
    try:
        pg.goto(arq.as_uri())
        pg.wait_for_timeout(300)
        filtro = "() => getComputedStyle(document.querySelector('.tabs .goo')).filter"
        assert pg.evaluate(filtro) == "none"                         # em repouso a pílula é nítida
        pg.click('[data-tab="replay"]')
        assert "url" in pg.evaluate(filtro)                          # durante a troca, o filtro
        pg.wait_for_timeout(400)
        assert pg.evaluate(filtro) == "none"
        # a bolha fica embaixo da aba ativa
        b = pg.evaluate("""() => { const a = document.querySelector('[data-tab=replay]').getBoundingClientRect(),
                                    b = document.querySelector('.tabs .bolha').getBoundingClientRect();
                                    return [Math.round(a.left - b.left), Math.round(a.width - b.width)]; }""")
        assert b == [0, 0], b
        # a página é clara, o mapa lê os *-mapa (os valores escuros de hoje: nenhum pixel do canvas muda)
        escuro, claro = le_tokens(tema="escuro"), le_tokens(tema="claro")
        lido = pg.evaluate("""() => { const s = getComputedStyle(document.documentElement);
            return ['ct-mapa', 'tr-mapa', 'tinta-mapa', 'fundo'].map(n => s.getPropertyValue('--' + n).trim()); }""")
        assert lido == [escuro["ct"], escuro["tr"], escuro["tinta"], claro["fundo"]]
        # o anel de 6 px da moldura é a --superficie da página clara, não a da ilha escura
        anel = pg.evaluate("() => getComputedStyle(document.getElementById('palco')).boxShadow")
        h = claro["superficie"]
        assert f"rgb({int(h[1:3], 16)}, {int(h[3:5], 16)}, {int(h[5:7], 16)}) 0px 0px 0px 6px" in anel, anel
        assert erros == []
    finally:
        ctx.close()
