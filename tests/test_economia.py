"""
Ajuste de economia do rating pelo corpus (metrics/economia.py).
"""
from __future__ import annotations

import polars as pl
import pytest

from metrics.economia import (
    K_ENCOLHIMENTO,
    ajusta_tabela,
    carrega_tabela,
    compra_por_jogador,
)
from metrics.rating import CelulasComFallback


def _confrontos(celulas: list[tuple[str, str, bool, str, bool, int, int]]) -> pl.DataFrame:
    """(lado, grupo, colete, grupo dele, colete dele, vitórias, derrotas)."""
    linhas = []
    for lado, g, c, gd, cd, v, d in celulas:
        linhas += [{"lado": lado, "grupo": g, "colete": c, "grupo_dele": gd, "colete_dele": cd, "venceu": True}] * v
        linhas += [{"lado": lado, "grupo": g, "colete": c, "grupo_dele": gd, "colete_dele": cd, "venceu": False}] * d
    return pl.DataFrame(linhas)


def test_a_classe_e_a_arma_mais_cara_mais_o_colete():
    compra = pl.DataFrame([
        {"round_num": 1, "steamid": 1, "inventory": ["Karambit", "Glock-18", "AK-47"], "armor_value": 100},
        {"round_num": 1, "steamid": 2, "inventory": ["Karambit", "USP-S"], "armor_value": 0},
    ])
    c = compra_por_jogador(compra).sort("steamid")
    assert c["grupo"].to_list() == ["rifle_t1", "pistola_inicial"]
    assert c["colete"].to_list() == [True, False]


def test_celula_com_pouca_amostra_encolhe_para_o_nivel_de_cima():
    """Três vitórias em três casos não é 100%: fica perto da célula sem colete."""
    conf = _confrontos([
        ("t", "rifle_t1", True, "pistola_inicial", False, 3, 0),     # célula rara
        ("t", "rifle_t1", True, "pistola_inicial", True, 40, 40),    # mesma, com colete do outro lado
        ("ct", "rifle_t1", True, "rifle_t1", True, 50, 50),
    ])
    t = ajusta_tabela(conf)
    rara = t["celulas"]["t||rifle_t1|colete||pistola_inicial|sem_colete"]
    assert rara["taxa_crua"] == 1.0
    assert rara["taxa"] < 0.75 and rara["amostra_fraca"]
    # o peso da própria célula é n / (n + K)
    assert K_ENCOLHIMENTO == 20.0


def test_sem_a_celula_com_colete_cai_na_celula_sem_colete():
    celulas = CelulasComFallback({("t", "rifle_t1", "pistola_inicial"): {"taxa": 0.9, "n": 30}})
    assert celulas.get(("t", "rifle_t1|colete", "pistola_inicial|sem_colete"))["taxa"] == 0.9
    assert celulas.get(("ct", "sniper|colete", "smg_shotgun|colete")) is None


def test_a_tabela_do_corpus_reproduz_os_fatos_de_economia():
    """O que a tabela TEM que mostrar, medido no corpus: rifle x rifle perto de
    50% (a HLTV publicou 48% no lado TR) e o colete mudando de patamar dentro da
    pistola inicial."""
    tabela = carrega_tabela()
    if tabela is None:
        pytest.skip("tabela de economia ainda não ajustada")
    sem = tabela["celulas_sem_colete"]
    rr = sem["t||rifle_t1||rifle_t1"]
    assert rr["n"] > 200 and 0.44 <= rr["taxa_crua"] <= 0.56
    base = tabela["taxa_base_por_lado"]
    assert 0.40 < base["t"] < 0.60 and abs(base["t"] + base["ct"] - 1.0) < 1e-9
