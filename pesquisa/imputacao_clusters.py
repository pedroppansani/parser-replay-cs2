"""Imputação do tempo até o contato no agrupamento de estilos (auditoria, item 4.7). Não grava nada.

Compara o agrupamento ANTIGO (nulo preenchido com "mediana da partida x 2") com o
NOVO (nulo mantido, coluna `sem_contato`, tempo preenchido com a mediana do
modelo global):
  1. ARI entre os rótulos antigos e os novos, nos mesmos (partida, round, jogador);
  2. o mesmo sem a coluna `sem_contato`, para separar os dois efeitos;
  3. estabilidade: reamostragem das PARTIDAS (bootstrap), modelo refeito em cada
     uma e aplicado ao conjunto inteiro, ARI contra o modelo do conjunto;
  4. tabela cruzada antigo x novo e os perfis em unidade de jogo.

Lê `cluster_features`/`cluster_assignments` antigos de uma pasta copiada antes
da mudança (argumento) e os novos de data/processed/.

Uso:
    py -3.12 -m pesquisa.imputacao_clusters <pasta_antes>
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import polars as pl
from sklearn.metrics import adjusted_rand_score

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))
from clustering.playstyle import FEATURE_COLUMNS, _profile_clusters, assign_with_model, fit_global_model  # noqa: E402

PROCESSED = RAIZ / "data" / "processed"
CHAVE = ["match_id", "round_num", "steamid"]
N_REAMOSTRAGENS = 30
SEMENTE = 20261002


def pool(base: Path, arquivo: str) -> pl.DataFrame:
    return pl.concat([pl.read_parquet(d / f"{arquivo}.parquet").with_columns(pl.lit(d.name).alias("match_id"))
                      for d in sorted(base.glob("match_*")) if (d / f"{arquivo}.parquet").exists()],
                     how="diagonal_relaxed")


def estabilidade(dados: pl.DataFrame, colunas: list[str]) -> np.ndarray:
    base = fit_global_model(dados.select(colunas + CHAVE), n_clusters=4)
    ref = assign_with_model(dados, base)["cluster"].to_numpy()
    partidas = sorted(dados["match_id"].unique().to_list())
    rng = np.random.default_rng(SEMENTE)
    aris = []
    for _ in range(N_REAMOSTRAGENS):
        escolha = rng.choice(partidas, size=len(partidas), replace=True)
        amostra = pl.concat([dados.filter(pl.col("match_id") == m) for m in escolha])
        modelo = fit_global_model(amostra.select(colunas + CHAVE), n_clusters=4)
        aris.append(adjusted_rand_score(ref, assign_with_model(dados, modelo)["cluster"].to_numpy()))
    return np.array(aris)


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    antes = Path(sys.argv[1])
    velho = pool(antes, "cluster_features").join(
        pool(antes, "cluster_assignments").select(CHAVE + [pl.col("cluster").alias("cluster_antigo")]), on=CHAVE)
    novo = pool(PROCESSED, "cluster_features")
    j = novo.join(velho.select(CHAVE + ["cluster_antigo"]), on=CHAVE, how="inner").sort(CHAVE)
    print(f"{novo.height} player-rounds novos, {velho.height} antigos, {j.height} casados")
    print(f"sem contato: {int(j['sem_contato'].sum())} ({j['sem_contato'].mean() * 100:.1f}%)")

    sem_flag = [c for c in FEATURE_COLUMNS if c != "sem_contato"]
    modelo = fit_global_model(j.select(FEATURE_COLUMNS + CHAVE), n_clusters=4)
    a = assign_with_model(j, modelo)
    modelo_sem = fit_global_model(j.select(sem_flag + CHAVE), n_clusters=4)
    b = assign_with_model(j.drop("sem_contato"), modelo_sem)
    print(f"\nARI antigo x novo (com sem_contato): {adjusted_rand_score(j['cluster_antigo'], a['cluster']):.3f}")
    print(f"ARI antigo x novo (sem a coluna):    {adjusted_rand_score(j['cluster_antigo'], b['cluster']):.3f}")
    print(f"silhueta: novo {modelo['silhouette']:.3f}, sem a coluna {modelo_sem['silhouette']:.3f}")

    print("\ntabela cruzada (linhas: antigo, colunas: novo):")
    print(a.with_columns(j["cluster_antigo"]).pivot(on="cluster", index="cluster_antigo", values="steamid",
                                                    aggregate_function="len", sort_columns=True).sort("cluster_antigo"))
    print("\nperfis ANTIGOS (unidade de jogo):")
    print(_profile_clusters(velho.rename({"cluster_antigo": "cluster"}), sem_flag))
    print("perfis NOVOS (com a coluna no agrupamento):")
    print(_profile_clusters(a, FEATURE_COLUMNS))
    print("\ntabela cruzada antigo x novo SEM a coluna no agrupamento:")
    print(b.with_columns(j["cluster_antigo"]).pivot(on="cluster", index="cluster_antigo", values="steamid",
                                                    aggregate_function="len", sort_columns=True).sort("cluster_antigo"))
    print("perfis NOVOS (sem a coluna no agrupamento):")
    print(_profile_clusters(b.with_columns(j["sem_contato"]), sem_flag + ["sem_contato"]))

    for nome, dados, cols in (("antigo", velho, sem_flag), ("novo com a coluna", j, FEATURE_COLUMNS),
                              ("novo sem a coluna", j.drop("sem_contato"), sem_flag)):
        e = estabilidade(dados, cols)
        print(f"\nestabilidade {nome} ({N_REAMOSTRAGENS} reamostragens das partidas): ARI médio {e.mean():.3f}, "
              f"mínimo {e.min():.3f}, p10 {np.percentile(e, 10):.3f}")


if __name__ == "__main__":
    main()
