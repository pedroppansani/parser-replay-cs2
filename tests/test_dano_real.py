"""
Dano real com vários acertos no mesmo tick (parsing.parser.dano_real_no_mesmo_tick).

O awpy trava cada acerto na vida do INÍCIO do tick; com balins de escopeta ou
dois atiradores no mesmo tick, a soma passava da vida da vítima.
"""
from __future__ import annotations

from pathlib import Path

import polars as pl
import pytest

from parsing.parser import dano_real_no_mesmo_tick

INTERIM = Path(__file__).resolve().parent.parent / "data" / "interim"


def _danos(linhas: list[tuple[int, int, int, int, int]]) -> pl.DataFrame:
    """(tick, atacante, vítima, dmg_health, victim_health); dmg_health_real como o awpy entrega."""
    return pl.DataFrame(
        [{"round_num": 1, "tick": t, "attacker_steamid": a, "victim_steamid": v, "dmg_health": d,
          "victim_health": h, "dmg_health_real": min(d, h)} for t, a, v, d, h in linhas],
        schema_overrides={"dmg_health_real": pl.Int32},
    )


def test_balins_no_mesmo_tick_nao_passam_da_vida():
    """Caso real (apEX, MAG-7): dois balins de 79 numa vítima com 100 de vida."""
    d = dano_real_no_mesmo_tick(_danos([(10, 1, 9, 79, 100), (10, 1, 9, 79, 100)]))
    assert d["dmg_health_real"].to_list() == [79, 21]


def test_dois_atiradores_no_mesmo_tick_dividem_o_que_sobrou():
    """Caso real: torzsi tira 2 de quem tinha 15; o tiro de 109 do Spinx no mesmo tick vale 13, não 15."""
    d = dano_real_no_mesmo_tick(_danos([(10, 1, 9, 2, 15), (10, 2, 9, 109, 15)]))
    assert d["dmg_health_real"].to_list() == [2, 13]


def test_ticks_diferentes_nao_mudam():
    """Em ticks diferentes a vida do início do tick já é a certa: nada muda."""
    antes = _danos([(10, 1, 9, 27, 100), (20, 1, 9, 27, 73), (30, 1, 9, 27, 18)])
    assert dano_real_no_mesmo_tick(antes)["dmg_health_real"].to_list() == [27, 27, 18]


def test_idempotente():
    d = _danos([(10, 1, 9, 79, 100), (10, 1, 9, 79, 100), (11, 2, 8, 50, 60)])
    uma = dano_real_no_mesmo_tick(d)
    assert dano_real_no_mesmo_tick(uma).equals(uma)
    assert uma["dmg_health_real"].dtype == pl.Int32


def _partidas():
    return sorted(p.parent.name for p in INTERIM.glob("*/damages.parquet")) if INTERIM.exists() else []


@pytest.mark.parametrize("match_id", _partidas() or ["sem_interim"])
def test_no_corpus_nenhuma_vitima_toma_mais_que_a_vida_num_tick(match_id):
    """Invariante no dado GRAVADO: a soma do dano real de um tick numa vítima
    nunca passa da vida que ela tinha no início do tick. Pega interim antigo,
    gravado antes da correção."""
    if match_id == "sem_interim":
        pytest.skip("sem data/interim")
    d = pl.read_parquet(INTERIM / match_id / "damages.parquet")
    excesso = (
        d.group_by("round_num", "victim_steamid", "tick")
        .agg(pl.col("dmg_health_real").sum().alias("soma"), pl.col("victim_health").max().alias("vida"))
        .filter(pl.col("soma") > pl.col("vida"))
    )
    assert excesso.height == 0, excesso.head(5)
