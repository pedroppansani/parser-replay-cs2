"""PC0: o erro do tempo pelo CAMINHO (grafo do `.nav`) contra o erro da RETA, nos pares que têm tempo real na tabela da C3 (`data/tempos/<mapa>.json`).

    py -3.12 -m scripts.pc0.compara_tempos de_mirage PASTA_DOS_NAV_JSON [SAIDA.json]

Para cada par de nós da tabela (pontos do Pedro): reta = distância / 250 u/s (o "não antes de" da C3); caminho = comprimento do caminho no grafo / 250. O tempo real é a mediana da C3.
Sai o erro da reta e do caminho contra a mediana (em s e em %), com a velocidade de 250 u/s e depois com UMA velocidade média calibrada no conjunto, e a cobertura (pares sem caminho)."""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np

from scripts.build_tempos import rastros
from scripts.pc0.grafo_nav import Grafo

V = 250.0


def z_dos_nos(nos: list, mapa: str) -> dict:
    """O z de cada nó: a mediana do z dos rastros a até 120 u dele (os andares sobrepostos se resolvem pelo corpus)."""
    xs, ys, zs = [], [], []
    for r in rastros(mapa):
        xs.append(r["x"])
        ys.append(r["y"])
        zs.append(r["z"])
    x, y, z = np.concatenate(xs), np.concatenate(ys), np.concatenate(zs)
    saida = {}
    from metrics.map_areas import floor_split_z
    corte = floor_split_z(mapa)
    for chave, nx_, ny_, andar in nos:
        m = np.hypot(x - nx_, y - ny_) < 120
        if corte is not None and andar in ("cima", "baixo"):      # mapa de dois andares: só o z do andar do nó
            m &= (z >= corte) if andar == "cima" else (z < corte)
        saida[chave] = float(np.median(z[m])) if m.sum() >= 5 else None
    return saida


def main(mapa: str, pasta: Path, saida: Path) -> None:
    t = json.loads(Path(f"data/tempos/{mapa}.json").read_text(encoding="utf-8"))
    nos = {n[0]: (n[1], n[2]) for n in t["nos"]}
    zn = z_dos_nos(t["nos"], mapa)
    g = Grafo(pasta / f"{mapa}.json")
    linhas, sem = [], 0
    for a, b, p25, med, p75, casos, partidas in t["pontos"]:
        pa, pb = (*nos[a], zn[a]), (*nos[b], zn[b])
        reta = math.hypot(pa[0] - pb[0], pa[1] - pb[1])
        r = g.comprimento_entre_pontos(pa, pb)
        if r is None:
            sem += 1
            continue
        rota, comp = r
        linhas.append((a, b, med, reta / V, comp / V, casos, len(rota)))
    n = len(linhas)
    print(f"{mapa}: {len(t['pontos'])} pares com tempo real; caminho achado em {n}; sem caminho {sem}")
    real = np.array([x[2] for x in linhas])
    reta = np.array([x[3] for x in linhas])
    cam = np.array([x[4] for x in linhas])

    def rel(pred, nome):
        e = pred - real
        ep = np.abs(e) / real * 100
        print(f"  {nome:32s} erro médio absoluto {np.mean(np.abs(e)):.2f} s; mediano {np.median(np.abs(e)):.2f} s; erro % mediano {np.median(ep):.0f}%; p90 {np.percentile(ep, 90):.0f}%; viés mediano {np.median(e):+.2f} s; dentro de 15%: {np.mean(ep <= 15) * 100:.0f}%")
    rel(reta, "reta a 250 u/s")
    rel(cam, "caminho a 250 u/s")
    k_reta = float(np.median(real / reta))
    k_cam = float(np.median(real / cam))
    rel(reta * k_reta, f"reta calibrada (x{k_reta:.2f})")
    rel(cam * k_cam, f"caminho calibrado (x{k_cam:.2f})")
    print(f"  caminho/reta: mediana {np.median(cam / reta):.2f}, p10 {np.percentile(cam / reta, 10):.2f}, p90 {np.percentile(cam / reta, 90):.2f}")
    print(f"  o caminho a 250 u/s é MENOR que o tempo real em {np.mean(cam < real) * 100:.0f}% dos pares (esperado: o real inclui curvas)")
    saida.write_text(json.dumps([[x[0], x[1]] + [round(float(v), 3) for v in x[2:]] for x in linhas], ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    main(sys.argv[1], Path(sys.argv[2]), Path(sys.argv[3]) if len(sys.argv) > 3 else Path("notas/logs/pc0-pares.json"))
