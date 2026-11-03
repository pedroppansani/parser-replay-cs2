"""As âncoras dos nomes de lugar no mapa (Fase M, decisão 52): metrics/lugares.rotulos."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from metrics.lugares import ANCORAS_POR_LUGAR, lugar, para_a_prancheta, para_o_replay, rotulos

RAIZ = Path(__file__).resolve().parents[1]
MAPAS = sorted(p.stem for p in (RAIZ / "data" / "lugares").glob("de_*.json"))


def _tabela(mapa):
    return json.loads((RAIZ / "data" / "lugares" / f"{mapa}.json").read_text(encoding="utf-8"))


def test_ha_tabelas_versionadas_para_conferir():
    assert len(MAPAS) >= 7


@pytest.mark.parametrize("mapa", MAPAS)
def test_cada_ancora_cai_dentro_da_propria_regiao_e_com_o_nome_da_tabela(mapa):
    tab = _tabela(mapa)
    saida = rotulos(tab)
    assert len(saida) == len(tab["andares"])
    for andar, lugares in enumerate(saida):
        for ix, pontos in lugares:
            assert 1 <= len(pontos) <= ANCORAS_POR_LUGAR
            for x, y in pontos:
                assert lugar(tab, x, y, andar) == tab["nomes"][ix], (mapa, andar, tab["nomes"][ix], x, y)


@pytest.mark.parametrize("mapa", MAPAS)
def test_so_nomes_da_tabela_e_sempre_o_mesmo_resultado(mapa):
    tab = _tabela(mapa)
    a, b = rotulos(tab), rotulos(json.loads(json.dumps(tab)))
    assert a == b
    usados = {ix for lugares in a for ix, _ in lugares}
    assert usados <= set(range(len(tab["nomes"])))      # nenhum nome inventado
    # cada nome que a tabela tem em algum andar ganha ao menos uma âncora
    assert usados == {i for andar in tab["andares"] for rle in andar.values() for i in rle[1::3]}


def test_a_primeira_ancora_e_a_mais_funda_e_as_outras_ficam_separadas():
    # região em L: 16 x 3 células, com uma perna de 3 x 2 em cima; a mais funda é o miolo da parte larga
    tab = {"lado": 8, "nomes": ["Longo"], "andares": [{
        "0": [0, 0, 3], "1": [0, 0, 3], "2": [0, 0, 16], "3": [0, 0, 16], "4": [0, 0, 16]}]}
    (andar,) = rotulos(tab)
    (ix, pontos), = andar
    assert ix == 0 and pontos[0][1] in (28.0, 20.0) and len(pontos) >= 2
    for i, a in enumerate(pontos):
        for b in pontos[i + 1:]:
            assert max(abs(a[0] - b[0]), abs(a[1] - b[1])) >= 6 * 8


def test_sem_tabela_nao_ha_nada_a_desenhar():
    assert rotulos(None) == [] and para_a_prancheta(None) is None and para_o_replay(None) is None


def test_o_replay_leva_so_os_nomes_e_a_prancheta_a_tabela_inteira():
    tab = _tabela("de_mirage")
    rep, pr = para_o_replay(tab), para_a_prancheta(tab)
    assert set(rep) == {"nomes", "rotulos"} and rep["nomes"] == tab["nomes"]
    assert pr["andares"] == tab["andares"] and pr["rotulos"] == rep["rotulos"]
    assert len(json.dumps(rep)) < 4_000          # cabe folgado na página
