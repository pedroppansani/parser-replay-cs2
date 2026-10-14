"""Grupos na prancheta: o link de convite é por página de mapa (decisão 47).

Quem entra com o código de um grupo da Mirage pela página da Inferno (colando o código, ou abrindo o
`#sala=` nela) é levado para a página da Mirage, já dentro do grupo, com o mesmo nick. Sem rede: as duas
páginas falam com o MESMO servidor falso (`falsa.compartilhado`, o localStorage do navegador do teste).
"""
from __future__ import annotations

import pytest

pytest.importorskip("playwright.sync_api")

from tests.test_grupos_browser import CLIENTES_JS, G  # noqa: E402
from tests.test_tactics_browser import contexto, navegador  # noqa: E402,F401

MIRAGE, INFERNO = "de_mirage", "de_inferno"
CHAVE = "teste-servidor-falso"


@pytest.fixture(scope="module")
def paginas(tmp_path_factory):
    from scripts.build_tactics_page import arquivo_da_pagina, build_html
    pasta = tmp_path_factory.mktemp("grupo-mapas")
    for mapa in (MIRAGE, INFERNO):
        html = build_html(mapa, grupo={"modo": "falsa", "site": "https://exemplo.github.io/site/",
                                       "pagina": arquivo_da_pagina(mapa),
                                       "falsa": {"compartilhado": CHAVE, "atrasoMs": 5}})
        (pasta / arquivo_da_pagina(mapa)).write_text(html, encoding="utf-8")
    return {MIRAGE: pasta / arquivo_da_pagina(MIRAGE), INFERNO: pasta / arquivo_da_pagina(INFERNO)}


def abre(ctx, pagina, hash_=""):
    pg = ctx.new_page()
    erros = []
    pg.on("pageerror", lambda e: erros.append(str(e)))
    pg.add_init_script(CLIENTES_JS)
    pg.goto(pagina.as_uri() + hash_)
    pg.wait_for_function("() => Prancheta._interno.S.estado !== null && !!document.getElementById('pr-painel-grupo')")
    pg._erros = erros
    return pg


def sala_da_lider_na_mirage(ctx, paginas):
    """A líder cria o grupo na página da Mirage e devolve o código."""
    pg = abre(ctx, paginas[MIRAGE])
    return pg.evaluate("async () => await window.__criaSala()")


def espera_na_mirage(pg, nick):
    pg.wait_for_function("() => /prancheta_de_mirage\\.html/.test(location.href) && !!window.Grupo && "
                         "Grupo._interno.G().fase === 'dentro' && Grupo._interno.G().membros.length > 0", timeout=15000)
    assert G(pg, "G.nick") == nick


def entra_pela_aba(pg, codigo, nick):
    pg.evaluate("() => Prancheta._interno.abaDoPainel('grupo')")
    pg.fill("#gr-nick", nick)
    pg.fill("#gr-codigo", codigo)
    pg.click('[data-acao="entrar"]')


def test_colar_o_codigo_na_pagina_de_outro_mapa_leva_para_a_do_mapa_certo(contexto, paginas):
    codigo = sala_da_lider_na_mirage(contexto, paginas)
    pg = abre(contexto, paginas[INFERNO])
    entra_pela_aba(pg, codigo, "spinx")
    espera_na_mirage(pg, "spinx")
    assert pg.url.endswith(f"#sala={codigo}")                 # o link limpo: sem o nick na barra
    assert "spinx" not in pg.url
    assert G(pg, "G.codigo") == codigo and G(pg, "G.papel") == "membro"
    assert pg.evaluate("() => Prancheta.grupo.documento().mapa") == MIRAGE
    pg.wait_for_function("() => !!Prancheta._interno.S.estado.pecas.pecaztrike", timeout=15000)   # a tática do grupo
    assert pg._erros == []


def test_o_link_sala_numa_pagina_de_outro_mapa_leva_para_a_do_mapa_certo(contexto, paginas):
    codigo = sala_da_lider_na_mirage(contexto, paginas)
    pg = abre(contexto, paginas[INFERNO], f"#sala={codigo}")
    assert pg.input_value("#gr-codigo") == codigo
    # abrir o link não entra sozinho: só o clique (e só com nick)
    assert G(pg, "G.fase") == "fora"
    pg.fill("#gr-nick", "Zé Pedro")
    pg.click('[data-acao="entrar"]')
    espera_na_mirage(pg, "Zé Pedro")                           # o nick (com acento e espaço) chega inteiro
    assert pg._erros == []


def test_o_mesmo_usuario_nao_conta_duas_vezes_nem_vira_nick_repetido(contexto, paginas):
    codigo = sala_da_lider_na_mirage(contexto, paginas)
    pg = abre(contexto, paginas[INFERNO])
    entra_pela_aba(pg, codigo, "spinx")
    espera_na_mirage(pg, "spinx")
    nicks = G(pg, "G.membros.map((m) => m.nick)")
    assert sorted(nicks) == ["nomad", "spinx"]                 # um membro só por pessoa: a líder e ela


def test_mapa_igual_nao_redireciona(contexto, paginas):
    codigo = sala_da_lider_na_mirage(contexto, paginas)
    pg = abre(contexto, paginas[MIRAGE])
    url = pg.url
    entra_pela_aba(pg, codigo, "spinx")
    pg.wait_for_function("() => Grupo._interno.G().fase === 'dentro' && Grupo._interno.G().membros.length > 0")
    assert pg.url.split("#")[0] == url.split("#")[0] and "nick" not in pg.url


def test_codigo_errado_nao_redireciona_e_diz_a_mesma_coisa(contexto, paginas):
    sala_da_lider_na_mirage(contexto, paginas)
    pg = abre(contexto, paginas[INFERNO])
    url = pg.url
    entra_pela_aba(pg, "ABCDEFGH", "spinx")
    pg.wait_for_function("() => (document.getElementById('gr-e-codigo') || {}).textContent === '✕ Erro: Nenhum grupo com esse código.'")
    assert pg.url == url and G(pg, "G.fase") == "fora"


def test_mapa_estranho_vindo_do_servidor_nao_vira_endereco(contexto, paginas):
    """O mapa vem do servidor e entra numa URL: fora do formato de salas.mapa, não navega."""
    pg = abre(contexto, paginas[INFERNO])
    # o servidor falso aceita qualquer texto de mapa; a página é que filtra
    codigo = pg.evaluate("""async () => { const L = window.__cliente('u-x', 'x'); await L.s.prepara();
        const r = await L.s.criar({ mapa: '../fora', cabecalho: Object.assign({}, Prancheta.grupo.documento(), { operacoes: [] }) });
        return r.codigo; }""")
    url = pg.url
    entra_pela_aba(pg, codigo, "spinx")
    pg.wait_for_function("() => ((document.getElementById('gr-e-codigo') || {}).textContent || '').indexOf('outro mapa') >= 0")
    assert pg.url == url and G(pg, "G.fase") == "fora"
