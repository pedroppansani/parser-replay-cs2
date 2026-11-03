"""As âncoras dos nomes de lugar no mapa (Fase M, decisão 52): metrics/lugares.rotulos."""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from metrics.lugares import ANCORAS_POR_LUGAR, lugar, para_a_prancheta, para_o_replay, rotulos, texto_do_lugar

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
    assert set(rep) == {"nomes", "textos", "rotulos"} and rep["nomes"] == tab["nomes"]
    assert pr["andares"] == tab["andares"] and pr["rotulos"] == rep["rotulos"]
    assert len(json.dumps(rep)) < 4_000          # cabe folgado na página


def _todos_os_nomes():
    return sorted({n for m in MAPAS for n in _tabela(m)["nomes"]})


def test_o_texto_do_lugar_separa_as_palavras_pelas_maiusculas_do_dado_e_o_of_colado():
    esperado = {
        "CTSpawn": "CT SPAWN", "TSpawn": "T SPAWN", "SnipersNest": "SNIPERS NEST", "TSideLower": "T SIDE LOWER",
        "ARamp": "A RAMP", "BDoors": "B DOORS", "BombsiteA": "BOMBSITE A", "MIDDLE": "MIDDLE", "Truck": "TRUCK",
        "Roof": "ROOF", "HutRoof": "HUT ROOF",
        # o "of" minúsculo colado entre uma minúscula e uma maiúscula (escolha do Pedro, 2026-11-03): só estes três nomes
        "TopofMid": "TOP OF MID", "BackofB": "BACK OF B", "BackofA": "BACK OF A",
    }
    for nome, texto in esperado.items():
        assert texto_do_lugar(nome) == texto, nome


def test_o_texto_so_acrescenta_espaco_as_letras_sao_as_do_dado():
    for nome in _todos_os_nomes():
        texto = texto_do_lugar(nome)
        assert texto.replace(" ", "") == nome.upper(), (nome, texto)       # nada traduzido, inventado nem trocado
        assert "  " not in texto and texto == texto.strip()


def test_a_regra_do_of_muda_so_esses_tres_nomes_e_nenhum_por_engano():
    def so_maiusculas(n):
        n = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", n)
        n = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1 \2", n)
        return n.upper()
    mudados = {n for n in _todos_os_nomes() if texto_do_lugar(n) != so_maiusculas(n)}
    assert mudados == {"TopofMid", "BackofB", "BackofA"}, mudados


@pytest.mark.parametrize("mapa", MAPAS)
def test_as_paginas_levam_o_texto_de_cada_nome(mapa):
    tab = _tabela(mapa)
    for pagina in (para_o_replay(tab), para_a_prancheta(tab)):
        assert pagina["textos"] == [texto_do_lugar(n) for n in tab["nomes"]] and len(pagina["textos"]) == len(pagina["nomes"])


def test_a_tabela_do_mapa_e_lida_uma_vez_e_mapa_sem_tabela_e_none():
    from metrics.lugares import tabela_do_mapa
    assert tabela_do_mapa("de_mirage") is tabela_do_mapa("de_mirage") and tabela_do_mapa("de_mirage")["lado"]
    assert tabela_do_mapa("de_train") is None and tabela_do_mapa("de_cache") is None
