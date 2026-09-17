"""
Gera a autópsia de todos os rounds da partida.

Uso:
    python -m scripts.build_breakdown match_01
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import polars as pl

from parsing.parser import kills_do_round_jogado

from metrics.round_breakdown import build_breakdowns
from metrics.timing import detect_tickrate
from scripts.build_insights import resolve_teams, side_of_team

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def build(match_id: str) -> Path:
    processed = PROJECT_ROOT / "data" / "processed" / match_id
    interim = PROJECT_ROOT / "data" / "interim" / match_id

    rounds = pl.read_parquet(processed / "rounds.parquet")
    kills = pl.read_parquet(interim / "kills.parquet")
    # mortes do tempo parado não pertencem a round nenhum (ver parsing.parser)
    kills = kills_do_round_jogado(kills, rounds)
    ticks = pl.read_parquet(interim / "ticks.parquet")
    grenades = pl.read_parquet(interim / "grenades.parquet") if (interim / "grenades.parquet").exists() else None

    team_of, _ = resolve_teams(ticks)
    # Tickrate detectado, nunca assumido: todo tempo do timeline depende dele.
    tickrate = int(detect_tickrate(rounds, ticks)["tickrate"])
    breakdowns = build_breakdowns(
        rounds, kills, ticks, grenades, team_of, side_of_team, tickrate
    )

    out = processed / "breakdown.json"
    out.write_text(json.dumps(breakdowns, ensure_ascii=False, separators=(",", ":"), default=str), encoding="utf-8")
    return out


def main() -> None:
    p = argparse.ArgumentParser(description="Gera a autópsia dos rounds da partida.")
    p.add_argument("match_id", type=str)
    args = p.parse_args()
    out = build(args.match_id)
    print(f"{out}  ({out.stat().st_size / 1024:.0f} KB)")


if __name__ == "__main__":
    main()
