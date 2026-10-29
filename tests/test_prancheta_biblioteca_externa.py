"""
A biblioteca de arremessos num arquivo próprio, carregado depois de a tela montar (cartão 20).

O site grava a biblioteca em `arremessos/<mapa>.js` e a prancheta a carrega ao fim do init; o modo embutido (o padrão do
`build_html`, usado pelos outros testes) continua igual. Aqui: a biblioteca que chega pelo arquivo é a MESMA da embutida;
o round aberto do Replay sai igual nos dois modos, também quando a biblioteca demora (o pedido do arquivo fica preso até o
teste soltar); enquanto ela não chega a busca fica desligada e diz por quê; e, se o arquivo não carregar, a prancheta
segue sem arremesso real e explica.
"""
from __future__ import annotations

import functools
import json
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

sync_api = pytest.importorskip("playwright.sync_api")

from tests.test_tactics_browser import navegador  # noqa: E402,F401  (fixture)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
MAPA, PARTIDA, RODADA, QUADRO = "de_mirage", "match_02", 6, 40
NO_ESTADO = """() => { const S = Prancheta._interno.S, e = S.estado;
  return { pecas: Object.values(e.pecas).map(p => [p.lado, p.rotulo]).sort(),
           granadas: Object.values(e.granadas).map(g => [g.arma, g.origem, g.destino, g.arremesso ? g.arremesso.id : null,
                                                         g.t === undefined ? null : g.t]).sort((a, b) => JSON.stringify(a) < JSON.stringify(b) ? -1 : 1),
           operacoes: S.doc.operacoes.length, origem: S.doc.origem }; }"""


def _precisa_de_dado():
    if not (PROJECT_ROOT / "data" / "lineups" / f"{MAPA}.json").exists():
        pytest.skip("biblioteca de arremessos não gerada (scripts/build_lineups.py)")
    if not (PROJECT_ROOT / "data" / "processed" / PARTIDA / "replay.json").exists():
        pytest.skip(f"sem data/processed/{PARTIDA}")


def _site(pasta: Path, externa: bool) -> Path:
    from scripts.build_tactics_page import arquivo_da_biblioteca, arquivo_da_pagina, biblioteca_js, build_html
    from scripts.build_web_page import build_html as partida
    (pasta / arquivo_da_pagina(MAPA)).write_text(build_html(MAPA, biblioteca_externa=externa), encoding="utf-8")
    (pasta / f"{PARTIDA}.html").write_text(partida(PARTIDA), encoding="utf-8")
    if externa:
        (pasta / arquivo_da_biblioteca(MAPA)).parent.mkdir(exist_ok=True)
        (pasta / arquivo_da_biblioteca(MAPA)).write_text(biblioteca_js(MAPA), encoding="utf-8")
    return pasta


@pytest.fixture(scope="module")
def sites(tmp_path_factory):
    _precisa_de_dado()
    return {"embutida": _site(tmp_path_factory.mktemp("bib-embutida"), False),
            "externa": _site(tmp_path_factory.mktemp("bib-externa"), True)}


@pytest.fixture(scope="module")
def servidor(sites):
    """O site externo servido por HTTP (como o Pages): o pedido do arquivo da biblioteca pode ser preso pelo teste."""
    srv = ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(_Quieto, directory=str(sites["externa"])))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{srv.server_address[1]}"
    srv.shutdown()


class _Quieto(SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass


def _abre_o_round(pg, base: str):
    """Do Replay da partida, "Abrir round na prancheta" no round e quadro fixos (o caminho de quem usa o site)."""
    pg.goto(f"{base}/{PARTIDA}.html")
    pg.locator('[data-tab="replay"]').first.click()
    pg.wait_for_function("() => window.MapAnnotations && MapAnnotations._interno.S.reprojecoes > 0")
    pg.locator("#strip button", has_text=str(RODADA)).first.click()
    pg.evaluate(f"() => {{ const s = document.getElementById('scrub'); s.value = {QUADRO}; s.dispatchEvent(new Event('input')); }}")
    pg.click("#anot-toggle")
    pg.click("#anot-abrir-round")


def _round_pronto(pg):
    pg.wait_for_function("() => window.Prancheta && Prancheta._interno.S.doc && Prancheta._interno.S.doc.origem"
                         " && Prancheta._interno.S.doc.origem.base_real")


def _round_embutido(navegador, sites):
    ctx = navegador.new_context(viewport={"width": 1400, "height": 1000})
    try:
        pg = ctx.new_page()
        _abre_o_round(pg, sites["embutida"].as_uri())
        _round_pronto(pg)
        return pg.evaluate(NO_ESTADO)
    finally:
        ctx.close()


def test_a_biblioteca_do_arquivo_e_a_mesma_da_embutida(navegador, sites):
    from scripts.build_tactics_page import arquivo_da_pagina
    ctx = navegador.new_context()
    try:
        pg = ctx.new_page()
        erros = []
        pg.on("pageerror", lambda e: erros.append(str(e)))
        pg.goto((sites["externa"] / arquivo_da_pagina(MAPA)).as_uri())          # aberta como arquivo (file://)
        pg.wait_for_function("() => Prancheta._interno.biblioteca() !== null")
        do_arquivo = pg.evaluate("() => JSON.stringify(Prancheta._interno.biblioteca())")
        esperada = json.loads((PROJECT_ROOT / "data" / "lineups" / f"{MAPA}.json").read_text(encoding="utf-8"))
        assert json.loads(do_arquivo) == esperada
        assert not pg.locator('aside [data-ferramenta="buscar"]').is_disabled()
        assert erros == []
        # a página leva só o caminho: a biblioteca não está mais no HTML
        html = (sites["externa"] / arquivo_da_pagina(MAPA)).read_text(encoding="utf-8")
        assert '"arremessos":' not in html and 'bibliotecaArquivo: "arremessos/de_mirage.js"' in html
    finally:
        ctx.close()


def test_o_round_do_replay_sai_igual_mesmo_com_a_biblioteca_atrasada(navegador, sites, servidor):
    esperado = _round_embutido(navegador, sites)
    assert any(g[3] for g in esperado["granadas"]), "o round fixo precisa ter granada ligada ao arremesso real"
    ctx = navegador.new_context(viewport={"width": 1400, "height": 1000})
    presos = []
    try:
        pg = ctx.new_page()
        erros = []
        pg.on("pageerror", lambda e: erros.append(str(e)))
        pg.route("**/arremessos/*.js", lambda rota: presos.append(rota))     # a biblioteca fica presa até o teste soltar
        _abre_o_round(pg, servidor)
        pg.wait_for_function("() => window.Prancheta && Prancheta._interno.S.estado !== null")
        pg.wait_for_function("() => document.querySelector('aside [data-ferramenta=\"buscar\"]') !== null")
        while not presos:
            pg.wait_for_timeout(50)
        # enquanto a biblioteca não chega: a tela está montada, o round ainda não foi criado e a busca diz por quê
        assert pg.evaluate("() => !Prancheta._interno.S.doc.origem")
        buscar = pg.locator('aside [data-ferramenta="buscar"]')
        assert buscar.is_disabled() and "Carregando os arremessos reais" in buscar.get_attribute("title")
        presos[0].fulfill(path=str(sites["externa"] / "arremessos" / f"{MAPA}.js"), content_type="text/javascript")
        _round_pronto(pg)
        assert pg.evaluate(NO_ESTADO) == esperado
        assert not buscar.is_disabled() and "Clique onde a granada deve cair" in buscar.get_attribute("title")
        assert erros == []
    finally:
        ctx.close()


def test_sem_o_arquivo_a_prancheta_segue_sem_arremesso_real_e_explica(navegador, tmp_path_factory):
    from scripts.build_tactics_page import arquivo_da_pagina, build_html
    _precisa_de_dado()
    pasta = tmp_path_factory.mktemp("bib-sem-arquivo")
    (pasta / arquivo_da_pagina(MAPA)).write_text(build_html(MAPA, biblioteca_externa=True), encoding="utf-8")
    ctx = navegador.new_context()
    try:
        pg = ctx.new_page()
        erros = []
        pg.on("pageerror", lambda e: erros.append(str(e)))
        pg.goto((pasta / arquivo_da_pagina(MAPA)).as_uri())
        pg.wait_for_function("() => !document.getElementById('pr-sem-biblioteca').hidden")
        assert "não carregaram" in pg.inner_text("#pr-sem-biblioteca")
        assert pg.locator('aside [data-ferramenta="buscar"]').is_disabled()
        assert pg.evaluate("() => Prancheta._interno.biblioteca()") is None
        assert erros == []
    finally:
        ctx.close()
