"""
Testes das métricas de utility (Fase 4) e da derivação de função por jogador.

Mesma filosofia dos demais: dados sintéticos escritos à mão pra travar a LÓGICA
descrita nos módulos. Se os números da partida real fazem sentido de jogo, quem
responde é a revisão manual — não estes testes.

Dois testes aqui travam decisões que já custaram bug de verdade:
`test_carried_grenades_are_not_counted_as_thrown` (granada parada no inventário
sendo contada como arremesso) e `test_projectile_count_matches_detonations`.
"""
from __future__ import annotations

from pathlib import Path

import polars as pl
import pytest

from metrics.grenades import (
    EFFECTIVE_BLIND_SECONDS,
    PROJECTILE_KIND,
    compute_grenade_metrics,
    flash_impact,
    grenades_thrown,
)
from metrics.player_roles import TRAIT_SPECS, assign_traits

TICKRATE = 128
INTERIM = Path(__file__).resolve().parent.parent / "data" / "interim"


def _roster(players: list[tuple[int, str, str]], rounds: int = 1) -> pl.DataFrame:
    rows = [
        {"round_num": r, "steamid": sid, "name": name, "side": side}
        for r in range(1, rounds + 1)
        for sid, name, side in players
    ]
    return pl.DataFrame(
        rows,
        schema={"round_num": pl.UInt32, "steamid": pl.UInt64, "name": pl.String, "side": pl.String},
    )


def _grenades(rows: list[dict]) -> pl.DataFrame:
    return pl.DataFrame(
        rows,
        schema={
            "round_num": pl.UInt32, "entity_id": pl.Int32, "thrower_steamid": pl.UInt64,
            "thrower": pl.String, "grenade_type": pl.String, "tick": pl.Int32,
            "X": pl.Float32, "Y": pl.Float32, "Z": pl.Float32,
        },
    )


def _blinds(rows: list[dict]) -> pl.DataFrame:
    return pl.DataFrame(
        rows,
        schema={
            "round_num": pl.UInt32, "tick": pl.Int32, "entityid": pl.Int32,
            "attacker_steamid": pl.UInt64, "attacker_side": pl.String,
            "user_steamid": pl.UInt64, "user_side": pl.String, "blind_duration": pl.Float32,
        },
    )


def _kills(rows: list[dict]) -> pl.DataFrame:
    return pl.DataFrame(
        rows,
        schema={
            "round_num": pl.UInt32, "tick": pl.Int32,
            "attacker_steamid": pl.UInt64, "attacker_side": pl.String,
            "victim_steamid": pl.UInt64, "victim_side": pl.String,
        },
    )


# --- Arremesso vs. inventário ---------------------------------------------

def test_carried_grenades_are_not_counted_as_thrown():
    """A entidade que acompanha o jogador não é um arremesso.

    Esse foi um bug real: a tabela `grenades` do awpy traz CFlashbang (a granada
    parada na mão, com uma amostra por tick do round inteiro) junto de
    CFlashbangProjectile (a que foi jogada). Contar as duas inflava os
    arremessos em ~2,5x e, no replay, desenhava uma granada colada em cada
    jogador do começo ao fim do round.
    """
    roster = _roster([(1, "A", "t")])
    grenades = _grenades(
        # arremessada: duas posições diferentes, voando
        [{"round_num": 1, "entity_id": 10, "thrower_steamid": 1, "thrower": "A",
          "grenade_type": "CFlashbangProjectile", "tick": 500 + i, "X": float(i * 50), "Y": 0.0, "Z": 0.0}
         for i in range(3)]
        # carregada: mesma granada no inventário, seguindo o jogador
        + [{"round_num": 1, "entity_id": 11, "thrower_steamid": 1, "thrower": "A",
            "grenade_type": "CFlashbang", "tick": 100 + i, "X": 0.0, "Y": 0.0, "Z": 0.0}
           for i in range(200)]
    )

    out = grenades_thrown(grenades, roster)
    assert out["flash_thrown"].sum() == 1


def test_projectile_kind_has_no_inventory_classes():
    """Nenhuma classe sem sufixo Projectile pode entrar no mapeamento."""
    assert all(k.endswith("Projectile") for k in PROJECTILE_KIND)


# --- Flash: efeito, não arremesso -----------------------------------------

def test_short_blind_does_not_count_as_enemy_flashed():
    """Abaixo do limiar o inimigo perde o HUD, não a briga.

    O tempo cru continua somado em enemy_blind_seconds — o limiar filtra a
    CONTAGEM de inimigos cegados, não esconde o tempo.
    """
    roster = _roster([(1, "A", "t"), (2, "B", "ct")])
    blinds = _blinds([{
        "round_num": 1, "tick": 1000, "entityid": 5,
        "attacker_steamid": 1, "attacker_side": "t",
        "user_steamid": 2, "user_side": "ct",
        "blind_duration": EFFECTIVE_BLIND_SECONDS - 0.4,
    }])

    row = flash_impact(blinds, _kills([]), roster, TICKRATE).filter(pl.col("steamid") == 1).row(0, named=True)
    assert row["enemies_flashed"] == 0
    assert row["enemy_blind_seconds"] == pytest.approx(EFFECTIVE_BLIND_SECONDS - 0.4, abs=1e-5)


def test_team_flash_is_not_netted_against_enemy_flash():
    """Cegar o próprio time é um erro à parte, não um desconto.

    Se os dois caíssem no mesmo saldo, quem cegou 2 inimigos e 2 companheiros
    apareceria igual a quem não jogou flash nenhuma.
    """
    roster = _roster([(1, "A", "t"), (2, "B", "ct"), (3, "C", "t")])
    blinds = _blinds([
        {"round_num": 1, "tick": 1000, "entityid": 5, "attacker_steamid": 1, "attacker_side": "t",
         "user_steamid": 2, "user_side": "ct", "blind_duration": 2.0},
        {"round_num": 1, "tick": 1000, "entityid": 5, "attacker_steamid": 1, "attacker_side": "t",
         "user_steamid": 3, "user_side": "t", "blind_duration": 3.0},
    ])

    row = flash_impact(blinds, _kills([]), roster, TICKRATE).filter(pl.col("steamid") == 1).row(0, named=True)
    assert row["enemies_flashed"] == 1
    assert row["enemy_blind_seconds"] == pytest.approx(2.0)
    assert row["teammates_flashed"] == 1
    assert row["team_blind_seconds"] == pytest.approx(3.0)


def test_self_flash_is_separated_from_team_flash():
    roster = _roster([(1, "A", "t")])
    blinds = _blinds([{
        "round_num": 1, "tick": 1000, "entityid": 5, "attacker_steamid": 1, "attacker_side": "t",
        "user_steamid": 1, "user_side": "t", "blind_duration": 2.5,
    }])

    row = flash_impact(blinds, _kills([]), roster, TICKRATE).filter(pl.col("steamid") == 1).row(0, named=True)
    assert row["self_blind_seconds"] == pytest.approx(2.5)
    assert row["team_blind_seconds"] == 0.0
    assert row["teammates_flashed"] == 0


def test_flash_assist_requires_victim_still_blind():
    """Kill depois da cegueira passar não é assist da flash."""
    roster = _roster([(1, "A", "t"), (2, "B", "ct"), (3, "C", "t")])
    blinds = _blinds([{
        "round_num": 1, "tick": 1000, "entityid": 5, "attacker_steamid": 1, "attacker_side": "t",
        "user_steamid": 2, "user_side": "ct", "blind_duration": 2.0,
    }])

    # companheiro mata dentro da janela de cegueira -> assist
    dentro = _kills([{"round_num": 1, "tick": 1000 + int(1.0 * TICKRATE), "attacker_steamid": 3,
                      "attacker_side": "t", "victim_steamid": 2, "victim_side": "ct"}])
    row = flash_impact(blinds, dentro, roster, TICKRATE).filter(pl.col("steamid") == 1).row(0, named=True)
    assert row["flash_assists"] == 1
    assert row["flash_kills"] == 0

    # muito depois do fim da cegueira (2s + folga) -> não é assist
    fora = _kills([{"round_num": 1, "tick": 1000 + int(8.0 * TICKRATE), "attacker_steamid": 3,
                    "attacker_side": "t", "victim_steamid": 2, "victim_side": "ct"}])
    row = flash_impact(blinds, fora, roster, TICKRATE).filter(pl.col("steamid") == 1).row(0, named=True)
    assert row["flash_assists"] == 0


def test_killing_own_flashed_enemy_is_kill_not_assist():
    """Quem flasha e mata sozinho não ganha assist — é outra jogada."""
    roster = _roster([(1, "A", "t"), (2, "B", "ct")])
    blinds = _blinds([{
        "round_num": 1, "tick": 1000, "entityid": 5, "attacker_steamid": 1, "attacker_side": "t",
        "user_steamid": 2, "user_side": "ct", "blind_duration": 2.0,
    }])
    kills = _kills([{"round_num": 1, "tick": 1050, "attacker_steamid": 1, "attacker_side": "t",
                     "victim_steamid": 2, "victim_side": "ct"}])

    row = flash_impact(blinds, kills, roster, TICKRATE).filter(pl.col("steamid") == 1).row(0, named=True)
    assert row["flash_kills"] == 1
    assert row["flash_assists"] == 0


def test_metrics_survive_match_without_any_flash():
    """Partida sem flash nenhuma não pode quebrar o pipeline."""
    roster = _roster([(1, "A", "t")])
    tables = {
        "grenades": _grenades([]),
        "kills": _kills([]),
        "player_blind": None,
        "damages": pl.DataFrame(
            [],
            schema={"round_num": pl.UInt32, "tick": pl.Int32, "attacker_steamid": pl.UInt64,
                    "attacker_side": pl.String, "victim_steamid": pl.UInt64, "victim_side": pl.String,
                    "weapon": pl.String, "dmg_health_real": pl.Int32},
        ),
        "rounds": pl.DataFrame(
            [{"round_num": 1, "freeze_end": 100}],
            schema={"round_num": pl.UInt32, "freeze_end": pl.Int32},
        ),
    }

    per_round, summary = compute_grenade_metrics(tables, roster, TICKRATE)
    assert per_round.height == 1
    assert summary["enemies_flashed"].sum() == 0
    assert summary["nades_thrown"].sum() == 0


# --- Validação contra a demo real -----------------------------------------

@pytest.mark.skipif(
    not (INTERIM / "match_01" / "grenades.parquet").exists(),
    reason="precisa de uma demo processada em data/interim/ (rode scripts/process_demo.py)",
)
@pytest.mark.parametrize(
    ("kind", "event"),
    [("flash", "flashbang_detonate"), ("he", "hegrenade_detonate"), ("smoke", "smokegrenade_detonate")],
)
def test_projectile_count_matches_detonations(kind: str, event: str):
    """Cada projétil na trajetória corresponde a uma detonação registrada.

    É a evidência de que PROJECTILE_KIND separa certo granada arremessada de
    granada carregada: são duas fontes independentes do demo (a trajetória da
    entidade e o evento de detonação) que têm que dar o mesmo número. Contando
    as classes de inventário junto, a trajetória dava ~2,5x mais.
    """
    match = INTERIM / "match_01"
    detonations = pl.read_parquet(match / f"{event}.parquet").height
    projectiles = (
        pl.read_parquet(match / "grenades.parquet")
        .filter(pl.col("grenade_type").is_in([k for k, v in PROJECTILE_KIND.items() if v == kind]))
        .select(["round_num", "entity_id"])
        .unique()
        .height
    )
    assert projectiles == detonations


# --- Função por jogador ----------------------------------------------------

def _signals(rows: list[dict]) -> pl.DataFrame:
    """Sinais mínimos pra assign_traits: só as colunas que as specs olham."""
    base = {spec.column: 0.0 for spec in TRAIT_SPECS}
    base.update({"steamid": 0, "name": "?", "team": "A"})
    return pl.DataFrame([{**base, **r} for r in rows])


def test_role_requires_passing_the_floor_not_just_leading_the_team():
    """Liderar um time que não joga AWP não faz de ninguém AWPer.

    É a razão de cada função ter piso absoluto além do ranking interno.
    """
    signals = _signals([
        {"steamid": 1, "name": "A", "team": "A", "awp_share": 0.05},
        {"steamid": 2, "name": "B", "team": "A", "awp_share": 0.0},
    ])
    traits = assign_traits(signals)
    assert "awp" not in traits["trait"].to_list()


def test_role_is_assigned_when_leader_passes_floor():
    # `awp_share` é "dos rounds em que o TIME teve AWP, em quantos ela era dele"
    # (decisão do Pedro, 2026-09-24): 0,80 é o AWPer do time, 0,40 não é mais --
    # na escala antiga (AWP / todos os rounds) 0,40 passava do piso de 0,25.
    signals = _signals([
        {"steamid": 1, "name": "A", "team": "A", "awp_share": 0.80},
        {"steamid": 2, "name": "B", "team": "A", "awp_share": 0.10},
    ])
    traits = assign_traits(signals).filter(pl.col("trait") == "awp")
    assert traits.height == 1
    assert traits["name"][0] == "A"


def test_roles_are_compared_within_the_team_not_across_the_match():
    """Cada time tem seu próprio líder de utility: função é divisão interna.

    Se a comparação fosse entre os 10 jogadores, o time inteiro que joga menos
    utility ficaria sem suporte nenhum, o que não descreve como ele joga.
    """
    signals = _signals([
        {"steamid": 1, "name": "A1", "team": "A", "enemy_blind_seconds": 80.0},
        {"steamid": 2, "name": "A2", "team": "A", "enemy_blind_seconds": 10.0},
        {"steamid": 3, "name": "B1", "team": "B", "enemy_blind_seconds": 30.0},
        {"steamid": 4, "name": "B2", "team": "B", "enemy_blind_seconds": 5.0},
    ])
    support = assign_traits(signals).filter(pl.col("trait") == "support")
    assert sorted(support["name"].to_list()) == ["A1", "B1"]
