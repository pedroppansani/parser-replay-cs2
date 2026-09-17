"""
Testes do clustering global (um KMeans para todas as partidas).

O que está sendo travado aqui é uma propriedade, não um número: o mesmo
(jogador, round) tem que cair no MESMO cluster independentemente de com quais
outras partidas ele foi processado. Sem isso, `clustering/cluster_names.json` --
que é um arquivo único aplicado a todas as partidas -- cola o nome no grupo
errado.

Há um teste de controle mostrando que o clustering por partida NÃO tem essa
propriedade. Ele existe pelo mesmo motivo do controle da convenção de pitch em
test_phase2_metrics: se um dia os dois passarem, o teste principal parou de
medir o que devia.
"""
from __future__ import annotations

import polars as pl
import pytest

from clustering.playstyle import (
    FEATURE_COLUMNS,
    FEATURES_DE_RESULTADO_REMOVIDAS,
    assign_with_model,
    cluster_playstyles,
    describe_clusters,
    fit_global_model,
    representative_rounds,
)

# Três comportamentos bem separados, pra o agrupamento não depender de sorte:
#   entry  -> contato cedo, perto do time, morre
#   lurk   -> contato tarde, longe do time, sobrevive
#   frag   -> dano e kills altos
PERFIS = {
    "entry": dict(damage=40.0, utility_damage=0.0, kills=0.2, trade_kills=0.0,
                  avg_distance_from_team=400.0, max_distance_from_team=700.0,
                  distinct_places=4.0, crosshair_score=70.0, height_score=50.0,
                  frac_entering_fight=0.30, time_of_first_contact_s=10.0, survived=0.0),
    "lurk": dict(damage=45.0, utility_damage=0.0, kills=0.4, trade_kills=0.0,
                 avg_distance_from_team=1000.0, max_distance_from_team=1700.0,
                 distinct_places=6.0, crosshair_score=70.0, height_score=50.0,
                 frac_entering_fight=0.08, time_of_first_contact_s=40.0, survived=1.0),
    "frag": dict(damage=190.0, utility_damage=8.0, kills=2.0, trade_kills=0.5,
                 avg_distance_from_team=600.0, max_distance_from_team=1100.0,
                 distinct_places=6.0, crosshair_score=72.0, height_score=52.0,
                 frac_entering_fight=0.18, time_of_first_contact_s=25.0, survived=0.6),
}


def _features(match_id: str, composicao: list[str], jitter: float = 0.0) -> pl.DataFrame:
    """Uma linha por (round, jogador) seguindo os perfis acima.

    `jitter` desloca a partida inteira, pra simular partidas com nível de dano
    diferente -- é justamente isso que faz o KMeans por partida renumerar.
    """
    linhas = []
    for i, perfil in enumerate(composicao):
        base = dict(PERFIS[perfil])
        base["damage"] += jitter
        linhas.append(
            {
                "round_num": i + 1,
                "steamid": 1000 + i,
                "name": f"{perfil}_{i}",
                "side": "t" if i % 2 else "ct",
                **base,
            }
        )
    df = pl.DataFrame(linhas)
    faltando = [c for c in FEATURE_COLUMNS if c not in df.columns]
    assert not faltando, f"fixture desatualizada: {faltando}"
    return df.with_columns(pl.lit(match_id).alias("match_id"))


@pytest.fixture
def pool() -> pl.DataFrame:
    # Composições diferentes de propósito: uma partida com mais frags, outra com
    # mais lurk. Se o modelo fosse ajustado por partida, cada uma acharia um
    # centro diferente para o mesmo comportamento.
    a = _features("match_a", ["entry"] * 6 + ["lurk"] * 2 + ["frag"] * 4)
    # A ORDEM das linhas importa para o teste de controle: é ela que muda a
    # inicialização do KMeans e faz o mesmo comportamento receber outro número
    # em cada partida -- exatamente o que acontece nas demos reais.
    b = _features("match_b", ["frag"] * 2 + ["lurk"] * 7 + ["entry"] * 2, jitter=5.0)
    return pl.concat([a, b], how="vertical")


def test_modelo_global_da_o_mesmo_cluster_em_qualquer_subconjunto(pool):
    """A propriedade que torna a nomeação válida."""
    model = fit_global_model(pool, n_clusters=3)

    juntas = assign_with_model(pool, model)
    separadas = pl.concat(
        [
            assign_with_model(pool.filter(pl.col("match_id") == mid), model)
            for mid in ("match_a", "match_b")
        ],
        how="vertical",
    )

    chave = ["match_id", "round_num", "steamid"]
    lado_a = juntas.select([*chave, "cluster"]).sort(chave)
    lado_b = separadas.select([*chave, "cluster"]).sort(chave)
    assert lado_a.equals(lado_b)


def test_modelo_global_agrupa_o_mesmo_comportamento_no_mesmo_cluster(pool):
    """Comportamento igual em partidas diferentes cai no mesmo cluster.

    É o outro lado da moeda do teste acima: não basta ser estável, tem que
    agrupar pelo que a gente quer agrupar.
    """
    model = fit_global_model(pool, n_clusters=3)
    atribuido = assign_with_model(pool, model).with_columns(
        pl.col("name").str.split("_").list.first().alias("perfil")
    )

    por_perfil = atribuido.group_by("perfil").agg(pl.col("cluster").n_unique().alias("n"))
    assert por_perfil["n"].max() == 1, "um mesmo perfil foi parar em clusters diferentes"
    assert atribuido["cluster"].n_unique() == 3


def test_clustering_por_partida_renumera_os_clusters(pool):
    """CONTROLE: o modo antigo não tem a propriedade acima.

    Se este teste começar a falhar, não comemore -- significa que o fixture
    deixou de reproduzir o problema, e o teste principal virou decoração.
    """
    rotulo_do_perfil = {}
    for mid in ("match_a", "match_b"):
        sub = pool.filter(pl.col("match_id") == mid)
        assignments, _, _ = cluster_playstyles(sub, n_clusters=3)
        frag = (
            assignments.filter(pl.col("name").str.starts_with("frag"))["cluster"].unique().to_list()
        )
        rotulo_do_perfil[mid] = frag[0]

    assert rotulo_do_perfil["match_a"] != rotulo_do_perfil["match_b"], (
        "o KMeans por partida deu o mesmo número ao grupo de frag nas duas — "
        "o fixture parou de reproduzir a renumeração"
    )


def test_assign_with_model_recusa_features_ausentes(pool):
    """Falhar alto é melhor que preencher com mediana e devolver cluster errado."""
    model = fit_global_model(pool, n_clusters=3)
    with pytest.raises(ValueError, match="Features ausentes"):
        assign_with_model(pool.drop("crosshair_score"), model)


def test_mediana_de_preenchimento_vem_do_modelo(pool):
    """Nulo preenchido com a mediana do CONJUNTO, não a do subconjunto.

    Se a mediana fosse recalculada a cada aplicação, o mesmo round nulo cairia
    em cluster diferente dependendo de quem foi processado junto — que é o bug
    que o modelo global existe para evitar, entrando pela porta dos fundos.
    """
    model = fit_global_model(pool, n_clusters=3)
    com_nulo = pool.with_columns(
        pl.when(pl.col("round_num") == 1)
        .then(None)
        .otherwise(pl.col("crosshair_score"))
        .alias("crosshair_score")
    )

    no_conjunto = assign_with_model(com_nulo, model).filter(pl.col("round_num") == 1)
    sozinho = assign_with_model(com_nulo.filter(pl.col("round_num") == 1), model)

    assert no_conjunto["cluster"].to_list() == sozinho["cluster"].to_list()


def test_exemplos_trazem_match_id_quando_vem_do_conjunto(pool):
    """Sem o match_id, "round 5" no relatório global não diz de qual partida."""
    model = fit_global_model(pool, n_clusters=3)
    assignments = assign_with_model(pool, model)

    assert "match_id" in representative_rounds(assignments).columns
    # e continua funcionando para uma partida só, onde a coluna não existe
    uma = assignments.filter(pl.col("match_id") == "match_a").drop("match_id")
    assert "match_id" not in representative_rounds(uma).columns


# --- Descrição legível dos grupos -------------------------------------------

def test_features_de_resultado_ficam_fora_do_agrupamento():
    """REGRESSÃO: com dano, kills e sobrevivência dentro, o agrupamento separava
    os rounds por COMO TERMINARAM, não por como foram jogados -- e isso a tabela
    de ADR já diz. Medido no conjunto: tirá-las levou a silhueta de 0,168 para
    0,216 e a variação explicada pelos dois eixos de 40% para 56%.
    """
    assert not set(FEATURE_COLUMNS) & set(FEATURES_DE_RESULTADO_REMOVIDAS)
    for proibida in ("damage", "kills", "survived", "trade_kills", "utility_damage"):
        assert proibida not in FEATURE_COLUMNS


def test_descricao_diz_no_que_o_grupo_se_afasta():
    """A frase é uma releitura da medição, não um apelido de jogo."""
    # Três grupos, e só a distância varia: com dois grupos todo z-score é ±1 e o
    # desempate entre features viraria ordem de dicionário, não medição.
    perfis = pl.DataFrame(
        {
            "cluster": [0, 1, 2],
            "n_rounds": [100, 100, 100],
            "avg_distance_from_team": [1200.0, 400.0, 800.0],
            "max_distance_from_team": [1800.0, 700.0, 1250.0],
            "distinct_places": [5.0, 5.0, 5.0],
            "crosshair_score": [70.0, 70.0, 70.0],
            "height_score": [0.9, 0.9, 0.9],
            "frac_entering_fight": [0.1, 0.1, 0.1],
            "time_of_first_contact_s": [25.0, 25.0, 25.0],
        }
    )
    d = describe_clusters(perfis)
    por_cluster = dict(zip(d["cluster"].to_list(), d["descricao"].to_list()))

    assert "longe do time" in por_cluster[0]
    assert "colado no time" in por_cluster[1]
    # e nenhum apelido de jogo aparece: isso é leitura humana, não do algoritmo
    for texto in por_cluster.values():
        for apelido in ("lurker", "entry", "âncora", "suporte", "AWPer"):
            assert apelido.lower() not in texto.lower()


def test_descricao_de_tabela_vazia_nao_estoura():
    vazio = pl.DataFrame(schema={"cluster": pl.Int32, "n_rounds": pl.UInt32})
    assert describe_clusters(vazio).height == 0
