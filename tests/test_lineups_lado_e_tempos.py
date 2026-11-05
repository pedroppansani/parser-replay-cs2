"""Reescrever R0: a biblioteca de arremessos grava o lado de quem lançou e os tempos reais da demo (voo e, no molotov, o efeito)."""
from __future__ import annotations

import json
from pathlib import Path

import polars as pl
import pytest

from scripts.build_lineups import MAX_VOO_S, tempos_e_lado

RAIZ = Path(__file__).resolve().parent.parent
TR = 64


def _tabelas():
    """Uma partida pequena: o entity_id 7 é reaproveitado (duas smokes), e há um molotov, uma HE e uma flash sem detonação."""
    pr = pl.DataFrame({
        "round_num": [1, 2, 1, 1, 1],
        "entity_id": [7, 7, 20, 30, 40],
        "steamid": [111, 222, 111, 333, 333],
        "tick_soltura": [1000, 5000, 1100, 1200, 1300],
        "kind": ["smoke", "smoke", "molotov", "he", "flash"],
    })
    ticks = pl.DataFrame({"steamid": [111, 111, 222, 333], "tick": [1000, 1100, 5000, 1200], "side": ["ct", "ct", "t", "t"]})
    t = {
        "ticks": ticks,
        "smokegrenade_detonate": pl.DataFrame({"entityid": [7, 7], "tick": [1192, 5256]}),   # 3 s e 4 s depois de soltar
        "hegrenade_detonate": pl.DataFrame({"entityid": [30], "tick": [1304]}),               # 1,625 s
        "flashbang_detonate": pl.DataFrame({"entityid": [], "tick": []}, schema={"entityid": pl.Int64, "tick": pl.Int64}),
        "infernos": pl.DataFrame({"thrower_steamid": [111, 111], "round_num": [1, 1], "start_tick": [900, 1228], "end_tick": [1300, 1678]}),
    }
    return t, pr


def test_o_voo_e_o_efeito_vem_do_evento_certo_mesmo_com_entity_id_reaproveitado():
    t, pr = _tabelas()
    r = {(x["round_num"], x["entity_id"]): x for x in tempos_e_lado(t, pr, TR).iter_rows(named=True)}
    assert r[(1, 7)]["voo_s"] == 3.0 and r[(2, 7)]["voo_s"] == 4.0          # cada smoke acha a SUA detonação
    assert r[(1, 30)]["voo_s"] == 1.62
    assert r[(1, 20)]["voo_s"] == 2.0 and r[(1, 20)]["efeito_s"] == 7.03    # o fogo de antes de soltar (start 900) não conta
    assert r[(1, 40)]["voo_s"] is None and r[(1, 40)]["efeito_s"] is None   # sem detonação na demo: nulo, nunca inventado
    assert r[(1, 7)]["efeito_s"] is None                                    # a smoke não tem fim na demo


def test_o_lado_e_o_da_pessoa_no_tick_da_soltura():
    t, pr = _tabelas()
    r = {(x["round_num"], x["entity_id"]): x["lado"] for x in tempos_e_lado(t, pr, TR).iter_rows(named=True)}
    assert r[(1, 7)] == "ct" and r[(2, 7)] == "t" and r[(1, 30)] == "t"


def test_voo_acima_do_limite_vira_nulo():
    t, pr = _tabelas()
    t["smokegrenade_detonate"] = pl.DataFrame({"entityid": [7], "tick": [1000 + int((MAX_VOO_S + 1) * TR)]})
    r = {(x["round_num"], x["entity_id"]): x for x in tempos_e_lado(t, pr, TR).iter_rows(named=True)}
    assert r[(1, 7)]["voo_s"] is None


def _bibliotecas():
    arqs = sorted((RAIZ / "data" / "lineups").glob("de_*.json"))
    if not arqs:
        pytest.skip("biblioteca de arremessos não gerada (scripts/build_lineups.py)")
    return [json.loads(a.read_text(encoding="utf-8")) for a in arqs]


def test_toda_entrada_da_biblioteca_tem_lado_e_ele_confere_com_o_replay_da_partida():
    lados = {}
    for bib in _bibliotecas():
        for a in bib["arremessos"]:
            assert a["lado"] in ("ct", "t"), a["id"]
            lados.setdefault(a["partida"], []).append(a)
    conferidos = 0
    for partida, entradas in lados.items():
        arq = RAIZ / "data" / "processed" / partida / "replay.json"
        if not arq.exists():
            continue
        rounds = {r["round"]: {p["name"]: p["side"] for p in r["players"]} for r in json.loads(arq.read_text(encoding="utf-8"))["rounds"]}
        for a in entradas:
            esperado = rounds.get(a["round"], {}).get(a["jogador"])
            if esperado is not None:
                assert a["lado"] == esperado, (a["id"], a["lado"], esperado)
                conferidos += 1
    assert conferidos > 20000


def test_voo_e_efeito_estao_em_faixas_honestas_e_quase_sempre_presentes():
    por_tipo: dict[str, list] = {}
    for bib in _bibliotecas():
        for a in bib["arremessos"]:
            por_tipo.setdefault(a["arma"], []).append(a)
            if a["voo_s"] is not None:
                assert 0 <= a["voo_s"] <= MAX_VOO_S, a["id"]
            if a["efeito_s"] is not None:
                assert a["arma"] == "molotov" and 0 < a["efeito_s"] <= 7.1, a["id"]   # só o molotov tem fim de efeito medido
    for tipo in ("smoke", "he", "flash", "molotov"):
        com = sum(a["voo_s"] is not None for a in por_tipo[tipo])
        assert com >= 0.95 * len(por_tipo[tipo]), (tipo, com, len(por_tipo[tipo]))
