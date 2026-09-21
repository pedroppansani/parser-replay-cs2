"""
Ajusta UM clustering de estilos para todas as partidas processadas e reescreve
as atribuições de cada uma com esse modelo.

Por que este script existe: o KMeans numera os grupos arbitrariamente. Treinando
por partida, o "cluster 3" de uma não é o "cluster 3" da outra -- e como
`clustering/cluster_names.json` é um arquivo único que o dashboard aplica a todas
as partidas, um nome dado olhando uma partida apareceria colado num grupo de
comportamento diferente nas demais. Medido nas 9 partidas: o grupo de dano alto
é o cluster 3 em match_01, o 2 em match_02 e o 0 em match_04.

Depois de rodar isto, o cluster N quer dizer a mesma coisa em toda partida, e
nomear passa a ser uma decisão válida.

Rode sempre que processar uma demo nova (o conjunto muda) ou quando quiser mexer
no k. Reajustar pode renumerar os clusters -- por isso o script avisa quando já
existem nomes dados, em vez de silenciosamente deixar o nome velho apontando
pro grupo errado.

Uso:
    py -3.12 -m scripts.fit_global_clusters              # k=4 (default)
    py -3.12 -m scripts.fit_global_clusters --clusters 5
    py -3.12 -m scripts.fit_global_clusters --dry-run    # só mostra, não grava
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import polars as pl

from clustering.playstyle import (
    _profile_clusters,
    assign_with_model,
    evaluate_cluster_counts,
    fit_global_model,
    load_cluster_names,
    load_global_model,
    representative_rounds,
    save_cluster_names_template,
    save_global_model,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
# Fora de data/processed/ de propósito: dashboard e build_site tratam TODA pasta
# lá dentro como uma partida (iterdir), então um diretório de agregado ali
# viraria uma partida fantasma no menu.
GLOBAL_DIR = PROJECT_ROOT / "data" / "global_clusters"

# Colunas mostradas no relatório de nomeação. São as que mais separam os grupos
# nos dados reais; a tabela completa fica no parquet.
REPORT_COLUMNS = [
    "n_rounds",
    "damage",
    "kills",
    "trade_kills",
    "utility_damage",
    "avg_distance_from_team",
    "max_distance_from_team",
    "distinct_places",
    "time_of_first_contact_s",
    "frac_entering_fight",
    "crosshair_score",
    "survived",
]


def load_pool() -> tuple[pl.DataFrame, list[str]]:
    """Empilha o cluster_features de todas as partidas, marcando a origem.

    `match_id` entra como coluna porque sem ela não há como checar se um grupo é
    comportamento recorrente ou artefato de uma única partida -- que é a primeira
    coisa a conferir antes de dar nome a um cluster.
    """
    frames, match_ids = [], []
    for match_dir in sorted(PROCESSED_DIR.glob("match_*")):
        path = match_dir / "cluster_features.parquet"
        if not path.exists():
            continue
        frames.append(
            pl.read_parquet(path).with_columns(pl.lit(match_dir.name).alias("match_id"))
        )
        match_ids.append(match_dir.name)
    if not frames:
        raise SystemExit(
            "Nenhuma partida processada em data/processed/. Rode scripts.process_demo antes."
        )
    return pl.concat(frames, how="diagonal"), match_ids


def report(profiles: pl.DataFrame, assignments: pl.DataFrame, model: dict) -> None:
    """Imprime o que é preciso olhar pra nomear cada cluster."""
    pl.Config.set_tbl_cols(30)
    pl.Config.set_tbl_width_chars(220)

    print("\n=== PERFIL DE CADA CLUSTER (médias em unidade de jogo) ===")
    print(profiles.select(["cluster", *[c for c in REPORT_COLUMNS if c in profiles.columns]]))

    print("\n=== PRESENÇA POR PARTIDA (cluster só de uma partida é artefato) ===")
    print(
        assignments.group_by(["match_id", "cluster"], maintain_order=True)
        .len()
        .pivot(on="cluster", index="match_id", values="len")
        .sort("match_id")
        .fill_null(0)
    )

    print("\n=== LADO (T/CT) ===")
    print(
        assignments.group_by(["cluster", "side"], maintain_order=True)
        .len()
        .pivot(on="side", index="cluster", values="len")
        .sort("cluster")
        .fill_null(0)
    )

    variancia = ", ".join(f"{v:.1%}" for v in model["explained_variance_ratio"])
    print(f"\nsilhueta no conjunto: {model['silhouette']:.3f}  |  variância explicada PCA: {variancia}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Ajusta o clustering global de estilos.")
    parser.add_argument("--clusters", type=int, default=4, help="k do KMeans (default: 4)")
    parser.add_argument("--dry-run", action="store_true", help="mostra o resultado sem gravar nada")
    args = parser.parse_args()

    pool, match_ids = load_pool()
    print(f"{pool.height} player-rounds de {len(match_ids)} partidas: {', '.join(match_ids)}")

    print("\n=== SILHUETA POR k NO CONJUNTO ===")
    silhouettes = evaluate_cluster_counts(pool)
    print(silhouettes)

    anterior = load_global_model()
    model = fit_global_model(pool, n_clusters=args.clusters)
    assignments = assign_with_model(pool, model)
    profiles = _profile_clusters(assignments, model["feature_columns"])
    examples = representative_rounds(assignments)

    report(profiles, assignments, model)

    nomes = {k: v for k, v in load_cluster_names().items() if v}
    if nomes and anterior is not None:
        print(
            "\nATENÇÃO: já existem clusters nomeados e o modelo foi reajustado. O KMeans"
            " pode ter renumerado os grupos -- confira se cada nome ainda descreve o"
            " perfil acima antes de publicar:"
        )
        for cid, nome in sorted(nomes.items()):
            print(f"  cluster {cid}: {nome}")

    if args.dry_run:
        print("\n--dry-run: nada foi gravado.")
        return

    save_global_model(model)
    GLOBAL_DIR.mkdir(parents=True, exist_ok=True)
    profiles.write_parquet(GLOBAL_DIR / "cluster_profiles.parquet")
    examples.write_parquet(GLOBAL_DIR / "cluster_examples.parquet")
    assignments.write_parquet(GLOBAL_DIR / "cluster_assignments.parquet")
    silhouettes.write_parquet(GLOBAL_DIR / "cluster_silhouettes.parquet")
    (GLOBAL_DIR / "model_meta.json").write_text(
        json.dumps(
            {k: v for k, v in model.items() if k not in ("cluster_centers", "pca_components")},
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    # Reescreve cada partida com os rótulos do modelo compartilhado. Sem este
    # passo o dashboard continuaria lendo os clusters treinados por partida, e o
    # nome global não corresponderia ao que o painel mostra.
    print("\nReescrevendo as atribuições de cada partida com o modelo global:")
    for match_id in match_ids:
        match_dir = PROCESSED_DIR / match_id
        sub = assignments.filter(pl.col("match_id") == match_id).drop("match_id")
        sub.write_parquet(match_dir / "cluster_assignments.parquet")
        _profile_clusters(sub, model["feature_columns"]).write_parquet(
            match_dir / "cluster_profiles.parquet"
        )
        representative_rounds(sub).write_parquet(match_dir / "cluster_examples.parquet")

        meta_path = match_dir / "match_meta.json"
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        meta["pca"] = {
            "explained_variance_ratio": model["explained_variance_ratio"],
            "feature_columns": model["feature_columns"],
            "n_clusters": model["n_clusters"],
            "fitted_on": "global",
            "n_player_rounds_global": model["n_player_rounds"],
        }
        meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"  {match_id}: {sub.height} player-rounds")

    save_cluster_names_template(profiles)
    print(
        "\nModelo salvo em clustering/global_model.json e agregados em"
        f" {GLOBAL_DIR.relative_to(PROJECT_ROOT)}/."
        "\nPróximo passo (é seu, não do código): preencher clustering/cluster_names.json"
        " olhando o perfil acima e os rounds de exemplo."
    )


if __name__ == "__main__":
    main()
