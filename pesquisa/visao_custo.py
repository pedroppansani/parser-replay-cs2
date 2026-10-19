"""Fase 18 (18.1): a linha de visão pelo mapa funciona nos 8 mapas? quanto custa? bate com o awpy 2.0.2?

    py -3.12 -m pesquisa.visao_custo [n_consultas]

Para cada mapa: lê o .tri, monta a grade (`metrics.erros.visao.Malha`) e responde `n` segmentos entre
posições reais de jogadores (olhos a olhos, pares do mesmo tick de uma partida daquele mapa).
Na Mirage e na Nuke (as malhas menores) monta também o `awpy.visibility.VisibilityChecker` do awpy
2.0.2 e compara resposta a resposta e o tempo. Só imprime.
"""
from __future__ import annotations

import json
import sys
import time

import numpy as np
import polars as pl

from metrics.erros import visao

RAIZ = visao.Path(__file__).resolve().parents[1]


def _partida_do_mapa(mapa: str) -> str | None:
    man = json.loads((RAIZ / "data" / "manifest.json").read_text(encoding="utf-8"))
    for m, v in sorted(man["partidas"].items()):
        if v.get("mapa") == mapa and (RAIZ / "data" / "interim" / m / "ticks.parquet").exists():
            return m
    return None


def segmentos(mapa: str, n: int, semente: int = 18) -> list[tuple]:
    m = _partida_do_mapa(mapa)
    t = pl.read_parquet(RAIZ / "data" / "interim" / m / "ticks.parquet",
                        columns=["tick", "steamid", "X", "Y", "Z", "is_alive", "side"])
    t = t.filter(pl.col("is_alive"))
    ticks = t["tick"].unique().sort().to_numpy()
    rng = np.random.default_rng(semente)
    out = []
    por_tick = {k[0]: g for k, g in t.group_by(["tick"], maintain_order=True)}
    escolhidos = rng.choice(ticks, size=min(len(ticks), n * 2), replace=False)
    for tk in escolhidos:
        g = por_tick.get(int(tk))
        if g is None or g.height < 2:
            continue
        a, b = rng.choice(g.height, size=2, replace=False)
        ra, rb = g.row(int(a), named=True), g.row(int(b), named=True)
        out.append(((ra["X"], ra["Y"], ra["Z"] + 64.0), (rb["X"], rb["Y"], rb["Z"] + 64.0)))
        if len(out) == n:
            break
    return out


def main(argv: list[str]) -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    n = int(argv[0]) if argv else 2000
    print("| mapa | triângulos | montar a grade (s) | consulta (ms, média) | livres | awpy 2.0.2: montar (s) | awpy: consulta (ms) | respostas iguais |")
    print("|---|---|---|---|---|---|---|---|")
    for mapa in ("de_ancient", "de_anubis", "de_dust2", "de_inferno", "de_mirage", "de_nuke", "de_overpass", "de_train"):
        tri = visao.le_tri(visao.TRIS_DIR / f"{mapa}.tri")
        t0 = time.perf_counter()
        malha = visao.Malha(tri)
        t_grade = time.perf_counter() - t0
        segs = segmentos(mapa, n)
        t0 = time.perf_counter()
        nossa = [malha.linha_livre(a, b) for a, b in segs]
        t_cons = (time.perf_counter() - t0) / len(segs) * 1000
        awpy_txt = "—", "—", "—"
        if mapa in ("de_mirage", "de_nuke"):
            from awpy.visibility import Triangle, VisibilityChecker
            from awpy.vector import Vector3
            sys.setrecursionlimit(100000)
            tris = [Triangle(Vector3(*map(float, x[0])), Vector3(*map(float, x[1])), Vector3(*map(float, x[2])))
                    for x in tri]
            t0 = time.perf_counter()
            vc = VisibilityChecker(triangles=tris)
            t_aw = time.perf_counter() - t0
            k = min(len(segs), 300)
            t0 = time.perf_counter()
            deles = [vc.is_visible(a, b) for a, b in segs[:k]]
            t_aw_c = (time.perf_counter() - t0) / k * 1000
            iguais = sum(x == y for x, y in zip(nossa[:k], deles))
            awpy_txt = f"{t_aw:.0f}", f"{t_aw_c:.1f}", f"{iguais} de {k}"
        print(f"| {mapa} | {malha.n} | {t_grade:.1f} | {t_cons:.2f} | {sum(nossa)} de {len(segs)} | "
              f"{awpy_txt[0]} | {awpy_txt[1]} | {awpy_txt[2]} |")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
