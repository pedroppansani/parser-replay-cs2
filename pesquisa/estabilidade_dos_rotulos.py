"""Estabilidade dos rótulos de jogador no corpus (auditoria, item 4.5). Não muda nada.

Duas perguntas:
  1. a regra por somas (a que a reamostragem usa) dá os MESMOS rótulos que o
     `assign_traits` na partida inteira? Se não der, a reamostragem mede outra coisa;
  2. quantos rótulos ficam abaixo do limiar e viram "tendência", por rótulo.

Lê o processado (as tabelas por round que o `process_demo` grava).

Uso:
    py -3.12 -m pesquisa.estabilidade_dos_rotulos
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import polars as pl

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))
from metrics.player_roles import (LIMIAR_DE_TENDENCIA, TRAIT_SPECS, assign_traits,  # noqa: E402
                                  estabilidade_dos_rotulos, rotulos_na_partida_inteira)

PROCESSED = RAIZ / "data" / "processed"
TABELAS = ["trade_kills_per_round", "awp_per_round", "lurk_per_round", "anchor_per_round",
           "grenades_per_round", "adr_per_round", "structural_roles"]


def partida(d: Path) -> tuple[dict, pl.DataFrame, pl.DataFrame, dict]:
    """(outputs, features, signals, team_of) de uma partida processada."""
    outputs = {t: pl.read_parquet(d / f"{t}.parquet") for t in TABELAS if (d / f"{t}.parquet").exists()}
    signals = pl.read_parquet(d / "player_roles.parquet")
    features = pl.read_parquet(d / "cluster_features.parquet")
    return outputs, features, signals, dict(zip(signals["steamid"].to_list(), signals["team"].to_list()))


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    difere, linhas = [], []
    for d in sorted(PROCESSED.glob("match_*")):
        outputs, features, signals, team_of = partida(d)
        if "enemy_blind_por_round" not in signals.columns:
            signals = signals.with_columns(
                pl.col("steamid").replace_strict(
                    dict(features.group_by("steamid").agg(pl.col("round_num").n_unique()).iter_rows()),
                    return_dtype=pl.UInt32).alias("rounds_jogados"))
            signals = signals.with_columns(
                (pl.col("enemy_blind_seconds") / pl.col("rounds_jogados")).alias("enemy_blind_por_round"))
        if "n_rounds_ct" not in signals.columns:
            ct = pl.read_parquet(d / "anchor_summary.parquet").select("steamid", "n_rounds_ct")
            signals = signals.join(ct, on="steamid", how="left")
        tracos = assign_traits(signals)
        oficiais = set(zip(tracos["steamid"].to_list(), tracos["trait"].to_list()))
        por_somas = rotulos_na_partida_inteira(outputs, features, signals, team_of)
        if oficiais != por_somas:
            difere.append((d.name, sorted(oficiais - por_somas), sorted(por_somas - oficiais)))
        est = estabilidade_dos_rotulos(outputs, features, signals, team_of)
        linhas.append(tracos.join(est.with_columns(pl.col("steamid").cast(tracos.schema["steamid"])),
                                  on=["steamid", "trait"], how="left")
                      .with_columns(pl.col("estabilidade").fill_null(0.0), pl.lit(d.name).alias("match_id")))
    print(f"partidas em que a regra por somas difere do assign_traits: {len(difere)}")
    for m, so_oficial, so_somas in difere:
        print(f"  {m}: só no assign_traits {so_oficial}; só nas somas {so_somas}")
    t = pl.concat(linhas, how="diagonal_relaxed")
    print(f"\n{t.height} rótulos; abaixo de {LIMIAR_DE_TENDENCIA:.2f} (tendência): "
          f"{t.filter(pl.col('estabilidade') < LIMIAR_DE_TENDENCIA).height}")
    for spec in TRAIT_SPECS:
        e = t.filter(pl.col("trait") == spec.key)["estabilidade"].to_numpy()
        if len(e):
            print(f"  {spec.label:20s} {len(e):4d} rótulos | tendência {(e < LIMIAR_DE_TENDENCIA).sum():4d} "
                  f"| estabilidade: mín {e.min():.2f}, p25 {np.percentile(e, 25):.2f}, mediana {np.median(e):.2f}")
    principal = t.sort(["match_id", "steamid", "priority"]).group_by(["match_id", "steamid"], maintain_order=True).first()
    print(f"\nrótulo PRINCIPAL: {principal.height}; tendência "
          f"{principal.filter(pl.col('estabilidade') < LIMIAR_DE_TENDENCIA).height}")
    print("os 8 menos estáveis:")
    for r in t.sort("estabilidade").head(8).iter_rows(named=True):
        print(f"  {r['match_id']} {r['name']:14s} {r['label']:18s} {r['estabilidade']:.2f}  {r['evidence']}")


if __name__ == "__main__":
    main()
