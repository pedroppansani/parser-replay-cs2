"""
Testes da geometria de mira.

O teste mais importante aqui é `test_angle_convention_matches_real_kills`: ele
valida a convenção de pitch/yaw do CS2 contra os dados reais, em vez de confiar
que eu li a documentação certo. A lógica: no tick em que alguém mata, a mira do
atacante tem que estar apontando pra vítima. Se o sinal do pitch estivesse
invertido, o erro angular medido explodiria -- e o teste falharia.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import polars as pl
import pytest

from metrics.geometry import (
    add_aim_error_columns,
    angle_between,
    pitch_to_target,
    view_vector,
    yaw_difference,
    yaw_to_target,
)

INTERIM = Path(__file__).resolve().parent.parent / "data" / "interim"


def test_view_vector_yaw_zero_points_to_positive_x():
    v = view_vector(np.array([0.0]), np.array([0.0]))[0]
    assert v[0] == pytest.approx(1.0)
    assert v[1] == pytest.approx(0.0, abs=1e-9)
    assert v[2] == pytest.approx(0.0, abs=1e-9)


def test_view_vector_negative_pitch_points_up():
    # Convenção do Source: pitch NEGATIVO é olhar pra cima -> componente z positiva
    up = view_vector(np.array([-45.0]), np.array([0.0]))[0]
    down = view_vector(np.array([45.0]), np.array([0.0]))[0]
    assert up[2] > 0
    assert down[2] < 0


def test_yaw_difference_wraps_around():
    # 179° e -179° estão a 2° de distância, não a 358°
    assert yaw_difference(np.array([179.0]), np.array([-179.0]))[0] == pytest.approx(2.0)
    assert yaw_difference(np.array([10.0]), np.array([350.0]))[0] == pytest.approx(20.0)


def test_yaw_to_target_cardinal_directions():
    assert yaw_to_target(np.array([0.0]), np.array([0.0]), np.array([100.0]), np.array([0.0]))[0] == pytest.approx(0.0)
    assert yaw_to_target(np.array([0.0]), np.array([0.0]), np.array([0.0]), np.array([100.0]))[0] == pytest.approx(90.0)


def test_pitch_to_target_sign():
    # alvo acima do atirador -> pitch negativo (olhar pra cima)
    p = pitch_to_target(
        np.array([0.0]), np.array([0.0]), np.array([0.0]),
        np.array([100.0]), np.array([0.0]), np.array([100.0]),
    )[0]
    assert p < 0


def test_angle_between_orthogonal_vectors():
    v1 = np.array([[1.0, 0.0, 0.0]])
    v2 = np.array([[0.0, 1.0, 0.0]])
    assert angle_between(v1, v2)[0] == pytest.approx(90.0)


@pytest.mark.skipif(
    not (INTERIM / "match_01" / "kills.parquet").exists(),
    reason="precisa de uma demo processada em data/interim/ (rode scripts/process_demo.py)",
)
def test_angle_convention_matches_real_kills():
    """No momento da kill, a mira do atacante aponta pra vítima.

    Valida a convenção de ângulos contra dados reais. Também roda a convenção
    INVERTIDA como controle -- ela tem que ser claramente pior, senão o teste
    não estaria medindo nada.
    """
    kills = pl.read_parquet(INTERIM / "match_01" / "kills.parquet").filter(
        pl.col("attacker_X").is_not_null()
        & pl.col("attacker_pitch").is_not_null()
        & pl.col("victim_X").is_not_null()
        & (~pl.col("weapon").is_in(["inferno", "planted_c4", "hegrenade"]))
    )
    assert kills.height > 50, "amostra pequena demais pra validar"

    correct = add_aim_error_columns(
        kills,
        shooter_x="attacker_X", shooter_y="attacker_Y", shooter_z="attacker_Z",
        shooter_pitch="attacker_pitch", shooter_yaw="attacker_yaw",
        target_x="victim_X", target_y="victim_Y", target_z="victim_Z",
    )["aim_error_deg"].to_numpy()

    inverted_input = kills.with_columns((-pl.col("attacker_pitch")).alias("pitch_inv"))
    inverted = add_aim_error_columns(
        inverted_input,
        shooter_x="attacker_X", shooter_y="attacker_Y", shooter_z="attacker_Z",
        shooter_pitch="pitch_inv", shooter_yaw="attacker_yaw",
        target_x="victim_X", target_y="victim_Y", target_z="victim_Z",
    )["aim_error_deg"].to_numpy()

    # com a convenção certa, a maioria das kills tem a mira quase em cima da vítima
    assert np.median(correct) < 4.0
    assert (correct < 5.0).mean() > 0.6
    # e a convenção invertida tem que ser sensivelmente pior (o controle)
    assert np.median(inverted) > np.median(correct) * 2
