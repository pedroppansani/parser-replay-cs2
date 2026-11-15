"""P2c (visual): a prancheta volta à navbar e os 10 mapas viram links; arrastar várias vezes no Reescrever; "Ver no mapa ↑" no celular; o nome do time; a peça sob o relógio."""
from __future__ import annotations

import pytest

sync_api = pytest.importorskip("playwright.sync_api")

from tests.test_reescrever_r1 import paginas_html, partidas  # noqa: E402,F401  (as páginas geradas)
from tests.test_reescrever_modo import navegador  # noqa: E402,F401


@pytest.mark.parametrize("largura", [375, 1440])
@pytest.mark.parametrize("pagina", ["landing", "jogadores", "reescrever", "partida", "prancheta"])
def test_os_quatro_links_da_navbar_cabem_sem_rolagem_lateral_e_em_uma_linha(navegador, paginas_html, pagina, largura):
    pasta, _ = paginas_html
    ctx = navegador.new_context(viewport={"width": largura, "height": 812})
    pg = ctx.new_page()
    try:
        pg.goto((pasta / f"{pagina}.html").as_uri())
        r = pg.evaluate("""() => { const n = document.querySelector('.site-nav'), as = [...n.querySelectorAll('a')], nb = n.getBoundingClientRect();
          return { textos: as.map(a => a.textContent), sobra: n.scrollWidth - n.clientWidth, topos: [...new Set(as.map(a => Math.round(a.getBoundingClientRect().top)))].length,
                   dentro: as.every(a => { const b = a.getBoundingClientRect(); return b.left >= nb.left - 0.5 && b.right <= nb.right + 0.5; }),
                   pagina: document.documentElement.scrollWidth - document.documentElement.clientWidth }; }""")
        assert r["textos"] == ["Partidas", "Jogadores", "Reescrever", "Prancheta"]
        assert r["sobra"] <= 0 and r["dentro"] and r["topos"] == 1 and r["pagina"] <= 0        # nenhuma rolagem lateral (nem a da navbar nem a da página) e os 4 na mesma linha
    finally:
        ctx.close()


# --------------------------------------------------------------------------------------------------------------------------------------------------------------------------
# arrastar várias vezes no Reescrever (0b): avançar o tempo, pausar e arrastar de novo põe uma parada nova que parte daquele quadro
# --------------------------------------------------------------------------------------------------------------------------------------------------------------------------

from tests.test_reescrever_comandos import _abre_no_instante  # noqa: E402
from tests.test_reescrever_modo import _estado  # noqa: E402
from tests.test_reescrever_r3 import XY  # noqa: E402


@pytest.fixture(scope="module")
def pagina_cmd(tmp_path_factory):
    from scripts.build_reescrever_comandos import escreve
    from scripts.build_web_page import build_html
    from tests.test_reescrever_modo import PARTIDA
    d = tmp_path_factory.mktemp("arrasta")
    arq = d / f"{PARTIDA}.html"
    arq.write_text(build_html(PARTIDA), encoding="utf-8")
    escreve(d, ["de_mirage"])
    return arq


def _arrasta(pg, nome, dx=70, dy=-50):
    """Pega a peça ONDE ELA ESTÁ na tela agora (no quadro em que a sua versão está pausada, não na última parada) e a solta `dx`, `dy` px adiante."""
    xy = pg.evaluate("n => window.__reescrever().pecas.find(p => p.nome === n).tela", nome)
    pg.mouse.move(*xy); pg.mouse.down(); pg.mouse.move(xy[0] + dx, xy[1] + dy, steps=5); pg.mouse.up()
    pg.wait_for_timeout(150)


def _trilha(pg, nome):
    return next(p for p in _estado(pg)["pecas"] if p["nome"] == nome)["trilha"]


def _avanca(pg, quadros):
    """Toca a sua versão e pausa `quadros` quadros depois (o quadro atual é o do scrub)."""
    alvo = int(_estado(pg)["quadro"]) + quadros
    pg.click("#play")
    pg.wait_for_function("q => window.__reescrever().quadro >= q", arg=alvo, timeout=20000)
    pg.click("#play")
    pg.wait_for_timeout(120)


def test_arrastar_de_novo_com_o_tempo_avancado_poe_uma_parada_nova_e_o_desfazer_tira_uma_por_vez(navegador, pagina_cmd):
    ctx, pg, erros = _abre_no_instante(navegador, pagina_cmd)
    try:
        pg.click("#rw-entrar")
        t0 = _estado(pg)["instante"]
        _arrasta(pg, "ropz", dx=60, dy=-40)                                                     # a primeira parada: no instante, como sempre
        _avanca(pg, 12)
        assert _estado(pg)["sua"] and pg.is_enabled("#rw-desfazer") and "avance o tempo e arraste outra vez" in pg.inner_text("#rw-dica")
        _arrasta(pg, "ropz", dx=-50, dy=60)                                                     # pausada: arrastar de novo = uma parada nova, daquele quadro
        _avanca(pg, 12)
        _arrasta(pg, "ropz", dx=40, dy=40)
        fs = [pa["f"] for pa in _trilha(pg, "ropz")]
        assert len(fs) == 3 and fs[0] == t0 and t0 < fs[1] < fs[2] and fs == sorted(fs)          # três paradas, em ordem, cada uma no quadro em que foi arrastada
        assert _estado(pg)["comandos"]["desfazer"] == 3
        mudou = pg.inner_text("#rw-mudou")
        assert mudou.count("ropz") >= 3                                                         # cada arrasto é uma linha, com o nick e o horário
        # o corte: volta o tempo para antes da segunda parada e arrasta: o que vinha depois some
        pg.evaluate("f => { const s = document.getElementById('scrub'); s.value = f; s.dispatchEvent(new Event('input')); }", fs[1] - 2)
        pg.wait_for_timeout(150)
        _arrasta(pg, "ropz", dx=20, dy=-80)
        novo = [pa["f"] for pa in _trilha(pg, "ropz")]
        assert novo[0] == t0 and len(novo) == 2 and novo[1] == fs[1] - 2                         # a primeira fica; a segunda e a terceira foram cortadas e entrou a nova
        assert _estado(pg)["comandos"]["desfazer"] == 4
        pg.click("#rw-desfazer"); pg.click("#rw-desfazer")                                      # dois Desfazer tiram uma parada por vez: o corte volta, depois a terceira
        assert [pa["f"] for pa in _trilha(pg, "ropz")] == fs[:2] and _estado(pg)["comandos"]["desfazer"] == 2
        assert erros == []
    finally:
        ctx.close()


def test_nao_arrasta_tocando_nem_antes_do_instante_nem_depois_da_morte_real(navegador, pagina_cmd):
    ctx, pg, erros = _abre_no_instante(navegador, pagina_cmd)
    try:
        pg.click("#rw-entrar")
        t0 = _estado(pg)["instante"]
        _arrasta(pg, "ZywOo", dx=60, dy=-40)                                                    # ZywOo morre no real depois do instante (quadro 249, 0:52)
        _avanca(pg, 8)
        pg.click("#play")                                                                       # tocando: nada é editável
        antes = _trilha(pg, "ZywOo")
        _arrasta(pg, "ZywOo", dx=-50, dy=50)
        assert _trilha(pg, "ZywOo") == antes and pg.is_disabled("#rw-desfazer")
        pg.click("#play")
        scrub = "f => { const s = document.getElementById('scrub'); s.value = f; s.dispatchEvent(new Event('input')); }"
        pg.evaluate(scrub, t0 - 6)                                                              # antes do instante do "Reescrever daqui"
        pg.wait_for_timeout(150)
        _arrasta(pg, "ZywOo", dx=-50, dy=50)
        assert _trilha(pg, "ZywOo") == antes
        pg.evaluate(scrub, 252)                                                                 # depois da morte real (249): só existe no real
        pg.wait_for_timeout(150)
        _arrasta(pg, "ZywOo", dx=-50, dy=50)
        assert _trilha(pg, "ZywOo") == antes and _estado(pg)["comandos"]["desfazer"] == 1
        pg.evaluate(scrub, 200)                                                                 # antes da morte: volta a valer
        pg.wait_for_timeout(150)
        _arrasta(pg, "ZywOo", dx=-50, dy=50)
        assert len(_trilha(pg, "ZywOo")) == 2 and erros == []
    finally:
        ctx.close()


# --------------------------------------------------------------------------------------------------------------------------------------------------------------------------
# "Ver no mapa ↑" no celular, depois do Aplicar (Reescrever e prancheta)
# --------------------------------------------------------------------------------------------------------------------------------------------------------------------------

def _dentro_da_janela(pg, seletor):
    return pg.evaluate("s => { const r = document.querySelector(s).getBoundingClientRect(); return r.top >= 0 && r.top < innerHeight && r.bottom > 0; }", seletor)


def test_ver_no_mapa_no_reescrever_leva_a_pagina_ao_mapa_poe_o_foco_nele_e_anuncia(navegador, pagina_cmd):
    from tests.test_reescrever_comandos import _abre_secao, _aplica, _escreve
    ctx, pg, erros = _abre_no_instante(navegador, pagina_cmd, 375, 812)
    try:
        _abre_secao(pg)
        assert pg.locator("#rw-cmd-ver-mapa").count() == 0                                      # antes do Aplicar não há botão
        _escreve(pg, "ropz corre pro meio aos 1:10"); _aplica(pg)
        assert pg.locator("#rw-cmd-ver-mapa").count() == 1 and pg.inner_text("#rw-cmd-ver-mapa") == "Ver no mapa ↑"
        pg.locator("#rw-cmd-ver-mapa").scroll_into_view_if_needed()
        assert not _dentro_da_janela(pg, "#palco")                                              # no celular o mapa ficou para cima
        y = pg.evaluate("scrollY")
        pg.click("#rw-cmd-ver-mapa")
        assert pg.evaluate("scrollY") < y and _dentro_da_janela(pg, "#map")                      # a página subiu ao mapa, de uma vez
        assert pg.evaluate("document.activeElement.id") == "map"                                 # o foco está no mapa (canvas com rótulo "Mapa do round")
        assert "O mapa está à vista." in pg.inner_text("#rw-cmd-cartao") and pg.locator("#rw-cmd-ver-mapa").count() == 0
        assert pg.get_attribute("#rw-cmd-cartao", "aria-live") == "polite" and erros == []       # o aviso vai pela região viva do cartão
    finally:
        ctx.close()


def test_ver_no_mapa_so_aparece_no_celular_e_nunca_no_computador(navegador, pagina_cmd):
    from tests.test_reescrever_comandos import _abre_secao, _aplica, _escreve
    ctx, pg, _ = _abre_no_instante(navegador, pagina_cmd, 1440, 900)
    try:
        _abre_secao(pg); _escreve(pg, "ropz corre pro meio aos 1:10"); _aplica(pg)
        assert pg.locator("#rw-cmd-ver-mapa").count() == 1 and not pg.is_visible("#rw-cmd-ver-mapa")      # existe, mas o CSS o esconde: o mapa já está ao lado
    finally:
        ctx.close()


def test_ver_no_mapa_na_prancheta_leva_a_pagina_ao_mapa_poe_o_foco_nele_e_anuncia(navegador, tmp_path_factory):
    from scripts.build_tactics_page import arquivo_da_pagina, build_html
    from tests.test_comandos_tempos import _peca, _ponto
    d = tmp_path_factory.mktemp("pr_vermapa")
    arq = d / arquivo_da_pagina("de_mirage")
    arq.write_text(build_html("de_mirage"), encoding="utf-8")
    ctx = navegador.new_context(viewport={"width": 375, "height": 812})
    pg = ctx.new_page(); erros = []
    pg.on("pageerror", lambda e: erros.append(str(e)))
    try:
        pg.goto(arq.as_uri())
        pg.wait_for_function("() => Prancheta._interno.S.estado !== null")
        base = _ponto("de_mirage", "Base TR")
        _peca(pg, base["x"], base["y"])
        pg.evaluate("() => Prancheta._interno.abaDoPainel('comandos')")
        pg.fill("#pr-cmd-texto", "tr 2 corre pro meio aos 1:30"); pg.click("#pr-cmd-entender")
        pg.wait_for_function("() => document.querySelectorAll('#pr-cmd-entendi li').length === 1")
        assert pg.locator("#pr-cmd-ver-mapa").count() == 0
        pg.click("#pr-cmd-aplicar")
        pg.wait_for_selector("#pr-cmd-ver-mapa")
        assert pg.inner_text("#pr-cmd-ver-mapa") == "Ver no mapa ↑"
        pg.locator("#pr-cmd-ver-mapa").scroll_into_view_if_needed()
        assert not _dentro_da_janela(pg, "#pr-palco")
        y = pg.evaluate("scrollY")
        pg.click("#pr-cmd-ver-mapa")
        assert pg.evaluate("scrollY") < y and _dentro_da_janela(pg, "#pr-mapa")
        assert pg.evaluate("document.activeElement.id") == "pr-mapa"
        assert "O mapa está à vista." in pg.inner_text("#pr-cmd-resultado") and pg.locator("#pr-cmd-ver-mapa").count() == 0 and erros == []
        pg.set_viewport_size({"width": 1440, "height": 900})                                    # no computador o botão fica escondido
        pg.fill("#pr-cmd-texto", "tr 2 corre pro meio aos 1:20"); pg.click("#pr-cmd-entender")
        pg.wait_for_function("() => document.querySelectorAll('#pr-cmd-entendi li').length === 1")
        pg.click("#pr-cmd-aplicar")
        assert pg.locator("#pr-cmd-ver-mapa").count() == 1 and not pg.is_visible("#pr-cmd-ver-mapa")
    finally:
        ctx.close()


# --------------------------------------------------------------------------------------------------------------------------------------------------------------------------
# o nome do time no cabeçalho da partida: "Time de <nick>" mantém a grafia do nick; os times profissionais continuam em maiúsculas
# --------------------------------------------------------------------------------------------------------------------------------------------------------------------------

@pytest.mark.parametrize("partida,esperado,transforma", [("match_01", ["Time de t1ltedbot", "Time de HLEB"], "none"), ("match_43", ["FURIA", "Vitality"], "uppercase")])
def test_o_nome_do_time_faceit_mantem_a_grafia_do_nick_e_o_profissional_segue_em_maiusculas(navegador, tmp_path_factory, partida, esperado, transforma):
    from pathlib import Path
    from scripts.build_web_page import build_html
    if not (Path(__file__).resolve().parent.parent / "data" / "processed" / partida / "web_payload.json").exists():
        pytest.skip("sem o processado")
    arq = tmp_path_factory.mktemp("cab") / f"{partida}.html"
    arq.write_text(build_html(partida), encoding="utf-8")
    ctx = navegador.new_context(viewport={"width": 1440, "height": 900})
    pg = ctx.new_page()
    try:
        pg.goto(arq.as_uri())
        r = pg.eval_on_selector_all(".placar .nome", "ns => ns.map(n => [n.textContent, getComputedStyle(n).textTransform, n.innerText])")
        assert sorted(t for t, _, _ in r) == sorted(esperado) and all(tt == transforma for _, tt, _ in r)
        assert sorted(i for _, _, i in r) == sorted(esperado if transforma == "none" else [e.upper() for e in esperado])      # o que se VÊ: a grafia do nick, ou o nome em maiúsculas
    finally:
        ctx.close()
