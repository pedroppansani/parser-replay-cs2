"""O Round Swing por jogador, em pontos percentuais POR ROUND, e a agregação entre partidas (RS1).

O número não é novo: é o sub-rating `round_swing` do rating (`metrics/rating.py`, decisões 22a/22f/22k) antes de virar razão centrada em 1,00. Aqui ele só é EXPOSTO, sem
mexer no modelo, na divisão do crédito nem no rating. Implementação própria da metodologia do Rating 3.0 da HLTV: o número pode diferir do deles.

Por que a soma e a soma dos quadrados vão junto no `insights.json`: a média entre partidas e o erro padrão do jogador saem de SOMAS (a razão das somas, como em
`metrics/agregado_jogadores.py`), nunca da média das médias, e o erro padrão exige a variância de UM round, que só as duas somas guardam.

  media = soma / n          erro padrão = raiz( (soma_quad - soma^2 / n) / (n - 1) / n )

O swing de um round ruim ou bom é grande (desvio de uns 20 p.p. por round, medido na RS0), então uma partida (~22 rounds) varia cerca de ±4 p.p. só por acaso:
o número de UMA partida conta o que aconteceu, não mede habilidade. Estável só com 100 rounds ou mais (decisão do Pedro, RS1).
"""
from __future__ import annotations

import math
from typing import Iterable

import polars as pl

# Abaixo disto o número não aparece: "poucos rounds". É o mesmo piso do rating (`MIN_ROUNDS_CONFIAVEL`).
MIN_ROUNDS_PARA_MOSTRAR = 30
# A partir disto o número é "estável" (a confiabilidade entre duas metades chega a ~0,6; medida na RS0).
ROUNDS_ESTAVEL = 100


def marcas(rounds: int) -> dict:
    """As duas marcas pelo número de rounds jogados."""
    return {"poucos_rounds": rounds < MIN_ROUNDS_PARA_MOSTRAR, "estavel": rounds >= ROUNDS_ESTAVEL}


def do_jogador(rounds: int, soma_pp: float, soma_quad_pp2: float) -> dict:
    """O bloco de um jogador a partir dos seus rounds, da soma do swing por round (p.p.) e da soma dos quadrados."""
    if rounds <= 0:
        return {"rounds": 0, "pp_por_round": None, "erro_padrao_pp": None, "soma_pp": 0.0, "soma_quad_pp2": 0.0, **marcas(0)}
    media = soma_pp / rounds
    if rounds > 1:
        variancia = max(0.0, (soma_quad_pp2 - soma_pp * soma_pp / rounds) / (rounds - 1))
        erro = math.sqrt(variancia / rounds)
    else:
        erro = None
    return {"rounds": int(rounds), "pp_por_round": round(media, 2), "erro_padrao_pp": None if erro is None else round(erro, 2),
            "soma_pp": round(soma_pp, 4), "soma_quad_pp2": round(soma_quad_pp2, 4), **marcas(rounds)}


def da_partida(per_round: pl.DataFrame, jogadores: Iterable[dict]) -> dict[int, dict]:
    """{steamid: bloco} de uma partida. `per_round`: o swing por (round, jogador) em fração (como sai de `rating()`); `jogadores`: o resumo do rating
    (com `rounds` JOGADOS por cada um: round sem evento do jogador conta zero, e entra no denominador)."""
    somas: dict[int, list[float]] = {}
    if per_round.height:
        for r in per_round.group_by("steamid", maintain_order=True).agg((100 * pl.col("swing")).sum().alias("soma"), ((100 * pl.col("swing")) ** 2).sum().alias("quad")).iter_rows(named=True):
            somas[int(r["steamid"])] = [float(r["soma"]), float(r["quad"])]
    saida = {}
    for j in jogadores:
        sid = int(j["steamid"])
        soma, quad = somas.get(sid, [0.0, 0.0])
        saida[sid] = do_jogador(int(j["rounds"]), soma, quad)
    return saida


def agrega(blocos: Iterable[tuple[int, dict]]) -> dict[int, dict]:
    """{steamid: bloco} entre partidas, somando rounds, soma e soma dos quadrados (a razão das somas)."""
    acc: dict[int, list[float]] = {}
    partidas: dict[int, int] = {}
    for sid, b in blocos:
        a = acc.setdefault(int(sid), [0, 0.0, 0.0])
        a[0] += int(b["rounds"]); a[1] += float(b["soma_pp"]); a[2] += float(b["soma_quad_pp2"])
        partidas[int(sid)] = partidas.get(int(sid), 0) + 1
    return {sid: {**do_jogador(int(a[0]), a[1], a[2]), "partidas": partidas[sid]} for sid, a in sorted(acc.items())}
