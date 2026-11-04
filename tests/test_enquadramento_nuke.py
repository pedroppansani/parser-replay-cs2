"""Fase B+ (decisão 54): na Nuke a vista de cada round enquadra tudo o que o round mostra (jogador, granada, área), então
ninguém sai do quadro nem fica com o nome cortado; as outras partidas não mudam."""
from __future__ import annotations

from pathlib import Path

import pytest

sync_api = pytest.importorskip("playwright.sync_api")

from tests.test_tactics_browser import navegador  # noqa: E402,F401  (fixture)

RAIZ = Path(__file__).resolve().parent.parent
NUKE, MIRAGE = "match_05", "match_02"


def _pagina(tmp_path_factory, nome):
    from scripts.build_web_page import build_html
    if not (RAIZ / "data" / "processed" / nome / "web_payload.json").exists():
        pytest.skip("sem o processado")
    arq = tmp_path_factory.mktemp(nome) / f"{nome}.html"
    arq.write_text(build_html(nome), encoding="utf-8")
    return arq


@pytest.fixture(scope="module")
def nuke(tmp_path_factory):
    return _pagina(tmp_path_factory, NUKE)


@pytest.fixture(scope="module")
def mirage(tmp_path_factory):
    return _pagina(tmp_path_factory, MIRAGE)


def _abre(navegador, arq, w=1440, h=900):
    ctx = navegador.new_context(viewport={"width": w, "height": h})
    pg = ctx.new_page()
    pg.goto(arq.as_uri() + "#replay")
    pg.wait_for_function("() => window.MapAnnotations && MapAnnotations._interno.S.reprojecoes > 0")
    pg.wait_for_timeout(500)
    return ctx, pg


VISTA = "() => { const v = MapAnnotations._interno.S.view; return [v.zoom, v.panX, v.panY]; }"


def test_a_conta_do_enquadramento_cobre_todos_os_pontos_com_margem(navegador, nuke):
    ctx, pg = _abre(navegador, nuke)
    try:
        r = pg.evaluate("""() => { const radar = { width: 1024, height: 1024 };
            const e = MapCore.enquadramento([[400, 400, 0], [600, 500, 30]], radar), v = { zoom: 1, panX: 0, panY: 0 };
            MapCore.vistaCentrada(v, radar, e.zoom, e.cx, e.cy);
            const ponta = [[400, 400], [630, 530]].map(p => [p[0] * v.zoom + v.panX, p[1] * v.zoom + v.panY]);
            const vazio = MapCore.enquadramento([], radar), largo = MapCore.enquadramento([[10, 10, 0], [1000, 1000, 0]], radar);
            return { zoom: e.zoom, ponta, vazio: vazio.zoom, largo: largo.zoom }; }""")
        assert r["zoom"] > 2 and r["vazio"] == 1 and r["largo"] == 1       # abaixo de 1,1 não mexe na vista
        assert all(90 <= c <= 1024 - 90 for pt in r["ponta"] for c in pt)       # a margem mínima de 90 px de tela
        assert all(0 <= c <= 1024 for pt in r["ponta"] for c in pt)
    finally:
        ctx.close()


def _pontos_do_round(r, radar, raio_smoke, raio_fogo):
    """Todos os pontos que o round mostra, em pixels do radar: [x, y, raio]."""
    mx = lambda x: (x - radar["origin_x"]) * radar["scale_px_per_unit"]   # noqa: E731
    my = lambda y: (radar["origin_y"] - y) * radar["scale_px_per_unit"]   # noqa: E731
    pts = []
    for p in r["players"]:
        pts += [(mx(x), my(y), 0) for x, y in zip(p["x"], p["y"]) if x is not None and y is not None]
    for n in r["nades"]:
        pts += [(mx(x), my(y), 0) for x, y in zip(n["x"], n["y"]) if x is not None and y is not None]
    pts += [(mx(q["x"]), my(q["y"]), 0) for q in r["pops"]]                    # onde a granada detonou
    for e in r["events"]:                                                      # kills e bomba: vítima e autor
        pts += [(mx(e[a]), my(e[b]), 0) for a, b in (("x", "y"), ("ax", "ay")) if e.get(a) is not None and e.get(b) is not None]
    pts += [(mx(z["x"]), my(z["y"]), raio_smoke) for z in r["smokes"]]
    pts += [(mx(z["x"]), my(z["y"]), raio_fogo) for z in r["fires"]]
    return pts


def test_na_nuke_nada_sai_do_quadro_em_nenhum_round(navegador, nuke):
    import json
    rounds = json.loads((RAIZ / "data" / "processed" / NUKE / "replay.json").read_text(encoding="utf-8"))["rounds"]
    ctx, pg = _abre(navegador, nuke)
    try:
        radar = pg.evaluate("() => ({ origin_x: __RADAR__.origin_x, origin_y: __RADAR__.origin_y, scale_px_per_unit: __RADAR__.scale_px_per_unit, "
                            "width: __RADAR__.width, height: __RADAR__.height, smoke: MapCore.RAIO_SMOKE_UNIDADES, fogo: MapCore.RAIO_MOLOTOV_UNIDADES })")
        escala = radar["scale_px_per_unit"]
        enquadrados = 0
        for r in rounds:
            pg.locator("#strip .rchip", has_text=str(r["round"])).first.click()
            pg.wait_for_timeout(120)
            zoom, px, py = pg.evaluate(VISTA)
            enquadrados += zoom > 1.1
            for x, y, raio in _pontos_do_round(r, radar, radar["smoke"] * escala, radar["fogo"] * escala):
                for cx, cy in ((x - raio, y - raio), (x + raio, y + raio)):
                    sx, sy = cx * zoom + px, cy * zoom + py
                    assert 0 <= sx <= radar["width"] and 0 <= sy <= radar["height"], (r["round"], zoom, (x, y, raio), (sx, sy))
        assert enquadrados >= len(rounds) // 2                      # a Nuke ganhou enquadramento na maioria dos rounds
    finally:
        ctx.close()


def test_o_nome_do_jogador_nao_fica_cortado_na_borda_da_nuke(navegador, nuke):
    ctx, pg = _abre(navegador, nuke, 1366, 657)
    try:
        for rnd in (9, 3, 14):
            pg.locator("#strip .rchip", has_text=str(rnd)).first.click()
            pg.wait_for_timeout(200)
            lado = pg.evaluate("document.getElementById('map').getBoundingClientRect().width")
            for fracao in (0.1, 0.4, 0.7, 0.95):
                pg.evaluate("""f => { const s = document.getElementById('scrub'); s.value = Math.round(+s.max * f);
                    s.dispatchEvent(new Event('input')); }""", fracao)
                pg.wait_for_timeout(150)
                caixas = pg.evaluate("window.__medicaoRotulos.caixas()")
                assert caixas
                for c in caixas:
                    assert c["x"] >= 0 and c["y"] >= 0 and c["x"] + c["w"] <= lado + 0.5 and c["y"] + c["h"] <= lado + 0.5, (rnd, fracao, c, lado)
    finally:
        ctx.close()


def test_as_outras_partidas_nao_mudam_e_o_zoom_manual_vale_ate_trocar_de_round(navegador, mirage, nuke):
    ctx, pg = _abre(navegador, mirage)
    try:
        for rnd in (1, 6, 15):
            pg.locator("#strip .rchip", has_text=str(rnd)).first.click()
            pg.wait_for_timeout(120)
            assert pg.evaluate(VISTA) == [1, 0, 0]
    finally:
        ctx.close()
    ctx, pg = _abre(navegador, nuke)
    try:
        pg.locator("#strip .rchip", has_text="9").first.click()
        pg.wait_for_timeout(150)
        z9 = pg.evaluate(VISTA)[0]
        pg.evaluate("MapAnnotations._interno.reseta()")            # a pessoa volta ao mapa inteiro
        assert pg.evaluate(VISTA) == [1, 0, 0]
        pg.click("#play"); pg.wait_for_timeout(300); pg.click("#play")
        assert pg.evaluate(VISTA) == [1, 0, 0]                      # tocar não reenquadra
        pg.locator("#strip .rchip", has_text="9").first.click()     # trocar de round (mesmo o 9) enquadra de novo
        pg.wait_for_timeout(150)
        assert pg.evaluate(VISTA)[0] == z9
    finally:
        ctx.close()
