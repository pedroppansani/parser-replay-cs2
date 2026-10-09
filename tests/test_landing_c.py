"""A landing da direção "Sala de demo" (design-C, entrega-sala-de-demo §7.1): topo em linguagem comum, três
números logo depois do texto, imagem com tamanho declarado, grade com filtros de origem e mapa, cards com os
nomes dos lados, "venceu" e a linha do decisor, e o cabeçalho da partida vindo pronto do build (CLS)."""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from scripts.build_site import (FRASE_DO_TOPO, TITULO_DA_PAGINA, TITULO_DO_TOPO, build_index, match_summary,
                                ordem_da_grade)
from scripts.numeros_citaveis import SAIDA

RAIZ = Path(__file__).resolve().parent.parent
REPO = "https://github.com/pedroppansani/parser-replay-cs2"


@pytest.fixture(scope="module")
def partidas():
    ids = sorted(d.name for d in (RAIZ / "data" / "processed").glob("match_*"))
    out = [m for m in (match_summary(i) for i in ids) if m]
    if not out:
        pytest.skip("sem partidas processadas")
    return out


@pytest.fixture(scope="module")
def landing(partidas):
    numeros = json.loads(SAIDA.read_text(encoding="utf-8"))
    pr = [{"mapa": m, "file": f"prancheta_{m}.html", "label": m} for m in sorted({p["map"] for p in partidas})]
    return build_index(partidas, REPO, pr, numeros=numeros, imagem="replay.webp", imagem_tamanho=(1156, 588),
                       legenda="Replay do round 6 de MOUZ × Falcons, em Dust II.")


def test_titulo_descricao_e_open_graph(landing):
    assert f"<title>{TITULO_DA_PAGINA}</title>" in landing
    assert f'<meta name="description" content="{FRASE_DO_TOPO}">' in landing
    for prop in ("og:title", "og:description", "og:image"):
        assert re.search(rf'<meta property="{prop}" content="[^"]+">', landing), prop
    assert f">{TITULO_DO_TOPO}</h1>" in landing and "Uma partida,<br>round a round" not in landing


def test_ordem_no_html_e_texto_numeros_imagem(landing):
    i_texto, i_nums, i_img = landing.index('class="heroi-texto"'), landing.index('id="tres-numeros"'), landing.index('class="figura"')
    assert i_texto < i_nums < i_img
    img = re.search(r"<img [^>]*>", landing).group(0)
    assert 'width="1156"' in img and 'height="588"' in img and 'loading="lazy"' in img
    assert "<figcaption>Replay do round 6" in landing


def test_os_rotulos_curtos_dos_tres_numeros_sao_os_do_documento(landing):
    for r in ("placares iguais aos oficiais", "de erro médio no rating", "de acerto no botão do arremesso"):
        assert r in landing
    readme = (RAIZ / "README.md").read_text(encoding="utf-8")
    for r in ("placares iguais aos oficiais", "de erro médio no rating", "de acerto no botão do arremesso"):
        assert r in readme                                                 # README e landing iguais


def test_cards_tem_os_nomes_dos_lados_venceu_e_a_linha_do_decisor(landing, partidas):
    assert not re.search(r"\bTime [AB]\b", re.sub(r"<[^>]+>", " ", landing))
    assert "impôs" not in landing and "de cegueira" not in landing       # a frase de cegueira saiu (§10)
    cards = re.findall(r'<a class="mcard cp".*?</a>', landing, re.S)
    assert len(cards) == len(partidas)
    for c in cards:
        assert c.count('class="tag-venceu"') <= 1
        assert re.search(r'class="cp-frase">(Decidida no round \d+|Nenhum round decidiu sozinho)', c), c[:300]


def test_profissionais_primeiro_e_as_mais_recentes_antes(partidas):
    grade = ordem_da_grade(partidas)
    origens = [m["origem"] for m in grade]
    assert origens == sorted(origens, key=lambda o: o != "profissional")
    pros = [m["data"] for m in grade if m["origem"] == "profissional"]
    assert pros == sorted(pros, reverse=True)
    assert ordem_da_grade(list(reversed(partidas))) == grade               # estável


def test_o_cabecalho_da_partida_vem_pronto_no_html():
    """Sem esperar o JS: placar, decisor e migalhas já estão no HTML (CLS da partida < 0,1 no A12)."""
    from scripts.build_web_page import build_html
    html = build_html("match_02", site={"matches": [], "current": "match_02", "repo": REPO,
                                         "jogadores": {"texto": "Jogadores no corpus", "aviso": "aviso"}})
    h1 = re.search(r'<h1 class="placar" id="titulo-partida">(.*?)</h1>', html, re.S).group(1)
    assert 'class="tag-venceu">venceu<' in h1 and "começou CT" in h1 and "começou TR" in h1
    assert re.search(r'<p class="decisor" id="decisor">Decidida no round \d+ · MVP ', html)
    assert '<a id="c-partidas" href="index.html">Partidas</a>' in html
    assert '<div class="demobar" id="demobar">' in html                   # visível desde o começo no site
    solta = build_html("match_02")
    assert "c-partidas" not in solta and '<div class="demobar" id="demobar" hidden>' in solta


sync_api = pytest.importorskip("playwright.sync_api")

from tests.test_tactics_browser import navegador  # noqa: E402,F401  (fixture)


def _abre(navegador, html, tmp_path, w, h):
    arq = tmp_path / "index.html"
    arq.write_text(html, encoding="utf-8")
    ctx = navegador.new_context(viewport={"width": w, "height": h})
    pg = ctx.new_page()
    erros = []
    pg.on("pageerror", lambda e: erros.append(str(e)))
    pg.goto(arq.as_uri())
    pg._erros = erros
    return ctx, pg


def test_na_dobra_de_375x667_aparecem_o_h1_e_o_ver_uma_partida(navegador, landing, tmp_path):
    ctx, pg = _abre(navegador, landing, tmp_path, 375, 667)
    try:
        r = pg.evaluate("""() => [document.querySelector('h1').getBoundingClientRect().bottom,
                                  document.getElementById('btn-partida').getBoundingClientRect().bottom, innerHeight]""")
        assert r[0] <= r[2] and r[1] <= r[2], r
        assert pg.evaluate("() => document.documentElement.scrollWidth") <= 375
    finally:
        ctx.close()


def test_filtros_de_origem_e_mapa_e_o_vazio(navegador, landing, partidas, tmp_path):
    ctx, pg = _abre(navegador, landing, tmp_path, 1300, 900)
    try:
        pros = sum(1 for m in partidas if m["origem"] == "profissional")
        visiveis = lambda: pg.eval_on_selector_all("#partidas .mcard", "els => els.filter(e => !e.hidden).map(e => e.dataset.origem)")  # noqa: E731
        assert set(visiveis()) == {"profissional"} and len(visiveis()) == pros       # padrão: profissionais
        assert pg.inner_text("#grade-contagem") == str(pros)
        pg.click('#filtro-origem button[data-valor="faceit"]')
        assert set(visiveis()) == {"faceit"}
        # um mapa sem partida da FACEIT dá o vazio, e o botão do vazio volta para todos os mapas
        mapas_faceit = {m["map"] for m in partidas if m["origem"] == "faceit"}
        so_pro = sorted({m["map"] for m in partidas} - mapas_faceit)
        if so_pro:
            pg.click(f'#filtro button[data-valor="{so_pro[0]}"]')
            assert visiveis() == [] and pg.is_visible("#vazio")
            pg.click("#mostra-todos")
            assert set(visiveis()) == {"faceit"} and pg.is_hidden("#vazio")
        pg.click('#filtro-origem button[data-valor=""]')
        assert len(visiveis()) == len(partidas)
        assert pg._erros == []
    finally:
        ctx.close()
