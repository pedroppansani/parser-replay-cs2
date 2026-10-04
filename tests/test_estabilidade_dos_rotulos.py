"""Rótulos com amostra mínima e estabilidade medida (auditoria, item 4.5)."""
from __future__ import annotations

from pathlib import Path

import polars as pl
import pytest

import metrics.player_roles as pr
import metrics.structural_roles as sr

RAIZ = Path(__file__).resolve().parent.parent
PROCESSED = RAIZ / "data" / "processed"


def _sinais(**colunas) -> pl.DataFrame:
    """Dois jogadores do mesmo time; `colunas` dá o valor de cada um."""
    base = {"steamid": [1, 2], "name": ["a", "b"], "team": ["A", "A"]}
    return pl.DataFrame({**base, **colunas})


def test_segundo_homem_nao_sai_de_uma_kill():
    """Antes: 1 kill, 1 trade = 100% das kills foram trade, e o rótulo saía."""
    poucas = _sinais(trade_share=[1.0, 0.1], total_kills=[1, 20])
    assert pr.assign_traits(poucas).filter(pl.col("trait") == "trade").height == 0
    bastantes = _sinais(trade_share=[0.5, 0.1], total_kills=[pr.MIN_KILLS_PARA_SEGUNDO_HOMEM, 20])
    assert pr.assign_traits(bastantes).filter(pl.col("trait") == "trade")["steamid"].to_list() == [1]


@pytest.mark.parametrize("chave, coluna, valor", [
    ("entry", "first_contact_share", 0.9), ("frag", "adr", 150.0), ("support", "enemy_blind_por_round", 3.0)])
def test_rotulo_por_round_exige_rounds_jogados(chave, coluna, valor):
    extra = {"enemy_blind_seconds": [30.0, 1.0]} if chave == "support" else {}
    poucos = _sinais(**{coluna: [valor, 0.0]}, rounds_jogados=[pr.MIN_ROUNDS_PARA_ROTULO - 1, 20], **extra)
    assert pr.assign_traits(poucos).filter(pl.col("trait") == chave).height == 0
    bastantes = _sinais(**{coluna: [valor, 0.0]}, rounds_jogados=[pr.MIN_ROUNDS_PARA_ROTULO, 20], **extra)
    assert pr.assign_traits(bastantes).filter(pl.col("trait") == chave)["steamid"].to_list() == [1]


def test_ancora_exige_o_minimo_de_rounds_do_lado():
    """Antes: "não rotacionou em 100% dos rounds de CT" saía de 1 round de CT."""
    assert pr.MIN_ROUNDS_DE_CT_PARA_ANCORA == sr.MIN_ROUNDS_POR_LADO
    poucos = _sinais(never_left_share=[1.0, 0.2], n_rounds_ct=[sr.MIN_ROUNDS_POR_LADO - 1, 12])
    assert pr.assign_traits(poucos).filter(pl.col("trait") == "anchor").height == 0
    bastantes = _sinais(never_left_share=[1.0, 0.2], n_rounds_ct=[sr.MIN_ROUNDS_POR_LADO, 12])
    assert pr.assign_traits(bastantes).filter(pl.col("trait") == "anchor")["steamid"].to_list() == [1]


def test_suporte_e_medido_por_round_e_nao_pelo_total():
    """24 s em 30 rounds (0,8 por round) passava do piso de 20 s no total."""
    assert pr.PISO_SUPORTE_POR_ROUND == pytest.approx(20.0 / 21)
    longa = _sinais(enemy_blind_por_round=[24.0 / 30, 0.1], enemy_blind_seconds=[24.0, 3.0], rounds_jogados=[30, 30])
    assert pr.assign_traits(longa).filter(pl.col("trait") == "support").height == 0
    curta = _sinais(enemy_blind_por_round=[24.0 / 20, 0.1], enemy_blind_seconds=[24.0, 2.0], rounds_jogados=[20, 20])
    linha = pr.assign_traits(curta).filter(pl.col("trait") == "support").row(0, named=True)
    assert linha["steamid"] == 1 and linha["evidence"] == "24s de cegueira imposta a inimigos"


def _partida(nome: str):
    from metrics.player_roles import entradas_da_partida_processada as partida
    d = PROCESSED / nome
    if not (d / "player_roles.parquet").exists():
        pytest.skip(f"sem o processado da {nome}")
    return partida(d)


@pytest.mark.parametrize("nome", ["match_01", "match_14", "match_40"])
def test_a_regra_por_somas_da_os_mesmos_rotulos_da_partida(nome):
    """A reamostragem só mede a regra de verdade se, sem reamostrar, der o mesmo."""
    outputs, features, signals, team_of = _partida(nome)
    tracos = pr.assign_traits(signals)
    oficiais = set(zip(tracos["steamid"].to_list(), tracos["trait"].to_list()))
    assert pr.rotulos_na_partida_inteira(outputs, features, signals, team_of) == oficiais
    gravados = pl.read_parquet(PROCESSED / nome / "player_traits.parquet")
    assert set(zip(gravados["steamid"].to_list(), gravados["trait"].to_list())) == oficiais


def test_a_estabilidade_e_a_mesma_em_duas_execucoes_e_fica_entre_0_e_1():
    outputs, features, signals, team_of = _partida("match_01")
    a = pr.estabilidade_dos_rotulos(outputs, features, signals, team_of)
    b = pr.estabilidade_dos_rotulos(outputs, features, signals, team_of)
    assert a.equals(b) and a.height > 0
    assert a["estabilidade"].min() > 0 and a["estabilidade"].max() <= 1


def test_o_processado_grava_a_estabilidade_e_marca_a_tendencia():
    d = PROCESSED / "match_01"
    if not (d / "player_traits.parquet").exists():
        pytest.skip("sem o processado da match_01")
    tracos = pl.read_parquet(d / "player_traits.parquet")
    assert tracos["estabilidade"].null_count() == 0
    assert (tracos["tendencia"] == (tracos["estabilidade"] < pr.LIMIAR_DE_TENDENCIA)).all()
    papeis = pl.read_parquet(d / "player_roles.parquet")
    sem_rotulo = papeis.filter(pl.col("role").is_null())
    assert not sem_rotulo["role_tendencia"].any()


def test_o_texto_da_tendencia_sai_do_python():
    assert pr.LIMIAR_DE_TENDENCIA == 0.70
    assert pr.rotulo_exibido("Lurker", True) == "Lurker (tendência)"
    assert pr.rotulo_exibido("Lurker", False) == "Lurker" and pr.rotulo_exibido(None, True) is None
    assert pr.evidencia_exibida("x", 0.9, False) == "x"
    assert pr.evidencia_exibida("x", 0.456, True) == (
        "x · tendência: o rótulo se mantém em 46% das reamostragens dos rounds")


# --- função dominante acima do acaso: pronta e desligada (decisão do Pedro) ---

def test_a_chance_ao_acaso_e_a_cauda_da_binomial():
    assert sr.funcoes_do_lado("ct") == 4 and sr.funcoes_do_lado("t") == 5
    assert sr.chance_ao_acaso(1, 1, "t") == pytest.approx(0.2)
    assert sr.chance_ao_acaso(2, 2, "ct") == pytest.approx(1 / 16)
    assert sr.chance_ao_acaso(1, 10, "t") == pytest.approx(1 - 0.8 ** 10)
    assert sr.chance_ao_acaso(0, 10, "t") == 1.0
    assert sr.chance_ao_acaso(6, 12, "t") < sr.ALFA_FUNCAO_ACIMA_DO_ACASO <= sr.chance_ao_acaso(5, 12, "t")


def test_a_exigencia_esta_desligada_e_so_grava_a_chance():
    from tests.test_structural_roles import _por_round_sintetico
    assert sr.EXIGE_FUNCAO_ACIMA_DO_ACASO is False
    r = sr.resume_por_lado(_por_round_sintetico({"entry": 1}, n=11)).row(0, named=True)
    assert r["funcao"] == "entry" and r["abaixo_do_acaso"] is False
    assert r["chance_ao_acaso"] == pytest.approx(1 - 0.8 ** 11)


def test_ligada_a_funcao_de_um_round_em_onze_deixa_de_ser_dominante(monkeypatch):
    """O caso real: ZywOo na match_14, "AWPer" de TR por 1 round em 11."""
    from tests.test_structural_roles import _por_round_sintetico
    monkeypatch.setattr(sr, "EXIGE_FUNCAO_ACIMA_DO_ACASO", True)
    r = sr.resume_por_lado(_por_round_sintetico({"awper": 1}, n=11)).row(0, named=True)
    assert r["funcao"] is None and r["abaixo_do_acaso"] is True and r["funcao_mais_frequente"] == "awper"
    assert sr.texto_empate(r) == "sem função dominante: AWPer em 1 de 11 rounds, o que não se destaca do acaso"
    r = sr.resume_por_lado(_por_round_sintetico({"entry": 8}, n=12)).row(0, named=True)
    assert r["funcao"] == "entry" and r["abaixo_do_acaso"] is False and sr.texto_empate(r) == ""
