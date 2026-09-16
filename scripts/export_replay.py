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

PROJECT_ROOT = Path(__file__).resolve().parent.parent

SAMPLE_EVERY = 32  # ticks
TICKRATE = 128
HALFTIME_ROUND = 12

# Durações padrão quando o demo não registra o fim da entidade (acontece quando
# o round acaba antes de a fumaça/fogo expirar). Valores do próprio awpy.
# Classes de entidade do demo -> categoria legível. As duas formas (projétil
# em voo e entidade depositada) apontam para a mesma categoria.
GRENADE_KIND = {
    "CHEGrenadeProjectile": "he",
    "CHEGrenade": "he",
    "CFlashbangProjectile": "flash",
    "CFlashbang": "flash",
    "CSmokeGrenadeProjectile": "smoke",
    "CSmokeGrenade": "smoke",
    "CMolotovProjectile": "molotov",
    "CMolotovGrenade": "molotov",
    "CIncendiaryGrenade": "molotov",
    "CDecoyProjectile": "decoy",
    "CDecoyGrenade": "decoy",
}

# Quanto o replay continua depois de a vitória ser decidida, pra a última morte
# e o desarme caberem na linha do tempo.
TAIL_TICKS = int(4.0 * TICKRATE)
# Folga antes do começo oficial do próximo round, onde os jogadores já foram
# teleportados pro spawn.
RESET_MARGIN_TICKS = int(1.5 * TICKRATE)

SMOKE_TICKS = int(20.0 * TICKRATE)
INFERNO_TICKS = int(7.03125 * TICKRATE)


def team_of_side(side: str, round_num: int) -> str:
    """Time real a partir do lado e do round (os lados trocam no intervalo)."""
    first_half = round_num <= HALFTIME_ROUND
    if side == "t":
        return "A" if first_half else "B"
    return "B" if first_half else "A"


def build(match_id: str) -> Path:
    processed = PROJECT_ROOT / "data" / "processed" / match_id
    interim = PROJECT_ROOT / "data" / "interim" / match_id

    rounds = pl.read_parquet(processed / "rounds.parquet")
    ticks = pl.read_parquet(interim / "ticks.parquet")
    kills = pl.read_parquet(interim / "kills.parquet")
    bomb = pl.read_parquet(interim / "bomb.parquet") if (interim / "bomb.parquet").exists() else None
    smokes = pl.read_parquet(interim / "smokes.parquet") if (interim / "smokes.parquet").exists() else None
    infernos = pl.read_parquet(interim / "infernos.parquet") if (interim / "infernos.parquet").exists() else None
    grenades = pl.read_parquet(interim / "grenades.parquet") if (interim / "grenades.parquet").exists() else None

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
            ["tick", "steamid", "name", "side", "X", "Y", "is_alive", "health", "active_weapon_name"]
        )

        # Armas viram índices num dicionário do round: repetir a string em cada
        # frame de cada jogador multiplicaria o tamanho do arquivo à toa.
        weapon_names: list[str] = []
        weapon_idx: dict[str, int] = {}

        def wid(w: str | None) -> int:
            if not w:
                return -1
            if w not in weapon_idx:
                weapon_idx[w] = len(weapon_names)
                weapon_names.append(w)
            return weapon_idx[w]

        players = []
        for (sid,), g in rt.group_by(["steamid"], maintain_order=True):
            g = g.sort("tick")
            gt = g["tick"].to_list()
            gx = g["X"].to_list()
            gy = g["Y"].to_list()
            ga = g["is_alive"].to_list()
            gh = g["health"].to_list()
            gw = g["active_weapon_name"].to_list()

            xs, ys, alive, hp, wp = [], [], [], [], []
            j = 0
            for f in frames:
                # avança até a amostra mais próxima sem passar do frame
                while j + 1 < len(gt) and gt[j + 1] <= f:
                    j += 1
                xs.append(int(round(gx[j])))
                ys.append(int(round(gy[j])))
                alive.append(1 if ga[j] else 0)
                hp.append(int(gh[j]) if gh[j] is not None else 0)
                wp.append(wid(gw[j]))

            side = g["side"][0]
            players.append(
                {
                    "name": g["name"][0],
                    "side": side,
                    "team": team_of_side(side, rn),
                    "x": xs,
                    "y": ys,
                    "alive": alive,
                    "hp": hp,
                    "w": wp,
                }
            )

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
        nades = []
        if grenades is not None:
            gr = grenades.filter(
                (pl.col("round_num") == rn)
                & (pl.col("tick") >= t0)
                & (pl.col("tick") <= t1)
                & pl.col("X").is_not_null()
                & pl.col("Y").is_not_null()
            ).sort("tick")
            for (eid,), g in gr.group_by(["entity_id"], maintain_order=True):
                kind = GRENADE_KIND.get(g["grenade_type"][0])
                if kind is None:
                    continue
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
                "players": players,
                "events": sorted(events, key=lambda e: e["f"]),
                "nades": nades,
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

    payload = {"bounds": bounds, "sample_hz": TICKRATE / SAMPLE_EVERY, "rounds": out_rounds}
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
