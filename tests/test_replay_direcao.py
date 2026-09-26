"""
Direção do olhar no replay (etapa 1): o dado e a convenção.

A ponta desenhada em cada jogador sai do yaw do demo. Dois testes seguram isso:

- DADO REAL: no tick de cada kill, o yaw do matador tem que apontar para a
  vítima (`yaw_to_target`). É a mesma validação da decisão 9 (erro mediano de
  1,76° no tick da kill). O CONTROLE com o sinal invertido (-yaw) tem que errar
  muito: se ele também passasse, o teste não estaria medindo convenção nenhuma.
- EXPORT: o array `d` do replay tem um valor por quadro, no mesmo índice da
  posição, sempre em [0, 360).
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import polars as pl
import pytest

from metrics.geometry import yaw_difference, yaw_to_target

INTERIM = Path("data/interim")
PROCESSED = Path("data/processed")

# Teto do erro mediano para o teste passar. A decisão 9 mediu 1,76° no tick da
# kill; 5° é folga para regressão, não um alvo.
MAX_ERRO_MEDIANO_GRAUS = 5.0
# Piso do erro do controle invertido. Espelhar o yaw leva o matador a olhar para
# o lado oposto do eixo X na maioria das kills; abaixo disso o controle não
# separa as duas convenções.
MIN_ERRO_CONTROLE_GRAUS = 45.0


def _kills_com_yaw() -> pl.DataFrame:
    partes = []
    for d in sorted(INTERIM.glob("match_*")):
        if not ((d / "kills.parquet").exists() and (d / "ticks.parquet").exists()):
            continue
        k = pl.read_parquet(d / "kills.parquet").select(
            "tick", pl.col("attacker_steamid").cast(pl.UInt64).alias("steamid"),
            "attacker_X", "attacker_Y", "victim_X", "victim_Y",
        ).drop_nulls()
        if k.height == 0:
            continue
        t = (pl.scan_parquet(d / "ticks.parquet")
             .filter(pl.col("tick").is_in(k["tick"].unique(maintain_order=True).implode()))
             .select("tick", pl.col("steamid").cast(pl.UInt64), "yaw")
             .collect())
        partes.append(k.join(t, on=["tick", "steamid"], how="inner").with_columns(pl.lit(d.name).alias("partida")))
    return pl.concat(partes) if partes else pl.DataFrame()


@pytest.fixture(scope="module")
def kills():
    df = _kills_com_yaw()
    if df.height == 0:
        pytest.skip("sem data/interim com kills e ticks")
    return df


def _erros(df: pl.DataFrame, sinal: float) -> np.ndarray:
    alvo = yaw_to_target(df["attacker_X"].to_numpy(), df["attacker_Y"].to_numpy(),
                         df["victim_X"].to_numpy(), df["victim_Y"].to_numpy())
    return yaw_difference(sinal * df["yaw"].to_numpy(), alvo)


def test_o_yaw_do_matador_aponta_para_a_vitima_no_tick_da_kill(kills):
    erro = float(np.median(_erros(kills, 1.0)))
    assert erro < MAX_ERRO_MEDIANO_GRAUS, (
        f"erro mediano {erro:.2f}° em {kills.height} kills de {kills['partida'].n_unique()} partidas")


def test_o_controle_com_o_sinal_invertido_erra_muito(kills):
    """Se este passasse com erro pequeno, o teste acima não mediria nada."""
    controle = float(np.median(_erros(kills, -1.0)))
    assert controle > MIN_ERRO_CONTROLE_GRAUS, f"controle invertido com erro mediano de só {controle:.2f}°"


def test_o_array_d_tem_um_yaw_por_quadro_em_0_360():
    replays = sorted(PROCESSED.glob("match_*/replay.json"))
    if not replays:
        pytest.skip("nenhum replay exportado")
    for caminho in replays:
        rep = json.loads(caminho.read_text(encoding="utf-8"))
        for r in rep["rounds"]:
            for p in r["players"]:
                assert "d" in p, f"{caminho.parent.name} round {r['round']}: {p['name']} sem direção"
                assert len(p["d"]) == len(p["x"]), f"{caminho.parent.name} round {r['round']}: {p['name']}"
                assert all(isinstance(v, int) and 0 <= v < 360 for v in p["d"]), \
                    f"{caminho.parent.name} round {r['round']}: {p['name']} com yaw fora de [0, 360)"
