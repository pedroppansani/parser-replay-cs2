"""
CLI pra processar um .dem: parseia, salva os dados crus em data/interim/ (local,
não vai pro git) e calcula as métricas das três fases, salvando em
data/processed/ (leve o suficiente pra ir pro repositório e alimentar o
dashboard público).

Uso:
    python -m scripts.process_demo data/raw/minha_partida.dem --match-id minha_partida

    # reaproveitando um parse anterior (pula os ~14s de parsing):
    python -m scripts.process_demo data/raw/minha_partida.dem --match-id x --from-interim

Depois disso, é só rodar o dashboard (streamlit run dashboard/app.py) que ele
já lista as partidas processadas em data/processed/.
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import polars as pl

from clustering.playstyle import (
    build_feature_matrix,
    cluster_playstyles,
    evaluate_cluster_counts,
    representative_rounds,
    save_cluster_names_template,
)
from metrics.awp_metrics import calculate_awp_metrics
from metrics.basic_metrics import compute_all_basic_metrics
from metrics.crosshair import calculate_crosshair_metrics
from metrics.positioning import calculate_positioning_metrics
from parsing.parser import ALL_TABLES, load_interim, parse_demo, save_interim

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def process(
    dem_path: Path,
    match_id: str,
    *,
    from_interim: bool = False,
    n_clusters: int = 4,
) -> Path:
    interim_dir = PROJECT_ROOT / "data" / "interim"
    processed_dir = PROJECT_ROOT / "data" / "processed" / match_id
    processed_dir.mkdir(parents=True, exist_ok=True)

    if from_interim:
        print(f"[1/6] Carregando parse anterior de data/interim/{match_id} ...")
        tables = load_interim(interim_dir, match_id)
        header = json.loads((interim_dir / match_id / "header.json").read_text(encoding="utf-8"))
        map_name = header.get("map_name", "desconhecido")
    else:
        print(f"[1/6] Parseando {dem_path.name} ...")
        t0 = time.time()
        demo = parse_demo(dem_path)
        map_name = demo.header.get("map_name", "desconhecido")
        print(f"      ok em {time.time() - t0:.1f}s -- mapa: {map_name}")
        print("[2/6] Salvando tabelas brutas (data/interim/, não vai pro git) ...")
        save_interim(demo, interim_dir, match_id)
        tables = {name: getattr(demo, name) for name in ALL_TABLES}

    outputs: dict[str, pl.DataFrame] = {}

    print("[3/6] Fase 1 -- métricas básicas (ADR, KAST, trades, utility) ...")
    outputs.update(compute_all_basic_metrics(tables))

    print("[4/6] Fase 2 -- AWP, crosshair placement e posicionamento ...")
    awp_round, awp_summary = calculate_awp_metrics(tables)
    outputs["awp_per_round"] = awp_round
    outputs["awp_summary"] = awp_summary

    ch_round, ch_summary, ch_samples = calculate_crosshair_metrics(tables, map_name)
    outputs["crosshair_per_round"] = ch_round
    outputs["crosshair_summary"] = ch_summary

    pos = calculate_positioning_metrics(tables, map_name)
    outputs["setup_snapshot"] = pos["setup_snapshot"]
    outputs["zone_occupancy"] = pos["zone_occupancy"]
    outputs["standard_setup"] = pos["standard_setup"]
    outputs["setup_deviation"] = pos["setup_deviation"]
    outputs["position_profile"] = pos["position_profile"]
    outputs["heatmap_bins"] = pos["heatmap_bins"]

    print("[5/6] Fase 3 -- clustering de estilos de jogo (PCA + KMeans) ...")
    features = build_feature_matrix(
        outputs, ch_round, pos["position_profile"], tables["damages"], tables["rounds"]
    )
    outputs["cluster_features"] = features

    silhouettes = evaluate_cluster_counts(features)
    outputs["cluster_silhouettes"] = silhouettes

    assignments, profiles, meta = cluster_playstyles(features, n_clusters=n_clusters)
    outputs["cluster_assignments"] = assignments
    outputs["cluster_profiles"] = profiles
    outputs["cluster_examples"] = representative_rounds(assignments)
    save_cluster_names_template(profiles)

    print("[6/6] Salvando métricas processadas ...")
    for name, df in outputs.items():
        df.write_parquet(processed_dir / f"{name}.parquet")
    tables["rounds"].write_parquet(processed_dir / "rounds.parquet")

    match_meta = {
        "match_id": match_id,
        "map_name": map_name,
        "n_rounds": tables["rounds"].height,
        "source_dem": str(dem_path),
        "pca": meta,
    }
    (processed_dir / "match_meta.json").write_text(
        json.dumps(match_meta, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print(f"\nPronto. Métricas processadas em: {processed_dir}")
    print(f"Melhor silhueta: k={silhouettes['n_clusters'][0]} ({silhouettes['silhouette'][0]:.3f})")
    return processed_dir


def main() -> None:
    parser = argparse.ArgumentParser(description="Processa um .dem do CS2 e calcula as métricas das 3 fases.")
    parser.add_argument("dem_path", type=Path, help="Caminho do arquivo .dem")
    parser.add_argument("--match-id", type=str, default=None, help="Identificador da partida (default: nome do arquivo)")
    parser.add_argument(
        "--from-interim",
        action="store_true",
        help="Reaproveita um parse anterior salvo em data/interim/ em vez de reparsear o .dem",
    )
    parser.add_argument("--clusters", type=int, default=4, help="Número de clusters do KMeans (default: 4)")
    args = parser.parse_args()

    match_id = args.match_id or args.dem_path.stem
    process(args.dem_path, match_id, from_interim=args.from_interim, n_clusters=args.clusters)


if __name__ == "__main__":
    main()
