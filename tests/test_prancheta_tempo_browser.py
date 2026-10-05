"""Prancheta no tempo (fase 8): interação, funções, granadas, linha do tempo e reprodução."""
from __future__ import annotations

import math

import pytest

pytest.importorskip("playwright.sync_api")

from tests.test_tactics_browser import (abre, arrasta_do_banco, contexto, interno, navegador, no_mapa,  # noqa: E402,F401
                                        pagina)


def _ops(pg, tipo=None):
    ops = interno(pg, "S.doc.operacoes")
    return [o for o in ops if tipo is None or o["tipo"] == tipo]


def _pixel_da_peca(pg, pid):
    q = interno(pg, f"I.quadroNoTempo(S.e3, S.t, I.centro()).pecas['{pid}']")
    px = interno(pg, f"I.jogoParaPixel({q['x']}, {q['y']})")
    c = pg.locator("#pr-mapa").bounding_box()
    w = interno(pg, "I.radar().width")
    return c["x"] + px[0] * c["width"] / w, c["y"] + px[1] * c["height"] / w


def _com_peca(pg):
    # o caminho por clique está pronto e desligado (CAMINHO_POR_CLIQUE): liga aqui
    interno(pg, "(I.ligaCaminhoPorClique(true), 0)")
    arrasta_do_banco(pg, "ct", "1", 0.5, 0.5)
    pid = interno(pg, "Object.keys(S.estado.pecas)[0]")
    pg.keyboard.press("Escape"); pg.keyboard.press("Escape")
    return pid


def test_arrastar_grava_ponto_no_horario_do_cabecote_e_nao_entra_em_caminho(contexto, pagina):
    pg = abre(contexto, pagina)
    pid = _com_peca(pg)
    interno(pg, "(I.defineTempo(20), 0)")
    x, y = _pixel_da_peca(pg, pid)
    pg.mouse.move(x, y); pg.mouse.down(); pg.mouse.move(x + 60, y - 40, steps=6); pg.mouse.up()
    (op,) = _ops(pg, "cria_caminho")
    assert op["peca"] == pid and len(op["pontos"]) == 1 and op["pontos"][0]["t"] == 20
    assert interno(pg, "I.estadoDaInteracao()") != "tracando_caminho"
    # no horário de um marco, arrastar é o move_peca de sempre
    interno(pg, "(I.defineTempo(0), 0)")
    x, y = _pixel_da_peca(pg, pid)
    pg.mouse.move(x, y); pg.mouse.down(); pg.mouse.move(x - 30, y + 30, steps=6); pg.mouse.up()
    assert len(_ops(pg, "move_peca")) == 1 and len(_ops(pg, "cria_caminho")) == 1


def test_clicar_na_peca_traca_caminho_e_enter_emite_um_cria_caminho(contexto, pagina):
    pg = abre(contexto, pagina)
    pid = _com_peca(pg)
    pg.mouse.click(*_pixel_da_peca(pg, pid))
    assert interno(pg, "I.estadoDaInteracao()") == "tracando_caminho"
    assert "Enter conclui" in pg.text_content("#pr-dica-estado")
    for fx, fy in ((0.55, 0.5), (0.6, 0.45), (0.6, 0.38)):
        pg.mouse.click(*no_mapa(pg, fx, fy))
    pg.keyboard.press("Enter")
    (op,) = _ops(pg, "cria_caminho")
    pts = op["pontos"]
    assert len(pts) == 3 and pts[0]["t"] < pts[1]["t"] < pts[2]["t"]
    # horários pela velocidade medida (rifle, correndo)
    v = interno(pg, "I.velocidade(null, 'correndo')")
    inicio = interno(pg, f"S.e3.pecas['{pid}'].pontos[0]")
    d = math.hypot(pts[0]["x"] - inicio["x"], pts[0]["y"] - inicio["y"])
    assert pts[0]["t"] == pytest.approx(d / v, abs=0.01)
    # a peça segue selecionada e o cabeçote foi para o fim do caminho
    assert interno(pg, "S.t") == pts[-1]["t"] and interno(pg, "S.sel.id") == pid
    # Ctrl+Z desfaz o caminho inteiro
    pg.keyboard.press("Control+z")
    assert interno(pg, f"S.e3.pecas['{pid}'].pontos.filter(p => p.caminho).length") == 0


def test_backspace_tira_o_ultimo_e_esc_cancela_o_trecho(contexto, pagina):
    pg = abre(contexto, pagina)
    pid = _com_peca(pg)
    pg.mouse.click(*_pixel_da_peca(pg, pid))
    pg.mouse.click(*no_mapa(pg, 0.55, 0.5)); pg.mouse.click(*no_mapa(pg, 0.6, 0.45))
    pg.keyboard.press("Backspace")
    assert interno(pg, "S.caminho.pontos.length") == 1
    assert interno(pg, f"!!S.estado.pecas['{pid}']")            # Backspace não apagou a peça
    pg.keyboard.press("Escape")
    assert interno(pg, "S.caminho") is None and _ops(pg, "cria_caminho") == []


def test_arrastar_no_modo_caminho_desenha_a_mao_e_simplifica(contexto, pagina):
    pg = abre(contexto, pagina)
    pid = _com_peca(pg)
    pg.mouse.click(*_pixel_da_peca(pg, pid))
    pg.mouse.move(*no_mapa(pg, 0.55, 0.55)); pg.mouse.down()
    for i in range(1, 30):
        pg.mouse.move(*no_mapa(pg, 0.55 + 0.004 * i, 0.55 + 0.0001 * (i % 2)))   # reta com tremor
    pg.mouse.up()
    n = interno(pg, "S.caminho.pontos.length")
    assert 1 <= n <= 3                              # Douglas-Peucker tirou o tremor
    pg.keyboard.press("Enter")
    assert len(_ops(pg, "cria_caminho")) == 1


def test_esperar_aqui_empurra_os_pontos_seguintes_numa_acao(contexto, pagina):
    pg = abre(contexto, pagina)
    pid = _com_peca(pg)
    pg.mouse.click(*_pixel_da_peca(pg, pid))
    for fx, fy in ((0.55, 0.5), (0.6, 0.45), (0.65, 0.4)):
        pg.mouse.click(*no_mapa(pg, fx, fy))
    pg.keyboard.press("Enter")
    antes = interno(pg, f"S.e3.pecas['{pid}'].pontos.filter(p => p.caminho).map(p => p.t)")
    primeiro = interno(pg, f"S.e3.pecas['{pid}'].pontos.filter(p => p.caminho)[0].id")
    pg.fill(f'[data-espera="{primeiro}"]', "3"); pg.press(f'[data-espera="{primeiro}"]', "Tab")
    depois = interno(pg, f"S.e3.pecas['{pid}'].pontos.filter(p => p.caminho).map(p => p.t)")
    assert depois[0] == antes[0] and depois[1:] == [round(t + 3, 2) for t in antes[1:]]
    pg.keyboard.press("Control+z")
    assert interno(pg, f"S.e3.pecas['{pid}'].pontos.filter(p => p.caminho).map(p => p.t)") == antes


def test_botao_direito_fora_do_marco_grava_yaw_no_horario(contexto, pagina):
    pg = abre(contexto, pagina)
    pid = _com_peca(pg)
    interno(pg, f"(S.sel = {{tipo: 'peca', id: '{pid}'}}, I.defineTempo(12), 0)")
    pg.mouse.click(*no_mapa(pg, 0.5, 0.2), button="right")
    (op,) = _ops(pg, "cria_caminho")
    assert op["pontos"][0]["t"] == 12 and op["pontos"][0]["yaw"] is not None
    assert _ops(pg, "gira_peca") == []


def test_desligado_o_clique_continua_movendo_no_horario_do_cabecote(contexto, pagina):
    pg = abre(contexto, pagina)
    arrasta_do_banco(pg, "ct", "1", 0.5, 0.5)
    pid = interno(pg, "S.sel.id")
    assert "tracando_caminho" not in interno(pg, "Object.keys(I.ESTADOS)")
    interno(pg, "(I.defineTempo(15), 0)")
    interno(pg, f"(S.sel = {{tipo: 'peca', id: '{pid}'}}, 0)")
    pg.mouse.click(*no_mapa(pg, 0.6, 0.55))
    (op,) = _ops(pg, "cria_caminho")
    assert op["pontos"][0]["t"] == 15 and interno(pg, "S.caminho") is None
