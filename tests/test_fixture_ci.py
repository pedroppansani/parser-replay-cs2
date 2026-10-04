"""A escada contra a HLTV e a soma zero do Round Swing rodando num clone limpo
(auditoria, item 5.7), sobre a fixture tests/fixtures/interim_ci.

Os testes de origem (test_escada.py e o da soma zero em test_rating.py) leem o
interim inteiro, que não é versionado, e por isso são pulados no CI. Estes
rodam as MESMAS conferências nas duas partidas da fixture. Os invariantes do
corpus (test_invariantes_corpus.py) não precisam de fixture: leem só
data/processed/, que é versionado.
"""
from __future__ import annotations

from pathlib import Path

import polars as pl
import pytest

from scripts.escada_validacao import TOLERANCIA_ADR, contagens
from scripts.gera_fixture_ci import COLUNAS_DE_TICKS, DESTINO, EVENTOS, LIMITE_BYTES, PARTIDAS

RAIZ = Path(__file__).resolve().parent.parent
INTERIM_REAL = RAIZ / "data" / "interim"


def test_a_fixture_cabe_em_10_mb_e_tem_as_duas_partidas():
    arquivos = list(DESTINO.rglob("*.parquet"))
    assert sum(f.stat().st_size for f in arquivos) <= LIMITE_BYTES
    assert sorted(p.name for p in DESTINO.iterdir() if p.is_dir()) == sorted(PARTIDAS)
    rounds = {m: pl.read_parquet(RAIZ / "data" / "processed" / m / "rounds.parquet").height for m in PARTIDAS}
    assert min(rounds.values()) <= 24 < max(rounds.values()), rounds     # uma com prorrogação, uma sem


def test_escada_na_fixture_rounds_kills_mortes_e_adr_batem_com_a_hltv():
    c = contagens(interim=DESTINO, partidas=list(PARTIDAS))
    assert sorted(c["match_id"].unique().to_list()) == sorted(PARTIDAS) and c.height == 20
    por_partida = c.unique("match_id")
    assert (por_partida["rounds"] == por_partida["rounds_oficial"]).all()
    errados = c.filter((c["kills"] != c["kills_oficial"]) | (c["mortes"] != c["mortes_oficial"]))
    assert errados.height == 0, errados.select("match_id", "nome", "kills_oficial", "kills", "mortes_oficial", "mortes")
    fora = c.filter((c["adr"] - c["adr_oficial"]).abs() > TOLERANCIA_ADR)
    assert fora.height == 0, fora.select("match_id", "nome", "adr_oficial", "adr")


@pytest.mark.parametrize("match_id", PARTIDAS)
def test_swing_soma_zero_na_fixture(match_id):
    """A mesma conferência de test_rating.py (decisão 22k), sobre a fixture."""
    from metrics.rating import ModeloDeRound, carrega_referencia, grupo_do_round, swing_por_evento
    from scripts.fit_rating import carrega_partida

    t, team_of, venc, _ = carrega_partida(match_id, pasta_interim=DESTINO)
    modelo = ModeloDeRound.da_referencia((carrega_referencia() or {}).get("modelo_de_round"))
    sw = swing_por_evento(t["kills"], t["damages"], t["player_blind"], t["rounds"],
                          grupo_do_round(t["ticks"], t["rounds"]), modelo, team_of, venc, 64)
    soma = dict(sw.group_by("round_num").agg(pl.col("swing").sum()).iter_rows())
    fim = dict(t["rounds"].select("round_num", "end").iter_rows())
    sem_matador = {
        int(r["round_num"]) for r in t["kills"].iter_rows(named=True)
        if r["tick"] < fim[r["round_num"]] and r.get("weapon") != "planted_c4"
        and (r["attacker_steamid"] is None or r["attacker_side"] == r["victim_side"])
    }
    assert soma
    for rn, s in soma.items():
        if int(rn) in sem_matador:
            assert s < 0, f"round {rn}: a vítima sem matador inimigo tinha que ter pago"
        else:
            assert abs(s) < 1e-9, f"round {rn} somou {s}"


@pytest.mark.parametrize("match_id", PARTIDAS)
def test_a_fixture_e_igual_ao_interim_quando_ele_existe(match_id):
    """Fixture desatualizada mentiria no CI: com o interim na máquina, ela tem de
    ser o recorte exato dele (`py -3.12 -m scripts.gera_fixture_ci` regera)."""
    if not (INTERIM_REAL / match_id / "kills.parquet").exists():
        pytest.skip("sem o interim real nesta máquina")
    for nome in EVENTOS:
        real = INTERIM_REAL / match_id / f"{nome}.parquet"
        if real.exists():
            assert pl.read_parquet(DESTINO / match_id / f"{nome}.parquet").equals(pl.read_parquet(real)), nome
    assert pl.read_parquet(DESTINO / match_id / "ticks.parquet").equals(
        pl.read_parquet(INTERIM_REAL / match_id / "ticks.parquet", columns=COLUNAS_DE_TICKS))
