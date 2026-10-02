import sys
from pathlib import Path
import polars as pl
R = Path(r"C:\Users\User\Desktop\Projetos Claude\01 - Parser de Replay CS2")
sys.path.insert(0, str(R))
sys.stdout.reconfigure(encoding="utf-8")
from metrics.structural_roles import chance_ao_acaso, ALFA_FUNCAO_ACIMA_DO_ACASO as ALFA

e = pl.concat([pl.read_parquet(d / "structural_roles_summary.parquet").with_columns(pl.lit(d.name).alias("match_id"))
               for d in sorted((R / "data" / "processed").glob("match_*"))], how="diagonal_relaxed")
print(e.columns)
d = e.filter(pl.col("funcao").is_not_null()).with_columns(
    pl.struct(["rounds_na_funcao", "rounds_no_lado", "side"]).map_elements(
        lambda r: chance_ao_acaso(r["rounds_na_funcao"], r["rounds_no_lado"], r["side"]), return_dtype=pl.Float64).alias("p"))
d = d.with_columns((pl.col("p") < ALFA).alias("fica"))
print("jogador-lados:", e.height, "com função hoje:", d.height, "ficam:", d["fica"].sum(), "saem:", (~d["fica"]).sum())
print(d.group_by("funcao").agg(pl.len().alias("hoje"), pl.col("fica").sum().alias("ficam")).sort("funcao"))
print(d.group_by("side").agg(pl.len().alias("hoje"), pl.col("fica").sum().alias("ficam")))
if "empate_vencido_pelo_awper" in d.columns:
    print("vencidos pelo awper:", d.filter(pl.col("empate_vencido_pelo_awper")).select(pl.len(), pl.col("fica").sum()))
print(d.with_columns((pl.col("rounds_na_funcao") / pl.col("rounds_no_lado")).round(1).alias("conc"))
      .group_by("conc").agg(pl.len(), pl.col("fica").sum()).sort("conc"))
aw = d.filter(pl.col("funcao") == "awper").sort("p", descending=True)
for r in aw.head(15).iter_rows(named=True):
    print(r["match_id"], r["name"], r["side"], r["rounds_na_funcao"], "de", r["rounds_no_lado"], round(r["p"], 3))
