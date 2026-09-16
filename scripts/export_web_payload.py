"""
Exporta um único JSON compacto com tudo que o painel web consome.

Separado do dashboard Streamlit de propósito: o Streamlit é a ferramenta de
trabalho (lê os parquet direto e mostra tudo), e o painel web é a peça de
portfólio — precisa ser leve, autocontido e sem dependência de servidor.

Uso:
    python -m scripts.export_web_payload match_01
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import polars as pl

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def build(match_id: str) -> Path:
    processed = PROJECT_ROOT / "data" / "processed" / match_id
    insights = json.loads((processed / "insights.json").read_text(encoding="utf-8"))

    def rd(name: str) -> pl.DataFrame:
        return pl.read_parquet(processed / f"{name}.parquet")

    # --- heatmap: arredonda pra reduzir bytes; é textura, não medição ---
    heat = rd("heatmap_bins").select(
        pl.col("side"),
        pl.col("x").round(0).cast(pl.Int32),
        pl.col("y").round(0).cast(pl.Int32),
        pl.col("samples").cast(pl.Int32),
    )

    # --- dano por round de cada jogador, pra sparkline ---
    adr_round = rd("adr_per_round").select(["round_num", "name", "damage"])
    damage_by_player: dict[str, list[int]] = {}
    for row in adr_round.sort("round_num").iter_rows(named=True):
        damage_by_player.setdefault(row["name"], []).append(int(row["damage"]))

    kast_round = rd("kast_per_round").select(["round_num", "name", "kast_round"])
    kast_by_player: dict[str, list[int]] = {}
    for row in kast_round.sort("round_num").iter_rows(named=True):
        kast_by_player.setdefault(row["name"], []).append(int(bool(row["kast_round"])))

    clusters = rd("cluster_assignments").select(
        pl.col("cluster"),
        pl.col("name"),
        pl.col("round_num"),
        pl.col("pca_1").round(3),
        pl.col("pca_2").round(3),
        pl.col("damage").cast(pl.Int32),
    )
    cluster_profiles = rd("cluster_profiles")

    crosshair = rd("crosshair_summary").select(
        ["name", "crosshair_score", "height_score", "direction_score",
         "median_enemy_aim_error_deg", "median_prefire_match_deg"]
    )
    awp = rd("awp_summary")
    awp_rounds = rd("awp_per_round").filter(pl.col("engagement_tick").is_not_null()).select(
        ["round_num", "name", "side", "time_to_first_shot_s", "net_displacement",
         "slow_fraction", "style", "outcome", "shot_place"]
    )
    setup_dev = rd("setup_deviation")
    standard_setup = rd("standard_setup")

    payload = {
        **insights,
        "heatmap": heat.to_dicts(),
        "damage_by_player": damage_by_player,
        "kast_by_player": kast_by_player,
        "clusters": clusters.to_dicts(),
        "cluster_profiles": cluster_profiles.to_dicts(),
        "crosshair": crosshair.to_dicts(),
        "awp": awp.to_dicts(),
        "awp_rounds": awp_rounds.to_dicts(),
        "setup_deviation": setup_dev.to_dicts(),
        "standard_setup": standard_setup.to_dicts(),
    }

    out = processed / "web_payload.json"
    out.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":"), default=str), encoding="utf-8")
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description="Exporta o JSON consumido pelo painel web.")
    parser.add_argument("match_id", type=str)
    args = parser.parse_args()
    out = build(args.match_id)
    print(f"{out}  ({out.stat().st_size / 1024:.0f} KB)")


if __name__ == "__main__":
    main()
