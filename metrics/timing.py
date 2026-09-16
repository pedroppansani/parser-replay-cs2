"""
Detecção do tickrate do demo — medido, não assumido.

POR QUE ESTE MÓDULO EXISTE (bug real, encontrado tarde):
O projeto assumia 128 ticks por segundo, que é o default do awpy e o que se
espera de um servidor FACEIT. Mas o demo do CS2 é gravado a 64, e nada no
arquivo avisa isso — o header não traz o campo. O resultado é que TODO tempo
derivado saía pela metade: rounds de 60s apareciam como 30s, a janela de trade
de 5s valia 10s de jogo, a janela de contato do crosshair valia o dobro, e a
reprodução do replay rodava em velocidade 2×.

O erro só apareceu porque alguém perguntou "esses rounds não são curtos demais
pra dar tempo de ir até o bombsite e plantar?". A resposta estava no dado.

COMO A DETECÇÃO FUNCIONA — duas âncoras físicas independentes:

1. TIMER DA BOMBA (preferida). No CS2 a bomba explode 40 segundos depois do
   plant (mp_c4timer 40). Se existe um round que terminou em explosão, o
   intervalo plant → fim em ticks dividido por 40 É o tickrate, sem chute.
   Nesta partida: 2624 ticks / 40s = 65,6 → 64.

2. VELOCIDADE MÁXIMA (fallback). A maior velocidade possível no CS2 é ~250 u/s
   (correndo com faca). Medimos o percentil 99,5 do deslocamento por tick de
   todos os jogadores vivos e escolhemos o tickrate que coloca esse valor perto
   do limite real. A 64 tick esta partida dá 256 u/s — bate. A 128 daria 512,
   que é impossível.

Se as duas âncoras discordarem, o módulo devolve a do timer da bomba e registra
o conflito, porque ela é uma constante exata do jogo e a outra é estatística.
"""
from __future__ import annotations

import numpy as np
import polars as pl

# Tickrates plausíveis de um demo de CS2.
CANDIDATES = (64, 128)

# Constantes físicas do jogo usadas como gabarito.
C4_TIMER_SECONDS = 40.0
MAX_PLAYER_SPEED = 250.0  # correndo com faca; qualquer arma é mais lento

DEFAULT_TICKRATE = 64


def _from_bomb_timer(rounds: pl.DataFrame) -> tuple[int | None, str]:
    """Tickrate a partir do intervalo plant → explosão (40s no CS2)."""
    exploded = rounds.filter(
        (pl.col("reason") == "bomb_exploded") & pl.col("bomb_plant").is_not_null()
    )
    if exploded.height == 0:
        return None, "nenhum round terminou em explosão"

    spans = (exploded["end"] - exploded["bomb_plant"]).to_numpy()
    implied = float(np.median(spans)) / C4_TIMER_SECONDS
    best = min(CANDIDATES, key=lambda c: abs(c - implied))
    detail = (
        f"plant→explosão de {int(np.median(spans))} ticks / {C4_TIMER_SECONDS:.0f}s "
        f"= {implied:.1f} ticks/s"
    )
    # só aceita se ficou razoavelmente perto de um candidato
    if abs(best - implied) / best > 0.12:
        return None, detail + " (longe demais de 64 ou 128)"
    return best, detail


def _from_player_speed(ticks: pl.DataFrame) -> tuple[int | None, str]:
    """Tickrate a partir da velocidade máxima observada (~250 u/s no CS2)."""
    needed = {"X", "Y", "tick", "steamid", "round_num", "is_alive"}
    if not needed.issubset(set(ticks.columns)):
        return None, "colunas de posição ausentes"

    g = (
        ticks.sort(["steamid", "round_num", "tick"])
        .with_columns(
            pl.col("X").diff().over(["steamid", "round_num"]).alias("dx"),
            pl.col("Y").diff().over(["steamid", "round_num"]).alias("dy"),
            pl.col("tick").diff().over(["steamid", "round_num"]).alias("dt"),
        )
        .filter((pl.col("dt") == 1) & pl.col("dx").is_not_null() & pl.col("is_alive"))
    )
    if g.height == 0:
        return None, "sem amostras consecutivas"

    per_tick = np.sqrt(g["dx"].to_numpy() ** 2 + g["dy"].to_numpy() ** 2)
    p995 = float(np.percentile(per_tick, 99.5))
    if p995 <= 0:
        return None, "deslocamento nulo"

    best = min(CANDIDATES, key=lambda c: abs(p995 * c - MAX_PLAYER_SPEED))
    return best, f"p99,5 do deslocamento = {p995 * best:.0f} u/s a {best} tick (limite real ~{MAX_PLAYER_SPEED:.0f})"


def detect_tickrate(rounds: pl.DataFrame, ticks: pl.DataFrame | None = None) -> dict:
    """Descobre o tickrate do demo e devolve o valor com a evidência.

    Retorna {"tickrate", "source", "detail", "agreement"} — a evidência vai junto
    de propósito: um número desses, escolhido em silêncio, foi exatamente o que
    produziu o bug que este módulo existe para evitar.
    """
    bomb_rate, bomb_detail = _from_bomb_timer(rounds)
    speed_rate, speed_detail = (None, "não avaliado")
    if ticks is not None:
        speed_rate, speed_detail = _from_player_speed(ticks)

    if bomb_rate is not None:
        return {
            "tickrate": bomb_rate,
            "source": "timer da bomba",
            "detail": bomb_detail,
            "agreement": None if speed_rate is None else (speed_rate == bomb_rate),
            "speed_detail": speed_detail,
        }
    if speed_rate is not None:
        return {
            "tickrate": speed_rate,
            "source": "velocidade máxima dos jogadores",
            "detail": speed_detail,
            "agreement": None,
            "speed_detail": speed_detail,
        }
    return {
        "tickrate": DEFAULT_TICKRATE,
        "source": "default (nenhuma âncora disponível)",
        "detail": bomb_detail,
        "agreement": None,
        "speed_detail": speed_detail,
    }
