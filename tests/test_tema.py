"""
O tema do site (Fase T): claro ou escuro, escolhido na landing e lembrado no navegador; na primeira visita, o do
aparelho; sem armazenamento, o do aparelho. O `tema.js` é um arquivo no <head> (sem script inline, a CSP não muda) e
aplica o tema antes de o corpo existir. A prancheta é sempre violeta e não carrega o `tema.js`. O botão da landing
funciona por teclado, tem nome e diz pelo aria-pressed se o escuro está ligado.
"""
from __future__ import annotations

import functools
import re
import shutil
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

from tests.test_csp import _paginas

RAIZ = Path(__file__).resolve().parent.parent
TEMA_JS = RAIZ / "dashboard" / "web" / "tema.js"
CHAVE = "goatdemo:tema"


@pytest.fixture(scope="module")
def paginas():
    return _paginas()


def test_o_tema_js_vem_no_head_das_paginas_do_site_e_nao_na_prancheta(paginas):
    for nome, html in paginas.items():
        head = html[:html.index("</head>")]
        if nome == "prancheta":
            assert 'data-tema="violeta"' in html and '<script src="tema.js">' not in html, nome
            continue
        # um arquivo, síncrono (sem async nem defer), antes do corpo: o tema vale desde a primeira pintura
        assert re.search(r'<script src="tema\.js"></script>', head), nome
        assert html.count('<script src="tema.js">') == 1, nome


def test_so_a_landing_tem_o_botao_de_tema(paginas):
    for nome, html in paginas.items():
        assert html.count('class="tema-botao"') == (1 if nome == "landing" else 0), nome


def test_o_tema_js_nao_tem_texto_nem_cor_e_so_le_e_aplica():
    js = TEMA_JS.read_text(encoding="utf-8")
    assert "prefers-color-scheme: dark" in js and CHAVE in js and "try" in js
    assert not re.search(r"#[0-9a-fA-F]{6}", js)


# --- no navegador, por HTTP (como o Pages) ---------------------------------------------------------------------

sync_api = pytest.importorskip("playwright.sync_api")

from tests.test_tactics_browser import navegador  # noqa: E402,F401  (fixture)


class _Quieto(SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass


@pytest.fixture(scope="module")
def site(paginas, tmp_path_factory):
    if "landing" not in paginas or "partida" not in paginas:
        pytest.skip("sem data/processed para montar a landing e a partida")
    pasta = tmp_path_factory.mktemp("tema")
    for nome, html in paginas.items():
        (pasta / f"{nome}.html").write_text(html, encoding="utf-8")
    shutil.copyfile(TEMA_JS, pasta / "tema.js")
    srv = ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(_Quieto, directory=str(pasta)))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{srv.server_address[1]}"
    srv.shutdown()


def _abre(navegador, url, esquema="light", bloqueia=False):
    ctx = navegador.new_context(color_scheme=esquema)
    if bloqueia:   # sem armazenamento (navegação privada, bloqueio): o acesso ao localStorage lança
        ctx.add_init_script("Object.defineProperty(window, 'localStorage', { get() { throw new Error('bloqueado'); } });")
    pg = ctx.new_page()
    erros = []
    pg.on("pageerror", lambda e: erros.append(str(e)))
    pg.goto(url)
    pg._erros = erros
    return ctx, pg


def _tema(pg):
    return pg.evaluate("() => document.documentElement.getAttribute('data-tema')")


@pytest.mark.parametrize("esquema,tema", [("light", "claro"), ("dark", "escuro")])
def test_na_primeira_visita_vale_o_tema_do_aparelho(navegador, site, esquema, tema):
    for pagina in ("landing", "partida", "jogadores"):
        ctx, pg = _abre(navegador, f"{site}/{pagina}.html", esquema)
        try:
            assert _tema(pg) == tema, pagina
            assert pg._erros == [], pagina
        finally:
            ctx.close()


def test_o_tema_ja_esta_aplicado_quando_o_corpo_comeca(navegador, site):
    """Sem piscar: o primeiro script do <body> já vê o tema escolhido (o tema.js rodou no <head>)."""
    ctx = navegador.new_context(color_scheme="dark")
    try:
        pg = ctx.new_page()
        pg.add_init_script("new MutationObserver((ms, o) => { if (document.body) { window.__noCorpo = "
                           "document.documentElement.getAttribute('data-tema'); o.disconnect(); } })"
                           ".observe(document, { childList: true, subtree: true });")
        pg.goto(f"{site}/landing.html")
        assert pg.evaluate("() => window.__noCorpo") == "escuro"
    finally:
        ctx.close()


def test_o_botao_troca_lembra_e_vale_nas_outras_paginas(navegador, site):
    ctx = navegador.new_context(color_scheme="light")
    try:
        pg = ctx.new_page()
        pg.goto(f"{site}/landing.html")
        botao = pg.locator(".tema-botao")
        assert botao.get_attribute("aria-pressed") == "false" and _tema(pg) == "claro"
        botao.focus()
        pg.keyboard.press("Enter")                                   # por teclado
        assert _tema(pg) == "escuro" and botao.get_attribute("aria-pressed") == "true"
        assert pg.evaluate("(c) => localStorage.getItem(c)", CHAVE) == "escuro"
        pg.goto(f"{site}/partida.html")                              # a escolha vale nas outras páginas
        assert _tema(pg) == "escuro"
        pg.goto(f"{site}/landing.html")
        pg.locator(".tema-botao").focus()
        pg.keyboard.press("Space")
        assert _tema(pg) == "claro" and pg.evaluate("(c) => localStorage.getItem(c)", CHAVE) == "claro"
    finally:
        ctx.close()


def test_a_escolha_guardada_vence_o_tema_do_aparelho(navegador, site):
    ctx = navegador.new_context(color_scheme="dark")
    try:
        ctx.add_init_script(f"try {{ localStorage.setItem('{CHAVE}', 'claro'); }} catch (e) {{}}")
        pg = ctx.new_page()
        pg.goto(f"{site}/jogadores.html")
        assert _tema(pg) == "claro"
    finally:
        ctx.close()


def test_sem_armazenamento_vale_o_do_aparelho_e_o_botao_ainda_troca(navegador, site):
    ctx, pg = _abre(navegador, f"{site}/landing.html", "dark", bloqueia=True)
    try:
        assert _tema(pg) == "escuro"
        pg.locator(".tema-botao").click()
        assert _tema(pg) == "claro"
        assert pg._erros == []
    finally:
        ctx.close()


def test_o_botao_tem_nome_e_cabe_no_toque_a_375(navegador, site):
    ctx = navegador.new_context(viewport={"width": 375, "height": 800}, color_scheme="light")
    try:
        pg = ctx.new_page()
        pg.goto(f"{site}/landing.html")
        botao = pg.get_by_role("button", name="Escuro")
        caixa = botao.bounding_box()
        assert caixa["height"] >= 44 and caixa["width"] >= 44
        assert pg.evaluate("() => document.documentElement.scrollWidth") <= 375
    finally:
        ctx.close()


@pytest.mark.parametrize("esquema", ["light", "dark"])
def test_a_prancheta_e_sempre_violeta(navegador, site, esquema):
    ctx = navegador.new_context(color_scheme=esquema)
    try:
        ctx.add_init_script(f"try {{ localStorage.setItem('{CHAVE}', 'claro'); }} catch (e) {{}}")
        pg = ctx.new_page()
        pg.goto(f"{site}/prancheta.html")
        assert _tema(pg) == "violeta"
        assert pg.evaluate("() => getComputedStyle(document.body).backgroundColor") == "rgb(4, 6, 28)"   # --fundo violeta
    finally:
        ctx.close()


def test_no_escuro_o_agente_e_desenhado_com_as_cores_do_claro_num_cartao(navegador, site):
    ctx = navegador.new_context(color_scheme="dark")
    try:
        pg = ctx.new_page()
        pg.goto(f"{site}/landing.html")
        agente = pg.locator("#agente")
        assert agente.get_attribute("data-tema") == "claro"
        assert pg.evaluate("() => getComputedStyle(document.getElementById('agente')).color") == "rgb(10, 10, 10)"  # --tinta do claro
        fundo = pg.evaluate("() => getComputedStyle(document.getElementById('agente'), '::before').backgroundColor")
        assert fundo == "rgb(250, 250, 250)"                          # o cartão: --superficie do claro
    finally:
        ctx.close()


def test_a_pagina_que_volta_da_memoria_com_a_escolha_mudada_recarrega(navegador, site):
    """Voltar e avançar: a página restaurada da memória do navegador (pageshow com persisted) depois de a escolha mudar
    em outra página recarrega com o tema novo (os gráficos leem as cores uma vez só)."""
    ctx = navegador.new_context(color_scheme="light")
    try:
        pg = ctx.new_page()
        pg.goto(f"{site}/partida.html")
        assert _tema(pg) == "claro"
        pg.evaluate("(c) => localStorage.setItem(c, 'escuro')", CHAVE)
        with pg.expect_navigation():
            pg.evaluate("() => window.dispatchEvent(new PageTransitionEvent('pageshow', { persisted: true }))")
        assert _tema(pg) == "escuro"
        # sem mudança, nada recarrega
        pg.evaluate("() => { window.__fica = 1; window.dispatchEvent(new PageTransitionEvent('pageshow', { persisted: true })); }")
        pg.wait_for_timeout(300)
        assert pg.evaluate("() => window.__fica") == 1
    finally:
        ctx.close()


def test_o_mapa_e_igual_nos_tres_temas():
    from metrics.paleta import TOKENS_DO_MAPA, le_tokens
    claro, escuro, violeta = (le_tokens(tema=t) for t in ("claro", "escuro", "violeta"))
    assert {n: escuro[n] for n in TOKENS_DO_MAPA} == {n: claro[n] for n in TOKENS_DO_MAPA} == {n: violeta[n] for n in TOKENS_DO_MAPA}
