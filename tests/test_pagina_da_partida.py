"""A página da partida como documento: modo padrão, título por partida e
celular sem rolagem horizontal. Playwright + Chrome (pulado sem navegador)."""
from __future__ import annotations

from pathlib import Path

import pytest

sync_api = pytest.importorskip("playwright.sync_api")

from tests.test_tactics_browser import navegador  # noqa: E402,F401  (fixture)

RAIZ = Path(__file__).resolve().parent.parent
# duas partidas de mapas diferentes; a primeira é profissional, a segunda FACEIT
PARTIDAS = ("match_23", "match_02")


@pytest.fixture(scope="module")
def paginas(tmp_path_factory):
    from scripts.build_web_page import build_html
    pasta = tmp_path_factory.mktemp("partida")
    out = {}
    for m in PARTIDAS:
        if not (RAIZ / "data" / "processed" / m / "web_payload.json").exists():
            pytest.skip(f"sem o processado da {m}")
        out[m] = pasta / f"{m}.html"
        out[m].write_text(build_html(m), encoding="utf-8")
    return out


def _abre(navegador, arq, largura=1300, celular=False):
    ctx = navegador.new_context(viewport={"width": largura, "height": 900}, is_mobile=celular,
                                device_scale_factor=2 if celular else 1)
    pg = ctx.new_page()
    erros = []
    pg.on("pageerror", lambda e: erros.append(str(e)))
    pg.goto(arq.as_uri())
    pg.wait_for_selector("[role=tab][data-tab]")
    pg._erros = erros
    return ctx, pg


def test_a_pagina_roda_em_modo_padrao_com_idioma_e_viewport(navegador, paginas):
    ctx, pg = _abre(navegador, paginas[PARTIDAS[0]])
    assert pg.evaluate("() => document.compatMode") == "CSS1Compat"
    assert pg.evaluate("() => document.documentElement.lang") == "pt-BR"
    assert pg.evaluate("() => document.characterSet") == "UTF-8"
    assert "width=device-width" in pg.get_attribute('meta[name="viewport"]', "content")
    assert pg._erros == []
    ctx.close()


def test_o_titulo_e_da_partida_e_traz_o_mapa(navegador, paginas):
    titulos = {}
    for m in PARTIDAS:
        ctx, pg = _abre(navegador, paginas[m])
        titulos[m] = pg.title()
        mapa = pg.text_content("#c-map").strip().removeprefix("de_")
        assert mapa.lower() in titulos[m].lower(), titulos[m]
        ctx.close()
    assert titulos[PARTIDAS[0]] != titulos[PARTIDAS[1]]


def test_titulo_sem_dado_fica_so_com_o_mapa(tmp_path, monkeypatch):
    import json
    import scripts.build_web_page as b
    base = tmp_path / "data" / "processed" / "match_x"
    base.mkdir(parents=True)
    (base / "match_meta.json").write_text(json.dumps({"map_name": "de_nuke"}), encoding="utf-8")
    monkeypatch.setattr(b, "PROJECT_ROOT", tmp_path)
    assert b.titulo_da_pagina("match_x") == "Nuke"


@pytest.mark.parametrize("partida", PARTIDAS)
def test_no_celular_nenhuma_aba_rola_na_horizontal_e_o_mapa_cabe(navegador, paginas, partida):
    ctx, pg = _abre(navegador, paginas[partida], largura=390, celular=True)
    for aba in pg.eval_on_selector_all("[role=tab][data-tab]", "els => els.map(e => e.dataset.tab)"):
        pg.click(f'[role=tab][data-tab="{aba}"]')
        pg.wait_for_timeout(150)
        assert pg.evaluate("() => document.documentElement.scrollWidth") <= 390, aba
    pg.click('[role=tab][data-tab="replay"]')
    caixa = pg.eval_on_selector("canvas#map", "e => { const r = e.getBoundingClientRect(); return [r.left, r.right]; }")
    assert caixa[0] >= 0 and caixa[1] <= 390, caixa
    ctx.close()
