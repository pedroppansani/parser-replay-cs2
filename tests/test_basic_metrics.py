"""
Testes com dados sintéticos (pequenos, escritos à mão) pra validar a LÓGICA das
métricas antes de rodar num .dem real de 200MB+. Isso separa dois tipos de erro:
"a fórmula está errada" (pego aqui, rápido) vs. "os números da minha partida
parecem estranhos" (só dá pra saber comparando com o que eu lembro do jogo).
"""
from __future__ import annotations

import polars as pl

from metrics.basic_metrics import (
    calculate_adr,
    calculate_kast,
    calculate_trade_kills,
    calculate_utility_damage,
    identify_trade_kills,
    roster_per_round,
)

TICKRATE = 128


def _ticks_df(rows: list[dict]) -> pl.DataFrame:
    schema = {
        "health": pl.Int32,
        "place": pl.String,
        "side": pl.String,
        "X": pl.Float32,
        "Y": pl.Float32,
        "Z": pl.Float32,
        "tick": pl.Int32,
        "steamid": pl.UInt64,
        "name": pl.String,
        "round_num": pl.UInt32,
    }
    defaults = {"place": "A", "X": 0.0, "Y": 0.0, "Z": 0.0}
    full_rows = [{**defaults, **r} for r in rows]
    return pl.DataFrame(full_rows, schema=schema)


def _kills_df(rows: list[dict]) -> pl.DataFrame:
    schema = {
        "round_num": pl.UInt32,
        "tick": pl.Int32,
        "attacker_steamid": pl.UInt64,
        "attacker_side": pl.String,
        "victim_steamid": pl.UInt64,
        "victim_side": pl.String,
        "assister_steamid": pl.UInt64,
    }
    defaults = {
        "assister_steamid": None,
        "attacker_side": "t",
        "victim_side": "ct",
    }
    full_rows = [{**defaults, **r} for r in rows]
    return pl.DataFrame(full_rows, schema=schema)


def _damages_df(rows: list[dict]) -> pl.DataFrame:
    defaults = {"attacker_side": "t", "victim_side": "ct", "weapon": "ak47"}
    full_rows = [{**defaults, **r} for r in rows]
    return pl.DataFrame(full_rows)


def test_trade_kill_is_detected_within_window():
    # Round 1: T1 (attacker) mata CT1 (kill A). 2s depois, CT2 mata T1 (kill B),
    # vingando o companheiro CT1. Kill B deve ser marcada como trade kill.
    kills = _kills_df(
        [
            {
                "round_num": 1,
                "tick": 1000,
                "attacker_steamid": 111,
                "attacker_side": "t",
                "victim_steamid": 222,
                "victim_side": "ct",
            },
            {
                "round_num": 1,
                "tick": 1000 + int(2 * TICKRATE),
                "attacker_steamid": 333,
                "attacker_side": "ct",
                "victim_steamid": 111,
                "victim_side": "t",
            },
        ]
    )
    flagged = identify_trade_kills(kills, trade_window_seconds=5.0, tickrate=TICKRATE)
    result = flagged.sort("tick")["is_trade_kill"].to_list()
    assert result == [False, True]


def test_trade_kill_outside_window_is_not_detected():
    # Mesma sequência, mas a vingança acontece 10s depois -- fora da janela de 5s.
    kills = _kills_df(
        [
            {
                "round_num": 1,
                "tick": 1000,
                "attacker_steamid": 111,
                "attacker_side": "t",
                "victim_steamid": 222,
                "victim_side": "ct",
            },
            {
                "round_num": 1,
                "tick": 1000 + int(10 * TICKRATE),
                "attacker_steamid": 333,
                "attacker_side": "ct",
                "victim_steamid": 111,
                "victim_side": "t",
            },
        ]
    )
    flagged = identify_trade_kills(kills, trade_window_seconds=5.0, tickrate=TICKRATE)
    assert flagged.sort("tick")["is_trade_kill"].to_list() == [False, False]


def test_trade_kill_does_not_cross_rounds():
    # Mesma sequência de novo, mas a "vingança" está em outro round -- não conta.
    kills = _kills_df(
        [
            {
                "round_num": 1,
                "tick": 9000,
                "attacker_steamid": 111,
                "attacker_side": "t",
                "victim_steamid": 222,
                "victim_side": "ct",
            },
            {
                "round_num": 2,
                "tick": 100,
                "attacker_steamid": 333,
                "attacker_side": "ct",
                "victim_steamid": 111,
                "victim_side": "t",
            },
        ]
    )
    flagged = identify_trade_kills(kills, trade_window_seconds=5.0, tickrate=TICKRATE)
    assert flagged["is_trade_kill"].to_list() == [False, False]


def test_calculate_trade_kills_summary_counts_correctly():
    kills = _kills_df(
        [
            {
                "round_num": 1,
                "tick": 1000,
                "attacker_steamid": 111,
                "attacker_side": "t",
                "victim_steamid": 222,
                "victim_side": "ct",
            },
            {
                "round_num": 1,
                "tick": 1000 + int(2 * TICKRATE),
                "attacker_steamid": 333,
                "attacker_side": "ct",
                "victim_steamid": 111,
                "victim_side": "t",
            },
        ]
    )
    roster = pl.DataFrame(
        {"round_num": [1, 1, 1], "steamid": [111, 222, 333], "name": ["A", "B", "C"], "side": ["t", "ct", "ct"]}
    )
    _, summary = calculate_trade_kills(kills, roster)
    row = summary.filter(pl.col("steamid") == 333).row(0, named=True)
    assert row["total_kills"] == 1
    assert row["total_trade_kills"] == 1
    assert row["trade_kill_pct"] == 100.0


def test_adr_excludes_friendly_fire_and_caps_overkill():
    damages = _damages_df(
        [
            # dano válido a inimigo, mas maior que a vida restante -> deve ser travado em 30
            {"round_num": 1, "attacker_steamid": 1, "victim_steamid": 2, "dmg_health": 90,
             "dmg_health_real": 30, "attacker_side": "t", "victim_side": "ct"},
            # fogo amigo -> não deve contar no ADR
            {"round_num": 1, "attacker_steamid": 1, "victim_steamid": 3, "dmg_health": 20,
             "dmg_health_real": 20, "attacker_side": "t", "victim_side": "t"},
        ]
    )
    roster = pl.DataFrame(
        {"round_num": [1, 1, 1], "steamid": [1, 2, 3], "name": ["A", "B", "C"], "side": ["t", "ct", "t"]}
    )
    per_round, summary = calculate_adr(damages, roster)
    row = summary.filter(pl.col("steamid") == 1).row(0, named=True)
    assert row["total_damage"] == 30
    assert row["adr"] == 30.0


def test_utility_damage_only_counts_grenade_weapons():
    damages = _damages_df(
        [
            {"round_num": 1, "attacker_steamid": 1, "victim_steamid": 2, "dmg_health": 50,
             "dmg_health_real": 50, "weapon": "hegrenade", "attacker_side": "t", "victim_side": "ct"},
            {"round_num": 1, "attacker_steamid": 1, "victim_steamid": 2, "dmg_health": 40,
             "dmg_health_real": 40, "weapon": "ak47", "attacker_side": "t", "victim_side": "ct"},
        ]
    )
    roster = pl.DataFrame({"round_num": [1, 1], "steamid": [1, 2], "name": ["A", "B"], "side": ["t", "ct"]})
    _, summary = calculate_utility_damage(damages, roster)
    row = summary.filter(pl.col("steamid") == 1).row(0, named=True)
    assert row["total_utility_damage"] == 50


def test_kast_true_when_only_survived():
    # Jogador não teve kill nem assist nem foi traded, mas sobreviveu o round -> conta KAST.
    ticks = _ticks_df(
        [
            {"round_num": 1, "steamid": 1, "name": "A", "side": "t", "health": 100, "tick": 100},
            {"round_num": 1, "steamid": 1, "name": "A", "side": "t", "health": 100, "tick": 200},
        ]
    )
    kills = _kills_df([])
    roster = roster_per_round(ticks)
    per_round, summary = calculate_kast(kills, ticks, roster)
    assert per_round["kast_round"].to_list() == [True]
    assert summary.row(0, named=True)["kast_pct"] == 100.0


def test_kast_false_when_died_and_not_traded():
    ticks = _ticks_df(
        [
            {"round_num": 1, "steamid": 1, "name": "A", "side": "t", "health": 100, "tick": 100},
            {"round_num": 1, "steamid": 1, "name": "A", "side": "t", "health": 0, "tick": 200},
        ]
    )
    kills = _kills_df(
        [
            {
                "round_num": 1,
                "tick": 200,
                "attacker_steamid": 99,
                "attacker_side": "ct",
                "victim_steamid": 1,
                "victim_side": "t",
            }
        ]
    )
    roster = roster_per_round(ticks)
    per_round, summary = calculate_kast(kills, ticks, roster)
    row = per_round.filter(pl.col("steamid") == 1).row(0, named=True)
    assert row["survived"] is False
    assert row["kast_round"] is False
