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
    "avg_distance_from_team",  # posicionamento: joga junto ou separado (Fase 2)
    "max_distance_from_team",
    "distinct_places",  # rotaciona muito ou ancora (Fase 2)
    "crosshair_score",  # disciplina de mira (Fase 2)
    "height_score",
    "frac_entering_fight",  # quanto do round foi passado entrando em briga (Fase 2)
    "time_of_first_contact_s",  # entra cedo ou espera (derivada abaixo)
]

# Estas cinco features SAIRAM da lista, e a saida foi o conserto do modulo:
#
#   damage, kills, trade_kills, utility_damage, survived
#
# Todas sao RESULTADO, nao comportamento. Com elas dentro, o KMeans agrupava os
# rounds por como eles terminaram -- os quatro grupos eram "round produtivo",
# "round longe e sobreviveu", "round que morreu entrando" e "round que morreu sem
# fazer nada". Isso contradizia o proposito declarado logo acima ("agrupar COMO o
# jogador jogou o round, nao se ele se deu bem") e, pior, nao acrescentava nada:
# a tabela de ADR ja diz como o round terminou.
#
# Medido no conjunto das 9 partidas (1.870 player-rounds), tirando as cinco:
#   silhueta k=4: 0,168 -> 0,216      silhueta k=3: 0,159 -> 0,236
#   variancia nos 2 eixos do grafico: 40% -> 56%
#
# E os grupos passaram a ler como estilo: joga separado e parado / entra sem a
# mira pronta / roda o mapa evitando briga / joga junto e rapido. So ai nomear
# passou a fazer sentido.
FEATURES_DE_RESULTADO_REMOVIDAS = [
    "damage", "kills", "trade_kills", "utility_damage", "survived",
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

    profiles = _profile_clusters(assignments, cols)

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
        # match_id só existe quando os exemplos saem do conjunto de várias
        # partidas. Sem ele, "round 5" no relatório global não diz de qual
        # partida -- e o exemplo perde a utilidade de poder ser assistido.
        .select(
            [c for c in ["cluster", "match_id", "round_num", "name", "side", "damage", "kills",
                         "avg_distance_from_team", "time_of_first_contact_s", "survived",
                         "distance_to_center"] if c in assignments.columns or c == "distance_to_center"]
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


# ---------------------------------------------------------------------------
# Modelo global: um único KMeans para todas as partidas
# ---------------------------------------------------------------------------
#
# Por que isso existe: até aqui o KMeans era treinado por partida, e o rótulo
# numérico que ele devolve é ARBITRÁRIO -- o "cluster 3" de uma partida não tem
# relação com o "cluster 3" da outra. Com uma partida só isso era inofensivo.
# Com nove, e um `cluster_names.json` único que o dashboard aplica a todas,
# passa a ser errado: o nome dado olhando o perfil de uma partida apareceria
# colado num grupo de comportamento diferente na seguinte. Foi medido: o grupo
# de dano alto é o cluster 3 em match_01, o 2 em match_02 e o 0 em match_04.
#
# A correção é treinar UMA vez no conjunto das partidas e só aplicar o modelo
# em cada uma. Aí o cluster 0 quer dizer a mesma coisa em todo lugar e nomear
# passa a fazer sentido. A unidade de análise continua sendo (jogador, round) --
# o que muda é onde o modelo é ajustado, não o que ele agrupa.
#
# O modelo é salvo como JSON, não pickle: é um punhado de vetores de números e
# vale mais poder ler o diff e não depender da versão do scikit-learn instalada
# do que economizar linhas.
GLOBAL_MODEL_FILE = Path(__file__).resolve().parent / "global_model.json"
GLOBAL_MODEL_VERSION = 1


def _profile_clusters(assignments: pl.DataFrame, cols: list[str]) -> pl.DataFrame:
    """Média de cada feature por cluster, em unidades ORIGINAIS.

    É esta tabela que se olha pra nomear um cluster -- por isso em unidade de
    jogo (dano, unidades de distância, segundos) e não em z-score.
    """
    return (
        assignments.group_by("cluster")
        .agg(pl.len().alias("n_rounds"), *[pl.col(c).mean().alias(c) for c in cols])
        .sort("cluster")
    )


def fit_global_model(
    features: pl.DataFrame,
    n_clusters: int = DEFAULT_N_CLUSTERS,
    n_components: int = 2,
    random_state: int = RANDOM_STATE,
) -> dict:
    """Ajusta scaler + PCA + KMeans no conjunto de TODAS as partidas.

    Devolve um dicionário serializável com tudo que é preciso pra reaplicar o
    mesmo modelo depois: as medianas de preenchimento, os parâmetros de
    padronização, os componentes do PCA e os centróides. As medianas entram no
    modelo porque preencher nulo com a mediana DA PARTIDA faria o mesmo round
    cair em cluster diferente dependendo de com quem ele foi processado.
    """
    cols = [c for c in FEATURE_COLUMNS if c in features.columns]
    mat = features.select(cols).with_columns([pl.col(c).cast(pl.Float64) for c in cols])
    medians = {c: float(mat[c].median() or 0.0) for c in cols}

    arr = _fill_and_matrix(mat, cols, medians)
    scaler = StandardScaler().fit(arr)
    x = scaler.transform(arr)

    pca = PCA(n_components=n_components, random_state=random_state).fit(x)
    kmeans = KMeans(n_clusters=n_clusters, random_state=random_state, n_init=10).fit(x)

    return {
        "version": GLOBAL_MODEL_VERSION,
        "n_clusters": n_clusters,
        "feature_columns": cols,
        "fill_medians": medians,
        "scaler_mean": scaler.mean_.tolist(),
        "scaler_scale": scaler.scale_.tolist(),
        "pca_mean": pca.mean_.tolist(),
        "pca_components": pca.components_.tolist(),
        "explained_variance_ratio": pca.explained_variance_ratio_.tolist(),
        "cluster_centers": kmeans.cluster_centers_.tolist(),
        "n_player_rounds": int(features.height),
        "silhouette": float(silhouette_score(x, kmeans.labels_)),
    }


def _fill_and_matrix(mat: pl.DataFrame, cols: list[str], medians: dict[str, float]) -> np.ndarray:
    """Preenche nulo/NaN com medianas DADAS (não recalculadas) e vira matriz."""
    filled = mat.with_columns(
        [pl.col(c).fill_null(medians[c]).fill_nan(medians[c]) for c in cols]
    )
    return np.nan_to_num(filled.to_numpy(), nan=0.0)


def assign_with_model(features: pl.DataFrame, model: dict) -> pl.DataFrame:
    """Aplica um modelo global já ajustado: devolve as features com cluster e PCA.

    Cluster = centróide mais próximo no espaço padronizado, que é exatamente o
    que o `KMeans.predict` faz -- reimplementado em numpy pra não precisar
    reconstruir o objeto do sklearn a partir do JSON.
    """
    cols = model["feature_columns"]
    faltando = [c for c in cols if c not in features.columns]
    if faltando:
        raise ValueError(
            f"Features ausentes para aplicar o modelo global: {faltando}. "
            "Reprocesse a partida ou reajuste o modelo."
        )

    mat = features.select(cols).with_columns([pl.col(c).cast(pl.Float64) for c in cols])
    arr = _fill_and_matrix(mat, cols, model["fill_medians"])

    x = (arr - np.asarray(model["scaler_mean"])) / np.asarray(model["scaler_scale"])
    coords = (x - np.asarray(model["pca_mean"])) @ np.asarray(model["pca_components"]).T

    centers = np.asarray(model["cluster_centers"])
    # distância de cada ponto a cada centróide, sem materializar o tensor 3D
    dists = ((x**2).sum(axis=1)[:, None] - 2 * x @ centers.T + (centers**2).sum(axis=1)[None, :])
    labels = dists.argmin(axis=1)

    return features.with_columns(
        pl.Series("cluster", labels.astype(np.int32)),
        *[pl.Series(f"pca_{i + 1}", coords[:, i]) for i in range(coords.shape[1])],
    )


def save_global_model(model: dict, path: Path = GLOBAL_MODEL_FILE) -> Path:
    path.write_text(json.dumps(model, indent=2, ensure_ascii=False), encoding="utf-8")
    return path


def load_global_model(path: Path = GLOBAL_MODEL_FILE) -> dict | None:
    """Modelo global salvo, ou None se ainda não foi ajustado.

    None é caso legítimo: numa checagem do repo recém-clonado, ou na primeira
    partida processada, ainda não existe conjunto pra ajustar. Quem chama cai
    no clustering por partida e avisa.
    """
    if not path.exists():
        return None
    try:
        model = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    if model.get("version") != GLOBAL_MODEL_VERSION:
        return None
    return model


# ---------------------------------------------------------------------------
# Descrição legível de cada grupo
# ---------------------------------------------------------------------------
#
# Isto NÃO é nomear o cluster, e a diferença importa. Nomear é dizer "esse é o
# lurker" -- leitura de jogo, que continua sendo do Pedro via cluster_names.json
# (decisão 8 do CLAUDE.md). O que este bloco faz é RESTATAR A MEDIÇÃO em
# português: "longe do time, encosta tarde" é o que os números dizem, não uma
# interpretação deles.
#
# Existe porque "Cluster 0" não significa nada para quem abre a página, e um
# gráfico de pontos com eixos de PCA significa menos ainda. Enquanto o painel
# mostrava isso, a aba inteira era decorativa.
#
# A descrição é derivada, não escrita à mão, pra continuar verdadeira quando o
# modelo for reajustado: compara cada grupo com a média dos grupos e conta as
# duas features em que ele mais se afasta.
FRASES_FEATURE = {
    "avg_distance_from_team": ("longe do time", "colado no time"),
    "max_distance_from_team": ("chega a se afastar muito", "nunca se afasta"),
    "distinct_places": ("passa por muitas regiões", "fica em poucas regiões"),
    "crosshair_score": ("mira bem posicionada", "mira atrasada"),
    "height_score": ("joga por cima", "joga por baixo"),
    "frac_entering_fight": ("vive entrando em briga", "quase não entra em briga"),
    "time_of_first_contact_s": ("encosta no adversário tarde", "encosta no adversário cedo"),
}

# Quantas características entram na descrição. Duas descrevem sem virar lista;
# com uma só, dois grupos parecidos ficariam com o mesmo texto.
N_CARACTERISTICAS = 2


def describe_clusters(profiles: pl.DataFrame) -> pl.DataFrame:
    """Uma frase por grupo, dizendo no que ele se afasta mais da média.

    Devolve `cluster`, `titulo` (a característica mais forte) e `descricao` (as
    duas mais fortes), além de `destaques` com o detalhe numérico de cada uma --
    o número anda junto pra dar pra discordar da frase olhando a medida.
    """
    cols = [c for c in FRASES_FEATURE if c in profiles.columns]
    if profiles.height == 0 or not cols:
        return pl.DataFrame(
            schema={"cluster": pl.Int32, "titulo": pl.String, "descricao": pl.String}
        )

    media = {c: float(profiles[c].mean()) for c in cols}
    desvio = {c: float(profiles[c].std() or 0.0) for c in cols}

    linhas = []
    for row in profiles.iter_rows(named=True):
        pontuadas = []
        for c in cols:
            if desvio[c] == 0:
                continue
            z = (float(row[c]) - media[c]) / desvio[c]
            alto, baixo = FRASES_FEATURE[c]
            pontuadas.append((abs(z), alto if z > 0 else baixo, c, float(row[c])))
        pontuadas.sort(reverse=True)
        escolhidas = pontuadas[:N_CARACTERISTICAS]

        linhas.append(
            {
                "cluster": int(row["cluster"]),
                "titulo": escolhidas[0][1] if escolhidas else "sem característica marcante",
                "descricao": ", ".join(p[1] for p in escolhidas),
                "n_rounds": int(row.get("n_rounds") or 0),
            }
        )
    return pl.DataFrame(linhas).sort("cluster")
