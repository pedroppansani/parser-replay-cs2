"""
O lurker é medido SEM os rounds com AWP e RELATIVO à função estrutural, com
amostra mínima (decisão do Pedro, 2026-09-24).

O caso que motivou: o m0NESY, cujo título é "AWPer, AWP na mão em 63% dos
rounds", levava "Lurker" como característica secundária (match_32). Segurar um
ângulo longe do time com a AWP é o trabalho do AWPer.

São dois consertos para duas causas diferentes, e os dois têm teste aqui:
  - estrutural: a régua é a taxa esperada da FUNÇÃO daqueles rounds, não a média
    do elenco (princípio da decisão 15c);
  - amostra: abaixo de MIN_ROUNDS_SEM_AWP a função não é afirmada -- é dado
    insuficiente, não uma medição que disse não.
"""
from __future__ import annotations

import polars as pl
import pytest

from metrics.player_roles import (
    MIN_ROUNDS_SEM_AWP,
    OFF_TEAM_ESPERADO_POR_FUNCAO,
    OFF_TEAM_ESPERADO_SEM_FUNCAO,
    PISO_LURK_RELATIVO,
    assign_traits,
    lurk_relativo,
)


def _outputs(rounds_fora: int, rounds_dentro: int, rounds_com_awp_fora: int = 0,
             funcao: str | None = None) -> dict[str, pl.DataFrame]:
    """Um jogador: `rounds_fora` rounds fora da área do time sem AWP, `rounds_dentro`
    dentro, e `rounds_com_awp_fora` rounds fora da área MAS com a AWP na mão."""
    linhas, r = [], 1
    for _ in range(rounds_fora):
        linhas.append({"round_num": r, "steamid": 1, "off_team": True}); r += 1
    for _ in range(rounds_dentro):
        linhas.append({"round_num": r, "steamid": 1, "off_team": False}); r += 1
    com_awp = []
    for _ in range(rounds_com_awp_fora):
        linhas.append({"round_num": r, "steamid": 1, "off_team": True})
        com_awp.append({"round_num": r, "steamid": 1}); r += 1
    lurk = pl.DataFrame(linhas, schema={"round_num": pl.UInt32, "steamid": pl.UInt64, "off_team": pl.Boolean})
    return {
        "lurk_per_round": lurk,
        "awp_per_round": pl.DataFrame(com_awp, schema={"round_num": pl.UInt32, "steamid": pl.UInt64}),
        "structural_roles": lurk.select("round_num", "steamid").with_columns(
            pl.lit(funcao, dtype=pl.String).alias("funcao")),
    }


def test_rounds_com_awp_ficam_fora_da_conta():
    """REGRESSÃO (m0NESY): o ângulo segurado com a AWP não é lurk."""
    r = lurk_relativo(_outputs(rounds_fora=2, rounds_dentro=6, rounds_com_awp_fora=6)).row(0, named=True)
    assert r["n_rounds_sem_awp"] == 8, "os rounds com AWP entraram no denominador"
    assert r["off_team_share_sem_awp"] == pytest.approx(2 / 8)


def test_a_regua_e_a_funcao_daqueles_rounds_e_nao_a_media_do_elenco():
    """Mesma taxa observada, funções diferentes -> relativo diferente.

    O trader joga fora da área do time bem menos que o entry (0,175 contra
    0,291 no corpus): 40% é muito mais fora do normal para um trader.
    """
    obs = 0.4
    trader = lurk_relativo(_outputs(4, 6, funcao="trader")).row(0, named=True)
    entry = lurk_relativo(_outputs(4, 6, funcao="entry")).row(0, named=True)
    assert trader["off_team_share_sem_awp"] == entry["off_team_share_sem_awp"] == pytest.approx(obs)
    assert trader["off_team_esperado"] == pytest.approx(OFF_TEAM_ESPERADO_POR_FUNCAO["trader"])
    assert trader["off_team_relativo"] > entry["off_team_relativo"]
    assert trader["off_team_relativo"] == pytest.approx(obs / OFF_TEAM_ESPERADO_POR_FUNCAO["trader"])


def test_round_sem_funcao_reconhecida_tem_regua_propria():
    r = lurk_relativo(_outputs(4, 6, funcao=None)).row(0, named=True)
    assert r["off_team_esperado"] == pytest.approx(OFF_TEAM_ESPERADO_SEM_FUNCAO)


def _sinais(rel: float, n: int) -> pl.DataFrame:
    """Dois jogadores do mesmo time: o primeiro lidera a métrica."""
    return pl.DataFrame({
        "steamid": [1, 2], "name": ["lider", "outro"], "team": ["A", "A"],
        "off_team_relativo": [rel, 0.1], "n_rounds_sem_awp": [n, 12],
        "off_team_share_sem_awp": [0.5, 0.05],
    })


def _tem_lurk(df: pl.DataFrame) -> bool:
    t = assign_traits(df)
    return t.height > 0 and "lurk" in t["trait"].to_list()


def test_amostra_curta_nao_afirma_lurk_mesmo_passando_do_piso():
    """Dado insuficiente não é "não qualifica": o rótulo simplesmente não sai."""
    assert not _tem_lurk(_sinais(rel=3.0, n=MIN_ROUNDS_SEM_AWP - 1))
    assert _tem_lurk(_sinais(rel=3.0, n=MIN_ROUNDS_SEM_AWP))


def test_quem_joga_o_esperado_da_funcao_nao_e_lurker():
    """Estar fora da área do time tanto quanto a função dele costuma estar é o
    trabalho, não desvio."""
    assert not _tem_lurk(_sinais(rel=1.0, n=12))
    assert not _tem_lurk(_sinais(rel=PISO_LURK_RELATIVO - 0.1, n=12))
    assert _tem_lurk(_sinais(rel=PISO_LURK_RELATIVO, n=12))


def test_a_evidencia_traz_o_bruto_junto_da_taxa():
    """Decisão 7a: taxa sempre com o bruto."""
    t = assign_traits(_sinais(rel=2.0, n=12)).filter(pl.col("trait") == "lurk").row(0, named=True)
    assert "6 de 12" in t["evidence"] and "2.0x" in t["evidence"].replace(",", ".")
