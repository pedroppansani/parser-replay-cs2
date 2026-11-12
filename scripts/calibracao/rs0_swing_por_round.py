"""RS0 (só leitura): o Round Swing por (partida, round, jogador) de todas as partidas do corpus, com a referência e o modelo gravados.

    py -3.12 -m scripts.calibracao.rs0_swing_por_round SAIDA.parquet
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import polars as pl

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ))
from metrics.rating import ModeloDeRound, carrega_referencia, rating  # noqa: E402
from scripts.fit_rating import carrega_partida, partidas_disponiveis, tickrate_da_partida  # noqa: E402


def main() -> None:
    saida = Path(sys.argv[1])
    ref = carrega_referencia()
    modelo = ModeloDeRound.da_referencia((ref or {}).get("modelo_de_round"))
    linhas = []
    for mid in partidas_disponiveis():
        t0 = time.time()
        tabelas, team_of, vencedor, kast = carrega_partida(mid)
        per_round, _ = rating(tabelas, team_of, vencedor, kast, tickrate_da_partida(tabelas), referencia=ref, modelo=modelo)
        nome = dict(tabelas["ticks"].group_by("steamid", maintain_order=True).agg(pl.col("name").last()).iter_rows())
        n_rounds = tabelas["rounds"].height
        d = per_round.with_columns(pl.lit(mid).alias("partida"), pl.col("steamid").map_elements(lambda s: nome.get(s), return_dtype=pl.String).alias("nome"),
                                   pl.lit(n_rounds).alias("rounds_da_partida"))
        linhas.append(d)
        print(f"{mid}: {d.height} linhas, {time.time() - t0:.0f} s", flush=True)
    pl.concat(linhas, how="diagonal").write_parquet(saida)
    print("FIM", flush=True)


if __name__ == "__main__":
    main()
