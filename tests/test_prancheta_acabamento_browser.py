"""Prancheta (auditoria, item 5.3): volta ao site, sem texto de depuração na
tela e banco de peças dizendo qual lado é qual."""
from __future__ import annotations

import pytest

pytest.importorskip("playwright.sync_api")

from tests.test_tactics_browser import abre, contexto, navegador, pagina  # noqa: E402,F401  (fixtures)


def test_cabecalho_volta_para_a_landing_e_para_as_partidas(contexto, pagina):
    pg = abre(contexto, pagina)
    # design-E: a volta ao site é o topo do site (marca -> landing; "Partidas" -> a grade da landing)
    assert pg.get_attribute(".site-topo .marca", "href") == "index.html"
    assert pg.get_attribute('.site-nav a:has-text("Partidas")', "href") == "index.html#partidas"


def test_o_contador_de_operacoes_sai_da_tela_e_fica_no_exportado(contexto, pagina):
    pg = abre(contexto, pagina)
    assert pg.locator("#pr-historico").count() == 0
    assert "operações · contador" not in pg.inner_text("body")
    doc = pg.evaluate("() => Prancheta._interno.S.doc")
    assert "operacoes" in doc and "contador" in doc


def test_o_banco_diz_qual_lado_e_ct_e_qual_e_tr(contexto, pagina):
    pg = abre(contexto, pagina)
    rotulos = pg.eval_on_selector_all("#pr-banco .pr-lado-rotulo", "els => els.map(e => [e.textContent, e.className])")
    assert rotulos == [["CT", "pr-lado-rotulo ct"], ["TR", "pr-lado-rotulo t"]]
    # cada rótulo vem logo antes das fichas do seu lado
    ordem = pg.eval_on_selector_all("#pr-banco > *", "els => els.map(e => e.dataset.lado || e.textContent)")
    assert ordem[0] == "CT" and set(ordem[1:6]) == {"ct"} and ordem[6] == "TR" and set(ordem[7:12]) == {"t"}
