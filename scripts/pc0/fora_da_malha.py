"""PC0: o que o corpus mostra que a malha do `.nav` NÃO tem (pulos, quedas, apoios), e o quanto o corpus cobre do que a malha tem.

    py -3.12 -m scripts.pc0.fora_da_malha de_mirage PASTA_DOS_NAV_JSON [N_MIN_RASTROS]

1. fidelidade da malha: a fração das células do corpus (pesadas pelas visitas) que caem DENTRO de uma área do `.nav` (o jogador pisou onde a malha diz que se pisa);
2. passagens fora da malha: pares de áreas A -> B que jogadores de verdade fizeram (amostras seguidas) e que o `.nav` NÃO liga (nem A == B), com a altura da queda e quantos rastros; é onde mora
   "pular da janela pro L" se os jogadores fazem isso;
3. cobertura do corpus: a fração da área caminhável da malha (pelo tamanho das áreas) a até 60 u de uma célula do corpus."""
from __future__ import annotations

import json
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path

from scripts.build_tempos import rastros
from scripts.pc0.grafo_corpus import GrafoCorpus
from scripts.pc0.grafo_nav import Grafo


SALTOS = 3      # uma célula de 40 u pode pular uma ou duas áreas pequenas da malha: "ligada" vale até este número de ligações da malha


def alcance(g: Grafo, a: int, k: int) -> set[int]:
    vistos, borda = {a}, {a}
    for _ in range(k):
        borda = {v for u in borda for v in g.lig[u]} - vistos
        vistos |= borda
    return vistos


def main(mapa: str, pasta: Path, n_min: int = 3) -> None:
    g = Grafo(pasta / f"{mapa}.json")
    gc = GrafoCorpus(rastros(mapa))
    # 1. fidelidade: cada célula do corpus vira a área da malha que a contém (z compatível)
    area_de: dict = {}
    dentro = fora = 0
    for c in gc.celulas:
        x, y, z = gc.centro[c]
        a = g.area_do_ponto(x, y, z, tol_xy=1.0)
        ok = a is not None and abs(g.cent[a][2] - z) < 110
        area_de[c] = a if ok else None
        peso = gc.visitas[c]
        if ok:
            dentro += peso
        else:
            fora += peso
    print(f"{mapa}: {len(gc.celulas)} células; visitas dentro de uma área da malha {100 * dentro / (dentro + fora):.1f}%; fora {100 * fora / (dentro + fora):.1f}%")
    # 2. passagens fora da malha
    pares: Counter = Counter()
    dz: dict = defaultdict(list)
    for (a, b), n in gc.n_lig.items():
        na, nb = area_de[a], area_de[b]
        if na is None or nb is None or na == nb:
            continue
        if nb not in alcance(g, na, SALTOS):
            pares[(na, nb)] += n
            dz[(na, nb)].append(gc.centro[b][2] - gc.centro[a][2])
    todos = sum(gc.n_lig[(a, b)] for (a, b) in gc.n_lig if area_de[a] is not None and area_de[b] is not None and area_de[a] != area_de[b])
    fora_n = sum(pares.values())
    print(f"passagens entre áreas diferentes: {todos}; que a malha NÃO liga (nem em {SALTOS} ligações): {fora_n} ({100 * fora_n / max(1, todos):.1f}%); pares de áreas distintos: {len(pares)}")
    DZ_MIN = float(sys.argv[4]) if len(sys.argv) > 4 else 0.0
    relevantes = [(k, n) for k, n in pares.items() if n >= n_min and abs(sum(dz[k]) / len(dz[k])) >= DZ_MIN]
    quedas = [(k, n) for k, n in pares.items() if n >= n_min and sum(dz[k]) / len(dz[k]) <= -60]
    print(f"quedas de 60 u ou mais fora da malha, com {n_min}+ rastros: {len(quedas)}")
    print(f"pares fora da malha com {n_min} rastros ou mais: {len(relevantes)}")
    saida = []
    for (na, nb), n in sorted(relevantes, key=lambda kv: -kv[1])[:25]:
        d = sum(dz[(na, nb)]) / len(dz[(na, nb)])
        ca, cb = g.cent[na], g.cent[nb]
        saida.append({"de": [round(v) for v in ca], "para": [round(v) for v in cb], "rastros": n, "dz": round(d), "vizinhas_na_malha": nb in g.lig[na] or na in g.lig[nb]})
        print(f"  ({ca[0]:.0f},{ca[1]:.0f},z{ca[2]:.0f}) -> ({cb[0]:.0f},{cb[1]:.0f},z{cb[2]:.0f})  {n} rastros  dz {d:+.0f}  {'(a volta existe)' if na in g.lig[nb] else ''}")
    # 3. cobertura do corpus sobre a malha
    cobre = 0.0
    total = 0.0
    centros = list(gc.celulas)
    por_grade: dict = defaultdict(list)
    for c in centros:
        x, y, z = gc.centro[c]
        por_grade[(int(x // 100), int(y // 100))].append((x, y, z))
    for i, a in g.areas.items():
        cx, cy, cz = g.cent[i]
        tam = abs(float((g.poly[i][1][0] - g.poly[i][0][0]) * (g.poly[i][-1][1] - g.poly[i][0][1]) - (g.poly[i][1][1] - g.poly[i][0][1]) * (g.poly[i][-1][0] - g.poly[i][0][0]))) if len(g.poly[i]) >= 3 else 0.0
        total += tam
        achou = False
        for gx in range(int(cx // 100) - 1, int(cx // 100) + 2):
            for gy in range(int(cy // 100) - 1, int(cy // 100) + 2):
                for (x, y, z) in por_grade.get((gx, gy), []):
                    if math.hypot(x - cx, y - cy) < 60 and abs(z - cz) < 60:
                        achou = True
                        break
                if achou:
                    break
            if achou:
                break
        if achou:
            cobre += tam
    print(f"cobertura do corpus sobre a área caminhável da malha: {100 * cobre / total:.0f}%")
    Path("notas/logs").mkdir(exist_ok=True)
    Path(f"notas/logs/pc0-fora-da-malha-{mapa}.json").write_text(json.dumps(saida, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main(sys.argv[1], Path(sys.argv[2]), int(sys.argv[3]) if len(sys.argv) > 3 else 3)
