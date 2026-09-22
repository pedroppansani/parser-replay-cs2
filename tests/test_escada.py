"""
Degraus 1, 2 e 4 da escada de validação (scripts/escada_validacao.py): contagem
contra a HLTV tem que bater EXATO.

Se um destes falhar, não olhe o rating: rating próximo com contagem errada é
coincidência.
"""
from __future__ import annotations

import polars as pl
import pytest

from scripts.escada_validacao import INTERIM, PROCESSED, REF, TOLERANCIA_ADR, contagens


def _sem_interim() -> bool:
    """O interim não é versionado (data/interim/ no .gitignore): num clone limpo
    estes testes não têm o que comparar e são pulados, não quebrados."""
    return not any(INTERIM.glob("*/kills.parquet")) if INTERIM.exists() else True

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
    if not (REF / "hltv_placar.json").exists() or not PROCESSED.exists() or _sem_interim():
        pytest.skip("sem referência oficial, dados processados ou interim")
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

    if _sem_interim():
        pytest.skip("sem data/interim (não versionado)")
    d = detalhado()
    if d.height == 0:
        pytest.skip("sem data/reference/hltv_detalhado.json")
    # o clutch ainda não é exato (67/80, ver CLAUDE.md 22j): fica fora desta trava
    errados = d.filter((pl.col("campo") != "clutches") & (pl.col("nosso") != pl.col("oficial")))
    assert errados.height == 0, errados


def test_transcricao_por_mapa_confere_sem_usar_o_nosso_numero():
    """Os Detailed stats por mapa (data/reference/brutos/) passam nas três
    conferências do importador: aberturas fecham por mapa, cada mapa casa com
    UMA partida por mapa + elenco + rounds, e o rating colado é o registrado.
    Uma transcrição nova com erro de digitação falha aqui antes de virar gabarito."""
    from scripts import importa_detalhado_mapas as imp

    d = imp.le_brutos()
    if d.height == 0:
        pytest.skip("sem transcrição por mapa")
    assert imp.confere_transcricao(d) == []
    casamento, erros = imp.casa_com_o_corpus(d)
    assert erros == []
    assert len(casamento) == d.select("serie", "mapa").unique().height
    assert imp.confere_rating(d, casamento) == []
