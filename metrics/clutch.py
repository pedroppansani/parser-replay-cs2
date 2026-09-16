"""
Situações de último vivo: as TENTATIVAS, não só as que deram certo.

Por que este módulo existe: `scripts/build_insights.py` já achava clutch, mas só
registrava quando o último vivo GANHAVA. Com isso não dá pra responder a pergunta
do "rei do NT" -- quem chega muito em situação de último vivo e quase nunca
converte -- porque o denominador (as tentativas) nunca foi calculado. Contar só
as vitórias é o mesmo erro de contar só os tiros que acertaram.

Uma situação começa no instante em que um time cai para um jogador vivo contra
dois ou mais. A partir dali o módulo mede o que o jogador fez com ela: quanto
dano tirou, quantas kills fez e se o round foi convertido.

Aviso de tamanho de amostra, registrado aqui porque é o que limita o uso: nas 9
partidas processadas são 19 clutches VENCIDOS em 187 rounds. Somando as
tentativas perdidas o número sobe, mas continua na casa de uma situação por
jogador por partida. Qualquer índice construído sobre isso precisa de um mínimo
de tentativas explícito -- ver MIN_CLUTCH_ATTEMPTS em metrics/archetypes.py.

Convenção do projeto: devolve (per_round, summary).
"""
from __future__ import annotations

import polars as pl

# Contra quantos inimigos, no mínimo, para a situação contar como clutch. 1v1 é
# um duelo, não um clutch: fica de fora porque quem "chega em 1v1" está só
# terminando um round equilibrado, e incluí-lo encheria a métrica de situações
# que não têm nada de heroico nem de fracasso.
MIN_ENEMIES_ALIVE = 2


def clutch_situations(
    kills: pl.DataFrame,
    rounds: pl.DataFrame,
    team_of: dict[int, str],
    winner_team_of_round: dict[int, str],
) -> tuple[pl.DataFrame, pl.DataFrame]:
    """Toda vez que alguém ficou por último contra 2+, tenha convertido ou não.

    `winner_team_of_round` mapeia round -> "A"/"B" já resolvido pelo lado, porque
    o vencedor vem do demo como lado (ct/t) e o lado troca no intervalo.

    per_round: uma linha por situação (round, jogador que ficou por último).
    summary: uma linha por jogador, com tentativas, conversões e o que ele
    produziu dentro das situações.
    """
    linhas = []

    for row in rounds.iter_rows(named=True):
        rn = int(row["round_num"])
        rk = kills.filter(pl.col("round_num") == rn).sort("tick")
        if rk.height == 0:
            continue

        vivos = {"A": 5, "B": 5}
        mortos: set[int] = set()
        ja_registrado: set[str] = set()

        for kill in rk.iter_rows(named=True):
            time_vitima = team_of.get(kill["victim_steamid"])
            if time_vitima is None:
                continue
            vivos[time_vitima] -= 1
            mortos.add(kill["victim_steamid"])

            for time, adversario in (("A", "B"), ("B", "A")):
                if time in ja_registrado:
                    continue
                if vivos[time] != 1 or vivos[adversario] < MIN_ENEMIES_ALIVE:
                    continue

                sobreviventes = [
                    sid for sid, t in team_of.items() if t == time and sid not in mortos
                ]
                if len(sobreviventes) != 1:
                    continue

                sid = sobreviventes[0]
                inicio = int(kill["tick"])

                # O que o jogador fez DEPOIS de ficar sozinho. O corte no tick da
                # situação é o que separa "segurou o round sozinho" de "já tinha
                # feito tudo antes de o time morrer".
                depois = rk.filter(pl.col("tick") > inicio)
                kills_dele = depois.filter(
                    (pl.col("attacker_steamid") == sid)
                    & (pl.col("victim_steamid").is_in(
                        [s for s, t in team_of.items() if t == adversario]
                    ))
                ).height

                linhas.append(
                    {
                        "round_num": rn,
                        "steamid": sid,
                        "team": time,
                        "enemies_alive": int(vivos[adversario]),
                        "start_tick": inicio,
                        "kills_in_clutch": int(kills_dele),
                        "won": winner_team_of_round.get(rn) == time,
                    }
                )
                ja_registrado.add(time)

    schema = {
        "round_num": pl.UInt32, "steamid": pl.UInt64, "team": pl.String,
        "enemies_alive": pl.Int32, "start_tick": pl.Int64,
        "kills_in_clutch": pl.Int32, "won": pl.Boolean,
    }
    per_round = pl.DataFrame(linhas, schema=schema) if linhas else pl.DataFrame(schema=schema)

    if per_round.height == 0:
        summary = pl.DataFrame(
            schema={
                "steamid": pl.UInt64, "clutch_attempts": pl.UInt32, "clutch_wins": pl.UInt32,
                "clutch_kills": pl.Int32, "clutch_conversion": pl.Float64,
            }
        )
        return per_round, summary

    summary = (
        per_round.group_by("steamid")
        .agg(
            pl.len().cast(pl.UInt32).alias("clutch_attempts"),
            pl.col("won").sum().cast(pl.UInt32).alias("clutch_wins"),
            pl.col("kills_in_clutch").sum().alias("clutch_kills"),
        )
        .with_columns(
            (pl.col("clutch_wins") / pl.col("clutch_attempts")).alias("clutch_conversion")
        )
        .sort("clutch_attempts", descending=True)
    )
    return per_round, summary


def add_damage_in_clutch(
    per_round: pl.DataFrame, damages: pl.DataFrame, team_of: dict[int, str]
) -> pl.DataFrame:
    """Soma o dano que o jogador causou a inimigos depois de ficar sozinho.

    Separado da função principal porque depende da tabela de damages, que nem
    todo chamador tem à mão -- e porque é ele que sustenta a leitura "tirou muito
    dano no clutch e mesmo assim não fechou", que é o retrato do rei do NT.
    """
    if per_round.height == 0:
        return per_round.with_columns(pl.lit(0, dtype=pl.Int64).alias("damage_in_clutch"))

    dano = (
        damages.join(
            per_round.select(["round_num", "steamid", "start_tick", "team"]),
            left_on=["round_num", "attacker_steamid"],
            right_on=["round_num", "steamid"],
            how="inner",
        )
        .filter(pl.col("tick") > pl.col("start_tick"))
        .with_columns(
            pl.col("victim_steamid")
            .map_elements(lambda s: team_of.get(s), return_dtype=pl.String)
            .alias("time_vitima")
        )
        .filter(pl.col("time_vitima") != pl.col("team"))
        .group_by(["round_num", "attacker_steamid"])
        .agg(pl.col("dmg_health_real").sum().alias("damage_in_clutch"))
        .rename({"attacker_steamid": "steamid"})
    )

    return per_round.join(dano, on=["round_num", "steamid"], how="left").with_columns(
        pl.col("damage_in_clutch").fill_null(0)
    )
