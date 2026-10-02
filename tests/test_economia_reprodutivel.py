"""A tabela de economia gravada tem de ser REPRODUTÍVEL.

`metrics/economia_reference.json` ficou duas semanas com um desempate ao acaso
(gravada em 2026-09-19, antes da correção de determinismo, e nunca regerada):
o código já era determinístico, mas nada conferia que o ARQUIVO era o que o
código produz. Regerar do corpus tem de dar exatamente o que está gravado; se
alguém mudar o código ou o corpus sem regerar, este teste falha.

Pulado sem `data/interim/` (a tabela sai da compra de cada round).
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from metrics.economia import REFERENCIA_ECONOMIA, ajusta_tabela

RAIZ = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="module")
def regerada():
    if not (RAIZ / "data" / "interim" / "match_23" / "compra.parquet").exists():
        pytest.skip("sem data/interim/")
    from scripts.fit_economia import confrontos_do_corpus
    return json.loads(json.dumps(ajusta_tabela(confrontos_do_corpus())))


def test_a_tabela_de_economia_gravada_e_a_que_o_codigo_produz(regerada):
    gravada = json.loads(REFERENCIA_ECONOMIA.read_text(encoding="utf-8"))
    for chave, valor in regerada.items():
        assert gravada.get(chave) == valor, (
            f"'{chave}' da economia gravada difere da regerada: rode py -3.12 -m scripts.fit_economia")


def test_a_tabela_diz_a_regra_de_desempate_e_o_commit_que_a_gerou():
    gravada = json.loads(REFERENCIA_ECONOMIA.read_text(encoding="utf-8"))
    assert gravada.get("regra_de_desempate") == "empate dividido entre as classes empatadas"
    assert gravada.get("gerada_por", {}).get("commit")
