"""Varredura da definição de trade contra DOIS gabaritos oficiais da HLTV.

    py -3.12 -m scripts.varre_trade

Gabaritos:
  - KAST de 310 jogadores (data/reference/hltv_componentes.json);
  - mortes trocadas, D(t), de 50 jogadores (data/reference/hltv_detalhado.json).

Dimensões varridas: janela em segundos, quem pode vingar (companheiro ou
qualquer um) e distância máxima entre o vingador e o lugar da morte.

A curva inteira é impressa de propósito: um ótimo estreito, cercado de valores
ruins, é coincidência do corpus; um ótimo largo e suave é regra.
"""
import json
import os
import sys
from pathlib import Path

import numpy as np
import polars as pl

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)
from metrics.basic_metrics import roster_per_round  # noqa: E402
from parsing.parser import load_interim  # noqa: E402

TR = 64
JANELAS = [1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 4.25, 4.5, 5.0, 5.5, 6.0, 7.0, 8.0]
DISTANCIAS = [None, 500.0, 900.0, 1500.0]

comp = json.loads((ROOT / "data/reference/hltv_componentes.json").read_text(encoding="utf-8"))["partidas"]
det = json.loads((ROOT / "data/reference/hltv_detalhado.json").read_text(encoding="utf-8"))
AP = {"sh1ro": "SH1R0", "mzinho": "Mzinho", "Techno": "Techno4K"}
mapas_da_serie = {m: s for s, v in det["series"].items() if v["serie_completa_no_corpus"] for m in v["mapas"]}
ids = sorted(set(comp) | set(mapas_da_serie))
DADOS = {m: load_interim(ROOT / "data/interim", m) for m in ids}


def trocas(k, janela_s, por_quem, dist_max):
    """(round, vítima) -> morte trocada, na definição pedida."""
    inim = k.filter(pl.col("attacker_steamid").is_not_null() & (pl.col("attacker_side") != pl.col("victim_side")))
    a = inim.select("round_num", "tick", pl.col("victim_steamid").alias("v"),
                    pl.col("attacker_steamid").alias("mat"), pl.col("victim_side").alias("lv"),
                    pl.col("victim_X").alias("vx"), pl.col("victim_Y").alias("vy"))
    b = k.select("round_num", pl.col("tick").alias("t2"), pl.col("victim_steamid").alias("mat"),
                 pl.col("attacker_side").alias("lvin"), pl.col("attacker_X").alias("ax"),
                 pl.col("attacker_Y").alias("ay"))
    j = a.join(b, on=["round_num", "mat"]).filter(
        (pl.col("t2") >= pl.col("tick")) & (pl.col("t2") - pl.col("tick") <= janela_s * TR))
    if por_quem == "companheiro":
        j = j.filter(pl.col("lvin") == pl.col("lv"))
    if dist_max is not None:
        j = j.filter(((pl.col("ax") - pl.col("vx")) ** 2 + (pl.col("ay") - pl.col("vy")) ** 2).sqrt() <= dist_max)
    return j.select("round_num", pl.col("v").alias("steamid")).unique(maintain_order=True)


def kast_rounds(t, trocadas):
    """KAST por jogador com a marcação de trade dada."""
    k = t["kills"]
    roster = roster_per_round(t["ticks"]).select("round_num", "steamid", "name").unique(maintain_order=True)
    inim = k.filter(pl.col("attacker_steamid").is_not_null() & (pl.col("attacker_side") != pl.col("victim_side")))
    K = inim.select("round_num", pl.col("attacker_steamid").alias("steamid")).unique(maintain_order=True).with_columns(pl.lit(True).alias("K"))
    a = k.filter(pl.col("assister_steamid").is_not_null() & ~pl.col("assistedflash").fill_null(False))
    A = a.select("round_num", pl.col("assister_steamid").alias("steamid")).unique(maintain_order=True).with_columns(pl.lit(True).alias("A"))
    D = k.select("round_num", pl.col("victim_steamid").alias("steamid")).unique(maintain_order=True).with_columns(pl.lit(True).alias("D"))
    T = trocadas.with_columns(pl.lit(True).alias("T"))
    pr = roster
    for x in (K, A, D, T):
        pr = pr.join(x.with_columns(pl.col("round_num").cast(roster.schema["round_num"]),
                                    pl.col("steamid").cast(roster.schema["steamid"])),
                     on=["round_num", "steamid"], how="left")
    pr = pr.with_columns([pl.col(c).fill_null(False) for c in ("K", "A", "D", "T")])
    pr = pr.with_columns((pl.col("K") | pl.col("A") | ~pl.col("D") | pl.col("T")).alias("kast"))
    return dict(pr.group_by("name", maintain_order=True).agg(pl.col("kast").sum()).iter_rows())


linhas = []
for janela in JANELAS:
    for por_quem in ("companheiro", "qualquer"):
        for dist in DISTANCIAS:
            kast_ok = kast_n = 0
            dt_ok = dt_n = dt_dif = 0
            por_serie = {}
            for mid, t in DADOS.items():
                tro = trocas(t["kills"], janela, por_quem, dist)
                if mid in comp:
                    nosso = kast_rounds(t, tro)
                    for nome, j in comp[mid]["jogadores"].items():
                        n2 = nome if nome in nosso else AP.get(nome, nome)
                        if n2 in nosso:
                            kast_n += 1
                            kast_ok += int(nosso[n2] == j["kast_rounds"])
                if mid in mapas_da_serie:
                    nome_por_id = dict(t["ticks"].group_by("steamid", maintain_order=True).agg(pl.col("name").last()).iter_rows())
                    cont = tro.group_by("steamid", maintain_order=True).len()
                    acc = por_serie.setdefault(mapas_da_serie[mid], {})
                    for sid, n in cont.iter_rows():
                        nome = nome_por_id.get(sid)
                        acc[nome] = acc.get(nome, 0) + n
            for serie, acc in por_serie.items():
                for nome, j in det["series"][serie]["jogadores"].items():
                    n2 = nome if nome in acc else AP.get(nome, nome)
                    dt_n += 1
                    dt_ok += int(acc.get(n2, 0) == j["mortes_trocadas"])
                    dt_dif += acc.get(n2, 0) - j["mortes_trocadas"]
            linhas.append({"janela_s": janela, "vingada_por": por_quem, "dist_max": dist or 0,
                           "kast_exatos": kast_ok, "kast_n": kast_n,
                           "dt_exatos": dt_ok, "dt_n": dt_n, "dt_soma_dif": dt_dif})
            print(f"janela {janela:>4}s  {por_quem:<12} dist {str(dist or '-'):>5}  "
                  f"KAST {kast_ok:>3}/{kast_n}   D(t) {dt_ok:>2}/{dt_n} (soma {dt_dif:+d})", flush=True)

print("\nLeitura: pico LARGO e suave é regra; um ótimo estreito, cercado de valores ruins,\nseria coincidência do corpus. A janela em uso vive em\nmetrics/basic_metrics.DEFAULT_TRADE_WINDOW_SECONDS.")
