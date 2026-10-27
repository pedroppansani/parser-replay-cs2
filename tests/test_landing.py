"""A landing: o topo diz o que é o projeto, cita três números que vêm de
numeros_citaveis.json e dá duas ações (v2-3, entrega-v2-goatdemo §5.2): "Explorar partidas", que desce para a
lista (a partida de exemplo é o primeiro card), e "Adicionar demo", que abre o diálogo com o link de Issues; o
GitHub fica no rodapé."""
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
        # design-C: o valor ganhou a classe do número (mono só em número) e cada item é um par dt/dd
        assert f'<b class="num">{n['valor']}</b>' in bloco, n["valor"]
        assert n["rotulo"] in bloco
    assert bloco.count('class="num-item"') == 3
    assert blocos_de_texto(numeros)["corpus"] in html


def test_o_topo_nao_tem_numero_escrito_a_mao():
    """No código da landing, fora do que vem do JSON, não há número de corpus."""
    fonte = (RAIZ / "scripts" / "build_site.py").read_text(encoding="utf-8")
    cabecalho = fonte[fonte.index('<section class="heroi"'):fonte.index('<div class="grid" id="partidas">')]   # design-C: novo topo
    assert not re.search(r"\b\d+ (partidas|mapas|jogador|testes|times)\b", cabecalho)
    assert not re.search(r"\b\d+ de \d+\b|\b0,\d{2,3}\b", cabecalho)


def test_as_duas_acoes_do_topo_e_os_links_resolvem(landing):
    partidas, _, html = landing
    hrefs = dict(re.findall(r'id="(btn-[a-z]+)" href="([^"]*)"', html))
    assert hrefs == {"btn-explorar": "#partidas"} and 'id="partidas"' in html
    assert re.search(r'<button class="btn" type="button" id="btn-demo" data-abre-demo>', html)
    assert f'id="link-issue" href="{REPO}/issues"' in html and f'id="link-github" href="{REPO}"' in html
    # e todo card aponta para uma partida da lista; o primeiro é a partida de exemplo, em destaque
    cards = re.findall(r'class="mcard cp" data-mapa="[^"]*" data-origem="[^"]*" href="([^"]*)"', html)
    assert set(cards) == {m["file"] for m in partidas}
    assert cards[0] == partida_de_exemplo(partidas)["file"] and html.count('data-exemplo="1"') == 1


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
    # design-C: a grade abre só com as profissionais; "Todas" mostra todas, e o filtro de mapa continua igual
    pg.click('#filtro-origem button[data-valor=""]')
    mapa = partidas[0]["map"]
    pg.click(f'#filtro button[data-valor="{mapa}"]')
    visiveis = pg.eval_on_selector_all("#partidas .mcard", "els => els.filter(e => !e.hidden).map(e => e.dataset.mapa)")
    assert visiveis and set(visiveis) == {mapa}
    pg.click('#filtro button[data-valor=""]')
    assert pg.locator("#partidas .mcard:not([hidden])").count() == len(partidas)
    assert erros == []
    ctx.close()
