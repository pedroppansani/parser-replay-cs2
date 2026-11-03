"""Cartão 15, opção B (modo palco, a partir de 1024 x 700): a faixa de rounds gruda sob as abas, o palco para logo
abaixo dela, o mapa tem um tamanho só no Replay e o celular não muda."""
from __future__ import annotations

from pathlib import Path

import pytest

sync_api = pytest.importorskip("playwright.sync_api")

from tests.test_replay_layout import _abre, pagina_html  # noqa: E402,F401  (fixture)
from tests.test_tactics_browser import navegador  # noqa: E402,F401  (fixture)

TELAS = [(1440, 900), (1366, 768)]
SONDA = """() => { const r = s => document.querySelector(s).getBoundingClientRect(), m = r('#map');
  return { mapa: Math.round(m.width * 100) / 100, altura: Math.round(m.height * 100) / 100, abasFim: r('#abas-moldura').bottom,
           faixaTopo: r('#strip').top, faixaFim: r('#strip').bottom, palco: r('#palco').top, squadCt: r('#squad-ct').top,
           squadT: r('#squad-t').top, play: r('#play').bottom, rolagem: scrollY, h: innerHeight }; }"""


@pytest.mark.parametrize("w,h", TELAS)
def test_o_palco_para_logo_abaixo_da_faixa_e_as_colunas_comecam_com_ele(navegador, pagina_html, w, h):
    ctx, pg = _abre(navegador, pagina_html, w, h, "")
    try:
        pg.click('[data-tab="replay"]')
        pg.wait_for_timeout(900)   # a rolagem suave
        s = pg.evaluate(SONDA)
        assert s["rolagem"] > 0
        assert abs(s["faixaTopo"] - s["abasFim"]) <= 1, s       # a faixa gruda sem vão nem sobreposição às abas
        assert abs(s["palco"] - (s["faixaFim"] + 8)) <= 1, s    # o palco logo abaixo da faixa, nada escondido atrás dela
        assert abs(s["squadCt"] - s["palco"]) <= 1 and abs(s["squadT"] - s["palco"]) <= 1, s
        assert s["play"] <= s["h"], s                            # o tocar à vista
        assert abs(s["mapa"] - s["altura"]) <= 1                 # quadrado
    finally:
        ctx.close()


@pytest.mark.parametrize("w,h", TELAS)
def test_o_mapa_tem_um_tamanho_so_no_replay(navegador, pagina_html, w, h):
    ctx, pg = _abre(navegador, pagina_html, w, h, "")
    try:
        pg.click('[data-tab="replay"]')
        pg.wait_for_timeout(900)
        base = pg.evaluate(SONDA)["mapa"]
        assert base > {900: 560, 768: 430}[h]                    # bem acima dos 345 e 231 de antes
        for passo in ("round", "tocar", "lugares", "rolar", "zoom"):
            if passo == "round":
                pg.locator("#strip .rchip", has_text="15").first.click()
            elif passo == "tocar":
                pg.click("#play"); pg.wait_for_timeout(300); pg.click("#play")
            elif passo == "lugares":
                pg.click("#lugares-botao")
            elif passo == "rolar":
                pg.mouse.wheel(0, 700); pg.wait_for_timeout(300)
            pg.wait_for_timeout(900)
            assert pg.evaluate(SONDA)["mapa"] == base, passo
    finally:
        ctx.close()


def test_trocar_de_round_com_a_faixa_a_vista_sem_rolar_a_pagina(navegador, pagina_html):
    ctx, pg = _abre(navegador, pagina_html, 1440, 900, "")
    try:
        pg.click('[data-tab="replay"]')
        pg.wait_for_timeout(900)
        antes = pg.evaluate(SONDA)
        pg.locator("#strip .rchip", has_text="7").first.click()
        pg.wait_for_timeout(900)
        depois = pg.evaluate(SONDA)
        assert depois["rolagem"] == antes["rolagem"] and depois["faixaTopo"] == antes["faixaTopo"]
        # com a página rolada para baixo (lista de lances), a faixa continua à vista e trocar de round volta ao palco
        pg.mouse.wheel(0, 1500); pg.wait_for_timeout(500)
        assert pg.evaluate(SONDA)["faixaTopo"] == antes["faixaTopo"]
        pg.wait_for_timeout(600)
        pg.locator("#strip .rchip", has_text="9").first.click()
        pg.wait_for_timeout(900)
        assert abs(pg.evaluate(SONDA)["rolagem"] - antes["rolagem"]) <= 1
    finally:
        ctx.close()


def test_nao_briga_com_a_rolagem_da_pessoa_e_reduzir_movimento_rola_na_hora(navegador, pagina_html):
    ctx, pg = _abre(navegador, pagina_html, 1440, 900, "")
    try:
        pg.click('[data-tab="replay"]')
        pg.wait_for_timeout(900)
        pg.mouse.wheel(0, 1500); pg.wait_for_timeout(700)
        rolada = pg.evaluate("scrollY")
        pg.mouse.wheel(0, 100)                                   # a pessoa está rolando ...
        pg.locator("#strip .rchip", has_text="3").first.click()  # ... e troca de round: a página não volta sozinha
        pg.wait_for_timeout(900)
        assert pg.evaluate("scrollY") >= rolada
    finally:
        ctx.close()
    ctx = navegador.new_context(viewport={"width": 1440, "height": 900}, reduced_motion="reduce")
    pg = ctx.new_page()
    try:
        pg.goto(pagina_html.as_uri())
        pg.wait_for_selector("#play", state="attached")
        pg.click('[data-tab="replay"]')
        pg.wait_for_timeout(50)                                  # sem suavização: já chegou
        s = pg.evaluate(SONDA)
        assert abs(s["palco"] - (s["faixaFim"] + 8)) <= 1 and s["rolagem"] > 0
    finally:
        ctx.close()


def test_o_celular_nao_muda(navegador, pagina_html):
    ctx, pg = _abre(navegador, pagina_html, 375, 812, "")
    try:
        pg.click('[data-tab="replay"]')
        pg.wait_for_timeout(500)
        s = pg.evaluate(SONDA)
        assert s["rolagem"] == 0
        assert pg.eval_on_selector("#strip", "e => getComputedStyle(e).position") == "static"
    finally:
        ctx.close()
