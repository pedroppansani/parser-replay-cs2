"""Reescrever R1 (decisão 56): a navbar com Reescrever, a prancheta livre como bloco da landing e a página de escolha."""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

sync_api = pytest.importorskip("playwright.sync_api")

from scripts.build_site import build_index, indice_de_sugeridos, match_summary  # noqa: E402
from tests.test_csp import MAPA, _paginas  # noqa: E402
from tests.test_tactics_browser import navegador  # noqa: E402,F401  (fixture)

RAIZ = Path(__file__).resolve().parent.parent
LINKS = ["Partidas", "Jogadores", "Reescrever"]


@pytest.fixture(scope="module")
def partidas():
    ids = sorted(d.name for d in (RAIZ / "data" / "processed").glob("match_*"))
    ms = [m for m in (match_summary(i) for i in ids) if m]
    if len(ms) < 6:
        pytest.skip("sem data/processed")
    return ms


@pytest.fixture(scope="module")
def paginas_html(partidas, tmp_path_factory):
    from scripts.build_reescrever import build_html as reescrever
    pasta = tmp_path_factory.mktemp("r1")
    paginas = _paginas()
    mapas = ["de_mirage", "de_nuke", "de_dust2"]
    numeros = json.loads((RAIZ / "data" / "processed" / "numeros_citaveis.json").read_text(encoding="utf-8"))
    paginas["landing"] = build_index(partidas[:6], "https://example.invalid/repo",
                                     [{"mapa": m, "file": f"prancheta_{m}.html", "label": m[3:].capitalize()} for m in mapas],
                                     numeros=numeros, imagem="replay.png")
    paginas["reescrever"] = reescrever(partidas, indice_de_sugeridos(partidas))
    for nome, html in paginas.items():
        (pasta / f"{nome}.html").write_text(html, encoding="utf-8")
    return pasta, paginas


def _nav(html):
    nav = re.search(r'<nav class="site-nav".*?</nav>', html, re.S).group(0)
    return re.findall(r'<a href="([^"]+)"( aria-current="page")?>([^<]+)</a>', nav)


def test_a_navbar_de_toda_pagina_tem_partidas_jogadores_e_reescrever_sem_prancheta(paginas_html):
    _, paginas = paginas_html
    esperado_atual = {"landing": "Partidas", "jogadores": "Jogadores", "reescrever": "Reescrever", "partida": None, "prancheta": None}
    for nome, atual in esperado_atual.items():
        links = _nav(paginas[nome])
        assert [t for _, _, t in links] == LINKS, nome
        assert [t for _, c, t in links if c] == ([atual] if atual else []), nome
        assert dict((t, h) for h, _, t in links)["Reescrever"] == "reescrever.html", nome


def test_o_bloco_da_prancheta_livre_na_landing_troca_o_mapa_do_botao_e_o_endereco_continua(navegador, paginas_html):
    pasta, _ = paginas_html
    ctx = navegador.new_context(viewport={"width": 1440, "height": 900})
    pg = ctx.new_page()
    try:
        pg.goto((pasta / "landing.html").as_uri())
        assert pg.inner_text("#h-tatica") == "Monte uma tática do zero"
        assert pg.inner_text("#tatica-abrir") == "Abrir a prancheta da Mirage"                   # começa na Mirage
        assert pg.get_attribute("#tatica-abrir", "href") == "prancheta_de_mirage.html"
        assert pg.locator("#tatica-mapas .chip").count() == 3
        pg.locator("#tatica-mapas .chip", has_text="Nuke").click()
        assert pg.inner_text("#tatica-abrir") == "Abrir a prancheta da Nuke"
        assert pg.get_attribute("#tatica-abrir", "href") == "prancheta_de_nuke.html"
        assert "prancheta_de_nuke.html" in pg.inner_text(".tatica-endereco")                    # o endereço de sempre continua valendo
        assert pg.get_attribute('#tatica-mapas .chip:has-text("Nuke")', "aria-pressed") == "true"
        assert pg.get_attribute('#tatica-mapas .chip:has-text("Mirage")', "aria-pressed") == "false"
        from scripts.build_site import TEXTOS_DA_LANDING
        assert pg.inner_text("#tatica-abrir") == TEXTOS_DA_LANDING["tatica_abrir"].format(mapa="Nuke")   # a frase vem do Python
        assert pg.get_attribute(".tatica-mini", "data-tema") == "violeta"                       # a miniatura no violeta da prancheta
    finally:
        ctx.close()


def test_a_pagina_de_escolha_mostra_os_sugeridos_com_motivo_e_leva_ao_replay_no_round(navegador, paginas_html, partidas):
    pasta, _ = paginas_html
    arquivos = {m["file"] for m in partidas}
    ctx = navegador.new_context(viewport={"width": 1440, "height": 900})
    pg = ctx.new_page(); erros = []
    pg.on("pageerror", lambda e: erros.append(str(e)))
    try:
        pg.goto((pasta / "reescrever.html").as_uri())
        assert pg.inner_text("h1") == "Reescrever um round"
        assert "Não é uma previsão." in pg.inner_text("#aviso")                                 # a frase fixa
        n = pg.locator("#sugeridos .sug").count()
        assert 1 <= n <= 12
        hrefs = [pg.locator("#sugeridos .sug").nth(i).locator("a").get_attribute("href").split("#")[0] for i in range(n)]
        assert len(set(hrefs)) == n                                                             # uma linha por partida
        motivos = {pg.locator("#sugeridos .sug").nth(i).locator(".motivos .rot").first.inner_text() for i in range(n)}
        assert len(motivos) >= 2, motivos                                                       # decisivo, momento e erro se misturam
        for i in range(n):
            linha = pg.locator("#sugeridos .sug").nth(i)
            assert linha.locator(".motivos li").count() >= 1                                    # o motivo escrito
            href = linha.locator("a").get_attribute("href")
            arq, _, resto = href.partition("#")
            assert arq in arquivos and re.fullmatch(r"replay\?round=\d+(&t=[\d.]+)?", resto), href
        assert pg.evaluate("document.documentElement.scrollWidth - innerWidth") == 0
        assert not re.search(r"Time [AB]", pg.inner_text("body"))                            # nenhum rótulo interno na tela
        # a ordem: a partida de exemplo, depois as profissionais, depois as da FACEIT
        from scripts.build_site import partida_de_exemplo
        exemplo = partida_de_exemplo(partidas)
        origem = {m["file"]: m.get("origem") for m in partidas}
        arqs = [h.split("#")[0] for h in hrefs]
        if exemplo and exemplo["file"] in arqs:
            assert arqs[0] == exemplo["file"]
        grupos = [0 if a == (exemplo or {}).get("file") else 1 if origem[a] == "profissional" else 2 for a in arqs]
        assert grupos == sorted(grupos), grupos
        assert erros == []
    finally:
        ctx.close()


def test_a_busca_filtra_sem_acento_mostra_o_vazio_e_abre_a_faixa_de_rounds(navegador, paginas_html, partidas):
    pasta, _ = paginas_html
    ctx = navegador.new_context(viewport={"width": 375, "height": 812})
    pg = ctx.new_page(); erros = []
    pg.on("pageerror", lambda e: erros.append(str(e)))
    try:
        pg.goto((pasta / "reescrever.html").as_uri())
        assert pg.locator("#resultados .partida-btn").count() == len(partidas)                # sem busca: todas
        pg.fill("#busca", "xyzxyz")
        assert pg.locator("#resultados .partida-btn").count() == 0
        assert pg.is_visible("#vazio") and "xyzxyz" in pg.inner_text("#vazio-texto")
        assert pg.inner_text("#contagem") == "0 partida(s)"
        pg.click("#limpa")
        assert pg.input_value("#busca") == "" and pg.locator("#resultados .partida-btn").count() == len(partidas)
        alvo = partidas[0]
        pg.fill("#busca", alvo["map_label"].upper())                                            # mapa, em maiúsculas
        assert pg.locator("#resultados .partida-btn").count() >= 1
        pg.fill("#busca", alvo["lados"]["A"]["nome"][:5])
        assert pg.locator("#resultados .partida-btn").count() >= 1
        pg.locator("#resultados .partida-btn").first.focus()
        pg.keyboard.press("Enter")                                                              # pelo teclado: o foco vai aos rounds
        assert pg.evaluate("document.activeElement.classList.contains('chip')")
        assert pg.get_attribute("#resultados .partida-btn >> nth=0", "aria-pressed") == "true"
        assert pg.is_visible("#faixa") and pg.locator("#faixa .chip").count() >= 10
        assert pg.is_hidden("#abrir")                                                           # só aparece depois de escolher o round
        pg.locator("#faixa .chip").nth(4).click()
        assert pg.is_visible("#abrir") and pg.inner_text("#abrir") == "Reescrever o round 5"
        assert re.fullmatch(r"match_\d+\.html#replay\?round=5", pg.get_attribute("#abrir", "href"))
        pg.fill("#busca", "xyzxyz")                                                             # a partida escolhida saiu do filtro
        assert pg.is_hidden("#faixa") and pg.is_hidden("#abrir")
        assert pg.evaluate("document.documentElement.scrollWidth - innerWidth") == 0
        assert erros == []
    finally:
        ctx.close()


def test_o_teclado_faz_o_caminho_todo_da_busca_ao_botao_reescrever_o_round(navegador, paginas_html, partidas):
    pasta, _ = paginas_html
    ctx = navegador.new_context(viewport={"width": 1440, "height": 900})
    pg = ctx.new_page()
    foco = "() => { const a = document.activeElement; return [a.tagName, a.id, a.className, a.textContent.slice(0, 40)]; }"
    try:
        pg.goto((pasta / "reescrever.html").as_uri())
        pg.focus("#busca")
        pg.keyboard.type(partidas[0]["lados"]["A"]["nome"][:5])
        assert pg.locator("#resultados .partida-btn").count() >= 1
        pg.keyboard.press("Tab")                                                         # do campo à primeira partida (o "Limpar" está escondido)
        assert pg.evaluate(foco)[2] == "partida-btn"
        pg.keyboard.press("Enter")                                                       # escolher a partida leva o foco aos rounds
        assert pg.evaluate(foco)[2:4] == ["chip", "1"]
        n = pg.locator("#faixa .chip").count()
        pg.keyboard.press("End")
        assert pg.evaluate(foco)[3] == str(n)
        pg.keyboard.press("ArrowLeft")
        assert pg.evaluate(foco)[3] == str(n - 1)
        pg.keyboard.press("Space")                                                       # escolher o round
        assert pg.is_visible("#abrir") and pg.inner_text("#abrir") == f"Reescrever o round {n - 1}"
        pg.keyboard.press("Tab")                                                         # a faixa é uma parada só: o próximo é o botão
        assert pg.evaluate(foco)[1] == "abrir"
        assert pg.get_attribute("#abrir", "href").endswith(f"#replay?round={n - 1}")
        assert pg.evaluate("document.activeElement.getBoundingClientRect().height") >= 44
    finally:
        ctx.close()


def test_a_biblioteca_e_a_prancheta_de_sempre_seguem_no_mesmo_endereco():
    assert MAPA and (RAIZ / "scripts" / "build_tactics_page.py").exists()
    from scripts.build_tactics_page import arquivo_da_pagina
    assert arquivo_da_pagina("de_mirage") == "prancheta_de_mirage.html"
