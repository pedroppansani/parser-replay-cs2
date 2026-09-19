"""
Casos de repick impressos, para conferir se a métrica mede o que o Pedro chama
de repick ("fica repickando no mesmo ângulo": sai, troca tiro, volta).

    py -3.12 -m scripts.casos_repick            # 10 casos, um por partida
    py -3.12 -m scripts.casos_repick --n 20 --partida match_38

Para cada caso: round, relógio do round (desde o fim do freeze time), tick para
achar no replay, onde ele estava, para onde mirava, quanto andou e quanto saiu
do lugar na janela antes da briga, QUANTAS VEZES saiu e voltou, e o que
aconteceu (matou ou morreu, para quem, com o quê).

A seleção é determinística (semente fixa) e espalhada: no máximo um caso por
partida, alternando entre brigas que ele venceu e que perdeu -- dez casos da
mesma partida ou só de vitórias esconderiam o que a métrica erra.
"""
from __future__ import annotations

import argparse
import random
import sys
from pathlib import Path

import numpy as np
import polars as pl

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from metrics.archetypes import engagement_ticks, repick_engagements  # noqa: E402
from metrics.awp_metrics import PRE_ENGAGEMENT_WINDOW_SECONDS, classify_engagement_style  # noqa: E402
from metrics.timing import detect_tickrate  # noqa: E402
from parsing.parser import load_interim  # noqa: E402

INTERIM = PROJECT_ROOT / "data" / "interim"
PROCESSED = PROJECT_ROOT / "data" / "processed"

# Distância do ponto de partida que conta como "saiu" do lugar na contagem de
# saídas. Um passo lateral de peek em CS2 é ~60-100u; 40u separa o balanço de
# mira parado de uma saída de verdade.
SAIDA_MIN = 40.0
SEMENTE = 2025


def _saidas(xs: np.ndarray, ys: np.ndarray) -> int:
    """Quantas vezes ele se afastou mais de SAIDA_MIN do ponto inicial e voltou para perto."""
    d = np.hypot(xs - xs[0], ys - ys[0])
    fora, n = False, 0
    for v in d:
        if not fora and v > SAIDA_MIN:
            fora, n = True, n + 1
        elif fora and v < SAIDA_MIN / 2:
            fora = False
    return n


def _rumo(yaw: float) -> str:
    """Yaw do CS2 em ponto cardeal do radar (0 = leste, 90 = norte)."""
    nomes = ["leste", "nordeste", "norte", "noroeste", "oeste", "sudoeste", "sul", "sudeste"]
    return nomes[int(((yaw % 360) + 22.5) // 45) % 8]


def casos_da_partida(match_id: str) -> list[dict]:
    t = load_interim(INTERIM, match_id)
    ticks, kills, rounds = t["ticks"], t["kills"], t["rounds"]
    tickrate = detect_tickrate(rounds, ticks)["tickrate"]
    eng = engagement_ticks(kills)
    estilos = classify_engagement_style(eng, ticks, tickrate=tickrate)
    marcados = repick_engagements(estilos)
    casos = []
    freeze = dict(rounds.select(pl.col("round_num").cast(pl.UInt32), "freeze_end").iter_rows())
    nome = dict(ticks.group_by("steamid").agg(pl.col("name").last()).iter_rows())
    janela = int(PRE_ENGAGEMENT_WINDOW_SECONDS * tickrate)
    for r in marcados.filter(pl.col("repick")).iter_rows(named=True):
        rn, sid, tk = int(r["round_num"]), r["steamid"], int(r["engagement_tick"])
        w = ticks.filter((pl.col("steamid") == sid) & (pl.col("round_num") == rn)
                         & (pl.col("tick") >= tk - janela) & (pl.col("tick") <= tk)).sort("tick")
        if w.height < 2:
            continue
        fim = w.row(-1, named=True)
        k = kills.filter((pl.col("round_num") == rn) & (pl.col("tick") == tk)
                         & ((pl.col("attacker_steamid") == sid) | (pl.col("victim_steamid") == sid))).row(0, named=True)
        if k["attacker_steamid"] == sid:
            aconteceu = f"MATOU {k['victim_name']} ({k['weapon']}{', HS' if k.get('headshot') else ''})"
        else:
            aconteceu = f"MORREU para {k['attacker_name'] or 'o mundo'} ({k['weapon']})"
        seg = (tk - freeze.get(rn, tk)) / tickrate
        casos.append({
            "match_id": match_id, "round": rn, "jogador": nome.get(sid), "lado": fim.get("side"),
            "relogio": f"{int(seg // 60)}:{int(seg % 60):02d}", "tick": tk, "local": fim.get("place") or "?",
            "mira": f"yaw {fim['yaw']:.0f}° ({_rumo(fim['yaw'])}), pitch {fim['pitch']:.0f}°",
            "andou": round(r["path_distance"]), "saiu_do_lugar": round(r["net_displacement"]),
            "saidas": _saidas(w["X"].to_numpy().astype(float), w["Y"].to_numpy().astype(float)),
            "venceu": k["attacker_steamid"] == sid, "aconteceu": aconteceu,
        })
    return casos


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--n", type=int, default=10)
    ap.add_argument("--partida")
    args = ap.parse_args()

    partidas = [args.partida] if args.partida else sorted(
        d.name for d in PROCESSED.glob("match_*") if (INTERIM / d.name / "ticks.parquet").exists())
    rnd = random.Random(SEMENTE)
    rnd.shuffle(partidas)
    escolhidos, quer_vitoria = [], True
    for mid in partidas:
        casos = casos_da_partida(mid)
        rnd.shuffle(casos)
        # alterna vitória / derrota; sem o tipo pedido, pega o que houver
        alvo = [c for c in casos if c["venceu"] == quer_vitoria] or casos
        por_partida = alvo[: (args.n if args.partida else 1)]
        escolhidos += por_partida
        quer_vitoria = not quer_vitoria
        if len(escolhidos) >= args.n:
            break

    print(f"CASOS DE REPICK -- janela de {PRE_ENGAGEMENT_WINDOW_SECONDS:.0f}s antes da briga; "
          f"'saídas' = vezes que se afastou mais de {SAIDA_MIN:.0f}u do ponto inicial e voltou\n")
    for i, c in enumerate(escolhidos[: args.n], 1):
        print(f"{i:>2}. {c['match_id']} round {c['round']} ({c['relogio']} do round, tick {c['tick']}) "
              f"-- {c['jogador']} ({c['lado']}) em {c['local']}")
        print(f"    mira: {c['mira']}")
        print(f"    nos {PRE_ENGAGEMENT_WINDOW_SECONDS:.0f}s antes: andou {c['andou']}u, terminou a {c['saiu_do_lugar']}u de onde "
              f"começou, {c['saidas']} saída(s) e volta(s)")
        print(f"    o que aconteceu: {c['aconteceu']}\n")


if __name__ == "__main__":
    main()
