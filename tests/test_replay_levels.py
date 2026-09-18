"""
Andares no replay (Nuke, Vertigo, Train).

Esta exportação já sumiu uma vez sem ninguém perceber: o painel continuou com o
código de andar pronto, mas o export_replay deixou de mandar `levels` e `lv`, e
as guardas do JavaScript simplesmente não desenhavam nada. Os testes travam o
lado da exportação.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.export_replay import level_of, map_levels

PROCESSED = Path(__file__).resolve().parent.parent / "data" / "processed"


def test_nuke_separa_os_andares_pelo_corte_oficial():
    levels = map_levels("de_nuke")
    assert [lv["name"] for lv in levels] == ["default", "lower"]
    # corte do overview da Valve: Z = -495
    assert level_of(-416.0, levels) == 0  # BombsiteA / Outside
    assert level_of(-704.0, levels) == 1  # BombsiteB


def test_mapa_de_um_andar_nao_tem_corte():
    levels = map_levels("de_mirage")
    assert len(levels) == 1
    assert level_of(-900.0, levels) == 0


def _nuke_replays():
    out = []
    for meta in sorted(PROCESSED.glob("*/match_meta.json")):
        if json.loads(meta.read_text(encoding="utf-8")).get("map_name") == "de_nuke":
            out.append(meta.parent / "replay.json")
    return [p for p in out if p.exists()]


@pytest.mark.skipif(not _nuke_replays(), reason="nenhuma partida de Nuke processada")
def test_replay_da_nuke_exporta_andar_e_callout():
    """O andar de baixo tem que conter o B — e não o A."""
    replay = json.loads(_nuke_replays()[0].read_text(encoding="utf-8"))
    assert len(replay["levels"]) == 2

    lower, upper = set(), set()
    for r in replay["rounds"]:
        for p in r["players"]:
            assert "lv" in p and "p" in p
            for lv, pi, alive in zip(p["lv"], p["p"], p["alive"]):
                if alive and pi >= 0:
                    (lower if lv == 1 else upper).add(r["places"][pi])

    assert "BombsiteB" in lower
    assert "BombsiteA" in upper
    assert "BombsiteA" not in lower
