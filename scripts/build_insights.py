"""
Insights da partida: round decisivo, MVP e "carrega piano".

As três perguntas que este módulo responde não têm definição oficial no CS —
então cada uma vem com uma fórmula explícita e com os componentes dela expostos
no output. A ideia é que dê pra discordar do peso, não do fato.

Gera `data/processed/<match_id>/insights.json`, consumido pelo dashboard.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import polars as pl

from metrics.player_roles import HALFTIME_ROUND, resolve_teams

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def side_of_team(team: str, round_num: int) -> str:
    """Que lado o time joga num round (troca depois do round 12)."""
    first_half = round_num <= HALFTIME_ROUND
    if team == "A":
        return "t" if first_half else "ct"
    return "ct" if first_half else "t"


def score_progression(rounds: pl.DataFrame) -> list[dict]:
    """Placar acumulado por TIME round a round."""
    a = b = 0
    out = []
    for row in rounds.iter_rows(named=True):
        rn = row["round_num"]
        winner_team = "A" if row["winner"] == side_of_team("A", rn) else "B"
        if winner_team == "A":
            a += 1
        else:
            b += 1
        out.append(
            {
                "round": int(rn),
                "winner_team": winner_team,
                "reason": row["reason"],
                "score_a": a,
                "score_b": b,
                "bomb_planted": row["bomb_plant"] is not None,
            }
        )
    return out


# ---------------------------------------------------------------------------
# Round decisivo
# ---------------------------------------------------------------------------

def round_situations(kills: pl.DataFrame, rounds: pl.DataFrame, team_of: dict[int, str]) -> dict[int, dict]:
    """Reconstrói, round a round, como a vantagem numérica evoluiu.

    Serve pra três coisas: achar clutch (último vivo que ganha), achar virada
    em desvantagem numérica, e achar quem abriu o round.
    """
    out: dict[int, dict] = {}

    for row in rounds.iter_rows(named=True):
        rn = int(row["round_num"])
        alive = {"A": 5, "B": 5}
        rk = kills.filter(pl.col("round_num") == rn).sort("tick")

        winner_team = "A" if row["winner"] == side_of_team("A", rn) else "B"
        loser_team = "B" if winner_team == "A" else "A"

        worst_deficit = 0  # maior desvantagem numérica que o vencedor superou
        clutch_player = None
        clutch_against = 0
        opening = None

        for i, kill in enumerate(rk.iter_rows(named=True)):
            victim_team = team_of.get(kill["victim_steamid"])
            attacker_team = team_of.get(kill["attacker_steamid"])
            if i == 0 and attacker_team is not None:
                opening = {
                    "player": kill["attacker_name"],
                    "team": attacker_team,
                    "victim": kill["victim_name"],
                    "weapon": kill["weapon"],
                }
            if victim_team is None:
                continue
            alive[victim_team] -= 1

            deficit = alive[loser_team] - alive[winner_team]
            worst_deficit = max(worst_deficit, deficit)

            # clutch: vencedor ficou com 1 vivo contra 2+ e ainda ganhou
            if alive[winner_team] == 1 and alive[loser_team] >= 2 and clutch_player is None:
                survivors = set(team_of) - set(
                    rk.filter(pl.col("tick") <= kill["tick"])["victim_steamid"].to_list()
                )
                team_survivors = [s for s in survivors if team_of.get(s) == winner_team]
                if len(team_survivors) == 1:
                    sid = team_survivors[0]
                    name_row = kills.filter(pl.col("attacker_steamid") == sid)
                    clutch_player = (
                        name_row["attacker_name"][0] if name_row.height else str(sid)
                    )
                    clutch_against = alive[loser_team]

        # multikill: quem mais matou no round, quando passa de 2 kills
        by_killer: dict[str, int] = {}
        for kill in rk.iter_rows(named=True):
            if team_of.get(kill["attacker_steamid"]) and kill["attacker_name"]:
                if team_of.get(kill["attacker_steamid"]) != team_of.get(kill["victim_steamid"]):
                    by_killer[kill["attacker_name"]] = by_killer.get(kill["attacker_name"], 0) + 1
        top_killer, top_kills = (None, 0)
        if by_killer:
            top_killer, top_kills = max(by_killer.items(), key=lambda kv: kv[1])

        out[rn] = {
            "winner_team": winner_team,
            "worst_deficit_overcome": int(worst_deficit),
            "clutch_player": clutch_player,
            "clutch_against": int(clutch_against),
            "opening": opening,
            "multikill_player": top_killer if top_kills >= 3 else None,
            "multikill_count": int(top_kills) if top_kills >= 3 else 0,
        }
    return out


def pick_decisive_round(progression: list[dict], situations: dict[int, dict]) -> dict:
    """Elege o round mais importante da partida.

    Componentes, todos expostos no output pra poder discordar do peso:

    1. VIRADA NO PLACAR (peso maior): o round que desempata ou vira o placar e
       depois do qual o vencedor nunca mais perde a liderança. É o "ponto sem
       volta" — e não depende de modelo de win probability (que está fora do
       escopo do projeto justamente por precisar de um corpus grande).
    2. DESVANTAGEM NUMÉRICA SUPERADA: ganhar 2v4 vale mais que ganhar 5v3.
    3. CLUTCH: o round terminou com um jogador sozinho contra dois ou mais.
    4. PLACAR APERTADO: rounds decididos com o jogo empatado ou a um round de
       distância pesam mais que rounds de jogo já resolvido.
    """
    final = progression[-1]
    champion = "A" if final["score_a"] > final["score_b"] else "B"

    # a partir de qual round o campeão assume a liderança e nunca mais a perde
    point_of_no_return = None
    for i, p in enumerate(progression):
        lead = p["score_a"] - p["score_b"]
        if champion == "B":
            lead = -lead
        if lead > 0 and all(
            (q["score_a"] - q["score_b"] if champion == "A" else q["score_b"] - q["score_a"]) > 0
            for q in progression[i:]
        ):
            point_of_no_return = p["round"]
            break

    scored = []
    for p in progression:
        rn = p["round"]
        sit = situations.get(rn, {})
        gap_before = abs(
            (p["score_a"] - (1 if p["winner_team"] == "A" else 0))
            - (p["score_b"] - (1 if p["winner_team"] == "B" else 0))
        )

        score = 0.0
        reasons = []

        if rn == point_of_no_return:
            score += 40
            reasons.append("assumiu a liderança que não devolveu mais")
        if sit.get("worst_deficit_overcome", 0) >= 2:
            score += 12 * sit["worst_deficit_overcome"]
            reasons.append(f"virou com {sit['worst_deficit_overcome']} jogadores a menos")
        if sit.get("clutch_player"):
            score += 20
            reasons.append(f"clutch de {sit['clutch_player']} em 1v{sit['clutch_against']}")
        if sit.get("multikill_count", 0) >= 3:
            score += 6 * sit["multikill_count"]
            reasons.append(f"{sit['multikill_count']}K de {sit['multikill_player']}")
        if gap_before <= 1:
            score += 15
            reasons.append("jogo empatado ou a um round de diferença")
        if p["reason"] == "bomb_defused":
            score += 8
            reasons.append("decidido no desarme")
        elif p["reason"] == "bomb_exploded":
            score += 6
            reasons.append("decidido na explosão")

        scored.append({**p, **sit, "importance": score, "reasons": reasons})

    best = max(scored, key=lambda x: x["importance"])
    return {"decisive": best, "point_of_no_return": point_of_no_return, "all_rounds": scored}


# ---------------------------------------------------------------------------
# MVP e "carrega piano"
# ---------------------------------------------------------------------------

def _norm(df: pl.DataFrame, col: str, invert: bool = False) -> pl.Expr:
    """Normaliza uma coluna pro intervalo 0-1 dentro da partida."""
    lo, hi = df[col].min(), df[col].max()
    if lo is None or hi is None or hi == lo:
        return pl.lit(0.5)
    expr = (pl.col(col) - lo) / (hi - lo)
    return (1 - expr) if invert else expr


def build_player_indices(
    basic: dict[str, pl.DataFrame],
    crosshair: pl.DataFrame,
    position: pl.DataFrame,
    features: pl.DataFrame,
    situations: dict[int, dict],
    team_of: dict[int, str],
) -> pl.DataFrame:
    """Monta a tabela por jogador com os dois índices.

    MVP — impacto que decide rounds:
        ADR, KAST, kills de abertura e clutches. Pesos declarados abaixo.

    CARREGA PIANO — o trabalho que não aparece na súmula:
        quem toma o primeiro contato cedo, gasta utility, passa o round entrando
        em briga e morre fazendo isso, SEM a contrapartida em estatística. O
        índice cresce com o esforço e é penalizado pela recompensa — por isso
        um jogador que faz tudo isso E ainda lidera o ADR não é carrega piano,
        é só o melhor jogador em campo.
    """
    adr = basic["adr_summary"].select(["steamid", "name", "adr"])
    kast = basic["kast_summary"].select(["steamid", "kast_pct"])
    util = basic["utility_damage_summary"].select(["steamid", "total_utility_damage", "utility_damage_per_round"])
    trades = basic["trade_kills_summary"].select(["steamid", "total_kills", "total_trade_kills"])

    openings: dict[str, int] = {}
    clutches: dict[str, int] = {}
    for sit in situations.values():
        op = sit.get("opening")
        if op:
            openings[op["player"]] = openings.get(op["player"], 0) + 1
        if sit.get("clutch_player"):
            clutches[sit["clutch_player"]] = clutches.get(sit["clutch_player"], 0) + 1

    per_player_round = features.group_by(["steamid"]).agg(
        pl.col("time_of_first_contact_s").median().alias("median_first_contact_s"),
        pl.col("survived").mean().alias("survival_rate"),
    )

    ch = crosshair.select(["steamid", "crosshair_score", "frac_entering_fight"])
    pos = (
        position.group_by("steamid")
        .agg(pl.col("avg_distance_from_team").mean().alias("avg_distance_from_team"))
    )

    df = (
        adr.join(kast, on="steamid", how="left")
        .join(util, on="steamid", how="left")
        .join(trades, on="steamid", how="left")
        .join(per_player_round, on="steamid", how="left")
        .join(ch, on="steamid", how="left")
        .join(pos, on="steamid", how="left")
        .with_columns(
            pl.col("name").map_elements(lambda n: openings.get(n, 0), return_dtype=pl.Int32).alias("opening_kills"),
            pl.col("name").map_elements(lambda n: clutches.get(n, 0), return_dtype=pl.Int32).alias("clutches"),
            pl.col("steamid").map_elements(lambda s: team_of.get(s, "?"), return_dtype=pl.String).alias("team"),
        )
    )

    # --- MVP: 40% ADR, 30% KAST, 20% aberturas, 10% clutches ---
    df = df.with_columns(
        (
            0.40 * _norm(df, "adr")
            + 0.30 * _norm(df, "kast_pct")
            + 0.20 * _norm(df, "opening_kills")
            + 0.10 * _norm(df, "clutches")
        ).alias("mvp_index")
    )

    # --- Carrega piano: esforço ingrato menos recompensa estatística ---
    effort = (
        0.30 * _norm(df, "median_first_contact_s", invert=True)  # toma contato cedo
        + 0.25 * _norm(df, "utility_damage_per_round")  # gasta utility
        + 0.25 * _norm(df, "frac_entering_fight")  # vive entrando em briga
        + 0.20 * _norm(df, "survival_rate", invert=True)  # e morre fazendo isso
    )
    reward = 0.5 * _norm(df, "adr") + 0.5 * _norm(df, "kast_pct")
    df = df.with_columns(
        effort.alias("effort_index"),
        reward.alias("reward_index"),
        (effort - reward).alias("piano_index"),
    )

    return df.sort("mvp_index", descending=True)


# ---------------------------------------------------------------------------

def build(match_id: str) -> Path:
    processed = PROJECT_ROOT / "data" / "processed" / match_id
    interim = PROJECT_ROOT / "data" / "interim" / match_id

    rounds = pl.read_parquet(processed / "rounds.parquet")
    kills = pl.read_parquet(interim / "kills.parquet")
    ticks = pl.read_parquet(interim / "ticks.parquet")

    basic = {
        n: pl.read_parquet(processed / f"{n}.parquet")
        for n in [
            "adr_summary",
            "kast_summary",
            "utility_damage_summary",
            "trade_kills_summary",
            "adr_per_round",
            "kast_per_round",
        ]
    }
    crosshair = pl.read_parquet(processed / "crosshair_summary.parquet")
    ch_round = pl.read_parquet(processed / "crosshair_per_round.parquet")
    crosshair = crosshair.join(
        ch_round.group_by("steamid").agg(pl.col("frac_entering_fight").mean()),
        on="steamid",
        how="left",
    )
    position = pl.read_parquet(processed / "position_profile.parquet")
    features = pl.read_parquet(processed / "cluster_features.parquet")

    team_of, rosters = resolve_teams(ticks)
    progression = score_progression(rounds)
    situations = round_situations(kills, rounds, team_of)
    decisive = pick_decisive_round(progression, situations)
    players = build_player_indices(basic, crosshair, position, features, situations, team_of)

    meta = json.loads((processed / "match_meta.json").read_text(encoding="utf-8"))
    final = progression[-1]

    payload = {
        "match": {
            "map": meta.get("map_name"),
            "rounds": len(progression),
            "score_a": final["score_a"],
            "score_b": final["score_b"],
            "rosters": rosters,
            "halftime": HALFTIME_ROUND,
        },
        "progression": progression,
        "decisive_round": decisive["decisive"],
        "point_of_no_return": decisive["point_of_no_return"],
        "rounds_scored": decisive["all_rounds"],
        "players": players.to_dicts(),
    }

    out = processed / "insights.json"
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description="Gera os insights da partida (round decisivo, MVP, carrega piano).")
    parser.add_argument("match_id", type=str)
    args = parser.parse_args()
    print(f"Insights salvos em: {build(args.match_id)}")


if __name__ == "__main__":
    main()
