"""Fase 11 no replay: a granada DESENHADA no "Desenhar" (camada de anotação, decisão 23). Carimbo, desfazer,
refazer, persistência, arrastar, Delete, área, atalhos 1 a 4 com o pincel e o fluxo só pelo teclado."""
from __future__ import annotations

import pytest

pytest.importorskip("playwright.sync_api")

from metrics.annotations import valida  # noqa: E402
from tests.test_annotations_browser import (abre, contexto, espera_mapa, estado, liga, modelo,  # noqa: E402,F401
                                            na_vista, navegador, partida, traco_na_tela)


def _granadas(pg):
    return [t for lista in modelo(pg)["rounds"].values() for t in lista if t["ferramenta"] == "granada"]


def _no_mapa(pg, fx, fy):
    na_vista(pg)
    c = pg.locator("#map").bounding_box()
    return c["x"] + c["width"] * fx, c["y"] + c["height"] * fy


def _cor(pg, arma):
    h = pg.evaluate(f"() => MapCore.NADE_COLOR[{arma!r}]")
    return tuple(int(h[i:i + 2], 16) for i in (1, 3, 5))


def _pincel(pg):
    liga(pg)
    assert pg.locator("#anot-granadas").is_hidden()                    # com a caneta, o carimbo não aparece
    pg.click('[data-ferramenta="granada"]')
    assert pg.is_visible("#anot-granadas")
    # a granada desenhada tem a cor do tipo e o tamanho do glifo: cor e espessura saem da barra
    assert pg.locator("#anot-cor").is_hidden() and pg.locator("#anot-espessuras").is_hidden()


def test_carimbar_desfazer_refazer_e_recarregar(contexto, partida):
    """Teste 1 do prompt: a smoke desenhada usa a pilha e a persistência das outras anotações."""
    pg = abre(contexto, partida)
    _pincel(pg)
    pg.click('[data-arma-desenho="smoke"]')
    pg.mouse.click(*_no_mapa(pg, 0.5, 0.45))
    gs = _granadas(pg)
    assert len(gs) == 1 and gs[0]["arma"] == "smoke" and gs[0]["area"] is False and len(gs[0]["pontos"]) == 1
    assert traco_na_tela(pg, gs[0]["pontos"][0], _cor(pg, "smoke"))
    assert valida(modelo(pg)) == []                                  # o espelho em Python aceita o arquivo
    pg.keyboard.press("Control+z")
    assert _granadas(pg) == []
    pg.keyboard.press("Control+Shift+z")
    assert _granadas(pg) == gs
    antes = modelo(pg)
    pg.evaluate("() => MapAnnotations._interno.gravaPendentes()")
    pg.reload()
    pg.locator('[data-tab="replay"]').first.click()
    pg.wait_for_function("() => MapAnnotations._interno.S.reprojecoes > 0")
    espera_mapa(pg)
    assert modelo(pg) == antes
    assert traco_na_tela(pg, gs[0]["pontos"][0], _cor(pg, "smoke"))


def test_arrastar_move_area_liga_e_delete_apaga(contexto, partida):
    pg = abre(contexto, partida)
    _pincel(pg)
    pg.click('[data-arma-desenho="molotov"]')
    a = _no_mapa(pg, 0.5, 0.45)
    pg.mouse.click(*a)
    antes = _granadas(pg)[0]["pontos"][0]
    pg.mouse.move(*a)
    pg.mouse.down()
    pg.mouse.move(a[0] + 40, a[1] + 30, steps=5)
    pg.mouse.up()
    gs = _granadas(pg)
    assert len(gs) == 1 and gs[0]["pontos"][0] != antes                 # moveu, não carimbou outra
    # a área só existe para smoke e molotov, e liga com a granada selecionada
    pg.click("#anot-area")
    assert _granadas(pg)[0]["area"] is True
    pg.keyboard.press("Delete")
    assert _granadas(pg) == []


def test_com_o_pincel_1_a_4_escolhem_o_tipo_e_o_teclado_carimba(contexto, partida):
    """Teste 4 (lado do replay) e teste 5: tudo pelo teclado -- 8 liga o pincel, 2 escolhe a flash, as setas
    andam o cursor e Enter carimba."""
    pg = abre(contexto, partida)
    liga(pg)
    pg.keyboard.press("8")
    assert estado(pg, "ferramenta") == "granada"
    pg.keyboard.press("2")
    assert estado(pg, "armaDesenho") == "flash" and estado(pg, "ferramenta") == "granada"
    for tecla in ("ArrowRight", "ArrowRight", "ArrowDown"):
        pg.keyboard.press(tecla)
    pg.keyboard.press("Enter")
    gs = _granadas(pg)
    assert len(gs) == 1 and gs[0]["arma"] == "flash"
    pg.keyboard.press("Delete")
    assert _granadas(pg) == []
    # o "?" explica os atalhos do pincel
    pg.click("#b-atalhos")
    ajuda = pg.inner_text("#atalhos")
    assert "8 é a granada desenhada" in ajuda and "1 a 4 escolhem smoke, flash, HE ou molotov" in ajuda


def test_legenda_tem_a_granada_desenhada(contexto, partida):
    pg = abre(contexto, partida)
    assert "granada desenhada" in pg.inner_text('[data-panel="replay"]')
