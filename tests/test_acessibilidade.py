"""Acessibilidade, Open Graph e favicon (auditoria, item 5.4)."""
from __future__ import annotations

import re
from pathlib import Path

import pytest

from metrics.paleta import (DICROMACIAS, contraste, delta_e_2000, hex_para_rgb, le_tokens, paleta_em_uso,
                                   rgb_para_lab, simula_dicromacia)
from scripts.fontes_web import le_fonte

RAIZ = Path(__file__).resolve().parent.parent
WEB = RAIZ / "dashboard" / "web"
# O que cada página injeta: os tokens (dashboard/web/tokens.css) entram pelo marcador /*__TOKENS__*/
FONTES = {"template": WEB / "template.html", "prancheta": WEB / "tactics.html", "landing": RAIZ / "scripts" / "build_site.py",
          "jogadores": WEB / "jogadores.html"}
TOKENS = WEB / "tokens.css"


def _var(texto: str, nome: str) -> str:
    return re.search(rf"--{nome}:\s*(#[0-9a-fA-F]{{6}})", texto).group(1)


def _tokens_dos_temas() -> dict[str, dict[str, str]]:
    """Os tokens de cor de cada tema que pinta texto: o claro e o escuro (landing, partida e jogadores, o que quem lê
    escolhe; o escuro também é a moldura do Replay) e o violeta (prancheta). Fase T: o escuro de antes da v2-5 deixou de
    ser um bloco `.board` por cima do violeta e virou o tema `escuro`."""
    return {tema: le_tokens(tema=tema) for tema in ("claro", "escuro", "violeta")}


# os fundos onde o --apagado aparece em cada tema; o --radar (o mapa) só existe dentro das ilhas escuras
FUNDOS_DO_TEMA = {"claro": ("fundo", "superficie", "superficie-2", "tl-fundo"),
                  "escuro": ("fundo", "superficie", "superficie-2", "tl-fundo", "radar"),
                  "violeta": ("fundo", "superficie", "superficie-2", "tl-fundo", "radar")}


@pytest.mark.parametrize("pagina", sorted(FONTES))
def test_dim_tem_contraste_de_4_5_em_todo_fundo_claro(pagina):
    # Migrado na design-A (decisão 44): a cor secundária é o token --apagado. Desde a v2 há três temas que pintam
    # texto (claro, escuro e violeta; Fase T: o escuro é o de antes da v2-5); cada --apagado é medido contra os fundos
    # do SEU tema (v2-7, OK do Pedro: antes o teste lia o primeiro --apagado do tokens.css, o do escuro). Cada página
    # recebe os MESMOS tokens pelo marcador e não define os dela.
    texto = le_fonte(FONTES[pagina])
    assert "/*__TOKENS__*/" in texto and not re.search(r"--apagado:", texto), pagina
    for tema, tk in _tokens_dos_temas().items():
        for fundo in FUNDOS_DO_TEMA[tema]:
            assert contraste(tk["apagado"], tk[fundo]) >= 4.5, (pagina, tema, tk["apagado"], fundo, contraste(tk["apagado"], tk[fundo]))


def test_o_dim_novo_nao_quebra_a_paleta_validada_da_decisao_10():
    apagado = _var(TOKENS.read_text(encoding="utf-8"), "apagado")
    for cor in paleta_em_uso().values():
        for tipo in DICROMACIAS:
            de = delta_e_2000(rgb_para_lab(simula_dicromacia(apagado, tipo)), rgb_para_lab(simula_dicromacia(cor, tipo)))
            assert de >= 8.0, (apagado, cor, tipo, de)
    assert 'apagado: tk("apagado")' in le_fonte(FONTES["template"])   # o C.apagado dos gráficos


@pytest.mark.parametrize("arquivo", [WEB / "template.html", WEB / "tactics.css", RAIZ / "scripts" / "build_site.py"])
def test_todo_controle_tem_foco_visivel(arquivo):
    assert re.search(r":where\(button, a\[href\], select, input, textarea, summary, \[tabindex\]\):focus-visible",
                     le_fonte(arquivo))


def test_canvas_com_rotulo_tem_papel_de_imagem():
    for arq in (WEB / "template.html", WEB / "tactics.html"):
        for tag in re.findall(r"<canvas[^>]*>", le_fonte(arq)):
            if "aria-label" in tag:
                assert 'role="img"' in tag, (arq.name, tag)


def test_paginas_tem_favicon_e_open_graph():
    from scripts.build_site import build_index
    from scripts.build_tactics_page import build_html as prancheta
    from scripts.meta_da_pagina import FAVICON
    landing = build_index([], "https://github.com/pedroppansani/parser-replay-cs2", [], numeros=None, imagem=None)
    for html in (landing, prancheta("de_mirage", site="https://pedroppansani.github.io/parser-replay-cs2/")):
        assert 'rel="icon"' in html and "og:title" in html and "og:description" in html
        assert 'property="og:image" content="https://pedroppansani.github.io/parser-replay-cs2/og/landing.png"' in html
    assert FAVICON.startswith("data:image/svg+xml,")


sync_api = pytest.importorskip("playwright.sync_api")

from tests.test_annotations_browser import abre, contexto, navegador, partida  # noqa: E402,F401  (fixtures)


def test_abas_andam_pelas_setas_e_so_a_ativa_entra_no_tab(contexto, partida):
    # design-B1: o Resumo é a primeira aba e a aberta por padrão (antes era o Replay); o comportamento
    # testado é o mesmo -- tabindex móvel, setas, End e volta ao começo.
    pg = contexto.new_page()
    pg.goto(partida["html"].as_uri())          # sem `abre`: ele já clica no Replay, e aqui vale o estado inicial
    tabs = pg.locator('[role="tab"]')
    assert [tabs.nth(i).get_attribute("tabindex") for i in range(tabs.count())] == ["0"] + ["-1"] * (tabs.count() - 1)
    tabs.first.focus()
    assert pg.evaluate("() => document.activeElement.dataset.tab") == "insights"
    pg.keyboard.press("ArrowRight")
    assert pg.evaluate("() => document.activeElement.dataset.tab") == "replay"
    assert pg.get_attribute('[data-tab="replay"]', "aria-selected") == "true"
    assert not pg.is_hidden('[data-panel="replay"]')
    pg.keyboard.press("End")
    assert pg.evaluate("() => document.activeElement.dataset.tab") == "estilos"
    pg.keyboard.press("ArrowRight")
    assert pg.evaluate("() => document.activeElement.dataset.tab") == "insights"
    pg.keyboard.press("Home")
    assert pg.evaluate("() => document.activeElement.dataset.tab") == "insights"
    pg.close()


def test_todo_json_injetado_nas_paginas_e_compacto():
    """Auditoria 5.5: nenhum build injeta JSON indentado."""
    for arq in ("build_web_page.py", "build_tactics_page.py", "build_site.py"):
        assert "compacto=False" not in (RAIZ / "scripts" / arq).read_text(encoding="utf-8"), arq
