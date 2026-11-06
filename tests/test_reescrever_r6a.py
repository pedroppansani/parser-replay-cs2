"""Reescrever R6a (decisão 61): o acabamento do mapa e das peças -- o nome da peça editada esmaece com ela, a Nuke dentro do Reescrever
(arrasto preso à área do andar, marcas de borda, fantasma do outro andar) e a peça do outro andar da prancheta com o desenho do Replay."""
from __future__ import annotations

import pytest

sync_api = pytest.importorskip("playwright.sync_api")

from tests.test_reescrever_modo import (  # noqa: E402,F401  (fixtures e ajudas)
    _abre, _estado, _sai, navegador, pagina)
from tests.test_reescrever_r3 import _arrasta  # noqa: E402

def _alfa_do_nome(pg, nome):
    """A opacidade com que o nome saiu no último desenho (a caixa colocada pela camada de rótulos); None: não saiu."""
    pg.evaluate("() => { const s = document.getElementById('scrub'); s.dispatchEvent(new Event('input')); }")
    pg.wait_for_timeout(200)
    alfas = pg.evaluate("n => window.__medicaoRotulos.caixas().filter(c => c.txt === n).map(c => c.alfa)", nome[:9])
    return alfas[-1] if alfas else None


def test_o_nome_da_peca_editada_esmaece_junto_com_ela_depois_da_morte_do_real(navegador, pagina):
    ctx, pg, erros = _abre(navegador, pagina, 1440, 900)
    try:
        pg.click("#rw-entrar"); _arrasta(pg, "molodoy")
        pg.click("#play"); pg.wait_for_timeout(300); pg.click("#play")
        assert _estado(pg)["esmaecidas"] == []
        assert _alfa_do_nome(pg, "molodoy") == 1                                            # vivo nos dois: o nome inteiro
        pg.evaluate("() => { const s = document.getElementById('scrub'); s.value = s.max; s.dispatchEvent(new Event('input')); }")
        assert _estado(pg)["esmaecidas"] == ["molodoy"]
        assert _alfa_do_nome(pg, "molodoy") == 0.4                                           # o real já o matou: o nome esmaece com a peça
        outro = next(p["nome"] for p in _estado(pg)["pecas"] if p["nome"] != "molodoy" and not p["editada"])
        assert _alfa_do_nome(pg, outro) in (1, None)                                         # as outras peças não mudam
        assert not erros
    finally:
        ctx.close()


# ---- a Nuke dentro do Reescrever (R6a) ----------------------------------------------------------------------------------------------------

PARTIDA_NUKE = "match_05"
ROUND_NUKE, FRAC_NUKE = 2, 0.5         # donk666, PR--, Dafra1D e PerdYYY estão no andar de baixo, com o de cima à mostra


@pytest.fixture(scope="module")
def pagina_nuke(tmp_path_factory):
    from tests.test_reescrever_modo import RAIZ
    from scripts.build_web_page import build_html
    if not (RAIZ / "data" / "processed" / PARTIDA_NUKE / "web_payload.json").exists():
        pytest.skip("sem o processado da partida da Nuke")
    arq = tmp_path_factory.mktemp("rwn") / f"{PARTIDA_NUKE}.html"
    arq.write_text(build_html(PARTIDA_NUKE), encoding="utf-8")
    return arq


def _arrasta_na_vista(pg, nome, dx, dy):
    """Arrasta a peça pela posição dela NA TELA (com o zoom do andar), por `dx`, `dy` px."""
    x, y = next(p for p in _estado(pg)["pecas"] if p["nome"] == nome)["tela"]
    pg.mouse.move(x, y); pg.mouse.down(); pg.mouse.move(x + dx, y + dy, steps=8); pg.mouse.up()
    pg.wait_for_timeout(200)


def _px(pg, p):
    """A posição da peça em pixels do radar (a área do andar vem nessa unidade)."""
    return pg.evaluate("p => { const R = window.__RADAR__; return [(p.x - R.origin_x) * R.scale_px_per_unit, (R.origin_y - p.y) * R.scale_px_per_unit]; }", p)


def test_na_nuke_selecionar_peca_do_outro_andar_leva_a_vista_a_ele_e_sair_devolve(navegador, pagina_nuke):
    ctx, pg, erros = _abre(navegador, pagina_nuke, 1440, 900, round_=ROUND_NUKE, frac=FRAC_NUKE)
    try:
        pg.click("#rw-entrar")
        e = _estado(pg)
        de_baixo = next(p["nome"] for p in e["pecas"] if p["editavel"] and p["nivel"] != e["andar"])
        antes = e["andar"]
        pg.locator(".peca-rw", has_text=de_baixo).first.click()
        e = _estado(pg)
        assert e["selecionada"] == de_baixo and e["andar"] == next(p["nivel"] for p in e["pecas"] if p["nome"] == de_baixo) != antes
        assert pg.locator(".levelpick button.on").get_attribute("data-lv") == str(e["andar"])        # o botão do andar acompanha
        _sai(pg)
        assert _estado(pg)["andar"] == antes and pg.locator(".levelpick button.on").get_attribute("data-lv") == "auto"
        assert not erros
    finally:
        ctx.close()


def test_na_nuke_a_peca_arrastada_nao_sai_da_area_do_andar_dela(navegador, pagina_nuke):
    ctx, pg, erros = _abre(navegador, pagina_nuke, 1440, 900, round_=ROUND_NUKE, frac=FRAC_NUKE)
    try:
        pg.click("#rw-entrar")
        e = _estado(pg)
        nome = next(p["nome"] for p in e["pecas"] if p["editavel"] and p["nivel"] != e["andar"])
        pg.locator(".peca-rw", has_text=nome).first.click()                                           # a vista vai para o andar dele
        pg.wait_for_timeout(400)
        for dx, dy, eixo, lado in ((1500, 0, 0, "x1"), (-1500, 0, 0, "x0"), (0, 1500, 1, "y1"), (0, -1500, 1, "y0")):   # para além de cada borda da área
            _arrasta_na_vista(pg, nome, dx, dy)
            e = _estado(pg)
            p = next(q for q in e["pecas"] if q["nome"] == nome)
            area = e["area"][p["nivel"]]
            xy = _px(pg, p)
            assert area["x0"] - 0.5 <= xy[0] <= area["x1"] + 0.5 and area["y0"] - 0.5 <= xy[1] <= area["y1"] + 0.5, (dx, dy, xy, area)
            assert abs(xy[eixo] - area[lado]) <= 1, (lado, xy, area)                                    # e parou EXATAMENTE na borda (o arrasto pegou a peça)
        assert not erros
    finally:
        ctx.close()


def test_na_nuke_as_marcas_de_borda_sao_so_de_quem_esta_no_outro_andar(navegador, pagina_nuke):
    ctx, pg, erros = _abre(navegador, pagina_nuke, 1440, 900, round_=ROUND_NUKE, frac=FRAC_NUKE)
    try:
        pg.click("#rw-entrar")
        e = _estado(pg)
        nivel = {p["nome"]: p["nivel"] for p in e["pecas"]}
        for andar in (0, 1):
            pg.locator(".levelpick button[data-lv='%d']" % andar).click()
            pg.wait_for_timeout(300)
            marcas = pg.evaluate("window.__marcasDeBorda()")
            assert all(nivel[m["nome"]] != andar for m in marcas)                                     # nunca marca quem está no andar mostrado
        assert not erros
    finally:
        ctx.close()
