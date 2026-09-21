"""
Ângulos de entrada ("pré-fire angles") por região do mapa.

O problema: pra dar crédito de crosshair placement a quem pré-mira um ângulo de
entrada conhecido -- mesmo sem inimigo visível ainda, que é exatamente o que um
jogador bom faz -- é preciso saber QUAIS são esses ângulos em cada canto do mapa.

Duas fontes, nessa ordem de prioridade:

1. MANUAL_ENTRY_ANGLES (abaixo, vazio por padrão): ângulos que eu (Pedro) defino
   à mão a partir do meu conhecimento do mapa. Tem prioridade sobre os derivados.
   É AQUI que entra o meu julgamento de jogo -- ver instruções no dicionário.

2. Derivação empírica (`derive_entry_angles`): olha para onde os jogadores
   estavam mirando no momento em que efetivamente mataram alguém, agrupado por
   região do mapa e lado. A lógica: se muitas kills naquela região aconteceram
   com o atacante olhando em torno de X graus, então X graus é um ângulo de
   briga real daquela região -- e pré-mirar ali é placement correto.

Optei por derivar em vez de chutar constantes: um ângulo inventado errado é pior
que nenhum ângulo, porque ele premia placement ruim e pune o bom silenciosamente.
A derivação melhora sozinha conforme mais demos forem processadas.
"""
from __future__ import annotations

import numpy as np
import polars as pl

# Quantas kills uma região precisa ter pra gerar um ângulo derivado confiável.
# Com poucas kills o "ângulo típico" vira ruído de uma jogada isolada.
MIN_KILLS_FOR_DERIVED_ANGLE = 4

# Tolerância padrão (graus) pra considerar que a mira "bate" com um ângulo de
# entrada. 25° é largo de propósito: pré-fire não precisa estar no pixel, precisa
# estar na direção certa pro inimigo aparecer dentro do campo de reação.
DEFAULT_ANGLE_TOLERANCE_DEG = 25.0

# Raio (graus) usado pra agrupar yaws parecidos ao achar as direções de briga de
# cada região. Dois kills com yaw dentro desse raio contam como o mesmo ângulo.
YAW_CLUSTER_RADIUS_DEG = 20.0


# ---------------------------------------------------------------------------
# Override manual -- PREENCHER COM CONHECIMENTO DE JOGO
# ---------------------------------------------------------------------------
# Formato:
#   MANUAL_ENTRY_ANGLES = {
#       "de_ancient": {
#           ("BombsiteA", "ct"): [
#               {"yaw": -90.0, "tolerance": 20.0, "desc": "pré-mira do donut pra saída de main"},
#           ],
#       }
#   }
# A chave é (place, side); `place` é o nome de região que o próprio demo usa
# (ver coluna `place` nos ticks: "BombsiteA", "Alley", "Middle", "TSideLower"...).
# `yaw` segue a convenção do CS2: 0° = eixo +X, cresce no anti-horário.
#
# Dica pra preencher: rode `scripts/show_derived_angles.py` -- ele lista os
# ângulos derivados por região, e aí é só corrigir/complementar o que não bate
# com o que você sabe do mapa.
MANUAL_ENTRY_ANGLES: dict[str, dict[tuple[str, str], list[dict]]] = {}


def _circular_mean(angles_deg: np.ndarray) -> float:
    """Média de ângulos respeitando o wrap-around (a média de 179° e -179° é 180°,
    não 0°)."""
    rad = np.radians(angles_deg)
    return float(np.degrees(np.arctan2(np.sin(rad).mean(), np.cos(rad).mean())))


def _circular_distance(a: np.ndarray, b: float) -> np.ndarray:
    """Distância angular (0..180) entre um array de ângulos e um ângulo."""
    diff = np.abs(a - b) % 360.0
    return np.where(diff > 180.0, 360.0 - diff, diff)


def _find_angle_modes(yaws: np.ndarray, radius: float, min_kills: int) -> list[tuple[float, int]]:
    """Acha as direções dominantes num conjunto de yaws, por busca gulosa de moda.

    Por que não usar bins de largura fixa (a primeira versão fazia isso): um
    ângulo que cai exatamente na borda do bin tem as kills que o sustentam
    divididas entre dois bins, e aí nenhum dos dois atinge o mínimo -- o ângulo
    simplesmente desaparece. Um teste com yaws em 89/90/91° pegou esse bug.
    Aqui, cada candidato é centrado num yaw observado de verdade, então não
    existe borda artificial.
    """
    remaining = yaws.copy()
    modes: list[tuple[float, int]] = []

    while remaining.size >= min_kills:
        # o candidato com mais vizinhos dentro do raio vira a direção dominante
        counts = np.array([int((_circular_distance(remaining, y) <= radius).sum()) for y in remaining])
        best = int(np.argmax(counts))
        if counts[best] < min_kills:
            break

        member_mask = _circular_distance(remaining, remaining[best]) <= radius
        members = remaining[member_mask]
        modes.append((_circular_mean(members), int(members.size)))
        remaining = remaining[~member_mask]

    return modes


def derive_entry_angles(
    kills: pl.DataFrame,
    min_kills: int = MIN_KILLS_FOR_DERIVED_ANGLE,
    radius: float = YAW_CLUSTER_RADIUS_DEG,
) -> pl.DataFrame:
    """Deriva ângulos de briga por (place, side) a partir de onde o atacante
    estava olhando nas kills daquela região.

    Retorna uma linha por ângulo derivado, com quantas kills sustentam ele --
    a contagem fica no output justamente pra dar pra julgar se o ângulo é sólido
    ou se veio de uma amostra pequena demais.
    """
    k = kills.filter(
        pl.col("attacker_place").is_not_null()
        & pl.col("attacker_yaw").is_not_null()
        & pl.col("attacker_side").is_not_null()
        & (~pl.col("weapon").is_in(["inferno", "planted_c4", "hegrenade"]))
    )
    if k.height == 0:
        return pl.DataFrame(
            schema={
                "place": pl.String,
                "side": pl.String,
                "yaw": pl.Float64,
                "n_kills": pl.UInt32,
                "source": pl.String,
            }
        )

    rows = []
    for (place, side), group in k.group_by(["attacker_place", "attacker_side"], maintain_order=True):
        yaws = group["attacker_yaw"].to_numpy().astype(float)
        for yaw, n in _find_angle_modes(yaws, radius, min_kills):
            rows.append(
                {"place": place, "side": side, "yaw": yaw, "n_kills": n, "source": "derivado"}
            )

    if not rows:
        return pl.DataFrame(
            schema={
                "place": pl.String,
                "side": pl.String,
                "yaw": pl.Float64,
                "n_kills": pl.UInt32,
                "source": pl.String,
            }
        )

    return pl.DataFrame(
        rows,
        schema={
            "place": pl.String,
            "side": pl.String,
            "yaw": pl.Float64,
            "n_kills": pl.UInt32,
            "source": pl.String,
        },
    ).sort(["place", "side", "n_kills"], descending=[False, False, True])


def entry_angles_for_map(map_name: str, kills: pl.DataFrame) -> pl.DataFrame:
    """Ângulos de entrada finais de um mapa: manuais primeiro, derivados depois.

    Se existir ângulo manual pra uma região, ele SUBSTITUI os derivados daquela
    região (meu conhecimento de jogo ganha da estatística de uma amostra pequena).
    """
    derived = derive_entry_angles(kills)

    manual_rows = []
    for (place, side), angles in MANUAL_ENTRY_ANGLES.get(map_name, {}).items():
        for a in angles:
            manual_rows.append(
                {
                    "place": place,
                    "side": side,
                    "yaw": float(a["yaw"]),
                    "n_kills": 0,
                    "source": "manual",
                }
            )

    if not manual_rows:
        return derived

    manual = pl.DataFrame(
        manual_rows,
        schema={"place": pl.String, "side": pl.String, "yaw": pl.Float64, "n_kills": pl.UInt32, "source": pl.String},
    )
    overridden = manual.select(["place", "side"]).unique(maintain_order=True)
    derived_kept = derived.join(overridden, on=["place", "side"], how="anti")
    return pl.concat([manual, derived_kept], how="vertical")


def build_angle_lookup(angles: pl.DataFrame) -> dict[tuple[str, str], np.ndarray]:
    """Converte a tabela de ângulos num dict {(place, side): array de yaws},
    que é o formato rápido de consultar dentro do loop de amostras.
    """
    lookup: dict[tuple[str, str], np.ndarray] = {}
    for row in angles.iter_rows(named=True):
        lookup.setdefault((row["place"], row["side"]), []).append(row["yaw"])
    return {k: np.array(v, dtype=float) for k, v in lookup.items()}
