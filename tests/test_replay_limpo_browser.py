"""Replay mais limpo (auditoria, item 5.1): a barra de desenho abre recolhida e
os eventos ainda por vir da linha do tempo ficam legíveis."""
from __future__ import annotations

import pytest

pytest.importorskip("playwright.sync_api")

from tests.test_annotations_browser import abre, contexto, navegador, partida  # noqa: E402,F401  (fixtures)


def test_a_barra_abre_recolhida_e_o_desenhar_mostra_as_ferramentas(contexto, partida):
    pg = abre(contexto, partida)
    visiveis = pg.evaluate("""() => [...document.querySelectorAll('#anot-barra button, #anot-barra a')]
        .filter(b => b.offsetParent !== null).map(b => b.id || b.textContent)""")
    # design-B3 (§7.2): com a barra recolhida ficam à vista Desenhar, Direção, Abrir round na prancheta,
    # Tela cheia e o "?" dos atalhos; as ferramentas de desenho continuam atrás do Desenhar
    assert visiveis == ["anot-toggle", "anot-direcao", "anot-abrir-round", "anot-fs", "b-atalhos"], visiveis
    assert pg.get_attribute("#anot-toggle", "aria-expanded") == "false"
    assert not pg.is_visible('[data-ferramenta="caneta"]') and not pg.is_visible("#anot-exportar")
    pg.click("#anot-toggle")
    assert pg.get_attribute("#anot-toggle", "aria-expanded") == "true"
    assert pg.is_visible("#anot-exportar") and pg.is_visible("#anot-zoom")
    pg.click("#anot-toggle")
    assert not pg.is_visible("#anot-exportar")
    pg.close()


def test_recolhida_a_barra_cabe_numa_linha_e_o_play_aparece_sem_rolar(navegador, partida):
    """Tela de notebook (1366x768) com o quadro do replay no topo: o play tem de
    aparecer. Medido: do topo do quadro ao fim do play eram 781 px com as três
    linhas de ferramentas; recolhida, 685 px."""
    ctx = navegador.new_context(viewport={"width": 1366, "height": 768})
    pg = abre(ctx, partida)
    pg.evaluate("() => document.getElementById('palco').scrollIntoView({block: 'start'})")
    barra = pg.evaluate("() => document.getElementById('anot-barra').getBoundingClientRect().height")
    play = pg.evaluate("() => document.getElementById('play').getBoundingClientRect().bottom")
    # uma linha só: os botões passaram a ter 44 px (A5, design-B3), então a linha tem 44 + respiro
    alvo = pg.evaluate("() => document.getElementById('anot-toggle').getBoundingClientRect().height")
    assert alvo >= 44 and barra < 2 * alvo, (barra, alvo)
    assert play <= 768, play
    ctx.close()


def test_evento_ainda_por_vir_tem_opacidade_de_pelo_menos_0_6(contexto, partida):
    pg = abre(contexto, partida)
    futuros = pg.evaluate("""() => [...document.querySelectorAll('.ev:not(.past):not(.now)')]
        .map(e => parseFloat(getComputedStyle(e).opacity))""")
    assert futuros and min(futuros) >= 0.6, futuros[:5]
    pg.close()
