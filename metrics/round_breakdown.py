"""
Autópsia do round: o que custou o round para quem perdeu.

O que este módulo faz e o que ele NÃO faz — a distinção importa mais aqui do que
em qualquer outra métrica do projeto:

FAZ: identifica momentos OBSERVÁVEIS que a literatura competitiva associa a
perder rounds, e os coloca em ordem cronológica com a evidência de cada um:
morrer na abertura sem ser trocado, morrer isolado longe do time, o instante em
que a desvantagem numérica virou irreversível, perder sem gastar utility,
perder o pós-plant.

NÃO FAZ: dizer que a rotação foi errada, que o call foi ruim ou que o jogador
devia estar em outro lugar. Isso exige saber o que o time combinou e o que o
adversário mostrou — informação que não está no demo. O que sai daqui é
"aconteceu isto, nesta ordem, e isto costuma custar round"; o julgamento de
*por que* aconteceu é de quem entende do jogo.

Por isso cada momento vem com tick e posição: dá pra clicar e assistir no
replay em vez de confiar no rótulo.
"""
from __future__ import annotations

import numpy as np
import polars as pl

TICKRATE = 128

# Janela para considerar uma morte "trocada" — mesma do resto do projeto.
TRADE_WINDOW_SECONDS = 5.0

# Distância (unidades) até o companheiro vivo mais próximo no instante da morte.
# Acima disso, ninguém tinha como trocar: a morte foi isolada. ~600u é cerca de
# 3 segundos de corrida, o tempo típico de uma troca acontecer.
ISOLATION_DISTANCE = 600.0

# Abaixo deste valor de equipamento, o round é de economia: perder não indica
# erro de execução, e a autópsia diz isso em vez de apontar culpados.
ECO_EQUIP_VALUE = 2000


def distance_phrase(dist: float) -> str:
    """Traduz a distância até o companheiro mais próximo para linguagem de jogo.

    O número cru em unidades do Source não diz nada para quem lê ("morreu a
    1000u" não é uma frase que alguém fala sobre CS). As faixas abaixo saem da
    própria escala do jogo: ~600u é o alcance em que uma troca ainda acontece,
    e acima de ~1500u o jogador está efetivamente em outra parte do mapa.
    O valor exato continua no dado, para auditoria.
    """
    if dist < 900:
        return "longe do companheiro mais próximo"
    if dist < 1500:
        return "muito longe do time"
    return "isolado, sem ninguém por perto"


def _alive_timeline(kills: pl.DataFrame, team_of: dict[int, str]) -> list[dict]:
    """Sequência de mortes do round com a contagem de vivos depois de cada uma."""
    alive = {"A": 5, "B": 5}
    out = []
    for k in kills.sort("tick").iter_rows(named=True):
        vt = team_of.get(k["victim_steamid"])
        if vt is None:
            continue
        alive[vt] -= 1
        out.append({**k, "alive_A": alive["A"], "alive_B": alive["B"]})
    return out


def _nearest_teammate_distance(
    ticks: pl.DataFrame, round_num: int, tick: int, steamid: int, team_of: dict[int, str]
) -> float | None:
    """Distância até o companheiro vivo mais próximo no instante da morte."""
    snap = ticks.filter((pl.col("round_num") == round_num) & (pl.col("tick") == tick))
    if snap.height == 0:
        near = ticks.filter(
            (pl.col("round_num") == round_num)
            & (pl.col("tick") >= tick - 8)
            & (pl.col("tick") <= tick + 8)
        )
        if near.height == 0:
            return None
        snap = near.filter(pl.col("tick") == near["tick"][0])

    me = snap.filter(pl.col("steamid") == steamid)
    if me.height == 0:
        return None
    my_team = team_of.get(steamid)
    mates = snap.filter(
        (pl.col("steamid") != steamid)
        & pl.col("is_alive")
        & pl.col("steamid").map_elements(lambda s: team_of.get(s) == my_team, return_dtype=pl.Boolean)
    )
    if mates.height == 0:
        return None

    dx = mates["X"].to_numpy() - me["X"][0]
    dy = mates["Y"].to_numpy() - me["Y"][0]
    return float(np.min(np.sqrt(dx**2 + dy**2)))


def analyze_round(
    round_row: dict,
    kills: pl.DataFrame,
    ticks: pl.DataFrame,
    grenades: pl.DataFrame | None,
    team_of: dict[int, str],
    side_of_team,
) -> dict:
    """Monta a autópsia de um round para o time que perdeu."""
    rn = int(round_row["round_num"])
    t0 = int(round_row["freeze_end"])
    winner = "A" if round_row["winner"] == side_of_team("A", rn) else "B"
    loser = "B" if winner == "A" else "A"

    rk = kills.filter(pl.col("round_num") == rn)
    timeline = _alive_timeline(rk, team_of)
    window = TRADE_WINDOW_SECONDS * TICKRATE

    # steamid -> nick, para poder nomear quem sobrou vivo (e não só quem morreu)
    roster = ticks.filter(pl.col("round_num") == rn).group_by("steamid").agg(pl.col("name").first())
    names = {int(r["steamid"]): r["name"] for r in roster.iter_rows(named=True)}

    moments = []
    tags = []

    # --- contexto econômico: round de eco não é erro de execução ---
    loser_side = side_of_team(loser, rn)
    setup = ticks.filter(
        (pl.col("round_num") == rn) & (pl.col("tick") <= t0 + 2 * TICKRATE) & (pl.col("side") == loser_side)
    )
    equip = None
    if setup.height:
        per_player = setup.group_by("steamid").agg(pl.col("current_equip_value").max().alias("v"))
        equip = float(per_player["v"].mean() or 0)
    is_eco = equip is not None and equip < ECO_EQUIP_VALUE
    if is_eco:
        tags.append("round de economia")

    # --- morte de abertura ---
    if timeline:
        first = timeline[0]
        victim_team = team_of.get(first["victim_steamid"])
        traded = any(
            t["tick"] > first["tick"]
            and t["tick"] - first["tick"] <= window
            and t["victim_steamid"] == first["attacker_steamid"]
            for t in timeline
        )
        if victim_team == loser:
            moments.append(
                {
                    "tick": int(first["tick"]),
                    "t": round((int(first["tick"]) - t0) / TICKRATE, 1),
                    "kind": "abertura_perdida",
                    "who": first["victim_name"],
                    "by": first["attacker_name"],
                    "traded": bool(traded),
                    "x": int(round(first["victim_X"])) if first["victim_X"] is not None else None,
                    "y": int(round(first["victim_Y"])) if first["victim_Y"] is not None else None,
                    "text": "perdeu a abertura" + ("" if traded else " e ninguém trocou"),
                }
            )
            tags.append("abertura perdida" + ("" if traded else " sem troca"))

    # --- mortes sem troca e mortes isoladas ---
    untraded = 0
    for k in timeline:
        if team_of.get(k["victim_steamid"]) != loser:
            continue
        traded = any(
            t["tick"] > k["tick"]
            and t["tick"] - k["tick"] <= window
            and t["victim_steamid"] == k["attacker_steamid"]
            for t in timeline
        )
        dist = _nearest_teammate_distance(ticks, rn, int(k["tick"]), int(k["victim_steamid"]), team_of)
        isolated = dist is not None and dist > ISOLATION_DISTANCE

        if not traded:
            untraded += 1
        if not traded and isolated:
            moments.append(
                {
                    "tick": int(k["tick"]),
                    "t": round((int(k["tick"]) - t0) / TICKRATE, 1),
                    "kind": "morte_isolada",
                    "who": k["victim_name"],
                    "by": k["attacker_name"],
                    "distance": round(dist),
                    "x": int(round(k["victim_X"])) if k["victim_X"] is not None else None,
                    "y": int(round(k["victim_Y"])) if k["victim_Y"] is not None else None,
                    "text": "morreu " + distance_phrase(dist) + " — sem troca possível",
                }
            )

    if untraded >= 2:
        tags.append(str(untraded) + " mortes sem troca")

    # --- instante em que a desvantagem virou irreversível ---
    for i, k in enumerate(timeline):
        deficit_from_here = all(
            (t["alive_A"] < t["alive_B"] if loser == "A" else t["alive_B"] < t["alive_A"])
            for t in timeline[i:]
        )
        loser_alive = k["alive_A"] if loser == "A" else k["alive_B"]
        winner_alive = k["alive_B"] if loser == "A" else k["alive_A"]
        # loser_alive >= 1: a última morte do round sempre satisfaz "ficou em
        # desvantagem e não recuperou", mas dizer "ficou em 0v1" não informa
        # nada — o round já tinha acabado ali.
        if deficit_from_here and loser_alive < winner_alive and loser_alive >= 1:
            # Quem "fica em 1v2" é quem SOBROU vivo, não quem acabou de morrer.
            # Nomear a vítima da kill aqui produzia a frase errada.
            dead_so_far = {t["victim_steamid"] for t in timeline[: i + 1]}
            survivors = [
                names.get(sid, str(sid))
                for sid, tm in team_of.items()
                if tm == loser and sid not in dead_so_far
            ]
            score = str(loser_alive) + "v" + str(winner_alive)
            if len(survivors) == 1:
                who, text = survivors[0], "ficou sozinho no " + score + " e não recuperou mais"
            else:
                who, text = None, "o time ficou em " + score + " e não recuperou mais"

            moments.append(
                {
                    "tick": int(k["tick"]),
                    "t": round((int(k["tick"]) - t0) / TICKRATE, 1),
                    "kind": "virada_numerica",
                    "who": who,
                    "by": k["attacker_name"],
                    "victim": k["victim_name"],
                    "survivors": survivors,
                    "score": score,
                    "x": int(round(k["victim_X"])) if k["victim_X"] is not None else None,
                    "y": int(round(k["victim_Y"])) if k["victim_Y"] is not None else None,
                    "text": text,
                }
            )
            break

    # --- utility gasta antes de a coisa desandar ---
    if grenades is not None:
        turning = next((m for m in moments if m["kind"] == "virada_numerica"), None)
        limit = turning["tick"] if turning else 10**9
        loser_names = {p for p, t in team_of.items() if t == loser}
        thrown = grenades.filter(
            (pl.col("round_num") == rn)
            & (pl.col("tick") <= limit)
            & pl.col("thrower_steamid").is_in(list(loser_names))
        )["entity_id"].n_unique()
        if thrown == 0 and not is_eco:
            tags.append("perdeu sem gastar utility")
            moments.append(
                {
                    "tick": t0,
                    "t": 0.0,
                    "kind": "sem_utility",
                    "text": "nenhuma granada do time até a desvantagem se firmar",
                }
            )

    # --- contexto da bomba ---
    planted = round_row["bomb_plant"] is not None
    if loser_side == "t" and not planted:
        tags.append("não chegou a plantar")
        moments.append({"tick": t0, "t": 0.0, "kind": "sem_plant", "text": "o round acabou sem a bomba ser plantada"})
    if loser_side == "ct" and planted and round_row["reason"] == "bomb_exploded":
        tags.append("perdeu o pós-plant")
        moments.append(
            {
                "tick": int(round_row["bomb_plant"]),
                "t": round((int(round_row["bomb_plant"]) - t0) / TICKRATE, 1),
                "kind": "pos_plant",
                "text": "bomba plantada e retake não aconteceu",
            }
        )

    moments.sort(key=lambda m: m["tick"])

    return {
        "round": rn,
        "loser_team": loser,
        "loser_side": loser_side,
        "winner_team": winner,
        "eco": bool(is_eco),
        "equip_value": round(equip) if equip is not None else None,
        "untraded_deaths": untraded,
        "tags": tags,
        "moments": moments,
    }


def build_breakdowns(
    rounds: pl.DataFrame,
    kills: pl.DataFrame,
    ticks: pl.DataFrame,
    grenades: pl.DataFrame | None,
    team_of: dict[int, str],
    side_of_team,
) -> list[dict]:
    """Autópsia de todos os rounds da partida."""
    return [
        analyze_round(r, kills, ticks, grenades, team_of, side_of_team)
        for r in rounds.iter_rows(named=True)
    ]
