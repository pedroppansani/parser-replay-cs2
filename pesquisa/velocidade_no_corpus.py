"""Velocidade de deslocamento medida no corpus (fase 8, item 8.1). Não muda nada.

A prancheta precisa do horário em que um jogador chega a cada ponto de um caminho
desenhado sem horário: distância / velocidade. A velocidade não é assumida: sai
dos ticks do corpus (64 por segundo), por arma na mão e por modo de andar.

MOVIMENTO LIVRE = regime estável: uma janela de JANELA_TICKS ticks seguidos do
mesmo jogador, vivo, no chão (subida ou descida de no máximo MAX_DZ_POR_TICK
por tick), com a mesma arma e o mesmo modo, em que a velocidade horizontal varia
pouco (coeficiente de variação abaixo de MAX_CV) e passa de MIN_VELOCIDADE (parado
não é andar). A velocidade da janela é a mediana dela. Isso tira a aceleração e a
frenagem, que não são a velocidade de quem atravessa o mapa. A sensibilidade a
essas escolhas sai na tabela (janela e CV alternativos).

Modos: correndo (sem shift e em pé), andando (shift, em pé), agachado.

Uso:
    py -3.12 -m pesquisa.velocidade_no_corpus [n_partidas]
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import polars as pl

RAIZ = Path(__file__).resolve().parents[1]
INTERIM = RAIZ / "data" / "interim"
MANIFESTO = RAIZ / "data" / "manifest.json"

JANELA_TICKS = 32          # meio segundo a 64 tick
MAX_CV = 0.05              # velocidade quase constante na janela
MAX_DZ_POR_TICK = 1.0      # unidades por tick: no chão (pulo e queda passam muito disso)
MIN_VELOCIDADE = 50.0      # u/s; abaixo é ajuste de posição, não deslocamento

GRUPOS = {
    "rifle": {"AK-47", "M4A4", "M4A1-S", "Galil AR", "FAMAS", "SG 553", "AUG"},
    "AWP": {"AWP"},
    "pistola": {"Glock-18", "USP-S", "P2000", "P250", "Five-SeveN", "Tec-9", "CZ75-Auto", "Desert Eagle",
                "Dual Berettas", "R8 Revolver"},
    "SMG": {"MP9", "MAC-10", "MP7", "MP5-SD", "UMP-45", "P90", "PP-Bizon"},
    "faca": None,              # qualquer arma com "knife"/"Knife"/"Karambit"... no nome
}


def grupo_da_arma(nome: str | None) -> str | None:
    if not nome:
        return None
    for g, nomes in GRUPOS.items():
        if nomes is not None and nome in nomes:
            return g
    n = nome.lower()
    if any(k in n for k in ("knife", "karambit", "bayonet", "daggers", "talon", "kukri", "faca")):
        return "faca"
    return None


def janelas(m: str, janela: int, max_cv: float) -> pl.DataFrame:
    t = pl.read_parquet(INTERIM / m / "ticks.parquet",
                        columns=["tick", "steamid", "X", "Y", "Z", "is_alive", "ducking", "is_walking",
                                 "is_scoped", "active_weapon_name", "round_num"])
    t = (t.filter(pl.col("is_alive")).sort(["steamid", "tick"])
         .with_columns(
             pl.col("active_weapon_name").map_elements(grupo_da_arma, return_dtype=pl.String).alias("grupo"),
             pl.when(pl.col("ducking")).then(pl.lit("agachado"))
               .when(pl.col("is_walking")).then(pl.lit("andando")).otherwise(pl.lit("correndo")).alias("modo"))
         .with_columns(
             ((pl.col("X").diff() ** 2 + pl.col("Y").diff() ** 2).sqrt() * 64
              / pl.col("tick").diff()).over("steamid").alias("v"),
             (pl.col("Z").diff().abs() / pl.col("tick").diff()).over("steamid").alias("dz"),
             (pl.col("tick").diff() == 1).over("steamid").alias("seguido"))
         .filter(pl.col("grupo").is_not_null() & ~pl.col("is_scoped")))
    # blocos de ticks seguidos com a mesma arma, o mesmo modo, no chão
    t = t.with_columns(
        (~pl.col("seguido") | (pl.col("grupo") != pl.col("grupo").shift(1).over("steamid"))
         | (pl.col("modo") != pl.col("modo").shift(1).over("steamid")) | (pl.col("dz") > MAX_DZ_POR_TICK))
        .fill_null(True).cum_sum().over("steamid").alias("bloco"))
    t = t.filter(pl.col("dz") <= MAX_DZ_POR_TICK)
    t = t.with_columns((pl.int_range(pl.len()).over(["steamid", "bloco"]) // janela).alias("janela"))
    j = (t.group_by(["steamid", "bloco", "janela"], maintain_order=True)
         .agg(pl.len().alias("n"), pl.col("v").median().alias("v_med"), pl.col("v").std().alias("v_std"),
              pl.col("grupo").first(), pl.col("modo").first())
         .filter((pl.col("n") == janela) & (pl.col("v_med") > MIN_VELOCIDADE)
                 & (pl.col("v_std") / pl.col("v_med") < max_cv)))
    return j.select("grupo", "modo", "v_med").with_columns(pl.lit(m).alias("partida"))


def mede(partidas: list[str], janela: int = JANELA_TICKS, max_cv: float = MAX_CV) -> pl.DataFrame:
    js = pl.concat([janelas(m, janela, max_cv) for m in partidas])
    return (js.group_by(["grupo", "modo"]).agg(pl.len().alias("janelas"), pl.col("partida").n_unique().alias("partidas"),
                                               pl.col("v_med").median().alias("mediana"),
                                               pl.col("v_med").quantile(0.25).alias("p25"),
                                               pl.col("v_med").quantile(0.75).alias("p75"))
            .sort(["grupo", "modo"]))


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 12
    man = json.loads(MANIFESTO.read_text(encoding="utf-8"))["partidas"]
    pro = sorted(m for m, v in man.items() if v.get("origem") == "profissional" and (INTERIM / m / "ticks.parquet").exists())
    partidas = pro[:n]
    base = mede(partidas)
    print(f"{len(partidas)} partidas profissionais ({partidas[0]} a {partidas[-1]}); janela {JANELA_TICKS} ticks, CV < {MAX_CV}\n")
    print("| arma | modo | mediana (u/s) | p25 | p75 | janelas | partidas |")
    print("|---|---|---|---|---|---|---|")
    for r in base.iter_rows(named=True):
        print(f"| {r['grupo']} | {r['modo']} | {r['mediana']:.1f} | {r['p25']:.1f} | {r['p75']:.1f} | {r['janelas']} | {r['partidas']} |")
    print("\nSensibilidade (mediana em u/s):")
    for jan, cv in ((16, 0.05), (64, 0.05), (32, 0.02), (32, 0.10)):
        alt = mede(partidas, jan, cv)
        linha = ", ".join(f"{r['grupo']}/{r['modo']} {r['mediana']:.1f}" for r in alt.iter_rows(named=True)
                          if r["grupo"] in ("rifle", "AWP"))
        print(f"  janela {jan}, CV < {cv}: {linha}")


if __name__ == "__main__":
    main()
