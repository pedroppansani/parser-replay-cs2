"""Grupos na prancheta (fase 16a): o link `#sala=` com nick salvo mostra UM botão, "Entrar no grupo da Mirage
como <nick>", com o campo do nick editável. Abrir o link não entra sozinho nem faz pedido (decisão 47); um clique
entra. Sem nick salvo, o formulário de sempre. Tudo com a SalaFalsa (sem rede, sem conta).
"""
from __future__ import annotations

import pytest

pytest.importorskip("playwright.sync_api")

from tests.test_grupos_browser import CLIENTES_JS, G  # noqa: E402
from tests.test_tactics_browser import contexto, navegador  # noqa: E402,F401

MAPA = "de_mirage"
CHAVE = "teste-convite-falso"
CHAVE_DO_NICK = "prancheta:grupo-nick"


@pytest.fixture(scope="module")
def pagina(tmp_path_factory):
    from scripts.build_tactics_page import arquivo_da_pagina, build_html
    html = tmp_path_factory.mktemp("grupo-convite") / arquivo_da_pagina(MAPA)
    html.write_text(build_html(MAPA, grupo={"modo": "falsa", "site": "https://exemplo.github.io/site/",
                                            "pagina": arquivo_da_pagina(MAPA),
                                            "falsa": {"compartilhado": CHAVE, "atrasoMs": 5}}), encoding="utf-8")
    return html


def abre(ctx, pagina, hash_="", nick_salvo=None):
    pg = ctx.new_page()
    erros = []
    pg.on("pageerror", lambda e: erros.append(str(e)))
    pg.add_init_script(CLIENTES_JS)
    if nick_salvo is not None:
        pg.add_init_script(f"try {{ localStorage.setItem({CHAVE_DO_NICK!r}, {nick_salvo!r}); }} catch (e) {{}}")
    pg.goto(pagina.as_uri() + hash_)
    pg.wait_for_function("() => Prancheta._interno.S.estado !== null && !!document.getElementById('pr-painel-grupo')")
    pg._erros = erros
    return pg


def sala_da_lider(ctx, pagina):
    pg = abre(ctx, pagina)
    return pg.evaluate("async () => await window.__criaSala()")


def nada_pedido(pg):
    return pg.evaluate("() => !window.__servidorFalso || window.__servidorFalso.pedidos.length === 0")


def test_link_com_nick_salvo_mostra_o_botao_e_nao_faz_pedido(contexto, pagina):
    codigo = sala_da_lider(contexto, pagina)
    pg = abre(contexto, pagina, f"#sala={codigo}", nick_salvo="spinx")
    pg.wait_for_selector("#gr-entrar-convite")
    assert pg.get_attribute("#pr-aba-grupo", "aria-selected") == "true"
    assert pg.inner_text("#gr-entrar-convite") == "Entrar no grupo da Mirage como spinx"
    assert pg.input_value("#gr-nick") == "spinx" and pg.is_editable("#gr-nick")
    assert pg.locator("#gr-codigo").count() == 0                    # o formulário de sempre não aparece
    assert pg.locator("#pr-painel-grupo .gr-convite button.gr-principal").count() == 1   # UM botão de entrada
    assert G(pg, "G.fase") == "fora"
    assert nada_pedido(pg)                                           # abrir o link não conecta a servidor nenhum
    caixa = pg.locator("#gr-entrar-convite").bounding_box()
    assert caixa["height"] >= 44
    assert pg._erros == []


def test_um_clique_entra_no_grupo(contexto, pagina):
    codigo = sala_da_lider(contexto, pagina)
    pg = abre(contexto, pagina, f"#sala={codigo}", nick_salvo="spinx")
    pg.click("#gr-entrar-convite")
    pg.wait_for_function("() => Grupo._interno.G().fase === 'dentro' && Grupo._interno.G().membros.length > 0")
    assert G(pg, "G.nick") == "spinx" and G(pg, "G.codigo") == codigo and G(pg, "G.papel") == "membro"
    assert pg._erros == []


def test_editar_o_nick_antes_do_clique_entra_com_o_nick_editado(contexto, pagina):
    codigo = sala_da_lider(contexto, pagina)
    pg = abre(contexto, pagina, f"#sala={codigo}", nick_salvo="spinx")
    pg.wait_for_selector("#gr-entrar-convite")
    pg.fill("#gr-nick", "zeta")
    assert pg.inner_text("#gr-entrar-convite") == "Entrar no grupo da Mirage como zeta"   # o rótulo acompanha o campo
    assert pg.evaluate("() => document.activeElement.id") == "gr-nick"                    # sem perder o foco
    pg.click("#gr-entrar-convite")
    pg.wait_for_function("() => Grupo._interno.G().fase === 'dentro' && Grupo._interno.G().membros.length > 0")
    assert G(pg, "G.nick") == "zeta"
    assert pg.evaluate("(c) => localStorage.getItem(c)", CHAVE_DO_NICK) == "zeta"
    assert pg._erros == []


def test_nick_editado_invalido_erra_no_campo_e_nao_entra(contexto, pagina):
    codigo = sala_da_lider(contexto, pagina)
    pg = abre(contexto, pagina, f"#sala={codigo}", nick_salvo="spinx")
    pg.wait_for_selector("#gr-entrar-convite")
    pg.fill("#gr-nick", "<b>x</b>")
    pg.click("#gr-entrar-convite")
    pg.wait_for_selector("#gr-e-nick")
    assert G(pg, "G.fase") == "fora" and pg.locator("#gr-nick[aria-invalid='true']").count() == 1
    assert pg.locator("#pr-painel-grupo b").count() == 0             # o texto do nick nunca vira marcação


def test_sem_nick_salvo_continua_o_formulario_de_sempre(contexto, pagina):
    codigo = sala_da_lider(contexto, pagina)
    pg = abre(contexto, pagina, f"#sala={codigo}")
    pg.wait_for_function("() => !!document.getElementById('gr-codigo')")
    assert pg.input_value("#gr-codigo") == codigo
    assert pg.locator("#gr-entrar-convite").count() == 0
    assert nada_pedido(pg)


def test_nick_salvo_invalido_nao_vira_botao(contexto, pagina):
    pg = abre(contexto, pagina, "#sala=K7M2Q9XR", nick_salvo="<img src=x>")
    pg.wait_for_function("() => !!document.getElementById('gr-codigo')")
    assert pg.locator("#gr-entrar-convite").count() == 0
    assert pg.locator("#pr-painel-grupo img").count() == 0


def test_outro_codigo_volta_ao_formulario(contexto, pagina):
    codigo = sala_da_lider(contexto, pagina)
    pg = abre(contexto, pagina, f"#sala={codigo}", nick_salvo="spinx")
    pg.wait_for_selector("#gr-entrar-convite")
    pg.click('[data-acao="convite-outro"]')
    pg.wait_for_function("() => !!document.getElementById('gr-codigo')")
    assert pg.input_value("#gr-codigo") == codigo and pg.input_value("#gr-nick") == "spinx"
    assert nada_pedido(pg)


def test_o_botao_cabe_em_375(navegador, pagina):
    ctx = navegador.new_context(viewport={"width": 375, "height": 800})          # 375 desde a abertura da página
    try:
        codigo = sala_da_lider(ctx, pagina)
        pg = abre(ctx, pagina, f"#sala={codigo}", nick_salvo="spinx_com_nick_longo_ok")
        pg.wait_for_selector("#gr-entrar-convite")
        assert pg.evaluate("() => document.documentElement.scrollWidth") <= 375
        assert pg.locator("#gr-entrar-convite").bounding_box()["height"] >= 44
        assert pg.inner_text("#gr-entrar-convite") == "Entrar no grupo da Mirage como spinx_com_nick_longo_ok"
    finally:
        ctx.close()
