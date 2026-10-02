"""Demo sem `grenade_thrown` (FACEIT): o evento é reconstruído do projétil.

A regra só vale porque, onde o evento existe, a reconstrução dá o MESMO
arremesso: tick do primeiro ponto do projétil, mira e pés da tabela em t-1. O
teste de identidade roda nas partidas de campeonato com o evento retirado de
propósito (pulado sem `data/interim/`).
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import polars as pl
import pytest

import metrics.grenade_throws as gt

RAIZ = Path(__file__).resolve().parent.parent
INTERIM = RAIZ / "data" / "interim"
PROCESSED = RAIZ / "data" / "processed"

# uma demo inteira, uma em partes e a que pula ticks
PARTIDAS_COM_EVENTO = ("match_23", "match_41", "match_16")
PARTIDA_FACEIT = "match_02"
# colunas que definem o lineup e o que a ficha afirma
COLUNAS = ("tick_soltura", "pitch", "yaw", "x", "y", "z", "botao", "postura", "no_ar",
           "residuo", "reproducao_exata")
# Medido nas 43 partidas com evento (2026-10-02): 20.862 de 20.863 idênticos; o
# que difere não tem o tick t-1 na tabela.
META_IDENTIDADE = 0.999


def _tabelas(partida: str) -> dict:
    from parsing.parser import TABELAS_DA_VERDADE, load_interim
    if not (INTERIM / partida / "ticks.parquet").exists():
        pytest.skip(f"sem o interim da {partida}")
    t = load_interim(INTERIM, partida)
    t["rounds"] = pl.read_parquet(PROCESSED / partida / "rounds.parquet")
    return {k: v for k, v in t.items() if k not in TABELAS_DA_VERDADE}


def test_evento_reconstruido_usa_o_tick_do_projetil_e_a_tabela_em_t_menos_1():
    ticks = pl.DataFrame({
        "tick": [10, 11, 12], "steamid": [7, 7, 7],
        "X": [1.0, 2.0, 3.0], "Y": [0.0, 0.0, 0.0], "Z": [5.0, 5.0, 5.0],
        "pitch": [-1.0, -2.0, -3.0], "yaw": [90.0, 91.0, 92.0],
    })
    tk = gt._Ticks(ticks)
    ev = gt.evento_pelo_projetil([{"steamid": 7, "kind": "smoke", "tick_primeiro": 12}], tk)
    (e,) = ev.iter_rows(named=True)
    assert e["tick"] == 12 and e["weapon"] == "smokegrenade"
    assert (e["user_X"], e["user_pitch"], e["user_yaw"]) == (2.0, -2.0, 91.0)      # a tabela em t-1
    # sem o tick t-1 na tabela não há evento: o arremesso fica com a ancoragem
    assert gt.evento_pelo_projetil([{"steamid": 7, "kind": "smoke", "tick_primeiro": 10}], tk).height == 0


@pytest.fixture
def ligada(monkeypatch):
    """A regra está DESLIGADA na produção até o Pedro aprovar; aqui ela liga."""
    monkeypatch.setattr(gt, "TICK_PELO_PROJETIL_SEM_EVENTO", True)


def test_desligada_por_padrao_ate_a_aprovacao():
    assert gt.TICK_PELO_PROJETIL_SEM_EVENTO is False


@pytest.mark.parametrize("partida", PARTIDAS_COM_EVENTO)
def test_sem_o_evento_a_reconstrucao_da_o_mesmo_arremesso(partida, ligada):
    t = _tabelas(partida)
    real, _ = gt.grenade_throws(t, 64)
    rec, _ = gt.grenade_throws({k: v for k, v in t.items() if k != "grenade_thrown"}, 64)
    chave = ["round_num", "entity_id", "tick_primeiro"]
    j = real.filter(pl.col("fonte_tick") == "oficial").join(rec, on=chave, how="inner", suffix="_rec")
    assert j.height > 300
    # sem o tick t-1 na tabela (a match_16 pula ticks) o arremesso fica com a
    # ancoragem, declarada; a identidade é cobrada onde a regra se aplicou
    assert (j["fonte_tick_rec"] == "projetil").mean() > 0.97, partida
    j = j.filter(pl.col("fonte_tick_rec") == "projetil")
    iguais = np.ones(j.height, dtype=bool)
    for c in COLUNAS:
        a, b = j[c], j[f"{c}_rec"]
        if a.dtype.is_float():
            ok = ((a - b).abs() < 1e-3) | (a.is_null() & b.is_null())
        else:
            ok = (a == b) | (a.is_null() & b.is_null())
        iguais &= ok.fill_null(False).to_numpy()
    assert iguais.mean() >= META_IDENTIDADE, (partida, int((~iguais).sum()), j.height)


def test_faceit_usa_o_tick_do_projetil_e_desligada_volta_a_ancoragem(monkeypatch, ligada):
    t = _tabelas(PARTIDA_FACEIT)
    assert "grenade_thrown" not in t
    pr, _ = gt.grenade_throws(t, 64)
    com_tick = pr.filter(pl.col("tick_soltura").is_not_null())
    assert (com_tick["fonte_tick"] == "projetil").mean() > 0.99
    assert (com_tick["tick_soltura"] == com_tick["tick_primeiro"]).mean() > 0.99
    monkeypatch.setattr(gt, "TICK_PELO_PROJETIL_SEM_EVENTO", False)
    antes, _ = gt.grenade_throws(t, 64)
    assert set(antes["fonte_tick"].drop_nulls().unique().to_list()) == {"ancoragem"}
    # o que a regra corrige: com a ancoragem, menos arremessos fecham botão
    assert pr["botao"].is_not_null().sum() > antes["botao"].is_not_null().sum()
