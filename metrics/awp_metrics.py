"""
Métricas de uso de AWP (Fase 2) -- primeira das métricas autorais.

A ideia aqui NÃO é medir "quem acerta mais AWP" (isso é só kill count com arma
filtrada). É descrever COMO a AWP foi jogada, em termos que fazem sentido pra
quem joga em nível competitivo:

  - Quanto o AWPer converte a primeira briga do round (o "pick"), que é a
    função principal da arma: abrir o round com vantagem numérica.
  - Quanto tempo ele leva pra tomar o primeiro contato (AWP que demora 40s pra
    aparecer joga um papel diferente de AWP que busca pick nos primeiros 15s).
  - Se ele buscou a briga (peek) ou deixou a briga vir até ele (hold).

IMPORTANTE -- peek e hold NÃO são certo e errado. São estilos válidos e
situacionais: hold é o padrão de CT segurando um ângulo longo, peek é o padrão
de quem precisa abrir espaço ou pegar informação. A métrica reporta a
distribuição, não uma nota. Qualquer leitura de "qual é melhor" depende do
contexto do round (lado, economia, mapa) e é justamente o tipo de julgamento que
eu (Pedro) faço revisando, não o que o código decide.

Todos os limiares abaixo são constantes justamente pra eu poder recalibrar
depois de comparar com demos que eu conheço.

CORREÇÃO REGISTRADA (leia antes de confiar em versões antigas deste arquivo):
Uma versão anterior deste módulo afirmava que a flag `is_scoped` do demo era
não confiável, alegando que 40% dos ticks "scopados" mostravam velocidade acima
de 150 u/s -- impossível para AWP scopada. Aquilo estava ERRADO, e o erro era
meu: o projeto assumia 128 ticks por segundo e o demo é 64, então toda
velocidade calculada saía com o dobro do valor real.

Com o tickrate correto, medido nesta partida:
    AWP sem scope   mediana 104 u/s, p90 200 u/s  (máximo real da arma: ~200)
    AWP scopada     mediana  29 u/s, p90 100 u/s  (só 9,7% passam de 100)
Ou seja, a flag é coerente com a física do jogo e o "achado" não existia. Fica
registrado aqui porque um número que ninguém questiona vira fato: a lição é que
uma anomalia física grande é, quase sempre, erro de calibração do observador
antes de ser defeito do dado.

A classificação peek/hold continua baseada em POSIÇÃO medida, que é o sinal mais
direto de deslocamento; `scoped_fraction` fica no output como informação
complementar, agora sem ressalva.
"""
from __future__ import annotations

import numpy as np
import polars as pl

from metrics.geometry import horizontal_distance

# Janela de análise antes do primeiro tiro de AWP do round. 3s é o suficiente pra
# capturar o movimento que levou à briga (um peek típico de AWP é sair, atirar e
# voltar em menos de 2s) sem pegar o reposicionamento do início do round.
PRE_ENGAGEMENT_WINDOW_SECONDS = 3.0

# Deslocamento líquido (unidades do Source) na janela pré-briga.
# Referência de escala: um jogador correndo com AWP na mão faz ~200 u/s, andando
# de shift ~half disso. Então:
#   < 120u em 3s  = praticamente parado -> segurando ângulo (hold)
#   > 250u em 3s  = claramente se deslocou pra briga -> peek agressivo
#   entre os dois = reposicionamento / peek curto, fica como "intermediário"
#                   (não força classificação binária onde a evidência é ambígua)
HOLD_MAX_DISPLACEMENT = 120.0
PEEK_MIN_DISPLACEMENT = 250.0

# Tempo depois do tiro pra considerar que o resultado (kill ou morte) pertence
# àquela briga. 2s cobre o tempo de um segundo tiro / troca de refle sem
# capturar uma briga totalmente diferente mais tarde no round.
ENGAGEMENT_RESOLUTION_SECONDS = 2.0

# Velocidade (u/s) abaixo da qual considero que o jogador estava efetivamente
# parado/esperando. Recalibrado depois da correção de tickrate: com 64 tick, a
# AWP scopada tem mediana de 29 u/s e a sem scope 104 u/s, então 70 separa os
# dois estados com folga dos dois lados.
SLOW_SPEED_THRESHOLD = 70.0

AWP_WEAPON_TICKS = "AWP"  # nome na coluna active_weapon_name dos ticks
AWP_WEAPON_SHOTS = "weapon_awp"  # nome na coluna weapon da tabela de tiros
AWP_WEAPON_KILLS = "awp"  # nome na coluna weapon da tabela de kills


def awp_rounds(ticks: pl.DataFrame) -> pl.DataFrame:
    """Uma linha por (round_num, steamid) pra quem teve a AWP NA MÃO no round.

    Uso "arma ativa em algum tick" em vez de "comprou AWP" porque o que interessa
    é o jogador ter efetivamente jogado o round com a AWP -- quem comprou e nunca
    sacou (ou dropou pro colega) não estava jogando de AWPer naquele round.
    """
    return (
        ticks.filter(pl.col("active_weapon_name") == AWP_WEAPON_TICKS)
        .group_by(["round_num", "steamid"], maintain_order=True)
        .agg(
            pl.col("name").first(),
            pl.col("side").first(),
            pl.col("tick").min().alias("first_awp_hold_tick"),
            pl.len().alias("ticks_with_awp"),
        )
        .sort(["round_num", "steamid"])
    )


def first_awp_engagements(
    shots: pl.DataFrame,
    rounds: pl.DataFrame,
    tickrate: int = 64,
) -> pl.DataFrame:
    """Primeiro tiro de AWP de cada jogador em cada round, com o tempo desde o
    fim do freeze time (ou seja, desde que o round "abriu" de verdade).
    """
    first_shots = (
        shots.filter(pl.col("weapon") == AWP_WEAPON_SHOTS)
        .sort("tick")
        .group_by(["round_num", "player_steamid"], maintain_order=True)
        .agg(
            pl.col("player_name").first().alias("name"),
            pl.col("tick").first().alias("engagement_tick"),
            pl.col("player_X").first().alias("shot_X"),
            pl.col("player_Y").first().alias("shot_Y"),
            pl.col("player_Z").first().alias("shot_Z"),
            pl.col("player_place").first().alias("shot_place"),
            pl.col("player_is_scoped").first().alias("scoped_at_shot"),
            pl.col("player_side").first().alias("side"),
        )
        .rename({"player_steamid": "steamid"})
    )

    return (
        first_shots.join(rounds.select(["round_num", "freeze_end"]), on="round_num", how="left")
        .with_columns(
            ((pl.col("engagement_tick") - pl.col("freeze_end")) / tickrate).alias("time_to_first_shot_s")
        )
        .sort(["round_num", "steamid"])
    )


def classify_engagement_style(
    engagements: pl.DataFrame,
    ticks: pl.DataFrame,
    window_seconds: float = PRE_ENGAGEMENT_WINDOW_SECONDS,
    tickrate: int = 64,
) -> pl.DataFrame:
    """Classifica cada primeira briga de AWP como hold / peek / intermediário.

    Olha a janela de `window_seconds` ANTES do tiro e mede:
      - deslocamento líquido: distância entre onde o jogador estava no início da
        janela e onde ele estava no tiro. Uso deslocamento LÍQUIDO (não distância
        percorrida) de propósito: quem faz jiggle peek e volta pro mesmo lugar
        está jogando um ângulo, não avançando espaço.
      - distância percorrida: soma dos deslocamentos tick a tick. Junto com o
        líquido, separa "andou e voltou" (percorrida alta, líquida baixa) de
        "ficou parado" (as duas baixas).
      - fração do tempo em velocidade baixa (`slow_fraction`): derivada de
        posição, é a versão confiável de "estava parado esperando a briga vir".
      - fração do tempo scopado: informação complementar (ver a correção
        registrada no topo do módulo).

    O resultado fica em colunas separadas (não só o rótulo final) pra eu poder
    auditar POR QUE cada briga foi classificada daquele jeito.
    """
    window_ticks = int(window_seconds * tickrate)
    rows = []

    for eng in engagements.iter_rows(named=True):
        window = ticks.filter(
            (pl.col("steamid") == eng["steamid"])
            & (pl.col("round_num") == eng["round_num"])
            & (pl.col("tick") >= eng["engagement_tick"] - window_ticks)
            & (pl.col("tick") <= eng["engagement_tick"])
        ).sort("tick")

        if window.height < 2:
            rows.append(
                {
                    "round_num": eng["round_num"],
                    "steamid": eng["steamid"],
                    "engagement_tick": eng["engagement_tick"],
                    "net_displacement": None,
                    "path_distance": None,
                    "slow_fraction": None,
                    "scoped_fraction": None,
                    "style": "indeterminado",
                }
            )
            continue

        xs = window["X"].to_numpy().astype(float)
        ys = window["Y"].to_numpy().astype(float)
        ticks_arr = window["tick"].to_numpy().astype(float)

        net = float(horizontal_distance(xs[0], ys[0], xs[-1], ys[-1]))
        step = np.sqrt(np.diff(xs) ** 2 + np.diff(ys) ** 2)
        path = float(np.sum(step))

        dt = np.diff(ticks_arr)
        speeds = np.divide(step, dt, out=np.zeros_like(step), where=dt > 0) * tickrate
        slow_fraction = float((speeds < SLOW_SPEED_THRESHOLD).mean()) if speeds.size else None

        scoped = window["is_scoped"].cast(pl.Float64).mean()
        scoped_fraction = float(scoped) if scoped is not None else None

        if net < HOLD_MAX_DISPLACEMENT:
            style = "hold"
        elif net > PEEK_MIN_DISPLACEMENT:
            style = "peek"
        else:
            style = "intermediario"

        rows.append(
            {
                "round_num": eng["round_num"],
                "steamid": eng["steamid"],
                "engagement_tick": eng["engagement_tick"],
                "net_displacement": round(net, 1),
                "path_distance": round(path, 1),
                "slow_fraction": round(slow_fraction, 3) if slow_fraction is not None else None,
                "scoped_fraction": round(scoped_fraction, 3) if scoped_fraction is not None else None,
                "style": style,
            }
        )

    styles = pl.DataFrame(
        rows,
        schema={
            "round_num": pl.UInt32,
            "steamid": pl.UInt64,
            "engagement_tick": pl.Int64,
            "net_displacement": pl.Float64,
            "path_distance": pl.Float64,
            "slow_fraction": pl.Float64,
            "scoped_fraction": pl.Float64,
            "style": pl.String,
        },
    )
    # A chave inclui o TICK da briga. REGRESSÃO: com só (round, jogador), o
    # repick -- que classifica TODAS as brigas, não só a primeira de AWP --
    # cruzava as k brigas de um jogador no round com os k estilos dele (k²
    # linhas; 916 em vez de 480 numa partida) e o repick_share saía ponderado
    # errado.
    return engagements.with_columns(pl.col("engagement_tick").cast(pl.Int64)).join(
        styles, on=["round_num", "steamid", "engagement_tick"], how="left")


def resolve_engagement_outcomes(
    engagements: pl.DataFrame,
    kills: pl.DataFrame,
    resolution_seconds: float = ENGAGEMENT_RESOLUTION_SECONDS,
    tickrate: int = 64,
) -> pl.DataFrame:
    """Diz se o AWPer ganhou ou perdeu a primeira briga dele no round.

    Regra:
      - ganhou (`won`): ele matou alguém com AWP dentro da janela de resolução
        depois do tiro, e não morreu antes disso;
      - perdeu (`lost`): ele morreu dentro da janela (o tiro dele não resolveu);
      - sem resolução (`no_trade`): errou o tiro mas ninguém morreu na janela --
        acontece bastante com AWP (tiro de informação, tiro pra segurar espaço).

    Separar "errou e morreu" de "errou e nada aconteceu" importa: o segundo caso
    muitas vezes é intencional (negar espaço), e jogar os dois no mesmo balde
    infla artificialmente a taxa de erro do AWPer.
    """
    window_ticks = int(resolution_seconds * tickrate)
    rows = []

    for eng in engagements.iter_rows(named=True):
        t0 = eng["engagement_tick"]
        t1 = t0 + window_ticks

        awp_kill = kills.filter(
            (pl.col("attacker_steamid") == eng["steamid"])
            & (pl.col("round_num") == eng["round_num"])
            & (pl.col("weapon") == AWP_WEAPON_KILLS)
            & (pl.col("tick") >= t0)
            & (pl.col("tick") <= t1)
        )
        own_death = kills.filter(
            (pl.col("victim_steamid") == eng["steamid"])
            & (pl.col("round_num") == eng["round_num"])
            & (pl.col("tick") >= t0)
            & (pl.col("tick") <= t1)
        )

        kill_tick = awp_kill["tick"].min() if awp_kill.height else None
        death_tick = own_death["tick"].min() if own_death.height else None

        if kill_tick is not None and (death_tick is None or kill_tick <= death_tick):
            outcome = "won"
        elif death_tick is not None:
            outcome = "lost"
        else:
            outcome = "no_trade"

        rows.append(
            {
                "round_num": eng["round_num"],
                "steamid": eng["steamid"],
                "outcome": outcome,
                "kills_in_engagement": awp_kill.height,
            }
        )

    outcomes = pl.DataFrame(
        rows,
        schema={
            "round_num": pl.UInt32,
            "steamid": pl.UInt64,
            "outcome": pl.String,
            "kills_in_engagement": pl.UInt32,
        },
    )
    return engagements.join(outcomes, on=["round_num", "steamid"], how="left")


def opening_kills_with_awp(kills: pl.DataFrame) -> pl.DataFrame:
    """Marca quais rounds tiveram o PRIMEIRO kill do round feito com AWP (o 'pick').

    O pick é a jogada que define o valor da AWP no round: abrir com vantagem
    numérica antes de qualquer troca. Um kill de AWP no meio do round vale, mas
    não é a mesma coisa.
    """
    # Só kill em inimigo abre o round: fogo amigo e morte sem atacante (bomba,
    # queda) antes do primeiro duelo não são pick de ninguém.
    first_kills = (
        kills.filter(
            pl.col("attacker_steamid").is_not_null()
            & (pl.col("attacker_side") != pl.col("victim_side"))
        )
        .sort("tick")
        .group_by("round_num", maintain_order=True)
        .agg(
            pl.col("attacker_steamid").first().alias("steamid"),
            pl.col("attacker_name").first().alias("name"),
            pl.col("weapon").first().alias("weapon"),
            pl.col("tick").first().alias("tick"),
        )
    )
    return first_kills.with_columns((pl.col("weapon") == AWP_WEAPON_KILLS).alias("opening_with_awp"))


def calculate_awp_metrics(
    tables: dict[str, pl.DataFrame], tickrate: int = 64
) -> tuple[pl.DataFrame, pl.DataFrame]:
    """Junta tudo: uma linha por (round, AWPer) com a briga daquele round, e um
    resumo agregado por jogador.
    """
    ticks, shots, kills, rounds = tables["ticks"], tables["shots"], tables["kills"], tables["rounds"]

    awp_r = awp_rounds(ticks)
    engagements = first_awp_engagements(shots, rounds, tickrate)
    engagements = classify_engagement_style(engagements, ticks, tickrate=tickrate)
    engagements = resolve_engagement_outcomes(engagements, kills, tickrate=tickrate)

    openings = opening_kills_with_awp(kills).filter(pl.col("opening_with_awp")).select(
        ["round_num", "steamid", "opening_with_awp"]
    )

    per_round = (
        awp_r.join(
            engagements.drop(["name", "side"]),
            on=["round_num", "steamid"],
            how="left",
        )
        .join(openings, on=["round_num", "steamid"], how="left")
        .with_columns(
            pl.col("opening_with_awp").fill_null(False),
            pl.col("outcome").fill_null("sem_briga"),  # teve AWP mas nunca atirou no round
        )
        .sort(["steamid", "round_num"])
    )

    summary = (
        per_round.group_by(["steamid", "name"], maintain_order=True)
        .agg(
            pl.len().alias("awp_rounds"),
            pl.col("engagement_tick").is_not_null().sum().alias("rounds_with_engagement"),
            (pl.col("outcome") == "won").sum().alias("engagements_won"),
            (pl.col("outcome") == "lost").sum().alias("engagements_lost"),
            (pl.col("outcome") == "no_trade").sum().alias("engagements_no_trade"),
            pl.col("opening_with_awp").sum().alias("opening_picks"),
            pl.col("time_to_first_shot_s").median().alias("median_time_to_first_shot_s"),
            (pl.col("style") == "hold").sum().alias("style_hold"),
            (pl.col("style") == "peek").sum().alias("style_peek"),
            (pl.col("style") == "intermediario").sum().alias("style_intermediate"),
        )
        .with_columns(
            # conversão = brigas ganhas / brigas que tiveram resolução (ganhou ou
            # perdeu). Tiro sem resolução fica de fora do denominador de propósito
            # -- ver docstring de resolve_engagement_outcomes.
            pl.when((pl.col("engagements_won") + pl.col("engagements_lost")) > 0)
            .then(
                100
                * pl.col("engagements_won")
                / (pl.col("engagements_won") + pl.col("engagements_lost"))
            )
            .otherwise(None)
            .alias("engagement_conversion_pct"),
            pl.when(pl.col("awp_rounds") > 0)
            .then(100 * pl.col("opening_picks") / pl.col("awp_rounds"))
            .otherwise(None)
            .alias("opening_pick_rate_pct"),
        )
        .sort("awp_rounds", descending=True)
    )

    return per_round, summary
