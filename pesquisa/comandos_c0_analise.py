"""C0 (Comandos na prancheta), só leitura: nomes de lugar por mapa e tempos reais de corrida entre dois lugares.

    py -3.12 -m pesquisa.comandos_c0_analise <pasta_com_viagens.parquet> <saida.json>

Parte 1 (item 1): por mapa, os `place` dos ticks (nome do jogo) contra a tabela que o mapa desenha: quantos, o tamanho da área
em unidades do jogo, em quantos pedaços separados cada nome aparece e onde fica a âncora contra o ponto típico dos jogadores.
Parte 2 (itens 2 e 4): os pares de lugares com amostra suficiente e quanto a linha reta erra o caminho andado.
"""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
import polars as pl

from metrics.lugares import PASSO_TICKS, _celulas_por_nome, rotulos, tabela_do_mapa, texto_do_lugar
from scripts.build_lineups import INTERIM, PROCESSED

RAIZ = Path(__file__).resolve().parent.parent
MAPAS = ["de_ancient", "de_anubis", "de_dust2", "de_inferno", "de_mirage", "de_nuke", "de_overpass"]
V_CORRENDO = 210.0          # u/s: mediana do rifle correndo, nota 2026-10-04-velocidade-e-voo
MINIMOS = (5, 10, 20, 30)


def componentes(celulas: set) -> list[set]:
    resto, saida = set(celulas), []
    while resto:
        ini = resto.pop(); pilha, comp = [ini], {ini}
        while pilha:
            cx, cy = pilha.pop()
            for v in ((cx + 1, cy), (cx - 1, cy), (cx, cy + 1), (cx, cy - 1)):
                if v in resto:
                    resto.discard(v); comp.add(v); pilha.append(v)
        saida.append(comp)
    return saida


def nomes_do_mapa(mapa: str) -> dict:
    tab = tabela_do_mapa(mapa)
    radar = json.loads((RAIZ / "assets" / "radars" / f"{mapa}.json").read_text(encoding="utf-8"))
    esc, lado = radar["scale_px_per_unit"], tab["lado"]
    u_celula = lado / esc                                     # lado da célula em unidades do jogo
    ancoras = rotulos(tab)
    # os place crus dos ticks (todas as partidas do mapa)
    crus: dict[str, int] = defaultdict(int); pos: dict = defaultdict(list)
    for d in sorted(INTERIM.glob("match_*")):
        mm = PROCESSED / d.name / "match_meta.json"
        if not mm.exists() or json.loads(mm.read_text(encoding="utf-8"))["map_name"] != mapa:
            continue
        t = (pl.scan_parquet(d / "ticks.parquet").filter((pl.col("tick") % PASSO_TICKS == 0) & pl.col("is_alive") & pl.col("place").is_not_null() & (pl.col("place") != ""))
             .select("place", "X", "Y").collect())
        for p, n in t["place"].value_counts().iter_rows():
            crus[p] += n
        for p, g in t.group_by("place"):
            pos[p[0]].append(g.select("X", "Y").to_numpy())
    linhas = []
    for ix, nome in enumerate(tab["nomes"]):
        ped, area, anc = 0, 0, None
        for andar in range(len(tab["andares"])):
            cel = _celulas_por_nome(tab, andar).get(ix, set())
            if cel:
                ped += len([c for c in componentes(cel) if len(c) >= 4])     # pedaço com pelo menos 4 células (ruído de borda fora)
                area += len(cel) * u_celula ** 2
            for ixn, pts in ancoras[andar]:
                if ixn == ix and pts and anc is None:
                    anc = (radar["origin_x"] + pts[0][0] / esc, radar["origin_y"] - pts[0][1] / esc)    # unidades do jogo (inverso de `amostras`)
        xy = np.concatenate(pos[nome]) if pos[nome] else np.zeros((0, 2))
        tip = np.median(xy, axis=0) if len(xy) else None
        linhas.append({"nome": nome, "texto": texto_do_lugar(nome), "ticks": int(crus.get(nome, 0)), "area_u2": round(area), "lado_u": round(area ** 0.5),
                       "pedacos": ped, "andares": sum(1 for a in range(len(tab["andares"])) if _celulas_por_nome(tab, a).get(ix)),
                       "ancora_xy": None if anc is None else [round(anc[0]), round(anc[1])],
                       "ponto_tipico_xy": None if tip is None else [round(float(tip[0])), round(float(tip[1]))],
                       "ancora_a_tipico_u": None if anc is None or tip is None else round(float(np.hypot(anc[0] - tip[0], anc[1] - tip[1])))})
    return {"mapa": mapa, "lado_celula_px": lado, "u_por_celula": round(u_celula, 1), "place_crus": len(crus), "na_tabela": len(tab["nomes"]),
            "fora_da_tabela": sorted(set(crus) - set(tab["nomes"])), "ticks_fora": int(sum(v for k, v in crus.items() if k not in tab["nomes"])),
            "ticks_total": int(sum(crus.values())), "lugares": linhas}


def pares(v: pl.DataFrame) -> dict:
    saida = {}
    for mapa in MAPAS:
        tab = tabela_do_mapa(mapa); nomes = set(tab["nomes"])
        m = v.filter((pl.col("mapa") == mapa) & pl.col("de").is_in(nomes) & pl.col("para").is_in(nomes))
        corr = m.filter(~pl.col("com_parada") & (pl.col("andando") <= 0.1) & (pl.col("reta_u") >= 300))     # corrida sem parar, a pelo menos 300 u
        g = (corr.group_by(["de", "para"]).agg(n=pl.len(), partidas=pl.col("partida").n_unique(), mediana_s=pl.col("dur_s").median(),
                                                 p25_s=pl.col("dur_s").quantile(0.25), p75_s=pl.col("dur_s").quantile(0.75), entrada_s=pl.col("dur_entrada_s").median(),
                                                 reta_u=pl.col("reta_u").median(), caminho_u=pl.col("caminho_u").median(),
                                                 direta=pl.col("direta").mean())
             .with_columns((pl.col("caminho_u") / pl.col("reta_u")).alias("razao"), (pl.col("reta_u") / V_CORRENDO).alias("estimado_s")))
        total_pares = len(nomes) * (len(nomes) - 1)
        saida[mapa] = {"viagens_todas": m.height, "viagens_corrida": corr.height, "pares_possiveis": total_pares, "pares_vistos": g.height,
                       "pares_com_minimo": {str(k): int(g.filter(pl.col("n") >= k).height) for k in MINIMOS},
                       "partidas_do_mapa": int(m["partida"].n_unique())}
        ok = g.filter(pl.col("n") >= 10)
        if ok.height:
            erro = ((pl.Series(ok["estimado_s"]) - pl.Series(ok["mediana_s"])) / pl.Series(ok["mediana_s"]))
            saida[mapa]["reta_contra_real"] = {"pares_n10": ok.height, "razao_caminho_reta_mediana": round(float(ok["razao"].median()), 2),
                                               "erro_rel_mediano_da_reta": round(float(erro.median()), 2),
                                               "reta_subestima_em_pct_dos_pares": round(float((erro < 0).mean()), 2),
                                               "erro_abs_mediano_s": round(float((pl.Series(ok["estimado_s"]) - pl.Series(ok["mediana_s"])).abs().median()), 1),
                                               "mediana_da_mediana_s": round(float(ok["mediana_s"].median()), 1)}
        saida[mapa]["_tabela"] = g.sort("n", descending=True).head(400).to_dicts()
    return saida


def main() -> None:
    v = pl.read_parquet(Path(sys.argv[1]) / "viagens.parquet")
    res = {"nomes": [nomes_do_mapa(m) for m in MAPAS], "pares": pares(v)}
    Path(sys.argv[2]).write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    for n in res["nomes"]:
        print(n["mapa"], "crus", n["place_crus"], "tabela", n["na_tabela"], "fora", n["fora_da_tabela"], "ticks_fora", n["ticks_fora"], "/", n["ticks_total"])
    for m, p in res["pares"].items():
        print(m, {k: p[k] for k in p if k != "_tabela"})


if __name__ == "__main__":
    main()
