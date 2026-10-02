"""Diagnóstico dos rótulos de jogador (auditoria, item 4.5). Não muda nada.

Três perguntas, medidas no corpus:
  1. com que AMOSTRA cada rótulo é dado hoje (o "Segundo homem" sai de quantas kills?);
  2. o "Suporte de utility" usa segundos de cegueira TOTAIS contra um piso fixo:
     quem ganha ou perde o rótulo se a medida for por round?
  3. a função dominante por lado pode sair de poucos rounds (2 de 12)?

Uso:
    py -3.12 -m pesquisa.rotulos_amostra
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import polars as pl

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))
from metrics.player_roles import TRAIT_SPECS  # noqa: E402

PROCESSED = RAIZ / "data" / "processed"


def corpus() -> tuple[pl.DataFrame, pl.DataFrame, pl.DataFrame]:
    papeis, tracos, estrut = [], [], []
    for d in sorted(PROCESSED.glob("match_*")):
        n = json.loads((d / "match_meta.json").read_text(encoding="utf-8"))["n_rounds"]
        papeis.append(pl.read_parquet(d / "player_roles.parquet").with_columns(
            pl.lit(d.name).alias("match_id"), pl.lit(n).alias("rounds")))
        t = pl.read_parquet(d / "player_traits.parquet")
        if t.height:
            tracos.append(t.with_columns(pl.lit(d.name).alias("match_id")))
        estrut.append(pl.read_parquet(d / "structural_roles_summary.parquet").with_columns(pl.lit(d.name).alias("match_id")))
    return (pl.concat(papeis, how="diagonal_relaxed"), pl.concat(tracos, how="diagonal_relaxed"),
            pl.concat(estrut, how="diagonal_relaxed"))


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    papeis, tracos, estrut = corpus()
    j = tracos.join(papeis.select("match_id", "steamid", "total_kills", "total_trade_kills", "rounds",
                                  "enemy_blind_seconds", "n_rounds_pressao_outro_lado"),
                    on=["match_id", "steamid"], how="left")
    print(f"{papeis.height} jogador-partidas, {tracos.height} rótulos\n")

    print("== 1. amostra por trás de cada rótulo")
    for spec in TRAIT_SPECS:
        t = j.filter(pl.col("trait") == spec.key)
        linha = f"{spec.label:20s} {t.height:4d} rótulos | amostra mínima hoje: {spec.minimo_amostra or 'nenhuma'}"
        if spec.key == "trade":
            k = t["total_kills"].to_numpy()
            linha += (f" | kills: mín {k.min()}, p10 {np.percentile(k, 10):.0f}, mediana {np.median(k):.0f}"
                      f" | com menos de 10 kills: {(k < 10).sum()}; trades: mín {t['total_trade_kills'].min()}")
        if spec.key == "anchor":
            r = t["n_rounds_pressao_outro_lado"].fill_null(0).to_numpy()
            linha += f" | rounds de CT com pressão no outro lado: mín {r.min()}, mediana {np.median(r):.0f}, zero em {(r == 0).sum()}"
        if spec.key in ("entry", "frag", "support"):
            r = t["rounds"].to_numpy()
            linha += f" | rounds da partida: mín {r.min()}, mediana {np.median(r):.0f}"
        print("  " + linha)

    print("\n== 2. suporte: segundos totais (piso 20) x por round")
    rounds = papeis["rounds"].to_numpy()
    piso_total = next(s.floor for s in TRAIT_SPECS if s.key == "support")
    equivalente = piso_total / float(np.median(rounds))
    print(f"  rounds por partida no corpus: mín {rounds.min()}, mediana {np.median(rounds):.0f}, máx {rounds.max()}")
    print(f"  piso equivalente por round = {piso_total} / mediana de rounds = {equivalente:.3f} s/round")
    p = papeis.with_columns((pl.col("enemy_blind_seconds") / pl.col("rounds")).alias("por_round"))
    lider = pl.col("enemy_blind_seconds") == pl.col("enemy_blind_seconds").max().over(["match_id", "team"])
    hoje = p.filter(lider & (pl.col("enemy_blind_seconds") >= piso_total))
    novo = p.filter(lider & (pl.col("por_round") >= equivalente))
    chave = lambda d: set(zip(d["match_id"].to_list(), d["steamid"].to_list()))  # noqa: E731
    ganham, perdem = chave(novo) - chave(hoje), chave(hoje) - chave(novo)
    print(f"  líderes de time acima do piso: hoje {hoje.height}, por round {novo.height}; ganham {len(ganham)}, perdem {len(perdem)}")
    for nome, grupo in (("GANHAM", ganham), ("PERDEM", perdem)):
        for m, s in sorted(grupo):
            r = p.filter((pl.col("match_id") == m) & (pl.col("steamid") == s)).row(0, named=True)
            print(f"    {nome} {m} {r['name']:14s} {r['enemy_blind_seconds']:.1f}s em {r['rounds']} rounds = {r['por_round']:.2f} s/round")
    fronteira = p.filter(lider).with_columns((pl.col("por_round") - equivalente).alias("dist")).sort(pl.col("dist").abs()).head(10)
    print("  fronteira (os 10 líderes mais próximos do piso por round):")
    for r in fronteira.iter_rows(named=True):
        print(f"    {r['match_id']} {r['name']:14s} {r['enemy_blind_seconds']:.1f}s / {r['rounds']} = {r['por_round']:.2f} ({r['dist']:+.2f})")

    print("\n== 3. função dominante por lado: com quantos rounds ela sai")
    d = estrut.filter(pl.col("funcao").is_not_null())
    print(f"  {d.height} jogador-lados com função dominante de {estrut.height}")
    print("  rounds na função dominante:", dict(sorted(d["rounds_na_funcao"].value_counts().iter_rows())))
    poucos = d.filter(pl.col("rounds_na_funcao") <= 3).sort("rounds_na_funcao")
    print(f"  com 3 rounds ou menos: {poucos.height}")
    for r in poucos.head(12).iter_rows(named=True):
        print(f"    {r['match_id']} {r['name']:14s} {r['side']} {r['funcao']} em {r['rounds_na_funcao']} de {r['rounds_no_lado']} rounds (concentração {r['concentracao']:.2f})")


if __name__ == "__main__":
    main()
