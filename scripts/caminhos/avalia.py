"""O erro do tempo pelo caminho contra o tempo real da C3 (`data/tempos/<mapa>.json`), com o grafo de `data/caminhos/<mapa>.json`, a 250 u/s; o mesmo cálculo da PC0 (erro absoluto em % da mediana real).

    py -3.12 -m scripts.caminhos.avalia de_mirage"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np

from scripts.caminhos.busca import VELOCIDADE_U_S, Caminhos

RAIZ = Path(__file__).resolve().parent.parent.parent


def pares_do_mapa(mapa: str) -> tuple[list, dict, dict]:
    """(pares da C3 [a, b, p25, med, p75, casos, partidas], posição de cada nó {chave: (x, y)}, z de cada nó {chave: z})."""
    d = json.loads((RAIZ / "data" / "caminhos" / f"{mapa}.json").read_text(encoding="utf-8"))
    t = json.loads((RAIZ / "data" / "tempos" / f"{mapa}.json").read_text(encoding="utf-8"))
    if t["pontos"]:
        return t["pontos"], {n[0]: (n[1], n[2]) for n in t["nos"]}, d["z_pontos"]
    from scripts.comandos_contexto import contexto
    nos = {a["nome"]: (a["x"], a["y"]) for a in contexto(mapa, so_conferidos=False)["areas"]}
    return t["areas"], nos, d["z_areas"]


def avalia(mapa: str, fio: bool = True, g: Caminhos | None = None) -> dict:
    g = g or Caminhos(json.loads((RAIZ / "data" / "caminhos" / f"{mapa}.json").read_text(encoding="utf-8")))
    pares, nos, zs = pares_do_mapa(mapa)
    real, reta, cam, dz = [], [], [], []
    for a, b, _p25, med, _p75, _casos, _partidas in pares:
        if a not in nos or b not in nos:
            continue
        pa, pb = (*nos[a], zs.get(a)), (*nos[b], zs.get(b))
        r = g.caminho(pa, pb, fio=fio)
        if r is None:
            continue
        real.append(med)
        reta.append(math.hypot(pa[0] - pb[0], pa[1] - pb[1]) / VELOCIDADE_U_S)
        cam.append(r["comprimento"] / VELOCIDADE_U_S)
        dz.append(abs((zs.get(a) or 0) - (zs.get(b) or 0)))
    real, reta, cam, dz = map(np.array, (real, reta, cam, dz))
    e = np.abs(cam - real) / real * 100
    er = np.abs(reta - real) / real * 100
    alto = dz >= 150
    return {"mapa": mapa, "pares": len(real), "total": len(pares), "erro_mediano_%": float(np.median(e)), "p90_%": float(np.percentile(e, 90)), "dentro_15%": float(np.mean(e <= 15) * 100),
            "vies_s": float(np.median(cam - real)), "reta_mediano_%": float(np.median(er)), "reta_dentro_15%": float(np.mean(er <= 15) * 100),
            "entre_andares": int(alto.sum()), "erro_entre_andares_%": float(np.median(e[alto])) if alto.sum() >= 3 else None,
            "reta_entre_andares_%": float(np.median(er[alto])) if alto.sum() >= 3 else None}


if __name__ == "__main__":
    for m in sys.argv[1:]:
        for fio in (True, False):
            r = avalia(m, fio)
            print(("com fio puxado" if fio else "sem fio puxado"), {k: (round(v, 2) if isinstance(v, float) else v) for k, v in r.items()})


def so_malha(d: dict) -> dict:
    """O mesmo grafo sem as células do corpus (para medir a malha sozinha, e o que o fio puxado melhora nela)."""
    nc = d["nc"]
    e, ant, novo = d["e"], 0, []
    ant_novo = 0
    for k in range(0, len(e), 2):
        ant += e[k]
        a, b = ant, e[k + 1]
        if a >= nc and b >= nc:
            novo += [(a - nc) - ant_novo, b - nc]
            ant_novo = a - nc
    return {**d, "nc": 0, "p": d["p"][3 * nc:], "e": novo}
