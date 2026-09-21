"""
Âncora e lurk medidos por área do mapa, não por distância.

A versão anterior media as duas coisas por proxy, e as duas estavam erradas na
definição:

- "Segura atrás" era contato tardio. Mas contato tardio é consequência de
  qualquer coisa que faça o round demorar; não diz que o jogador ficou FIXO num
  bombsite. Um CT que rotaciona duas vezes e chega atrasado na briga tinha o
  mesmo número de um âncora.
- "Joga afastado" era distância média do time. Mas dois CTs parados em bombsites
  opostos estão à mesma distância um do outro que um lurker do resto do time --
  e são coisas opostas.

A definição de jogo que estas métricas implementam (é a do Pedro):

  Âncora é o CT que fica sempre no mesmo bombsite, **mesmo quando a leitura do
  round aponta pro outro lado**. Na Dust2, é quem fica dentro do B mesmo com os
  T indicando A. O que define não é ficar parado: é não rotacionar.

  Lurker é o T que está em outra parte do mapa enquanto o time executa. Time
  indo pro A, ele tentando infiltrar o meio ou o B. O que define é a separação
  DE ÁREA em relação ao time, não a distância em unidades.

Por isso as duas dependem de `metrics/map_areas.py`, que agrupa os callouts do
demo em A / Mid / B.

Convenção do projeto: cada métrica devolve (per_round, summary). O round a round
vem primeiro porque é nele que a validação manual acontece -- um `hold_share` de
0,8 não diz nada sobre QUAIS rounds o jogador rotacionou.
"""
from __future__ import annotations

import polars as pl

from metrics.map_areas import AREA_A, AREA_B, AREA_SPAWN

# Fração mínima do tempo vivo numa área para ela contar como a área do jogador
# naquele round. Abaixo disso o jogador passou o round em trânsito e o round não
# entra no denominador -- forçar uma área em cima de quem só atravessou o mapa
# inventaria rotação onde houve só passagem.
MIN_AREA_SHARE = 0.50

# Quanto do round o jogador precisa passar na área do OUTRO bombsite pra aquilo
# contar como rotação, e não como passagem. Medido: quando um CT aparece na área
# do outro site, o quartil de baixo dessas visitas fica em 15,6% do round -- são
# os corredores de ligação, que em alguns mapas ficam geometricamente do lado do
# site vizinho. Sem este piso, um âncora que fez 12 de 12 rounds dentro do B
# pontuava ZERO em "nunca saiu", porque o caminho do spawn até o B passa por
# callouts classificados como A.
MIN_OTHER_SITE_SHARE = 0.15


def player_round_area_shares(
    positions: pl.DataFrame, area_of_place: dict[str, str]
) -> pl.DataFrame:
    """Quanto do round cada jogador passou em CADA área, uma linha por área.

    A tabela longa (e não só a área dominante) existe porque as duas perguntas da
    âncora são diferentes: "onde ele passou a maior parte do round" e "ele chegou
    a pisar no outro bombsite". A segunda não dá pra responder a partir da
    primeira.

    `positions` são as amostras dos jogadores VIVOS (ver
    positioning.position_samples): o tempo depois da morte não diz onde o jogador
    escolheu jogar. Amostras de spawn saem fora (ver AREA_SPAWN).
    """
    com_area = positions.with_columns(
        pl.col("place").replace_strict(area_of_place, default=None).alias("area")
    ).filter(pl.col("area").is_not_null() & (pl.col("area") != AREA_SPAWN))

    if com_area.height == 0:
        return pl.DataFrame(
            schema={
                "round_num": pl.UInt32, "steamid": pl.UInt64, "name": pl.String,
                "side": pl.String, "area": pl.String, "samples": pl.UInt32,
                "n_samples": pl.UInt32, "share": pl.Float64,
            }
        )

    por_area = com_area.group_by(["round_num", "steamid", "name", "side", "area"], maintain_order=True).agg(
        pl.len().cast(pl.UInt32).alias("samples")
    )
    total = por_area.group_by(["round_num", "steamid"], maintain_order=True).agg(
        pl.col("samples").sum().cast(pl.UInt32).alias("n_samples")
    )

    return (
        por_area.join(total, on=["round_num", "steamid"], how="left")
        .with_columns((pl.col("samples") / pl.col("n_samples")).alias("share"))
        .sort(["round_num", "steamid", "share"], descending=[False, False, True])
    )


def player_round_areas(shares: pl.DataFrame) -> pl.DataFrame:
    """Área dominante de cada jogador em cada round, com a fração do tempo nela."""
    if shares.height == 0:
        return pl.DataFrame(
            schema={
                "round_num": pl.UInt32, "steamid": pl.UInt64, "name": pl.String,
                "side": pl.String, "area": pl.String, "area_share": pl.Float64,
                "n_samples": pl.UInt32,
            }
        )
    return (
        # empate resolvido pelo nome da área só pra ser determinístico; o caso é
        # raro e o filtro de MIN_AREA_SHARE derruba quase todo empate mesmo
        shares.sort(["samples", "area"], descending=[True, False])
        .group_by(["round_num", "steamid"], maintain_order=True)
        .first()
        .select(["round_num", "steamid", "name", "side", "area",
                 pl.col("share").alias("area_share"), "n_samples"])
        .sort(["round_num", "steamid"])
    )


def _area_majoritaria(areas: pl.DataFrame, chaves: list[str]) -> pl.DataFrame:
    """Área onde estava a MAIORIA do grupo, por round.

    Empate devolve null de propósito: um time dividido 2-2 entre A e B não tem
    "a área do time", e chutar uma delas faria o parceiro do lurker parecer
    lurker também.
    """
    contagem = areas.group_by([*chaves, "area"], maintain_order=True).agg(pl.len().alias("n"))
    ranked = contagem.with_columns(
        pl.col("n").rank("dense", descending=True).over(chaves).alias("rk"),
        pl.len().over([*chaves, "n"]).alias("empatados"),
    ).filter(pl.col("rk") == 1)

    return ranked.with_columns(
        pl.when(pl.col("empatados") > 1).then(None).otherwise(pl.col("area")).alias("group_area")
    ).select([*chaves, "group_area"]).unique(subset=chaves, maintain_order=True, keep="first")


def anchor_metrics(
    shares: pl.DataFrame,
    min_area_share: float = MIN_AREA_SHARE,
    min_other_site_share: float = MIN_OTHER_SITE_SHARE,
) -> tuple[pl.DataFrame, pl.DataFrame]:
    """Quanto cada CT fica fixo no seu bombsite, e se ele fica mesmo contra a leitura.

    Devolve (per_round, summary). São TRÊS números, porque medem coisas diferentes
    e nenhum sozinho descreve a função:

    `hold_share` -- fração dos rounds de CT em que a área dominante do jogador foi
    a área de casa dele. Mede fixação, e satura: em nível profissional quase todo
    CT passa a maior parte do round no site que lhe cabe, então a mediana entre os
    líderes de time é 1,00 e o número quase não separa ninguém.

    `never_left_share` -- fração dos rounds de CT em que o jogador não rotacionou
    pro outro bombsite. É o mais próximo de "sempre fixo num bomb". Duas coisas
    tiveram que ser resolvidas pra este número querer dizer o que parece:
    o spawn saiu da conta (o CTSpawn da Ancient fica do lado do A, então todo CT
    "pisava no A" em todo round), e visitas curtas ao outro lado não contam como
    rotação (ver MIN_OTHER_SITE_SHARE) -- sem isso, um jogador com 12 de 12
    rounds dentro do B pontuava zero por causa do corredor de ligação. É null,
    não 1,0, para quem joga o meio: sem bombsite de casa não há o que ancorar.

    `no_rotate_share` -- fração dos rounds em que ficou em casa CONTANDO SÓ os
    rounds em que os T foram majoritariamente pro outro site. Conceitualmente é a
    melhor das três: é exatamente a situação em que âncora e rotador se comportam
    diferente. Na prática o denominador é pequeno (1 a 7 rounds por jogador numa
    partida), então ele anda junto na saída (`n_rounds_pressao_outro_lado`) pra
    dar pra ver quando o número não vale nada.
    """
    dominantes = player_round_areas(shares)
    firmes = dominantes.filter(pl.col("area_share") >= min_area_share)
    cts = firmes.filter(pl.col("side") == "ct")
    ts = firmes.filter(pl.col("side") == "t")

    if cts.height == 0:
        vazio = pl.DataFrame(schema={"steamid": pl.UInt64, "name": pl.String})
        return vazio, vazio

    # Área de casa: onde o jogador jogou mais rounds de CT. É derivada do próprio
    # jogador e não de uma tabela de posições "certas" por mapa -- quem ancora o
    # B de um time pode ancorar o A de outro.
    casa = (
        cts.group_by(["steamid", "area"], maintain_order=True)
        .agg(pl.len().alias("rounds_na_area"))
        .sort(["rounds_na_area", "area"], descending=[True, False])
        .group_by("steamid", maintain_order=True)
        .first()
        .select(["steamid", pl.col("area").alias("home_area")])
    )

    # Para onde os T foram no round: é a "leitura" contra a qual o CT resiste.
    area_dos_t = _area_majoritaria(ts, ["round_num"]).rename({"group_area": "enemy_area"})

    # Rotacionou pro outro bombsite? Vem da tabela longa, não da área dominante:
    # um âncora que sai e volta pode terminar o round com o site dele como área
    # dominante e ainda assim ter rotacionado. O piso de permanência
    # (MIN_OTHER_SITE_SHARE) é o que separa rotação de passagem.
    outro_site = (
        shares.join(casa, on="steamid", how="inner")
        .filter(
            pl.col("home_area").is_in([AREA_A, AREA_B])
            & pl.col("area").is_in([AREA_A, AREA_B])
            & (pl.col("area") != pl.col("home_area"))
            & (pl.col("share") >= min_other_site_share)
        )
        .select(["round_num", "steamid"])
        .unique(maintain_order=True)
        .with_columns(pl.lit(True).alias("rotacionou"))
    )

    per_round = (
        cts.join(casa, on="steamid", how="left")
        .join(area_dos_t, on="round_num", how="left")
        .join(outro_site, on=["round_num", "steamid"], how="left")
        .with_columns(pl.col("rotacionou").fill_null(False))
        .with_columns(
            (pl.col("area") == pl.col("home_area")).alias("held_home"),
            # Só conta como "leitura pro outro lado" quando os T se comprometeram
            # com um SITE. Time agrupado no meio não indicou nada ainda -- é a
            # fase em que o round pode virar pra qualquer lado, e ficar em casa
            # ali não é resistir a leitura nenhuma. Round de maioria no Mid sai
            # do denominador em vez de virar crédito de graça pro âncora.
            (
                pl.col("enemy_area").is_in([AREA_A, AREA_B])
                & (pl.col("enemy_area") != pl.col("home_area"))
            ).alias("pressao_outro_lado"),
        )
        .select(["round_num", "steamid", "name", "area", "home_area", "enemy_area",
                 "held_home", "rotacionou", "pressao_outro_lado", "area_share"])
        .sort(["steamid", "round_num"])
    )

    summary = (
        per_round.group_by(["steamid", "name"], maintain_order=True)
        .agg(
            pl.col("home_area").first(),
            pl.len().alias("n_rounds_ct"),
            pl.col("held_home").mean().alias("hold_share"),
            # Null, e não 1,0, para quem joga o meio: quem não tem bombsite de
            # casa não é âncora de bombsite nenhum, e "nunca saiu do site dele"
            # não é uma frase verdadeira sobre ele -- é uma divisão por zero
            # disfarçada. Com 1,0 ele lideraria o time na métrica sem nunca ter
            # ancorado nada.
            pl.when(pl.col("home_area").first().is_in([AREA_A, AREA_B]))
            .then((~pl.col("rotacionou")).mean())
            .otherwise(None)
            .alias("never_left_share"),
            pl.col("pressao_outro_lado").sum().alias("n_rounds_pressao_outro_lado"),
            pl.col("held_home")
            .filter(pl.col("pressao_outro_lado"))
            .mean()
            .alias("no_rotate_share"),
        )
        .sort("never_left_share", descending=True)
    )

    return per_round, summary


def lurk_metrics(
    shares: pl.DataFrame,
    min_area_share: float = MIN_AREA_SHARE,
) -> tuple[pl.DataFrame, pl.DataFrame]:
    """Quanto cada T joga numa área diferente da do resto do time.

    Devolve (per_round, summary).

    A comparação é com o RESTO do time, não com o time inteiro: incluir o próprio
    jogador na maioria faz o lurker puxar a maioria pra si em rounds de time
    dividido, e a métrica se esconde.
    """
    dominantes = player_round_areas(shares)
    ts = dominantes.filter((pl.col("side") == "t") & (pl.col("area_share") >= min_area_share))
    if ts.height == 0:
        vazio = pl.DataFrame(schema={"steamid": pl.UInt64, "name": pl.String})
        return vazio, vazio

    # Cross join do round com ele mesmo pra, para cada jogador, olhar só os
    # companheiros. É barato: são 5 jogadores por round.
    companheiros = ts.select(["round_num", "steamid", "area"]).join(
        ts.select(["round_num", pl.col("steamid").alias("outro"), pl.col("area").alias("area_outro")]),
        on="round_num",
        how="inner",
    ).filter(pl.col("steamid") != pl.col("outro"))

    area_do_resto = (
        _area_majoritaria(
            companheiros.select(["round_num", "steamid", pl.col("area_outro").alias("area")]),
            ["round_num", "steamid"],
        )
        .rename({"group_area": "team_area"})
    )

    per_round = (
        ts.join(area_do_resto, on=["round_num", "steamid"], how="left")
        .with_columns(
            pl.when(pl.col("team_area").is_null())
            .then(None)
            .otherwise(pl.col("area") != pl.col("team_area"))
            .alias("off_team")
        )
        .select(["round_num", "steamid", "name", "area", "team_area", "off_team", "area_share"])
        .sort(["steamid", "round_num"])
    )

    summary = (
        per_round.group_by(["steamid", "name"], maintain_order=True)
        .agg(
            pl.len().alias("n_rounds_t"),
            pl.col("off_team").is_not_null().sum().alias("n_rounds_time_definido"),
            pl.col("off_team").mean().alias("off_team_share"),
        )
        .sort("off_team_share", descending=True)
    )

    return per_round, summary
