"""C0b, só leitura: dá para medir o tempo de corrida do corpus ENTRE DOIS PONTOS DO PEDRO (em vez de entre áreas da demo)?

    py -3.12 -m pesquisa.comandos_c0b_pontos <raiz_dos_dados> <saida.json> [mapa ...]

`raiz_dos_dados` é a pasta que tem `data/interim` e `data/processed` (o repositório principal, quando se roda de um worktree). Cada jogador vivo, a cada 8
ticks, é "no ponto P" quando P é o ponto do Pedro mais perto e está a até RAIO_U do jogador (senão, em nenhum). Uma viagem é a mesma da C0 (saída de P1
-> primeira chegada a P2, corrida sem parada, a pelo menos 300 u, no máximo 25 s). Conta, por mapa, quantos pares de pontos têm n >= 20 casos em >= 3
partidas, e compara com os pares de áreas da demo (C0). Só mapas de um andar.
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

import numpy as np
import polars as pl

from scripts.build_lineups import detect_tickrate, load_interim

RAIZ = Path(__file__).resolve().parent.parent
PASSO, LIMITE_S, PARADO_U_S, PARADA_MAX_S, RAIO_U = 8, 25.0, 40.0, 1.0, 200.0


def pontos(mapa: str) -> tuple[list[str], np.ndarray]:
    nomes, xy = [], []
    for r in csv.DictReader(open(RAIZ / "data" / "reference" / "callouts_br.csv", encoding="utf-8-sig"), delimiter=";"):
        if r["mapa"] == mapa and r["tipo"] == "lugar" and r["nome"] not in ("Default",):
            nomes.append(r["nome"] + (f" ({r['qualificacao']})" if r["qualificacao"] else "") + f"#{len(nomes)}"); xy.append((float(r["x"]), float(r["y"])))
    return nomes, np.array(xy)


def viagens(dados: Path, nome: str, nomes: list[str], P: np.ndarray) -> list[tuple]:
    inter, proc = dados / "data" / "interim", dados / "data" / "processed"
    t = load_interim(inter, nome)
    rounds = pl.read_parquet(proc / nome / "rounds.parquet")
    tr = int(detect_tickrate(rounds, t["ticks"])["tickrate"]); passo = max(1, round(PASSO * tr / 64)); dt = passo / tr
    ini = {r["round_num"]: (r["freeze_end"], r["end"]) for r in rounds.iter_rows(named=True) if r["freeze_end"] is not None and r["end"] is not None}
    tk = (t["ticks"].filter((pl.col("tick") % passo == 0) & pl.col("is_alive")).select("tick", "round_num", "steamid", "X", "Y", "is_walking").sort("steamid", "round_num", "tick"))
    saida = []
    for (sid, rd), g in tk.group_by(["steamid", "round_num"], maintain_order=True):
        if rd not in ini:
            continue
        a, b = ini[rd]; g = g.filter((pl.col("tick") >= a) & (pl.col("tick") <= b))
        if g.height < 4:
            continue
        x, y = g["X"].to_numpy().astype(float), g["Y"].to_numpy().astype(float); ticks = g["tick"].to_numpy(); walk = g["is_walking"].fill_null(False).to_numpy().astype(float)
        d = np.hypot(x[:, None] - P[None, :, 0], y[:, None] - P[None, :, 1]); k = d.argmin(axis=1); perto = d[np.arange(len(k)), k] <= RAIO_U
        passos = np.hypot(np.diff(x), np.diff(y)); vel = np.concatenate([[0.0], passos / ((np.diff(ticks) / tr).clip(min=dt))])
        acum = np.concatenate([[0.0], np.cumsum(passos)]); cp = np.concatenate([[0], np.cumsum((vel < PARADO_U_S).astype(int))])
        runs, i0 = [], None
        for i in range(len(k) + 1):
            atual = int(k[i]) if i < len(k) and perto[i] else None
            if i0 is not None and (atual != runs_p or i == len(k) or ticks[i] - ticks[i - 1] > 4 * passo):
                runs.append((runs_p, i0, i - 1)); i0 = None
            if atual is not None and i0 is None:
                i0, runs_p = i, atual
        for ri, (A, pri, ult) in enumerate(runs):
            vistos = {A}
            for rj in range(ri + 1, len(runs)):
                B, prim, _ = runs[rj]
                if B in vistos:
                    continue
                vistos.add(B); dur = (ticks[prim] - ticks[ult]) / tr
                if dur <= 0 or dur > LIMITE_S:
                    break
                reta = float(np.hypot(x[prim] - x[ult], y[prim] - y[ult]))
                if reta < 300 or (cp[prim + 1] - cp[ult + 1]) * dt > PARADA_MAX_S or walk[ult:prim + 1].mean() > 0.1:
                    continue
                saida.append((nome, A, B, dur, (ticks[prim] - ticks[pri]) / tr, reta))
    return saida


def main() -> None:
    dados, saida, mapas = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3:] or ["de_mirage", "de_dust2", "de_inferno"]
    res = {}
    for mapa in mapas:
        nomes, P = pontos(mapa); todas = []
        for d in sorted((dados / "data" / "interim").glob("match_*")):
            mm = dados / "data" / "processed" / d.name / "match_meta.json"
            if mm.exists() and json.loads(mm.read_text(encoding="utf-8"))["map_name"] == mapa:
                todas += viagens(dados, d.name, nomes, P)
        df = pl.DataFrame(todas, schema=["partida", "de", "para", "dur_s", "dur_entrada_s", "reta_u"], orient="row")
        g = df.group_by(["de", "para"]).agg(n=pl.len(), partidas=pl.col("partida").n_unique(), mediana_s=pl.col("dur_s").median(), entrada_s=pl.col("dur_entrada_s").median())
        res[mapa] = {"pontos": len(nomes), "pontos_visitados": int(len(set(df["de"]) | set(df["para"]))), "viagens": df.height, "pares_possiveis": len(nomes) * (len(nomes) - 1),
                     "pares_vistos": g.height, "pares_n5": int(g.filter(pl.col("n") >= 5).height), "pares_n10": int(g.filter(pl.col("n") >= 10).height),
                     "pares_n20_3partidas": int(g.filter((pl.col("n") >= 20) & (pl.col("partidas") >= 3)).height),
                     "exemplos": [{"de": nomes[r["de"]], "para": nomes[r["para"]], "n": r["n"], "partidas": r["partidas"], "saida_entrada_s": round(r["mediana_s"], 1), "entrada_entrada_s": round(r["entrada_s"], 1)}
                                  for r in g.filter((pl.col("n") >= 20) & (pl.col("partidas") >= 3)).sort("n", descending=True).head(5).to_dicts()]}
        print(mapa, {k: v for k, v in res[mapa].items() if k != "exemplos"}, flush=True)
    saida.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
