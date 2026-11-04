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


def _pontos_do_round(r, radar, raio_smoke, raio_fogo, andar):
    """Os pontos que o round mostra NAQUELE andar, em pixels do radar: [x, y, raio]. Granada, área, detonação e kill não trazem
    andar no dado: valem o de quem as fez, no instante em que as fez."""
    mx = lambda x: (x - radar["origin_x"]) * radar["scale_px_per_unit"]   # noqa: E731
    my = lambda y: (radar["origin_y"] - y) * radar["scale_px_per_unit"]   # noqa: E731
    por_nome = {p["name"]: p for p in r["players"]}

    def dele(nome, f):
        p = por_nome.get(nome)
        return p is not None and p["lv"][max(0, min(len(p["lv"]) - 1, int(f)))] == andar

    ok = lambda x, y: x is not None and y is not None   # noqa: E731
    pts = []
    for p in r["players"]:
        pts += [(mx(x), my(y), 0) for x, y, lv in zip(p["x"], p["y"], p["lv"]) if ok(x, y) and lv == andar]
    for n in r["nades"]:
        if dele(n["by"], n["f0"]):
            pts += [(mx(x), my(y), 0) for x, y in zip(n["x"], n["y"]) if ok(x, y)]
    pts += [(mx(q["x"]), my(q["y"]), 0) for q in r["pops"] if dele(q["by"], q["f"])]
    for e in r["events"]:                                                      # kills e bomba: vítima e autor
        vitima, autor = e.get("victim") or e.get("attacker"), e.get("attacker") or e.get("victim")
        if dele(vitima, e["f"]) and ok(e.get("x"), e.get("y")):
            pts.append((mx(e["x"]), my(e["y"]), 0))
        if dele(autor, e["f"]) and ok(e.get("ax"), e.get("ay")):
            pts.append((mx(e["ax"]), my(e["ay"]), 0))
    pts += [(mx(z["x"]), my(z["y"]), raio_smoke) for z in r["smokes"] if dele(z["by"], z["f0"])]
    pts += [(mx(z["x"]), my(z["y"]), raio_fogo) for z in r["fires"] if dele(z["by"], z["f0"])]
    return pts


def _rounds():
    import json
    return json.loads((RAIZ / "data" / "processed" / NUKE / "replay.json").read_text(encoding="utf-8"))["rounds"]


def _radar(pg):
    return pg.evaluate("() => ({ origin_x: __RADAR__.origin_x, origin_y: __RADAR__.origin_y, scale_px_per_unit: __RADAR__.scale_px_per_unit, "
                       "width: __RADAR__.width, height: __RADAR__.height, smoke: MapCore.RAIO_SMOKE_UNIDADES, fogo: MapCore.RAIO_MOLOTOV_UNIDADES })")


def _trava_andar(pg, andar):
    pg.locator(f'.levelpick button[data-lv="{andar}"]').click()
    pg.wait_for_timeout(60)


def test_na_nuke_nada_sai_do_quadro_em_nenhum_round_nem_em_nenhum_andar(navegador, nuke):
    rounds = _rounds()
    ctx, pg = _abre(navegador, nuke)
    try:
        radar = _radar(pg)
        escala = radar["scale_px_per_unit"]
        zooms = {0: [], 1: []}
        for r in rounds:
            pg.locator("#strip .rchip", has_text=str(r["round"])).first.click()
            pg.wait_for_timeout(100)
            for andar in (0, 1):
                _trava_andar(pg, andar)
                zoom, px, py = pg.evaluate(VISTA)
                zooms[andar].append(zoom)
                for x, y, raio in _pontos_do_round(r, radar, radar["smoke"] * escala, radar["fogo"] * escala, andar):
                    for cx, cy in ((x - raio, y - raio), (x + raio, y + raio)):
                        sx, sy = cx * zoom + px, cy * zoom + py
                        assert 0 <= sx <= radar["width"] and 0 <= sy <= radar["height"], (r["round"], andar, zoom, (x, y, raio), (sx, sy))
        # o quadro é a área do andar: o mesmo zoom em todos os rounds, com a trava de 2,5
        assert len(set(zooms[0])) == 1 and len(set(zooms[1])) == 1, zooms
        assert 1.1 < zooms[0][0] < zooms[1][0] <= 2.5, zooms
    finally:
        ctx.close()


def test_todo_jogador_vivo_do_outro_andar_fora_do_quadro_tem_a_sua_marca_na_borda(navegador, nuke):
    rounds = _rounds()
    ctx, pg = _abre(navegador, nuke)
    try:
        radar = _radar(pg)
        vistos = 0
        for r in rounds[::2]:
            pg.locator("#strip .rchip", has_text=str(r["round"])).first.click()
            pg.wait_for_timeout(100)
            for andar in (0, 1):
                _trava_andar(pg, andar)
                zoom, px, py = pg.evaluate(VISTA)
                for f in range(0, r["frames"], max(1, r["frames"] // 6)):
                    pg.evaluate("""f => { const s = document.getElementById('scrub'); s.value = f; s.dispatchEvent(new Event('input')); }""", f)
                    pg.wait_for_timeout(40)
                    esperados = set()
                    for p in r["players"]:
                        if not p["alive"][f] or p["lv"][f] == andar:
                            continue
                        sx = ((p["x"][f] - radar["origin_x"]) * radar["scale_px_per_unit"]) * zoom + px
                        sy = ((radar["origin_y"] - p["y"][f]) * radar["scale_px_per_unit"]) * zoom + py
                        if not (0 <= sx <= radar["width"] and 0 <= sy <= radar["height"]):
                            esperados.add(p["name"])
                    marcas = pg.evaluate("window.__marcasDeBorda()")
                    assert esperados == {m["nome"] for m in marcas}, (r["round"], andar, f, esperados, marcas)
                    vistos += len(esperados)
                    lado = pg.evaluate("document.getElementById('map').getBoundingClientRect().width")
                    for m in marcas:                                       # a marca fica dentro do mapa, nunca na barra de tocar
                        assert 0 < m["x"] < lado and 0 < m["y"] < lado, (m, lado)
                    for i, a in enumerate(marcas):                          # e duas marcas nunca se sobrepõem
                        for b in marcas[i + 1:]:
                            assert max(abs(a["x"] - b["x"]), abs(a["y"] - b["y"])) >= 12, (r["round"], andar, f, a, b)
        assert vistos > 0                                  # o caso existe de verdade na partida
    finally:
        ctx.close()


@pytest.mark.parametrize("w,h", [(1440, 900), (1366, 657), (375, 812)])
def test_nenhum_nome_se_sobrepoe_nem_sai_do_quadro_nem_vai_para_baixo_da_barra_de_tocar(navegador, nuke, w, h):
    ctx, pg = _abre(navegador, nuke, w, h)
    try:
        for rnd in (9, 3, 14):
            pg.locator("#strip .rchip", has_text=str(rnd)).first.click()
            pg.wait_for_timeout(200)
            for andar in (0, 1):
                _trava_andar(pg, andar)
                pg.evaluate("document.getElementById('map').scrollIntoView({block: 'center'})") if w < 1024 else None
                geo = pg.evaluate("""() => { const m = document.getElementById('map').getBoundingClientRect(),
                    t = document.querySelector('.transport').getBoundingClientRect(); return { lado: m.width, fundo: m.bottom, barra: t.top }; }""")
                if w >= 1024:
                    assert geo["fundo"] <= geo["barra"] + 0.5, geo      # o mapa termina antes da barra de tocar
                lado = geo["lado"]
                for fracao in (0.1, 0.4, 0.7, 0.95):
                    pg.evaluate("""f => { const s = document.getElementById('scrub'); s.value = Math.round(+s.max * f);
                        s.dispatchEvent(new Event('input')); }""", fracao)
                    pg.wait_for_timeout(150)
                    caixas = pg.evaluate("window.__medicaoRotulos.caixas()")
                    for c in caixas:
                        assert c["x"] >= 0 and c["y"] >= 0 and c["x"] + c["w"] <= lado + 0.5 and c["y"] + c["h"] <= lado + 0.5, (rnd, andar, fracao, c, lado)
                    for i, a in enumerate(caixas):
                        for b in caixas[i + 1:]:
                            dentro = a["x"] < b["x"] + b["w"] and b["x"] < a["x"] + a["w"] and a["y"] < b["y"] + b["h"] and b["y"] < a["y"] + a["h"]
                            assert not dentro, (rnd, andar, fracao, a, b)
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
        _trava_andar(pg, 1)                                         # trocar de andar passa para o quadro daquele andar
        assert pg.evaluate(VISTA)[0] != z9
        _trava_andar(pg, 0)
        assert pg.evaluate(VISTA)[0] == z9
    finally:
        ctx.close()
