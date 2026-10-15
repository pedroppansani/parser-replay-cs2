"""Ponto-chave atrasado na linha do tempo da prancheta (fase 17, decisões 35 e 44).

O atraso é CALCULADO do log (posições, horários e velocidade medida da função); nunca é gravado.
Cor: `--aviso` (amarelo), nunca `--erro`. Cor nunca é a única pista: há "+2,3 s" ao lado e o
mesmo dito no `aria-label`/`title`.
"""
import json
import math

import pytest

pytest.importorskip("playwright.sync_api")

from tests.test_tactics_browser import abre, arrasta_do_banco, contexto, interno, navegador, pagina  # noqa: E402,F401


def _peca_com_caminho(pg, t_do_segundo, distancia=900):
    """Uma peça com dois pontos-chave: o segundo a `distancia` u do primeiro, no horário pedido."""
    arrasta_do_banco(pg, "ct", "1", 0.5, 0.5)
    pid = interno(pg, "Object.keys(S.estado.pecas)[0]")
    pg.keyboard.press("Escape"); pg.keyboard.press("Escape")
    q = interno(pg, f"S.e3.pecas['{pid}'].pontos[0]")
    pg.evaluate("""([pid, x, y, t1, d]) => Prancheta._interno.emiteLote([["cria_caminho", { peca: pid, pontos: [
        { t: 10, x: x, y: y, nivel: 0 }, { t: t1, x: x + d, y: y, nivel: 0 }] }]])""",
                [pid, q["x"], q["y"], t_do_segundo, distancia])
    return pid


def test_ponto_atrasado_e_amarelo_com_o_atraso_ao_lado_e_em_texto(contexto, pagina):
    pg = abre(contexto, pagina)
    pid = _peca_com_caminho(pg, 10.5)
    v = interno(pg, "I.velocidade(null, 'correndo')")
    esperado = 900 / v - 0.5
    atrasos = interno(pg, "I.atrasosDosPontos(S.e3, S.doc)")
    assert len(atrasos) == 1 and list(atrasos.values())[0] == pytest.approx(esperado, abs=1e-6)
    texto = f"{esperado:.1f}".replace(".", ",")
    marca = pg.locator(".pr-marca.atrasado")
    assert marca.count() == 1
    # preenchido em --aviso (o mesmo valor que o token resolve), nunca em --erro
    cor = marca.evaluate("e => getComputedStyle(e).backgroundColor")
    aviso = pg.evaluate("""() => { const d = document.createElement('i'); d.style.color = 'var(--aviso)';
        document.body.appendChild(d); const c = getComputedStyle(d).color; d.remove(); return c; }""")
    erro = pg.evaluate("""() => { const d = document.createElement('i'); d.style.color = 'var(--erro)';
        document.body.appendChild(d); const c = getComputedStyle(d).color; d.remove(); return c; }""")
    assert cor == aviso and cor != erro
    # o "+2,3 s" ao lado e o texto equivalente (acessibilidade: não só a cor)
    assert pg.locator(".pr-atraso").text_content() == f"+{texto} s"
    assert f"chega {texto} s atrasado" in marca.get_attribute("aria-label")
    assert f"chega {texto} s atrasado" in marca.get_attribute("title")
    assert f"{texto} s atrasado" in pg.locator("#pr-roteiro").text_content()
    # os pontos em dia não ganham nada
    todos = interno(pg, f"S.e3.pecas['{pid}'].pontos.filter(p => !p.fora).length")
    assert pg.locator(".pr-marca.ct:not(.granada)").count() == todos > 1 and pg.locator(".pr-marca.atrasado").count() == 1


def test_ponto_que_da_tempo_de_chegar_nao_e_marcado(contexto, pagina):
    pg = abre(contexto, pagina)
    v = interno(pg, "I.velocidade(null, 'correndo')")
    _peca_com_caminho(pg, 10 + 900 / v + 0.5)
    assert interno(pg, "I.atrasosDosPontos(S.e3, S.doc)") == {}
    assert pg.locator(".pr-marca.atrasado").count() == 0 and pg.locator(".pr-atraso").count() == 0


def test_o_atraso_nao_e_guardado_no_log_nem_no_json(contexto, pagina):
    pg = abre(contexto, pagina)
    _peca_com_caminho(pg, 10.5)
    antes = interno(pg, "JSON.stringify(S.doc)")
    assert pg.locator(".pr-marca.atrasado").count() == 1
    # mexer no cabeçote, redesenhar e gravar não muda o documento por um byte
    interno(pg, "(I.defineTempo(3), I.defineTempo(12), I.atualizaTudo(), 0)")
    assert interno(pg, "JSON.stringify(S.doc)") == antes
    assert "atras" not in antes.lower()
    # nenhuma operação ganhou campo de atraso: ele vem só de horário e posição, que já estão no log
    assert not any("atras" in k for o in interno(pg, "S.doc.operacoes") for k in o)
    assert not any("atras" in k for o in interno(pg, "S.doc.operacoes") for pt in o.get("pontos", []) for k in pt)
    # o mesmo log, lido do zero, devolve o mesmo atraso (função pura do log)
    a1 = interno(pg, "I.atrasosDosPontos(S.e3, S.doc)")
    a2 = interno(pg, "I.atrasosDosPontos(I.taticaNoTempo(S.doc.operacoes), S.doc)")
    assert a1 == a2 and len(a1) == 1


def test_o_modo_do_ponto_entra_na_velocidade_do_atraso(contexto, pagina):
    pg = abre(contexto, pagina)
    arrasta_do_banco(pg, "ct", "1", 0.5, 0.5)
    pid = interno(pg, "Object.keys(S.estado.pecas)[0]")
    pg.keyboard.press("Escape"); pg.keyboard.press("Escape")
    q = interno(pg, f"S.e3.pecas['{pid}'].pontos[0]")
    pg.evaluate("""([pid, x, y]) => Prancheta._interno.emiteLote([["cria_caminho", { peca: pid, pontos: [
        { t: 10, x: x, y: y, nivel: 0 }, { t: 12, x: x + 300, y: y, nivel: 0, modo: "andando" }] }]])""",
                [pid, q["x"], q["y"]])
    v = interno(pg, "I.velocidade(null, 'andando')")
    (atraso,) = interno(pg, "Object.values(I.atrasosDosPontos(S.e3, S.doc))")
    assert atraso == pytest.approx(300 / v - 2, abs=1e-6)
