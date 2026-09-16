"""
Clustering de estilos de jogo (Fase 3): PCA + KMeans sobre as métricas das
Fases 1 e 2.

O que o módulo faz e o que ele NÃO faz:

FAZ: agrupa (jogador, round) em perfis com comportamento parecido e descreve
cada grupo pelas features que o distinguem -- "esse grupo tem dano alto, morre
cedo, fica longe do time e entra primeiro nas brigas".

NÃO FAZ: dar nome aos grupos. "Entry fragger", "lurker", "suporte de utility"
são interpretações de jogo, e um KMeans não tem como saber disso -- ele só sabe
que existe um agrupamento no espaço de features. A nomeação é minha (Pedro),
feita olhando o perfil de cada cluster em `cluster_profiles` e os rounds de
exemplo em `representative_rounds`, e fica registrada em `cluster_names.json`
(ver CLUSTER_NAMES_FILE). O dashboard lê esse arquivo -- enquanto eu não nomear,
ele mostra "Cluster 0, 1, 2..." e avisa que falta nomear, em vez de inventar
rótulo automático.

Decisões técnicas:
- Unidade de análise é (jogador, round), não (jogador). Um mesmo jogador joga
  papéis diferentes em rounds diferentes (entry no round de execução, âncora no
  round de save), e agregar por partida esconde justamente isso.
- Features padronizadas (z-score) antes do PCA, senão ADR (escala 0-150) domina
  tudo e as features de 0 a 1 somem.
- PCA antes do KMeans pra descorrelacionar (ADR e kills são muito
  correlacionados) e deixar o scatter 2D do dashboard honesto -- os dois eixos
  do gráfico são de fato as duas direções de maior variação.
- `n_clusters` default 4, mas o módulo calcula a silhueta pra 2..8 pra eu poder
  escolher com base em evidência em vez de chute.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import polars as pl
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import StandardScaler

CLUSTER_NAMES_FILE = Path(__file__).resolve().parent / "cluster_names.json"

DEFAULT_N_CLUSTERS = 4
RANDOM_STATE = 42  # fixo pra o clustering ser reprodutível entre execuções

# Features usadas no clustering. Cada uma é um comportamento observável, não um
# resultado -- a ideia é agrupar COMO o jogador jogou o round, não se ele se deu
# bem. Por isso entram coisas como distância do time e tempo até o contato, e
# fica de fora, por exemplo, "ganhou o round".
FEATURE_COLUMNS = [
    "damage",  # dano no round (Fase 1)
    "utility_damage",  # dano de granada (Fase 1)
    "kills",  # kills no round (Fase 1)
    "trade_kills",  # kills de trade (Fase 1)
    "avg_distance_from_team",  # posicionamento: joga junto ou separado (Fase 2)
    "max_distance_from_team",
    "distinct_places",  # rotaciona muito ou ancora (Fase 2)
    "crosshair_score",  # disciplina de mira (Fase 2)
    "height_score",
    "frac_entering_fight",  # quanto do round foi passado entrando em briga (Fase 2)
    "time_of_first_contact_s",  # entra cedo ou espera (derivada abaixo)
    "survived",  # sobreviveu o round (Fase 1, como 0/1)
]


def first_contact_per_player_round(damages: pl.DataFrame, rounds: pl.DataFrame, tickrate: int = 64) -> pl.DataFrame:
    """Segundos entre o fim do freeze time e o primeiro contato do jogador.

    Contato = causou ou sofreu dano. É o separador mais direto entre quem abre o
    round e quem joga atrás: entry fragger toma contato nos primeiros segundos,
    lurker e âncora demoram.
    """
    contacts = pl.concat(
        [
            damages.filter(pl.col("attacker_steamid").is_not_null()).select(
                pl.col("round_num"), pl.col("attacker_steamid").alias("steamid"), pl.col("tick")
            ),
            damages.filter(pl.col("victim_steamid").is_not_null()).select(
                pl.col("round_num"), pl.col("victim_steamid").alias("steamid"), pl.col("tick")
            ),
        ],
        how="vertical",
    )

    return (
        contacts.group_by(["round_num", "steamid"])
        .agg(pl.col("tick").min().alias("first_contact_tick"))
        .join(rounds.select(["round_num", "freeze_end", "end"]), on="round_num", how="left")
        .with_columns(
            ((pl.col("first_contact_tick") - pl.col("freeze_end")) / tickrate).alias("time_of_first_contact_s")
        )
        .select(["round_num", "steamid", "time_of_first_contact_s"])
    )


def build_feature_matrix(
    basic: dict[str, pl.DataFrame],
    crosshair_per_round: pl.DataFrame,
    position_profile: pl.DataFrame,
    damages: pl.DataFrame,
    rounds: pl.DataFrame,
    tickrate: int = 64,
) -> pl.DataFrame:
    """Monta uma linha por (round, jogador) com todas as features do clustering."""
    adr = basic["adr_per_round"].select(["round_num", "steamid", "name", "damage"])
    util = basic["utility_damage_per_round"].select(["round_num", "steamid", "utility_damage"])
    kast = basic["kast_per_round"].select(["round_num", "steamid", "survived", "had_kill", "was_traded"])
    trades = basic["trade_kills_per_round"].select(["round_num", "steamid", "kills", "trade_kills"])

    contact = first_contact_per_player_round(damages, rounds, tickrate)

    features = (
        adr.join(util, on=["round_num", "steamid"], how="left")
        .join(kast, on=["round_num", "steamid"], how="left")
        .join(trades, on=["round_num", "steamid"], how="left")
        .join(
            crosshair_per_round.select(
                ["round_num", "steamid", "crosshair_score", "height_score", "frac_entering_fight"]
            ),
            on=["round_num", "steamid"],
            how="left",
        )
        .join(
            position_profile.select(
                [
                    "round_num",
                    "steamid",
                    "avg_distance_from_team",
                    "max_distance_from_team",
                    "distinct_places",
                    "side",
                ]
            ),
            on=["round_num", "steamid"],
            how="left",
        )
        .join(contact, on=["round_num", "steamid"], how="left")
    )

    return features.with_columns(
        pl.col("kills").fill_null(0),
        pl.col("trade_kills").fill_null(0),
        pl.col("utility_damage").fill_null(0),
        pl.col("survived").cast(pl.Float64).fill_null(0.0),
        # sem contato no round = o round inteiro sem briga. Preencher com a
        # duração do round seria mais correto que 0, mas como nem todo round tem
        # a mesma duração, uso a mediana dos contatos observados + margem, pra não
        # criar um outlier artificial que distorce o PCA.
        pl.col("time_of_first_contact_s").fill_null(
            pl.col("time_of_first_contact_s").median() * 2
        ),
    ).sort(["round_num", "steamid"])


def evaluate_cluster_counts(
    features: pl.DataFrame, k_range: range = range(2, 9), random_state: int = RANDOM_STATE
) -> pl.DataFrame:
    """Silhueta média pra cada número de clusters candidato.

    Silhueta mede o quanto cada ponto está mais perto do próprio grupo do que do
    grupo vizinho (-1 a 1, maior é melhor). Serve pra escolher k com evidência --
    mas o valor final é sempre uma decisão de interpretação: um k com silhueta
    ligeiramente pior pode ser preferível se os grupos fizerem mais sentido de jogo.
    """
    x, _ = _prepare_matrix(features)
    rows = []
    for k in k_range:
        if k >= x.shape[0]:
            continue
        labels = KMeans(n_clusters=k, random_state=random_state, n_init=10).fit_predict(x)
        rows.append({"n_clusters": k, "silhouette": float(silhouette_score(x, labels))})
    return pl.DataFrame(rows).sort("silhouette", descending=True)


def _prepare_matrix(features: pl.DataFrame) -> tuple[np.ndarray, list[str]]:
    """Seleciona as colunas de feature presentes, preenche nulos e padroniza."""
    cols = [c for c in FEATURE_COLUMNS if c in features.columns]
    mat = features.select(cols).with_columns([pl.col(c).cast(pl.Float64) for c in cols])
    # mediana pra nulo remanescente: não desloca a distribuição como a média faria
    mat = mat.with_columns([pl.col(c).fill_null(pl.col(c).median()).fill_nan(pl.col(c).median()) for c in cols])
    arr = mat.to_numpy()
    arr = np.nan_to_num(arr, nan=0.0)
    return StandardScaler().fit_transform(arr), cols


def cluster_playstyles(
    features: pl.DataFrame,
    n_clusters: int = DEFAULT_N_CLUSTERS,
    n_components: int = 2,
    random_state: int = RANDOM_STATE,
) -> tuple[pl.DataFrame, pl.DataFrame, dict]:
    """Roda PCA + KMeans e devolve (assignments, cluster_profiles, meta).

    - `assignments`: cada (round, jogador) com o cluster e as coordenadas PCA
      (que são os eixos do scatter no dashboard)
    - `cluster_profiles`: média de cada feature por cluster, em unidades ORIGINAIS
      (não padronizadas) -- é olhando essa tabela que eu nomeio os clusters
    - `meta`: variância explicada e peso de cada feature nos componentes, pra
      saber o que cada eixo do gráfico significa
    """
    x, cols = _prepare_matrix(features)

    pca = PCA(n_components=n_components, random_state=random_state)
    coords = pca.fit_transform(x)

    kmeans = KMeans(n_clusters=n_clusters, random_state=random_state, n_init=10)
    labels = kmeans.fit_predict(x)

    assignments = features.with_columns(
        pl.Series("cluster", labels.astype(np.int32)),
        *[pl.Series(f"pca_{i + 1}", coords[:, i]) for i in range(n_components)],
    )

    profiles = (
        assignments.group_by("cluster")
        .agg(
            pl.len().alias("n_rounds"),
            *[pl.col(c).mean().alias(c) for c in cols],
        )
        .sort("cluster")
    )

    meta = {
        "explained_variance_ratio": [float(v) for v in pca.explained_variance_ratio_],
        "feature_columns": cols,
        "component_loadings": {
            f"pca_{i + 1}": {c: float(w) for c, w in zip(cols, pca.components_[i])}
            for i in range(n_components)
        },
        "n_clusters": n_clusters,
    }
    return assignments, profiles, meta


def representative_rounds(assignments: pl.DataFrame, per_cluster: int = 5) -> pl.DataFrame:
    """Rounds mais próximos do centro de cada cluster -- os exemplos pra eu
    assistir/conferir na hora de nomear o cluster.
    """
    centers = assignments.group_by("cluster").agg(
        pl.col("pca_1").mean().alias("cx"), pl.col("pca_2").mean().alias("cy")
    )
    return (
        assignments.join(centers, on="cluster", how="left")
        .with_columns(
            (((pl.col("pca_1") - pl.col("cx")) ** 2 + (pl.col("pca_2") - pl.col("cy")) ** 2).sqrt()).alias(
                "distance_to_center"
            )
        )
        .sort(["cluster", "distance_to_center"])
        .group_by("cluster")
        .head(per_cluster)
        .select(
            ["cluster", "round_num", "name", "side", "damage", "kills", "avg_distance_from_team",
             "time_of_first_contact_s", "survived", "distance_to_center"]
        )
        .sort(["cluster", "distance_to_center"])
    )


def load_cluster_names(path: Path = CLUSTER_NAMES_FILE) -> dict[str, str]:
    """Nomes que eu dei pros clusters. Vazio = ainda não nomeei."""
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def save_cluster_names_template(profiles: pl.DataFrame, path: Path = CLUSTER_NAMES_FILE) -> Path:
    """Cria o arquivo de nomes em branco, com uma entrada por cluster, se ainda
    não existir. Não sobrescreve nomes já dados.
    """
    existing = load_cluster_names(path)
    template = {str(c): existing.get(str(c), "") for c in profiles["cluster"].to_list()}
    path.write_text(json.dumps(template, indent=2, ensure_ascii=False), encoding="utf-8")
    return path
