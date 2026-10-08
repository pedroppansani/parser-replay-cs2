"""Os tokens da direção "Sala de demo" (decisão 44): uma fonte só para cor e fonte (design-A)."""
from __future__ import annotations

import re
from pathlib import Path

import pytest

from metrics.paleta import le_tokens

RAIZ = Path(__file__).resolve().parent.parent
WEB = RAIZ / "dashboard" / "web"
TOKENS = WEB / "tokens.css"


def _css(arquivo: Path) -> str:
    """O CSS de um arquivo: ele todo, ou o que está dentro do <style> (HTML e landing)."""
    t = arquivo.read_text(encoding="utf-8")
    if arquivo.suffix == ".css":
        return t
    i = t.index("<style>")
    return t[i:t.index("</style>", i)]


FONTES_DO_CSS = [WEB / "template.html", WEB / "tactics.css", WEB / "annotations.css", WEB / "jogadores.html",
                 RAIZ / "scripts" / "build_site.py"]


def test_tokens_css_tem_os_mesmos_valores_do_prototipo_do_design():
    """O arquivo do projeto só acrescenta (--f-codigo); nenhum valor do design é alterado."""
    proto = (RAIZ / "notas" / "design" / "prototipo" / "tokens.css").read_text(encoding="utf-8")
    projeto = TOKENS.read_text(encoding="utf-8")
    declaracoes = lambda t: dict(re.findall(r"^\s*(--[a-z0-9-]+):\s*([^;]+);", t, re.M))  # noqa: E731
    do_design, do_projeto = declaracoes(proto), declaracoes(projeto)
    assert {k: v for k, v in do_projeto.items() if k in do_design} == do_design
    assert set(do_projeto) - set(do_design) == {"--f-codigo"}


@pytest.mark.parametrize("arquivo", FONTES_DO_CSS, ids=lambda a: a.name)
def test_nenhum_arquivo_define_cor_por_conta_propria(arquivo):
    css = _css(arquivo)
    assert not re.search(r"^\s*--[a-z0-9-]+\s*:\s*(#|rgb)", css, re.M), "só tokens.css define cor de variável"
    # nenhum hex nem rgba fixo; a exceção é o espectro do seletor de cor (função da ferramenta, não tema)
    sem_espectro = re.sub(r"\.anot-(sv|matiz)\s*\{.*?\}", "", css, flags=re.S) if arquivo.name == "annotations.css" else css
    sem_comentarios = re.sub(r"/\*.*?\*/", "", sem_espectro, flags=re.S)
    achados = re.findall(r"#[0-9a-fA-F]{3,8}\b|rgba?\([^)]*\)", sem_comentarios)
    assert not achados, achados[:5]


@pytest.mark.parametrize("hospedeira", [WEB / "template.html", WEB / "tactics.html", WEB / "jogadores.html", RAIZ / "scripts" / "build_site.py"],
                         ids=lambda a: a.name)
def test_toda_pagina_recebe_os_tokens_e_as_fontes_pelos_marcadores(hospedeira):
    texto = hospedeira.read_text(encoding="utf-8")
    assert texto.count("/*__TOKENS__*/") == 1 and texto.count("<!--__FONTES__-->") == 1


def test_nenhuma_variavel_antiga_sobrou():
    antigas = re.compile(r"var\(--(paper|paper-2|card|ink|ink-2|ink2|dim|line|line-2|aqua|dec|display|body|mono|shadow-1|shadow-2|ct-soft|t-soft)[,)]")
    for arquivo in FONTES_DO_CSS:
        achados = antigas.findall(_css(arquivo))
        assert not achados, (arquivo.name, achados[:5])


def test_paginas_geradas_nao_deixam_marcador_e_carregam_so_as_duas_familias():
    from scripts.build_jogadores import build_html as jogadores
    from scripts.build_tactics_page import build_html as prancheta
    from scripts.build_web_page import build_html as partida
    from scripts.design_head import FONTES_URL
    paginas = {"partida": partida("match_02"), "prancheta": prancheta("de_mirage"), "jogadores": jogadores()}
    from scripts.build_site import build_index
    paginas["landing"] = build_index([], "https://github.com/pedroppansani/parser-replay-cs2", [], numeros=None, imagem=None)
    for nome, html in paginas.items():
        assert "__TOKENS__" not in html and "__FONTES__" not in html, nome
        assert html.count(FONTES_URL) == 1, nome
        for velha in ("Bricolage", "Figtree", "DM Mono", "DM+Mono"):
            assert velha not in html, (nome, velha)
        assert "--fundo: #0b0f14" in html and "Archivo Fallback" in html, nome
    assert FONTES_URL.count("family=") == 2


def test_o_favicon_tem_as_duas_bolinhas_nas_cores_dos_tokens():
    from urllib.parse import unquote

    from scripts.meta_da_pagina import FAVICON
    tk = le_tokens()
    svg = unquote(FAVICON)
    for token in ("fundo", "ct", "tr"):
        assert tk[token] in svg, token


def test_as_cores_das_granadas_do_canvas_vem_dos_tokens(contexto, pagina):
    from tests.test_tactics_browser import abre, interno
    tk = le_tokens()
    pg = abre(contexto, pagina)
    cores = interno(pg, "MapCore.NADE_COLOR")
    assert cores == {"smoke": tk["smoke"], "molotov": tk["molotov"], "he": tk["he"], "flash": tk["flash"], "decoy": tk["apagado"]}
    pg.close()


pytest.importorskip("playwright.sync_api")
from tests.test_tactics_browser import contexto, navegador, pagina  # noqa: E402,F401


def test_a_peca_da_prancheta_tem_a_cor_do_lado_nos_tokens(contexto, pagina):
    """Lê o pixel do CENTRO de cada peça na tela: CT e TR saem nas cores dos tokens (e não pretas, como
    saíam quando o JS pedia a variável `--t`, que o design renomeou para `--tr`)."""
    import io

    from PIL import Image

    from tests.test_prancheta_tempo_browser import _tatica_no_tempo
    from tests.test_tactics_browser import abre, interno
    tk = le_tokens()
    pg = abre(contexto, pagina)
    _tatica_no_tempo(pg)                                         # uma peça TR em t = 0
    interno(pg, "(I.defineTempo(0), 0)")
    x, y = interno(pg, "I.quadroNoTempo(S.e3, 0, I.centro()).pecas.a.x"), interno(pg, "I.quadroNoTempo(S.e3, 0, I.centro()).pecas.a.y")
    px = interno(pg, f"I.jogoParaPixel({x}, {y})")
    caixa = pg.locator("#pr-mapa").bounding_box()
    w = interno(pg, "I.radar().width")
    pg.locator("#pr-mapa").scroll_into_view_if_needed()
    caixa = pg.locator("#pr-mapa").bounding_box()
    cx, cy = caixa["x"] + px[0] * caixa["width"] / w, caixa["y"] + px[1] * caixa["height"] / w
    img = Image.open(io.BytesIO(pg.screenshot())).convert("RGB")
    rgb = img.getpixel((round(cx), round(cy)))
    esperado = tuple(int(tk["tr"][i:i + 2], 16) for i in (1, 3, 5))
    assert rgb == esperado, (rgb, esperado)
    pg.close()
