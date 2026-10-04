"""Regras candidatas do round decisivo (fase 6, passo 6.2): funções puras, nenhuma ligada."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from metrics.decisivo_candidatas import empate_por_frase, regra_a, regra_b, regra_c, regra_d, todas
from metrics.win_probability import curva_da_partida

PROCESSED = Path(__file__).resolve().parent.parent / "data" / "processed"


def _curva(vencedores: str) -> list[dict]:
    """Curva de uma partida sintética a partir da sequência de vencedores ("AABBA...")."""
    a = b = 0
    prog = []
    for i, v in enumerate(vencedores, 1):
        a, b = a + (v == "A"), b + (v == "B")
        prog.append({"round": i, "winner_team": v, "score_a": a, "score_b": b})
    return curva_da_partida(prog).to_dicts()


VIRADA = "BBBBBBBBBBAAAAAAAAAAAAA"          # 0-10, depois 13-10 para A
LARGO = "AAAAAAAAAAAAA"                      # 13-0
EMPATADA = "AB" * 12 + "A" * 4               # 12-12 o tempo todo, A vence a prorrogação 16-12


def test_virada_tem_round_decisivo_na_regra_c_e_ele_e_o_que_cruza_os_50():
    c = regra_c(_curva(VIRADA), "A")
    assert c["round"] is not None and not c["empate"] and c["porque"].startswith("virada definitiva")
    curva = {r["round"]: r for r in _curva(VIRADA)}
    assert curva[c["round"]]["wp_a_antes"] < 0.5 <= curva[c["round"]]["wp_a_depois"]
    assert regra_d(_curva(VIRADA), "A")["round"] == c["round"]


def test_placar_largo_nao_tem_decisivo_em_a_nem_em_c():
    assert regra_a(_curva(LARGO))["round"] is None
    c = regra_c(_curva(LARGO), "A")
    assert c["round"] is None and c["porque"].startswith("sem virada")


def test_empatada_ate_o_fim_tem_maior_salto_e_empate_pela_frase():
    curva = _curva(EMPATADA)
    a = regra_a(curva)
    assert a["round"] is not None
    assert regra_d(curva, "A")["porque"].startswith(("houve virada", "sem virada"))


def test_b_nao_depende_da_escala_do_placar():
    curva = _curva(VIRADA)
    dobrada = [{**r, "wpa_abs": r["wpa_abs"] * 2} for r in curva]
    assert regra_b(curva, 1.5)["round"] == regra_b(dobrada, 1.5)["round"]


def test_empate_e_a_mesma_porcentagem_na_frase():
    assert empate_por_frase(0.1234, 0.1201) and not empate_por_frase(0.13, 0.12) and not empate_por_frase(0.1, None)


def test_a_candidata_a_reproduz_a_regra_de_producao_no_corpus():
    arquivos = sorted(PROCESSED.glob("match_*/insights.json"))
    if not arquivos:
        pytest.skip("sem o processado")
    for f in arquivos:
        d = json.loads(f.read_text(encoding="utf-8"))
        m = d["match"]
        r = todas(d["win_probability"]["curve"], "A" if m["score_a"] > m["score_b"] else "B")
        atual = d["decisive_round"]["round"] if d.get("decisive_round") else None
        assert r["A"]["round"] == atual, f.parent.name
