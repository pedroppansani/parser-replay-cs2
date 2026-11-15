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
