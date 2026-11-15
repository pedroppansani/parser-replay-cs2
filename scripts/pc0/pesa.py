"""PC0: o PESO do dado de caminho por mapa e o quanto o erro do tempo muda ao enxugá-lo.

    py -3.12 -m scripts.pc0.pesa de_mirage PASTA_DOS_NAV_JSON

Dois formatos, os dois como o site os entregaria (um arquivo `.js` que chama uma função com um JSON; o servidor manda comprimido, então o tamanho que importa é o gzip e o brotli):
  corpus: {"p": [x, y, z, x, y, z, ...] (int16, o centro de cada célula), "e": [de, para, de, para, ...] (índices, em ordem, com o `de` em delta)};
  nav:    o mesmo, com o centro de cada área da malha e as ligações dirigidas (sem os polígonos: só serve ao caminho pelos centros).
Variantes do corpus: lado da célula (40, 64, 96 u) e ligações com 2 ou 3 rastros no mínimo; para cada uma, o erro do tempo contra o real da C3 (mediana, em %)."""
from __future__ import annotations

import gzip
import json
import math
import sys
import zlib
from pathlib import Path

import numpy as np

from scripts.build_tempos import rastros
from scripts.pc0.compara_fontes import avalia
from scripts.pc0.compara_tempos import z_dos_nos
from scripts.pc0.grafo_corpus import GrafoCorpus
from scripts.pc0.grafo_nav import Grafo


def pacote(centros: list[tuple[float, float, float]], arestas: list[tuple[int, int]]) -> dict:
    arestas = sorted(arestas)
    e, ant = [], 0
    for a, b in arestas:
        e += [a - ant, b]
        ant = a
    return {"p": [int(round(v)) for c in centros for v in c], "e": e}


def tamanhos(obj: dict) -> tuple[int, int, int]:
    txt = ("recebe(" + json.dumps(obj, separators=(",", ":")) + ");").encode("utf-8")
    try:
        import brotli
        br = len(brotli.compress(txt, quality=9))
    except ImportError:
        br = -1
    return len(txt), len(gzip.compress(txt, 9)), br


def main(mapa: str, pasta: Path) -> None:
    t = json.loads(Path(f"data/tempos/{mapa}.json").read_text(encoding="utf-8"))
    pares = t["pontos"] if t["pontos"] else t["areas"]
    lista_nos = t["nos"]
    nos = {n[0]: (n[1], n[2]) for n in lista_nos}
    zn = z_dos_nos(lista_nos, mapa)
    rs = rastros(mapa)
    g = Grafo(pasta / f"{mapa}.json")
    ids = list(g.areas)
    pos = {i: k for k, i in enumerate(ids)}
    nav_pacote = pacote([g.cent[i] for i in ids], [(pos[a], pos[b]) for a in ids for b in g.lig[a] if b in pos])
    n, gz, br = tamanhos(nav_pacote)
    print(f"nav: {len(ids)} áreas, {len(nav_pacote['e']) // 2} ligações: {n / 1024:.0f} KB cru, {gz / 1024:.0f} KB gzip, {br / 1024:.0f} KB brotli")
    print(f"{'corpus':28} {'células':>8} {'ligações':>9} {'cru KB':>7} {'gzip KB':>8} {'brotli KB':>9} {'erro % med':>10} {'<=15%':>6} {'cobertura':>9}")
    for s, zs, mv, ml in [(40, 48, 3, 2), (40, 48, 3, 3), (64, 48, 3, 2), (64, 48, 3, 3), (96, 48, 3, 2), (96, 48, 5, 3)]:
        gc = GrafoCorpus(rs, s=s, zs=zs, min_visitas=mv, min_ligacoes=ml)
        cel = sorted(gc.celulas)
        idx = {c: k for k, c in enumerate(cel)}
        pk = pacote([gc.centro[c] for c in cel], [(idx[a], idx[b]) for a, bs in gc.adj.items() for b in bs])
        n, gz, br = tamanhos(pk)
        r = avalia("x", gc.comprimento_entre_pontos, pares, nos, zn)
        print(f"{'célula ' + str(s) + ' u, >=' + str(ml) + ' rastros':28} {len(cel):8d} {gc.ligacoes:9d} {n / 1024:7.0f} {gz / 1024:8.0f} {br / 1024:9.0f} {r['erro_%_mediano']:10.1f} {r['dentro_15%']:6d} {r['cobertura_%']:8d}%")


if __name__ == "__main__":
    main(sys.argv[1], Path(sys.argv[2]))
