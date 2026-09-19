"""
Degraus 1, 2 e 4 da escada de validação (scripts/escada_validacao.py): contagem
contra a HLTV tem que bater EXATO.

Se um destes falhar, não olhe o rating: rating próximo com contagem errada é
coincidência.
"""
from __future__ import annotations

import polars as pl
import pytest

from scripts.escada_validacao import PROCESSED, REF, TOLERANCIA_ADR, contagens

# ADRs que ficam abaixo do oficial depois da correção do dano no mesmo tick, e
# que nenhuma regra testada explica (dano em companheiro, corte do freeze time,
# cauda do round). Todos ABAIXO, no máximo 0,76 de ADR. Um caso novo aqui é
# regressão; um destes passando a bater é para tirar da lista.
ADR_SEM_EXPLICACAO = {
    ("match_42", "Spinx"), ("match_33", "Jimpphat"), ("match_47", "torzsi"),
    ("match_46", "ZywOo"), ("match_47", "apEX"), ("match_23", "ZywOo"),
    ("match_39", "w0nderful"), ("match_48", "apEX"), ("match_53", "apEX"),
}


@pytest.fixture(scope="module")
def c():
    if not (REF / "hltv_placar.json").exists() or not PROCESSED.exists():
        pytest.skip("sem referência oficial ou sem dados processados")
    return contagens()


def test_rounds_kills_e_mortes_batem_exato_com_a_hltv(c):
    por_partida = c.unique("match_id")
    assert (por_partida["rounds"] == por_partida["rounds_oficial"]).all()
    errados = c.filter((c["kills"] != c["kills_oficial"]) | (c["mortes"] != c["mortes_oficial"]))
    assert errados.height == 0, errados.select("match_id", "nome", "kills_oficial", "kills", "mortes_oficial", "mortes")


def test_adr_bate_no_arredondamento_fora_dos_casos_conhecidos(c):
    fora = {(r["match_id"], r["nome"]) for r in c.iter_rows(named=True)
            if abs(r["adr"] - r["adr_oficial"]) > TOLERANCIA_ADR}
    assert fora - ADR_SEM_EXPLICACAO == set(), f"ADR novo fora do oficial: {sorted(fora - ADR_SEM_EXPLICACAO)}"
    assert c.height >= 400


def test_aberturas_multikills_e_headshots_batem_exato_com_a_hltv():
    """Degrau 4, pela página 'Detailed stats' (por série)."""
    from scripts.escada_validacao import detalhado

    d = detalhado()
    if d.height == 0:
        pytest.skip("sem data/reference/hltv_detalhado.json")
    errados = d.filter(pl.col("nosso") != pl.col("oficial"))
    assert errados.height == 0, errados
