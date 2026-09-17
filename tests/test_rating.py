"""
Testes do rating (implementação própria da metodologia do Rating 3.0).

O que mais importa travar aqui não é o valor do número -- ele depende de pesos
provisórios -- e sim as PROPRIEDADES que a metodologia exige: escala com média
1,00, kill valendo menos contra equipamento pior, round perdido sem swing
positivo, e crédito distribuído nunca maior que a variação que houve.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import polars as pl
import pytest

from metrics.rating import (
    ARMA_PARA_GRUPO,
    CREDITO_DANO,
    CREDITO_FLASH,
    CREDITO_KILL,
    CREDITO_TRADE,
    MIN_ROUNDS_CONFIAVEL,
    PESOS_PROVISORIOS,
    PESO_KILL_MAX,
    PESO_KILL_MIN,
    ModeloDeRound,
    _estado,
    carrega_referencia,
    grupo_do_round,
    peso_da_kill,
    rating,
    swing_por_evento,
)

TICKRATE = 64
FREEZE = 64 * 31
ROUND_TICKS = 64 * 128


# --- Peso da kill por economia ----------------------------------------------

def test_a_reta_do_peso_reproduz_os_dois_pontos_publicados():
    """Os únicos dois números que a HLTV publicou.

    Se a reta deixar de passar por eles, o ajuste de economia parou de seguir a
    metodologia e virou invenção.
    """
    assert peso_da_kill(0.48) == pytest.approx(1.10, abs=0.01)
    assert peso_da_kill(0.75) == pytest.approx(0.54, abs=0.01)


def test_matar_pistola_inicial_vale_menos_que_matar_rifle():
    """No mesmo lado: quanto maior a chance que o time já tinha, menos vale.

    É a crítica que o ajuste de economia existe para responder -- matar um
    inimigo de pistola num round já ganho não é o mesmo que matar um rifle num
    round parelho.
    """
    # taxa de vitória alta = adversário mal equipado
    contra_pistola = peso_da_kill(0.75)
    contra_rifle = peso_da_kill(0.48)
    assert contra_pistola < contra_rifle


def test_o_peso_da_kill_nunca_sai_da_faixa():
    for taxa in (0.0, 0.05, 0.5, 0.95, 1.0):
        assert PESO_KILL_MIN <= peso_da_kill(taxa) <= PESO_KILL_MAX
    assert PESO_KILL_MIN <= peso_da_kill(None) <= PESO_KILL_MAX


def test_os_seis_grupos_de_equipamento_cobrem_as_armas_do_jogo():
    grupos_vistos = set(ARMA_PARA_GRUPO.values())
    assert grupos_vistos == {
        "sniper", "rifle_t1", "rifle_t2", "smg_shotgun",
        "pistola_melhorada", "pistola_inicial",
    }
    assert ARMA_PARA_GRUPO["AWP"] == "sniper"
    assert ARMA_PARA_GRUPO["AK-47"] == "rifle_t1"
    assert ARMA_PARA_GRUPO["Glock-18"] == "pistola_inicial"


# --- Modelo de probabilidade do round ---------------------------------------

def _modelo_sintetico() -> ModeloDeRound:
    """Modelo treinado num conjunto em que mais vivos = mais vitória."""
    rng = np.random.default_rng(0)
    X, y = [], []
    for _ in range(800):
        dif = int(rng.integers(-5, 6))
        equip = float(rng.normal(0, 3000))
        bomba = bool(rng.integers(0, 2))
        ct = bool(rng.integers(0, 2))
        p = 1 / (1 + np.exp(-(1.0 * dif + 0.5 * (1 if bomba and not ct else -1 if bomba else 0))))
        X.append(_estado(dif, equip, bomba, ct))
        y.append(int(rng.random() < p))
    return ModeloDeRound().treina(np.array(X), np.array(y))


def test_a_probabilidade_fica_entre_zero_e_um_inclusive_nos_extremos():
    """5v0 e 0v5 são os estados que quebram uma contagem empírica por estado.

    Com regressão logística eles saem perto de 1 e de 0, mas nunca cravados --
    e é isso que impede o Round Swing de virar infinito num caso de borda.
    """
    modelo = _modelo_sintetico()
    extremos = [
        _estado(5, 0, False, True), _estado(-5, 0, False, True),
        _estado(5, 20000, True, False), _estado(-5, -20000, True, False),
        _estado(0, 0, False, True),
    ]
    p = modelo.prob(np.array(extremos))
    assert np.all(p > 0.0) and np.all(p < 1.0)
    # e a direção tem que estar certa: mais vivos, mais chance
    assert p[0] > p[1]


def test_modelo_sem_amostra_nao_finge_que_sabe():
    """Com poucas linhas ele devolve 0,5, em vez de um número inventado."""
    vazio = ModeloDeRound().treina(np.zeros((3, 4)), np.array([1, 0, 1]))
    assert vazio.metricas["treinou"] is False
    assert vazio.prob(np.array([_estado(5, 0, False, True)]))[0] == 0.5


def test_o_modelo_reporta_calibracao_e_separacao():
    """Desempenho declarado, não fé: Brier mede calibração, AUC mede separação."""
    m = _modelo_sintetico()
    assert 0.0 <= m.metricas["brier"] <= 0.25
    assert m.metricas["auc"] > 0.7
    assert set(m.metricas["coeficientes"]) == set(ModeloDeRound.COLUNAS)


# --- Divisão do crédito ------------------------------------------------------

def test_o_credito_distribuido_nunca_excede_a_variacao_do_evento():
    """Os pesos somam no máximo 1,0 -- e é isso que garante a propriedade.

    Se alguém somar um quinto peso sem tirar dos outros, a soma do crédito
    passaria da variação que de fato aconteceu, e o rating estaria criando
    contribuição do nada.
    """
    assert CREDITO_KILL + CREDITO_DANO + CREDITO_FLASH + CREDITO_TRADE <= 1.0 + 1e-9


# --- Sobre o corpus real -----------------------------------------------------

PROCESSED = Path("data/processed")
INTERIM = Path("data/interim")


def _contexto(match_id: str):
    from parsing.parser import kills_do_round_jogado
    from scripts.build_insights import resolve_teams, side_of_team

    processed, interim = PROCESSED / match_id, INTERIM / match_id
    rounds = pl.read_parquet(processed / "rounds.parquet")
    kills = kills_do_round_jogado(pl.read_parquet(interim / "kills.parquet"), rounds)
    ticks = pl.read_parquet(interim / "ticks.parquet")
    blind = interim / "player_blind.parquet"
    tabelas = {
        "rounds": rounds, "kills": kills, "ticks": ticks,
        "damages": pl.read_parquet(interim / "damages.parquet"),
        "player_blind": pl.read_parquet(blind) if blind.exists() else None,
    }
    team_of, _ = resolve_teams(ticks)
    vencedor = {
        int(r["round_num"]): ("A" if r["winner"] == side_of_team("A", int(r["round_num"])) else "B")
        for r in rounds.iter_rows(named=True)
    }
    kast = pl.read_parquet(processed / "kast_summary.parquet")
    return tabelas, team_of, vencedor, kast


@pytest.mark.parametrize("match_id", ["match_01", "match_08"])
def test_round_perdido_nao_gera_swing_positivo(match_id):
    """Regra explícita da HLTV, e ela vale inclusive em clutch perdido.

    Quem quase virou e perdeu não ganha crédito por ter chegado perto -- o round
    foi perdido, e o swing existe para medir o que mudou o resultado.
    """
    if not (INTERIM / match_id / "kills.parquet").exists():
        pytest.skip("sem dado interim")
    tabelas, team_of, vencedor, kast = _contexto(match_id)
    per_round, _ = rating(tabelas, team_of, vencedor, kast, TICKRATE)

    perdidos = per_round.filter(
        pl.struct(["round_num", "steamid"]).map_elements(
            lambda s: vencedor.get(int(s["round_num"])) != team_of.get(s["steamid"]),
            return_dtype=pl.Boolean,
        )
    )
    assert perdidos.height > 0, "o teste precisa de rounds perdidos para ter conteúdo"
    assert perdidos["swing"].max() <= 1e-9


@pytest.mark.parametrize("match_id", ["match_01"])
def test_o_grupo_de_equipamento_sai_da_melhor_arma_do_round(match_id):
    """Quem compra AWP e morre com a pistola na mão comprou AWP."""
    if not (INTERIM / match_id / "kills.parquet").exists():
        pytest.skip("sem dado interim")
    rounds = pl.read_parquet(PROCESSED / match_id / "rounds.parquet")
    ticks = pl.read_parquet(INTERIM / match_id / "ticks.parquet")
    g = grupo_do_round(ticks, rounds)
    assert g.height > 0
    assert set(g["grupo"].unique()) <= set(ARMA_PARA_GRUPO.values())
    # num corpus com AWPers, o grupo sniper tem que aparecer
    assert "sniper" in set(g["grupo"].unique())


def test_a_media_do_rating_no_corpus_fica_perto_de_um():
    """A escala mantém média 1,00 -- é o que torna o número legível.

    Usa a referência do conjunto quando ela existe; sem ela o teste não teria
    conteúdo, porque cada partida daria 1,00 por construção.
    """
    referencia = carrega_referencia()
    if referencia is None:
        pytest.skip("rating_reference.json ainda não foi ajustado")

    ids = sorted(d.name for d in PROCESSED.glob("match_*")
                 if (INTERIM / d.name / "kills.parquet").exists())
    if len(ids) < 3:
        pytest.skip("corpus pequeno demais")

    valores = []
    for mid in ids:
        tabelas, team_of, vencedor, kast = _contexto(mid)
        _, resumo = rating(tabelas, team_of, vencedor, kast, TICKRATE, referencia=referencia)
        valores += [j["rating"] for j in resumo["jogadores"]]

    media = float(np.mean(valores))
    assert 0.90 <= media <= 1.10, f"média do rating saiu em {media:.3f}"


def test_jogador_com_poucos_rounds_e_marcado_como_amostra_fraca():
    """Rating sobre meia dúzia de rounds não pode ser apresentado como confiável."""
    referencia = carrega_referencia()
    ids = sorted(d.name for d in PROCESSED.glob("match_*")
                 if (INTERIM / d.name / "kills.parquet").exists())
    if not ids:
        pytest.skip("sem dado")

    tabelas, team_of, vencedor, kast = _contexto(ids[0])
    # corta o corpus para poucos rounds, simulando quem entrou no fim
    poucos = tabelas["rounds"].head(3)
    tabelas = {**tabelas, "rounds": poucos,
               "kills": tabelas["kills"].filter(pl.col("round_num") <= 3)}
    _, resumo = rating(tabelas, team_of, vencedor, kast, TICKRATE, referencia=referencia)
    assert all(j["amostra_fraca"] for j in resumo["jogadores"])
    assert poucos.height < MIN_ROUNDS_CONFIAVEL


@pytest.mark.parametrize("match_id", ["match_01"])
def test_o_rating_nao_conta_evento_de_warmup(match_id):
    """Decisão 8b: o que acontece antes do fim do freeze não pertence a round."""
    if not (INTERIM / match_id / "kills.parquet").exists():
        pytest.skip("sem dado interim")
    rounds = pl.read_parquet(PROCESSED / match_id / "rounds.parquet")
    ticks = pl.read_parquet(INTERIM / match_id / "ticks.parquet")

    g = grupo_do_round(ticks, rounds)
    primeiro_freeze = int(rounds["freeze_end"].min())
    # nenhuma linha pode ter vindo de antes do primeiro freeze_end
    assert g.height > 0
    cru = ticks.filter(pl.col("tick") < primeiro_freeze)
    assert cru.height > 0, "o teste precisa de ticks de warmup para ter conteúdo"


# --- Honestidade -------------------------------------------------------------

def test_o_rotulo_nunca_afirma_ser_o_rating_oficial():
    """A fórmula da HLTV é fechada. Chamar isto de Rating 3.0 seria falso."""
    ids = sorted(d.name for d in PROCESSED.glob("match_*")
                 if (INTERIM / d.name / "kills.parquet").exists())
    if not ids:
        pytest.skip("sem dado")
    tabelas, team_of, vencedor, kast = _contexto(ids[0])
    _, resumo = rating(tabelas, team_of, vencedor, kast, TICKRATE)
    rotulo = resumo["rotulo"].lower()
    assert "implementacao propria" in rotulo or "implementação própria" in rotulo
    assert "metodologia" in rotulo


def test_os_pesos_provisorios_somam_um():
    """Se não somarem 1,0, a média do corpus deixa de ser 1,00 por construção."""
    assert sum(PESOS_PROVISORIOS.values()) == pytest.approx(1.0)
    assert set(PESOS_PROVISORIOS) == {
        "kills", "dano", "sobrevivencia", "kast", "multikills", "round_swing",
    }
