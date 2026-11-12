"""P1b: o nome da peça nunca fica embaixo do relógio grande da prancheta nem cortado pela borda do mapa.

O relógio ("1:55") é HTML por cima do mapa, então a camada de rótulos do canvas não o via: com a peça na borda de cima, perto do canto de cima à esquerda,
o nome ("TR 2") ia parar embaixo dele. Agora o relógio entra na mesma camada como obstáculo (`MapCore.rotulosReserva`) e o nome usa o mesmo cálculo de
posições da Fase M (embaixo da peça ou ao lado, o que couber). Uma peça por vez, nos 4 cantos da área visível, no meio e embaixo do próprio relógio,
na Mirage e na Nuke, nos 3 tamanhos de tela.
"""
from __future__ import annotations

from pathlib import Path

import pytest

sync_api = pytest.importorskip("playwright.sync_api")

RAIZ = Path(__file__).resolve().parent.parent
TAMANHOS = {"375": (375, 812), "1366x657": (1366, 657), "1440x900": (1440, 900)}
# (fração x, fração y) da ÁREA VISÍVEL do mapa; o relógio fica no canto de cima à esquerda
POSICOES = {"canto-cima-esq": (0.03, 0.03), "canto-cima-dir": (0.97, 0.03), "canto-baixo-esq": (0.03, 0.97), "canto-baixo-dir": (0.97, 0.97),
            "meio": (0.5, 0.5), "embaixo-do-relogio": (None, None)}


@pytest.fixture(scope="module")
def navegador():
    with sync_api.sync_playwright() as p:
        try:
            b = p.chromium.launch(channel="chrome")
        except Exception:
            try:
                b = p.chromium.launch()
            except Exception as err:  # pragma: no cover - depende da máquina
                pytest.skip(f"sem Chrome para o Playwright: {err}")
        yield b
        b.close()


_PAGINAS: dict = {}


def _pagina(tmp_path_factory, mapa):
    if not (RAIZ / "data" / "lineups" / f"{mapa}.json").exists():
        pytest.skip("biblioteca de arremessos não gerada (scripts/build_lineups.py)")
    if mapa not in _PAGINAS:
        from scripts.build_tactics_page import build_html
        html = tmp_path_factory.mktemp(f"nome_peca_{mapa}") / f"prancheta_{mapa}.html"
        html.write_text(build_html(mapa), encoding="utf-8")
        _PAGINAS[mapa] = html
    return _PAGINAS[mapa]


COLOCA = """([fx, fy]) => {
  const I = Prancheta._interno, S = I.S, cv = document.getElementById('pr-mapa'), v = S.view || { zoom: 1, panX: 0, panY: 0 };
  const rel = document.getElementById('pr-relogio-grande'), rr = rel.getBoundingClientRect(), cr = cv.getBoundingClientRect();
  const k = I.radar().width / cr.width;
  // em px de tela relativos ao canvas; (null, null) = o centro do relógio
  const sx = fx === null ? rr.left - cr.left + rr.width / 2 : fx * cr.width, sy = fy === null ? rr.top - cr.top + rr.height / 2 : fy * cr.height;
  const g = I.pixelParaJogo((sx * k - v.panX) / v.zoom, (sy * k - v.panY) / v.zoom);
  I.emiteLote([["cria_peca", { peca: "p1", lado: "t", rotulo: "2", passo: S.estado.passos[0].passo, x: g[0], y: g[1], nivel: 0 }]]);
}"""
TIRA = "() => Prancheta._interno.emiteLote([['remove_peca', { peca: 'p1' }]])"

MEDE = """() => {
  const cv = document.getElementById('pr-mapa'), cr = cv.getBoundingClientRect(), rel = document.getElementById('pr-relogio-grande');
  const rr = rel && !rel.hidden ? rel.getBoundingClientRect() : null;
  return { canvas: [cr.width, cr.height], relogio: rr ? [rr.left - cr.left, rr.top - cr.top, rr.width, rr.height] : null,
           caixas: window.__medicaoRotulos.caixas().map(c => ({ txt: c.txt, x: c.x, y: c.y, w: c.w, h: c.h })) };
}"""


@pytest.mark.parametrize("tamanho", list(TAMANHOS))
@pytest.mark.parametrize("mapa", ["de_mirage", "de_nuke"])
def test_nenhum_nome_de_peca_fica_embaixo_do_relogio_nem_fora_do_mapa(navegador, tmp_path_factory, mapa, tamanho):
    w, h = TAMANHOS[tamanho]
    ctx = navegador.new_context(viewport={"width": w, "height": h})
    try:
        pg = ctx.new_page()
        pg.goto(_pagina(tmp_path_factory, mapa).as_uri()); pg.wait_for_function("() => Prancheta._interno.S.estado !== null")
        for nome, (fx, fy) in POSICOES.items():      # uma peça por vez: cada caso é medido sozinho
            pg.evaluate(COLOCA, [fx, fy]); pg.wait_for_timeout(200)
            m = pg.evaluate(MEDE)
            assert m["relogio"], "o relógio grande tem que estar à mostra (a prancheta tem horário)"
            assert [c["txt"] for c in m["caixas"]] == ["TR 2"], f"{mapa} {tamanho} {nome}: a peça tem que ter o nome 'TR 2': {m['caixas']}"
            (c,) = m["caixas"]
            rx, ry, rw, rh = m["relogio"]; cw, ch = m["canvas"]
            cobre = c["x"] < rx + rw and c["x"] + c["w"] > rx and c["y"] < ry + rh and c["y"] + c["h"] > ry
            assert not cobre, f"{mapa} {tamanho} {nome}: o nome ficou embaixo do relógio ({c} contra {m['relogio']})"
            assert c["x"] >= -0.5 and c["y"] >= -0.5 and c["x"] + c["w"] <= cw + 0.5 and c["y"] + c["h"] <= ch + 0.5, f"{mapa} {tamanho} {nome}: o nome sai do mapa ({c})"
            pg.evaluate(TIRA)
    finally:
        ctx.close()
