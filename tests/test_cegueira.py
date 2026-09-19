"""
Reconstrução da cegueira por flash (parsing/cegueira.py).

As demos de campeonato não gravam `player_blind`; a reconstrução sai de
`flash_duration` + detonações. Ela só entra no projeto porque é validada contra
o evento real nas demos que o têm -- o último teste roda essa validação.
"""
from __future__ import annotations

from pathlib import Path

import polars as pl
import pytest

from parsing.cegueira import reconstroi, valida_contra_eventos


def _ticks(serie: dict[int, list[tuple[int, float]]]) -> pl.DataFrame:
    linhas = [
        {"round_num": 1, "tick": t, "steamid": sid, "name": f"j{sid}", "side": "ct" if sid < 10 else "t",
         "flash_duration": d}
        for sid, pontos in serie.items() for t, d in pontos
    ]
    return pl.DataFrame(linhas).with_columns(pl.col("round_num").cast(pl.UInt32), pl.col("steamid").cast(pl.UInt64))


def _det(linhas: list[tuple[int, int, int, str]]) -> pl.DataFrame:
    return pl.DataFrame(
        [{"tick": t, "entityid": e, "user_steamid": s, "user_name": f"j{s}", "user_side": lado}
         for t, e, s, lado in linhas]
    ).with_columns(pl.col("user_steamid").cast(pl.UInt64))


def test_cegueira_que_emenda_em_outra_conta_duas_vezes():
    """O valor não passa por zero entre duas flashes seguidas: ele TROCA. Contar
    só a transição 0 -> positivo perderia a segunda flash."""
    ticks = _ticks({1: [(100, 0.0), (101, 2.5), (102, 2.5), (150, 1.2), (151, 1.2), (230, 0.0)]})
    det = _det([(101, 7, 20, "t"), (150, 8, 21, "t")])
    rec = reconstroi(ticks, det)
    assert rec["tick"].to_list() == [101, 150]
    assert rec["blind_duration"].to_list() == pytest.approx([2.5, 1.2])
    assert rec["attacker_steamid"].to_list() == [20, 21]


def test_duas_flashes_no_mesmo_instante_ficam_sem_dono():
    """Flash mal atribuída é pior que flash sem dono."""
    ticks = _ticks({1: [(100, 0.0), (101, 3.0)]})
    rec = reconstroi(ticks, _det([(101, 7, 20, "t"), (101, 8, 21, "t")]))
    assert rec["atribuicao"].to_list() == ["ambigua"]
    assert rec["attacker_steamid"].to_list() == [None]


def test_detonacao_longe_no_tempo_nao_e_dona():
    ticks = _ticks({1: [(100, 0.0), (101, 3.0)]})
    rec = reconstroi(ticks, _det([(140, 7, 20, "t")]))
    assert rec["atribuicao"].to_list() == ["sem_detonacao"]


def test_a_reconstrucao_reproduz_o_evento_real_nas_demos_que_o_tem():
    """A validação que autoriza a reconstrução a entrar no projeto: nas demos de
    FACEIT, que gravam `player_blind`, reconstruir e comparar. Medido nas 9:
    1.578 de 1.578 achadas, todas com o arremessador certo e a duração exata."""
    pastas = [p for p in sorted(Path("data/interim").glob("match_*"))
              if (p / "player_blind.parquet").exists() and (p / "flashbang_detonate.parquet").exists()]
    reais = []
    for d in pastas:
        real = pl.read_parquet(d / "player_blind.parquet")
        if "origem" in real.columns:          # já é reconstruída: não serve de gabarito
            continue
        reais.append((d, real))
    if not reais:
        pytest.skip("nenhuma demo com o evento real de cegueira")
    for d, real in reais[:3]:
        ticks = pl.read_parquet(d / "ticks.parquet", columns=["round_num", "tick", "steamid", "name", "side", "flash_duration"])
        v = valida_contra_eventos(reconstroi(ticks, pl.read_parquet(d / "flashbang_detonate.parquet")), real)
        assert v["achadas"] == v["reais"] == v["reconstruidas"], (d.name, v)
        assert v["dono_errado"] == 0 and v["inventadas"] == 0, (d.name, v)
