"""
Exporta o replay simplificado: trajetórias, kills e eventos de bomba por round.

É o insumo da aba de replay do painel — o "replay simplificado de rounds
específicos" previsto na Fase 3. A ideia não é recriar o jogo, é conseguir
responder "o que aconteceu naquele round?" sem abrir o CS2.

Amostragem: uma posição a cada 32 ticks (4 por segundo a 128 tick). É suave o
bastante pra leitura de movimento e mantém o arquivo pequeno — o painel precisa
ser autocontido, sem servidor.

Uso:
    python -m scripts.export_replay match_01
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import polars as pl

from metrics.grenades import EFFECTIVE_BLIND_SECONDS, PROJECTILE_KIND

PROJECT_ROOT = Path(__file__).resolve().parent.parent

SAMPLE_EVERY = 32  # ticks
TICKRATE = 128
HALFTIME_ROUND = 12

# Quanto o replay continua depois de a vitória ser decidida, pra a última morte
# e o desarme caberem na linha do tempo.
TAIL_TICKS = int(4.0 * TICKRATE)
# Folga antes do começo oficial do próximo round, onde os jogadores já foram
# teleportados pro spawn.
RESET_MARGIN_TICKS = int(1.5 * TICKRATE)

SMOKE_TICKS = int(20.0 * TICKRATE)
INFERNO_TICKS = int(7.03125 * TICKRATE)

# Folga pra casar o dano de HE com a detonação que o causou. O demo registra o
# player_hurt no mesmo tick na maioria das vezes, mas vítimas processadas no
# tick seguinte aparecem alguns ticks depois.
POP_DAMAGE_TICKS = int(0.5 * TICKRATE)


def map_levels(map_name: str) -> list[dict]:
    """Andares do mapa, na ordem em que o radar os empilha.

    Vem do `verticalsections` do próprio overview da Valve (extraído por
    scripts/extract_radars.py). Mapas de um andar só devolvem um nível, e aí o
    replay nem grava a coluna.

    Isso existe por causa da Nuke: A fica em cima de B, então num mapa 2D os
    dois sites se sobrepõem. Sem separar por altura, dois jogadores em andares
    diferentes aparecem colados no mesmo ponto.
    """
    meta_path = PROJECT_ROOT / "assets" / "radars" / f"{map_name}.json"
    if not meta_path.exists():
        return [{"name": "default", "min": -1e9, "max": 1e9}]

    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    sections = meta.get("vertical_sections")
    if not sections:
        return [{"name": "default", "min": -1e9, "max": 1e9}]

    # "default" primeiro (é a imagem principal do radar), depois os demais de
    # cima para baixo
    ordered = sorted(
        ({"name": k, "min": v["min"], "max": v["max"]} for k, v in sections.items()),
        key=lambda s: (s["name"] != "default", -s["max"]),
    )
    return ordered


def level_of(z: float | None, levels: list[dict]) -> int:
    if z is None or len(levels) == 1:
        return 0
    for i, lv in enumerate(levels):
        if lv["min"] <= z < lv["max"]:
            return i
    return 0


def team_of_side(side: str, round_num: int) -> str:
    """Time real a partir do lado e do round (os lados trocam no intervalo)."""
    first_half = round_num <= HALFTIME_ROUND
    if side == "t":
        return "A" if first_half else "B"
    return "B" if first_half else "A"


def build(match_id: str) -> Path:
    processed = PROJECT_ROOT / "data" / "processed" / match_id
    interim = PROJECT_ROOT / "data" / "interim" / match_id

    map_name = json.loads((processed / "match_meta.json").read_text(encoding="utf-8"))["map_name"]
    levels = map_levels(map_name)

    rounds = pl.read_parquet(processed / "rounds.parquet")
    ticks = pl.read_parquet(interim / "ticks.parquet")
    kills = pl.read_parquet(interim / "kills.parquet")
    def opt(name: str) -> pl.DataFrame | None:
        path = interim / f"{name}.parquet"
        return pl.read_parquet(path) if path.exists() else None

    bomb = opt("bomb")
    smokes = opt("smokes")
    infernos = opt("infernos")
    grenades = opt("grenades")
    damages = opt("damages")
    blinds_all = opt("player_blind")
    flash_det = opt("flashbang_detonate")
    he_det = opt("hegrenade_detonate")

    out_rounds = []

    for r in rounds.iter_rows(named=True):
        rn = int(r["round_num"])
        t0 = int(r["freeze_end"])

        # `end` é o tick em que a vitória é decidida, não o instante em que a
        # última coisa acontece: a morte que fecha o round cai fracionariamente
        # depois dele, e cortar ali deixava jogador aparecendo vivo num round
        # que já tinha acabado. Estendemos alguns segundos, sem chegar no
        # `official_end` — lá os jogadores já foram teleportados pro spawn do
        # round seguinte, e isso apareceria como um salto no mapa.
        t_decided = int(r["end"])
        hard_stop = int(r["official_end"]) - RESET_MARGIN_TICKS if r["official_end"] is not None else None
        t1 = t_decided + TAIL_TICKS
        if hard_stop is not None:
            t1 = min(t1, max(t_decided, hard_stop))

        frames = list(range(t0, t1 + 1, SAMPLE_EVERY))
        if len(frames) < 2:
            continue

        rt = ticks.filter(
            (pl.col("round_num") == rn) & (pl.col("tick") >= t0) & (pl.col("tick") <= t1)
        ).select(
            ["tick", "steamid", "name", "side", "X", "Y", "Z", "is_alive", "health",
             "active_weapon_name", "place"]
        )

        # Armas e áreas viram índices num dicionário do round: repetir a string
        # em cada frame de cada jogador multiplicaria o tamanho do arquivo à toa.
        weapon_names: list[str] = []
        weapon_idx: dict[str, int] = {}
        place_names: list[str] = []
        place_idx: dict[str, int] = {}

        def interned(value: str | None, names: list[str], idx: dict[str, int]) -> int:
            if not value:
                return -1
            if value not in idx:
                idx[value] = len(names)
                names.append(value)
            return idx[value]

        players = []
        for (sid,), g in rt.group_by(["steamid"], maintain_order=True):
            g = g.sort("tick")
            gt = g["tick"].to_list()
            gx = g["X"].to_list()
            gy = g["Y"].to_list()
            gz = g["Z"].to_list()
            ga = g["is_alive"].to_list()
            gh = g["health"].to_list()
            gw = g["active_weapon_name"].to_list()
            gp = g["place"].to_list()

            xs, ys, alive, hp, wp, pl_, lv = [], [], [], [], [], [], []
            j = 0
            for f in frames:
                # avança até a amostra mais próxima sem passar do frame
                while j + 1 < len(gt) and gt[j + 1] <= f:
                    j += 1
                xs.append(int(round(gx[j])))
                ys.append(int(round(gy[j])))
                alive.append(1 if ga[j] else 0)
                hp.append(int(gh[j]) if gh[j] is not None else 0)
                wp.append(interned(gw[j], weapon_names, weapon_idx))
                pl_.append(interned(gp[j], place_names, place_idx))
                lv.append(level_of(gz[j], levels))

            side = g["side"][0]
            player = {
                "name": g["name"][0],
                "side": side,
                "team": team_of_side(side, rn),
                "x": xs,
                "y": ys,
                "alive": alive,
                "hp": hp,
                "w": wp,
                "p": pl_,
            }
            # `lv` só existe em mapa de mais de um andar: em Mirage todo mundo
            # está sempre no nível 0 e o array seria peso morto no arquivo.
            if len(levels) > 1:
                player["lv"] = lv
            players.append(player)

        def frame_of(tick: int) -> int:
            return max(0, min(len(frames) - 1, (int(tick) - t0) // SAMPLE_EVERY))

        events = []
        for k in kills.filter(pl.col("round_num") == rn).sort("tick").iter_rows(named=True):
            if k["victim_X"] is None:
                continue
            events.append(
                {
                    "type": "kill",
                    "f": frame_of(k["tick"]),
                    "t": round((int(k["tick"]) - t0) / TICKRATE, 1),
                    "x": int(round(k["victim_X"])),
                    "y": int(round(k["victim_Y"])),
                    "ax": int(round(k["attacker_X"])) if k["attacker_X"] is not None else None,
                    "ay": int(round(k["attacker_Y"])) if k["attacker_Y"] is not None else None,
                    "attacker": k["attacker_name"],
                    "victim": k["victim_name"],
                    "weapon": k["weapon"],
                    "headshot": bool(k["headshot"]),
                    "side": k["attacker_side"],
                }
            )

        # A tabela de bomba traz posição e autor de cada evento — melhor que
        # inferir a partir do tick do round.
        if bomb is not None:
            relevant = bomb.filter(
                (pl.col("round_num") == rn)
                & pl.col("event").is_in(["plant", "defuse", "detonate"])
                & (pl.col("tick") >= t0)
                & (pl.col("tick") <= t1)
            ).sort("tick")
            for b in relevant.iter_rows(named=True):
                events.append(
                    {
                        "type": {"plant": "plant", "defuse": "defuse", "detonate": "explode"}[b["event"]],
                        "f": frame_of(b["tick"]),
                        "t": round((int(b["tick"]) - t0) / TICKRATE, 1),
                        "x": int(round(b["X"])) if b["X"] is not None else None,
                        "y": int(round(b["Y"])) if b["Y"] is not None else None,
                        "player": b["name"],
                        "site": b["bombsite"] or r["bomb_site"],
                    }
                )

        # Utility que ocupa área: fumaça e fogo têm início, fim e posição, então
        # aparecem no mapa como zonas durante o tempo em que existiram.
        def zones(df: pl.DataFrame | None, default_ticks: int) -> list[dict]:
            if df is None:
                return []
            sel = df.filter((pl.col("round_num") == rn) & (pl.col("start_tick") <= t1))
            out = []
            for z in sel.iter_rows(named=True):
                start = int(z["start_tick"])
                end = int(z["end_tick"]) if z["end_tick"] is not None else start + default_ticks
                if end < t0 or z["X"] is None:
                    continue
                out.append(
                    {
                        "f0": frame_of(start),
                        "f1": frame_of(min(end, t1)),
                        "x": int(round(z["X"])),
                        "y": int(round(z["Y"])),
                        "by": z["thrower_name"],
                    }
                )
            return out

        # Granadas: só o VOO de cada projétil. Depois que ela para, o que
        # importa já é o efeito (a zona de smoke/fogo), não a caixinha parada no
        # chão — desenhar as duas coisas polui o mapa sem informar nada.
        #
        # O filtro por PROJECTILE_KIND é o que separa granada arremessada de
        # granada carregada no inventário: sem ele, a entidade que acompanha o
        # jogador entrava aqui e virava um ponto colorido colado nele o round
        # inteiro (ver nota em metrics/grenades.PROJECTILE_KIND).
        nades = []
        if grenades is not None:
            gr = grenades.filter(
                (pl.col("round_num") == rn)
                & (pl.col("tick") >= t0)
                & (pl.col("tick") <= t1)
                & pl.col("grenade_type").is_in(list(PROJECTILE_KIND))
                & pl.col("X").is_not_null()
                & pl.col("Y").is_not_null()
            ).sort("tick")
            for (eid,), g in gr.group_by(["entity_id"], maintain_order=True):
                kind = PROJECTILE_KIND[g["grenade_type"][0]]
                gt = g["tick"].to_list()
                gx = g["X"].to_list()
                gy = g["Y"].to_list()

                xs, ys = [], []
                j = 0
                f0 = frame_of(gt[0])
                still = 0
                for f in range(f0, len(frames)):
                    target = frames[f]
                    if target < gt[0]:
                        continue
                    while j + 1 < len(gt) and gt[j + 1] <= target:
                        j += 1
                    x, y = int(round(gx[j])), int(round(gy[j]))
                    if xs and abs(x - xs[-1]) + abs(y - ys[-1]) < 12:
                        still += 1
                        if still >= 2:
                            break
                    else:
                        still = 0
                    xs.append(x)
                    ys.append(y)
                    if gt[j] >= gt[-1]:
                        break

                if len(xs) >= 2:
                    nades.append({"k": kind, "by": g["thrower"][0], "f0": f0, "x": xs, "y": ys})

        # Detonações de flash e HE. Ao contrário de smoke e fogo, elas acontecem
        # num instante e não têm zona — o que importa é o efeito: quem ficou cego
        # e por quanto tempo, quanto dano a HE tirou. Sem isso o mapa mostra a
        # granada voando e depois nada, que é justamente a parte que decide a
        # briga.
        pops = []
        blinds = []

        if flash_det is not None and blinds_all is not None:
            round_blinds = blinds_all.filter(pl.col("round_num") == rn)
            for d in flash_det.filter(
                (pl.col("round_num") == rn) & (pl.col("tick") >= t0) & (pl.col("tick") <= t1)
            ).sort("tick").iter_rows(named=True):
                hit = round_blinds.filter(pl.col("entityid") == d["entityid"]).sort(
                    "blind_duration", descending=True
                )
                victims = []
                for b in hit.iter_rows(named=True):
                    dur = float(b["blind_duration"])
                    victims.append(
                        {
                            "n": b["user_name"],
                            "s": round(dur, 1),
                            # inimigo do arremessador: é o que torna a flash boa
                            "e": int(b["attacker_side"] != b["user_side"]),
                        }
                    )
                    start_f = frame_of(b["tick"])
                    blinds.append(
                        {
                            "n": b["user_name"],
                            "f0": start_f,
                            "f1": frame_of(int(b["tick"]) + int(dur * TICKRATE)),
                            "s": round(dur, 1),
                        }
                    )
                pops.append(
                    {
                        "k": "flash",
                        "f": frame_of(d["tick"]),
                        "t": round((int(d["tick"]) - t0) / TICKRATE, 1),
                        "x": int(round(d["x"])),
                        "y": int(round(d["y"])),
                        "by": d["user_name"],
                        "side": d["user_side"],
                        "hit": victims,
                    }
                )

        if he_det is not None:
            he_dmg = (
                damages.filter((pl.col("round_num") == rn) & (pl.col("weapon") == "hegrenade"))
                if damages is not None
                else None
            )
            for d in he_det.filter(
                (pl.col("round_num") == rn) & (pl.col("tick") >= t0) & (pl.col("tick") <= t1)
            ).sort("tick").iter_rows(named=True):
                dmg = 0
                if he_dmg is not None:
                    # o dano é registrado no mesmo tick da detonação ou pouco
                    # depois; a folga cobre as vítimas processadas no tick seguinte
                    near = he_dmg.filter(
                        (pl.col("attacker_steamid") == d["user_steamid"])
                        & (pl.col("tick") >= d["tick"])
                        & (pl.col("tick") <= d["tick"] + POP_DAMAGE_TICKS)
                    )
                    dmg = int(near["dmg_health_real"].sum() or 0)
                pops.append(
                    {
                        "k": "he",
                        "f": frame_of(d["tick"]),
                        "t": round((int(d["tick"]) - t0) / TICKRATE, 1),
                        "x": int(round(d["x"])),
                        "y": int(round(d["y"])),
                        "by": d["user_name"],
                        "side": d["user_side"],
                        "dmg": dmg,
                    }
                )

        out_rounds.append(
            {
                "round": rn,
                "winner_team": team_of_side(r["winner"], rn),
                "winner_side": r["winner"],
                "reason": r["reason"],
                "frames": len(frames),
                "seconds": round((t1 - t0) / TICKRATE, 1),
                "decided_f": max(0, min(len(frames) - 1, (t_decided - t0) // SAMPLE_EVERY)),
                "weapons": weapon_names,
                "places": place_names,
                "players": players,
                "events": sorted(events, key=lambda e: e["f"]),
                "nades": nades,
                "pops": sorted(pops, key=lambda p: p["f"]),
                "blinds": blinds,
                "smokes": zones(smokes, SMOKE_TICKS),
                "fires": zones(infernos, INFERNO_TICKS),
            }
        )

    bounds = {
        "minX": int(ticks["X"].min()),
        "maxX": int(ticks["X"].max()),
        "minY": int(ticks["Y"].min()),
        "maxY": int(ticks["Y"].max()),
    }

    payload = {
        "bounds": bounds,
        "sample_hz": TICKRATE / SAMPLE_EVERY,
        "map": map_name,
        "levels": levels,
        # o painel usa o mesmo limiar das métricas pra decidir quais flashes
        # entram na linha do tempo, em vez de ter um número próprio que
        # silenciosamente diverge do que as tabelas contam
        "effective_blind_s": EFFECTIVE_BLIND_SECONDS,
        "rounds": out_rounds,
    }
    out = processed / "replay.json"
    out.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description="Exporta o replay simplificado por round.")
    parser.add_argument("match_id", type=str)
    args = parser.parse_args()
    out = build(args.match_id)
    print(f"{out}  ({out.stat().st_size / 1024:.0f} KB)")


if __name__ == "__main__":
    main()
