"""Galil ou FAMAS com colete (rifle_t2|colete, grupo "força" da decisão 8i): a vitória separada pelo grupo de
compra do ADVERSÁRIO naquele round (eco, pistola, força ou compra cheia), com os rounds em cada célula.

Pergunta do Pedro (fase 17): os 61% dessa linha vêm da força da compra ou de ela costumar enfrentar o eco do
outro time (o time que ganhou a pistola e joga contra o eco)? Só mede; não muda classificação nem número
publicado. A fonte é a mesma da tabela da 8i: `scripts.fit_economia.confrontos_do_corpus` (um registro por
round, time, classe dele e classe do adversário, com o peso do EMPATE DIVIDIDO da 8i) e o grupo de compra de
`metrics.economia.grupo_de_compra`. Rounds são time-rounds com o peso do empate (por isso há frações).

Uso:
    py -3.12 -m pesquisa.galil_famas_por_adversario
"""
from __future__ import annotations

import sys

import polars as pl

from metrics.economia import grupo_de_compra
from scripts.fit_economia import confrontos_do_corpus

ROTULO = {"eco": "eco", "pistola": "pistola", "forca": "força", "cheia": "compra cheia"}
ORDEM = ("eco", "pistola", "forca", "cheia")


def tabela(conf: pl.DataFrame, grupo: str = "rifle_t2") -> pl.DataFrame:
    """Vitória da classe `grupo` com colete por grupo do adversário: rounds (soma dos pesos) e taxa ponderada."""
    gal = conf.filter((pl.col("grupo") == grupo) & pl.col("colete")).with_columns(
        pl.struct(["grupo_dele", "colete_dele"]).map_elements(
            lambda r: grupo_de_compra(r["grupo_dele"], r["colete_dele"]), return_dtype=pl.Utf8).alias("adversario"))
    t = (gal.group_by("adversario", maintain_order=True)
         .agg(pl.col("peso").sum().alias("rounds"),
              (pl.col("peso") * pl.col("venceu").cast(pl.Float64)).sum().alias("vitorias")))
    total = gal.select(pl.lit("total").alias("adversario"), pl.col("peso").sum().alias("rounds"),
                       (pl.col("peso") * pl.col("venceu").cast(pl.Float64)).sum().alias("vitorias"))
    ordem = {g: i for i, g in enumerate(ORDEM + ("total",))}
    return (pl.concat([t, total])
            .with_columns((pl.col("vitorias") / pl.col("rounds")).alias("vitoria"),
                          pl.col("adversario").replace_strict(ordem, return_dtype=pl.Int64).alias("_o"))
            .sort("_o").drop("_o"))


def _br(x: float) -> str:
    return f"{x:.1f}".replace(".", ",")


def imprime(t: pl.DataFrame, titulo: str) -> None:
    n_total = float(t.filter(pl.col("adversario") == "total")["rounds"][0])
    print(f"\n{titulo}\n")
    print("| grupo do adversário | rounds | fração dos rounds | vitória |")
    print("|---|---|---|---|")
    for r in t.iter_rows(named=True):
        nome = "**total**" if r["adversario"] == "total" else ROTULO[r["adversario"]]
        print(f"| {nome} | {_br(r['rounds'])} | {r['rounds'] / n_total:.0%} | {r['vitoria']:.0%} |")


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    conf = confrontos_do_corpus()
    print(f"{conf['match_id'].n_unique()} partidas")
    imprime(tabela(conf, "rifle_t2"), "Galil ou FAMAS com colete (rifle_t2, força), por grupo do adversário")
    # para comparar: a compra cheia de rifle (rifle_t1 com colete) contra os mesmos grupos
    imprime(tabela(conf, "rifle_t1"), "Comparação: rifle de primeira linha com colete (rifle_t1, compra cheia)")


if __name__ == "__main__":
    main()
