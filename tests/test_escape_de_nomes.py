"""Nome de jogador é DADO, nunca marcação.

O template montava HTML por concatenação sem escapar nada, e o build injetava o
JSON dentro de <script> sem tratar `</`. Um nick como
`</script><img src=x onerror=...>` fechava o script e executava código.

A partida é a match_02 real com dois nicks trocados em todo o payload (o que o
parser gravaria se alguém jogasse com esses nomes).
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.json_em_script import js, texto_seguro

RAIZ = Path(__file__).resolve().parent.parent
PARTIDA = "match_02"                   # Mirage: tem prancheta para o "Tática deste instante"
# FACEIT e profissional: as frases geradas mudam com a partida, e cada uma
# exercita pontos diferentes da página
PARTIDAS = (PARTIDA, "match_23")
MAU_SCRIPT = '</script><img src=x onerror="window.__x=1">'
MAU_NEGRITO = "<b>negrito</b>"
BARRA = chr(92)


# ---------------------------------------------------------------------------
# A injeção de JSON em <script> (roda sempre)
# ---------------------------------------------------------------------------

def test_json_em_script_nao_deixa_fechar_o_script():
    saida = js({"nome": MAU_SCRIPT, "c": "<!--x", "l": chr(0x2028) + chr(0x2029)})
    assert "</script" not in saida and "<!--" not in saida
    assert chr(0x2028) not in saida and chr(0x2029) not in saida
    # e o valor continua o mesmo para quem lê
    assert json.loads(saida.replace("<" + BARRA + "!--", "<!--")) == \
        {"nome": MAU_SCRIPT, "c": "<!--x", "l": chr(0x2028) + chr(0x2029)}


def test_texto_seguro_serve_para_json_ja_serializado():
    bruto = json.dumps({"n": MAU_SCRIPT}, ensure_ascii=False)
    assert "</script" in bruto and "</script" not in texto_seguro(bruto)
    assert json.loads(texto_seguro(bruto)) == {"n": MAU_SCRIPT}


def test_os_dois_builds_usam_a_mesma_injecao():
    """Nenhum build serializa JSON para dentro de <script> por conta própria."""
    for nome in ("build_web_page.py", "build_tactics_page.py"):
        fonte = (RAIZ / "scripts" / nome).read_text(encoding="utf-8")
        assert "json_em_script" in fonte, nome
        injecoes = [l for l in fonte.splitlines() if ".replace(\"/*__" in l or "html.replace(\"/*__" in l]
        assert injecoes, nome
        for l in injecoes:
            assert "json.dumps(" not in l, f"{nome}: injeção sem a função segura: {l.strip()}"


def test_a_landing_escapa_os_nicks():
    from scripts.build_site import build_index
    m = {"file": "match_x.html", "map_label": "Mirage", "score_a": 13, "score_b": 9, "rounds": 22,
         "rosters": {"A": [MAU_SCRIPT, "ok"], "B": [MAU_NEGRITO]}, "mvp": MAU_NEGRITO, "extra": None,
         "has_radar": True}
    html = build_index([m], "https://example.invalid/repo")
    assert "<img src=x" not in html and MAU_NEGRITO not in html
    assert "&lt;b&gt;negrito&lt;/b&gt;" in html


# ---------------------------------------------------------------------------
# No navegador
# ---------------------------------------------------------------------------

sync_api = pytest.importorskip("playwright.sync_api")

from tests.test_tactics_browser import navegador  # noqa: E402,F401  (fixture)

INJETADOS = """() => ({
  x: window.__x,
  img: document.querySelectorAll('img[src="x"]').length,
  b: Array.from(document.querySelectorAll('b')).filter(e => e.textContent === 'negrito').length,
})"""


@pytest.fixture(scope="module")
def paginas(tmp_path_factory):
    from scripts.build_tactics_page import build_html as prancheta
    from scripts.build_web_page import build_html
    if not (RAIZ / "data" / "lineups" / "de_mirage.json").exists():
        pytest.skip("sem a biblioteca da Mirage")
    pasta = tmp_path_factory.mktemp("nomes")
    for partida in PARTIDAS:
        orig = RAIZ / "data" / "processed" / partida
        if not (orig / "web_payload.json").exists():
            pytest.skip(f"sem o processado da {partida}")
        elencos = json.loads((orig / "web_payload.json").read_text(encoding="utf-8"))["match"]["rosters"]
        troca = {elencos["A"][0]: MAU_SCRIPT, elencos["B"][0]: MAU_NEGRITO}
        base = pasta / f"dados_{partida}"
        base.mkdir()
        for arq in ("web_payload.json", "replay.json", "breakdown.json", "match_meta.json"):
            texto = (orig / arq).read_text(encoding="utf-8")
            if arq != "match_meta.json":
                for bom, mau in troca.items():
                    # o nome como valor inteiro, como chave e dentro de frases geradas
                    texto = texto.replace(json.dumps(bom)[1:-1], json.dumps(mau)[1:-1])
            (base / arq).write_text(texto, encoding="utf-8")
        (pasta / f"{partida}.html").write_text(build_html(partida, base=base), encoding="utf-8")
    (pasta / "prancheta_de_mirage.html").write_text(prancheta("de_mirage"), encoding="utf-8")
    return pasta


def _abre(navegador, arq):
    ctx = navegador.new_context(viewport={"width": 1400, "height": 1000})
    pg = ctx.new_page()
    erros = []
    pg.on("pageerror", lambda e: erros.append(str(e)))
    pg.goto(arq.as_uri())
    pg.wait_for_selector("[role=tab][data-tab]")
    pg._erros = erros
    return ctx, pg


@pytest.mark.parametrize("partida", PARTIDAS)
def test_nome_malicioso_aparece_literal_e_nao_vira_marcacao(navegador, paginas, partida):
    ctx, pg = _abre(navegador, paginas / f"{partida}.html")
    try:
        assert pg._erros == []
        literais = set()
        for aba in pg.eval_on_selector_all("[role=tab][data-tab]", "els => els.map(e => e.dataset.tab)"):
            pg.click(f'[role=tab][data-tab="{aba}"]')
            pg.wait_for_timeout(250)
            r = pg.evaluate(INJETADOS)
            assert r == {"x": None, "img": 0, "b": 0}, (aba, r)
            texto = pg.inner_text(f'[data-panel="{aba}"]')
            if MAU_NEGRITO in texto:
                literais.add(aba)
            if "onerror" in texto:
                literais.add(aba + ":script")
        # o nome aparece, e aparece LITERAL (as abas de jogador o mostram)
        assert {"jogadores", "perfil", "estilos"} <= literais, literais
        assert "onerror" in pg.inner_text("#tc-a") + pg.inner_text("#tc-b")
        assert pg._erros == []
    finally:
        ctx.close()


def test_o_nome_malicioso_chega_literal_a_prancheta_pelo_instante(navegador, paginas):
    ctx, pg = _abre(navegador, paginas / f"{PARTIDA}.html")
    try:
        pg.locator('[data-tab="replay"]').first.click()
        pg.wait_for_function("() => window.MapAnnotations && MapAnnotations._interno.S.reprojecoes > 0")
        pg.locator("#strip button", has_text="1").first.click()
        pg.evaluate("() => { const s = document.getElementById('scrub'); s.value = 8; s.dispatchEvent(new Event('input')); }")
        pg.click("#anot-toggle")   # a barra de desenho abre recolhida (auditoria 5.1)
        pg.click("#anot-tatica-instante")
        pg.wait_for_function("() => window.Prancheta && Prancheta._interno.S.estado !== null")
        rotulos = pg.evaluate("""() => { const I = Prancheta._interno;
            return Object.values(I.quadroDoPasso(I.S.estado, 0, I.centro()).pecas).map(p => p.rotulo); }""")
        # a prancheta limita o tamanho do rótulo: o nome longo chega LITERAL e cortado
        assert MAU_NEGRITO in rotulos
        assert any(r.startswith("</script><img") and MAU_SCRIPT.startswith(r) for r in rotulos), rotulos
        assert pg.evaluate(INJETADOS) == {"x": None, "img": 0, "b": 0}
        banco = pg.inner_text("#pr-banco")
        assert MAU_NEGRITO in banco and "onerror" in banco
        assert pg._erros == []
    finally:
        ctx.close()
