"""
Diagnóstico das entradas do timeline: onde cada evento caiu e por quê.

Existe porque um card de round mostrava "-69,0s — PoisonLilies perdeu a abertura"
com o mesmo jogador como vítima e matador. Tempo negativo num timeline cuja
origem é o fim do freeze time significa evento antes do round começar a ser
jogado, e a magnitude (69s ≈ 4.400 ticks) descarta erro de arredondamento.

Para cada entrada imprime o tick do evento e as quatro fronteiras do round com
que ele foi casado, mais o delta. Sem interpretar nada: a leitura é do Pedro.

Uso:
    py -3.12 -m scripts.debug_timeline            # só o que está fora da janela
    py -3.12 -m scripts.debug_timeline --tudo     # todas as entradas
    py -3.12 -m scripts.debug_timeline --match match_08
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import polars as pl

from metrics.timing import detect_tickrate

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
INTERIM_DIR = PROJECT_ROOT / "data" / "interim"

# Quanto tempo depois do fim do round um evento ainda é plausível. O replay já
# estende o round por uma cauda (TAIL_TICKS em scripts/export_replay.py) porque
# dá para morrer depois do round decidido; além disso é evento de outro round.
CAUDA_PLAUSIVEL_S = 8.0


def fronteiras(rounds: pl.DataFrame) -> dict[int, dict]:
    return {int(r["round_num"]): r for r in rounds.iter_rows(named=True)}


def analisa(match_id: str, mostrar_tudo: bool) -> list[dict]:
    processed = PROCESSED_DIR / match_id
    breakdown_path = processed / "breakdown.json"
    if not breakdown_path.exists():
        return []

    rounds = pl.read_parquet(processed / "rounds.parquet")
    ticks_path = INTERIM_DIR / match_id / "ticks.parquet"
    ticks = pl.read_parquet(ticks_path) if ticks_path.exists() else None
    tickrate = int(detect_tickrate(rounds, ticks)["tickrate"])

    bordas = fronteiras(rounds)
    breakdown = json.loads(breakdown_path.read_text(encoding="utf-8"))

    linhas = []
    for b in breakdown:
        rn = int(b["round"])
        r = bordas.get(rn)
        if r is None:
            linhas.append({"match": match_id, "round": rn, "problema": "round inexistente"})
            continue

        freeze_end, fim = int(r["freeze_end"]), int(r["end"])
        oficial = r["official_end"]
        limite = fim + int(CAUDA_PLAUSIVEL_S * tickrate)

        for m in b.get("moments", []):
            tick = m.get("tick")
            if tick is None:
                continue
            delta = int(tick) - freeze_end
            fora = tick < freeze_end or tick > limite
            if not (fora or mostrar_tudo):
                continue
            linhas.append(
                {
                    "match": match_id,
                    "round": rn,
                    "kind": m.get("kind"),
                    "who": m.get("who"),
                    "by": m.get("by"),
                    "tick": int(tick),
                    "start": int(r["start"]),
                    "freeze_end": freeze_end,
                    "end": fim,
                    "official_end": None if oficial is None else int(oficial),
                    "delta_ticks": delta,
                    "delta_s": round(delta / tickrate, 1),
                    "antes_do_freeze_end": tick < freeze_end,
                    "depois_do_fim": tick > limite,
                    "auto_matador": m.get("who") is not None and m.get("who") == m.get("by"),
                    "ultimo_round": rn == int(rounds["round_num"].max()),
                    "tickrate": tickrate,
                }
            )
    return linhas


def main() -> None:
    p = argparse.ArgumentParser(description="Diagnóstico do timeline dos rounds.")
    p.add_argument("--match", type=str, default=None)
    p.add_argument("--tudo", action="store_true", help="imprime todas as entradas")
    args = p.parse_args()

    alvos = (
        [args.match]
        if args.match
        else sorted(d.name for d in PROCESSED_DIR.glob("match_*") if d.is_dir())
    )

    todas = []
    for match_id in alvos:
        todas.extend(analisa(match_id, args.tudo))

    if not todas:
        print("Nenhuma entrada fora da janela [freeze_end, end + cauda]. Timeline limpo.")
        return

    pl.Config.set_tbl_rows(80)
    pl.Config.set_tbl_width_chars(220)
    pl.Config.set_tbl_cols(20)
    tabela = pl.DataFrame(todas)

    print(f"{tabela.height} entrada(s)\n")
    print(
        tabela.select(
            [c for c in ["match", "round", "kind", "who", "by", "tick", "start",
                         "freeze_end", "end", "official_end", "delta_ticks", "delta_s",
                         "auto_matador", "ultimo_round"] if c in tabela.columns]
        )
    )

    if "antes_do_freeze_end" in tabela.columns:
        antes = tabela.filter(pl.col("antes_do_freeze_end"))
        depois = tabela.filter(pl.col("depois_do_fim"))
        auto = tabela.filter(pl.col("auto_matador"))
        print(
            f"\nantes do freeze_end: {antes.height}"
            f"  ·  depois do fim + cauda: {depois.height}"
            f"  ·  vítima = matador: {auto.height}"
        )
        if antes.height:
            print(
                "\nOs que estão antes do freeze_end caem no intervalo start→freeze_end,"
                "\nou seja, DENTRO do freeze time do round. O round só começa a ser"
                "\njogado quando o freeze acaba — evento ali não pertence ao round."
            )


if __name__ == "__main__":
    main()
