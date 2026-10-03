"""Textos da página da partida (auditoria, item 5.2)."""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from metrics.formatting import format_pct_par

RAIZ = Path(__file__).resolve().parent.parent
PROCESSED = RAIZ / "data" / "processed"
TEMPLATE = (RAIZ / "dashboard" / "web" / "template.html").read_text(encoding="utf-8")


def test_porcentagens_comparadas_que_o_arredondamento_iguala_ganham_uma_casa():
    assert format_pct_par(0.1204, 0.1249) == ("12,0%", "12,5%")
    assert format_pct_par(0.08, 0.12) == ("8%", "12%")
    assert format_pct_par(None, 0.12) == ("—", "12%")


def _textos(v):
    if isinstance(v, dict):
        for x in v.values():
            yield from _textos(x)
    elif isinstance(v, list):
        for x in v:
            yield from _textos(x)
    elif isinstance(v, str):
        yield v


def test_nenhuma_frase_do_corpus_tem_hifen_duplo_nem_porcentagens_iguais_comparadas():
    arquivos = sorted(PROCESSED.glob("match_*/insights.json"))
    if not arquivos:
        pytest.skip("sem o processado")
    for f in arquivos:
        narrativa = json.loads(f.read_text(encoding="utf-8"))["narrative"]
        for t in _textos(narrativa):
            assert " -- " not in t, (f.parent.name, t)
            for m in re.finditer(r"(\d+(?:,\d)?)%[^.]{0,40}?(?:abaixo|acima) d[oa]s? (\d+(?:,\d)?)%", t):
                assert m.group(1) != m.group(2), (f.parent.name, m.group(0))


def test_o_h1_da_partida_e_o_mapa_e_o_placar():
    from scripts.build_web_page import titulo_da_partida
    assert "Uma partida,<br>round a round" not in TEMPLATE
    d = PROCESSED / "match_02"
    if not (d / "web_payload.json").exists():
        pytest.skip("sem o processado da match_02")
    m = json.loads((d / "web_payload.json").read_text(encoding="utf-8"))["match"]
    assert titulo_da_partida(d) == f"Mirage {m['score_a']}–{m['score_b']}"


def test_rotulos_da_mesma_tela_nao_se_repetem_e_os_textos_trocados():
    assert TEMPLATE.count('"Roda o mapa"') == 0      # o grupo de estilo vem do cluster_names
    assert "em quadra" not in TEMPLATE and "faz no mapa" in TEMPLATE
    assert "D.dica_mira" in TEMPLATE
