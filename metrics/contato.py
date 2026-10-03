"""O que é "contato" num round. Uma regra, um lugar (auditoria, item 4.8).

Contato = causou ou sofreu dano. Era escrito duas vezes, igual, em
clustering/playstyle.py e em metrics/structural_roles.py.
"""
from __future__ import annotations

import polars as pl


def primeiro_contato(damages: pl.DataFrame) -> pl.DataFrame:
    """(round_num, steamid, tick_contato): o tick do primeiro dano causado ou
    sofrido por cada jogador em cada round. Quem não teve contato não aparece."""
    lados = [
        damages.select(pl.col("round_num"), pl.col(col).alias("steamid"), pl.col("tick"))
        for col in ("attacker_steamid", "victim_steamid")
    ]
    return (
        pl.concat(lados)
        .filter(pl.col("steamid").is_not_null())
        .group_by(["round_num", "steamid"], maintain_order=True)
        .agg(pl.col("tick").min().alias("tick_contato"))
    )
