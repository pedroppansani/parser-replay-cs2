"""
Round de faca gravado na demo.

Caso real que motivou: Vitality x Spirit (Mirage) veio com o round de faca como
round 1. A regra de lados supõe que o round 1 é o primeiro do jogo, os lados da
faca não são os do primeiro tempo, e o placar saiu 15-9 em 24 rounds --
impossível, porque quem chega a 13 encerra o mapa.
"""
from __future__ import annotations

import json
from pathlib import Path

import polars as pl
import pytest

from metrics.sides import placar_valido as _placar_valido
from parsing.parser import remove_round_de_faca, round_de_faca

PROCESSED = Path("data/processed")


def _tabelas(armas_do_round_1: list[str]) -> dict[str, pl.DataFrame]:
    return {
        "rounds": pl.DataFrame({"round_num": [1, 2, 3], "winner": ["t", "ct", "ct"]},
                               schema_overrides={"round_num": pl.UInt32}),
        "damages": pl.DataFrame({
            "round_num": [1] * len(armas_do_round_1) + [2, 3],
            "weapon": armas_do_round_1 + ["glock", "ak47"],
        }),
        "ticks": pl.DataFrame({"round_num": [None, 1, 2, 3], "tick": [0, 10, 20, 30]}),
        "header_sem_round": pl.DataFrame({"x": [1]}),
    }


def test_round_so_de_faca_sai_e_os_seguintes_sao_renumerados():
    limpo, removeu = remove_round_de_faca(_tabelas(["knife", "knife_karambit", "knife_m9_bayonet"]))
    assert removeu
    assert limpo["rounds"]["round_num"].to_list() == [1, 2]
    assert limpo["rounds"]["winner"].to_list() == ["ct", "ct"]     # o round 1 era o da faca
    assert limpo["rounds"].schema["round_num"] == pl.UInt32          # tipo preservado
    assert limpo["damages"]["weapon"].to_list() == ["glock", "ak47"]
    # linha sem round (antes do primeiro round) fica, como estava
    assert limpo["ticks"]["round_num"].to_list() == [None, 1, 2]
    assert limpo["header_sem_round"].height == 1


def test_round_de_pistola_nao_e_confundido_com_faca():
    """Pistol round também tem facada; o que separa é existir dano de arma de fogo."""
    tabelas = _tabelas(["knife", "usp_silencer", "glock"])
    assert round_de_faca(tabelas) is None
    limpo, removeu = remove_round_de_faca(tabelas)
    assert not removeu and limpo["rounds"].height == 3


def test_round_sem_dano_nenhum_nao_e_tratado_como_faca():
    assert round_de_faca(_tabelas([])) is None


@pytest.mark.parametrize("a,b,n,ok", [
    (13, 11, 24, True), (13, 12, 25, False), (16, 14, 30, True), (19, 15, 34, True),
    (15, 9, 24, False), (16, 13, 29, True), (16, 11, 27, False), (8, 5, 13, True),
])
def test_regra_do_placar_valido(a, b, n, ok):
    assert _placar_valido(a, b, n) is ok


def test_nenhuma_partida_processada_tem_placar_impossivel():
    """A rede que pega esta classe de bug em qualquer demo nova: lado errado,
    round a mais ou a menos, demo dividida sem fundir."""
    partidas = sorted(PROCESSED.glob("match_*/insights.json"))
    if not partidas:
        pytest.skip("nenhuma partida processada")
    ruins = []
    for p in partidas:
        m = json.loads(p.read_text(encoding="utf-8"))["match"]
        n = pl.read_parquet(p.parent / "rounds.parquet").height
        if not _placar_valido(m["score_a"], m["score_b"], n):
            ruins.append(f"{p.parent.name} {m['score_a']}-{m['score_b']} em {n} rounds")
    assert not ruins, ruins
