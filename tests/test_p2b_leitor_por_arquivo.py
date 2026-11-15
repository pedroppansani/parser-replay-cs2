"""P2b: o leitor dos comandos (`comandos/leitor.js`, ~39 KB) sai do HTML da prancheta do site e passa a ser pedido quando a aba Comandos abre, como o plano.

A página gerada sozinha (os testes da C1 a C4) o traz embutido, como antes; só `leitor_externo=True` (o build do site) o deixa de fora. Quem aperta "Entender" antes de ele chegar vê
"Carregando os comandos…" e a frase é entendida quando chega; se o arquivo não vem, o aviso de sempre e o "Aplicar" desligado."""
from __future__ import annotations

import html
import http.server
import re
import shutil
import threading
import time
from pathlib import Path

import pytest

pytest.importorskip("playwright.sync_api")

from tests.test_comandos_tempos import _escreve, _peca, _ponto  # noqa: E402,F401
from tests.test_tactics_browser import abre, contexto, interno, navegador  # noqa: E402,F401

RAIZ = Path(__file__).resolve().parent.parent
MAPA = "de_mirage"
WEB = RAIZ / "dashboard" / "web" / "comandos"


def _site(tmp_path_factory, com_leitor=True):
    """A prancheta como o site a gera (biblioteca, plano e leitor externos), com `comandos/plano.js` e (ou não) `comandos/leitor.js` ao lado."""
    from scripts.build_tactics_page import ARQUIVO_DO_LEITOR, ARQUIVO_DO_PLANO, arquivo_da_pagina, build_html
    pasta = tmp_path_factory.mktemp("site_leitor")
    (pasta / arquivo_da_pagina(MAPA)).write_text(build_html(MAPA, biblioteca_externa=True, plano_externo=True, leitor_externo=True), encoding="utf-8")
    (pasta / "comandos").mkdir(exist_ok=True)
    shutil.copyfile(WEB / "plano.js", pasta / ARQUIVO_DO_PLANO)
    if com_leitor:
        shutil.copyfile(WEB / "leitor.js", pasta / ARQUIVO_DO_LEITOR)
    return pasta, arquivo_da_pagina(MAPA)


def test_a_pagina_gerada_sozinha_traz_o_leitor_e_a_do_site_so_o_caminho():
    from scripts.build_tactics_page import ARQUIVO_DO_LEITOR, build_html
    sozinha, site = build_html(MAPA, plano_externo=True), build_html(MAPA, biblioteca_externa=True, plano_externo=True, leitor_externo=True)
    chave = re.compile(r'"leitor_arquivo"\s*:\s*"' + re.escape(ARQUIVO_DO_LEITOR) + '"')
    assert "LeitorDeComandos = {" in sozinha and not chave.search(sozinha)
    assert "LeitorDeComandos = {" not in site and chave.search(site)
    assert len(sozinha) - len(site) > 35_000                                                  # o que a prancheta do site deixa de carregar com a página
    csp = lambda h: html.unescape(re.search(r'<meta http-equiv="Content-Security-Policy" content="([^"]*)"', h).group(1))
    assert csp(sozinha) == csp(site) and "script-src 'self' 'unsafe-inline'" in csp(site)      # a política de segurança não afrouxa


def test_no_site_o_leitor_so_e_pedido_quando_a_aba_abre_e_depois_funciona(contexto, tmp_path_factory):
    pasta, pagina = _site(tmp_path_factory)
    pg = contexto.new_page()
    pedidos = []
    pg.on("request", lambda r: pedidos.append(r.url))
    pg.goto((pasta / pagina).as_uri())
    pg.wait_for_function("() => Prancheta._interno.S.estado !== null")
    pg.wait_for_timeout(400)
    assert not any(u.endswith("comandos/leitor.js") for u in pedidos) and pg.evaluate("() => typeof LeitorDeComandos") == "undefined"
    assert pg.locator("[data-aba=comandos], #pr-aba-comandos").count() >= 0                    # (a aba existe: o teste seguinte a abre escrevendo)
    base = _ponto(MAPA, "Base TR")
    _peca(pg, base["x"], base["y"])
    _escreve(pg, "tr 2 corre pro meio aos 1:30")
    pg.wait_for_function("() => document.querySelectorAll('#pr-cmd-entendi li').length === 1 && !document.getElementById('pr-cmd-carregando-plano')", timeout=15000)
    assert any(u.endswith("comandos/leitor.js") for u in pedidos) and any(u.endswith("comandos/plano.js") for u in pedidos)
    assert "chega" in pg.inner_text("#pr-cmd-entendi") and pg.is_enabled("#pr-cmd-aplicar")
    pg.close()


def test_o_arquivo_do_leitor_que_nao_carrega_vira_aviso_e_o_aplicar_fica_desligado(contexto, tmp_path_factory):
    pasta, pagina = _site(tmp_path_factory, com_leitor=False)
    pg = abre(contexto, pasta / pagina)
    base = _ponto(MAPA, "Base TR")
    _peca(pg, base["x"], base["y"])
    _escreve(pg, "tr 2 corre pro meio aos 1:30")
    pg.wait_for_function("() => !!document.getElementById('pr-cmd-sem-plano')", timeout=15000)
    assert "Recarregue a página" in pg.inner_text("#pr-cmd-sem-plano") and pg.is_disabled("#pr-cmd-aplicar")
    assert interno(pg, "S.doc.operacoes.filter(o => o.tipo === 'cria_caminho').length") == 0


def test_entender_antes_de_o_leitor_chegar_mostra_carregando_e_entende_quando_chega(contexto, tmp_path_factory):
    pasta, pagina = _site(tmp_path_factory)

    class Lento(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *a, **k):
            super().__init__(*a, directory=str(pasta), **k)

        def do_GET(self):
            if self.path.endswith("comandos/leitor.js"):
                time.sleep(1.5)                                                               # o leitor demora: dá tempo de apertar Entender antes
            super().do_GET()

        def log_message(self, *a):
            pass

    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Lento)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    try:
        pg = contexto.new_page()
        pg.goto(f"http://127.0.0.1:{srv.server_address[1]}/{pagina}")
        pg.wait_for_function("() => Prancheta._interno.S.estado !== null")
        base = _ponto(MAPA, "Base TR")
        _peca(pg, base["x"], base["y"])
        _escreve(pg, "tr 2 corre pro meio aos 1:30")                                          # abre a aba, escreve e aperta Entender com o leitor ainda a caminho
        assert pg.locator("#pr-cmd-carregando-plano").count() == 1 or pg.evaluate("() => typeof LeitorDeComandos") != "undefined"
        pg.wait_for_function("() => document.querySelectorAll('#pr-cmd-entendi li').length === 1 && !document.getElementById('pr-cmd-carregando-plano')", timeout=15000)
        assert "chega" in pg.inner_text("#pr-cmd-entendi")
        pg.close()
    finally:
        srv.shutdown()


# --------------------------------------------------------------------------------------------------------------------------------------------------------------------------
# a página da partida: a seção Comandos (JS e CSS) só vem quando alguém ENTRA no Reescrever
# --------------------------------------------------------------------------------------------------------------------------------------------------------------------------

def _partida(tmp_path_factory, com_casca=True):
    from scripts.build_reescrever_comandos import ARQUIVO_DA_CASCA, escreve
    from scripts.build_web_page import build_html
    from tests.test_reescrever_modo import PARTIDA
    d = tmp_path_factory.mktemp("partida_p2b")
    arq = d / f"{PARTIDA}.html"
    arq.write_text(build_html(PARTIDA), encoding="utf-8")
    escreve(d, [MAPA])
    if not com_casca:
        (d / ARQUIVO_DA_CASCA).unlink()
    return arq


def _no_round(pg, arq):
    pg.goto(arq.as_uri() + "#replay")
    pg.wait_for_function("() => window.MapAnnotations && MapAnnotations._interno.S.reprojecoes > 0")
    pg.wait_for_timeout(500)
    pg.locator("#strip .rchip", has_text="23").first.click()
    pg.wait_for_timeout(200)


def test_a_pagina_da_partida_nao_traz_a_secao_comandos_nem_o_css_dela():
    from scripts.build_web_page import build_html
    from tests.test_reescrever_modo import PARTIDA
    h = build_html(PARTIDA)
    assert ".rw-cmd-cartao" not in h and "rw-cmd-texto" not in h and "CascaDoReescrever = " not in h        # nem o JS da seção nem as regras dela estão na página
    assert "comandos/casca.js" in h                                                                         # só o caminho, para o ponto de entrada


def test_a_secao_so_e_pedida_ao_entrar_no_reescrever_e_o_resto_so_ao_abrir_a_secao(navegador, tmp_path_factory):
    arq = _partida(tmp_path_factory)
    ctx = navegador.new_context(viewport={"width": 1440, "height": 900})
    pg = ctx.new_page(); pedidos = []; erros = []
    pg.on("request", lambda r: pedidos.append(r.url))
    pg.on("pageerror", lambda e: erros.append(str(e)))
    try:
        _no_round(pg, arq)
        assert not [u for u in pedidos if "/comandos/" in u] and pg.locator("#rw-comandos").count() == 0 and pg.locator("#rw-cmd-css").count() == 0
        pg.click("#rw-entrar")
        pg.wait_for_selector("#rw-comandos")
        assert sorted(u.rsplit("/comandos/", 1)[1] for u in pedidos if "/comandos/" in u) == ["casca.js"]        # entrar pede só a seção; o leitor e o resto esperam a seção abrir
        assert pg.locator("#rw-cmd-css").count() == 1 and pg.evaluate("typeof LeitorDeComandos") == "undefined"
        pg.click("#rw-cmd-abre")
        pg.wait_for_function("() => window.ComandosNoReescrever && document.querySelector('#rw-cmd-cartao .rw-cmd-vazio')")
        assert sorted(u.rsplit("/comandos/", 1)[1] for u in pedidos if "/comandos/" in u) == ["casca.js", "leitor.js", "plano.js", "real.js", "real/de_mirage.js", "reescrever.js"]
        n = len(pedidos)
        pg.click("#rw-sair"); pg.click("#rw-entrar"); pg.wait_for_selector("#rw-comandos")                    # sair e entrar de novo: nada novo pedido, uma seção só
        assert len(pedidos) == n and pg.locator("#rw-comandos").count() == 1 and pg.locator("#rw-cmd-css").count() == 1 and erros == []
    finally:
        ctx.close()


def test_a_secao_que_nao_carrega_diz_o_motivo_e_o_resto_do_reescrever_continua(navegador, tmp_path_factory):
    arq = _partida(tmp_path_factory, com_casca=False)
    ctx = navegador.new_context(viewport={"width": 1440, "height": 900})
    pg = ctx.new_page(); erros = []
    pg.on("pageerror", lambda e: erros.append(str(e)))
    try:
        _no_round(pg, arq)
        pg.click("#rw-entrar")
        pg.wait_for_selector(".rw-cmd-lugar .rw-cmd-erro")
        assert "Não consegui carregar os comandos" in pg.inner_text(".rw-cmd-lugar .rw-cmd-erro") and pg.get_attribute(".rw-cmd-lugar .rw-cmd-erro", "role") == "alert"
        assert pg.evaluate("window.__reescrever().ativo") and pg.locator(".peca-rw").count() >= 5 and erros == []      # as peças, o banco e o resto continuam
    finally:
        ctx.close()
