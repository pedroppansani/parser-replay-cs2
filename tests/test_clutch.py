"""
Testes das situações de último vivo.

A regressão central: antes disto, clutch só era registrado quando o jogador
GANHAVA (scripts/build_insights.py só guardava o vencedor). Com isso não existia
denominador, e "quem chega muito em último vivo e não converte" era impossível de
medir. Contar só as vitórias é o mesmo erro de contar só os tiros que acertaram.
"""
from __future__ import annotations

import polars as pl

from metrics.clutch import MIN_ENEMIES_ALIVE, add_damage_in_clutch, clutch_situations

# Time A = jogadores 1..5, Time B = 11..15.
TEAM_OF = {**{i: "A" for i in range(1, 6)}, **{i: "B" for i in range(11, 16)}}


def _kills(sequencia: list[tuple[int, int, int]]) -> pl.DataFrame:
    """sequencia: (tick, attacker_steamid, victim_steamid)"""
    return pl.DataFrame(
        {
            "round_num": [1] * len(sequencia),
            "tick": [t for t, _, _ in sequencia],
            "attacker_steamid": [a for _, a, _ in sequencia],
            "victim_steamid": [v for _, _, v in sequencia],
        }
    ).with_columns(pl.col("round_num").cast(pl.UInt32))


def _rounds() -> pl.DataFrame:
    return pl.DataFrame({"round_num": [1], "winner": ["t"]}).with_columns(
        pl.col("round_num").cast(pl.UInt32)
    )


def test_tentativa_perdida_tambem_e_registrada():
    """O caso que não existia no dado: ficou por último contra 3 e perdeu."""
    kills = _kills([(100, 11, 2), (110, 12, 3), (120, 13, 4), (130, 14, 5), (200, 11, 1)])
    per_round, summary = clutch_situations(kills, _rounds(), TEAM_OF, {1: "B"})

    assert per_round.height == 1
    linha = per_round.row(0, named=True)
    assert linha["steamid"] == 1
    assert linha["won"] is False
    assert summary.row(0, named=True)["clutch_attempts"] == 1
    assert summary.row(0, named=True)["clutch_wins"] == 0


def test_tentativa_convertida_conta_como_vitoria():
    kills = _kills(
        [(100, 11, 2), (110, 12, 3), (120, 13, 4), (130, 14, 5),
         (200, 1, 11), (210, 1, 12), (220, 1, 13), (230, 1, 14), (240, 1, 15)]
    )
    per_round, summary = clutch_situations(kills, _rounds(), TEAM_OF, {1: "A"})

    linha = per_round.row(0, named=True)
    assert linha["won"] is True
    assert linha["kills_in_clutch"] == 5
    assert summary.row(0, named=True)["clutch_conversion"] == 1.0


def test_um_contra_um_nao_e_clutch():
    """1v1 é duelo. Contá-lo encheria a métrica de situação sem nada de especial."""
    kills = _kills(
        [(100, 11, 2), (110, 12, 3), (120, 13, 4), (130, 14, 5),
         (140, 1, 11), (150, 1, 12), (160, 1, 13), (170, 1, 14)]
    )
    per_round, _ = clutch_situations(kills, _rounds(), TEAM_OF, {1: "A"})

    # quando o time A cai para 1, o B ainda tinha 5 -> conta;
    # a situação inversa (B com 1 contra 1) não deve entrar
    assert all(linha["enemies_alive"] >= MIN_ENEMIES_ALIVE for linha in per_round.iter_rows(named=True))


def test_kills_antes_de_ficar_sozinho_nao_contam():
    """Separa "segurou o round sozinho" de "já tinha feito tudo antes"."""
    kills = _kills(
        [(50, 1, 11), (60, 1, 12),          # matou dois ANTES
         (100, 13, 2), (110, 13, 3), (120, 13, 4), (130, 13, 5),  # time morreu
         (200, 1, 13)]                       # matou um DEPOIS
    )
    per_round, _ = clutch_situations(kills, _rounds(), TEAM_OF, {1: "A"})
    assert per_round.row(0, named=True)["kills_in_clutch"] == 1


def test_dano_no_clutch_conta_so_depois_da_situacao_comecar():
    kills = _kills([(100, 11, 2), (110, 12, 3), (120, 13, 4), (130, 14, 5)])
    per_round, _ = clutch_situations(kills, _rounds(), TEAM_OF, {1: "B"})

    damages = pl.DataFrame(
        {
            "round_num": [1, 1],
            "tick": [50, 200],
            "attacker_steamid": [1, 1],
            "victim_steamid": [11, 11],
            "dmg_health_real": [40, 70],
        }
    ).with_columns(pl.col("round_num").cast(pl.UInt32))

    com_dano = add_damage_in_clutch(per_round, damages, TEAM_OF)
    assert com_dano.row(0, named=True)["damage_in_clutch"] == 70


def test_fogo_amigo_nao_entra_no_dano_do_clutch():
    kills = _kills([(100, 11, 2), (110, 12, 3), (120, 13, 4), (130, 14, 5)])
    per_round, _ = clutch_situations(kills, _rounds(), TEAM_OF, {1: "B"})

    damages = pl.DataFrame(
        {
            "round_num": [1],
            "tick": [200],
            "attacker_steamid": [1],
            "victim_steamid": [2],  # companheiro
            "dmg_health_real": [50],
        }
    ).with_columns(pl.col("round_num").cast(pl.UInt32))

    com_dano = add_damage_in_clutch(per_round, damages, TEAM_OF)
    assert com_dano.row(0, named=True)["damage_in_clutch"] == 0


def test_round_sem_situacao_devolve_tabela_vazia_com_schema():
    """Tabela vazia com schema certo, pra o join a jusante não estourar."""
    kills = _kills([(100, 11, 2)])
    per_round, summary = clutch_situations(kills, _rounds(), TEAM_OF, {1: "B"})
    assert per_round.height == 0
    assert "clutch_attempts" in summary.columns
