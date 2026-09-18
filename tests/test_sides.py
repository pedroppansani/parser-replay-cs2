"""
Regra de lados por round, inclusive na prorrogação.

O bug que motivou isto: a troca de lado só era conhecida no intervalo do round
12, então na prorrogação os rounds 28+ iam para o time errado. FURIA x Falcons
(PGL Cluj-Napoca 2026, Mirage) saía 17-13 -- placar impossível no CS2 -- quando
a HLTV registra 16-14.

O teste principal não confere a regra contra ela mesma: confere contra o LADO
REAL de cada jogador em cada round, em todas as partidas processadas.
"""
from __future__ import annotations

import json
from pathlib import Path

import polars as pl
import pytest

from metrics.player_roles import resolve_teams
from metrics.sides import side_of_team, team_of_side

ROOT = Path(__file__).resolve().parent.parent
INTERIM = ROOT / "data" / "interim"
PROCESSED = ROOT / "data" / "processed"


def test_prorrogacao_comeca_no_lado_do_segundo_tempo_e_troca_a_cada_3():
    lados = "".join("T" if side_of_team("A", r) == "t" else "C" for r in range(1, 37))
    assert lados == "T" * 12 + "C" * 12 + "CCC" + "TTT" + "CCC" + "TTT"


def test_team_of_side_e_o_inverso_de_side_of_team():
    for r in range(1, 40):
        for time in ("A", "B"):
            assert team_of_side(side_of_team(time, r), r) == time


def _partidas_com_ticks():
    return sorted(p.name for p in INTERIM.glob("match_*") if (p / "ticks.parquet").exists())


@pytest.mark.skipif(not _partidas_com_ticks(), reason="precisa de data/interim/ processado")
@pytest.mark.parametrize("match_id", _partidas_com_ticks())
def test_regra_bate_com_o_lado_real_dos_jogadores(match_id: str):
    ticks = pl.read_parquet(
        INTERIM / match_id / "ticks.parquet", columns=["round_num", "tick", "steamid", "name", "side"]
    )
    team_of, _ = resolve_teams(ticks)
    real = (
        ticks.sort("tick")
        .group_by(["round_num", "steamid"])
        .agg(pl.col("side").first())
        .with_columns(pl.col("steamid").replace_strict(team_of, default=None).alias("team"))
        .filter(pl.col("team") == "A")
        .group_by("round_num")
        .agg(pl.col("side").mode().first())
    )
    erradas = [
        (int(r), s) for r, s in real.iter_rows()
        if s in ("t", "ct") and s != side_of_team("A", int(r))
    ]
    assert not erradas, f"{match_id}: lado previsto errado nos rounds {erradas}"


def test_mirage_de_furia_x_falcons_fecha_16_14_como_na_hltv():
    """Âncora externa: placar publicado pela HLTV (PGL Cluj-Napoca 2026)."""
    alvo = None
    for meta in PROCESSED.glob("*/match_meta.json"):
        src = json.loads(meta.read_text(encoding="utf-8")).get("source_dem", "")
        if src.replace("\\", "/").endswith("furia-vs-falcons-m1-mirage.dem"):
            alvo = meta.parent
    if alvo is None or not (alvo / "insights.json").exists():
        pytest.skip("partida FURIA x Falcons (Mirage) não processada")
    m = json.loads((alvo / "insights.json").read_text(encoding="utf-8"))["match"]
    assert sorted([m["score_a"], m["score_b"]], reverse=True) == [16, 14]
