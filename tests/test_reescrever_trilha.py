"""Reescrever CR1b: a peça editada tem uma TRILHA com horário. Até o quadro em que parte ela segue o caminho REAL; dali anda em linha reta, na velocidade medida, até cada
parada; uma parada que parte no meio da anterior CORTA a anterior. Arrastar uma peça é o caso de UMA parada, no instante (a conta de antes: os testes do R2 e do R3 seguem
sem mudança). Quem edita sem arrastar (os comandos, CR1c) usa `window.__reescrever.trilha.define(nome, [{f, x, y}])`, que recusa o que o modelo não sustenta."""
from __future__ import annotations

import json
import math

import pytest

sync_api = pytest.importorskip("playwright.sync_api")

from tests.test_reescrever_modo import PARTIDA, RAIZ, ROUND, _abre, _estado, navegador, pagina  # noqa: E402,F401  (fixtures e ajudas)
from tests.test_reescrever_r3 import _arrasta  # noqa: E402

HZ = 4          # quadros gravados por segundo


def _real():
    R = json.loads((RAIZ / "data" / "processed" / PARTIDA / "replay.json").read_text(encoding="utf-8"))
    r = next(x for x in R["rounds"] if x["round"] == ROUND)
    return {p["name"]: p for p in r["players"]}, r


def _define(pg, nome, paradas):
    return pg.evaluate("([n, ps]) => window.__reescrever.trilha.define(n, ps)", [nome, paradas])


def _peca(pg, nome):
    return next(p for p in _estado(pg)["pecas"] if p["nome"] == nome)


def _viva_ate_depois(jogadores, t0, ate):
    """Um jogador vivo no instante e ainda vivo em `ate` (para a peça partir sem já estar morta no real)."""
    return next(n for n, p in jogadores.items() if p["alive"][t0] and p["alive"][ate])


def _toca_ate(pg, quadro):
    pg.click("#play")
    pg.wait_for_function("q => window.__reescrever().quadro >= q", arg=quadro, timeout=30000)
    pg.click("#play")
    pg.wait_for_timeout(120)


def test_arrastar_e_uma_parada_no_instante_com_a_conta_de_antes(navegador, pagina):
    ctx, pg, erros = _abre(navegador, pagina, 1440, 900)
    try:
        pg.click("#rw-entrar")
        nome = _arrasta(pg)
        est = _estado(pg); p = _peca(pg, nome)
        assert p["editada"] and p["trilha"] == [{"f": est["instante"], "x": p["x"], "y": p["y"]}]          # UMA parada, em t0, onde se soltou
        assert p["partida"] == est["instante"] and len(p["trechos"]) == 1
        t = p["trechos"][0]
        assert (t["ax"], t["ay"]) == (p["x0"], p["y0"])                                                    # parte do ponto do real no instante
        assert abs(t["d"] - math.hypot(p["x"] - p["x0"], p["y"] - p["y0"])) < 1e-6
        assert abs(t["dur"] - t["d"] / p["velocidade"]) < 1e-9 and abs(t["f1"] - (est["instante"] + t["dur"] * HZ)) < 1e-9
        pg.click("#rw-voltar")
        p = _peca(pg, nome)
        assert not p["editada"] and p["trilha"] == [] and p["trechos"] == [] and p["partida"] is None     # "Voltar ao real" apaga a trilha
        assert erros == []
    finally:
        ctx.close()


def test_a_trilha_segue_o_real_ate_partir_e_depois_anda_na_velocidade_medida_e_para_na_ultima_parada(navegador, pagina):
    jogadores, _ = _real()
    ctx, pg, erros = _abre(navegador, pagina, 1440, 900)
    try:
        pg.click("#rw-entrar")
        t0 = _estado(pg)["instante"]
        f0 = t0 + 4                                                                                        # parte 1 s depois do instante
        nome = _viva_ate_depois(jogadores, t0, f0 + 60)
        a = jogadores[nome]
        alvo = {"f": f0, "x": a["x"][f0] + 300, "y": a["y"][f0]}
        assert _define(pg, nome, [alvo]) is True
        p = _peca(pg, nome)
        assert p["editada"] and p["partida"] == f0 and p["trilha"] == [alvo]
        t = p["trechos"][0]
        assert (t["ax"], t["ay"]) == (a["x"][f0], a["y"][f0])                                              # parte do ponto do REAL no quadro em que parte, não do instante
        pg.click("#play"); pg.wait_for_timeout(60)
        antes = _estado(pg)
        assert antes["quadro"] < f0 and _peca(pg, nome)["agora"] is None                                    # antes de partir é o real (o replay a desenha como sempre)
        pg.click("#play")
        _toca_ate(pg, f0 + 8)
        est = _estado(pg); p = _peca(pg, nome)
        decorrido = (est["quadro"] - f0) / HZ
        andou = math.hypot(p["agora"][0] - t["ax"], p["agora"][1] - t["ay"])
        assert abs(andou - min(t["d"], p["velocidade"] * decorrido)) < 1.5                                  # velocidade medida, em linha reta, a partir de f0
        assert erros == []
    finally:
        ctx.close()


def test_a_segunda_parada_corta_a_primeira_onde_a_peca_esta_e_segue_dali(navegador, pagina):
    jogadores, _ = _real()
    ctx, pg, erros = _abre(navegador, pagina, 1440, 900)
    try:
        pg.click("#rw-entrar")
        t0 = _estado(pg)["instante"]
        f0, f1 = t0 + 2, t0 + 6                                                                            # a segunda parte antes de a peça chegar na primeira
        nome = _viva_ate_depois(jogadores, t0, f1 + 60)
        a = jogadores[nome]
        p1 = {"f": f0, "x": a["x"][f0] + 1500, "y": a["y"][f0]}
        p2 = {"f": f1, "x": a["x"][f0], "y": a["y"][f0] + 600}
        assert _define(pg, nome, [p1, p2]) is True
        p = _peca(pg, nome); v = p["velocidade"]
        t1, t2 = p["trechos"]
        assert t1["f1"] > f1 and p["partida"] == f0                                                        # a primeira corrida ainda não tinha acabado: é cortada
        andou = min(t1["d"], v * (f1 - f0) / HZ)
        esperado = (t1["ax"] + (t1["bx"] - t1["ax"]) * andou / t1["d"], t1["ay"] + (t1["by"] - t1["ay"]) * andou / t1["d"])
        assert t2["f0"] == f1 and abs(t2["ax"] - esperado[0]) < 1e-6 and abs(t2["ay"] - esperado[1]) < 1e-6    # o caminho novo segue de onde a peça estava
        assert (t2["bx"], t2["by"]) == (p2["x"], p2["y"]) and (p["x"], p["y"]) == (p2["x"], p2["y"])      # a última parada é o que se mostra parado
        mudou = pg.locator("#rw-mudou li").all_inner_texts()
        assert sum(1 for t in mudou if t.startswith(nome + " sai")) == 2                                    # "O que mudou": um item por trecho
        assert erros == []
    finally:
        ctx.close()


def test_o_que_o_real_fez_antes_de_a_peca_partir_nao_e_diferenca(navegador, pagina):
    """A granada que o jogador jogou ANTES de partir é igual nas duas versões: só entra no "só no real" e em "O que mudou" a de depois da partida."""
    jogadores, r = _real()
    ctx, pg, erros = _abre(navegador, pagina, 1440, 900)
    try:
        pg.click("#rw-entrar")
        t0 = _estado(pg)["instante"]
        alvo = next(((n["by"], n) for n in r["nades"] if t0 + 8 < n["f0"] < 300 and jogadores[n["by"]]["alive"][int(n["f0"]) + 2] and jogadores[n["by"]]["alive"][t0]), None)
        assert alvo, "o round 23 tem granada de quem está vivo depois dela"
        nome, n = alvo
        tarde = int(n["f0"]) + 2
        a = jogadores[nome]
        assert _define(pg, nome, [{"f": t0, "x": a["x"][t0] + 300, "y": a["y"][t0]}]) is True              # parte já no instante: a granada de depois é só do real
        cedo = (_estado(pg)["soNoReal"], len(pg.locator("#rw-mudou li").all_inner_texts()))
        assert _define(pg, nome, [{"f": tarde, "x": a["x"][tarde] + 300, "y": a["y"][tarde]}]) is True     # parte depois de a granada sair: ela fica igual nos dois
        tardia = (_estado(pg)["soNoReal"], len(pg.locator("#rw-mudou li").all_inner_texts()))
        assert tardia[0] < cedo[0] and tardia[1] < cedo[1], (cedo, tardia)
        assert erros == []
    finally:
        ctx.close()


def test_a_morte_do_real_depois_de_partir_fica_so_no_real_e_a_peca_esmaece(navegador, pagina):
    jogadores, r = _real()
    ctx, pg, erros = _abre(navegador, pagina, 1440, 900)
    try:
        pg.click("#rw-entrar")
        t0 = _estado(pg)["instante"]
        morte = next(e for e in r["events"] if e["type"] == "kill" and e["f"] > t0 + 20 and jogadores[e["victim"]]["alive"][t0])
        nome, f0 = morte["victim"], t0 + 4
        a = jogadores[nome]
        assert _define(pg, nome, [{"f": f0, "x": a["x"][f0] + 300, "y": a["y"][f0]}]) is True
        assert any("morreu para" in t and t.startswith("No real, " + nome) for t in pg.locator("#rw-mudou li").all_inner_texts())     # o aviso da D3, como no arrastar
        _toca_ate(pg, math.ceil(morte["f"]) + 2)
        assert nome in _estado(pg)["esmaecidas"]                                                             # depois da morte do real a peça editada fica esmaecida
        assert erros == []
    finally:
        ctx.close()


def test_define_recusa_o_que_o_modelo_nao_sustenta_e_nao_deixa_rastro(navegador, pagina):
    jogadores, r = _real()
    ctx, pg, erros = _abre(navegador, pagina, 1440, 900)
    try:
        pg.click("#rw-entrar")
        est = _estado(pg); t0 = est["instante"]
        vivo = next(p for p in est["pecas"] if p["editavel"])["nome"]
        morto = next((p["nome"] for p in est["pecas"] if not p["editavel"]), None)
        a = jogadores[vivo]
        ok = {"f": t0 + 4, "x": a["x"][t0 + 4] + 300, "y": a["y"][t0 + 4]}
        ruins = [
            (vivo, []),                                                                                      # sem parada
            (vivo, [dict(ok, f=t0 - 1)]),                                                                    # antes do instante: o real não muda
            (vivo, [dict(ok, f=10 ** 6)]),                                                                   # depois do fim do round
            (vivo, [dict(ok, f=float("nan"))]),
            (vivo, [dict(ok, x=None)]),
            (vivo, [ok, dict(ok, f=ok["f"], x=ok["x"] + 50)]),                                               # fora de ordem (mesmo quadro)
            (vivo, [dict(ok, x=a["x"][t0 + 4] + 2, y=a["y"][t0 + 4])]),                                      # menos de 8 u do real: não é edição
            ("ninguém", [ok]),
        ] + ([(morto, [ok])] if morto else [])                                                               # quem já morreu só existe no real (D3)
        for nome, paradas in ruins:
            assert _define(pg, nome, paradas) is False, (nome, paradas)
        assert all(p["trilha"] == [] and not p["editada"] for p in _estado(pg)["pecas"])
        assert _define(pg, vivo, [ok]) is True and _peca(pg, vivo)["editada"]
        # com a sua versão tocando nada é editável
        pg.click("#play"); pg.wait_for_timeout(200)
        assert _define(pg, vivo, [dict(ok, x=ok["x"] + 100)]) is False
        assert erros == []
    finally:
        ctx.close()


def test_sair_e_entrar_de_novo_nao_guardam_a_trilha(navegador, pagina):
    jogadores, _ = _real()
    ctx, pg, erros = _abre(navegador, pagina, 1440, 900)
    try:
        pg.click("#rw-entrar")
        t0 = _estado(pg)["instante"]
        nome = _viva_ate_depois(jogadores, t0, t0 + 40)
        a = jogadores[nome]
        assert _define(pg, nome, [{"f": t0 + 4, "x": a["x"][t0 + 4] + 300, "y": a["y"][t0 + 4]}]) is True
        pg.click("#rw-sair"); pg.click("#rw-descartar")
        pg.click("#rw-entrar")
        assert all(p["trilha"] == [] and not p["editada"] and p["trechos"] == [] for p in _estado(pg)["pecas"])
        assert erros == []
    finally:
        ctx.close()
