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
    _profile_clusters,
    assign_with_model,
    build_feature_matrix,
    cluster_playstyles,
    evaluate_cluster_counts,
    load_global_model,
    representative_rounds,
    save_cluster_names_template,
)
from metrics.awp_metrics import calculate_awp_metrics
from metrics.basic_metrics import compute_all_basic_metrics, roster_per_round
from metrics.crosshair import calculate_crosshair_metrics
from metrics.map_areas import area_lookup, derive_place_areas
from metrics.grenades import compute_grenade_metrics
from metrics.player_roles import build_player_roles, resolve_teams
from metrics.structural_roles import structural_roles
from metrics.positioning import calculate_positioning_metrics
from metrics.site_roles import (
    anchor_metrics,
    lurk_metrics,
    player_round_area_shares,
    player_round_areas,
)
from parsing.parser import (
    ALL_TABLES,
    kills_do_round_jogado,
    grenade_event_tables,
    load_interim,
    parse_demo,
    save_interim,
)

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
        # save_interim grava mais tabelas do que ALL_TABLES, e load_interim as lê
        # de volta. Sem repeti-las aqui, parsear do zero entrega MENOS dado que
        # `--from-interim` e as métricas que dependem delas degradam em silêncio:
        # `bomb` é a origem dos centróides de bombsite em metrics/map_areas.py,
        # e sem ela a partição A/Mid/B cai no fallback.
        for name in ("bomb", "smokes", "infernos"):
            tables[name] = getattr(demo, name)
        # Os eventos de granada não são atributos do Demo (vêm do dict de eventos
        # crus), então não entram pelo getattr acima. Sem esta linha, parsear do
        # zero produz métricas de flash zeradas enquanto `--from-interim`
        # produz as certas — e a diferença passa despercebida porque zero é um
        # número plausível.
        tables.update(grenade_event_tables(demo))
        # Mesmo filtro que o load_interim aplica: sem ele, parsear do zero conta
        # mortes do tempo parado e dá +1 kill a quem se matou no pré-round.
        tables["kills"] = kills_do_round_jogado(tables["kills"], tables["rounds"])

    outputs: dict[str, pl.DataFrame] = {}

    print("[3/6] Fase 1 -- métricas básicas (ADR, KAST, trades, utility) ...")
    outputs.update(compute_all_basic_metrics(tables))

    print("[4/6] Fase 2 -- AWP, crosshair placement, posicionamento e utility ...")
    gren_round, gren_summary = compute_grenade_metrics(tables, roster_per_round(tables["ticks"]))
    outputs["grenades_per_round"] = gren_round
    outputs["grenades_summary"] = gren_summary

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

    # Áreas macro do mapa (A / Mid / B) e as funções que dependem DELAS, não de
    # distância: âncora é quem fica no mesmo site mesmo com a leitura apontando
    # pro outro, lurker é o T que joga área diferente da do time. Ver
    # metrics/site_roles.py.
    place_areas = derive_place_areas(pos["positions"], tables.get("bomb"), map_name)
    outputs["place_areas"] = place_areas
    area_shares = player_round_area_shares(pos["positions"], area_lookup(place_areas))
    outputs["player_round_area_shares"] = area_shares
    outputs["player_round_areas"] = player_round_areas(area_shares)
    if place_areas.height == 0:
        print(
            f"      AVISO: não foi possível localizar os dois bombsites em {map_name}."
            " Âncora e lurk ficam sem métrica nesta partida."
        )
    anchor_round, anchor_sum = anchor_metrics(area_shares)
    outputs["anchor_per_round"] = anchor_round
    outputs["anchor_summary"] = anchor_sum
    lurk_round, lurk_sum = lurk_metrics(area_shares)
    outputs["lurk_per_round"] = lurk_round
    outputs["lurk_summary"] = lurk_sum

    print("[5/6] Fase 3 -- clustering de estilos de jogo (PCA + KMeans) ...")
    features = build_feature_matrix(
        outputs, ch_round, pos["position_profile"], tables["damages"], tables["rounds"]
    )
    outputs["cluster_features"] = features

    silhouettes = evaluate_cluster_counts(features)
    outputs["cluster_silhouettes"] = silhouettes

    # Se já existe um modelo ajustado no conjunto das partidas, ele manda: o
    # rótulo numérico do KMeans é arbitrário, então treinar de novo só nesta
    # partida faria o "cluster 2" daqui não ser o "cluster 2" das outras -- e
    # `cluster_names.json` é um arquivo só, aplicado a todas. Ver
    # scripts/fit_global_clusters.py.
    global_model = load_global_model()
    if global_model is not None:
        assignments = assign_with_model(features, global_model)
        profiles = _profile_clusters(assignments, global_model["feature_columns"])
        meta = {
            "explained_variance_ratio": global_model["explained_variance_ratio"],
            "feature_columns": global_model["feature_columns"],
            "n_clusters": global_model["n_clusters"],
            "fitted_on": "global",
            "n_player_rounds_global": global_model["n_player_rounds"],
        }
        print(
            f"      modelo global ({global_model['n_player_rounds']} player-rounds,"
            f" k={global_model['n_clusters']}). Rode scripts.fit_global_clusters"
            " para reajustar incluindo esta partida."
        )
    else:
        assignments, profiles, meta = cluster_playstyles(features, n_clusters=n_clusters)
        meta["fitted_on"] = "match"
        print(
            "      AVISO: sem modelo global (clustering/global_model.json). Os"
            " clusters desta partida foram treinados só nela e os números NÃO"
            " correspondem aos das outras. Rode scripts.fit_global_clusters."
        )

    outputs["cluster_assignments"] = assignments
    outputs["cluster_profiles"] = profiles
    outputs["cluster_examples"] = representative_rounds(assignments)
    save_cluster_names_template(profiles)

    # --- Funções ESTRUTURAIS (metrics/structural_roles.py) ---
    # Qual é o trabalho do jogador no round, por lado. É leitura independente do
    # perfil comportamental (metrics/archetypes.py): um âncora pode ser carrega
    # piano ou baiter, e as duas coisas são verdade ao mesmo tempo.
    team_of_sr, _ = resolve_teams(tables["ticks"])
    funcoes_round, funcoes_resumo = structural_roles(
        tables, team_of_sr, map_name, match_id=match_id
    )
    outputs["structural_roles"] = funcoes_round
    outputs["structural_roles_summary"] = funcoes_resumo

    roles, traits = build_player_roles(outputs, features, tables["ticks"])
    outputs["player_roles"] = roles
    outputs["player_traits"] = traits

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
