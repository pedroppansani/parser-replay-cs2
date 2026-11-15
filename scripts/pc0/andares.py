"""PC0: como cada fonte trata os ANDARES (Nuke, Vertigo): faixa de altura, a maior componente fortemente conexa do grafo, as ligações verticais (escada, rampa, queda, escada de mão) e o que o corpus mostra.

    py -3.12 -m scripts.pc0.andares PASTA_DOS_NAV_JSON [mapas...]"""
from __future__ import annotations

import sys
from pathlib import Path

import networkx as nx
import numpy as np

from scripts.build_tempos import rastros
from scripts.pc0.grafo_corpus import GrafoCorpus
from scripts.pc0.grafo_nav import Grafo


def main(pasta: Path, mapas: list[str]) -> None:
    for m in mapas:
        g = Grafo(pasta / f"{m}.json")
        zs = np.array([g.cent[i][2] for i in g.ids])
        G = nx.DiGraph()
        for a, bs in g.lig.items():
            for b in bs:
                G.add_edge(a, b)
        scc = max(nx.strongly_connected_components(G), key=len)
        vert = [(a, b) for a, bs in g.lig.items() for b in bs if abs(g.cent[b][2] - g.cent[a][2]) >= 100]
        quedas = [(a, b) for a, b in vert if g.cent[b][2] - g.cent[a][2] <= -100 and a not in g.lig.get(b, [])]      # só desce (sem a volta): queda
        print(f"{m}: nav z {zs.min():.0f}..{zs.max():.0f}; {len(g.ids)} áreas; maior componente fortemente conexa {100 * len(scc) / len(g.ids):.0f}%; escadas de mão {g.escadas}; ligações verticais (>=100 u) {len(vert)}, das quais quedas de uma mão só {len(quedas)}")
        rs = rastros(m)
        if not rs:
            print("   corpus: nenhuma partida deste mapa")
            continue
        gc = GrafoCorpus(rs, s=64, zs=48, min_visitas=3, min_ligacoes=2)
        cz = np.array([gc.centro[c][2] for c in gc.celulas])
        vc = [(a, b) for a, bs in gc.adj.items() for b in bs if abs(gc.centro[b][2] - gc.centro[a][2]) >= 100]
        qc = [(a, b) for a, b in vc if gc.centro[b][2] - gc.centro[a][2] <= -100 and a not in gc.adj.get(b, [])]
        print(f"   corpus: z {cz.min():.0f}..{cz.max():.0f}; {len(gc.celulas)} células; ligações verticais (>=100 u) {len(vc)}, das quais queda de uma mão só {len(qc)}")


if __name__ == "__main__":
    main(Path(sys.argv[1]), sys.argv[2:] or ["de_nuke", "de_vertigo", "de_mirage"])
