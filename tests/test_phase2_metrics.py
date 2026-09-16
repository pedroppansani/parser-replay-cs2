"""
Testes das métricas autorais da Fase 2 (AWP, crosshair) e do clustering da Fase 3.

Mesma filosofia dos testes da Fase 1: dados sintéticos pequenos, escritos à mão,
pra separar "a lógica está implementada como descrita" (pego aqui) de "os
números da partida fazem sentido de jogo" (só a revisão manual responde).
"""
from __future__ import annotations

import numpy as np
import polars as pl
import pytest

from metrics.awp_metrics import (
    HOLD_MAX_DISPLACEMENT,
    PEEK_MIN_DISPLACEMENT,
    awp_rounds,
    classify_engagement_style,
    first_awp_engagements,
    resolve_engagement_outcomes,
)
from metrics.crosshair import _linear_score, add_contact_window_flag, build_pitch_reference
from metrics.map_angles import derive_entry_angles

TICKRATE = 128


def _ticks(rows: list[dict]) -> pl.DataFrame:
    schema = {
        "round_num": pl.UInt32, "tick": pl.Int32, "steamid": pl.UInt64, "name": pl.String,
        "side": pl.String, "X": pl.Float32, "Y": pl.Float32, "Z": pl.Float32,
        "active_weapon_name": pl.String, "is_scoped": pl.Boolean, "is_alive": pl.Boolean,
        "health": pl.Int32, "place": pl.String, "pitch": pl.Float32, "yaw": pl.Float32,
        "flash_duration": pl.Float32,
    }
    defaults = {
        "name": "A", "side": "ct", "Z": 0.0, "active_weapon_name": "AWP", "is_scoped": True,
        "is_alive": True, "health": 100, "place": "Middle", "pitch": 0.0, "yaw": 0.0,
        "flash_duration": 0.0,
    }
    return pl.DataFrame([{**defaults, **r} for r in rows], schema=schema)


def _straight_line_ticks(start_tick: int, n: int, step: float, steamid: int = 1) -> list[dict]:
    """Ticks consecutivos andando em linha reta no eixo X, `step` unidades por tick."""
    return [
        {"round_num": 1, "tick": start_tick + i, "steamid": steamid, "X": i * step, "Y": 0.0}
        for i in range(n)
    ]


def _engagement(tick: int, steamid: int = 1) -> pl.DataFrame:
    return pl.DataFrame(
        [{"round_num": 1, "steamid": steamid, "engagement_tick": tick}],
        schema={"round_num": pl.UInt32, "steamid": pl.UInt64, "engagement_tick": pl.Int32},
    )


# --- AWP: classificação de estilo -----------------------------------------

def test_stationary_awper_is_classified_as_hold():
    # jogador praticamente parado nos 3s antes do tiro
    ticks = _ticks(_straight_line_ticks(1000, 385, step=0.0))
    result = classify_engagement_style(_engagement(1384), ticks, tickrate=TICKRATE)
    row = result.row(0, named=True)
    assert row["net_displacement"] < HOLD_MAX_DISPLACEMENT
    assert row["style"] == "hold"
    assert row["slow_fraction"] == pytest.approx(1.0)


def test_moving_awper_is_classified_as_peek():
    # ~1.6 u/tick = ~205 u/s, velocidade de corrida com AWP
    ticks = _ticks(_straight_line_ticks(1000, 385, step=1.6))
    result = classify_engagement_style(_engagement(1384), ticks, tickrate=TICKRATE)
    row = result.row(0, named=True)
    assert row["net_displacement"] > PEEK_MIN_DISPLACEMENT
    assert row["style"] == "peek"
    assert row["slow_fraction"] == pytest.approx(0.0)


def test_jiggle_peek_counts_as_hold_not_peek():
    """Sair e voltar pro mesmo lugar é jogar um ângulo, não avançar espaço.

    É por isso que a classificação usa deslocamento LÍQUIDO e não distância
    percorrida -- esse teste trava essa decisão de design.
    """
    out = [{"round_num": 1, "tick": 1000 + i, "steamid": 1, "X": i * 2.0, "Y": 0.0} for i in range(96)]
    back = [{"round_num": 1, "tick": 1096 + i, "steamid": 1, "X": 190.0 - i * 2.0, "Y": 0.0} for i in range(96)]
    result = classify_engagement_style(_engagement(1191), _ticks(out + back), tickrate=TICKRATE)
    row = result.row(0, named=True)
    assert row["path_distance"] > 300  # andou bastante...
    assert row["net_displacement"] < HOLD_MAX_DISPLACEMENT  # ...mas voltou pro mesmo lugar
    assert row["style"] == "hold"


# --- AWP: resolução da briga ----------------------------------------------

def _kills(rows: list[dict]) -> pl.DataFrame:
    schema = {
        "round_num": pl.UInt32, "tick": pl.Int32, "attacker_steamid": pl.UInt64,
        "victim_steamid": pl.UInt64, "weapon": pl.String, "attacker_side": pl.String,
        "victim_side": pl.String,
    }
    defaults = {"weapon": "awp", "attacker_side": "ct", "victim_side": "t"}
    return pl.DataFrame([{**defaults, **r} for r in rows], schema=schema)


def test_engagement_won_when_awp_kill_follows_shot():
    kills = _kills([{"round_num": 1, "tick": 1100, "attacker_steamid": 1, "victim_steamid": 2}])
    out = resolve_engagement_outcomes(_engagement(1000), kills, tickrate=TICKRATE)
    assert out.row(0, named=True)["outcome"] == "won"


def test_engagement_lost_when_awper_dies_first():
    kills = _kills(
        [
            {"round_num": 1, "tick": 1050, "attacker_steamid": 2, "victim_steamid": 1,
             "weapon": "ak47", "attacker_side": "t", "victim_side": "ct"},
        ]
    )
    out = resolve_engagement_outcomes(_engagement(1000), kills, tickrate=TICKRATE)
    assert out.row(0, named=True)["outcome"] == "lost"


def test_missed_shot_without_death_is_no_trade_not_loss():
    """Tiro de AWP que erra mas não custa a vida não é 'perdeu a briga'.

    Separar isso importa: com AWP, muito tiro é de informação ou pra negar
    espaço, e contar como derrota infla a taxa de erro do AWPer.
    """
    out = resolve_engagement_outcomes(_engagement(1000), _kills([]), tickrate=TICKRATE)
    assert out.row(0, named=True)["outcome"] == "no_trade"


def test_kill_outside_resolution_window_does_not_count():
    # kill 10s depois do tiro é outra briga, não a resolução dessa
    kills = _kills([{"round_num": 1, "tick": 1000 + 10 * TICKRATE, "attacker_steamid": 1, "victim_steamid": 2}])
    out = resolve_engagement_outcomes(_engagement(1000), kills, tickrate=TICKRATE)
    assert out.row(0, named=True)["outcome"] == "no_trade"


def test_awp_rounds_only_counts_awp_in_hand():
    ticks = _ticks(
        [
            {"round_num": 1, "tick": 10, "steamid": 1, "X": 0.0, "Y": 0.0, "active_weapon_name": "AWP"},
            {"round_num": 1, "tick": 11, "steamid": 2, "X": 0.0, "Y": 0.0, "active_weapon_name": "AK-47"},
        ]
    )
    result = awp_rounds(ticks)
    assert result.height == 1
    assert result.row(0, named=True)["steamid"] == 1


# --- Crosshair -------------------------------------------------------------

def test_linear_score_boundaries():
    assert _linear_score(np.array([0.0]), 5.0, 20.0)[0] == pytest.approx(1.0)
    assert _linear_score(np.array([5.0]), 5.0, 20.0)[0] == pytest.approx(1.0)
    assert _linear_score(np.array([20.0]), 5.0, 20.0)[0] == pytest.approx(0.0)
    assert _linear_score(np.array([100.0]), 5.0, 20.0)[0] == pytest.approx(0.0)
    # erro negativo é tratado pelo módulo, o score usa o valor absoluto
    assert _linear_score(np.array([-20.0]), 5.0, 20.0)[0] == pytest.approx(0.0)


def test_contact_window_flag_marks_only_samples_before_contact():
    samples = pl.DataFrame(
        {
            "round_num": pl.Series([1, 1, 1], dtype=pl.UInt32),
            "steamid": pl.Series([1, 1, 1], dtype=pl.UInt64),
            "tick": pl.Series([1000, 1100, 5000], dtype=pl.Int32),
        }
    )
    shots = pl.DataFrame(
        {
            "round_num": pl.Series([1], dtype=pl.UInt32),
            "player_steamid": pl.Series([1], dtype=pl.UInt64),
            "tick": pl.Series([1110], dtype=pl.Int32),
        }
    )
    damages = pl.DataFrame(
        {
            "round_num": pl.Series([], dtype=pl.UInt32),
            "attacker_steamid": pl.Series([], dtype=pl.UInt64),
            "victim_steamid": pl.Series([], dtype=pl.UInt64),
            "tick": pl.Series([], dtype=pl.Int32),
        }
    )
    out = add_contact_window_flag(samples, shots, damages, window_seconds=1.0, tickrate=TICKRATE).sort("tick")
    flags = out["in_contact_window"].to_list()
    # tick 1000: contato em 1110 está a 110 ticks (<128) -> dentro da janela
    # tick 1100: contato em 1110 está a 10 ticks -> dentro
    # tick 5000: não há contato depois -> fora
    assert flags == [True, True, False]


def test_pitch_reference_uses_region_median():
    kills = pl.DataFrame(
        {
            "attacker_place": ["Ramp"] * 5,
            "attacker_pitch": [6.0, 7.0, 8.0, 7.0, 7.0],
            "weapon": ["ak47"] * 5,
        }
    )
    ref = build_pitch_reference(kills, min_kills=4)
    assert ref["Ramp"] == pytest.approx(7.0)


def test_pitch_reference_ignores_regions_with_few_kills():
    kills = pl.DataFrame(
        {"attacker_place": ["Ramp", "Ramp"], "attacker_pitch": [6.0, 8.0], "weapon": ["ak47", "ak47"]}
    )
    assert build_pitch_reference(kills, min_kills=4) == {}


# --- Ângulos de entrada ----------------------------------------------------

def test_derive_entry_angles_requires_minimum_sample():
    kills = pl.DataFrame(
        {
            "attacker_place": ["Alley"] * 3,
            "attacker_side": ["ct"] * 3,
            "attacker_yaw": [90.0, 92.0, 88.0],
            "weapon": ["ak47"] * 3,
        }
    )
    assert derive_entry_angles(kills, min_kills=4).height == 0
    assert derive_entry_angles(kills, min_kills=3).height == 1


def test_derive_entry_angles_separates_distinct_directions():
    # duas direções de briga bem distintas na mesma região não podem virar uma média
    kills = pl.DataFrame(
        {
            "attacker_place": ["Alley"] * 8,
            "attacker_side": ["ct"] * 8,
            "attacker_yaw": [90.0, 91.0, 89.0, 90.5, -90.0, -91.0, -89.0, -90.5],
            "weapon": ["ak47"] * 8,
        }
    )
    angles = derive_entry_angles(kills, min_kills=4)
    assert angles.height == 2
    yaws = sorted(angles["yaw"].to_list())
    assert yaws[0] == pytest.approx(-90.125, abs=1.0)
    assert yaws[1] == pytest.approx(90.125, abs=1.0)
