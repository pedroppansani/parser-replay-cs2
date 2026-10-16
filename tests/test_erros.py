"""Tipos de erro da aba Perfil (fase 12, metrics/erros.py; definições da fase 18), com situações montadas à mão.

Cada tipo tem uma situação que deve contar e uma que não deve para cada filtro da tabela do
pedido (12.6, item 1); a ordem "explícito ou depende" tem um teste por regra (item 3); o eco fica
fora (item 4); e a mesma partida em dois processos com PYTHONHASHSEED diferente dá as mesmas
ocorrências (item 2).

Fase 18 (18.5, item 2): as situações montadas trazem também o olhar de cada jogador (yaw), as paredes
(triângulos) e os tiros, porque "visível para o jogador" (metrics/visao.py) entra nas definições. Os testes
que verificavam a definição antiga (distância de troca, "atrás do aliado", "morrer para o matador já é ir
para a troca") foram migrados para a nova; os casos que o Pedro já julgou, com os dados reais, estão em
tests/test_erros_casos_julgados.py.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import numpy as np
import polars as pl
import pytest

from metrics import erros as E
from metrics import visao as V

RAIZ = Path(__file__).resolve().parent.parent
TR = 64
TIME_A = [1, 2, 3, 4, 5]          # TR no round 1
TIME_B = [6, 7, 8, 9, 10]         # CT no round 1


def _lado(sid: int) -> str:
    return "t" if sid in TIME_A else "ct"


def kill(t: int, atacante: int, vitima: int, pa=(1000.0, 0.0, 0.0), pv=(0.0, 0.0, 0.0), arma="ak47", rn=1) -> dict:
    return {"round_num": rn, "tick": t, "attacker_steamid": atacante, "attacker_side": _lado(atacante),
            "victim_steamid": vitima, "victim_side": _lado(vitima), "weapon": arma,
            "attacker_X": pa[0], "attacker_Y": pa[1], "attacker_Z": pa[2],
            "victim_X": pv[0], "victim_Y": pv[1], "victim_Z": pv[2]}


def dano(t: int, atacante: int, vitima: int, d: int = 20, arma: str = "ak47", rn: int = 1) -> dict:
    return {"round_num": rn, "tick": t, "attacker_steamid": atacante, "victim_steamid": vitima,
            "attacker_side": _lado(atacante), "victim_side": _lado(vitima), "weapon": arma, "dmg_health_real": d}


def cegueira(t: int, atacante: int, usuario: int, dur: float, rn: int = 1) -> dict:
    return {"round_num": rn, "tick": t, "attacker_steamid": atacante, "user_steamid": usuario,
            "attacker_side": _lado(atacante), "user_side": _lado(usuario), "blind_duration": dur}


def parede(x: float, y0: float, y1: float, z0: float = -100.0, z1: float = 300.0) -> np.ndarray:
    """Uma parede no plano x = const, de y0 a y1 (dois triângulos)."""
    a, b, c, d = (x, y0, z0), (x, y1, z0), (x, y1, z1), (x, y0, z1)
    return np.array([[a, b, c], [a, c, d]], dtype=float)


def _onde_padrao(sid: int) -> tuple:
    # longe de tudo e fora do campo de visão de todos: o TR fica no +X olhando para +X, o CT no -X olhando para -X
    return (5000.0 + 100 * sid, 5000.0) if sid in TIME_A else (-5000.0 - 100 * sid, 5000.0)


def partida(kills: list[dict], onde: dict[int, tuple], *, danos=(), cegos=(), sem_arma=(), eco=None,
            funcoes=None, awpers=(), plant=None, vencedor="ct", corte=None, onde_por_tick=None,
            olhar=None, olhar_por_tick=None, paredes=None, tiros=(), chance=None) -> E.Partida:
    """Uma partida de um round. `onde` = {steamid: (x, y[, z])} vale para todo instante; `onde_por_tick`
    sobrescreve a partir de um tick (a visão usa o tick mais próximo antes do instante). `olhar` = {steamid:
    yaw} (padrão: o TR olha para +X, o CT para -X); `paredes` = triângulos do mapa; `tiros` = (tick, steamid,
    yaw); `chance` = a função da chance do round (None: sem o filtro de round decidido)."""
    ticks = sorted({k["tick"] for k in kills} | {k["tick"] - 1 for k in kills} | set(onde_por_tick or {})
                   | set(olhar_por_tick or {}) | {0})
    linhas = []
    for t in ticks:
        for sid in TIME_A + TIME_B:
            pos = None
            for x in sorted(onde_por_tick or {}):
                if x <= t and sid in onde_por_tick[x]:
                    pos = onde_por_tick[x][sid]
            x, y, *z = pos or onde.get(sid) or _onde_padrao(sid)
            yaw = (olhar or {}).get(sid, 0.0 if sid in TIME_A else 180.0)
            for x2 in sorted(olhar_por_tick or {}):
                if x2 <= t and sid in olhar_por_tick[x2]:
                    yaw = olhar_por_tick[x2][sid]
            linhas.append({"round_num": 1, "tick": t, "steamid": sid, "side": _lado(sid), "X": float(x),
                           "Y": float(y), "Z": float(z[0]) if z else 0.0, "is_alive": True, "yaw": float(yaw)})
    pos = pl.DataFrame(linhas, schema={"round_num": pl.Int64, "tick": pl.Int64, "steamid": pl.Int64,
                                       "side": pl.String, "X": pl.Float64, "Y": pl.Float64, "Z": pl.Float64,
                                       "is_alive": pl.Boolean, "yaw": pl.Float64})
    blinds = pl.DataFrame(list(cegos), schema={"round_num": pl.Int64, "tick": pl.Int64, "attacker_steamid": pl.Int64,
                                               "user_steamid": pl.Int64, "attacker_side": pl.String,
                                               "user_side": pl.String, "blind_duration": pl.Float64})
    malha = V.Malha(np.concatenate(paredes)) if paredes else None
    return E.Partida(
        match_id="sintetica", tickrate=TR,
        rounds=pl.DataFrame([{"round_num": 1, "freeze_end": 0, "end": 20000, "winner": vencedor, "bomb_plant": plant}],
                            schema={"round_num": pl.Int64, "freeze_end": pl.Int64, "end": pl.Int64,
                                    "winner": pl.String, "bomb_plant": pl.Int64}),
        kills=pl.DataFrame(kills) if kills else pl.DataFrame(schema=list(kill(0, 1, 6))),
        damages=pl.DataFrame(list(danos), schema={"round_num": pl.Int64, "tick": pl.Int64, "attacker_steamid": pl.Int64,
                                                  "victim_steamid": pl.Int64, "attacker_side": pl.String,
                                                  "victim_side": pl.String, "weapon": pl.String,
                                                  "dmg_health_real": pl.Int64}),
        blinds=blinds, posicoes=pos.drop("yaw"),
        primeira_arma={(1, s): 0 for s in TIME_A + TIME_B if s not in sem_arma},
        team_of={**{s: "A" for s in TIME_A}, **{s: "B" for s in TIME_B}},
        nomes={s: f"j{s}" for s in TIME_A + TIME_B}, corte_de_andar=corte,
        rounds_de_economia=set(eco or ()), funcoes=funcoes or {}, awpers=set(awpers),
        variacao={(1, k["tick"], k["victim_steamid"]): {"delta": -0.2, "vivos_antes": {}} for k in kills},
        alavanca={(1, "A"): 0.1, (1, "B"): 0.1},
        visao=V.Visao(pos, malha, cegueira=V.cegueira_efetiva(blinds, TR)),
        tiros=pl.DataFrame([{"round_num": 1, "tick": t, "player_steamid": s, "player_yaw": float(y)} for t, s, y in tiros],
                           schema={"round_num": pl.Int64, "tick": pl.Int64, "player_steamid": pl.Int64,
                                   "player_yaw": pl.Float64}),
        chance=chance)


def _do(oc: list[dict], sid: int) -> list[dict]:
    return [o for o in oc if o["steamid"] == sid]


def _contam(oc: list[dict], sid: int) -> list[dict]:
    return [o for o in _do(oc, sid) if o["filtro"] is None]


# o aliado 1 morre em (0,0) para o 6 em (1000,0); o jogador 2 está a 300 do aliado, olhando para o matador
BASE = {1: (0, 0), 2: (300, 0), 6: (1000, 0)}


# --- Não trocou o aliado ---------------------------------------------------------------------------

def test_nao_trocou_conta_quem_viu_o_matador_e_nao_trocou():
    oc = _do(E.nao_trocou(partida([kill(1000, 6, 1)], BASE)), 2)
    assert len(oc) == 1 and oc[0]["filtro"] is None and oc[0]["matador_visivel"] is True
    assert oc[0]["aliado_steamid"] == 1 and oc[0]["matador_steamid"] == 6 and oc[0]["dist_aliado"] == 300.0
    assert oc[0]["dwpa"] == pytest.approx(-0.2 * 0.1)       # ΔWPA = variação do round x alavanca
    assert oc[0]["seg_matador_visivel"] == pytest.approx(5.0, abs=0.05)


def test_nao_trocou_nao_conta_com_o_matador_fora_da_visao_nem_com_a_morte_trocada():
    # fase 18 (era "longe do aliado"): o matador fora da visão do jogador (ele olhava para o outro lado) não conta
    oc = _do(E.nao_trocou(partida([kill(1000, 6, 1)], BASE, olhar={2: 180.0})), 2)
    assert oc[0]["filtro"] == E.FILTRO_MATADOR_FORA_DA_VISAO and oc[0]["matador_visivel"] is False
    # parede entre o jogador e o matador: também fora
    oc = _do(E.nao_trocou(partida([kill(1000, 6, 1)], BASE, paredes=[parede(600, -500, 500)])), 2)
    assert oc[0]["filtro"] == E.FILTRO_MATADOR_FORA_DA_VISAO
    # a distância é contexto, não critério: longe do aliado e com o matador visível, conta
    longe = {**BASE, 2: (-E.DIST_TROCA - 400, 0)}
    assert len(_contam(E.nao_trocou(partida([kill(1000, 6, 1)], longe)), 2)) == 1
    trocada = [kill(1000, 6, 1), kill(1000 + 2 * TR, 3, 6, pa=(500, 0, 0), pv=(1000, 0, 0))]
    assert _do(E.nao_trocou(partida(trocada, BASE)), 2) == []


def test_nao_trocou_fora_cego_em_duelo_e_sem_arma():
    p = partida([kill(1000, 6, 1)], BASE, cegos=[cegueira(950, 7, 2, 3.0)])
    assert _do(E.nao_trocou(p), 2)[0]["filtro"] == E.FILTRO_CEGO
    p = partida([kill(1000, 6, 1)], BASE, danos=[dano(1000 - E.S_DUELO * TR + 5, 2, 7)])
    assert _do(E.nao_trocou(p), 2)[0]["filtro"] == E.FILTRO_DUELO
    p = partida([kill(1000, 6, 1)], BASE, danos=[dano(1000 - E.S_DUELO * TR - 5, 2, 7)])
    assert _do(E.nao_trocou(p), 2)[0]["filtro"] is None     # dano antes da janela do duelo não conta
    p = partida([kill(1000, 6, 1)], BASE, sem_arma=[2])
    assert _do(E.nao_trocou(p), 2)[0]["filtro"] == E.FILTRO_SEM_ARMA


def test_distancia_e_no_mesmo_andar():
    # fase 18: "perto" só vale em "morreu sozinho"; o aliado na laje de baixo, a 300 no plano, não está perto
    em_baixo = {1: (0, 0), 2: (300, 0, -600), 6: (1000, 0)}
    olhar = {2: 180.0}                                # e não vê o matador
    assert len(_contam(E.morreu_sozinho(partida([kill(1000, 6, 1)], em_baixo, corte=-495.0, olhar=olhar)), 1)) == 1
    oc = _do(E.morreu_sozinho(partida([kill(1000, 6, 1)], em_baixo, olhar=olhar)), 1)       # mapa de um andar
    assert oc[0]["filtro"] == E.FILTRO_ALIADO_COM_O_MATADOR
    assert E.distancia({"X": 0, "Y": 0, "Z": 0}, {"X": 300, "Y": 0, "Z": -600}, -495.0) == float("inf")


# --- Possível bait ---------------------------------------------------------------------------------

# recuou: na janela o jogador 2 sai de (300,0) para (50,0), 250 mais longe do matador parado em (1000,0)
RECUA = {1100: {2: (50, 0)}}


def test_possivel_bait_visivel_sem_atirar_e_recuando():
    oc = _do(E.possivel_bait(partida([kill(1000, 6, 1)], BASE, onde_por_tick=RECUA)), 2)
    assert len(oc) == 1 and oc[0]["tipo"] == E.POSSIVEL_BAIT and oc[0]["filtro"] is None
    assert oc[0]["recuo"] == pytest.approx(250.0) and oc[0]["atirou_no_matador"] is False
    assert E.TITULOS[E.POSSIVEL_BAIT].startswith("Possível")


def test_possivel_bait_nao_conta_parado_atirando_ou_dando_dano():
    # visível e parado sem atirar: "não trocou", mas não bait
    p = partida([kill(1000, 6, 1)], BASE)
    assert len(_contam(E.nao_trocou(p), 2)) == 1
    assert _do(E.possivel_bait(p), 2)[0]["filtro"] == E.FILTRO_NAO_RECUOU
    # recuou, mas atirou no matador (mira nele) ou deu dano: engajou
    p = partida([kill(1000, 6, 1)], BASE, onde_por_tick=RECUA, tiros=[(1050, 2, 0.0)])
    assert _do(E.possivel_bait(p), 2)[0]["filtro"] == E.FILTRO_ENGAJOU
    p = partida([kill(1000, 6, 1)], BASE, onde_por_tick=RECUA, danos=[dano(1100, 2, 6)])
    assert _do(E.possivel_bait(p), 2)[0]["filtro"] == E.FILTRO_ENGAJOU
    # um tiro para o outro lado (fora do cone) não é atirar nele
    p = partida([kill(1000, 6, 1)], BASE, onde_por_tick=RECUA, tiros=[(1050, 2, 40.0)])
    assert _do(E.possivel_bait(p), 2)[0]["filtro"] is None


def test_o_empate_de_distancia_nao_e_atras():
    # o caso do PAiN-M- (match_03, round 20): colado no aliado, à mesma distância do matador, parado
    colado = {1: (0, 0), 2: (0, 4), 6: (1000, 0)}
    p = partida([kill(1000, 6, 1)], colado)
    oc = _do(E.possivel_bait(p), 2)[0]
    assert oc["dist_matador_jogador"] == pytest.approx(oc["dist_matador_aliado"], abs=1.0)
    assert oc["filtro"] == E.FILTRO_NAO_RECUOU


def test_possivel_bait_saiu_da_linha_andando_e_nao_quando_o_matador_saiu():
    muro = [parede(500, 100, 1000)]               # a linha y = 0 passa livre; de (300, 300) para o matador, fecha
    p = partida([kill(1000, 6, 1)], BASE, paredes=muro, onde_por_tick={1100: {2: (300, 300)}})
    oc = _do(E.possivel_bait(p), 2)[0]
    assert oc["saiu_da_linha"] is True and oc["recuo"] < E.RECUO_MINIMO and oc["filtro"] is None
    # o matador é quem foi para trás da parede, o jogador ficou parado: não é bait
    p = partida([kill(1000, 6, 1)], BASE, paredes=muro, onde_por_tick={1100: {6: (1000, 400)}})
    oc = _do(E.possivel_bait(p), 2)[0]
    assert oc["saiu_da_linha"] is False and oc["filtro"] == E.FILTRO_NAO_RECUOU


def test_possivel_bait_herda_os_filtros_de_nao_trocou():
    p = partida([kill(1000, 6, 1)], BASE, onde_por_tick=RECUA, cegos=[cegueira(990, 7, 2, 2.0)])
    assert _do(E.possivel_bait(p), 2)[0]["filtro"] == E.FILTRO_CEGO
    p = partida([kill(1000, 6, 1)], BASE, onde_por_tick=RECUA, olhar={2: 180.0})
    assert _do(E.possivel_bait(p), 2)[0]["filtro"] == E.FILTRO_MATADOR_FORA_DA_VISAO


# --- Perdeu a troca --------------------------------------------------------------------------------

def test_perdeu_a_troca_foi_e_morreu_sem_matar():
    p = partida([kill(1000, 6, 1), kill(1100, 6, 2, pv=(300, 0, 0))], BASE, danos=[dano(1050, 2, 6)])
    oc = _do(E.perdeu_a_troca(p), 2)
    assert len(oc) == 1 and oc[0]["tick"] == 1100 and oc[0]["filtro"] is None and oc[0]["inimigos_visiveis"] == 1
    # atirar nele (sem acertar) também é ir para a troca
    p = partida([kill(1000, 6, 1), kill(1100, 6, 2, pv=(300, 0, 0))], BASE, tiros=[(1050, 2, 1.0)])
    assert _contam(E.perdeu_a_troca(p), 2)
    # andar na direção dele com ele visível também (de 300 para 600: 300 mais perto)
    p = partida([kill(1000, 6, 1), kill(1100, 6, 2, pv=(600, 0, 0))], BASE, onde_por_tick={1060: {2: (600, 0)}})
    assert _contam(E.perdeu_a_troca(p), 2)
    # fase 18: morrer para o matador SEM ter ido trocar (sem tiro, sem dano, parado) não é perder a troca
    p = partida([kill(1000, 6, 1), kill(1100, 6, 2, pv=(300, 0, 0))], BASE)
    assert _do(E.perdeu_a_troca(p), 2)[0]["filtro"] == E.FILTRO_SEM_ENGAJAMENTO


def test_perdeu_a_troca_nao_conta_quem_trocou_ou_nao_foi():
    trocou = [kill(1000, 6, 1), kill(1050, 2, 6, pa=(300, 0, 0), pv=(1000, 0, 0)), kill(1100, 7, 2, pv=(300, 0, 0))]
    assert _do(E.perdeu_a_troca(partida(trocou, BASE)), 2) == []
    outro = [kill(1000, 6, 1), kill(1100, 7, 2, pv=(300, 0, 0))]          # morreu para outro, sem ir no matador
    assert _do(E.perdeu_a_troca(partida(outro, BASE)), 2)[0]["filtro"] == E.FILTRO_SEM_ENGAJAMENTO
    depois = [kill(1000, 6, 1), kill(1000 + 6 * TR, 6, 2, pv=(300, 0, 0))]   # fora da janela de troca
    assert _do(E.perdeu_a_troca(partida(depois, BASE)), 2) == []


def test_perdeu_a_troca_com_tres_inimigos_visiveis_fica_fora():
    tres = {**BASE, 7: (1000, 150), 8: (1000, -150)}
    p = partida([kill(1000, 6, 1), kill(1100, 6, 2, pv=(300, 0, 0))], tres, danos=[dano(1050, 2, 6)])
    oc = _do(E.perdeu_a_troca(p), 2)[0]
    assert oc["inimigos_visiveis"] == 3 and oc["filtro"] == E.FILTRO_DOIS_OU_MAIS
    # os outros dois atrás de uma parede: um só visível, conta
    p = partida([kill(1000, 6, 1), kill(1100, 6, 2, pv=(300, 0, 0))], tres, danos=[dano(1050, 2, 6)],
                paredes=[parede(800, 100, 400), parede(800, -400, -100)])
    oc = _do(E.perdeu_a_troca(p), 2)[0]
    assert oc["inimigos_visiveis"] == 1 and oc["filtro"] is None


def test_perdeu_a_troca_com_a_propria_morte_trocada_fica_fora():
    k = [kill(1000, 6, 1), kill(1100, 6, 2, pv=(300, 0, 0)), kill(1200, 3, 6, pa=(-500, 0, 0), pv=(1000, 0, 0))]
    oc = _do(E.perdeu_a_troca(partida(k, BASE, danos=[dano(1050, 2, 6)])), 2)[0]
    assert oc["filtro"] == E.FILTRO_MORTE_TROCADA and oc["trocada"] is True and oc["trocada_por_steamid"] == 3


# --- Morreu sozinho --------------------------------------------------------------------------------

SOZINHO = {1: (0, 0), 6: (1000, 0)}


def test_morreu_sozinho_sem_aliado_perto_nem_com_o_matador_a_vista():
    # a morte sem troca com o aliado mais perto a 1.300 unidades, sem ver o matador: morreu sozinho
    p = partida([kill(1000, 6, 1)], {**SOZINHO, 2: (-1300, 0)}, olhar={2: 180.0})
    oc = _do(E.morreu_sozinho(p), 1)
    assert len(oc) == 1 and oc[0]["filtro"] is None and oc[0]["dist_aliado"] == 1300.0
    assert E.TITULOS[E.MORREU_SOZINHO] == "Morreu sozinho"
    assert E.COMO_MELHORAR[E.MORREU_SOZINHO] == ("Se não é o lurker, jogue onde um aliado consiga te trocar e avise "
                                                 "a posição. Morrer sem troca dá vantagem numérica de graça.")


def test_morreu_sozinho_nao_conta_com_aliado_perto_vendo_o_matador_nem_trocado():
    assert _do(E.morreu_sozinho(partida([kill(1000, 6, 1)], BASE, olhar={2: 180.0})), 1)[0]["filtro"] == \
        E.FILTRO_ALIADO_COM_O_MATADOR                                          # aliado a 300
    longe_vendo = {**SOZINHO, 2: (-1300, 0)}                                   # a 1.300, mas com o matador à vista
    assert _do(E.morreu_sozinho(partida([kill(1000, 6, 1)], longe_vendo)), 1)[0]["filtro"] == \
        E.FILTRO_ALIADO_COM_O_MATADOR
    trocada = [kill(1000, 6, 1, pv=(0, 0, 0)), kill(1100, 3, 6, pa=(5000, 0, 0), pv=(1000, 0, 0))]
    assert _do(E.morreu_sozinho(partida(trocada, SOZINHO)), 1) == []


def test_morreu_sozinho_fora_no_1_contra_n():
    antes = [kill(100 * i, 6, s, pv=(4000, 0, 0)) for i, s in enumerate((2, 3, 4, 5), start=1)]
    oc = _do(E.morreu_sozinho(partida(antes + [kill(1000, 6, 1)], SOZINHO)), 1)
    assert oc[0]["filtro"] == E.FILTRO_1_CONTRA_N


def test_a_morte_trocada_a_mil_unidades_nao_e_erro_de_ninguem():
    # o 1 morre a 1.000 do aliado chamando a atenção; o 3 mata o matador pelas costas na janela: foi trocado
    k = [kill(1000, 6, 1, pv=(0, 0, 0)), kill(1000 + TR, 3, 6, pa=(1500, 0, 0), pv=(1000, 0, 0))]
    p = partida(k, {1: (0, 0), 2: (-1000, 0), 3: (1500, 0), 6: (1000, 0)}, olhar={3: 180.0})
    tab = E.ocorrencias(p)
    da_morte = tab.filter((pl.col("tick") == 1000) & pl.col("filtro").is_null()
                          & pl.col("tipo").is_in([E.NAO_TROCOU, E.POSSIVEL_BAIT, E.MORREU_SOZINHO,
                                                  E.PRIMEIRA_MORTE_SEM_TROCA]))
    assert da_morte.height == 0
    m = E.mortes_trocadas(p).row(0, named=True)
    assert m["trocada"] is True and m["trocada_por_steamid"] == 3 and m["dist_de_quem_trocou"] == 1500.0


# --- Primeira morte sem troca ----------------------------------------------------------------------

def test_primeira_morte_sem_troca():
    p = partida([kill(1000, 6, 1), kill(2000, 7, 2)], BASE)
    oc = E.primeira_morte_sem_troca(p)
    assert [o["steamid"] for o in oc] == [1]                      # só a primeira morte do round
    trocada = [kill(1000, 6, 1), kill(1100, 2, 6, pa=(300, 0, 0), pv=(1000, 0, 0))]
    assert E.primeira_morte_sem_troca(partida(trocada, BASE)) == []


# --- Round decidido e situação ---------------------------------------------------------------------

def test_round_com_chance_acima_de_95_ou_abaixo_de_5_fica_fora():
    for c, fora in ((0.97, True), (0.03, True), (0.95, False), (0.05, False), (0.6, False)):
        p = partida([kill(1000, 6, 1)], BASE, chance=lambda rn, time, t, a, b, c=c: c)
        oc = _do(E.nao_trocou(p), 2)[0]
        assert (oc["filtro"] == E.FILTRO_ROUND_DECIDIDO) is fora, c
        assert oc["chance_vitoria"] == pytest.approx(c)


def test_a_situacao_nunca_e_0_contra_0_com_jogadores_vivos():
    # uma flash aos 0:08, antes de qualquer morte do round: 5 contra 5 (era "0 contra 0")
    p = partida([kill(3000, 6, 1)], BASE, cegos=[cegueira(512, 2, 3, 5.0)])
    oc = E.flash_no_time(p)[0]
    assert (oc["vivos_time"], oc["vivos_adversario"]) == (5, 5)
    # depois da primeira morte: 4 contra 5 para o time do morto
    p = partida([kill(400, 6, 1)], BASE, cegos=[cegueira(512, 2, 3, 5.0)])
    assert (E.flash_no_time(p)[0]["vivos_time"], E.flash_no_time(p)[0]["vivos_adversario"]) == (4, 5)
    # e o dano de utilidade também
    p = partida([], {}, danos=[dano(100, 2, 3, 30, "hegrenade")])
    oc = E.dano_de_utilidade_no_time(p)[0]
    assert (oc["vivos_time"], oc["vivos_adversario"]) == (5, 5)


# --- Flash no time e dano de utilidade no time -----------------------------------------------------

def test_flash_no_time_pela_soma_da_partida_e_por_uma_flash():
    muitas = [cegueira(100 * i, 2, 3, 2.0) for i in range(1, 16)]          # 30 s na partida
    oc = E.flash_no_time(partida([], {}, cegos=muitas))
    assert len(oc) == 15 and all(o["filtro"] is None for o in oc)
    assert all(o["valor"] == 2.0 and o["valor_soma_lado"] == 30.0 for o in oc)    # o evento e a soma do lado
    uma = [cegueira(100, 2, 3, E.SEG_CEGUEIRA_ALIADO_UMA + 0.5), cegueira(200, 2, 4, 1.0)]
    oc = E.flash_no_time(partida([], {}, cegos=uma))
    assert [o["filtro"] for o in oc] == [None, E.FILTRO_ABAIXO_DO_LIMIAR]
    # a flash no inimigo e a autoflash não contam
    assert E.flash_no_time(partida([], {}, cegos=[cegueira(100, 2, 7, 5.0), cegueira(200, 2, 2, 5.0)])) == []


def test_dano_de_utilidade_no_time_pela_soma_da_partida():
    oc = E.dano_de_utilidade_no_time(partida([], {}, danos=[dano(100, 2, 3, 30, "hegrenade")]))
    assert len(oc) == 1 and oc[0]["filtro"] is None and oc[0]["valor"] == 30
    oc = E.dano_de_utilidade_no_time(partida([], {}, danos=[dano(100, 2, 3, 10, "hegrenade")]))
    assert oc[0]["filtro"] == E.FILTRO_ABAIXO_DO_LIMIAR
    assert E.dano_de_utilidade_no_time(partida([], {}, danos=[dano(100, 2, 3, 90, "ak47")])) == []


def test_evento_com_zero_de_dano_nao_e_ocorrencia_mesmo_com_a_soma_acima_do_limiar():
    # o jogo manda player_hurt com 0 de dano no aliado na borda da HE; a soma do lado (30) passa do limiar
    oc = E.dano_de_utilidade_no_time(partida([], {}, danos=[dano(100, 2, 3, 30, "hegrenade"),
                                                            dano(500, 2, 4, 0, "hegrenade")]))
    assert [(o["valor"], o["filtro"], o["valor_soma_lado"]) for o in oc] == [
        (30.0, None, 30.0), (0.0, E.FILTRO_EVENTO_ZERADO, 30.0)]


def test_utilidade_no_bolso_nao_existe():
    # o inventário na hora da morte não existe no dado (decisão 46): o tipo não é criado
    assert not any("bolso" in t for t in E.TIPOS)
    assert not hasattr(E, "MIN_GRANADAS_NO_BOLSO")


# --- Explícito ou depende da tática: uma regra por teste -------------------------------------------

def _nivel(p: E.Partida, tipo: str, sid: int) -> tuple:
    oc = [o for o in E.ocorrencias(p).to_dicts() if o["tipo"] == tipo and o["steamid"] == sid]
    assert oc, (tipo, sid)
    return oc[0]["nivel"], oc[0]["motivo"], oc[0]["filtro"]


ISOLADO = SOZINHO


def test_regra_1_eco_e_time_guardando_arma_ficam_de_fora():
    assert _nivel(partida([kill(1000, 6, 1)], BASE, eco={(1, "A")}), E.NAO_TROCOU, 2) == (None, None, E.FILTRO_ECONOMIA)
    p = partida([kill(1000, 6, 1)], BASE, plant=500, vencedor="ct")      # TR plantou e perdeu o round
    assert _nivel(p, E.NAO_TROCOU, 2)[2] == E.FILTRO_GUARDANDO_ARMA
    p = partida([kill(1000, 6, 1)], BASE, plant=500, vencedor="t")       # pós-plant vencido: conta
    assert _nivel(p, E.NAO_TROCOU, 2)[0] == E.EXPLICITO


def test_regra_2_morreu_sozinho_do_lurker():
    p = partida([kill(1000, 6, 1)], ISOLADO, funcoes={(1, "t"): {"funcao": "lurker", "tendencia": False}})
    assert _nivel(p, E.MORREU_SOZINHO, 1)[:2] == (E.DEPENDE, E.MOTIVO_LURKER)


def test_regra_3_primeira_morte_do_entry():
    p = partida([kill(1000, 6, 1)], ISOLADO, funcoes={(1, "t"): {"funcao": "entry", "tendencia": False}})
    assert _nivel(p, E.PRIMEIRA_MORTE_SEM_TROCA, 1)[:2] == (E.DEPENDE, E.MOTIVO_ENTRY)


def test_regra_4_awper_no_angulo_de_abertura():
    p = partida([kill(1000, 6, 1)], ISOLADO, funcoes={(1, "t"): {"funcao": "awper", "tendencia": False}})
    assert _nivel(p, E.PRIMEIRA_MORTE_SEM_TROCA, 1)[:2] == (E.DEPENDE, E.MOTIVO_AWPER)
    assert _nivel(p, E.MORREU_SOZINHO, 1)[:2] == (E.DEPENDE, E.MOTIVO_AWPER)      # a morte é a abertura
    # morte do AWPer sozinho que NÃO é a abertura cai na regra 7
    p = partida([kill(500, 7, 3, pv=(9000, 9000, 0)), kill(1000, 6, 1)], ISOLADO,
                funcoes={(1, "t"): {"funcao": "awper", "tendencia": False}})
    assert _nivel(p, E.MORREU_SOZINHO, 1)[:2] == (E.DEPENDE, E.MOTIVO_GERAL)


def test_regra_5_funcao_so_tendencia_acrescenta_o_motivo():
    p = partida([kill(1000, 6, 1)], ISOLADO, funcoes={(1, "t"): {"funcao": "lurker", "tendencia": True}})
    nivel, motivo, _ = _nivel(p, E.MORREU_SOZINHO, 1)
    assert nivel == E.DEPENDE and motivo == f"{E.MOTIVO_LURKER}; {E.MOTIVO_TENDENCIA}"


def test_regra_6_tipos_explicitos():
    # fase 18: "não trocou" e "possível bait" só existem com o matador visível, e saem sempre explícitos
    p = partida([kill(1000, 6, 1)], BASE, onde_por_tick=RECUA)
    assert _nivel(p, E.NAO_TROCOU, 2)[:2] == (E.EXPLICITO, E.MOTIVO_EXPLICITO[E.NAO_TROCOU])
    assert _nivel(p, E.POSSIVEL_BAIT, 2)[:2] == (E.EXPLICITO, E.MOTIVO_EXPLICITO[E.POSSIVEL_BAIT])
    oc = E.ocorrencias(partida([], {}, cegos=[cegueira(100, 2, 3, 30.0)])).to_dicts()
    assert oc[0]["nivel"] == E.EXPLICITO


def test_regra_7_o_resto_depende_da_tatica():
    p = partida([kill(1000, 6, 1)], ISOLADO)
    assert _nivel(p, E.MORREU_SOZINHO, 1)[:2] == (E.DEPENDE, E.MOTIVO_GERAL)
    assert _nivel(p, E.PRIMEIRA_MORTE_SEM_TROCA, 1)[:2] == (E.DEPENDE, E.MOTIVO_GERAL)


def test_tipos_validados_comeca_vazia():
    assert E.TIPOS_DE_ERRO_VALIDADOS == frozenset()


# --- O corpus ---------------------------------------------------------------------------------------

def _corpus() -> list[Path]:
    return sorted((RAIZ / "data" / "processed").glob(f"match_*/{E.ARQUIVO}"))


def test_nenhuma_ocorrencia_contada_em_round_de_economia():
    """Item 4: toda ocorrência num round de eco ou pistola do time (regra 8i) ficou de fora."""
    arquivos = _corpus()
    if not arquivos:
        pytest.skip("sem as ocorrências gravadas")
    from metrics.economia import grupos_de_compra
    from leitura.insights import resolve_teams
    conferidas = 0
    for arq in arquivos[:6]:
        m = arq.parent.name
        compra = RAIZ / "data" / "interim" / m / "compra.parquet"
        ticks = RAIZ / "data" / "interim" / m / "ticks.parquet"
        if not compra.exists():
            continue
        team_of, _ = resolve_teams(pl.read_parquet(ticks, columns=["steamid", "side", "round_num", "tick", "name"]))
        g = grupos_de_compra(pl.read_parquet(compra), team_of)
        eco = {(int(r["round_num"]), r["time"]) for r in g.filter(
            pl.col("grupo_compra").is_in(["eco", "pistola"]) & (pl.col("peso") > 0)).iter_rows(named=True)}
        oc = pl.read_parquet(arq).filter(pl.col("filtro").is_null())
        for o in oc.iter_rows(named=True):
            assert (o["round_num"], team_of[int(o["steamid"])]) not in eco, (m, o)
            conferidas += 1
    if conferidas == 0:
        pytest.skip("sem interim para conferir")


def test_mesmas_ocorrencias_em_dois_processos_com_hash_diferente(tmp_path):
    """Item 2 (decisão 28) e 18.5, item 3: a mesma partida, PYTHONHASHSEED diferente, a mesma tabela byte a
    byte (com a visão da fase 18) e a mesma tabela de mortes trocadas."""
    m = "match_01"
    if not (RAIZ / "data" / "interim" / m / "ticks.parquet").exists():
        pytest.skip("sem o interim")
    if not V.malha_disponivel("de_ancient"):
        pytest.skip("sem a malha do mapa (py -3.12 -m scripts.visao_malhas)")
    codigo = ("import sys; from metrics import erros as E; p = E.carrega_partida(sys.argv[1]); "
              "E.ocorrencias(p).write_csv(sys.argv[2]); E.mortes_trocadas(p).write_csv(sys.argv[2] + '.mortes')")
    saidas = []
    for semente in ("1", "4242"):
        arq = tmp_path / f"oc_{semente}.csv"
        env = {**os.environ, "PYTHONHASHSEED": semente, "PYTHONPATH": str(RAIZ)}
        subprocess.run([sys.executable, "-c", codigo, m, str(arq)], check=True, cwd=RAIZ, env=env)
        saidas.append(arq.read_bytes() + (tmp_path / f"oc_{semente}.csv.mortes").read_bytes())
    assert saidas[0] == saidas[1] and len(saidas[0]) > 1000


# --- Fase 15: o limiar da partida vale por lado; toda ocorrência tem lado e relógio ----------------

def test_o_limiar_da_partida_vale_por_lado():
    # o mesmo jogador: 15 s no TR e 15 s no CT. Somados (30 s) passariam de 27 s; por lado, nenhum lado passa
    def oc(side, i):
        return {"steamid": 2, "side": side, "valor": 3.0, "filtro": None, "i": i}
    linhas = [oc("t", i) for i in range(5)] + [oc("ct", i) for i in range(5)]
    E._aplica_limiar(linhas, E.SEG_CEGUEIRA_ALIADO, None)
    assert all(o["filtro"] == E.FILTRO_ABAIXO_DO_LIMIAR for o in linhas)
    # 30 s num lado só passa
    so_tr = [oc("t", i) for i in range(10)]
    E._aplica_limiar(so_tr, E.SEG_CEGUEIRA_ALIADO, None)
    assert all(o["filtro"] is None for o in so_tr)


def test_toda_ocorrencia_tem_lado_e_relogio():
    p = partida([kill(1000, 6, 1), kill(2000, 7, 2)], BASE, cegos=[cegueira(500, 2, 3, 5.0)])
    tab = E.ocorrencias(p)
    assert tab.height > 0
    assert tab["side"].null_count() == 0 and tab["relogio"].null_count() == 0
    # 1000 ticks a 64/s = 15,6 s depois do freeze: o relógio desce de 1:55 -> 1:39
    r = tab.filter((pl.col("tipo") == E.PRIMEIRA_MORTE_SEM_TROCA)).row(0, named=True)
    assert r["relogio"] == "1:39"


def test_o_lado_vem_dos_ticks_quando_o_round_nao_tem_kill():
    p = partida([], {}, cegos=[cegueira(100, 2, 3, 5.0)])
    p.lados[(1, 2)] = "t"
    assert E.flash_no_time(p)[0]["side"] == "t"
