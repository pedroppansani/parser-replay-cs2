"""
Acumula o perfil de cada jogador em todas as partidas processadas.

O perfil de uma partida (`data/processed/<match_id>/player_profile.parquet`, saído
do `build_insights`) descreve o jogador naquela partida. Este script soma os
perfis e produz o acumulado, que é o número que vale: um perfil de 9 partidas
diz muito mais que um de 1, e "puxa AWP em 40% dos rounds" só começa a
significar alguma coisa depois de umas 100 rodadas.

A soma é de NUMERADORES E DENOMINADORES, com a taxa recalculada no fim -- não é
média das taxas. Média de taxas dá o mesmo peso a uma partida de 16 rounds e a
uma de 30, e o perfil passa a descrever as partidas em vez do jogador.

Uso:
    py -3.12 -m scripts.build_player_profiles
"""
from __future__ import annotations

import json
from pathlib import Path

import polars as pl

from metrics.player_profile import CATEGORIAS, accumulate

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
# Fora de data/processed/ de propósito: dashboard e build_site tratam toda pasta
# lá dentro como uma partida.
OUT_DIR = PROJECT_ROOT / "data" / "player_profiles"


def main() -> None:
    perfis = []
    for match_dir in sorted(PROCESSED_DIR.glob("match_*")):
        caminho = match_dir / "player_profile.parquet"
        if not caminho.exists():
            print(f"  {match_dir.name}: sem player_profile.parquet, pulando")
            continue
        perfis.append(pl.read_parquet(caminho))

    if not perfis:
        raise SystemExit(
            "Nenhum perfil encontrado. Rode scripts.build_insights nas partidas antes."
        )

    resumo = accumulate(perfis)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    resumo.write_parquet(OUT_DIR / "summary.parquet")
    pl.concat(perfis, how="diagonal").write_parquet(OUT_DIR / "per_match.parquet")
    (OUT_DIR / "categorias.json").write_text(
        json.dumps(CATEGORIAS, ensure_ascii=False, indent=1), encoding="utf-8"
    )

    print(
        f"{len(perfis)} partidas · {resumo.height} jogadores · "
        f"{resumo['rounds_jogados'].sum()} jogador-rounds"
    )
    print(f"\nperfil acumulado em {OUT_DIR.relative_to(PROJECT_ROOT)}/\n")

    pl.Config.set_tbl_width_chars(150)
    amostra = resumo.sort("pct_rounds_com_awp", descending=True, nulls_last=True).head(6)
    print("quem mais puxa AWP no conjunto:")
    for r in amostra.iter_rows(named=True):
        taxa = "-" if r["pct_rounds_com_awp"] is None else f"{r['pct_rounds_com_awp'] * 100:.0f}%"
        print(
            f"  {r['name']:<16} {taxa:>5} ({r['pct_rounds_com_awp_n']} de "
            f"{r['pct_rounds_com_awp_d']})  ·  {r['partidas']} partida(s)"
        )


if __name__ == "__main__":
    main()
