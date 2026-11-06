"""L1: o voltar do navegador entre os endereços da página (#perfil, #replay) leva a aba junto; com o Reescrever editado o aviso abre, e cancelar
deixa o endereço igual à aba que continua à mostra (antes ele ficava diferente)."""
from __future__ import annotations

import pytest

sync_api = pytest.importorskip("playwright.sync_api")

from tests.test_reescrever_modo import (  # noqa: E402,F401  (fixtures e ajudas)
    _abre, _estado, navegador, pagina)
from tests.test_reescrever_r3 import _arrasta  # noqa: E402

ABA = "document.querySelector('.tabs [role=tab][aria-selected=true]').dataset.tab"


def _historico(navegador, pagina):
    """Abre em #perfil e vai para #replay: duas entradas do histórico na mesma página."""
    ctx = navegador.new_context(viewport={"width": 1440, "height": 900})
    pg = ctx.new_page(); erros = []
    pg.on("pageerror", lambda e: erros.append(str(e)))
    pg.goto(pagina.as_uri() + "#perfil")
    pg.wait_for_function(f"() => {ABA} === 'perfil'")
    pg.wait_for_timeout(500)
    pg.evaluate("location.hash = '#replay'")                                  # mudar o endereço à mão: a aba tem de acompanhar
    pg.wait_for_function(f"() => {ABA} === 'replay'")
    pg.wait_for_function("() => window.MapAnnotations && MapAnnotations._interno.S.reprojecoes > 0")
    pg.wait_for_timeout(500)
    return ctx, pg, erros


def test_o_voltar_leva_a_aba_junto_com_o_endereco(navegador, pagina):
    ctx, pg, erros = _historico(navegador, pagina)
    try:
        pg.go_back()
        pg.wait_for_function(f"() => {ABA} === 'perfil'")
        assert pg.evaluate("location.hash") == "#perfil"
        pg.go_forward()
        pg.wait_for_function(f"() => {ABA} === 'replay'")
        assert pg.evaluate("location.hash") == "#replay" and not erros
    finally:
        ctx.close()


def test_cancelar_o_aviso_pelo_voltar_deixa_o_endereco_igual_a_aba_que_aparece(navegador, pagina):
    ctx, pg, erros = _historico(navegador, pagina)
    try:
        pg.evaluate("document.getElementById('rw-entrar').click()"); pg.wait_for_timeout(300)
        pg.wait_for_timeout(900)
        _arrasta(pg)
        pg.go_back()                                                         # o endereço vai para #perfil e o aviso abre
        pg.wait_for_selector("#rw-continuar", state="visible")
        pg.click("#rw-continuar")                                            # cancela: continua editando
        pg.wait_for_function(f"() => location.hash.startsWith('#replay')")
        assert pg.evaluate(ABA) == "replay" and _estado(pg)["ativo"]
        assert pg.evaluate("location.hash").startswith("#replay")           # o endereço é o da aba que aparece
        assert any(p["editada"] for p in _estado(pg)["pecas"])               # e nada se perdeu
        pg.evaluate("location.hash = '#perfil'")                             # de novo (agora mudando o endereço à mão), descartando
        pg.wait_for_selector("#rw-descartar", state="visible")
        pg.click("#rw-descartar")
        pg.wait_for_function(f"() => {ABA} === 'perfil'")
        assert pg.evaluate("location.hash") == "#perfil" and not _estado(pg)["ativo"] and not erros
    finally:
        ctx.close()


def test_cancelar_o_aviso_devolve_o_endereco_com_round_e_tempo(navegador, pagina):
    """O endereço que abre o Replay num round e tempo (`#replay?round=23&t=40`) volta inteiro, não só `#replay`."""
    ctx = navegador.new_context(viewport={"width": 1440, "height": 900})
    pg = ctx.new_page(); erros = []
    pg.on("pageerror", lambda e: erros.append(str(e)))
    try:
        pg.goto(pagina.as_uri() + "#replay?round=23&t=40")
        pg.wait_for_function("() => window.MapAnnotations && MapAnnotations._interno.S.reprojecoes > 0")
        pg.wait_for_timeout(1200)
        endereco = pg.evaluate("location.hash")
        assert endereco == "#replay?round=23&t=40"
        pg.evaluate("document.getElementById('rw-entrar').click()"); pg.wait_for_timeout(1000)
        _arrasta(pg)
        pg.evaluate("location.hash = '#perfil'")
        pg.wait_for_selector("#rw-continuar", state="visible")
        pg.click("#rw-continuar")
        pg.wait_for_function("() => location.hash.startsWith('#replay')")
        assert pg.evaluate("location.hash") == endereco and pg.evaluate(ABA) == "replay" and not erros
    finally:
        ctx.close()
