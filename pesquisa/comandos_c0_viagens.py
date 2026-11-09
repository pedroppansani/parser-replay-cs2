"""C0 (Comandos na prancheta), só leitura: as viagens reais entre dois lugares do mapa, nas partidas do corpus.

    py -3.12 -m pesquisa.comandos_c0_viagens <pasta_de_saida>

Uma viagem é: o jogador vivo, no round valendo (do fim do freeze ao fim do round), sai do lugar A (último tick dentro de A) e
chega ao lugar B (primeiro tick dentro de B depois disso). `dur_s` conta da saída de A; `dur_entrada_s`, da entrada em A (quem parte do meio de A fica entre as duas). Vale cada B distinto que aparece depois de A, pelo primeiro tick.
Os lugares são os `place` dos ticks (o nome que o jogo dá), amostrados a cada 8 ticks. Para cada viagem grava: duração, caminho
andado (soma dos passos horizontais), distância em linha reta entre o ponto de saída e o de chegada, se foi direta (B é o lugar
seguinte), se houve parada (mais de 1 s abaixo de 40 u/s) e a fração de ticks andando (shift). Nada de partida vai para o repo:
a saída é uma tabela de trabalho.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import polars as pl

from scripts.build_lineups import INTERIM, PROCESSED, detect_tickrate, load_interim

PASSO = 8              # ticks entre amostras
LIMITE_S = 25.0        # viagem mais longa que isso é espera, não deslocamento
PARADO_U_S = 40.0      # abaixo disso o jogador está parado
PARADA_MAX_S = 1.0     # mais que isso parado no meio da viagem = "com parada"


def viagens_da_partida(nome: str) -> pl.DataFrame | None:
    meta = PROCESSED / nome / "match_meta.json"
    if not meta.exists() or not (INTERIM / nome / "ticks.parquet").exists():
        return None
    import json
    mapa = json.loads(meta.read_text(encoding="utf-8"))["map_name"]
    t = load_interim(INTERIM, nome)
    rounds = pl.read_parquet(PROCESSED / nome / "rounds.parquet")
    tr = int(detect_tickrate(rounds, t["ticks"])["tickrate"])
    passo = max(1, round(PASSO * tr / 64))
    dt = passo / tr
    ini = {r["round_num"]: (r["freeze_end"], r["end"]) for r in rounds.iter_rows(named=True) if r["freeze_end"] is not None and r["end"] is not None}
    tk = (t["ticks"].filter((pl.col("tick") % passo == 0) & pl.col("is_alive") & pl.col("place").is_not_null() & (pl.col("place") != ""))
          .select("tick", "round_num", "steamid", "side", "X", "Y", "Z", "place", "is_walking").sort("steamid", "round_num", "tick"))
    saida = []
    for (sid, rd), g in tk.group_by(["steamid", "round_num"], maintain_order=True):
        if rd not in ini:
            continue
        a, b = ini[rd]
        g = g.filter((pl.col("tick") >= a) & (pl.col("tick") <= b))
        if g.height < 4:
            continue
        x, y = g["X"].to_numpy().astype(float), g["Y"].to_numpy().astype(float)
        ticks = g["tick"].to_numpy(); pl_ = g["place"].to_list(); walk = g["is_walking"].fill_null(False).to_numpy().astype(float)
        passos = np.hypot(np.diff(x), np.diff(y)); vel = np.concatenate([[0.0], passos / ((np.diff(ticks) / tr).clip(min=dt))])
        acum = np.concatenate([[0.0], np.cumsum(passos)])
        parado = (vel < PARADO_U_S).astype(int)
        cp = np.concatenate([[0], np.cumsum(parado)])
        # corridas de ticks do mesmo lugar: (lugar, primeiro, último)
        runs, i0 = [], 0
        for i in range(1, len(pl_) + 1):
            if i == len(pl_) or pl_[i] != pl_[i0] or ticks[i] - ticks[i - 1] > 4 * passo:
                runs.append((pl_[i0], i0, i - 1)); i0 = i
        lado = g["side"][0]
        for ri, (A, pri, ult) in enumerate(runs):
            vistos = {A}
            for rj in range(ri + 1, len(runs)):
                B, prim, _ = runs[rj]
                if B in vistos:
                    continue
                vistos.add(B)
                dur = (ticks[prim] - ticks[ult]) / tr
                if dur <= 0 or dur > LIMITE_S:
                    break
                if ticks[prim] - ticks[prim - 1] > 4 * passo:      # buraco nos dados (morte, troca de round): não é viagem
                    continue
                n_par = cp[prim + 1] - cp[ult + 1]
                saida.append((nome, mapa, lado, int(rd), sid, A, B, dur, float((ticks[prim] - ticks[pri]) / tr), float(acum[prim] - acum[ult]),
                              float(np.hypot(x[prim] - x[ult], y[prim] - y[ult])), rj == ri + 1,
                              bool(n_par * dt > PARADA_MAX_S), float(walk[ult:prim + 1].mean()),
                              float(x[ult]), float(y[ult]), float(x[prim]), float(y[prim])))
    if not saida:
        return None
    cols = ["partida", "mapa", "lado", "round", "steamid", "de", "para", "dur_s", "dur_entrada_s", "caminho_u", "reta_u", "direta", "com_parada", "andando", "x0", "y0", "x1", "y1"]
    return pl.DataFrame(saida, schema=cols, orient="row")


def main() -> None:
    pasta = Path(sys.argv[1]); pasta.mkdir(parents=True, exist_ok=True)
    partes = []
    for d in sorted(INTERIM.glob("match_*")):
        v = viagens_da_partida(d.name)
        print(d.name, 0 if v is None else v.height, flush=True)
        if v is not None:
            partes.append(v)
    pl.concat(partes).write_parquet(pasta / "viagens.parquet")
    print("FIM", sum(p.height for p in partes))


if __name__ == "__main__":
    main()
