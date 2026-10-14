"""Fase 15, granada desenhada V3 (§19.7 e §19.1 do design; decisão 45): o A25 medido no canvas REAL do map_core.js
contra os radares locais, o tracejado em px de tela nos dois anéis e o carimbo no lugar do alfa de 85%."""
from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("playwright.sync_api")

from scripts.design import mede_granada_real as mg  # noqa: E402

MAP_CORE = (Path(__file__).resolve().parent.parent / "dashboard" / "web" / "map_core.js").read_text(encoding="utf-8")


def test_a25_a_desenhada_se_separa_da_real_em_todo_mapa_com_partida():
    """Média dos quatro tipos >= 4,5 e nenhum tipo < 3,5, em 1440 e 375 px, 1x e 2x (modo "mesmo tamanho")."""
    com_partida = mg.mapas_com_partida()
    assert {"mirage", "dust2"} <= com_partida
    linhas = mg.mede([m for m in mg.radares() if m in com_partida], posicoes=16)
    resumo = mg.resumo(linhas)
    assert len(resumo) == len(com_partida) * len(mg.ESCALAS) * len(mg.DENSIDADES)
    reprovam = {(r["mapa"], r["largura"], r["densidade"]): (round(r["media"], 2), r["pior_tipo"], round(r["pior"], 2))
                for r in resumo if not r["passa"]}
    assert not reprovam, reprovam


def test_o_tracejado_do_anel_e_de_3_5_e_3_px_de_tela_nos_dois_aneis():
    from scripts.design.mede_anel_tracejado import passo_de_tela
    passos = passo_de_tela()
    assert len(passos) == len(mg.ESCALAS) * len(mg.DENSIDADES)
    assert all(p["mesmo_passo"] and p["passo_de_tela"] for p in passos), passos


def test_o_alfa_de_85_saiu_e_o_carimbo_e_em_px_de_tela():
    assert "ALFA_GRANADA_DESENHADA" not in MAP_CORE and "globalAlpha *=" not in MAP_CORE.split("function nadeGlyph")[1].split("function carimboDaDesenhada")[0]
    assert "TRACEJADO_DO_DESENHO = [3.5, 3]" in MAP_CORE
    assert "CARIMBO_LADO_TELA = 4" in MAP_CORE
