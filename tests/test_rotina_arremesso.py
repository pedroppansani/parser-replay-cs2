"""A rotina de arremesso do jogo contra o GABARITO da demo (decisão 21a).

O gabarito (`tests/fixtures/gabarito_arremessos_*.json.gz`, 12 partidas) traz,
por arremesso, o que o jogo gravou (botão, chão, postura, velocidade e posição
iniciais do projétil) e as entradas que a produção tem sem o .dem. Estes testes
rodam só com ele: nem .dem nem interim.

Metas de AFIRMAÇÃO (o que o produto mostra como fato), POR PARTIDA: botão
>= 99%, "no ar" >= 99% sobre os determinados, postura >= 99,5% fora da faixa
neutra, e a invariante do vizinho absoluta. A posição de saída e a velocidade
calculada não são afirmadas: entram por uma CATRACA -- o número medido fica
gravado aqui e o teste falha se ele piorar.

Estes números são DENTRO da amostra (as constantes saíram deste gabarito). O
número honesto de generalização é o da validação fora da amostra registrada na
decisão 21a.
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
from metrics.gabarito import _entradas, carrega_gabarito

# Catraca (2026-09-27, 12 partidas, com a guarda do voo): os valores medidos
# quando a rota A entrou. O teste falha se a qualidade PIORAR; se melhorar,
# atualiza-se o número aqui.
CATRACA_VELOCIDADE_MENOS_DE_5 = 0.9446    # fração com erro < 5 u/s (modelo aplicado, fora da guarda)
CATRACA_VELOCIDADE_P99 = 10.14            # u/s
CATRACA_POSICAO_MENOS_DE_1 = 0.6489       # fração com botão e postura a < 1 u

META = 0.99
META_POSTURA = 0.995


def _botao_gravado(f: float) -> float:
    return round(f * 2) / 2


@pytest.fixture(scope="module")
def casos():
    arremessos, _ = carrega_gabarito()
    out = []
    for a in arremessos:
        z, xy, vp, z_saida, t = _entradas(a)
        e = a["entrada"]
        out.append((a, rotina_do_jogo(z, xy, vp, z_saida, e["pitch"], e["yaw"], t), estado_vertical(z, xy, t)))
    return out


def _por_partida(casos):
    por: dict[str, list] = {}
    for c in casos:
        por.setdefault(c[0]["id"].split(":")[0], []).append(c)
    return por


def test_o_gabarito_tem_as_13_partidas():
    _, partidas = carrega_gabarito()
    assert len(partidas) == 13 and "match_23" in partidas


def test_botao_acerta_o_gravado_em_cada_partida(casos):
    for partida, cs in _por_partida(casos).items():
        rot = [(r["botao"], _botao_gravado(a["demo"]["forca"])) for a, r, _ in cs if r["botao"] is not None]
        acertos = sum(b == g for b, g in rot)
        assert acertos / len(rot) >= META, f"{partida}: {acertos}/{len(rot)}"


def test_no_ar_acerta_o_chao_gravado_nos_determinados(casos):
    for partida, cs in _por_partida(casos).items():
        com = [(r["no_ar"], not a["demo"]["no_chao"]) for a, r, _ in cs if r["no_ar"] is not None]
        acertos = sum(p == g for p, g in com)
        assert acertos / len(com) >= META, f"{partida}: {acertos}/{len(com)}"


def test_postura_fora_da_faixa_acerta_duck_amount(casos):
    for partida, cs in _por_partida(casos).items():
        com = [(r["postura"], a["demo"]["duck_amount"]) for a, r, _ in cs
               if r["postura"] is not None and a["demo"]["no_chao"] and a["demo"]["duck_amount"] in (0.0, 1.0)]
        acertos = sum((p == "agachado") == (d == 1.0) for p, d in com)
        assert acertos / len(com) >= META_POSTURA, f"{partida}: {acertos}/{len(com)}"


def test_invariante_o_erro_do_modelo_nunca_alcanca_o_botao_vizinho(casos):
    """Nenhum arremesso recebe botão se o erro possível da velocidade puder
    levá-lo ao botão vizinho: erro < (menor distância entre centros -
    tolerância). A tolerância decide se o rótulo é dado; o erro mede o modelo
    (catraca). Tudo lido das constantes."""
    centros = sorted(VELOCIDADE_BOTAO.values())
    limite = min(b - a for a, b in zip(centros, centros[1:])) - TOLERANCIA_BOTAO
    for a, r, ev in casos:
        if r["botao"] is None:
            continue
        vj = np.array([ev["vh"][0], ev["vh"][1], ev["vz"]])
        u = direcao_do_lancamento(a["entrada"]["pitch"], a["entrada"]["yaw"])
        erro = float(np.linalg.norm(VELOCIDADE_BOTAO[r["botao"]] * u + FATOR_HERANCA * vj - np.array(a["demo"]["v0"])))
        assert erro < limite, f"{a['id']}: {erro:.1f} u/s >= {limite:.1f}"


def test_a_guarda_do_voo_neutraliza_os_vetores_grosseiramente_errados(casos):
    """Os dois que quebravam a invariante na validação fora da amostra e os
    outros vetores com erro acima de 50 u/s saem neutros pela guarda."""
    por_id = {a["id"]: r for a, r, _ in casos}
    for i in ("match_16:10:199", "match_14:6:222", "match_18:13:477", "match_15:16:92",
              "match_20:4:489", "match_19:7:527"):
        assert por_id[i]["botao"] is None, i
        assert por_id[i]["estado_vertical"] == "vetor incoerente com o voo", (i, por_id[i]["estado_vertical"])


def test_falhas_conhecidas_saem_neutras(casos):
    """Parábola quebrada (match_23: 6:158, 12:181, 21:502) fica sem botão por
    DETECÇÃO, e o agachar no ar que quebra a parábola no tick da soltura
    (7:143) também."""
    por_id = {a["id"]: r for a, r, _ in casos}
    for i in ("match_23:6:158", "match_23:12:181", "match_23:21:502", "match_23:7:143"):
        assert por_id[i]["botao"] is None, i


def test_soltura_19_ticks_depois_do_pulo_usa_a_vz_real(casos):
    r = next(r for a, r, _ in casos if a["id"] == "match_23:16:81")
    assert r["estado_vertical"] == "vz real 19+" and r["botao"] == 1.0


def test_catraca_da_velocidade(casos):
    erros = []
    for a, r, ev in casos:
        if ev["vz"] is None or r["estado_vertical"] == "vetor incoerente com o voo":
            continue
        vj = np.array([ev["vh"][0], ev["vh"][1], ev["vz"]])
        u = direcao_do_lancamento(a["entrada"]["pitch"], a["entrada"]["yaw"])
        b = _botao_gravado(a["demo"]["forca"])
        erros.append(np.linalg.norm(VELOCIDADE_BOTAO[b] * u + FATOR_HERANCA * vj - np.array(a["demo"]["v0"])))
    erros = np.array(erros)
    fr = float(np.mean(erros < 5))
    assert fr >= CATRACA_VELOCIDADE_MENOS_DE_5, f"velocidade < 5 u/s caiu para {fr:.4f}"
    assert np.percentile(erros, 99) <= CATRACA_VELOCIDADE_P99, np.percentile(erros, 99)


def test_catraca_da_posicao_de_saida(casos):
    from metrics.gabarito import pes_da_saida
    erros = []
    for a, r, ev in casos:
        if r["botao"] is None or r["postura"] is None:
            continue
        u = direcao_do_lancamento(a["entrada"]["pitch"], a["entrada"]["yaw"])
        h = (ALTURA_SAIDA_AGACHADO if r["postura"] == "agachado" else ALTURA_SAIDA_EM_PE) \
            + ALTURA_SAIDA_POR_BOTAO * (r["botao"] - 1)
        calc = pes_da_saida(a, ev) + np.array([0, 0, h]) + AVANCO_SAIDA * u
        erros.append(np.linalg.norm(calc - np.array(a["demo"]["p0"])))
    fr = float(np.mean(np.array(erros) < 1))
    assert fr >= CATRACA_POSICAO_MENOS_DE_1, f"posição < 1 u caiu para {fr:.4f}"


def test_as_constantes_do_gabarito_sao_o_recalculo_e_nao_numero_digitado():
    """As constantes em metrics/gabarito_constantes.json têm de ser exatamente o
    que o cálculo dá a partir das partidas que o arquivo declara: gabarito novo
    no disco não muda as constantes sozinho (recalcular é decisão registrada)."""
    from metrics.gabarito import calcula
    gravado = json.loads((Path(__file__).parents[1] / "metrics" / "gabarito_constantes.json").read_text(encoding="utf-8"))
    arremessos, partidas = carrega_gabarito()
    assert set(gravado["partidas"]) <= set(partidas)
    novo = calcula([a for a in arremessos if a["id"].split(":")[0] in gravado["partidas"]])
    for chave in ("tolerancia_botao", "faixa_postura_neutra", "limiar_guarda_voo", "deslocamento_primeiro_segmento_z"):
        assert gravado[chave] == novo[chave], chave


def test_ancora_a_direcao_do_lancamento_no_dado_real(casos):
    """ÂNCORA: o gerador sintético de test_grenade_throws importa
    direcao_do_lancamento da produção, então um erro nela passaria nos dois
    lados. Aqui ela é conferida contra m_vInitialVelocity nos arremessos PARADOS
    (herança zero, sem ruído da velocidade do jogador): o ângulo entre a
    velocidade inicial gravada e a direção prevista.
    Medido (13 partidas, n = 1.253): mediana 0,00015°, p95 0,14°, p99 0,56°;
    76% abaixo de 0,01° arremesso a arremesso -- a cauda é provavelmente a mira
    girando dentro do tick, que o gabarito não guarda. Um remapeamento errado
    (80/90 no lugar de 100/90, sinal trocado) leva a mediana a graus."""
    ang = []
    for a, r, ev in casos:
        if ev["regra"] != "chão" or np.hypot(*ev["vh"]) > 1e-6 or abs(ev["vz_derivada"]) > 1e-6:
            continue
        u = direcao_do_lancamento(a["entrada"]["pitch"], a["entrada"]["yaw"])
        w = np.array(a["demo"]["v0"])
        ang.append(np.degrees(np.arccos(np.clip(w @ u / np.linalg.norm(w), -1, 1))))
    ang = np.array(ang)
    assert ang.size > 1000
    assert np.median(ang) < 0.01, np.median(ang)
    assert np.percentile(ang, 95) < 0.2, np.percentile(ang, 95)
