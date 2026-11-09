"""C0 (Comandos na prancheta), só leitura: dá para achar "a molotov real que cai em X, do mesmo lado, perto de onde o jogador está, com o voo conhecido"?

    py -3.12 -m pesquisa.comandos_c0_biblioteca <saida.json>

Para cada mapa com biblioteca e tabela de lugares: o nome do destino de cada molotov (o nome de lugar do mapa mais perto do ponto de queda, a mesma
regra de `lugarDe` em 11-reescrever-granada.js: bombsite só na primeira âncora, andar pelo corte da Nuke), os 3 destinos mais comuns, e para cada um,
por lado: quantas molotovs reais têm voo e efeito, de quantos pontos de lançamento distintos (agrupados a 150 u), e em que fração das posições reais de
jogadores do lado (a cada 4 s nos primeiros 45 s do round) existe uma dessas molotovs lançada a até 150 u (a regra do Reescrever R4) ou 400 u.
"""
from __future__ import annotations

import json
import math
import re
import sys
from collections import Counter
from pathlib import Path

import numpy as np
import polars as pl

from metrics.lugares import rotulos, tabela_do_mapa
from metrics.map_areas import floor_split_z
from scripts.build_lineups import INTERIM, PROCESSED, detect_tickrate, load_interim

RAIZ = Path(__file__).resolve().parent.parent
MAPAS = ["de_ancient", "de_anubis", "de_dust2", "de_inferno", "de_mirage", "de_nuke", "de_overpass"]
RAIOS = (150, 400)


def nome_mais_perto(tab, anc, radar, x, y, andar):
    px, py = (x - radar["origin_x"]) * radar["scale_px_per_unit"], (radar["origin_y"] - y) * radar["scale_px_per_unit"]
    melhor, dm = None, math.inf
    for ix, pts in anc[andar]:
        if re.fullmatch(r"Bombsite[A-Z]", tab["nomes"][ix]):
            pts = pts[:1]
        for ax, ay in pts:
            d = math.hypot(ax - px, ay - py)
            if d < dm:
                dm, melhor = d, tab["nomes"][ix]
    return melhor


def pontos_dos_jogadores(mapa: str, ids: set) -> dict:
    """Posições (x, y, lado) a cada 4 s nos primeiros 45 s do round, de jogadores vivos."""
    saida = {"t": [], "ct": []}
    for nome in sorted(ids):
        t = load_interim(INTERIM, nome)
        rounds = pl.read_parquet(PROCESSED / nome / "rounds.parquet")
        tr = int(detect_tickrate(rounds, t["ticks"])["tickrate"])
        for r in rounds.iter_rows(named=True):
            if r["freeze_end"] is None:
                continue
            a = r["freeze_end"]
            g = (t["ticks"].filter((pl.col("round_num") == r["round_num"]) & pl.col("is_alive") & (pl.col("tick") >= a) & (pl.col("tick") <= a + 45 * tr)
                                   & ((pl.col("tick") - a) % (4 * tr) == 0)).select("side", "X", "Y"))
            for s, x, y in g.iter_rows():
                if s in saida:
                    saida[s].append((x, y))
    return {k: np.array(v) for k, v in saida.items()}


def main() -> None:
    saida = {}
    for mapa in MAPAS:
        arq = RAIZ / "data" / "lineups" / f"{mapa}.json"
        tab = tabela_do_mapa(mapa)
        radar = json.loads((RAIZ / "assets" / "radars" / f"{mapa}.json").read_text(encoding="utf-8"))
        anc = rotulos(tab); corte = floor_split_z(mapa)
        arr = [a for a in json.loads(arq.read_text(encoding="utf-8"))["arremessos"] if a["arma"] == "molotov"]
        for a in arr:
            andar = 1 if (corte is not None and len(anc) > 1 and a["destino"][2] < corte) else 0
            a["_lugar"] = nome_mais_perto(tab, anc, radar, a["destino"][0], a["destino"][1], andar)
        uteis = [a for a in arr if a["voo_s"] is not None and a.get("efeito_s") is not None]
        comuns = [n for n, _ in Counter(a["_lugar"] for a in uteis).most_common(3)]
        pts = pontos_dos_jogadores(mapa, {a["partida"] for a in json.loads(arq.read_text(encoding="utf-8"))["arremessos"]})
        linhas = []
        for lugar in comuns:
            for lado in ("t", "ct"):
                ar = [a for a in uteis if a["_lugar"] == lugar and a["lado"] == lado]
                if not ar:
                    linhas.append({"destino": lugar, "lado": lado, "molotovs_com_voo_e_efeito": 0}); continue
                orig = np.array([[a["origem"][0], a["origem"][1]] for a in ar])
                pontos = []
                for o in orig:                                              # pontos de lançamento distintos (guloso, 150 u)
                    if all(math.hypot(o[0] - p[0], o[1] - p[1]) > 150 for p in pontos):
                        pontos.append(o)
                P = pts[lado]
                d = np.hypot(P[:, None, 0] - orig[None, :, 0], P[:, None, 1] - orig[None, :, 1]).min(axis=1) if len(P) else np.array([])
                linhas.append({"destino": lugar, "lado": lado, "molotovs_com_voo_e_efeito": len(ar), "pontos_de_lancamento": len(pontos),
                               "cobertura": {str(r): round(float((d <= r).mean()), 3) for r in RAIOS}, "posicoes_testadas": int(len(P))})
        saida[mapa] = {"molotovs": len(arr), "com_voo_e_efeito": len(uteis), "sem_nome": sum(1 for a in arr if a["_lugar"] is None), "destinos": linhas}
        print(mapa, saida[mapa]["molotovs"], saida[mapa]["com_voo_e_efeito"], flush=True)
    Path(sys.argv[1]).write_text(json.dumps(saida, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
