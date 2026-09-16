"""
Testes da partição do mapa em áreas e das métricas de âncora e lurk.

Mesma filosofia dos outros: mapa sintético pequeno, escrito à mão, com as
posições escolhidas pra cada caso ser óbvio de conferir a olho. O que se testa
aqui é "a lógica faz o que a definição de jogo diz", não "os números da partida
real fazem sentido" -- essa segunda pergunta é do Pedro.

Dois testes travam bugs que aconteceram de verdade nos dados reais e que, sem
eles, voltam silenciosamente:

- o CTSpawn da Ancient cai geometricamente do lado do A, então contar o spawn
  fazia TODO CT "ir pro A" em todo round;
- os corredores de ligação entre os dois lados também caem de um lado, então
  contar qualquer passagem como rotação zerava a métrica de um âncora que jogou
  12 de 12 rounds dentro do próprio bombsite.
"""
from __future__ import annotations

import polars as pl
import pytest

from metrics.map_areas import (
    AREA_A,
    AREA_B,
    AREA_MID,
    AREA_SPAWN,
    area_lookup,
    derive_place_areas,
)
from metrics.site_roles import (
    MIN_OTHER_SITE_SHARE,
    anchor_metrics,
    lurk_metrics,
    player_round_area_shares,
    player_round_areas,
)

# Mapa sintético: A em x=-1000, B em x=+1000, tudo no mesmo Y e Z. Os callouts
# ficam ao longo do eixo x, então a razão de distância é fácil de prever.
LUGARES = {
    "BombsiteA": -1000.0,
    "HallA": -700.0,
    "Middle": 0.0,
    "HallB": 700.0,
    "BombsiteB": 1000.0,
    "CTSpawn": -600.0,  # do lado do A de propósito, como na Ancient
}


def _positions(linhas: list[dict]) -> pl.DataFrame:
    """linhas: {round_num, steamid, name, side, place, ticks}"""
    registros = []
    for linha in linhas:
        for i in range(linha["ticks"]):
            registros.append(
                {
                    "round_num": linha["round_num"],
                    "tick": i,
                    "steamid": linha["steamid"],
                    "name": linha["name"],
                    "side": linha["side"],
                    "place": linha["place"],
                    "X": LUGARES[linha["place"]],
                    "Y": 0.0,
                    "Z": 0.0,
                }
            )
    return pl.DataFrame(registros).with_columns(
        pl.col("round_num").cast(pl.UInt32), pl.col("steamid").cast(pl.UInt64)
    )


def _bomb() -> pl.DataFrame:
    return pl.DataFrame(
        {
            "tick": [1, 2],
            "event": ["plant", "plant"],
            "X": [LUGARES["BombsiteA"], LUGARES["BombsiteB"]],
            "Y": [0.0, 0.0],
            "Z": [0.0, 0.0],
            "bombsite": ["BombsiteA", "BombsiteB"],
        }
    )


@pytest.fixture
def areas() -> dict[str, str]:
    pos = _positions(
        [{"round_num": 1, "steamid": 1, "name": "p", "side": "ct", "place": p, "ticks": 2}
         for p in LUGARES]
    )
    return area_lookup(derive_place_areas(pos, _bomb(), "de_teste"))


def test_callouts_vao_para_o_site_mais_proximo(areas):
    assert areas["BombsiteA"] == AREA_A
    assert areas["HallA"] == AREA_A
    assert areas["BombsiteB"] == AREA_B
    assert areas["HallB"] == AREA_B


def test_equidistante_vira_mid(areas):
    """Mid não é desenhado: é o que fica a distâncias parecidas dos dois sites."""
    assert areas["Middle"] == AREA_MID


def test_spawn_fica_fora_da_particao(areas):
    """REGRESSÃO: o CTSpawn da Ancient fica do lado do A.

    Sem esta regra, todo CT "passava pelo A" em todo round e a métrica de não
    rotacionar zerava para times inteiros -- inclusive para quem ficou 12 de 12
    rounds dentro do B.
    """
    assert areas["CTSpawn"] == AREA_SPAWN


def test_area_dominante_ignora_amostras_de_spawn(areas):
    pos = _positions(
        [
            {"round_num": 1, "steamid": 1, "name": "p", "side": "ct", "place": "CTSpawn", "ticks": 8},
            {"round_num": 1, "steamid": 1, "name": "p", "side": "ct", "place": "BombsiteB", "ticks": 2},
        ]
    )
    dominante = player_round_areas(player_round_area_shares(pos, areas))
    # sem o filtro, o spawn seria a área dominante (8 de 10 amostras)
    assert dominante["area"].to_list() == [AREA_B]
    assert dominante["area_share"][0] == 1.0


def _rounds_ct(steamid: int, nome: str, plano: list[tuple[str, int]], n_rounds: int) -> list[dict]:
    linhas = []
    for r in range(1, n_rounds + 1):
        for place, ticks in plano:
            linhas.append({"round_num": r, "steamid": steamid, "name": nome,
                           "side": "ct", "place": place, "ticks": ticks})
    return linhas


def test_ancora_que_nunca_sai_pontua_um(areas):
    linhas = _rounds_ct(1, "ancora", [("BombsiteB", 10)], 4)
    # um T por round, pro cálculo da área inimiga não ficar vazio
    linhas += [{"round_num": r, "steamid": 9, "name": "t", "side": "t",
                "place": "BombsiteA", "ticks": 10} for r in range(1, 5)]
    _, summary = anchor_metrics(player_round_area_shares(_positions(linhas), areas))

    linha = summary.row(0, named=True)
    assert linha["home_area"] == AREA_B
    assert linha["never_left_share"] == 1.0
    assert linha["no_rotate_share"] == 1.0  # os T foram pro A em todos os rounds


def test_passagem_curta_pelo_outro_lado_nao_conta_como_rotacao(areas):
    """REGRESSÃO: o caminho até o próprio bombsite pode cruzar a área do outro.

    O jogador passa 1 de 20 amostras (5% do round) no corredor do lado A e joga
    o resto dentro do B. Isso é trajeto, não rotação -- e era o que zerava a
    métrica de âncoras reais.
    """
    plano = [("HallA", 1), ("BombsiteB", 19)]
    assert 1 / 20 < MIN_OTHER_SITE_SHARE, "fixture precisa ficar abaixo do piso"

    linhas = _rounds_ct(1, "ancora", plano, 4)
    linhas += [{"round_num": r, "steamid": 9, "name": "t", "side": "t",
                "place": "BombsiteA", "ticks": 10} for r in range(1, 5)]
    _, summary = anchor_metrics(player_round_area_shares(_positions(linhas), areas))

    assert summary.row(0, named=True)["never_left_share"] == 1.0


def test_rotacao_de_verdade_conta(areas):
    """Metade do round do outro lado é rotação, não passagem."""
    linhas = _rounds_ct(1, "rotador", [("BombsiteB", 10), ("HallA", 10)], 4)
    linhas += [{"round_num": r, "steamid": 9, "name": "t", "side": "t",
                "place": "BombsiteA", "ticks": 10} for r in range(1, 5)]
    _, summary = anchor_metrics(player_round_area_shares(_positions(linhas), areas))

    assert summary.row(0, named=True)["never_left_share"] == 0.0


def test_quem_joga_o_meio_nao_recebe_numero_de_ancora(areas):
    """Null, não 1,0: sem bombsite de casa não há o que ancorar.

    Com 1,0 o jogador de meio lideraria o time na métrica sem nunca ter ancorado
    nada, e ganharia o rótulo de âncora.
    """
    linhas = _rounds_ct(1, "meio", [("Middle", 10)], 4)
    linhas += [{"round_num": r, "steamid": 9, "name": "t", "side": "t",
                "place": "BombsiteA", "ticks": 10} for r in range(1, 5)]
    _, summary = anchor_metrics(player_round_area_shares(_positions(linhas), areas))

    linha = summary.row(0, named=True)
    assert linha["home_area"] == AREA_MID
    assert linha["never_left_share"] is None


def test_lurk_compara_com_o_resto_do_time(areas):
    """O T sozinho no B enquanto os outros quatro vão pro A."""
    linhas = []
    for r in range(1, 5):
        linhas.append({"round_num": r, "steamid": 1, "name": "lurker", "side": "t",
                       "place": "BombsiteB", "ticks": 10})
        for i in range(2, 6):
            linhas.append({"round_num": r, "steamid": i, "name": f"exec{i}", "side": "t",
                           "place": "BombsiteA", "ticks": 10})

    _, summary = lurk_metrics(player_round_area_shares(_positions(linhas), areas))
    por_nome = dict(zip(summary["name"].to_list(), summary["off_team_share"].to_list()))

    assert por_nome["lurker"] == 1.0
    # e quem executou junto não vira lurker por tabela
    assert all(por_nome[f"exec{i}"] == 0.0 for i in range(2, 6))


def test_time_dividido_nao_define_area_do_time(areas):
    """Time 2-2 entre os dois sites não tem "área do time".

    O round sai do denominador em vez de chutar uma das duas -- chutar faria o
    jogador do meio parecer que se separou de um time que nunca se juntou.
    """
    linhas = []
    for r in range(1, 3):
        for i, place in ((1, "Middle"), (2, "BombsiteA"), (3, "BombsiteA"),
                         (4, "BombsiteB"), (5, "BombsiteB")):
            linhas.append({"round_num": r, "steamid": i, "name": f"p{i}", "side": "t",
                           "place": place, "ticks": 10})

    per_round, summary = lurk_metrics(player_round_area_shares(_positions(linhas), areas))

    # p1: os outros quatro estão 2-2, não há maioria
    do_meio = per_round.filter(pl.col("name") == "p1")
    assert do_meio["team_area"].null_count() == do_meio.height
    assert do_meio["off_team"].null_count() == do_meio.height
    assert summary.filter(pl.col("name") == "p1")["n_rounds_time_definido"][0] == 0

    # p2: excluindo ele, sobram 1 no A, 2 no B e 1 no meio -- há maioria (B), e
    # ele está fora dela
    do_a = per_round.filter(pl.col("name") == "p2")
    assert do_a["team_area"].to_list() == [AREA_B, AREA_B]
    assert do_a["off_team"].to_list() == [True, True]
