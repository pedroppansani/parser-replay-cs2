"""Cartão 27: o nome de exibição do evento vem de uma tabela pequena e versionada (data/reference/eventos.json), não de exceção no código."""
from __future__ import annotations

import json
from pathlib import Path

from scripts.build_web_page import nome_do_evento, origem_da_partida

RAIZ = Path(__file__).resolve().parent.parent
TABELA = json.loads((RAIZ / "data" / "reference" / "eventos.json").read_text(encoding="utf-8"))["eventos"]


def _partidas():
    return json.loads((RAIZ / "data" / "manifest.json").read_text(encoding="utf-8")).get("partidas", {})


def test_todo_evento_do_corpus_esta_na_tabela_e_a_tabela_nao_tem_sobra():
    usados = {v["evento"] for v in _partidas().values() if v.get("evento")}
    assert usados <= set(TABELA), f"evento sem nome de exibição em data/reference/eventos.json: {sorted(usados - set(TABELA))}"
    assert set(TABELA) <= usados, f"nome na tabela que nenhuma partida usa: {sorted(set(TABELA) - usados)}"


def test_os_nomes_saem_com_acento_e_como_a_hltv_escreve():
    assert nome_do_evento("iem-krakw-2026") == "IEM Kraków 2026"
    assert nome_do_evento("pgl-cluj-napoca-2026") == "PGL Cluj-Napoca 2026"
    assert nome_do_evento("starladder-budapest-major-2025") == "StarLadder Budapest Major 2025"
    assert nome_do_evento("blast-open-lisbon-2025") == "BLAST Open Lisbon 2025"
    assert all(n == n.strip() and "  " not in n for n in TABELA.values())


def test_a_origem_da_partida_usa_a_tabela_e_a_faceit_continua_faceit():
    for mid, v in _partidas().items():
        if v.get("origem") == "faceit":
            assert origem_da_partida(mid) == "FACEIT"
        elif v.get("evento"):
            assert origem_da_partida(mid) == TABELA[v["evento"]]
    kr = next(m for m, v in _partidas().items() if v.get("evento") == "iem-krakw-2026")
    assert "Kraków" in origem_da_partida(kr) and "Krakw" not in origem_da_partida(kr)
