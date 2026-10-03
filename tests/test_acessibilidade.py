"""Acessibilidade, Open Graph e favicon (auditoria, item 5.4)."""
from __future__ import annotations

import re
from pathlib import Path

import pytest

from scripts.valida_paleta import (DICROMACIAS, contraste, delta_e_2000, hex_para_rgb, paleta_em_uso,
                                   rgb_para_lab, simula_dicromacia)

RAIZ = Path(__file__).resolve().parent.parent
WEB = RAIZ / "dashboard" / "web"
FONTES = {"template": WEB / "template.html", "prancheta": WEB / "tactics.css", "landing": RAIZ / "scripts" / "build_site.py"}


def _var(texto: str, nome: str) -> str:
    return re.search(rf"--{nome}:\s*(#[0-9a-fA-F]{{6}})", texto).group(1)


@pytest.mark.parametrize("pagina", sorted(FONTES))
def test_dim_tem_contraste_de_4_5_em_todo_fundo_claro(pagina):
    texto = FONTES[pagina].read_text(encoding="utf-8")
    dim = _var(texto, "dim")
    for fundo in ("#ffffff", "#eef1f5", "#e7ebf1"):       # card, paper, paper-2
        assert contraste(dim, fundo) >= 4.5, (pagina, dim, fundo, contraste(dim, fundo))


def test_o_dim_novo_nao_quebra_a_paleta_validada_da_decisao_10():
    dim = _var(FONTES["template"].read_text(encoding="utf-8"), "dim")
    for cor in paleta_em_uso().values():
        for tipo in DICROMACIAS:
            de = delta_e_2000(rgb_para_lab(simula_dicromacia(dim, tipo)), rgb_para_lab(simula_dicromacia(cor, tipo)))
            assert de >= 8.0, (dim, cor, tipo, de)
    assert 'dim: "' + dim + '"' in FONTES["template"].read_text(encoding="utf-8")   # o C.dim dos gráficos


@pytest.mark.parametrize("arquivo", [WEB / "template.html", WEB / "tactics.css", RAIZ / "scripts" / "build_site.py"])
def test_todo_controle_tem_foco_visivel(arquivo):
    assert re.search(r":where\(button, a\[href\], select, input, textarea, summary, \[tabindex\]\):focus-visible",
                     arquivo.read_text(encoding="utf-8"))


def test_canvas_com_rotulo_tem_papel_de_imagem():
    for arq in (WEB / "template.html", WEB / "tactics.html"):
        for tag in re.findall(r"<canvas[^>]*>", arq.read_text(encoding="utf-8")):
            if "aria-label" in tag:
                assert 'role="img"' in tag, (arq.name, tag)


def test_paginas_tem_favicon_e_open_graph():
    from scripts.build_site import build_index
    from scripts.build_tactics_page import build_html as prancheta
    from scripts.meta_da_pagina import FAVICON
    landing = build_index([], "https://github.com/pedroppansani/parser-replay-cs2", [], numeros=None, imagem=None)
    for html in (landing, prancheta("de_mirage", site="https://pedroppansani.github.io/parser-replay-cs2/")):
        assert 'rel="icon"' in html and "og:title" in html and "og:description" in html
        assert 'property="og:image" content="https://pedroppansani.github.io/parser-replay-cs2/replay.png"' in html
    assert FAVICON.startswith("data:image/svg+xml,")


sync_api = pytest.importorskip("playwright.sync_api")

from tests.test_annotations_browser import abre, contexto, navegador, partida  # noqa: E402,F401  (fixtures)


def test_abas_andam_pelas_setas_e_so_a_ativa_entra_no_tab(contexto, partida):
    pg = abre(contexto, partida)
    tabs = pg.locator('[role="tab"]')
    assert [tabs.nth(i).get_attribute("tabindex") for i in range(tabs.count())] == ["0"] + ["-1"] * (tabs.count() - 1)
    tabs.first.focus()
    pg.keyboard.press("ArrowRight")
    assert pg.evaluate("() => document.activeElement.dataset.tab") == "insights"
    assert pg.get_attribute('[data-tab="insights"]', "aria-selected") == "true"
    assert not pg.is_hidden('[data-panel="insights"]')
    pg.keyboard.press("End")
    assert pg.evaluate("() => document.activeElement.dataset.tab") == "estilos"
    pg.keyboard.press("ArrowRight")
    assert pg.evaluate("() => document.activeElement.dataset.tab") == "replay"
    pg.close()
