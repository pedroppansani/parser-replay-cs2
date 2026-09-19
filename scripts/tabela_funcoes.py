"""
Tabela de funções com os componentes abertos, por jogador, em todas as partidas
profissionais -- para conferir se cada rótulo é o que o jogador de fato faz.

    py -3.12 -m scripts.tabela_funcoes             # todos os times
    py -3.12 -m scripts.tabela_funcoes --time Vitality
    py -3.12 -m scripts.tabela_funcoes --csv saida.csv

Três leituras lado a lado, que NÃO se misturam (decisão 7d):
  1. função estrutural por lado (metrics/structural_roles.py): a dominante nos
     rounds daquele lado, somando as partidas, com a conta ("âncora 60 de 96");
  2. rótulo da partida (metrics/player_roles.py): o mais frequente entre as
     partidas, e os componentes que decidem esses rótulos -- é onde vivem os
     pisos 0,80 / 0,40 / 0,32;
  3. o eixo carrega piano <-> baiter (metrics/archetypes.py): índice médio e em
     quantas partidas ele caiu em cada ponta, com o sacrifício e a isca crus.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import polars as pl

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from metrics.archetypes import PISO_BAITER, PISO_CARREGA_PIANO  # noqa: E402
from metrics.structural_roles import FUNCOES  # noqa: E402

PROCESSED = PROJECT_ROOT / "data" / "processed"
MANIFESTO = PROJECT_ROOT / "data" / "manifest.json"


def _time(nome: str) -> str:
    n = (nome or "").strip()
    return n[5:] if n.lower().startswith("team ") else n


def _le(tabela: str, partidas: dict[str, dict]) -> pl.DataFrame:
    partes = []
    for mid, info in partidas.items():
        p = PROCESSED / mid / f"{tabela}.parquet"
        if p.exists():
            time_de = {n: _time(info["times"][t]["nome"]) for t in ("A", "B") for n in info["times"][t]["jogadores"]}
            df = pl.read_parquet(p)
            partes.append(df.with_columns(
                pl.lit(mid).alias("match_id"),
                pl.col("name").replace_strict(time_de, default=None).alias("time_real")))
    return pl.concat(partes, how="diagonal_relaxed") if partes else pl.DataFrame()


def tabela() -> pl.DataFrame:
    man = json.loads(MANIFESTO.read_text(encoding="utf-8"))["partidas"]
    pro = {m: v for m, v in man.items() if v.get("origem") == "profissional"}

    # 1. função estrutural por lado, somando os rounds de todas as partidas
    est = _le("structural_roles_summary", pro).drop_nulls("time_real")
    por_funcao = (est.drop_nulls("funcao").group_by("name", "side", "funcao")
                  .agg(pl.col("rounds_na_funcao").sum().alias("n")))
    total_lado = est.unique(["match_id", "name", "side"]).group_by("name", "side").agg(
        pl.col("rounds_no_lado").sum().alias("d"))
    dom = (por_funcao.sort("n", descending=True).group_by("name", "side", maintain_order=True).first()
           .join(total_lado, on=["name", "side"])
           .with_columns((pl.col("funcao").replace_strict({k: v[0] for k, v in FUNCOES.items()}, default=pl.col("funcao"))
                          + " " + pl.col("n").cast(pl.Utf8) + " de " + pl.col("d").cast(pl.Utf8)).alias("txt")))
    ct = dom.filter(pl.col("side") == "ct").select("name", pl.col("txt").alias("CT: função dominante"))
    tr = dom.filter(pl.col("side") == "t").select("name", pl.col("txt").alias("TR: função dominante"))

    # 2. rótulo da partida e os componentes que o decidem
    pr = _le("player_roles", pro).drop_nulls("time_real")
    rot = (pr.drop_nulls("role").group_by("name", "role").agg(pl.len().alias("n"))
           .sort("n", descending=True).group_by("name", maintain_order=True).first())
    partidas = pr.group_by("name").agg(pl.len().alias("partidas"), pl.col("time_real").mode().first().alias("time"))
    comp = pr.group_by("name").agg(
        pl.col("awp_share").mean().round(2).alias("awp"),
        pl.col("first_contact_share").mean().round(2).alias("abre(0,32)"),
        pl.col("off_team_share").mean().round(2).alias("lurk(0,40)"),
        pl.col("never_left_share").mean().round(2).alias("âncora(0,80)"),
        pl.col("enemy_blind_seconds").mean().round(0).alias("cegou_s"),
        pl.col("trade_share").mean().round(2).alias("trade"),
        pl.col("adr").mean().round(0).alias("adr"),
    )

    # 3. eixo carrega piano <-> baiter
    ar = _le("archetypes_summary", pro).drop_nulls("time_real")
    eixo = ar.group_by("name").agg(
        pl.col("sacrifice_index").mean().round(2).alias("eixo"),
        (pl.col("sacrifice_index") >= PISO_CARREGA_PIANO).sum().alias("partidas_piano"),
        (pl.col("sacrifice_index") <= PISO_BAITER).sum().alias("partidas_baiter"),
        (pl.col("sacrificio_rounds").sum().cast(pl.Utf8) + "/" + pl.col("pagou_rounds").sum().cast(pl.Utf8)).alias("colheu/pagou"),
        pl.col("bait_untraded_per_round").mean().round(2).alias("isca/round"),
    ) if "sacrifice_index" in ar.columns else pl.DataFrame({"name": []})

    return (partidas.join(ct, on="name", how="left").join(tr, on="name", how="left")
            .join(rot.select("name", (pl.col("role") + " (" + pl.col("n").cast(pl.Utf8) + ")").alias("rótulo mais comum")),
                  on="name", how="left")
            .join(comp, on="name", how="left").join(eixo, on="name", how="left")
            .sort(["time", "name"]))


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--time")
    ap.add_argument("--csv")
    args = ap.parse_args()
    t = tabela()
    if args.time:
        t = t.filter(pl.col("time").str.contains(args.time))
    if args.csv:
        t.write_csv(args.csv)
        print(f"gravado em {args.csv}")
        return
    pl.Config.set_tbl_rows(200)
    pl.Config.set_tbl_cols(30)
    pl.Config.set_tbl_width_chars(400)
    pl.Config.set_fmt_str_lengths(40)
    print(t)


if __name__ == "__main__":
    main()
