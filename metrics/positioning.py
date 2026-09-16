"""
Posicionamento (Fase 2): onde o time estava, e o quanto aquilo fugiu do padrão.

Duas perguntas diferentes, tratadas separadamente:

1. ONDE (descritivo) -- heatmaps. Posições amostradas ao longo do round, binadas
   em grade 2D, prontas pro dashboard desenhar por cima do radar do mapa.

2. O QUANTO FUGIU DO PADRÃO (comparativo) -- aqui mora uma decisão de design
   importante. O spec pedia comparar "onde o time estava de fato vs. padrões
   esperados de setup". O caminho ingênuo seria eu escrever à mão qual é o setup
   "certo" de cada mapa -- mas setup certo depende de economia, placar, lado e
   do que o time adversário vem fazendo, então uma tabela fixa minha seria
   chute disfarçado de métrica.
   O que o módulo faz em vez disso: deriva o setup padrão DO PRÓPRIO TIME
   naquela partida (a distribuição modal de regiões ocupadas no início do round,
   por lado) e mede o desvio de cada round em relação a esse padrão. Isso
   responde "esse round foi fora do que esse time normalmente faz", que é uma
   pergunta objetiva e útil -- e não depende de eu adivinhar o meta.
   Se eu quiser cravar um setup esperado manualmente, tem o hook
   MANUAL_EXPECTED_SETUP abaixo.

Observação sobre o radar: o overlay da imagem do mapa depende dos assets do awpy
(`awpy get maps`), que precisam de rede liberada. O módulo não depende deles --
ele entrega as posições e os bins; quem tiver os assets desenha por cima do
radar, quem não tiver desenha em coordenadas de jogo (analiticamente idêntico).
"""
from __future__ import annotations

import numpy as np
import polars as pl

# Quantos segundos depois do fim do freeze time consideramos o "setup" do round.
# 10s é tempo suficiente pro time ocupar as posições iniciais (rotina de CT,
# saída padrão de T) e cedo o bastante pra ainda não ter virado execução.
SETUP_SECONDS_AFTER_FREEZE = 10.0

# Amostragem das posições pro heatmap: 1 amostra a cada 64 ticks = 2 por segundo.
# Suficiente pra densidade espacial; mais que isso só engorda o parquet.
POSITION_SAMPLE_EVERY_N_TICKS = 64

# Tamanho do bin do heatmap em unidades de jogo. 64u ≈ a largura de um jogador,
# uma granularidade que mostra corredores e posições sem virar ruído.
HEATMAP_BIN_SIZE = 64.0

# Setup esperado definido à mão, se eu quiser sobrescrever o padrão derivado.
# Formato: {"de_ancient": {"ct": {"BombsiteA": 2, "Middle": 1, "BombsiteB": 2}}}
MANUAL_EXPECTED_SETUP: dict[str, dict[str, dict[str, int]]] = {}


def position_samples(
    ticks: pl.DataFrame,
    rounds: pl.DataFrame,
    sample_every: int = POSITION_SAMPLE_EVERY_N_TICKS,
) -> pl.DataFrame:
    """Posições amostradas dos jogadores vivos durante o tempo de jogo do round."""
    return (
        ticks.join(rounds.select(["round_num", "freeze_end", "end"]), on="round_num", how="inner")
        .filter(
            (pl.col("tick") >= pl.col("freeze_end"))
            & (pl.col("tick") <= pl.col("end"))
            & (pl.col("tick") % sample_every == 0)
            & pl.col("is_alive")
        )
        .select(["round_num", "tick", "steamid", "name", "side", "place", "X", "Y", "Z"])
    )


def heatmap_bins(
    positions: pl.DataFrame,
    bin_size: float = HEATMAP_BIN_SIZE,
) -> pl.DataFrame:
    """Agrega as posições numa grade 2D. Uma linha por (side, bin_x, bin_y) com
    a contagem de amostras -- é o insumo do heatmap no dashboard.

    Mantém `steamid` fora do group_by de propósito: o heatmap de time é o que
    mostra padrão de setup. Pra heatmap individual, filtre antes de chamar.
    """
    return (
        positions.with_columns(
            (pl.col("X") / bin_size).floor().cast(pl.Int32).alias("bin_x"),
            (pl.col("Y") / bin_size).floor().cast(pl.Int32).alias("bin_y"),
        )
        .group_by(["side", "bin_x", "bin_y"])
        .agg(pl.len().alias("samples"))
        .with_columns(
            (pl.col("bin_x") * bin_size + bin_size / 2).alias("x"),
            (pl.col("bin_y") * bin_size + bin_size / 2).alias("y"),
        )
        .sort("samples", descending=True)
    )


def setup_snapshot(
    ticks: pl.DataFrame,
    rounds: pl.DataFrame,
    seconds_after_freeze: float = SETUP_SECONDS_AFTER_FREEZE,
    tickrate: int = 64,
) -> pl.DataFrame:
    """Onde cada jogador estava no momento de "setup" de cada round.

    Pega o tick mais próximo de freeze_end + N segundos (ou a última posição viva
    antes disso, se o jogador morreu antes -- raro, mas acontece em round de
    contato rápido).
    """
    targets = rounds.select(
        pl.col("round_num"),
        (pl.col("freeze_end") + int(seconds_after_freeze * tickrate)).alias("setup_tick"),
    )

    return (
        ticks.join(targets, on="round_num", how="inner")
        .filter(pl.col("tick") <= pl.col("setup_tick"))
        .sort("tick")
        .group_by(["round_num", "steamid"])
        .agg(
            pl.col("name").last(),
            pl.col("side").last(),
            pl.col("place").last(),
            pl.col("X").last(),
            pl.col("Y").last(),
            pl.col("Z").last(),
            pl.col("is_alive").last().alias("alive_at_setup"),
        )
        .sort(["round_num", "steamid"])
    )


def zone_occupancy(setup: pl.DataFrame) -> pl.DataFrame:
    """Quantos jogadores de cada lado estavam em cada região, por round."""
    return (
        setup.filter(pl.col("place").is_not_null())
        .group_by(["round_num", "side", "place"])
        .agg(pl.len().alias("players"))
        .sort(["round_num", "side", "players"], descending=[False, False, True])
    )


def standard_setup(occupancy: pl.DataFrame) -> pl.DataFrame:
    """Setup padrão de cada lado: média de jogadores por região ao longo dos rounds.

    É a referência empírica contra a qual os rounds individuais são comparados.
    """
    n_rounds = occupancy.select(pl.col("round_num").n_unique()).item()
    return (
        occupancy.group_by(["side", "place"])
        .agg(pl.col("players").sum().alias("total_players"))
        .with_columns((pl.col("total_players") / n_rounds).alias("avg_players"))
        .sort(["side", "avg_players"], descending=[False, True])
    )


def setup_deviation(
    occupancy: pl.DataFrame,
    standard: pl.DataFrame,
    map_name: str | None = None,
) -> pl.DataFrame:
    """Desvio do setup de cada round em relação ao padrão do time.

    Cálculo: soma das diferenças absolutas de ocupação por região, dividida por 2.

    COMO LER ESSE NÚMERO (importante): ele é um índice RELATIVO, não uma contagem
    de jogadores fora do lugar. O padrão derivado é uma média fracionária
    espalhada por muitas regiões (ex: Middle 1.09, Alley 0.64, SideHall 0.45...),
    então mesmo um round perfeitamente típico acumula diferenças e nunca zera. O
    que vale é a COMPARAÇÃO entre rounds: os rounds com maior desvio são os que
    mais fugiram do que aquele time costuma fazer.
    Por isso vem junto a coluna `deviation_index`, normalizada pela mediana do
    próprio lado: 1.0 = round tão típico quanto a mediana, 2.0 = duas vezes mais
    fora do padrão que o normal daquele time.

    Com MANUAL_EXPECTED_SETUP preenchido pro mapa, usa aquele setup como
    referência em vez do padrão derivado.
    """
    reference = standard.select(["side", "place", "avg_players"])

    if map_name and map_name in MANUAL_EXPECTED_SETUP:
        manual_rows = [
            {"side": side, "place": place, "avg_players": float(count)}
            for side, places in MANUAL_EXPECTED_SETUP[map_name].items()
            for place, count in places.items()
        ]
        if manual_rows:
            reference = pl.DataFrame(manual_rows)

    # produto cartesiano round x referência, pra que região esperada e ausente no
    # round conte como desvio (e não simplesmente suma do join)
    rounds_sides = occupancy.select(["round_num", "side"]).unique()
    expected = rounds_sides.join(reference, on="side", how="left")

    joined = expected.join(occupancy, on=["round_num", "side", "place"], how="left").with_columns(
        pl.col("players").fill_null(0)
    )

    deviation = (
        joined.with_columns((pl.col("players") - pl.col("avg_players")).abs().alias("abs_diff"))
        .group_by(["round_num", "side"])
        .agg((pl.col("abs_diff").sum() / 2).alias("setup_deviation"))
    )

    return deviation.with_columns(
        (pl.col("setup_deviation") / pl.col("setup_deviation").median().over("side")).alias("deviation_index")
    ).sort(["round_num", "side"])


def player_position_profile(positions: pl.DataFrame, setup: pl.DataFrame) -> pl.DataFrame:
    """Perfil posicional por jogador/round -- vira feature do clustering da Fase 3.

    - `avg_distance_from_team`: o quanto o jogador ficou longe do centro de massa
      do próprio time durante o round. É o indicador mais direto de lurk: quem
      joga separado do time tem essa média alta de forma consistente.
    - `distinct_places`: quantas regiões o jogador passou (rotação vs. âncora).
    - `setup_place`: onde ele começou o round.
    """
    team_centroid = (
        positions.group_by(["round_num", "tick", "side"])
        .agg(pl.col("X").mean().alias("team_x"), pl.col("Y").mean().alias("team_y"))
    )

    with_centroid = positions.join(team_centroid, on=["round_num", "tick", "side"], how="left").with_columns(
        (((pl.col("X") - pl.col("team_x")) ** 2 + (pl.col("Y") - pl.col("team_y")) ** 2).sqrt()).alias(
            "distance_from_team"
        )
    )

    profile = (
        with_centroid.group_by(["round_num", "steamid", "name"])
        .agg(
            pl.col("distance_from_team").mean().alias("avg_distance_from_team"),
            pl.col("distance_from_team").max().alias("max_distance_from_team"),
            pl.col("place").n_unique().alias("distinct_places"),
            pl.col("side").first(),
        )
        .sort(["steamid", "round_num"])
    )

    return profile.join(
        setup.select(["round_num", "steamid", pl.col("place").alias("setup_place")]),
        on=["round_num", "steamid"],
        how="left",
    )


def calculate_positioning_metrics(
    tables: dict[str, pl.DataFrame], map_name: str | None = None
) -> dict[str, pl.DataFrame]:
    """Roda o pipeline de posicionamento e devolve todas as tabelas de uma vez."""
    ticks, rounds = tables["ticks"], tables["rounds"]

    positions = position_samples(ticks, rounds)
    setup = setup_snapshot(ticks, rounds)
    occupancy = zone_occupancy(setup)
    standard = standard_setup(occupancy)
    deviation = setup_deviation(occupancy, standard, map_name)
    profile = player_position_profile(positions, setup)
    heatmap = heatmap_bins(positions)

    return {
        "positions": positions,
        "setup_snapshot": setup,
        "zone_occupancy": occupancy,
        "standard_setup": standard,
        "setup_deviation": deviation,
        "position_profile": profile,
        "heatmap_bins": heatmap,
    }
