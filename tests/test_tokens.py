"""Os tokens da direção visual (decisões 44 e 48): uma fonte só para cor e fonte, por tema."""
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


def test_tokens_css_tem_os_valores_do_prototipo_v2_no_claro_e_os_de_hoje_no_escuro():
    """v2-1 (decisão 48): o claro e a forma são os do protótipo v2; o escuro é o da Sala de demo (as páginas
    ficam nele e não mudam de cor) e o canvas lê os *-mapa com os valores escuros de hoje."""
    proto_v2 = RAIZ / "notas" / "design" / "prototipo-v2" / "tokens.css"
    claro_do_design, claro = le_tokens(proto_v2, "claro"), le_tokens(tema="claro")
    # a única diferença é deliberada: o texto do mapa fica no #e8edf2 de hoje (plano v2-0 §4.3), não no #ffffff
    assert {k for k, v in claro_do_design.items() if claro.get(k) != v} == {"tinta-mapa"}
    declaracoes = lambda t: dict(re.findall(r"(--[a-z0-9-]+):\s*([^;]+);", t))  # noqa: E731
    do_design, do_projeto = declaracoes(proto_v2.read_text(encoding="utf-8")), declaracoes(TOKENS.read_text(encoding="utf-8"))
    for forma in ("--f-texto", "--f-num", "--r-card", "--r-ctl", "--r-cab", "--r-moldura", "--r-mapa", "--curva", "--nav-h"):
        assert do_projeto[forma] == do_design[forma], forma
    sala = (RAIZ / "notas" / "design" / "prototipo" / "tokens.css").read_text(encoding="utf-8")
    de_hoje = dict(re.findall(r"^\s*--([a-z0-9-]+):\s*(#[0-9a-f]{6});", sala, re.M))
    escuro = le_tokens(tema="escuro")
    assert {k: escuro[k] for k in de_hoje} == de_hoje


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
    """As duas famílias (Geist e Geist Mono) vêm do próprio site, em fontes/; nenhum pedido ao Google Fonts (48)."""
    from scripts.build_jogadores import build_html as jogadores
    from scripts.build_tactics_page import build_html as prancheta
    from scripts.build_web_page import build_html as partida
    from scripts.design_head import FONTES, FONTES_DIR
    paginas = {"partida": partida("match_02"), "prancheta": prancheta("de_mirage"), "jogadores": jogadores()}
    from scripts.build_site import build_index
    paginas["landing"] = build_index([], "https://github.com/pedroppansani/parser-replay-cs2", [], numeros=None, imagem=None)
    for nome, html in paginas.items():
        assert "__TOKENS__" not in html and "__FONTES__" not in html, nome
        for velha in ("Bricolage", "Figtree", "DM Mono", "DM+Mono", "Archivo", "JetBrains", "fonts.googleapis", "fonts.gstatic"):
            assert velha not in html, (nome, velha)
        baixadas = re.findall(r'font-family: "([^"]+)"; src: url\(fontes/([^)]+)\)', html)
        assert baixadas == [(f, a) for f, a in FONTES], nome
        assert html.count("src: url(") == 2, nome
        # v2-4: landing, partida e jogadores no claro; a prancheta segue no escuro de hoje até a v2-5
        tema = "escuro" if nome == "prancheta" else "claro"
        assert f'<html lang="pt-BR" data-tema="{tema}">' in html and "--fundo: #0b0f14" in html, nome
        assert "Geist Fallback" in html and "Geist Mono Fallback" in html, nome
    assert {f for f, _ in FONTES} == {"Geist", "Geist Mono"}
    assert all((FONTES_DIR / a).stat().st_size > 0 for _, a in FONTES) and (FONTES_DIR / "OFL.txt").exists()


def test_o_favicon_e_a_cabra_c_da_marca_em_0a0a0a():
    # v2-2 (decisão 48, entrega-v2-goatdemo §1): o favicon é a cabra C da marca em #0a0a0a, sem cor de lado
    from urllib.parse import unquote

    from scripts.meta_da_pagina import FAVICON
    svg = unquote(FAVICON.removeprefix("data:image/svg+xml,"))
    cabra = (WEB / "marca" / "cabra-c.svg").read_text(encoding="utf-8")
    assert svg == " ".join(cabra.replace("currentColor", "#0a0a0a").split())
    assert 'fill="#0a0a0a"' in svg and "currentColor" not in svg
    tk = le_tokens()
    for token in ("ct", "tr"):
        assert tk[token] not in svg, token


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
