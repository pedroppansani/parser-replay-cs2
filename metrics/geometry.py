"""
Geometria de mira do CS2: converter pitch/yaw em direção, medir erro angular, etc.

Convenções do Source/CS2 (importante, porque errar isso inverte toda a análise de
crosshair placement):
  - `yaw`: 0° aponta pro eixo +X, cresce no sentido anti-horário. Range -180..180.
  - `pitch`: NEGATIVO é olhar pra CIMA, POSITIVO é olhar pra BAIXO (invertido em
    relação ao que a intuição matemática sugere). Range -89..89.
  - A posição (X, Y, Z) do jogador é nos PÉS, não nos olhos. A altura dos olhos em
    pé é ~64 unidades acima dos pés (agachado ~46).

Essa convenção não foi assumida: `tests/test_geometry.py` valida ela contra kills
reais da demo (no tick da kill, a mira do atacante tem que estar apontando pra
vítima -- se o sinal do pitch estivesse invertido, o erro vertical explodiria).
"""
from __future__ import annotations

import numpy as np
import polars as pl

# Altura dos olhos acima da origem do jogador (pés), em unidades do Source.
EYE_HEIGHT_STANDING = 64.0
EYE_HEIGHT_CROUCHED = 46.0

# Altura aproximada do centro da cabeça de um inimigo em pé, acima dos pés dele.
# Uso 64 (nível dos olhos) em vez de 72 (topo do crânio) porque o alvo "certo" de
# crosshair placement é a linha dos olhos, não o topo da cabeça.
HEAD_HEIGHT = 64.0


def view_vector(pitch: np.ndarray, yaw: np.ndarray) -> np.ndarray:
    """Converte pitch/yaw (graus) num vetor unitário de direção da mira.

    Retorna array shape (n, 3) com as componentes (x, y, z).
    O sinal negativo no z vem da convenção invertida do pitch (positivo = baixo).
    """
    pitch_rad = np.radians(np.asarray(pitch, dtype=float))
    yaw_rad = np.radians(np.asarray(yaw, dtype=float))
    cos_pitch = np.cos(pitch_rad)
    return np.stack(
        [
            cos_pitch * np.cos(yaw_rad),
            cos_pitch * np.sin(yaw_rad),
            -np.sin(pitch_rad),
        ],
        axis=-1,
    )


def angle_between(v1: np.ndarray, v2: np.ndarray) -> np.ndarray:
    """Ângulo (graus) entre dois conjuntos de vetores, elemento a elemento."""
    v1n = v1 / np.linalg.norm(v1, axis=-1, keepdims=True)
    v2n = v2 / np.linalg.norm(v2, axis=-1, keepdims=True)
    dot = np.clip(np.sum(v1n * v2n, axis=-1), -1.0, 1.0)
    return np.degrees(np.arccos(dot))


def yaw_difference(yaw_a: np.ndarray, yaw_b: np.ndarray) -> np.ndarray:
    """Diferença angular horizontal em graus, já normalizada pro range 0..180.

    Precisa de wrap-around porque yaw 179° e yaw -179° estão a 2° de distância,
    não a 358°.
    """
    diff = np.abs(np.asarray(yaw_a, dtype=float) - np.asarray(yaw_b, dtype=float)) % 360.0
    return np.where(diff > 180.0, 360.0 - diff, diff)


def yaw_to_target(
    from_x: np.ndarray, from_y: np.ndarray, to_x: np.ndarray, to_y: np.ndarray
) -> np.ndarray:
    """Yaw (graus) que aponta da posição A pra posição B, no plano horizontal."""
    return np.degrees(np.arctan2(np.asarray(to_y) - np.asarray(from_y), np.asarray(to_x) - np.asarray(from_x)))


def pitch_to_target(
    from_x: np.ndarray,
    from_y: np.ndarray,
    from_z: np.ndarray,
    to_x: np.ndarray,
    to_y: np.ndarray,
    to_z: np.ndarray,
) -> np.ndarray:
    """Pitch (graus, convenção do CS2) que aponta de A pra B.

    `from_z` já deve ser a altura dos OLHOS e `to_z` a altura do ALVO (cabeça),
    não as posições de pé cru -- quem chama é responsável por somar os offsets.
    """
    dx = np.asarray(to_x, dtype=float) - np.asarray(from_x, dtype=float)
    dy = np.asarray(to_y, dtype=float) - np.asarray(from_y, dtype=float)
    dz = np.asarray(to_z, dtype=float) - np.asarray(from_z, dtype=float)
    horizontal = np.sqrt(dx**2 + dy**2)
    # negativo porque pitch positivo é pra baixo no Source
    return -np.degrees(np.arctan2(dz, np.maximum(horizontal, 1e-9)))


def horizontal_distance(
    x1: np.ndarray, y1: np.ndarray, x2: np.ndarray, y2: np.ndarray
) -> np.ndarray:
    """Distância no plano XY (ignora altura)."""
    return np.sqrt(
        (np.asarray(x2, dtype=float) - np.asarray(x1, dtype=float)) ** 2
        + (np.asarray(y2, dtype=float) - np.asarray(y1, dtype=float)) ** 2
    )


def add_aim_error_columns(
    df: pl.DataFrame,
    *,
    shooter_x: str,
    shooter_y: str,
    shooter_z: str,
    shooter_pitch: str,
    shooter_yaw: str,
    target_x: str,
    target_y: str,
    target_z: str,
    eye_height: float = EYE_HEIGHT_STANDING,
    target_height: float = HEAD_HEIGHT,
    prefix: str = "",
) -> pl.DataFrame:
    """Adiciona colunas de erro de mira (total, horizontal e vertical) a um DataFrame.

    - `<prefix>aim_error_deg`: erro angular total entre a mira e a cabeça do alvo
    - `<prefix>yaw_error_deg`: só o componente horizontal
    - `<prefix>pitch_error_deg`: só o componente vertical (assinado: positivo = mira
      ACIMA da cabeça do alvo, negativo = mira abaixo). O sinal importa: mirar
      alto demais e mirar no chão são erros diferentes na prática.
    """
    sx = df[shooter_x].to_numpy().astype(float)
    sy = df[shooter_y].to_numpy().astype(float)
    sz = df[shooter_z].to_numpy().astype(float) + eye_height
    tx = df[target_x].to_numpy().astype(float)
    ty = df[target_y].to_numpy().astype(float)
    tz = df[target_z].to_numpy().astype(float) + target_height

    aim = view_vector(df[shooter_pitch].to_numpy(), df[shooter_yaw].to_numpy())
    to_target = np.stack([tx - sx, ty - sy, tz - sz], axis=-1)

    total_err = angle_between(aim, to_target)
    ideal_yaw = yaw_to_target(sx, sy, tx, ty)
    ideal_pitch = pitch_to_target(sx, sy, sz, tx, ty, tz)
    yaw_err = yaw_difference(df[shooter_yaw].to_numpy(), ideal_yaw)
    # pitch positivo = pra baixo, então (ideal - atual) positivo significa que a
    # mira está ACIMA do alvo.
    pitch_err = ideal_pitch - df[shooter_pitch].to_numpy().astype(float)

    return df.with_columns(
        pl.Series(f"{prefix}aim_error_deg", total_err),
        pl.Series(f"{prefix}yaw_error_deg", yaw_err),
        pl.Series(f"{prefix}pitch_error_deg", pitch_err),
    )
