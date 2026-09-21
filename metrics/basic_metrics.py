"""
Métricas básicas de CS2 competitivo (Fase 1): ADR, KAST, trade kills, utility damage.

Filosofia do módulo: cada métrica é calculada primeiro ROUND A ROUND (uma linha por
jogador por round), e só depois agregada pro total da partida. Isso é proposital --
o diferencial desse projeto é eu (Pedro) validar as métricas comparando com o que eu
lembro de ter acontecido em rounds específicos, não só confiar num número agregado
final. Toda função devolve (per_round, summary) por esse motivo.
"""
from __future__ import annotations

import polars as pl

# Janela de tempo (segundos) pra considerar uma kill como "trade kill": matar o
# inimigo que acabou de matar um companheiro de time. 5s é a faixa usada por
# HLTV/Leetify (a maioria fica entre 3-5s) -- deixei como constante fácil de
# recalibrar se eu comparar com demos e achar que está contando trade demais/de menos.
DEFAULT_TRADE_WINDOW_SECONDS = 5.0

# Granadas que causam dano direto. NÃO inclui smokegrenade (não causa dano) nem
# planted_c4 (dano da bomba, não é "utility" no sentido clássico da métrica).
UTILITY_WEAPONS = {"hegrenade", "inferno", "molotov", "incgrenade"}


# ---------------------------------------------------------------------------
# Helpers de base
# ---------------------------------------------------------------------------

def roster_per_round(ticks: pl.DataFrame) -> pl.DataFrame:
    """Uma linha por (round_num, steamid): nome e lado (side) no início do round.

    Serve de "espinha dorsal" pras outras métricas -- é contra esse roster que a
    gente faz left join, então jogador que não teve kill/dano num round aparece
    com 0, em vez de simplesmente sumir da tabela.
    """
    return (
        ticks.sort("tick")
        .group_by(["round_num", "steamid"], maintain_order=True)
        .agg(
            pl.col("name").first(),
            pl.col("side").first(),
        )
    )


def deaths_per_round(kills: pl.DataFrame) -> pl.DataFrame:
    """Quem morreu em cada round, pela lista de mortes CONTADAS.

    A sobrevivência do KAST sai daqui, e não da vida no último tick do round.
    Pelo tick, 71 jogador-rounds nas 52 partidas apareciam como "sobreviveu"
    tendo morrido: os ticks do round acabam antes da morte do último round da
    partida ou da cauda depois do fim do round, e o jogador ganhava o S do KAST
    no mesmo round em que a morte entrava no K-D. E o contrário também: a morte
    descartada no intervalo (kills_do_round_jogado) continuava "morte" pelo
    tick. Com uma fonte só, K-D e KAST nunca se contradizem.
    """
    return (
        kills.filter(pl.col("victim_steamid").is_not_null())
        .select(["round_num", pl.col("victim_steamid").alias("steamid")])
        .unique(maintain_order=True)
        .with_columns(pl.lit(True).alias("died"))
    )


def enemy_damages(damages: pl.DataFrame) -> pl.DataFrame:
    """Dano só contra inimigos (exclui fogo amigo e linhas com side nulo)."""
    return damages.filter(
        pl.col("attacker_side").is_not_null()
        & pl.col("victim_side").is_not_null()
        & (pl.col("attacker_side") != pl.col("victim_side"))
    )


def enemy_kills(kills: pl.DataFrame) -> pl.DataFrame:
    """Kills só contra inimigos (exclui teamkill e suicídio/world)."""
    return kills.filter(
        pl.col("attacker_side").is_not_null()
        & pl.col("victim_side").is_not_null()
        & (pl.col("attacker_side") != pl.col("victim_side"))
    )


# ---------------------------------------------------------------------------
# ADR
# ---------------------------------------------------------------------------

def calculate_adr(damages: pl.DataFrame, roster: pl.DataFrame) -> tuple[pl.DataFrame, pl.DataFrame]:
    """ADR = dano médio (a inimigos, sem overkill) causado por round.

    Usa dmg_health_real, que o awpy já calcula travando o dano no HP restante da
    vítima -- sem isso, um headshot de AWP (115 de dano) num inimigo com 40 de
    vida infla o dano "de verdade" acima do que aconteceu. É assim que
    HLTV/Leetify calculam ADR também. Com vários acertos no mesmo tick a trava
    do awpy falha (usa a vida do início do tick para todos); o parsing corrige
    isso antes de chegar aqui (`parsing.parser.dano_real_no_mesmo_tick`).
    """
    dmg_by_round = (
        enemy_damages(damages)
        .group_by(["round_num", "attacker_steamid"], maintain_order=True)
        .agg(pl.col("dmg_health_real").sum().alias("damage"))
        .rename({"attacker_steamid": "steamid"})
    )

    per_round = (
        roster.select(["round_num", "steamid", "name"])
        .unique(maintain_order=True)
        .join(dmg_by_round, on=["round_num", "steamid"], how="left")
        .with_columns(pl.col("damage").fill_null(0))
        .sort(["steamid", "round_num"])
    )

    summary = (
        per_round.group_by(["steamid", "name"], maintain_order=True)
        .agg(
            pl.col("damage").sum().alias("total_damage"),
            pl.col("round_num").n_unique().alias("rounds_played"),
        )
        .with_columns((pl.col("total_damage") / pl.col("rounds_played")).alias("adr"))
        .sort("adr", descending=True)
    )
    return per_round, summary


# ---------------------------------------------------------------------------
# Utility damage
# ---------------------------------------------------------------------------

def calculate_utility_damage(damages: pl.DataFrame, roster: pl.DataFrame) -> tuple[pl.DataFrame, pl.DataFrame]:
    """Dano de granada (HE + fogo) causado a inimigos, por round e agregado."""
    dmg_by_round = (
        enemy_damages(damages)
        .filter(pl.col("weapon").is_in(UTILITY_WEAPONS))
        .group_by(["round_num", "attacker_steamid"], maintain_order=True)
        .agg(pl.col("dmg_health_real").sum().alias("utility_damage"))
        .rename({"attacker_steamid": "steamid"})
    )

    per_round = (
        roster.select(["round_num", "steamid", "name"])
        .unique(maintain_order=True)
        .join(dmg_by_round, on=["round_num", "steamid"], how="left")
        .with_columns(pl.col("utility_damage").fill_null(0))
        .sort(["steamid", "round_num"])
    )

    summary = (
        per_round.group_by(["steamid", "name"], maintain_order=True)
        .agg(
            pl.col("utility_damage").sum().alias("total_utility_damage"),
            pl.col("round_num").n_unique().alias("rounds_played"),
        )
        .with_columns(
            (pl.col("total_utility_damage") / pl.col("rounds_played")).alias("utility_damage_per_round")
        )
        .sort("utility_damage_per_round", descending=True)
    )
    return per_round, summary


# ---------------------------------------------------------------------------
# Trade kills
# ---------------------------------------------------------------------------

def _pares_de_trade(kills: pl.DataFrame, trade_window_seconds: float, tickrate: int) -> pl.DataFrame:
    """Pares (morte original, vingança): uma linha por kill de trade, com a
    kill que ela vingou nas colunas `_prev`.

    Os dois lados do par importam e são coisas diferentes: o kill de trade
    (`kill_id`) é mérito de quem vingou; a morte vingada (`victim_steamid_prev`)
    é o T do KAST de quem morreu.
    """
    window_ticks = trade_window_seconds * tickrate
    k = kills.select(
        [
            "round_num",
            "tick",
            "attacker_steamid",
            "attacker_side",
            "victim_steamid",
            "victim_side",
        ]
    ).with_row_index("kill_id")
    return k.join(k, on="round_num", suffix="_prev").filter(
        (pl.col("tick") > pl.col("tick_prev"))
        & (pl.col("tick") - pl.col("tick_prev") <= window_ticks)
        & (pl.col("attacker_side") == pl.col("victim_side_prev"))
        & (pl.col("victim_steamid") == pl.col("attacker_steamid_prev"))
    )


def traded_deaths(
    kills: pl.DataFrame,
    trade_window_seconds: float = DEFAULT_TRADE_WINDOW_SECONDS,
    tickrate: int = 64,
) -> pl.DataFrame:
    """Quem teve a morte vingada: o T do KAST.

    REGRESSÃO: o KAST marcava a vítima do KILL DE TRADE -- o inimigo que tinha
    matado o companheiro e morreu em seguida. Esse inimigo já tem um kill no
    round, então a marcação nunca acrescentava nada: o T do KAST esteve
    desligado desde a primeira versão (mudar a janela de 3s para 10s não mudava
    um único KAST), e o KAST ficava ~5 pontos abaixo do da HLTV. Quem ganha o T
    é o companheiro que morreu primeiro.
    """
    return (
        _pares_de_trade(kills, trade_window_seconds, tickrate)
        .select(["round_num", pl.col("victim_steamid_prev").alias("steamid")])
        .unique(maintain_order=True)
        .with_columns(pl.lit(True).alias("was_traded"))
    )


def identify_trade_kills(
    kills: pl.DataFrame,
    trade_window_seconds: float = DEFAULT_TRADE_WINDOW_SECONDS,
    tickrate: int = 64,
) -> pl.DataFrame:
    """Marca quais kills são "trade kills": o attacker matou quem, pouco antes,
    tinha acabado de matar um companheiro de time do attacker.

    Lógica, pensada pra ser auditável round a round:
      Pra cada round, olha pares de kills (kill_prev, kill_atual) onde:
        1. kill_atual aconteceu depois de kill_prev, dentro da janela de trade;
        2. a vítima de kill_prev era companheira de time de quem matou em
           kill_atual (ou seja, kill_prev matou um mate do attacker atual);
        3. quem morreu em kill_atual é justamente quem matou em kill_prev
           (o attacker atual vingou o companheiro matando o responsável).
      Se os três batem, kill_atual é marcada como is_trade_kill = True.
    """
    trade_kill_ids = _pares_de_trade(kills, trade_window_seconds, tickrate)["kill_id"].unique(maintain_order=True).to_list()

    return (
        kills.with_row_index("kill_id")
        .with_columns(pl.col("kill_id").is_in(trade_kill_ids).alias("is_trade_kill"))
        .drop("kill_id")
    )


def calculate_trade_kills(
    kills: pl.DataFrame,
    roster: pl.DataFrame,
    trade_window_seconds: float = DEFAULT_TRADE_WINDOW_SECONDS,
    tickrate: int = 64,
) -> tuple[pl.DataFrame, pl.DataFrame]:
    """Quantas kills de cada jogador foram trade kills, por round e agregado."""
    kills_flagged = identify_trade_kills(kills, trade_window_seconds, tickrate)
    kills_flagged = enemy_kills(kills_flagged)

    per_round = (
        kills_flagged.group_by(["round_num", "attacker_steamid"], maintain_order=True)
        .agg(
            pl.len().alias("kills"),
            pl.col("is_trade_kill").sum().alias("trade_kills"),
        )
        .rename({"attacker_steamid": "steamid"})
        .sort(["steamid", "round_num"])
    )

    summary = (
        per_round.group_by("steamid", maintain_order=True)
        .agg(
            pl.col("kills").sum().alias("total_kills"),
            pl.col("trade_kills").sum().alias("total_trade_kills"),
        )
        .join(roster.select(["steamid", "name"]).unique(maintain_order=True), on="steamid", how="left")
        .with_columns(
            pl.when(pl.col("total_kills") > 0)
            .then(100 * pl.col("total_trade_kills") / pl.col("total_kills"))
            .otherwise(0.0)
            .alias("trade_kill_pct")
        )
        .sort("total_trade_kills", descending=True)
    )
    return per_round, summary


# ---------------------------------------------------------------------------
# KAST
# ---------------------------------------------------------------------------

def calculate_kast(
    kills: pl.DataFrame,
    roster: pl.DataFrame,
    trade_window_seconds: float = DEFAULT_TRADE_WINDOW_SECONDS,
    tickrate: int = 64,
) -> tuple[pl.DataFrame, pl.DataFrame]:
    """KAST% = % de rounds em que o jogador teve pelo menos um: Kill, Assist,
    Survived (sobreviveu o round) ou foi Traded (a morte dele foi vingada por um
    companheiro dentro da janela de trade).

    É a métrica clássica de "impacto individual consistente" (popularizada por
    HLTV) -- um jogador com KAST alto raramente está "fora" do round, mesmo em
    rounds que não fechou o kill decisivo.
    """
    had_kill = (
        enemy_kills(kills)
        .select(["round_num", "attacker_steamid"])
        .unique(maintain_order=True)
        .rename({"attacker_steamid": "steamid"})
        .with_columns(pl.lit(True).alias("had_kill"))
    )

    # Assistência por flash NÃO conta como o A do KAST, como na HLTV. Medido
    # contra o KAST oficial de 50 jogadores (5 partidas): sem a flash assist,
    # 38 de 50 idênticos; contando, 33 de 50. O cegar continua medido onde é o
    # assunto (métricas de utility), só não vira "participou do round" aqui.
    assistencias = kills.filter(pl.col("assister_steamid").is_not_null())
    if "assistedflash" in assistencias.columns:
        assistencias = assistencias.filter(~pl.col("assistedflash").fill_null(False))
    had_assist = (
        assistencias
        .select(["round_num", "assister_steamid"])
        .unique(maintain_order=True)
        .rename({"assister_steamid": "steamid"})
        .with_columns(pl.lit(True).alias("had_assist"))
    )

    died = deaths_per_round(kills)

    was_traded = traded_deaths(kills, trade_window_seconds, tickrate)

    per_round = (
        roster.select(["round_num", "steamid", "name"])
        .unique(maintain_order=True)
        .join(had_kill, on=["round_num", "steamid"], how="left")
        .join(had_assist, on=["round_num", "steamid"], how="left")
        .join(died, on=["round_num", "steamid"], how="left")
        .join(was_traded, on=["round_num", "steamid"], how="left")
        .with_columns(
            [
                pl.col("had_kill").fill_null(False),
                pl.col("had_assist").fill_null(False),
                # quem jogou o round (roster) e não está entre as mortes contadas
                (~pl.col("died").fill_null(False)).alias("survived"),
                pl.col("was_traded").fill_null(False),
            ]
        )
        .drop("died")
        .with_columns(
            (pl.col("had_kill") | pl.col("had_assist") | pl.col("survived") | pl.col("was_traded")).alias(
                "kast_round"
            )
        )
        .sort(["steamid", "round_num"])
    )

    summary = (
        per_round.group_by(["steamid", "name"], maintain_order=True)
        .agg(
            pl.col("kast_round").sum().alias("kast_rounds"),
            pl.col("round_num").n_unique().alias("rounds_played"),
        )
        .with_columns((100 * pl.col("kast_rounds") / pl.col("rounds_played")).alias("kast_pct"))
        .sort("kast_pct", descending=True)
    )
    return per_round, summary


# ---------------------------------------------------------------------------
# Ponto de entrada único
# ---------------------------------------------------------------------------

def compute_all_basic_metrics(tables: dict[str, pl.DataFrame]) -> dict[str, pl.DataFrame]:
    """Roda as 4 métricas da Fase 1 e devolve um dict com todas as tabelas
    (per_round e summary de cada uma), prontas pra salvar em parquet ou plugar
    no dashboard.
    """
    roster = roster_per_round(tables["ticks"])

    adr_round, adr_summary = calculate_adr(tables["damages"], roster)
    util_round, util_summary = calculate_utility_damage(tables["damages"], roster)
    trade_round, trade_summary = calculate_trade_kills(tables["kills"], roster)
    kast_round, kast_summary = calculate_kast(tables["kills"], roster)

    return {
        "adr_per_round": adr_round,
        "adr_summary": adr_summary,
        "utility_damage_per_round": util_round,
        "utility_damage_summary": util_summary,
        "trade_kills_per_round": trade_round,
        "trade_kills_summary": trade_summary,
        "kast_per_round": kast_round,
        "kast_summary": kast_summary,
    }
