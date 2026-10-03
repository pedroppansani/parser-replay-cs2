"""Uma regra, um lugar (auditoria, item 4.8): janela de trade, troca de lado,
contato e "é o AWPer do time" são definidos uma vez e importados."""
from __future__ import annotations

import re
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
PASTAS = ("metrics", "clustering", "scripts", "parsing")


def _codigo():
    for pasta in PASTAS:
        for f in sorted((RAIZ / pasta).rglob("*.py")):
            yield f.relative_to(RAIZ).as_posix(), f.read_text(encoding="utf-8")


def test_janela_de_trade_e_troca_de_lado_so_em_constantes():
    # nome de janela de trade (TRADE + WINDOW/JANELA/SEGUNDOS) ou de troca de lado
    padrao = re.compile(r"^\s*([A-Z_]*(TRADE_WINDOW|JANELA_TRADE|SEGUNDOS_TRADE)[A-Z_]*|[A-Z_]*HALFTIME[A-Z_]*"
                        r"|REGULATION_HALF)\s*=\s*\d", re.M)
    achados = [arq for arq, txt in _codigo() if arq != "metrics/constantes.py" and padrao.search(txt)]
    assert not achados, f"constante redefinida fora de metrics/constantes.py: {achados}"


def test_contato_e_calculado_num_lugar_so():
    """O agrupamento por (round, jogador) do primeiro dano mora em metrics/contato.py."""
    padrao = re.compile(r'pl\.col\("tick"\)\.min\(\)\.alias\("(first_contact_tick|tick_contato)"\)')
    achados = [arq for arq, txt in _codigo() if arq != "metrics/contato.py" and padrao.search(txt)]
    assert not achados, achados


def test_o_awper_do_time_sai_de_uma_funcao_so():
    padrao = re.compile(r'col\("trait"\)\s*==\s*"awp"')
    achados = [arq for arq, txt in _codigo() if arq != "metrics/player_roles.py" and padrao.search(txt)]
    assert not achados, f"use metrics.player_roles.awpers_do_time: {achados}"


def test_o_card_awper_so_vai_para_o_awper_do_time():
    import polars as pl

    from metrics.match_highlights import _candidatos_comportamentais
    from metrics.archetypes import PAPEIS
    linha = {"steamid": 7, "name": "x", "team": "A", **{f"idx_{p}": None for p in PAPEIS}, "idx_awper": 0.9}
    arq = pl.DataFrame([linha])
    assert [c["funcao"] for c in _candidatos_comportamentais(arq, "A", awpers=set())] == []
    assert [c["funcao"] for c in _candidatos_comportamentais(arq, "A", awpers={7})] == ["awper"]
