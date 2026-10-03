"""Round sem contato fica nulo na tabela (auditoria, item 4.7)."""
from __future__ import annotations

from pathlib import Path

import polars as pl
import pytest

from clustering.playstyle import FEATURE_COLUMNS, GLOBAL_MODEL_VERSION, load_global_model

PROCESSED = Path(__file__).resolve().parent.parent / "data" / "processed"


def test_no_corpus_sem_contato_e_nulo_e_nao_um_valor_inventado():
    arquivos = sorted(PROCESSED.glob("match_*/cluster_features.parquet"))
    if not arquivos:
        pytest.skip("sem o processado")
    for f in arquivos:
        t = pl.read_parquet(f)
        assert (t["sem_contato"] == 1.0).to_list() == t["time_of_first_contact_s"].is_null().to_list(), f.parent.name


def test_sem_contato_fica_fora_do_agrupamento_e_o_modelo_preenche_com_a_mediana_dele():
    """Como feature, o ARI contra o agrupamento anterior foi 0,652 (abaixo de 0,9)."""
    assert "sem_contato" not in FEATURE_COLUMNS
    modelo = load_global_model()
    if modelo is None:
        pytest.skip("sem o modelo global")
    assert modelo["version"] == GLOBAL_MODEL_VERSION == 2
    assert "time_of_first_contact_s" in modelo["fill_medians"]
