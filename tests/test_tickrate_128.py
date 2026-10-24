"""Cada função que recebia o tickrate escrito dá o MESMO resultado em segundos a 64 e a 128 tick.

Cartão 12 (nota 22j), `fix-tickrate-resto`: o dado sintético é o mesmo FATO (os eventos nos mesmos
instantes, em segundos); só a contagem de ticks muda (`seg * tickrate`). Se uma função ainda
assumisse 64, o resultado a 128 sairia diferente do de 64. Não depende de `data/`.

Fora daqui, por precisarem do mapa, de uma partida inteira ou de uma `.dem` (provados no corpus
pelo sha256 dos dados gerados, e não por um dado sintético): `parse_demo`, `visao_da_partida`,
`sub_ratings`, `analyze_round`, `export_replay.build`, `build_lineups`, `verdade_do_arremesso` e os
scripts de calibração (que só trocaram o 64 escrito por `tickrate_da_partida`).
"""
from __future__ import annotations

import numpy as np
import polars as pl
import pytest

from clustering.playstyle import first_contact_per_player_round
from metrics.archetypes import (
    TRADE_WINDOW_SECONDS, bait_events, flash_convertida, marca_repick,
)
from metrics.awp_metrics import (
    AWP_WEAPON_KILLS, AWP_WEAPON_SHOTS, PRE_ENGAGEMENT_WINDOW_SECONDS, classify_engagement_style, first_awp_engagements,
    resolve_engagement_outcomes,
)
from metrics.basic_metrics import (
    calculate_kast, calculate_trade_kills, identify_trade_kills, traded_deaths,
)
from metrics.crosshair import CONTACT_WINDOW_SECONDS, add_contact_window_flag
from metrics.grenade_throws import GRAVIDADE, VZ_PULO, estado_vertical
from metrics.positioning import SETUP_SECONDS_AFTER_FREEZE, setup_snapshot
from metrics.rating import amostras_de_round
from metrics.timing import detect_tickrate
from scripts.fit_rating import tickrate_da_partida

TICKRATES = (64, 128)


def tk(seg: float, tickrate: int) -> int:
    """Os ticks de `seg` segundos."""
    return int(round(seg * tickrate))


def igual_nos_dois(cena):
    """Roda `cena(tickrate)` a 64 e a 128 e exige o mesmo resultado."""
    a, b = (cena(t) for t in TICKRATES)
    assert a == b, f"64 tick: {a}\n128 tick: {b}"
    return a


def u32(df: pl.DataFrame) -> pl.DataFrame:
    return df.with_columns(pl.col("round_num").cast(pl.UInt32))


# --- métricas básicas: janela de trade --------------------------------------

def _kills_de_troca(tr: int, vinganca_s: float) -> pl.DataFrame:
    return u32(pl.DataFrame([
        {"round_num": 1, "tick": 1000, "attacker_steamid": 111, "attacker_side": "t",
         "victim_steamid": 222, "victim_side": "ct", "assister_steamid": None},
        {"round_num": 1, "tick": 1000 + tk(vinganca_s, tr), "attacker_steamid": 333, "attacker_side": "ct",
         "victim_steamid": 111, "victim_side": "t", "assister_steamid": None},
    ], schema_overrides={"assister_steamid": pl.UInt64}))


@pytest.mark.parametrize("vinganca_s,esperado", [(2.0, [False, True]), (10.0, [False, False])])
def test_trade_kill_na_janela_em_segundos(vinganca_s, esperado):
    def cena(tr):
        k = _kills_de_troca(tr, vinganca_s)
        return (identify_trade_kills(k, trade_window_seconds=5.0, tickrate=tr).sort("tick")["is_trade_kill"].to_list(),
                traded_deaths(k, trade_window_seconds=5.0, tickrate=tr)["steamid"].to_list())
    marcas, vingados = igual_nos_dois(cena)
    assert marcas == esperado and vingados == ([222] if True in esperado else [])


def test_kast_e_trade_kills_usam_o_tickrate_recebido():
    ticks = pl.DataFrame({
        "round_num": [1] * 3, "steamid": [111, 222, 333], "name": ["a", "b", "c"], "side": ["t", "ct", "ct"],
        "tick": [100] * 3, "health": [100] * 3,
    }).with_columns(pl.col("round_num").cast(pl.UInt32), pl.col("steamid").cast(pl.UInt64))
    from metrics.basic_metrics import roster_per_round

    def cena(tr):
        k = _kills_de_troca(tr, 2.0)
        kast, _ = calculate_kast(k, roster_per_round(ticks), tickrate=tr)
        _, resumo = calculate_trade_kills(k, roster_per_round(ticks), tickrate=tr)
        return (sorted(kast.select("steamid", "was_traded", "kast_round").rows()),
                sorted(resumo.select("steamid", "total_trade_kills").rows()))
    igual_nos_dois(cena)


# --- AWP --------------------------------------------------------------------

def _awp(tr: int, andando: bool):
    """Um AWPer com o primeiro tiro 6,5 s depois do freeze; anda 200 u/s na janela ou fica parado."""
    freeze = 1000
    tiro = freeze + tk(6.5, tr)
    rounds = u32(pl.DataFrame({"round_num": [1], "freeze_end": [freeze]}))
    shots = u32(pl.DataFrame({
        "round_num": [1], "tick": [tiro], "weapon": [AWP_WEAPON_SHOTS], "player_steamid": [7], "player_name": ["x"],
        "player_X": [0.0], "player_Y": [0.0], "player_Z": [0.0], "player_place": ["A"],
        "player_is_scoped": [True], "player_side": ["ct"]}))
    n = tk(PRE_ENGAGEMENT_WINDOW_SECONDS, tr)
    pts = np.arange(tiro - n, tiro + 1)
    x = (pts - pts[0]) / tr * 200.0 if andando else np.zeros(len(pts))
    ticks = u32(pl.DataFrame({"round_num": [1] * len(pts), "steamid": [7] * len(pts), "tick": pts,
                              "X": x, "Y": np.zeros(len(pts)), "is_scoped": [False] * len(pts)}))
    kills = u32(pl.DataFrame({"round_num": [1], "tick": [tiro + tk(1.0, tr)], "attacker_steamid": [7],
                              "victim_steamid": [9], "weapon": [AWP_WEAPON_KILLS]}))
    eng = first_awp_engagements(shots, rounds, tr)
    est = classify_engagement_style(eng, ticks, tickrate=tr)
    res = resolve_engagement_outcomes(eng, kills, tickrate=tr)
    return (eng["time_to_first_shot_s"].to_list(), est["style"].to_list(),
            [round(v, 6) for v in est["slow_fraction"].to_list()],
            [round(v, 3) for v in est["path_distance"].to_list()],
            res["outcome"].to_list())


@pytest.mark.parametrize("andando", [True, False])
def test_awp_tempo_estilo_e_desfecho_em_segundos(andando):
    tempo, estilo, *_ = igual_nos_dois(lambda tr: _awp(tr, andando))
    assert tempo == [6.5] and estilo[0] != "indeterminado"


# --- crosshair e posicionamento --------------------------------------------

def test_janela_de_contato_do_crosshair_em_segundos():
    def cena(tr):
        amostras = u32(pl.DataFrame({
            "round_num": [1] * 4, "steamid": [5] * 4,
            "tick": [tk(s, tr) for s in (0.0, 0.5, 1.5, 2.5)]}))
        tiros = u32(pl.DataFrame({"round_num": [1], "player_steamid": [5], "tick": [tk(2.0, tr)]}))
        dano = u32(pl.DataFrame({"round_num": [1], "attacker_steamid": [None], "victim_steamid": [None],
                                 "tick": [0]}, schema_overrides={"attacker_steamid": pl.Int64,
                                                                 "victim_steamid": pl.Int64}))
        out = add_contact_window_flag(amostras, tiros, dano, tickrate=tr)
        return out.sort("tick")["in_contact_window"].to_list()
    assert igual_nos_dois(cena) == [False, False, True, False] and CONTACT_WINDOW_SECONDS == 1.0


def test_setup_snapshot_pega_o_instante_em_segundos():
    def cena(tr):
        passo = tr // 8
        pts = np.arange(0, tk(30, tr) + 1, passo)
        ticks = u32(pl.DataFrame({
            "round_num": [1] * len(pts), "steamid": [3] * len(pts), "tick": pts + 500, "name": ["j"] * len(pts),
            "side": ["ct"] * len(pts), "place": ["A"] * len(pts), "X": pts / tr * 10.0,
            "Y": [0.0] * len(pts), "Z": [0.0] * len(pts), "is_alive": [True] * len(pts)}))
        rounds = u32(pl.DataFrame({"round_num": [1], "freeze_end": [500]}))
        return setup_snapshot(ticks, rounds, tickrate=tr)["X"].to_list()
    assert igual_nos_dois(cena) == [SETUP_SECONDS_AFTER_FREEZE * 10.0]


# --- clustering -------------------------------------------------------------

def test_primeiro_contato_em_segundos():
    def cena(tr):
        rounds = u32(pl.DataFrame({"round_num": [1], "freeze_end": [1000], "end": [1000 + tk(115, tr)]}))
        dano = u32(pl.DataFrame({"round_num": [1], "attacker_steamid": [4], "victim_steamid": [5],
                                 "tick": [1000 + tk(8.5, tr)]}))
        return first_contact_per_player_round(dano, rounds, tr).sort("steamid")["time_of_first_contact_s"].to_list()
    assert igual_nos_dois(cena) == [8.5, 8.5]


# --- papéis (archetypes) ----------------------------------------------------

def test_bait_events_janela_de_troca_em_segundos():
    """Companheiro morre; o observado vinga (dentro / fora da janela de troca)."""
    def cena(tr, vinganca_s):
        base = 1000
        k = u32(pl.DataFrame([
            {"round_num": 1, "tick": base, "attacker_steamid": 99, "victim_steamid": 2,
             "victim_X": 0.0, "victim_Y": 0.0},
            {"round_num": 1, "tick": base + tk(vinganca_s, tr), "attacker_steamid": 1, "victim_steamid": 99,
             "victim_X": 0.0, "victim_Y": 0.0}]))
        ticks = u32(pl.DataFrame({"round_num": [1, 1], "tick": [base, base], "steamid": [1, 2],
                                  "X": [300.0, 0.0], "Y": [0.0, 0.0], "is_alive": [True, True]}))
        return bait_events(k, ticks, {1: "A", 2: "A", 99: "B"}, tickrate=tr)["traded"].to_list()
    dentro = igual_nos_dois(lambda tr: cena(tr, TRADE_WINDOW_SECONDS - 1.0))
    fora = igual_nos_dois(lambda tr: cena(tr, TRADE_WINDOW_SECONDS + 1.0))
    assert dentro == [True] and fora == [False]


def test_flash_convertida_janela_em_segundos():
    def cena(tr, kill_s):
        cegas = pl.DataFrame({"round_num": [1], "tick": [1000], "attacker_steamid": [1], "attacker_side": ["t"],
                              "user_steamid": [10], "user_side": ["ct"]})
        mortes = pl.DataFrame({"round_num": [1], "tick": [1000 + tk(kill_s, tr)], "victim_steamid": [10],
                               "attacker_steamid": [3], "attacker_side": ["t"]})
        return flash_convertida(cegas, mortes, tickrate=tr).height
    assert igual_nos_dois(lambda tr: cena(tr, 2.0)) == 1
    assert igual_nos_dois(lambda tr: cena(tr, 4.0)) == 0


def test_repick_janela_de_sair_e_voltar_em_segundos():
    """Sai do ângulo a 120 u em 1 s e volta em 2 s; o dano cai no meio (t = 1,5 s)."""
    def cena(tr):
        seg = [0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0]
        x = [0.0, 60.0, 120.0, 120.0, 60.0, 5.0, 0.0]
        ticks = u32(pl.DataFrame({"round_num": [1] * 7, "steamid": [1] * 7, "tick": [tk(s, tr) for s in seg],
                                  "X": x, "Y": [0.0] * 7}))
        styles = u32(pl.DataFrame({"round_num": [1], "steamid": [1], "engagement_tick": [tk(3.0, tr)],
                                   "net_displacement": [0.0], "path_distance": [400.0]}))
        kills = u32(pl.DataFrame({"round_num": [1], "tick": [tk(3.0, tr)], "victim_X": [0.0], "victim_Y": [0.0],
                                  "weapon": ["ak47"], "attacker_steamid": [1], "victim_steamid": [2]}))
        dano = u32(pl.DataFrame({"round_num": [1], "tick": [tk(1.5, tr)], "attacker_steamid": [1],
                                 "victim_steamid": [2]}))
        r = marca_repick(styles, ticks, kills, dano, None, tickrate=tr)
        return r["repick"].to_list(), r["evento_no_angulo"].to_list(), r["saidas"].to_list()
    assert igual_nos_dois(cena)[0] == [True]


# --- rating -----------------------------------------------------------------

def test_amostras_do_round_swing_com_o_tempo_em_segundos():
    def cena(tr):
        base = 1000
        rounds = u32(pl.DataFrame({"round_num": [1], "freeze_end": [base], "bomb_plant": [base + tk(40, tr)]}))
        kills = u32(pl.DataFrame({"round_num": [1, 1], "tick": [base + tk(20, tr), base + tk(50, tr)],
                                  "victim_steamid": [2, 3]}))
        grupos = u32(pl.DataFrame({"round_num": [1] * 4, "steamid": [1, 2, 3, 4], "equip": [4000, 4000, 3000, 3000],
                                   "side": ["ct", "ct", "t", "t"]}))
        X, y = amostras_de_round(kills, rounds, grupos, {1: "A", 2: "A", 3: "B", 4: "B"}, {1: "A"}, tr)
        return X.round(9).tolist(), y.tolist()
    X, _ = igual_nos_dois(cena)
    assert len(X) == 4 and round(20 / 115, 9) in X[0]   # o relógio do round (20 s), normalizado


# --- gravidade dos arremessos ----------------------------------------------

def _pulo(tr: int, subida_s: float):
    """Pés de um jogador que pula `subida_s` antes de soltar a granada (física discreta do jogo)."""
    antes = tk(0.25, tr)                      # chão antes do pulo
    no_ar = tk(subida_s, tr)                  # ticks entre a decolagem e a soltura
    n = antes + no_ar + 2
    dt = 1.0 / tr
    z, v = [0.0], VZ_PULO
    for k in range(1, n):
        if k <= antes:
            z.append(0.0)
        else:
            v -= GRAVIDADE * dt            # a velocidade cai antes de mover (a convenção do jogo)
            z.append(z[-1] + v * dt)
    xy = np.column_stack([np.arange(n) / tr * 250.0, np.zeros(n)])
    ev = estado_vertical(np.array(z), xy, tr)
    # a vz da regra fixa é constante; a "real" é a derivada do passo, que muda com o tamanho do passo
    return ev["regra"], ev["no_ar"], round(ev["vz"], 3) if ev["regra"] == "regra fixa 6-13" else None


def test_estado_vertical_gravidade_e_janelas_em_segundos():
    """Pulo e soltura 0,125 s depois (8 ticks a 64, 16 a 128): a mesma regra fixa; 0,5 s: vz real."""
    regra, no_ar, vz = igual_nos_dois(lambda tr: _pulo(tr, 0.125))
    assert regra == "regra fixa 6-13" and no_ar is True and vz is not None
    regra, no_ar, _ = igual_nos_dois(lambda tr: _pulo(tr, 0.5))
    assert regra == "vz real 19+" and no_ar is True


def test_estado_vertical_no_chao_a_128_nao_vira_ar():
    for tr in TICKRATES:
        n = tk(1.0, tr)
        ev = estado_vertical(np.zeros(n), np.column_stack([np.arange(n) / tr * 250.0, np.zeros(n)]), tr)
        assert ev["regra"] == "chão" and ev["no_ar"] is False


# --- as calibrações leem o tickrate da partida ------------------------------

def test_tickrate_da_partida_vem_do_timer_da_bomba():
    def partida(tr):
        rounds = pl.DataFrame({"round_num": [1, 2], "reason": ["bomb_exploded"] * 2,
                               "bomb_plant": [1000, 90000], "end": [1000 + 40 * tr, 90000 + 40 * tr]})
        return {"rounds": rounds, "ticks": pl.DataFrame({"tick": [0]})}
    assert [tickrate_da_partida(partida(tr)) for tr in TICKRATES] == [64, 128]
    assert detect_tickrate(partida(128)["rounds"])["tickrate"] == 128
