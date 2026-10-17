"""Pisos de função e a regra de exibição (resposta do Pedro ao material de calibração, decisão 31).

- os pisos respondidos são constantes com a data e o tamanho do corpus;
- o Lurker não vale para quem tem "Abre o round" na mesma partida (no dado e na reamostragem);
- quando o jogador tem mais de um rótulo, a tela mostra UM: o AWPer sempre ganha; sem AWPer, a
  maior margem relativa acima do piso (valor ÷ piso); os outros continuam no dado.
"""
from __future__ import annotations

import numpy as np
import polars as pl

from metrics import player_roles as pr


def _sinais(linhas: list[dict]) -> pl.DataFrame:
    """Sinais mínimos para assign_traits: as colunas das specs, sem as de amostra."""
    base = {spec.column: 0.0 for spec in pr.TRAIT_SPECS}
    base.update({"steamid": 0, "name": "?", "team": "A"})
    return pl.DataFrame([{**base, **r} for r in linhas])


def _titulo(traits: pl.DataFrame, steamid: int) -> str:
    t = pr.ordem_na_tela(traits).filter((pl.col("steamid") == steamid) & (pl.col("ordem") == 1))
    return t["trait"].item()


def test_pisos_respondidos_sao_constantes_com_data_e_corpus():
    pisos = {s.key: s.floor for s in pr.TRAIT_SPECS}
    assert pisos["awp"] == pr.PISO_AWPER == 0.533
    assert pisos["entry"] == pr.PISO_ABRE_O_ROUND == 0.320
    assert pisos["lurk"] == pr.PISO_LURK_RELATIVO == 1.284
    assert pisos["anchor"] == pr.PISO_ANCORA == 0.90
    assert pisos["trade"] == pr.PISO_SEGUNDO_HOMEM == 0.350
    assert pisos["frag"] == pr.PISO_PRINCIPAL_FRAGGER == 85.0
    assert pr.DATA_DOS_PISOS == "2026-10-17"
    assert (pr.PARTIDAS_DOS_PISOS, pr.JOGADOR_PARTIDAS_DOS_PISOS) == (52, 520)


def test_ancora_abaixo_de_090_nao_e_mais_ancora():
    sinais = _sinais([{"steamid": 1, "name": "a", "never_left_share": 0.85},
                      {"steamid": 2, "name": "b", "never_left_share": 0.10}])
    assert "anchor" not in pr.assign_traits(sinais)["trait"].to_list()
    sinais = sinais.with_columns(pl.Series("never_left_share", [0.90, 0.10]))
    assert pr.assign_traits(sinais).filter(pl.col("trait") == "anchor")["steamid"].to_list() == [1]


def test_lurker_com_abre_o_round_na_mesma_partida_fica_so_com_abre_o_round():
    """Ficar longe do time por entrar na frente não é lurkar (xertioN, apEX)."""
    sinais = _sinais([
        {"steamid": 1, "name": "entry", "first_contact_share": 0.45, "off_team_relativo": 2.0},
        {"steamid": 2, "name": "outro", "first_contact_share": 0.10, "off_team_relativo": 0.5},
    ])
    t = pr.assign_traits(sinais)
    assert t.filter(pl.col("steamid") == 1)["trait"].to_list() == ["entry"]
    # sem o "Abre o round", o mesmo número de lurk vale o rótulo
    so_lurk = sinais.with_columns(pl.Series("first_contact_share", [0.25, 0.10]))
    assert pr.assign_traits(so_lurk).filter(pl.col("steamid") == 1)["trait"].to_list() == ["lurk"]


def test_a_exclusao_do_lurker_vale_reamostragem_a_reamostragem():
    """Na reamostragem, o lurk só conta na amostra em que o "Abre o round" não saiu."""
    um = np.ones((2, 2))
    # jogador 0 lidera os dois; na amostra 0 ele abre 40% (entry), na amostra 1, 20% (não)
    entry = (np.array([[4.0, 2.0], [1.0, 1.0]]), np.full((2, 2), 10.0), np.full((2, 2), 10.0))
    lurk = (np.array([[8.0, 8.0], [1.0, 1.0]]), np.full((2, 2), 2.0), np.full((2, 2), 10.0))
    sinais = {"times": ["A", "A"], "entry": entry, "lurk": lurk}
    ok = pr._qualificados(sinais, lambda m: m * um)
    assert ok["entry"][0].tolist() == [True, False]
    assert ok["lurk"][0].tolist() == [False, True]


def test_awper_que_tambem_abre_o_round_aparece_como_awper():
    """O ZywOo que passa em "Abre o round" aparece como AWPer, mesmo com margem maior no entry."""
    sinais = _sinais([
        {"steamid": 1, "name": "ZywOo", "awp_share": 0.60, "first_contact_share": 0.60},
        {"steamid": 2, "name": "outro", "awp_share": 0.10, "first_contact_share": 0.10},
    ])
    t = pr.assign_traits(sinais)
    assert sorted(t.filter(pl.col("steamid") == 1)["trait"].to_list()) == ["awp", "entry"]  # nada some
    assert (0.60 / pr.PISO_ABRE_O_ROUND) > (0.60 / pr.PISO_AWPER)
    assert _titulo(t, 1) == "awp"


def test_dois_rotulos_sem_awper_mostram_o_de_maior_margem():
    # Abre o round 0,40 / 0,32 = 1,25; Principal fragger 110 / 85 = 1,29 -> o fragger ganha,
    # embora o "Abre o round" tenha prioridade menor (que era a regra antiga do título)
    sinais = _sinais([
        {"steamid": 1, "name": "a", "first_contact_share": 0.40, "adr": 110.0},
        {"steamid": 2, "name": "b", "first_contact_share": 0.10, "adr": 60.0},
    ])
    t = pr.assign_traits(sinais)
    assert _titulo(t, 1) == "frag"
    ordem = pr.ordem_na_tela(t).filter(pl.col("steamid") == 1).sort("ordem")["trait"].to_list()
    assert ordem == ["frag", "entry"]
    # com 0,50 de abertura (1,56 contra os 1,29 do ADR), a abertura ganha
    t = pr.assign_traits(sinais.with_columns(pl.Series("first_contact_share", [0.50, 0.10])))
    assert _titulo(t, 1) == "entry"


def test_empate_de_margem_desempata_pela_prioridade():
    sinais = _sinais([
        {"steamid": 1, "name": "a", "first_contact_share": pr.PISO_ABRE_O_ROUND * 1.5,
         "adr": pr.PISO_PRINCIPAL_FRAGGER * 1.5},
        {"steamid": 2, "name": "b"},
    ])
    assert _titulo(pr.assign_traits(sinais), 1) == "entry"


def test_o_cartao_ordena_os_rotulos_pela_ordem_da_tela():
    """O template monta o título e as características na ordem que vem do Python."""
    from pathlib import Path
    tpl = (Path(__file__).resolve().parents[1] / "dashboard" / "web" / "template.html").read_text(encoding="utf-8")
    assert "a.ordem != null ? a.ordem - b.ordem" in tpl
