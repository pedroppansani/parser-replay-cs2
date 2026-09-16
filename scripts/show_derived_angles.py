"""
Lista os ângulos de entrada derivados dos dados, por região do mapa.

É a ferramenta de calibração: rode isso, compare com o que você sabe do mapa e
preencha/corrija o que for preciso em MANUAL_ENTRY_ANGLES (metrics/map_angles.py).
Ângulo manual tem prioridade sobre o derivado.

Uso:
    python -m scripts.show_derived_angles match_01
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import polars as pl

from metrics.map_angles import entry_angles_for_map

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def main() -> None:
    parser = argparse.ArgumentParser(description="Mostra os ângulos de entrada derivados de uma partida.")
    parser.add_argument("match_id", type=str, help="ID da partida já parseada (pasta em data/interim/)")
    args = parser.parse_args()

    match_dir = PROJECT_ROOT / "data" / "interim" / args.match_id
    if not match_dir.exists():
        raise SystemExit(f"Partida não encontrada em {match_dir}. Rode scripts/process_demo.py antes.")

    kills = pl.read_parquet(match_dir / "kills.parquet")
    header = json.loads((match_dir / "header.json").read_text(encoding="utf-8"))
    map_name = header.get("map_name", "desconhecido")

    angles = entry_angles_for_map(map_name, kills)

    print(f"Mapa: {map_name}")
    print(f"Ângulos de entrada ({angles.height}):\n")
    with pl.Config(tbl_rows=100):
        print(angles)

    print(
        "\nPra sobrescrever algum desses com o seu conhecimento de jogo, edite\n"
        "MANUAL_ENTRY_ANGLES em metrics/map_angles.py no formato:\n\n"
        f'    MANUAL_ENTRY_ANGLES = {{\n'
        f'        "{map_name}": {{\n'
        f'            ("BombsiteA", "ct"): [\n'
        f'                {{"yaw": -110.0, "tolerance": 20.0, "desc": "pré-mira pra saída de main"}},\n'
        f"            ],\n"
        f"        }}\n"
        f"    }}\n\n"
        "Atenção: `n_kills` baixo (4-5) significa ângulo sustentado por pouca "
        "evidência — é justamente onde o seu julgamento vale mais que o dado."
    )


if __name__ == "__main__":
    main()
