"""
Papéis nomeados: o que cada jogador FAZ, com a evidência que sustenta o rótulo.

Este módulo substitui o índice "carrega piano" antigo, que era `esforço −
recompensa`. Aquela fórmula estava errada por construção: quem tem recompensa
baixa vence a subtração, e recompensa baixa é, na maior parte das vezes, jogar
mal. Ela elegia o pior jogador da partida e colava nele um rótulo que significa
outra coisa.

Carrega piano é quem SE SACRIFICA E O TIME LUCRA COM ISSO. Por isso o índice
aqui é um PRODUTO, não uma diferença: esforço alto multiplicado por benefício ao
time. Produto zera quando qualquer um dos dois lados zera, que é exatamente o que
a definição exige — quem morre cedo sem gerar nada não é carrega piano, e quem
gera muito sem se expor também não é.

Os papéis NÃO são exclusivos: cada um é um índice independente e o mesmo jogador
pode pontuar em vários. Um AWPer pode ser carry; um âncora pode ser camper.

Sobre a escala dos índices: cada componente vira um PERCENTIL contra a
distribuição do conjunto das partidas (`archetype_reference.json`, ajustado por
scripts/fit_archetype_reference.py, mesmo padrão do global_model.json do
clustering). Isso responde "o quanto este jogador se destaca NESTE papel
comparado ao que é normal nele", que é a pergunta do card de destaque — e não
"quem é o maior desta partida", que numa partida ruim elegeria alguém mediano.
Sem o arquivo de referência, cai para normalização dentro da própria partida e
avisa.

Convenção do projeto: devolve (per_round, summary).
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import polars as pl

from metrics.awp_metrics import HOLD_MAX_DISPLACEMENT
from metrics.geometry import horizontal_distance

PROJECT_ROOT = Path(__file__).resolve().parent.parent
REFERENCE_FILE = PROJECT_ROOT / "metrics" / "archetype_reference.json"

# --- Limiares de calibração -------------------------------------------------

# Janela de trade, a mesma das métricas básicas: se o companheiro morreu e você
# não matou quem o matou em 5s, você não trocou aquela morte.
TRADE_WINDOW_SECONDS = 5.0

# Distância até o companheiro que morreu para a morte ser considerada "do seu
# lado". Além disso o jogador está jogando outra parte do mapa e não tinha como
# trocar -- cobrá-lo seria transformar posicionamento em acusação. 900u é a
# ordem de grandeza de um duelo apoiável: dá para chegar no trade dentro da
# janela sem atravessar o mapa.
BAIT_MAX_DISTANCE = 900.0

# Repick: reaparecer no mesmo ângulo. Reusa a assinatura de jiggle que
# awp_metrics já mede (decisão 1 do CLAUDE.md) -- distância percorrida alta com
# deslocamento LÍQUIDO baixo. O deslocamento líquido baixo é o mesmo limiar do
# hold; o que distingue repick de ficar parado é ter andado no meio.
REPICK_MIN_PATH = 250.0
REPICK_MIN_RATIO = 3.0  # percorreu 3x mais do que saiu do lugar

# Mínimo de situações de último vivo para o "rei do NT" aparecer. Nas 9 partidas
# são 182 tentativas em 187 rounds, ~2 por jogador por partida: sem um mínimo, o
# índice premiaria quem teve UMA situação e não converteu.
MIN_CLUTCH_ATTEMPTS = 3

# Mínimo de rounds com AWP na mão para o papel de AWPer existir. Abaixo disso é
# AWP de round de força.
MIN_AWP_ROUNDS = 4

# Kills no round que caracterizam multikill, igual ao usado nos insights.
MULTIKILL_MIN = 3


# --- Fatos por round --------------------------------------------------------

def round_facts(
    features: pl.DataFrame,
    grenades: pl.DataFrame,
    rounds: pl.DataFrame,
    positions: pl.DataFrame,
) -> pl.DataFrame:
    """Uma linha por (round, jogador) com o que os papéis precisam.

    Quase tudo já existe em `cluster_features` (dano, kills, trades, sobreviveu,
    foi trocado, tempo até o contato). O que este passo acrescenta é: se o round
    foi vencido, quem foi o primeiro do time a encostar no adversário, e quanto
    o jogador andou no round.
    """
    vencedor = rounds.select(
        pl.col("round_num").cast(pl.UInt32), pl.col("winner").alias("winner_side")
    )

    # Distância percorrida no round, das amostras de posição. É o que separa
    # camper (fica) de quem roda o mapa; `distinct_places` sozinho não separa,
    # porque dá pra andar muito dentro de duas regiões grandes.
    andou = (
        positions.sort(["round_num", "steamid", "tick"])
        .with_columns(
            (pl.col("X") - pl.col("X").shift(1).over(["round_num", "steamid"])).alias("dx"),
            (pl.col("Y") - pl.col("Y").shift(1).over(["round_num", "steamid"])).alias("dy"),
        )
        .with_columns((pl.col("dx") ** 2 + pl.col("dy") ** 2).sqrt().alias("passo"))
        .group_by(["round_num", "steamid"])
        .agg(pl.col("passo").sum().alias("path_distance_round"))
    )

    gren = grenades.select(
        ["round_num", "steamid", "enemy_blind_seconds", "utility_damage", "nades_thrown"]
    ).rename({"utility_damage": "utility_damage_gren"})

    # `cluster_features` guarda survived/was_traded como 0.0/1.0 (o clustering
    # precisa deles numericos). Aqui eles voltam a ser booleanos, senao qualquer
    # negacao estoura -- "dtype Float64 not supported in 'not' operation".
    features = features.with_columns(
        pl.col("survived").cast(pl.Boolean),
        pl.col("was_traded").cast(pl.Boolean),
    )

    facts = (
        features.join(vencedor, on="round_num", how="left")
        .join(andou, on=["round_num", "steamid"], how="left")
        .join(gren, on=["round_num", "steamid"], how="left")
        .with_columns(
            (pl.col("side") == pl.col("winner_side")).alias("round_won"),
            pl.col("path_distance_round").fill_null(0.0),
            pl.col("enemy_blind_seconds").fill_null(0.0),
            pl.col("nades_thrown").fill_null(0),
        )
    )

    # Primeiro do próprio time a tomar contato no round. A comparação é dentro do
    # time e dentro do round: "encostou antes dos companheiros" é a definição de
    # entry que o projeto usa (decisão 13 do CLAUDE.md).
    facts = facts.with_columns(
        pl.col("time_of_first_contact_s")
        .rank("min")
        .over(["round_num", "side"])
        .alias("posto_contato")
    ).with_columns(
        # Quantos companheiros empataram no primeiro lugar. Empate acontece
        # quando uma granada só pega vários do time no MESMO tick: medido, são
        # 24 de 374 lados-round nas 9 partidas, um deles com quatro jogadores
        # empatados em 10,359375s. Marcar os quatro como quem abriu o round
        # infla a métrica de entry de todo mundo -- ninguém abriu nada ali.
        pl.col("posto_contato").eq(1).sum().over(["round_num", "side"]).alias("empatados_no_primeiro")
    ).with_columns(
        (
            (pl.col("posto_contato") == 1)
            & (pl.col("empatados_no_primeiro") == 1)
            & pl.col("time_of_first_contact_s").is_not_null()
        ).alias("first_contact_of_team")
    )

    return facts.sort(["round_num", "steamid"])


def bait_events(
    kills: pl.DataFrame,
    ticks: pl.DataFrame,
    team_of: dict[int, str],
    tickrate: int = 64,
    max_distance: float = BAIT_MAX_DISTANCE,
    trade_window_seconds: float = TRADE_WINDOW_SECONDS,
) -> pl.DataFrame:
    """Mortes de companheiro com um jogador vivo e perto que não trocou.

    Uma linha por (round, jogador observado, morte de companheiro observada).
    `traded` diz se ele vingou aquela morte dentro da janela.

    O filtro de distância existe pra não transformar posicionamento em acusação:
    quem estava do outro lado do mapa não tinha como trocar, e contá-lo como
    quem "deixou morrer" seria medir o mapa, não a intenção.
    """
    janela = int(trade_window_seconds * tickrate)

    mortes = kills.select(
        pl.col("round_num").cast(pl.UInt32),
        pl.col("tick").alias("death_tick"),
        pl.col("victim_steamid"),
        pl.col("attacker_steamid").alias("killer_steamid"),
        pl.col("victim_X"), pl.col("victim_Y"),
    ).filter(pl.col("victim_steamid").is_not_null())

    if mortes.height == 0:
        return pl.DataFrame(
            schema={"round_num": pl.UInt32, "steamid": pl.UInt64, "death_tick": pl.Int64,
                    "victim_steamid": pl.UInt64, "distance": pl.Float64, "traded": pl.Boolean}
        )

    # Posição de todo mundo no tick de cada morte: uma linha por (morte, jogador).
    pos_na_morte = ticks.select(
        ["round_num", "tick", "steamid", "X", "Y", "is_alive"]
    ).join(
        mortes.select(["round_num", "death_tick"]).unique(),
        left_on=["round_num", "tick"],
        right_on=["round_num", "death_tick"],
        how="inner",
    ).rename({"tick": "death_tick"})

    candidatos = (
        mortes.join(pos_na_morte, on=["round_num", "death_tick"], how="inner")
        .filter(
            pl.col("is_alive")
            & (pl.col("steamid") != pl.col("victim_steamid"))
        )
        .with_columns(
            pl.col("steamid").map_elements(lambda s: team_of.get(s), return_dtype=pl.String).alias("time"),
            pl.col("victim_steamid").map_elements(lambda s: team_of.get(s), return_dtype=pl.String).alias("time_vitima"),
        )
        .filter(pl.col("time").is_not_null() & (pl.col("time") == pl.col("time_vitima")))
    )

    if candidatos.height == 0:
        return pl.DataFrame(
            schema={"round_num": pl.UInt32, "steamid": pl.UInt64, "death_tick": pl.Int64,
                    "victim_steamid": pl.UInt64, "distance": pl.Float64, "traded": pl.Boolean}
        )

    candidatos = candidatos.with_columns(
        (
            (pl.col("X") - pl.col("victim_X")) ** 2 + (pl.col("Y") - pl.col("victim_Y")) ** 2
        ).sqrt().alias("distance")
    ).filter(pl.col("distance") <= max_distance)

    # Trocou aquela morte? Matou o assassino do companheiro dentro da janela.
    vinganças = kills.select(
        pl.col("round_num").cast(pl.UInt32),
        pl.col("attacker_steamid").alias("steamid"),
        pl.col("victim_steamid").alias("killer_steamid"),
        pl.col("tick").alias("revenge_tick"),
    )

    com_troca = (
        candidatos.join(vinganças, on=["round_num", "steamid", "killer_steamid"], how="left")
        .with_columns(
            (
                pl.col("revenge_tick").is_not_null()
                & (pl.col("revenge_tick") > pl.col("death_tick"))
                & (pl.col("revenge_tick") <= pl.col("death_tick") + janela)
            ).alias("traded")
        )
        .group_by(["round_num", "steamid", "death_tick", "victim_steamid"])
        .agg(pl.col("distance").first(), pl.col("traded").any())
    )

    return com_troca.sort(["round_num", "death_tick", "steamid"])


def repick_engagements(styles: pl.DataFrame) -> pl.DataFrame:
    """Marca quais engajamentos têm a assinatura de repick.

    Recebe a saída de `awp_metrics.classify_engagement_style` (que já mede
    deslocamento líquido e distância percorrida) e aplica o critério de jiggle:
    andou bastante e terminou perto de onde começou. É "sai e volta no mesmo
    ângulo", não "trocou a morte do companheiro" -- essa é outra métrica
    (trade_share).
    """
    if styles.height == 0:
        return styles.with_columns(pl.lit(False).alias("repick"))

    return styles.with_columns(
        (
            pl.col("net_displacement").is_not_null()
            & (pl.col("net_displacement") < HOLD_MAX_DISPLACEMENT)
            & (pl.col("path_distance") >= REPICK_MIN_PATH)
            & (pl.col("path_distance") >= REPICK_MIN_RATIO * pl.col("net_displacement").clip(1.0))
        ).alias("repick")
    )


# --- Referência de escala ---------------------------------------------------

def load_reference(path: Path = REFERENCE_FILE) -> dict | None:
    """Quantis de cada componente no conjunto das partidas, ou None."""
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def percentil(valor: float | None, quantis: list[float] | None) -> float:
    """Posição de `valor` na distribuição de referência, de 0 a 1.

    Percentil e não z-score porque os componentes são assimétricos (dano de
    utility, clutches, picks de abertura têm cauda longa) e um z-score deixaria
    um único jogador extremo achatar todos os outros.
    """
    if valor is None or quantis is None or not quantis:
        return 0.0
    arr = np.asarray(quantis, dtype=float)
    return float(np.searchsorted(arr, float(valor), side="right") / len(arr))


# --- Sinais de economia (a forma ECO do carrega piano) ----------------------

# Nomes de exibição, como vêm no demo (`active_weapon_name`): "AK-47", não
# "ak47". Descobri isso na marra -- a primeira versão usou os codenames e casou
# zero linha em 9 partidas, o que passaria como "ninguém joga de SMG".
SMGS = {"MP9", "MAC-10", "MP5-SD", "UMP-45", "P90", "MP7", "PP-Bizon"}
RIFLES = {"AK-47", "M4A1-S", "M4A4", "Galil AR", "FAMAS", "AUG", "SG 553",
          "AWP", "SSG 08", "SCAR-20", "G3SG1"}

# Fração do time que precisa estar de rifle para a SMG de um jogador contar como
# sacrifício de economia. Abaixo disso é round de eco do time inteiro, e aí a SMG
# não é sacrifício de ninguém em particular.
TEAM_RIFLE_FRACTION = 0.60

# Quanto abaixo da média do próprio time, em dólares de equipamento, conta como
# ter comprado menos para o companheiro comprar mais. Medido em match_01: o
# quartil de baixo do desvio fica em -280, e quem fica sistematicamente abaixo
# aparece com média de -300 a -400.
UNDERBUY_DELTA = -400.0


def economy_signals(ticks: pl.DataFrame, rounds: pl.DataFrame) -> pl.DataFrame:
    """Equipamento de cada jogador contra a média do PRÓPRIO TIME no mesmo round.

    A comparação é interna e por round de propósito: o que interessa não é ter
    pouco dinheiro (o time inteiro tem, em round de eco), é ter menos que os
    companheiros no mesmo round -- que é a assinatura de quem abriu mão para o
    outro comprar.

    A arma primária é a mais EMPUNHADA no round, não a do fim do freeze time: no
    freeze o jogador costuma estar com a faca ou a pistola na mão, e uma versão
    anterior disto contou zero SMG em 9 partidas por causa disso.
    """
    alvo = rounds.select(["round_num", "freeze_end"])

    compra = (
        ticks.join(alvo, on="round_num", how="inner")
        .filter(pl.col("tick") >= pl.col("freeze_end"))
        .sort("tick")
        .group_by(["round_num", "steamid"])
        .first()
        .select(
            ["round_num", "steamid", "name", "side",
             # o awpy devolve este campo como UInt32 em 7 das 9 partidas e
             # Float64 nas outras 2 (depende de a demo ter tick sem o valor).
             # Normalizar aqui deixa o schema de saída estável -- sem isso,
             # empilhar as partidas para qualquer análise do conjunto estoura.
             pl.col("current_equip_value").cast(pl.Float64)]
        )
    )

    primaria = (
        ticks.filter(
            pl.col("is_alive") & pl.col("active_weapon_name").is_in(list(SMGS | RIFLES))
        )
        .group_by(["round_num", "steamid", "active_weapon_name"])
        .len()
        .sort("len", descending=True)
        .group_by(["round_num", "steamid"], maintain_order=True)
        .first()
        .select(["round_num", "steamid", pl.col("active_weapon_name").alias("primary_weapon")])
    )

    eco = (
        compra.join(primaria, on=["round_num", "steamid"], how="left")
        .with_columns(
            pl.col("current_equip_value").mean().over(["round_num", "side"]).alias("team_equip_mean"),
            pl.col("primary_weapon").is_in(list(SMGS)).fill_null(False).alias("is_smg"),
            pl.col("primary_weapon").is_in(list(RIFLES)).fill_null(False).alias("is_rifle"),
        )
        .with_columns(
            (pl.col("current_equip_value") - pl.col("team_equip_mean")).alias("equip_delta"),
            pl.col("is_rifle").mean().over(["round_num", "side"]).alias("team_frac_rifle"),
        )
        .with_columns(
            (
                (pl.col("equip_delta") <= UNDERBUY_DELTA)
                | (pl.col("is_smg") & (pl.col("team_frac_rifle") >= TEAM_RIFLE_FRACTION))
            ).alias("eco_sacrifice")
        )
    )
    return eco.select(
        ["round_num", "steamid", "current_equip_value", "team_equip_mean", "equip_delta",
         "primary_weapon", "is_smg", "team_frac_rifle", "eco_sacrifice"]
    )


def solo_hold_signals(player_areas: pl.DataFrame) -> pl.DataFrame:
    """Rounds de CT em que o jogador ficou SOZINHO na área que jogou.

    É a forma CT do carrega piano: segurar um bombsite sem companheiro enquanto o
    time joga em outro lugar. Quem está sozinho na área entra em desvantagem
    numérica por construção -- não precisa contar inimigos pra saber que um
    jogador contra a execução de um time está em minoria.
    """
    if player_areas.height == 0:
        return pl.DataFrame(
            schema={"round_num": pl.UInt32, "steamid": pl.UInt64, "alone_in_area": pl.Boolean}
        )

    return (
        player_areas.with_columns(
            pl.len().over(["round_num", "side", "area"]).alias("na_area")
        )
        .with_columns(((pl.col("side") == "ct") & (pl.col("na_area") == 1)).alias("alone_in_area"))
        .select(["round_num", "steamid", "alone_in_area"])
    )


# --- Componentes por jogador ------------------------------------------------

# Todo componente bruto que entra em algum índice. A lista é explícita porque é
# ela que o arquivo de referência precisa cobrir -- componente novo sem entrada
# na referência cai em percentil 0 e some do índice em silêncio.
COMPONENTES = [
    "first_contact_share", "util_per_round", "frac_entering_fight", "death_rate",
    "traded_death_share", "piano_t_share", "piano_ct_share", "piano_eco_share",
    "damage_share", "kill_share", "multikill_rounds", "clutch_wins",
    "distinct_places_mean", "path_per_round", "repick_share",
    "awp_round_share", "awp_conversion", "awp_opening_picks",
    "bait_no_trade_share", "bait_untraded_per_round", "bait_return_per_opp", "survival_rate",
    "clutch_attempts", "clutch_conversion", "clutch_damage_per_attempt",
]


def player_components(
    facts: pl.DataFrame,
    eco: pl.DataFrame,
    solo: pl.DataFrame,
    bait: pl.DataFrame,
    repick: pl.DataFrame,
    clutch_round: pl.DataFrame,
    awp_summary: pl.DataFrame | None,
    team_of: dict[int, str],
) -> tuple[pl.DataFrame, pl.DataFrame]:
    """Devolve (per_round, componentes): os fatos round a round e o agregado.

    Os componentes saem em unidade CRUA (fração de rounds, dólares, unidades de
    mapa). A conversão para escala comparável acontece só em `archetype_indices`,
    contra a referência do conjunto -- assim a tabela por jogador continua
    auditável em número de jogo, que é o que permite discordar do índice.
    """
    per_round = (
        facts.join(eco, on=["round_num", "steamid"], how="left")
        .join(solo, on=["round_num", "steamid"], how="left")
        .with_columns(
            pl.col("eco_sacrifice").fill_null(False),
            pl.col("alone_in_area").fill_null(False),
            pl.col("steamid")
            .map_elements(lambda s: team_of.get(s), return_dtype=pl.String)
            .alias("team"),
        )
        .with_columns(
            # As três formas do carrega piano. O que une as três é a segunda
            # metade: o time converteu o round em que ele pagou a conta.
            (
                (pl.col("side") == "t")
                & pl.col("first_contact_of_team")
                & ~pl.col("survived")
            ).alias("piano_t_paid_raw"),
            (
                (pl.col("side") == "ct") & pl.col("alone_in_area") & ~pl.col("survived")
            ).alias("piano_ct_paid_raw"),
            pl.col("eco_sacrifice").alias("piano_eco_paid_raw"),
        )
        .with_columns(
            # "o time colheu": venceu o round, ou (no caso do entry) a morte dele
            # foi trocada -- a troca e o benefício imediato mesmo em round perdido
            (pl.col("piano_t_paid_raw") & (pl.col("round_won") | pl.col("was_traded"))).alias("piano_t"),
            (pl.col("piano_ct_paid_raw") & pl.col("round_won")).alias("piano_ct"),
            (pl.col("piano_eco_paid_raw") & pl.col("round_won")).alias("piano_eco"),
        )
    )

    rounds_por_lado = per_round.group_by(["steamid", "side"]).agg(pl.len().alias("n"))
    t_rounds = rounds_por_lado.filter(pl.col("side") == "t").select(
        ["steamid", pl.col("n").alias("t_rounds")]
    )
    ct_rounds = rounds_por_lado.filter(pl.col("side") == "ct").select(
        ["steamid", pl.col("n").alias("ct_rounds")]
    )

    base = per_round.group_by(["steamid", "name", "team"]).agg(
        pl.len().alias("rounds_played"),
        pl.col("first_contact_of_team").mean().alias("first_contact_share"),
        (pl.col("enemy_blind_seconds") + pl.col("utility_damage")).mean().alias("util_per_round"),
        pl.col("frac_entering_fight").mean().alias("frac_entering_fight"),
        pl.col("survived").mean().alias("survival_rate"),
        pl.col("was_traded").filter(~pl.col("survived")).mean().alias("traded_death_share"),
        pl.col("damage").sum().alias("total_damage"),
        pl.col("kills").sum().alias("total_kills"),
        (pl.col("kills") >= MULTIKILL_MIN).sum().alias("multikill_rounds"),
        pl.col("distinct_places").mean().alias("distinct_places_mean"),
        pl.col("path_distance_round").mean().alias("path_per_round"),
        pl.col("piano_t").sum().alias("piano_t_rounds"),
        pl.col("piano_ct").sum().alias("piano_ct_rounds"),
        pl.col("piano_eco").sum().alias("piano_eco_rounds"),
        pl.col("eco_sacrifice").sum().alias("eco_sacrifice_rounds"),
    )

    # Fatias do time: dano e kills do jogador sobre o total do próprio time. E a
    # traducao direta de "levar o time nas costas" -- e por ser fracao do time,
    # não sofre com partida de placar alto ou baixo.
    totais_time = base.group_by("team").agg(
        pl.col("total_damage").sum().alias("team_damage"),
        pl.col("total_kills").sum().alias("team_kills"),
    )

    comp = (
        base.join(totais_time, on="team", how="left")
        .join(t_rounds, on="steamid", how="left")
        .join(ct_rounds, on="steamid", how="left")
        .with_columns(
            pl.col("t_rounds").fill_null(0), pl.col("ct_rounds").fill_null(0),
            pl.col("traded_death_share").fill_null(0.0),
        )
        .with_columns(
            (pl.col("total_damage") / pl.col("team_damage")).alias("damage_share"),
            (pl.col("total_kills") / pl.col("team_kills")).alias("kill_share"),
            (1.0 - pl.col("survival_rate")).alias("death_rate"),
            pl.when(pl.col("t_rounds") > 0)
            .then(pl.col("piano_t_rounds") / pl.col("t_rounds"))
            .otherwise(0.0)
            .alias("piano_t_share"),
            pl.when(pl.col("ct_rounds") > 0)
            .then(pl.col("piano_ct_rounds") / pl.col("ct_rounds"))
            .otherwise(0.0)
            .alias("piano_ct_share"),
            (pl.col("piano_eco_rounds") / pl.col("rounds_played")).alias("piano_eco_share"),
        )
    )

    comp = _junta_repick(comp, repick)
    comp = _junta_bait(comp, bait)
    comp = _junta_clutch(comp, clutch_round)
    comp = _junta_awp(comp, awp_summary)

    return per_round, comp


def _junta_repick(comp: pl.DataFrame, repick: pl.DataFrame) -> pl.DataFrame:
    """Fracao dos engajamentos do jogador com assinatura de repick."""
    if repick.height == 0 or "repick" not in repick.columns:
        return comp.with_columns(
            pl.lit(0.0).alias("repick_share"), pl.lit(0, dtype=pl.UInt32).alias("engagements")
        )
    agg = repick.group_by("steamid").agg(
        pl.len().cast(pl.UInt32).alias("engagements"),
        pl.col("repick").mean().alias("repick_share"),
    )
    return comp.join(agg, on="steamid", how="left").with_columns(
        pl.col("repick_share").fill_null(0.0), pl.col("engagements").fill_null(0)
    )


def _junta_bait(comp: pl.DataFrame, bait: pl.DataFrame) -> pl.DataFrame:
    """Oportunidades de troca perto de um companheiro morto, e o que saiu delas."""
    if bait.height == 0:
        return comp.with_columns(
            pl.lit(0, dtype=pl.UInt32).alias("bait_opportunities"),
            pl.lit(0.0).alias("bait_no_trade_share"),
            pl.lit(0.0).alias("bait_return_per_opp"),
            pl.lit(0.0).alias("bait_untraded_per_round"),
        )
    agg = bait.group_by("steamid").agg(
        pl.len().cast(pl.UInt32).alias("bait_opportunities"),
        (~pl.col("traded")).mean().alias("bait_no_trade_share"),
    )
    comp = comp.join(agg, on="steamid", how="left").with_columns(
        pl.col("bait_opportunities").fill_null(0), pl.col("bait_no_trade_share").fill_null(0.0)
    )
    # Retorno: kills por oportunidade. E o "muitas vezes sem conseguir nada" da
    # definição -- fica como evidencia ao lado do indice, não como multiplicador,
    # porque o que define o papel e o comportamento, não o aproveitamento.
    #
    # O indice usa `bait_untraded_per_round`, não a fracao: não trocar e o normal
    # (mediana de 0,84 nas 9 partidas), então a fracao quase não separa ninguem e
    # ainda faria a evidencia soar como acusação em cima de um número médio. O
    # que varia de verdade e QUANTAS vezes por round ele esta por perto de um
    # companheiro caindo sem que a troca venha.
    return comp.with_columns(
        pl.when(pl.col("bait_opportunities") > 0)
        .then(pl.col("total_kills") / pl.col("bait_opportunities"))
        .otherwise(0.0)
        .alias("bait_return_per_opp"),
        (
            pl.col("bait_opportunities") * pl.col("bait_no_trade_share")
            / pl.col("rounds_played")
        ).alias("bait_untraded_per_round"),
    )


def _junta_clutch(comp: pl.DataFrame, clutch_round: pl.DataFrame) -> pl.DataFrame:
    """Tentativas de último vivo, conversão e dano produzido dentro delas."""
    if clutch_round.height == 0:
        return comp.with_columns(
            pl.lit(0, dtype=pl.UInt32).alias("clutch_attempts"),
            pl.lit(0, dtype=pl.UInt32).alias("clutch_wins"),
            pl.lit(0.0).alias("clutch_conversion"),
            pl.lit(0.0).alias("clutch_damage_per_attempt"),
        )
    tem_dano = "damage_in_clutch" in clutch_round.columns
    agg = clutch_round.group_by("steamid").agg(
        pl.len().cast(pl.UInt32).alias("clutch_attempts"),
        pl.col("won").sum().cast(pl.UInt32).alias("clutch_wins"),
        (
            pl.col("damage_in_clutch").mean() if tem_dano else pl.lit(0.0)
        ).alias("clutch_damage_per_attempt"),
    )
    return (
        comp.join(agg, on="steamid", how="left")
        .with_columns(
            pl.col("clutch_attempts").fill_null(0),
            pl.col("clutch_wins").fill_null(0),
            pl.col("clutch_damage_per_attempt").fill_null(0.0),
        )
        .with_columns(
            pl.when(pl.col("clutch_attempts") > 0)
            .then(pl.col("clutch_wins") / pl.col("clutch_attempts"))
            .otherwise(0.0)
            .alias("clutch_conversion")
        )
    )


def _junta_awp(comp: pl.DataFrame, awp_summary: pl.DataFrame | None) -> pl.DataFrame:
    """Rounds com AWP na mao, conversão da primeira briga e picks de abertura."""
    vazio = comp.with_columns(
        pl.lit(0, dtype=pl.Int64).alias("awp_rounds"),
        pl.lit(0.0).alias("awp_round_share"),
        pl.lit(0.0).alias("awp_conversion"),
        pl.lit(0, dtype=pl.Int64).alias("awp_opening_picks"),
    )
    if awp_summary is None or awp_summary.height == 0:
        return vazio
    necessarias = {"steamid", "awp_rounds", "engagement_conversion_pct", "opening_picks"}
    if not necessarias.issubset(set(awp_summary.columns)):
        return vazio

    agg = awp_summary.select(
        [
            "steamid",
            pl.col("awp_rounds").cast(pl.Int64),
            pl.col("engagement_conversion_pct").alias("awp_conversion"),
            pl.col("opening_picks").cast(pl.Int64).alias("awp_opening_picks"),
        ]
    )
    return (
        comp.join(agg, on="steamid", how="left")
        .with_columns(
            pl.col("awp_rounds").fill_null(0),
            pl.col("awp_conversion").fill_null(0.0),
            pl.col("awp_opening_picks").fill_null(0),
        )
        .with_columns((pl.col("awp_rounds") / pl.col("rounds_played")).alias("awp_round_share"))
    )


# --- Indices dos papeis -----------------------------------------------------

# Metadados de cada papel: o rotulo que aparece no card e a frase curta que
# explica o que ele significa. O texto e DESCRITIVO em todos, inclusive nos
# criticos (mochila, baiter): o card descreve comportamento, nunca julga a
# pessoa. "Foi mal" não e destaque -- ver `pick_highlight`.
PAPEIS = {
    "carrega_piano": (
        "Carrega piano",
        "assume o custo e o time colhe",
    ),
    "carry": (
        "Carry",
        "leva o time nas costas",
    ),
    "awper": (
        "AWPer",
        "jogou de AWP e produziu com ela",
    ),
    "rei_do_nt": (
        "Rei do NT",
        "chega muito em último vivo e quase não converte",
    ),
    "camper": (
        "Camper",
        "poucas regiões por round, quase não se desloca",
    ),
    "repick": (
        "Repick",
        "reaparece no mesmo ângulo em vez de ocupar espaço",
    ),
    "baiter": (
        "Joga atras da morte alheia",
        "companheiro cai por perto e a troca não vem",
    ),
    "mochila": (
        "Carregado",
        "pouco esforço e pouco impacto no round",
    ),
}


def _percentis(valores, quantis: list[float] | None) -> list[float]:
    """Percentil de cada valor contra a referencia, ou dentro da própria partida."""
    brutos = [None if v is None else float(v) for v in valores]
    if quantis:
        return [percentil(v, quantis) for v in brutos]

    # Sem referencia: posicao dentro da própria partida. E o melhor que da pra
    # fazer, e e pior de proposito -- numa partida em que ninguem se destacou,
    # alguem ainda fica em 1,0. Quem chama avisa.
    validos = sorted(v for v in brutos if v is not None)
    if not validos:
        return [0.0 for _ in brutos]
    return [
        0.0 if v is None else (sum(1 for x in validos if x <= v) / len(validos))
        for v in brutos
    ]


def _media(*colunas: list[float]) -> list[float]:
    return [sum(vals) / len(vals) for vals in zip(*colunas)]


def archetype_indices(
    components: pl.DataFrame, reference: dict | None = None
) -> pl.DataFrame:
    """Um indice por papel para cada jogador, com a evidencia que o sustenta.

    Cada componente bruto vira percentil contra a referencia do conjunto (ver o
    topo do modulo). Os indices sao combinacoes explicitas desses percentis:

    - carrega_piano: soma das TRES formas ja pagas (entry de T, solo hold de CT,
      sacrificio de economia). Nao e uma formula de entry -- um jogador pode ser
      carrega piano a partida inteira sem nunca ter sido o primeiro a morrer.
    - carry: fatia de dano, fatia de kills, multikills e clutches convertidos.
    - mochila: esforco baixo E impacto baixo, como produto dos dois complementos.
    - rei_do_nt: muitas tentativas de ultimo vivo, producao alta dentro delas e
      conversao baixa. So existe acima de MIN_CLUTCH_ATTEMPTS.
    - camper: poucas regioes distintas E pouco deslocamento, como produto.
    - repick: fracao de engajamentos com a assinatura de jiggle.
    - awper: fatia de rounds com AWP vezes o que produziu com ela. So existe
      acima de MIN_AWP_ROUNDS.
    - baiter: companheiro caiu perto, a troca nao veio, e ele seguiu vivo.
    """
    if components.height == 0:
        return components

    quantis = (reference or {}).get("quantis", {})
    pct = {
        nome: _percentis(components[nome].to_list(), quantis.get(nome))
        for nome in COMPONENTES
        if nome in components.columns
    }

    zeros = [0.0] * components.height

    def p(nome: str) -> list[float]:
        return pct.get(nome, zeros)

    esforco = _media(
        p("first_contact_share"), p("util_per_round"),
        p("frac_entering_fight"), p("death_rate"),
    )
    impacto = _media(p("damage_share"), p("kill_share"))

    # O carrega piano soma as tres formas ANTES do percentil: as tres são a
    # mesma moeda (fracao de rounds em que ele pagou e o time colheu), então
    # somar em unidade crua e legitimo e preserva quem faz um pouco de cada.
    piano_bruto = [
        a + b + c
        for a, b, c in zip(
            components["piano_t_share"].to_list(),
            components["piano_ct_share"].to_list(),
            components["piano_eco_share"].to_list(),
        )
    ]
    piano = _percentis(piano_bruto, quantis.get("piano_total_share"))

    carry = _media(p("damage_share"), p("kill_share"), p("multikill_rounds"), p("clutch_wins"))
    mochila = [(1 - e) * (1 - i) for e, i in zip(esforco, impacto)]
    camper = [
        (1 - d) * (1 - c)
        for d, c in zip(p("distinct_places_mean"), p("path_per_round"))
    ]
    baiter = [b * s for b, s in zip(p("bait_untraded_per_round"), p("survival_rate"))]

    tentativas = components["clutch_attempts"].to_list()
    conversao = components["clutch_conversion"].to_list()
    rei_nt = [
        0.0 if t < MIN_CLUTCH_ATTEMPTS else a * d * (1 - c)
        for t, a, d, c in zip(tentativas, p("clutch_attempts"), p("clutch_damage_per_attempt"), conversao)
    ]

    awp_rounds = components["awp_rounds"].to_list()
    produz = _media(p("awp_conversion"), p("awp_opening_picks"))
    awper = [
        0.0 if r < MIN_AWP_ROUNDS else s * q
        for r, s, q in zip(awp_rounds, p("awp_round_share"), produz)
    ]

    return components.with_columns(
        pl.Series("piano_total_share", piano_bruto),
        pl.Series("effort_pct", esforco),
        pl.Series("impact_pct", impacto),
        pl.Series("idx_carrega_piano", piano),
        pl.Series("idx_carry", carry),
        pl.Series("idx_mochila", mochila),
        pl.Series("idx_camper", camper),
        pl.Series("idx_repick", p("repick_share")),
        pl.Series("idx_baiter", baiter),
        pl.Series("idx_rei_do_nt", rei_nt),
        pl.Series("idx_awper", awper),
    )


def piano_form(row: dict) -> str | None:
    """Qual das tres formas do carrega piano pesou mais para este jogador.

    Existe porque o card precisa dizer COMO ele pagou a conta: entrar e morrer
    abrindo espaco, segurar bomb sozinho, ou abrir mao de arma. Sem isso o
    rotulo vira generico e o leitor nao consegue conferir no replay.
    """
    formas = {
        "entrada": row.get("piano_t_share") or 0.0,
        "solo no bomb": row.get("piano_ct_share") or 0.0,
        "economia": row.get("piano_eco_share") or 0.0,
    }
    maior = max(formas, key=lambda k: formas[k])
    return maior if formas[maior] > 0 else None


def _plural(n: float, singular: str, plural: str) -> str:
    """"1 round" e "3 rounds". Detalhe pequeno que denuncia texto gerado."""
    n = int(n)
    return f"{n} {singular if n == 1 else plural}"


def evidencia(papel: str, row: dict) -> str:
    """Frase curta de evidência, só com o que existe naquela partida.

    Regra do projeto: campo que não existe some da frase. Uma frase curta e
    verdadeira vale mais que uma completa e inventada.

    Papel sem sustentação nenhuma devolve string VAZIA, e não uma frase com
    zeros. "AWP na mão em 0 rounds" descreve a ausência do papel como se fosse o
    papel -- foi o que uma varredura das 720 frases possíveis (8 papéis x 90
    jogador-partidas) encontrou em 74 casos. Hoje eles não chegam à tela porque
    `pick_highlight` ignora índice zero, mas a frase não pode depender disso.
    """
    pedacos: list[str] = []

    if papel == "carrega_piano":
        forma = piano_form(row)
        if forma is None:
            return ""
        if forma == "entrada":
            pedacos.append(
                "abriu o contato do time e morreu em "
                + _plural(row["piano_t_rounds"], "round convertido", "rounds convertidos")
            )
        elif forma == "solo no bomb":
            pedacos.append(
                "segurou bomb sozinho e caiu em "
                + _plural(row["piano_ct_rounds"], "round que o time ganhou",
                          "rounds que o time ganhou")
            )
        elif forma == "economia":
            pedacos.append(
                "jogou "
                + _plural(row["eco_sacrifice_rounds"], "round", "rounds")
                + " com menos equipamento que o time"
            )
        if row.get("traded_death_share"):
            pedacos.append(f"{row['traded_death_share'] * 100:.0f}% das mortes dele foram trocadas")

    elif papel == "carry":
        pedacos.append(f"{row['damage_share'] * 100:.0f}% do dano do time")
        if row.get("multikill_rounds"):
            pedacos.append(_plural(row["multikill_rounds"], "round de multikill",
                                   "rounds de multikill"))
        if row.get("clutch_wins"):
            pedacos.append(_plural(row["clutch_wins"], "clutch fechado", "clutches fechados"))

    elif papel == "awper":
        if not row.get("awp_rounds"):
            return ""
        pedacos.append("AWP na mão em " + _plural(row["awp_rounds"], "round", "rounds"))
        if row.get("awp_conversion"):
            pedacos.append(f"{row['awp_conversion']:.0f}% de conversão na primeira briga")
        if row.get("awp_opening_picks"):
            pedacos.append(_plural(row["awp_opening_picks"], "pick de abertura",
                                   "picks de abertura"))

    elif papel == "rei_do_nt":
        if not row.get("clutch_attempts"):
            return ""
        pedacos.append("ficou por último " + _plural(row["clutch_attempts"], "vez", "vezes"))
        pedacos.append(_plural(row["clutch_wins"], "convertida", "convertidas"))
        if row.get("clutch_damage_per_attempt"):
            pedacos.append(f"média de {row['clutch_damage_per_attempt']:.0f} de dano em cada")

    elif papel == "camper":
        pedacos.append(f"{row['distinct_places_mean']:.1f} regiões por round")
        pedacos.append(f"{row['path_per_round']:.0f}u percorridas")

    elif papel == "repick":
        if not row.get("repick_share"):
            return ""
        pedacos.append(f"{row['repick_share'] * 100:.0f}% dos engajamentos saindo e voltando")
        if row.get("engagements"):
            pedacos.append("em " + _plural(row["engagements"], "briga", "brigas"))

    elif papel == "baiter":
        if not row.get("bait_opportunities"):
            return ""
        # A frase conta o que aconteceu, sem adjetivo: quantas vezes um
        # companheiro caiu perto dele sem a troca vir, e o que ele tirou disso.
        pedacos.append(
            _plural(row["bait_opportunities"], "morte de companheiro", "mortes de companheiro")
            + f" a menos de {BAIT_MAX_DISTANCE:.0f}u dele"
        )
        pedacos.append(f"sobreviveu a {row['survival_rate'] * 100:.0f}% dos rounds")
        if row.get("bait_return_per_opp") is not None:
            pedacos.append(f"{row['bait_return_per_opp']:.1f} kill por situação")

    elif papel == "mochila":
        pedacos.append(f"{row['damage_share'] * 100:.0f}% do dano do time")
        pedacos.append(f"sobreviveu a {row['survival_rate'] * 100:.0f}% dos rounds")

    return ", ".join(p for p in pedacos if p)


# Papeis que descrevem o jogador por baixo. Nao são proibidos no card de
# destaque -- um mochila extremo E o retrato daquela partida -- mas so entram
# quando o indice e alto de verdade, porque "foi mal" não e destaque.
PAPEIS_CRITICOS = ("mochila", "baiter", "rei_do_nt")

# O quanto um papel critico precisa estar acima do normal para virar destaque.
# 0,85 = entre os 15% mais marcantes daquele papel no conjunto das partidas.
LIMIAR_CRITICO = 0.85


def pick_highlight(
    indices: pl.DataFrame,
    excluir_steamid: int | None = None,
    excluir_papeis: tuple[str, ...] = ("carry",),
) -> dict | None:
    """Escolhe quem vai no card da direita: o jogador que exemplifica um papel
    com MAIS FORCA, comparado ao que e normal naquele papel.

    O criterio e o proprio indice, porque ele ja e um percentil contra a
    distribuicao do conjunto -- 0,9 em camper e 0,9 em AWPer querem dizer a
    mesma coisa ("entre os 10% mais marcantes naquele papel"), e por isso podem
    competir na mesma escala. NAO ha ordem de preferencia entre papeis: se o
    carrega piano da partida foi mediano e teve um AWPer dominante, ganha o
    AWPer.

    `excluir_steamid` tira quem ja aparece no card da esquerda, e
    `excluir_papeis` tira o PAPEL daquele card -- sem isso os dois destaques da
    partida saem como "carry" e a aba conta a mesma coisa duas vezes.
    """
    candidatos = []
    for row in indices.iter_rows(named=True):
        if excluir_steamid is not None and row["steamid"] == excluir_steamid:
            continue
        for papel in PAPEIS:
            if papel in excluir_papeis:
                continue
            valor = row.get(f"idx_{papel}") or 0.0
            if valor <= 0:
                continue
            if papel in PAPEIS_CRITICOS and valor < LIMIAR_CRITICO:
                continue
            candidatos.append(
                {
                    "steamid": row["steamid"],
                    "name": row["name"],
                    "team": row["team"],
                    "role": papel,
                    "label": PAPEIS[papel][0],
                    "meaning": PAPEIS[papel][1],
                    "index": float(valor),
                    "evidence": evidencia(papel, row),
                }
            )

    if not candidatos:
        return None
    return max(candidatos, key=lambda c: c["index"])


# --- Orquestracao -----------------------------------------------------------

def engagement_ticks(kills: pl.DataFrame) -> pl.DataFrame:
    """Brigas resolvidas em que cada jogador esteve: as que ele matou e as que morreu.

    Usar kills (e nao a tabela de tiros) mantem o custo baixo e cobre os dois
    lados do duelo. Usar so as kills dele enviesaria o repick para as vezes em
    que o jiggle deu certo.
    """
    def lado(col: str) -> pl.DataFrame:
        return kills.select(
            pl.col("round_num").cast(pl.UInt32),
            pl.col(col).alias("steamid"),
            pl.col("tick").alias("engagement_tick"),
        )

    return (
        pl.concat([lado("attacker_steamid"), lado("victim_steamid")])
        .filter(pl.col("steamid").is_not_null())
        .unique()
        .sort(["round_num", "engagement_tick"])
    )


def compute_for_match(
    tables: dict,
    outputs: dict,
    positions: pl.DataFrame,
    player_areas: pl.DataFrame,
    team_of: dict[int, str],
    winner_team_of_round: dict[int, str],
    tickrate: int = 64,
    reference: dict | None = None,
) -> tuple[pl.DataFrame, pl.DataFrame]:
    """Monta todos os papeis de uma partida. Devolve (per_round, summary).

    Existe para o pipeline (scripts/process_demo.py) e o ajuste da referencia
    (scripts/fit_archetype_reference.py) rodarem exatamente o mesmo caminho --
    referencia ajustada por um caminho diferente do que a gera seria uma escala
    que nao corresponde ao que o painel mostra.
    """
    from metrics.awp_metrics import classify_engagement_style
    from metrics.clutch import add_damage_in_clutch, clutch_situations

    ticks, kills, rounds = tables["ticks"], tables["kills"], tables["rounds"]

    facts = round_facts(outputs["cluster_features"], outputs["grenades_per_round"], rounds, positions)
    eco = economy_signals(ticks, rounds)
    solo = solo_hold_signals(player_areas)
    bait = bait_events(kills, ticks, team_of, tickrate=tickrate)

    styles = classify_engagement_style(engagement_ticks(kills), ticks, tickrate=tickrate)
    repick = repick_engagements(styles)

    clutch_round, _ = clutch_situations(kills, rounds, team_of, winner_team_of_round)
    clutch_round = add_damage_in_clutch(clutch_round, tables["damages"], team_of)

    per_round, comp = player_components(
        facts, eco, solo, bait, repick, clutch_round, outputs.get("awp_summary"), team_of
    )
    summary = archetype_indices(comp, reference)
    return per_round, summary


def build_reference(componentes: pl.DataFrame, n_quantis: int = 100) -> dict:
    """Quantis de cada componente no conjunto das partidas.

    Guarda os quantis e nao a amostra inteira: o arquivo fica pequeno e legivel
    no diff, e o percentil sai de uma busca binaria. `piano_total_share` entra
    junto porque o indice de carrega piano e calculado sobre a soma das tres
    formas, nao sobre cada uma.
    """
    quantis: dict[str, list[float]] = {}
    alvos = [c for c in (*COMPONENTES, "piano_total_share") if c in componentes.columns]
    passos = [i / n_quantis for i in range(1, n_quantis + 1)]

    for nome in alvos:
        serie = componentes[nome].drop_nulls()
        if serie.len() == 0:
            continue
        quantis[nome] = [float(serie.quantile(q) or 0.0) for q in passos]

    return {
        "versao": 1,
        "n_jogador_partidas": int(componentes.height),
        "quantis": quantis,
    }
