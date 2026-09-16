"""
Mostra a partição A / Mid / B derivada para cada mapa processado, pra revisão.

Existe pelo mesmo motivo do scripts/show_derived_angles.py: a classificação é
derivada dos dados, mas quem sabe se ela bate com o jogo é o Pedro. O script
imprime cada callout com a razão de distância que decidiu a área (0,5 =
equidistante dos dois bombsites), do mais "A" para o mais "B", pra ficar visível
quais estão em cima da fronteira.

Discordou de algum? Preencha `MANUAL_PLACE_AREAS` em metrics/map_areas.py e
reprocesse a partida daquele mapa. O caso mais provável é a Nuke: os dois sites
ficam empilhados na vertical e a derivação lá é a mais frágil das nove partidas.

Uso:
    py -3.12 -m scripts.show_map_areas             # todos os mapas
    py -3.12 -m scripts.show_map_areas de_nuke     # um mapa
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import polars as pl

from metrics.map_areas import floor_split_z

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"


def mapas_processados() -> dict[str, list[str]]:
    """map_name -> match_ids, pras partidas já processadas."""
    por_mapa: dict[str, list[str]] = {}
    for match_dir in sorted(PROCESSED_DIR.glob("match_*")):
        meta_path = match_dir / "match_meta.json"
        if not meta_path.exists():
            continue
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        por_mapa.setdefault(meta["map_name"], []).append(match_dir.name)
    return por_mapa


def main() -> None:
    parser = argparse.ArgumentParser(description="Áreas macro derivadas por mapa.")
    parser.add_argument("map_name", nargs="?", default=None, help="filtra um mapa só")
    args = parser.parse_args()

    por_mapa = mapas_processados()
    if not por_mapa:
        raise SystemExit("Nenhuma partida processada em data/processed/.")

    for map_name, match_ids in sorted(por_mapa.items()):
        if args.map_name and map_name != args.map_name:
            continue

        # Qualquer partida do mapa serve: a partição é geométrica, não da partida.
        # A primeira é usada, e as demais aparecem no cabeçalho como referência de
        # quanto dado sustenta a derivação.
        areas = pl.read_parquet(PROCESSED_DIR / match_ids[0] / "place_areas.parquet")
        split = floor_split_z(map_name)
        andares = f", dois andares (corte em Z={split:.0f})" if split is not None else ""
        print(f"\n=== {map_name} ({len(match_ids)} partida(s): {', '.join(match_ids)}{andares})")

        if areas.height == 0:
            print("  sem partição: não foi possível localizar os dois bombsites.")
            continue

        for row in areas.sort("area_ratio").iter_rows(named=True):
            marca = " <- manual" if row["source"] == "manual" else ""
            print(
                f"  {row['area_ratio']:.2f}  {row['area']:<6} {row['place']:<18}"
                f" ({row['n_samples']} amostras){marca}"
            )


if __name__ == "__main__":
    main()
