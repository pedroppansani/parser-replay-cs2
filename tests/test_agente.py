"""O agente da landing (entrega-v2-goatdemo §6, decisão 48): os .js batem com o manifesto (sha256), o gerador
nunca é importado, e no navegador só o agente sorteado é baixado (N2) e sem JS aparece o quadro fixo do TR (N6)."""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
WEB = RAIZ / "dashboard" / "web"
MANIFESTO = json.loads((WEB / "agentes.manifesto.json").read_text(encoding="utf-8"))


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


@pytest.mark.parametrize("lado", ["tr", "ct"])
def test_os_js_e_os_quadros_batem_com_o_manifesto(lado):
    a = MANIFESTO["agentes"][lado]
    assert _sha(WEB / a["arquivo"]) == a["sha256"]
    assert _sha(WEB / a["quadro_fixo"]) == a["quadro_fixo_sha256"]
    # o nome dentro do arquivo é o que o tocador procura (agente.js: CHAVE)
    assert f'(window.AGENTES=window.AGENTES||{{}})["{a["nome_no_arquivo"]}"]=' in (WEB / a["arquivo"]).read_text(encoding="utf-8")


def test_o_corte_de_privacidade_e_o_do_plano():
    assert MANIFESTO["agentes"]["tr"]["corte_de_privacidade_y"] == 590
    assert MANIFESTO["agentes"]["ct"]["corte_de_privacidade_y"] == 545
    gerador = (RAIZ / "scripts" / "converte_agente.py").read_text(encoding="utf-8")
    assert 'CORTE_MAXIMO_Y = {"tr": 590, "ct": 545}' in gerador


def test_nenhum_teste_importa_o_gerador_do_agente():
    """converte_agente importa onnxruntime, cv2 e rembg (fora do requirements): importá-lo quebraria o CI."""
    padrao = re.compile(r"^\s*(from|import)\s+(scripts\.)?converte_agente\b|import_module\([^)]*converte_agente", re.M)
    achados = [t.name for t in (RAIZ / "tests").glob("*.py") if padrao.search(t.read_text(encoding="utf-8"))]
    assert not achados, achados
    build = (RAIZ / "scripts" / "build_site.py").read_text(encoding="utf-8")
    assert "converte_agente" not in build


sync_api = pytest.importorskip("playwright.sync_api")

from tests.test_tactics_browser import navegador  # noqa: E402,F401  (fixture)


@pytest.fixture(scope="module")
def site(tmp_path_factory):
    """A landing gerada com o agente/ ao lado, como no site."""
    from scripts.build_site import build_index, copia_agente
    pasta = tmp_path_factory.mktemp("landing")
    copia_agente(pasta)
    (pasta / "index.html").write_text(build_index([], "https://example.invalid/repo", [], numeros=None), encoding="utf-8")
    return pasta / "index.html"


@pytest.mark.parametrize("lado", ["tr", "ct"])
def test_so_o_agente_sorteado_e_baixado_e_toca(navegador, site, lado):
    ctx = navegador.new_context(viewport={"width": 375, "height": 800})
    pg = ctx.new_page()
    pedidos, erros = [], []
    pg.on("request", lambda r: pedidos.append(r.url))
    pg.on("pageerror", lambda e: erros.append(str(e)))
    try:
        pg.goto(site.as_uri() + f"?agente={lado}")
        pg.wait_for_function("() => document.getElementById('agente').classList.contains('pronto')", timeout=10000)
        agentes = [u.rsplit("/", 1)[-1] for u in pedidos if "/agente/" in u]
        assert agentes == [f"agente-{lado}.js"]
        assert pg.get_attribute("#agente", "data-lado") == lado
        assert pg.get_attribute("#agente", "aria-label") == f"Agente {lado.upper()} com fuzil"
        assert erros == []
    finally:
        ctx.close()


def test_sem_javascript_aparece_o_quadro_fixo_do_tr(navegador, site):
    ctx = navegador.new_context(viewport={"width": 375, "height": 800}, java_script_enabled=False)
    pg = ctx.new_page()
    pedidos = []
    pg.on("request", lambda r: pedidos.append(r.url))
    try:
        pg.goto(site.as_uri() + "?agente=ct")
        assert pg.get_attribute("#agente", "aria-label") == "Agente TR com fuzil"
        assert pg.is_visible("#agente .q-tr") and not pg.is_visible("#agente .q-ct")
        caixa = pg.locator("#agente").bounding_box()
        assert caixa["width"] > 100 and abs(caixa["width"] / caixa["height"] - 251 / 264) < 0.02
        assert not [u for u in pedidos if "/agente/" in u]
    finally:
        ctx.close()
