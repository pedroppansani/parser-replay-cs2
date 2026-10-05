"""Tempo de voo das granadas medido no corpus (fase 8, item 8.1). Não muda nada.

A prancheta mostra a granada fazendo o arco até o destino no tempo de voo. Sem
arremesso real ligado, o tempo sai de uma estimativa pela distância -- e a
estimativa sai daqui: do aparecimento do projétil (primeiro tick com posição na
tabela `grenades`) até a detonação (`*_detonate`, `inferno_startburn` para a
molotov), e a distância horizontal entre os dois pontos.

Para cada tipo: mediana do tempo, a correlação tempo x distância e a regressão
tempo = a + b * distância. Flash e HE estouram por pavio (o tempo quase não
depende da distância); smoke e molotov estouram quando param ou batem no chão.

Uso:
    py -3.12 -m pesquisa.voo_das_granadas [n_partidas]
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import polars as pl

RAIZ = Path(__file__).resolve().parents[1]
INTERIM = RAIZ / "data" / "interim"
TICKRATE = 64
DETONACAO = {"smoke": ("smokegrenade_detonate", "CSmokeGrenadeProjectile"),
             "flash": ("flashbang_detonate", "CFlashbangProjectile"),
             "he": ("hegrenade_detonate", "CHEGrenadeProjectile"),
             "molotov": ("inferno_startburn", None)}


def medicoes(m: str) -> pl.DataFrame:
    g = pl.read_parquet(INTERIM / m / "grenades.parquet").filter(pl.col("X").is_not_null())
    inicio = (g.sort("tick").group_by(["round_num", "entity_id"], maintain_order=True)
              .agg(pl.col("tick").first().alias("t0"), pl.col("X").first().alias("x0"), pl.col("Y").first().alias("y0"),
                   pl.col("grenade_type").first().alias("classe")))
    saida = []
    for arma, (tabela, classe) in DETONACAO.items():
        f = INTERIM / m / f"{tabela}.parquet"
        if not f.exists():
            continue
        d = pl.read_parquet(f).select("round_num", pl.col("entityid").alias("entity_id"), pl.col("tick").alias("t1"),
                                      pl.col("x").alias("x1"), pl.col("y").alias("y1"))
        j = inicio.join(d, on=["round_num", "entity_id"], how="inner")
        if classe is not None:
            j = j.filter(pl.col("classe") == classe)
        else:
            j = j.filter(pl.col("classe") == "CMolotovProjectile")
        saida.append(j.select(pl.lit(arma).alias("arma"),
                              ((pl.col("t1") - pl.col("t0")) / TICKRATE).alias("segundos"),
                              ((pl.col("x1") - pl.col("x0")) ** 2 + (pl.col("y1") - pl.col("y0")) ** 2).sqrt().alias("distancia"))
                      .filter((pl.col("segundos") > 0) & (pl.col("segundos") < 10)))
    # molotov: o inferno_startburn traz a entidade do FOGO, não a do projétil; o
    # voo é a vida do próprio projétil na trajetória (ele some no impacto)
    mol = (g.filter(pl.col("grenade_type") == "CMolotovProjectile").sort("tick")
           .group_by(["round_num", "entity_id"], maintain_order=True)
           .agg(((pl.col("tick").last() - pl.col("tick").first()) / TICKRATE).alias("segundos"),
                ((pl.col("X").last() - pl.col("X").first()) ** 2 + (pl.col("Y").last() - pl.col("Y").first()) ** 2)
                .sqrt().alias("distancia"))
           .select(pl.lit("molotov").alias("arma"), "segundos", "distancia")
           .filter((pl.col("segundos") > 0) & (pl.col("segundos") < 10)))
    saida = [s for s in saida if s.height and s["arma"][0] != "molotov"] + [mol]
    return pl.concat(saida) if saida else pl.DataFrame()


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 12
    man = json.loads((RAIZ / "data" / "manifest.json").read_text(encoding="utf-8"))["partidas"]
    pro = sorted(k for k, v in man.items() if v.get("origem") == "profissional" and (INTERIM / k / "grenades.parquet").exists())[:n]
    t = pl.concat([medicoes(m) for m in pro])
    print(f"{len(pro)} partidas profissionais, {t.height} granadas\n")
    print("| granada | n | tempo mediano (s) | p25 | p75 | correlação tempo x distância | tempo = a + b·distância |")
    print("|---|---|---|---|---|---|---|")
    for arma in DETONACAO:
        s = t.filter(pl.col("arma") == arma)
        if s.height < 10:
            continue
        x, y = s["distancia"].to_numpy(), s["segundos"].to_numpy()
        b, a = np.polyfit(x, y, 1)
        r = np.corrcoef(x, y)[0, 1]
        print(f"| {arma} | {s.height} | {np.median(y):.2f} | {np.percentile(y, 25):.2f} | {np.percentile(y, 75):.2f} | "
              f"{r:.2f} | {a:.3f} + {b * 1000:.3f}·d/1000 |")


if __name__ == "__main__":
    main()
