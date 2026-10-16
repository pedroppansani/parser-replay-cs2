"""
Degrau 4b da escada (scripts/escada_validacao.assistencia_flash): assistência de
flash contra a coluna A (f) da HLTV.

O degrau é INFORMATIVO enquanto não bate (decisão 22j, cartão 1 das pendências):
estes testes travam a montagem da comparação (quantas linhas, que oficial, que
número nosso), não a igualdade com a HLTV. Lê só o processado, versionado.
"""
from __future__ import annotations

import polars as pl
import pytest

from scripts.escada_validacao import PROCESSED, REF, assistencia_flash


@pytest.fixture(scope="module")
def af():
    if not (REF / "hltv_detalhado.json").exists() or not PROCESSED.exists():
        pytest.skip("sem referência oficial ou dados processados")
    d = assistencia_flash()
    if d.height == 0:
        pytest.skip("sem Detailed stats")
    return d


def test_compara_as_70_linhas_por_mapa_e_as_80_por_serie(af):
    mapa = af.filter(pl.col("nivel") == "mapa")
    serie = af.filter(pl.col("nivel") == "serie")
    assert mapa.height == 70
    assert mapa.group_by("unidade").len()["len"].to_list() == [10] * 7
    assert serie.height == 80
    assert serie["serie"].n_unique() == 8


def test_oficial_e_o_transcrito(af):
    """A coluna oficial é a A (f) colada, sem passar pelo nosso número."""
    from scripts import importa_detalhado_mapas as imp

    brutos = imp.le_brutos()
    assert af.filter(pl.col("nivel") == "mapa")["oficial"].sum() == brutos["assist_flash"].sum()


def test_nosso_e_o_gravado_e_os_mapas_somam_a_serie(af):
    """O número nosso é o `flash_assists` gravado; nas 3 séries transcritas por
    mapa, os mapas somam exatamente a linha da série (nosso e oficial)."""
    mapa = af.filter(pl.col("nivel") == "mapa")
    for r in mapa.head(3).iter_rows(named=True):
        mid = r["unidade"].split(" ")[0]
        g = pl.read_parquet(PROCESSED / mid / "grenades_summary.parquet")
        assert r["nosso"] == g.filter(pl.col("name").str.to_lowercase() == r["nome"].lower())["flash_assists"][0]
    soma = mapa.group_by("serie", "nome", maintain_order=True).agg(pl.col("nosso").sum(), pl.col("oficial").sum())
    serie = af.filter(pl.col("nivel") == "serie").select("serie", "nome", "nosso", "oficial")
    junto = soma.join(serie, on=["serie", "nome"], suffix="_serie")
    assert junto.height == 30
    assert (junto["nosso"] == junto["nosso_serie"]).all()
    assert (junto["oficial"] == junto["oficial_serie"]).all()


def test_diferenca_e_nosso_menos_oficial(af):
    assert (af["dif"] == af["nosso"] - af["oficial"]).all()
