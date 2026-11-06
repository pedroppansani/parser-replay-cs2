"""Reescrever R6b (decisão 62): os blocos "em breve", o alternador Real | Sua versão no celular e o teclado (setas) com o anúncio só ao soltar."""
from __future__ import annotations

import re

import pytest

sync_api = pytest.importorskip("playwright.sync_api")

from tests.test_reescrever_modo import (  # noqa: E402,F401  (fixtures e ajudas)
    _abre, _estado, _sai, navegador, pagina)

TELAS = {"1440x900": (1440, 900), "1366x657": (1366, 657), "375": (375, 812)}
PALCO = "() => { const r = document.getElementById('palco').getBoundingClientRect(); return [Math.round(r.left), Math.round(r.top + scrollY), Math.round(r.width), Math.round(r.height)]; }"


def _clica(pg, sel, nth=0):
    pg.evaluate("([s, i]) => document.querySelectorAll(s)[i].click()", [sel, nth])
    pg.wait_for_timeout(120)


def _px_do_radar(p_, pg):
    return pg.evaluate("p => { const R = window.__RADAR__; return [(p.x - R.origin_x) * R.scale_px_per_unit, (R.origin_y - p.y) * R.scale_px_per_unit]; }", p_)


@pytest.mark.parametrize("tela", list(TELAS))
def test_os_blocos_em_breve_aparecem_desligados_e_nao_fazem_nada(navegador, pagina, tela):
    ctx, pg, erros = _abre(navegador, pagina, *TELAS[tela])
    try:
        _clica(pg, "#rw-entrar")
        itens = pg.locator("#rw-depois .rw-breve")
        assert itens.count() == 3
        assert [t.split("\n")[0].strip() for t in itens.all_inner_texts()] == ["Quando fizeram isso de verdade", "Compartilhar por link", "Salvar no grupo"]
        for i in range(3):
            it = itens.nth(i)
            assert it.get_attribute("aria-disabled") == "true" and "em breve" in it.inner_text()
            assert it.locator("a, button, input, [tabindex]").count() == 0                      # nada a que se chegue por Tab
        antes, url = pg.evaluate(PALCO), pg.url
        ops = _estado(pg)["pecas"]
        itens.first.evaluate("e => e.click()")
        assert pg.evaluate(PALCO) == antes and pg.url == url and _estado(pg)["pecas"] == ops   # clicar não faz nada
        assert not erros
    finally:
        ctx.close()


def test_o_alternador_so_existe_no_celular_e_no_modo(navegador, pagina):
    for tela in ("1440x900", "1366x657"):
        ctx, pg, _ = _abre(navegador, pagina, *TELAS[tela])
        try:
            _clica(pg, "#rw-entrar")
            assert not pg.locator("#rw-ver").is_visible()                                       # no computador o real vem como fantasma
        finally:
            ctx.close()
    ctx, pg, erros = _abre(navegador, pagina, 375, 812)
    try:
        assert not pg.locator("#rw-ver").is_visible()                                           # fora do modo, nada
        _clica(pg, "#rw-entrar")
        assert pg.locator("#rw-ver").is_visible()
        assert pg.get_attribute("#rw-ver", "role") == "radiogroup"
        radios = pg.locator("#rw-ver [role=radio]")
        assert radios.count() == 2 and [t.strip() for t in radios.all_inner_texts()] == ["Real", "Sua versão"]
        assert all(radios.nth(i).bounding_box()["height"] >= 43.5 for i in range(2))
        assert not pg.locator("#rw-fantasma").is_visible()                                      # sem fantasma por cima
        # nada se sobrepõe: o alternador fica fora do transporte, do mapa e da legenda
        a = pg.locator("#rw-ver").bounding_box()
        for outro in (".transport", "#map", "#maplegend"):
            b = pg.locator(outro).first.bounding_box()
            assert a["y"] >= b["y"] + b["height"] - 1 or a["y"] + a["height"] <= b["y"] + 1, outro
        assert not erros
    finally:
        ctx.close()


def test_no_celular_real_mostra_o_real_e_sua_versao_a_sua_com_o_rotulo_e_o_relogio(navegador, pagina):
    ctx, pg, erros = _abre(navegador, pagina, 375, 812)
    try:
        _clica(pg, "#rw-entrar")
        nome = next(p["nome"] for p in _estado(pg)["pecas"] if p["editavel"])
        x, y = next(p for p in _estado(pg)["pecas"] if p["nome"] == nome)["tela"]
        pg.mouse.move(x, y); pg.mouse.down(); pg.mouse.move(x + 50, y - 30, steps=6); pg.mouse.up(); pg.wait_for_timeout(200)
        _clica(pg, "#play"); pg.wait_for_timeout(500); _clica(pg, "#play")
        e = _estado(pg)
        assert e["sua"] and e["ver"] == "sua" and next(p for p in e["pecas"] if p["nome"] == nome)["agora"] is not None
        assert re.match(r"Sua versão · \d+:\d\d$", e["rotuloVer"])
        pg.locator("#rw-ver [data-ver=real]").evaluate("e => e.click()"); pg.wait_for_timeout(200)
        e = _estado(pg)
        assert e["ver"] == "real" and e["vendoReal"] and next(p for p in e["pecas"] if p["nome"] == nome)["agora"] is None   # o real: a peça não vai ao ponto novo
        assert re.match(r"Real · \d+:\d\d$", e["rotuloVer"])
        assert pg.get_attribute("#rw-ver [data-ver=real]", "aria-checked") == "true" and pg.get_attribute("#rw-ver [data-ver=sua]", "aria-checked") == "false"
        pg.locator("#rw-ver [data-ver=real]").focus(); pg.keyboard.press("ArrowRight")           # radiogroup: a seta troca e leva o foco
        assert _estado(pg)["ver"] == "sua" and pg.evaluate("document.activeElement.dataset.ver") == "sua"
        assert not erros
    finally:
        ctx.close()


def test_as_setas_movem_a_peca_em_foco_e_o_leitor_de_tela_so_ouve_ao_soltar(navegador, pagina):
    ctx, pg, erros = _abre(navegador, pagina, 1440, 900)
    try:
        _clica(pg, "#rw-entrar")
        nome = next(p["nome"] for p in _estado(pg)["pecas"] if p["editavel"])
        pg.locator(f".peca-rw[data-nome='{nome}']").focus()
        p0 = next(p for p in _estado(pg)["pecas"] if p["nome"] == nome)
        x0, y0 = p0["x"], p0["y"]
        pg.evaluate("() => { window.__mut = 0; new MutationObserver(l => { window.__mut += l.length; }).observe(document.getElementById('rw-mudou'), { childList: true, characterData: true, subtree: true }); }")
        pg.keyboard.down("ArrowRight"); pg.keyboard.down("ArrowRight"); pg.keyboard.down("ArrowRight")          # a tecla repetindo
        p = next(q for q in _estado(pg)["pecas"] if q["nome"] == nome)
        assert abs(p["x"] - (x0 + 60)) < 0.01 and abs(p["y"] - y0) < 0.01                                     # 3 passos de 20 u para a direita
        assert pg.evaluate("window.__mut") == 0                                                              # nada anunciado enquanto a tecla está apertada
        pg.keyboard.up("ArrowRight")
        assert pg.evaluate("window.__mut") > 0 and "vai até o ponto marcado" in pg.inner_text("#rw-mudou")    # ao soltar, uma vez
        pg.keyboard.press("Shift+ArrowUp")                                                                    # Shift anda mais (norte = y maior)
        p = next(q for q in _estado(pg)["pecas"] if q["nome"] == nome)
        assert abs(p["y"] - (y0 + 100)) < 0.01 and _estado(pg)["selecionada"] == nome
        assert pg.evaluate("document.activeElement.dataset.nome") == nome                                     # o foco fica na peça
        assert not erros
    finally:
        ctx.close()


def test_as_setas_respeitam_o_mapa_o_ponto_do_real_e_quem_esta_morto(navegador, pagina):
    ctx, pg, erros = _abre(navegador, pagina, 1440, 900)
    try:
        _clica(pg, "#rw-entrar")
        e = _estado(pg)
        nome = next(p["nome"] for p in e["pecas"] if p["editavel"])
        pg.locator(f".peca-rw[data-nome='{nome}']").focus()
        pg.keyboard.press("ArrowRight"); pg.keyboard.press("ArrowLeft")                                       # de volta ao ponto do real: não conta como movida
        assert not next(p for p in _estado(pg)["pecas"] if p["nome"] == nome)["editada"] and "Nada ainda" in pg.inner_text("#rw-mudou")
        for _ in range(80):                                                                                    # empurra até a borda do mapa
            pg.keyboard.press("Shift+ArrowLeft")
        x, y = _px_do_radar(next(p for p in _estado(pg)["pecas"] if p["nome"] == nome), pg)
        assert x >= -0.5 and y >= -0.5                                                                         # nunca sai da imagem do radar
        morto = next((p["nome"] for p in e["pecas"] if not p["editavel"]), None)
        if morto:
            pg.locator(f".peca-rw[data-nome='{morto}']").focus(); pg.keyboard.press("ArrowRight")
            assert not next(p for p in _estado(pg)["pecas"] if p["nome"] == morto)["editada"]                 # quem já morreu no instante não se move
        assert not erros
    finally:
        ctx.close()
