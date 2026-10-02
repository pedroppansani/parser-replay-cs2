"""Rating: `rounds` é o que o jogador JOGOU, não o total da partida.

Antes, todos recebiam o total, a marca de amostra fraca da página nunca
acendia, e os subcomponentes por round de quem entrou no meio eram divididos
por rounds que ele não jogou. A partida é a match_01 real com um jogador
retirado dos sete primeiros rounds (pulado sem `data/interim/`).
"""
from __future__ import annotations

import polars as pl
import pytest

from metrics.rating import carrega_referencia, rating
from tests.test_rating import INTERIM, PROCESSED, TICKRATE, _contexto

PARTIDA = "match_01"
ENTRA_NO_ROUND = 8


@pytest.fixture(scope="module")
def cenario():
    if not (INTERIM / PARTIDA / "kills.parquet").exists():
        pytest.skip("sem o interim da match_01")
    tabelas, team_of, vencedor, kast = _contexto(PARTIDA)
    sid = int(tabelas["ticks"]["steamid"].drop_nulls()[0])
    fora = (pl.col("steamid") == sid) & (pl.col("round_num") < ENTRA_NO_ROUND)
    tabelas = {**tabelas, "ticks": tabelas["ticks"].filter(~fora)}
    return tabelas, team_of, vencedor, kast, sid


def test_rounds_e_o_que_o_jogador_jogou(cenario):
    tabelas, team_of, vencedor, kast, sid = cenario
    total = tabelas["rounds"].height
    _, resumo = rating(tabelas, team_of, vencedor, kast, TICKRATE, referencia=carrega_referencia())
    por = {int(j["steamid"]): j for j in resumo["jogadores"]}
    assert por[sid]["rounds"] == total - (ENTRA_NO_ROUND - 1)
    assert all(j["rounds"] == total for s, j in por.items() if s != sid)
    # os subcomponentes por round usam os rounds que ELE jogou
    j = por[sid]
    assert j["sub_kills"] == pytest.approx(j["kills_ponderadas"] / j["rounds"])
    assert j["sub_sobrevivencia"] == pytest.approx(1.0 - j["mortes"] / j["rounds"])
    assert j["rounds"] == (j.get("rounds_ct") or 0) + (j.get("rounds_t") or 0)


def test_quem_entra_no_round_8_recebe_a_marca_de_amostra_fraca(cenario):
    from scripts.build_insights import FRACAO_MINIMA_DE_ROUNDS, _rating_da_partida
    tabelas, team_of, vencedor, kast, sid = cenario
    rounds = tabelas["rounds"]
    assert rounds.height - (ENTRA_NO_ROUND - 1) < FRACAO_MINIMA_DE_ROUNDS * rounds.height
    _, por_jogador = _rating_da_partida(tabelas, INTERIM / PARTIDA, rounds, team_of, vencedor, kast, TICKRATE)
    assert por_jogador[sid]["rating_amostra_fraca"] is True
    assert not any(v["rating_amostra_fraca"] for s, v in por_jogador.items() if s != sid)
