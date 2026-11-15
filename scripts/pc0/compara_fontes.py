"""PC0: as duas fontes de caminho (o grafo do `.nav` e o grafo das trajetórias do corpus) contra a reta, nos pares com tempo real da C3.

    py -3.12 -m scripts.pc0.compara_fontes de_mirage PASTA_DOS_NAV_JSON

Sai, para cada fonte: cobertura (pares com caminho), erro mediano em % e dentro de 15%, com 250 u/s. O grafo do corpus roda duas vezes: com todas as partidas (o teto) e com METADE (as de índice
par; a outra metade não entra no grafo): é o que se espera de um par que o corpus nunca viu. A tabela da C3 (o tempo real) usa todas as partidas nos dois casos."""
from __future__ import annotations

import json
import math
import sys
import time
from pathlib import Path

import numpy as np

from scripts.build_tempos import rastros
from scripts.pc0.compara_tempos import V, z_dos_nos
from scripts.pc0.grafo_corpus import GrafoCorpus
from scripts.pc0.grafo_nav import Grafo


def avalia(nome: str, f, pares, nos, zn) -> dict:
    real, reta, cam, dzs = [], [], [], []
    for a, b, p25, med, p75, casos, partidas in pares:
        if a not in nos or b not in nos:
            continue
        pa, pb = (*nos[a], zn[a]), (*nos[b], zn[b])
        r = f(pa, pb)
        if r is None:
            continue
        real.append(med)
        reta.append(math.hypot(pa[0] - pb[0], pa[1] - pb[1]) / V)
        cam.append(r[1] / V)
        dzs.append(abs((zn[a] or 0) - (zn[b] or 0)))
    real, reta, cam, dzs = map(np.array, (real, reta, cam, dzs))
    e = np.abs(cam - real) / real * 100
    er = np.abs(reta - real) / real * 100
    alto = dzs >= 150      # pares entre andares (os nós diferem em z por 150 u ou mais)
    extra = {}
    if alto.sum() >= 3:
        extra = {"entre_andares": int(alto.sum()), "erro_%_entre_andares": round(float(np.median(e[alto])), 1), "reta_%_entre_andares": round(float(np.median(er[alto])), 1),
                 "erro_%_mesmo_andar": round(float(np.median(e[~alto])), 1), "reta_%_mesmo_andar": round(float(np.median(er[~alto])), 1)}
    return {**extra, "fonte": nome, "pares": len(real), "total": len(pares), "cobertura_%": round(100 * len(real) / len(pares)), "erro_%_mediano": round(float(np.median(e)), 1),
            "p90_%": round(float(np.percentile(e, 90)), 1), "dentro_15%": round(float(np.mean(e <= 15) * 100)), "vies_s": round(float(np.median(cam - real)), 2),
            "reta_nos_mesmos_pares_%_mediano": round(float(np.median(er)), 1), "reta_dentro_15%": round(float(np.mean(er <= 15) * 100))}


def main(mapa: str, pasta: Path) -> None:
    t = json.loads(Path(f"data/tempos/{mapa}.json").read_text(encoding="utf-8"))
    if t["pontos"]:
        lista_nos, pares = t["nos"], t["pontos"]
    else:      # o mapa só tem pares de ÁREAS da demo (âncora de cada área, do contexto dos comandos)
        from scripts.comandos_contexto import contexto
        lista_nos = [[a["nome"], a["x"], a["y"], a["andar"] if a["andar"] in ("cima", "baixo") else ""] for a in contexto(mapa, so_conferidos=False)["areas"]]
        pares = t["areas"]
    nos = {n[0]: (n[1], n[2]) for n in lista_nos}
    zn = z_dos_nos(lista_nos, mapa)
    rs = rastros(mapa)
    partidas = sorted({r["partida"] for r in rs})
    saida = []
    g = Grafo(pasta / f"{mapa}.json")
    saida.append(avalia("nav (fio puxado)", g.comprimento_entre_pontos, pares, nos, zn))
    t0 = time.time()
    gc = GrafoCorpus(rs)
    print(f"grafo do corpus (todas): {len(gc.celulas)} células, {gc.ligacoes} ligações; {time.time() - t0:.0f}s")
    saida.append(avalia("corpus, todas as partidas", gc.comprimento_entre_pontos, pares, nos, zn))
    metade = set(partidas[::2])
    gm = GrafoCorpus([r for r in rs if r["partida"] in metade])
    print(f"grafo do corpus (metade, {len(metade)} partidas): {len(gm.celulas)} células, {gm.ligacoes} ligações")
    saida.append(avalia("corpus, metade das partidas", gm.comprimento_entre_pontos, pares, nos, zn))
    for s in saida:
        print(s)


if __name__ == "__main__":
    main(sys.argv[1], Path(sys.argv[2]))
