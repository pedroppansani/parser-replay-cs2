"""A rotina de arremesso do jogo contra o GABARITO da demo (decisão 21a).

O gabarito (`tests/fixtures/gabarito_arremessos_match_23.json`) traz, por
arremesso, o que o jogo gravou (botão, chão, postura, velocidade e posição
iniciais do projétil) e as entradas que a produção tem sem o .dem. Estes testes
rodam só com ele: nem .dem nem interim.

Metas de AFIRMAÇÃO (o que o produto mostra como fato): botão, "no ar" e
postura, >= 99%. A posição de saída e a velocidade calculada não são afirmadas:
entram por uma CATRACA -- o número medido fica gravado aqui e o teste falha se
ele piorar.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from metrics.grenade_throws import (
    ALTURA_SAIDA_AGACHADO,
    ALTURA_SAIDA_EM_PE,
    ALTURA_SAIDA_POR_BOTAO,
    AVANCO_SAIDA,
    FATOR_HERANCA,
    TOLERANCIA_BOTAO,
    VELOCIDADE_BOTAO,
    direcao_do_lancamento,
    estado_vertical,
    rotina_do_jogo,
)

GABARITO = Path(__file__).parent / "fixtures" / "gabarito_arremessos_match_23.json"
T = 64

# Catraca (2026-09-27, match_23): os valores medidos quando a rota A entrou. O
# teste falha se a qualidade PIORAR; melhorou, atualiza-se o número aqui.
CATRACA_VELOCIDADE_MENOS_DE_5 = 0.9604    # fração com erro < 5 u/s (n = 430)
CATRACA_VELOCIDADE_P99 = 9.73             # u/s
CATRACA_VELOCIDADE_MAXIMO = 22.24         # u/s (11:140, limite de subtick)
CATRACA_POSICAO_MENOS_DE_1 = 0.6924         # fração com botão e postura a < 1 u (n = 426)


def _botao_gravado(f: float) -> float:
    return round(f * 2) / 2


@pytest.fixture(scope="module")
def casos():
    doc = json.loads(GABARITO.read_text(encoding="utf-8"))
    out = []
    for a in doc["arremessos"]:
        e = a["entrada"]
        pp = np.array(e["proj_pontos"])
        pt = e["proj_ticks"]
        vp = (pp[1] - pp[0]) / ((pt[1] - pt[0]) / T)
        z_saida = pp[0][2] - vp[2] * (pt[0] - e["tick_soltura"]) / T
        r = rotina_do_jogo(np.array(e["z_janela"]), np.array(e["xy_janela"]), vp, z_saida,
                           e["pitch"], e["yaw"], T)
        out.append((a, r, estado_vertical(np.array(e["z_janela"]), np.array(e["xy_janela"]), T)))
    return out


def test_o_gabarito_tem_a_partida_inteira():
    doc = json.loads(GABARITO.read_text(encoding="utf-8"))
    assert doc["partida"] == "match_23" and len(doc["arremessos"]) == 434


def test_botao_acerta_o_gravado_em_pelo_menos_99_porcento(casos):
    rot = [(r["botao"], _botao_gravado(a["demo"]["forca"])) for a, r, _ in casos if r["botao"] is not None]
    acertos = sum(b == g for b, g in rot)
    assert acertos / len(rot) >= 0.99, f"{acertos}/{len(rot)}"


def test_no_ar_acerta_o_chao_gravado_em_pelo_menos_99_porcento(casos):
    com = [(r["no_ar"], not a["demo"]["no_chao"]) for a, r, _ in casos if r["no_ar"] is not None]
    acertos = sum(p == g for p, g in com)
    assert acertos / len(com) >= 0.99, f"{acertos}/{len(com)}"


def test_escada_e_rampa_nao_viram_no_ar(casos):
    """Os 9 do gabarito com |vz| >= 60 que a demo diz estarem no chão."""
    escada = [(a, r) for a, r, ev in casos if a["demo"]["no_chao"] and abs(ev["vz_derivada"]) >= 60]
    assert len(escada) == 9
    assert all(r["no_ar"] is not True for _, r in escada)


def test_postura_acerta_duck_amount_em_pelo_menos_99_porcento(casos):
    com = [(r["postura"], a["demo"]["duck_amount"]) for a, r, _ in casos
           if r["postura"] is not None and a["demo"]["duck_amount"] in (0.0, 1.0)]
    acertos = sum((p == "agachado") == (d == 1.0) for p, d in com)
    assert acertos / len(com) >= 0.99, f"{acertos}/{len(com)}"


def test_invariante_o_erro_do_modelo_nunca_alcanca_o_botao_vizinho(casos):
    """Nenhum arremesso recebe botão se o erro possível da velocidade puder
    levá-lo ao botão vizinho: erro < (menor distância entre centros -
    tolerância). Tolerância e erro são coisas diferentes: a tolerância decide
    se o rótulo é dado (distância ao centro); o erro mede o modelo (catraca).
    Tudo lido das constantes, sem número fixo aqui."""
    centros = sorted(VELOCIDADE_BOTAO.values())
    limite = min(b - a for a, b in zip(centros, centros[1:])) - TOLERANCIA_BOTAO
    for a, r, ev in casos:
        if r["botao"] is None:
            continue
        vj = np.array([ev["vh"][0], ev["vh"][1], ev["vz"]])
        u = direcao_do_lancamento(a["entrada"]["pitch"], a["entrada"]["yaw"])
        erro = float(np.linalg.norm(VELOCIDADE_BOTAO[r["botao"]] * u + FATOR_HERANCA * vj - np.array(a["demo"]["v0"])))
        assert erro < limite, f"{a['id']}: {erro:.1f} u/s >= {limite:.1f}"


def test_falhas_conhecidas_saem_neutras(casos):
    """Parábola quebrada (6:158, 12:181, 21:502) e o agachar no ar que quebra a
    parábola no tick da soltura (7:143) ficam sem botão por DETECÇÃO."""
    por_id = {a["id"]: r for a, r, _ in casos}
    for i in ("match_23:6:158", "match_23:12:181", "match_23:21:502", "match_23:7:143"):
        assert por_id[i]["botao"] is None, i
        assert por_id[i]["estado_vertical"].startswith("ambíguo"), (i, por_id[i]["estado_vertical"])


def test_soltura_19_ticks_depois_do_pulo_usa_a_vz_real(casos):
    r = next(r for a, r, _ in casos if a["id"] == "match_23:16:81")
    assert r["estado_vertical"] == "vz real 19+" and r["botao"] == 1.0


def test_catraca_da_velocidade(casos):
    erros = []
    for a, r, ev in casos:
        if ev["vz"] is None:
            continue
        vj = np.array([ev["vh"][0], ev["vh"][1], ev["vz"]])
        u = direcao_do_lancamento(a["entrada"]["pitch"], a["entrada"]["yaw"])
        b = _botao_gravado(a["demo"]["forca"])
        erros.append(np.linalg.norm(VELOCIDADE_BOTAO[b] * u + FATOR_HERANCA * vj - np.array(a["demo"]["v0"])))
    erros = np.array(erros)
    fr = float(np.mean(erros < 5))
    assert fr >= CATRACA_VELOCIDADE_MENOS_DE_5, f"velocidade < 5 u/s caiu para {fr:.4f}"
    assert np.percentile(erros, 99) <= CATRACA_VELOCIDADE_P99, np.percentile(erros, 99)
    assert erros.max() <= CATRACA_VELOCIDADE_MAXIMO, erros.max()


def test_catraca_da_posicao_de_saida(casos):
    erros = []
    for a, r, ev in casos:
        if r["botao"] is None or r["postura"] is None:
            continue
        e = a["entrada"]
        u = direcao_do_lancamento(e["pitch"], e["yaw"])
        h = (ALTURA_SAIDA_AGACHADO if r["postura"] == "agachado" else ALTURA_SAIDA_EM_PE) \
            + ALTURA_SAIDA_POR_BOTAO * (r["botao"] - 1)
        pes = np.array([*e["xy_janela"][-2], e["z_janela"][-2] + ev["z_ref"]])
        if ev["regra"] == "regra fixa 6-13":
            # pés no instante decolagem + 0,1 s: horizontal pela janela
            t01 = -ev["ticks_desde_decolagem"] / T + 0.1
            J = np.array(e["xy_janela"]); k = (len(J) - 2) + t01 * T - 0.5
            i0 = int(np.floor(k)); f = k - i0
            pes[:2] = J[i0] * (1 - f) + J[i0 + 1] * f
        erros.append(np.linalg.norm(pes + np.array([0, 0, h]) + AVANCO_SAIDA * u - np.array(a["demo"]["p0"])))
    fr = float(np.mean(np.array(erros) < 1))
    assert fr >= CATRACA_POSICAO_MENOS_DE_1, f"posição < 1 u caiu para {fr:.3f}"


def test_as_constantes_do_gabarito_sao_o_recalculo_e_nao_numero_digitado():
    """tolerância e faixa de postura em metrics/gabarito_constantes.json têm de
    ser exatamente o que o cálculo dá a partir do gabarito versionado."""
    from scripts.constantes_do_gabarito import calcula, carrega_gabarito
    gravado = json.loads((Path(__file__).parents[1] / "metrics" / "gabarito_constantes.json").read_text(encoding="utf-8"))
    arremessos, partidas = carrega_gabarito()
    novo = calcula(arremessos)
    assert gravado["tolerancia_botao"] == novo["tolerancia_botao"]
    assert gravado["faixa_postura_neutra"] == novo["faixa_postura_neutra"]
    assert gravado["partidas"] == partidas
