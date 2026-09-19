"""
Reconstrução da cegueira por flash quando a demo não traz o evento `player_blind`.

POR QUE EXISTE
--------------
As demos de campeonato (43 das 52 do corpus) NÃO gravam `player_blind`. Sem
ele, tudo o que depende de flash saía zerado sem aviso: o cegar do suporte, a
utility que antecede a jogada do carrega piano e o crédito de flash no Round
Swing. As de FACEIT gravam -- e é com elas que a reconstrução é validada
(`valida_contra_eventos`).

O QUE O DADO DIZ (medido, não suposto)
-------------------------------------
`flash_duration` nos ticks NÃO decresce durante a cegueira. No tick em que a
flash pega, ele recebe a duração TOTAL daquela cegueira e fica parado; volta a
zero quando a cegueira acaba. Se uma segunda flash pega o jogador ainda cego, o
valor TROCA para a nova duração sem passar por zero. Por isso o início de uma
cegueira é todo tick em que o valor muda para um número positivo -- não só a
transição de zero para positivo, que perderia a flash em quem já estava cego
(comum em execução). Em match_05: 93 eventos reais; 88 transições 0 -> positivo
+ 5 positivo -> outro positivo = 93.

A ATRIBUIÇÃO
------------
Casa o início da cegueira com a detonação de uma flash (`flashbang_detonate`,
que as demos de campeonato gravam). Janela curta, porque a cegueira começa no
mesmo tick da detonação. Com duas detonações candidatas próximas demais para
separar, a cegueira fica SEM DONO: flash mal atribuída é pior que flash sem dono
(o suporte ganharia crédito de flash que não jogou).
"""
from __future__ import annotations

import polars as pl

# Distância máxima, em ticks, entre a detonação e o início da cegueira para as
# duas serem a mesma flash. A cegueira começa no MESMO tick da detonação nos
# eventos reais; 2 ticks (31 ms a 64 tick) só absorvem arredondamento.
JANELA_CASAMENTO_TICKS = 2

# Duas detonações candidatas cuja distância ao início da cegueira difere menos
# que isto são indistinguíveis pelo tempo: a cegueira fica sem dono.
LIMIAR_AMBIGUIDADE_TICKS = 1

COLUNAS = [
    "round_num", "tick", "entityid",
    "attacker_steamid", "attacker_name", "attacker_side",
    "user_steamid", "user_name", "user_side",
    "blind_duration", "origem", "atribuicao",
]


def inicios_de_cegueira(ticks: pl.DataFrame) -> pl.DataFrame:
    """Um registro por cegueira: quem, quando e por quanto tempo."""
    t = ticks.select(["round_num", "tick", "steamid", "name", "side", "flash_duration"]).sort(["steamid", "tick"])
    anterior = pl.col("flash_duration").shift(1).over("steamid").fill_null(0.0)
    return (
        t.filter((pl.col("flash_duration") > 0) & (pl.col("flash_duration") != anterior))
        .select(
            pl.col("round_num"),
            pl.col("tick"),
            pl.col("steamid").alias("user_steamid"),
            pl.col("name").alias("user_name"),
            pl.col("side").alias("user_side"),
            pl.col("flash_duration").cast(pl.Float32).alias("blind_duration"),
        )
    )


def reconstroi(ticks: pl.DataFrame, detonacoes: pl.DataFrame | None) -> pl.DataFrame:
    """Tabela no formato de `player_blind`, reconstruída dos ticks.

    `atribuicao`: "unica" (uma detonação candidata, ou a mais próxima com folga),
    "ambigua" (duas candidatas indistinguíveis -- sem dono) ou "sem_detonacao"
    (nenhuma flash detonou na janela -- sem dono).
    """
    inicios = inicios_de_cegueira(ticks)
    if inicios.height == 0:
        return pl.DataFrame(schema={c: pl.Utf8 for c in COLUNAS}).head(0)

    if detonacoes is None or detonacoes.height == 0:
        det = pl.DataFrame(schema={"tick_det": pl.Int32, "entityid": pl.Int32, "attacker_steamid": pl.UInt64,
                                   "attacker_name": pl.Utf8, "attacker_side": pl.Utf8})
    else:
        det = detonacoes.select(
            pl.col("tick").alias("tick_det"),
            pl.col("entityid"),
            pl.col("user_steamid").alias("attacker_steamid"),
            pl.col("user_name").alias("attacker_name"),
            pl.col("user_side").alias("attacker_side"),
        )

    pares = (
        inicios.with_row_index("cegueira")
        .join(det, how="cross")
        .with_columns((pl.col("tick") - pl.col("tick_det")).abs().alias("dist"))
        .filter(pl.col("dist") <= JANELA_CASAMENTO_TICKS)
        .sort(["cegueira", "dist"])
    )
    melhor = pares.group_by("cegueira", maintain_order=True).agg(
        pl.col("entityid").first(),
        pl.col("attacker_steamid").first(),
        pl.col("attacker_name").first(),
        pl.col("attacker_side").first(),
        pl.col("dist").first().alias("d1"),
        pl.col("dist").slice(1, 1).first().alias("d2"),
    )
    base = inicios.with_row_index("cegueira").join(melhor, on="cegueira", how="left")
    ambigua = pl.col("d2").is_not_null() & ((pl.col("d2") - pl.col("d1")) < LIMIAR_AMBIGUIDADE_TICKS)
    atribuicao = (
        pl.when(pl.col("d1").is_null()).then(pl.lit("sem_detonacao"))
        .when(ambigua).then(pl.lit("ambigua"))
        .otherwise(pl.lit("unica"))
    )
    sem_dono = pl.col("atribuicao") != "unica"
    return (
        base.with_columns(atribuicao.alias("atribuicao"))
        .with_columns(
            pl.when(sem_dono).then(None).otherwise(pl.col(c)).alias(c)
            for c in ("entityid", "attacker_steamid", "attacker_name", "attacker_side")
        )
        .with_columns(pl.lit("reconstruida").alias("origem"))
        .select(COLUNAS)
        .sort("tick")
    )


def valida_contra_eventos(reconstruida: pl.DataFrame, real: pl.DataFrame) -> dict:
    """Compara a reconstrução com o evento real numa demo que tem os dois.

    Casamento por (cegado, tick) com a mesma janela da atribuição. Mede: quantas
    cegueiras reais foram achadas, quantas com o arremessador certo, quantas com
    o errado, quantas ficaram sem dono, e as reconstruídas que não existem.
    """
    r = real.select(
        pl.col("user_steamid"), pl.col("tick").alias("tick_real"),
        pl.col("attacker_steamid").alias("lancador_real"),
        pl.col("blind_duration").alias("dur_real"),
    ).with_row_index("id_real")
    c = reconstruida.select(
        pl.col("user_steamid"), pl.col("tick").alias("tick_rec"),
        pl.col("attacker_steamid").alias("lancador_rec"),
        pl.col("blind_duration").alias("dur_rec"),
    ).with_row_index("id_rec")
    # Pareia pela MENOR distância primeiro: o mesmo jogador cegado duas vezes
    # com 1 tick de diferença (duas flashes quase juntas) tem dois pares
    # possíveis, e parear pela ordem descartava um par válido.
    pares = (
        r.join(c, on="user_steamid")
        .with_columns((pl.col("tick_real") - pl.col("tick_rec")).abs().alias("dist"))
        .filter(pl.col("dist") <= JANELA_CASAMENTO_TICKS)
        .sort(["dist", "id_real", "id_rec"])
        .unique("id_real", keep="first", maintain_order=True)
        .unique("id_rec", keep="first", maintain_order=True)
    )
    achadas = pares.height
    certo = pares.filter(pl.col("lancador_rec") == pl.col("lancador_real")).height
    sem_dono = pares.filter(pl.col("lancador_rec").is_null()).height
    errado = achadas - certo - sem_dono
    dur_err = (pares["dur_rec"] - pares["dur_real"]).abs() if achadas else pl.Series([0.0])
    return {
        "reais": r.height,
        "reconstruidas": c.height,
        "achadas": achadas,
        "dono_certo": certo,
        "dono_errado": errado,
        "sem_dono": sem_dono,
        "inventadas": c.height - achadas,
        "erro_max_duracao_s": float(dur_err.max() or 0.0),
    }
