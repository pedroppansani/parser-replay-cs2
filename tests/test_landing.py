"""A landing: o topo diz o que é o projeto, cita três números que vêm de
numeros_citaveis.json e dá três caminhos (uma partida, a prancheta, o GitHub)."""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from scripts.build_site import build_index, match_summary, partida_de_exemplo
from scripts.numeros_citaveis import SAIDA, blocos_de_texto, tres_numeros

RAIZ = Path(__file__).resolve().parent.parent
REPO = "https://example.invalid/repo"


def _partidas() -> list[dict]:
    ids = sorted(d.name for d in (RAIZ / "data" / "processed").glob("match_*"))[:12]
    out = [m for m in (match_summary(i) for i in ids) if m]
    if not out:
        pytest.skip("sem partidas processadas")
    return out


def _pranchetas(partidas: list[dict]) -> list[dict]:
    return [{"mapa": m, "file": f"prancheta_{m}.html", "label": m} for m in sorted({p["map"] for p in partidas})]


@pytest.fixture(scope="module")
def landing():
    partidas = _partidas()
    numeros = json.loads(SAIDA.read_text(encoding="utf-8"))
    return partidas, numeros, build_index(partidas, REPO, _pranchetas(partidas), numeros=numeros, imagem="replay.png")


def test_os_tres_numeros_do_topo_vem_do_json(landing):
    _, numeros, html = landing
    bloco = html[html.index('id="tres-numeros"'):html.index('id="filtro"')]
    for n in tres_numeros(numeros):
        assert f"<b>{n['valor']}</b>" in bloco, n["valor"]
        assert n["rotulo"] in bloco
    assert bloco.count('class="num"') == 3
    assert blocos_de_texto(numeros)["corpus"] in html


def test_o_topo_nao_tem_numero_escrito_a_mao():
    """No código da landing, fora do que vem do JSON, não há número de corpus."""
    fonte = (RAIZ / "scripts" / "build_site.py").read_text(encoding="utf-8")
    cabecalho = fonte[fonte.index('<header class="hero">'):fonte.index('<div class="grid" id="partidas">')]
    assert not re.search(r"\b\d+ (partidas|mapas|jogador|testes|times)\b", cabecalho)
    assert not re.search(r"\b\d+ de \d+\b|\b0,\d{2,3}\b", cabecalho)


def test_os_tres_botoes_existem_e_os_links_resolvem(landing):
    partidas, _, html = landing
    hrefs = dict(re.findall(r'id="(btn-[a-z]+)" href="([^"]*)"', html))
    assert set(hrefs) == {"btn-partida", "btn-prancheta", "btn-github"}
    assert hrefs["btn-partida"] in {m["file"] for m in partidas}
    assert hrefs["btn-prancheta"] in {p["file"] for p in _pranchetas(partidas)}
    assert hrefs["btn-github"] == REPO
    # e todo card aponta para uma partida da lista
    assert set(re.findall(r'class="mcard" data-mapa="[^"]*" href="([^"]*)"', html)) == {m["file"] for m in partidas}


def test_a_partida_de_exemplo_segue_o_criterio_declarado():
    base = {"has_radar": True, "tem_round_decisivo": True, "origem": "profissional", "rounds": 24}
    larga = {**base, "id": "match_a", "score_a": 13, "score_b": 3}
    apertada = {**base, "id": "match_b", "score_a": 13, "score_b": 11}
    faceit = {**base, "id": "match_c", "score_a": 13, "score_b": 12, "origem": "faceit"}
    sem_decisivo = {**base, "id": "match_d", "score_a": 13, "score_b": 12, "tem_round_decisivo": False}
    assert partida_de_exemplo([larga, apertada, faceit, sem_decisivo])["id"] == "match_b"
    assert partida_de_exemplo([faceit])["id"] == "match_c"            # sem profissional: a primeira com radar
    assert partida_de_exemplo([]) is None


sync_api = pytest.importorskip("playwright.sync_api")

from tests.test_tactics_browser import navegador  # noqa: E402,F401  (fixture)


def test_landing_no_celular_nao_rola_na_horizontal_e_o_filtro_funciona(navegador, landing, tmp_path):
    partidas, _, html = landing
    arq = tmp_path / "index.html"
    arq.write_text(html, encoding="utf-8")
    ctx = navegador.new_context(viewport={"width": 390, "height": 844}, is_mobile=True, device_scale_factor=2)
    pg = ctx.new_page()
    erros = []
    pg.on("pageerror", lambda e: erros.append(str(e)))
    pg.goto(arq.as_uri())
    assert pg.evaluate("() => document.documentElement.scrollWidth") <= 390
    mapa = partidas[0]["map"]
    pg.click(f'#filtro button[data-filtro="{mapa}"]')
    visiveis = pg.eval_on_selector_all("#partidas .mcard", "els => els.filter(e => !e.hidden).map(e => e.dataset.mapa)")
    assert visiveis and set(visiveis) == {mapa}
    pg.click('#filtro button[data-filtro=""]')
    assert pg.locator("#partidas .mcard:not([hidden])").count() == len(partidas)
    assert erros == []
    ctx.close()
