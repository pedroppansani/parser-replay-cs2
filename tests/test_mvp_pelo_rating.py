"""MVP = maior rating da partida, com empate declarado dentro do erro do rating (item 4.6)."""
from __future__ import annotations

import json
from pathlib import Path

import polars as pl
import pytest

import metrics.match_highlights as mh
from leitura.narrativa import historia_mvp

PROCESSED = Path(__file__).resolve().parent.parent / "data" / "processed"


def _players(ratings, adrs=None):
    n = len(ratings)
    adrs = adrs or [80.0] * n
    return pl.DataFrame({
        "steamid": [1000 + i for i in range(n)], "name": [f"j{i}" for i in range(n)],
        "team": ["A"] * n, "adr": adrs, "kast_pct": [70.0] * n,
        "opening_kills": [1] * n, "clutches": [0] * n, "rating": ratings,
    }).with_columns(pl.col("steamid").cast(pl.UInt64))


def test_o_mvp_e_o_maior_rating_mesmo_sem_liderar_o_adr():
    mvp = mh.mvp_da_partida(_players([1.10, 1.40, 0.90], adrs=[120.0, 70.0, 60.0]), {}, margem=0.08)
    assert mvp["name"] == "j1" and mvp["rating_texto"] == "1,40" and mvp["empatados"] == []
    assert historia_mvp(mvp).startswith("j1 foi o MVP, com rating 1,40 contra 1,10 de j0")


def test_dentro_da_margem_e_empate_declarado():
    mvp = mh.mvp_da_partida(_players([1.30, 1.25, 1.21, 0.9]), {}, margem=0.08)
    assert mvp["name"] == "j0"
    assert [e["name"] for e in mvp["empatados"]] == ["j1"]          # 0,09 de distância não empata
    assert historia_mvp(mvp).startswith(
        "j0 teve o maior rating (1,30), empatado com j1 (1,25) dentro do erro do rating (0,080)")


def test_empate_exato_desempata_pelo_steamid_e_nao_pela_ordem_de_entrada():
    a = mh.mvp_da_partida(_players([1.2, 1.2]), {}, margem=0.08)
    b = mh.mvp_da_partida(_players([1.2, 1.2]).reverse(), {}, margem=0.08)
    assert a["steamid"] == b["steamid"] == 1000


def test_sem_rating_nao_ha_mvp():
    assert mh.mvp_da_partida(_players([None, None]), {}, margem=0.08) is None
    assert mh.mvp_da_partida(_players([1.0]).drop("rating"), {}, margem=0.08) is None


def test_a_margem_e_o_erro_fora_da_amostra_gravado():
    dado = json.loads(mh.ARQUIVO_DA_VALIDACAO.read_text(encoding="utf-8"))
    assert mh.margem_de_ruido_do_rating() == dado["deixa_uma_partida_fora"]["erro_medio"]
    assert not hasattr(mh, "PESOS_MVP")


def test_no_corpus_o_card_e_a_landing_mostram_o_maior_rating():
    arquivos = sorted(PROCESSED.glob("match_*/insights.json"))
    if not arquivos:
        pytest.skip("sem o processado")
    from scripts.build_site import match_summary
    for f in arquivos:
        d = json.loads(f.read_text(encoding="utf-8"))
        maior = max(p["rating"] for p in d["players"])
        assert d["mvp_card"]["rating"] == maior, f.parent.name
        assert match_summary(f.parent.name)["mvp"] == d["mvp_card"]["name"], f.parent.name
