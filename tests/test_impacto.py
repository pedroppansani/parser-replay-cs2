"""Métricas de impacto (fase 7, item 7.2): utilidade que rendeu, trocas e situações.

Sem gabarito publicado para a maioria delas, a validação é por invariante no
corpus e por casos sintéticos. As contagens que já existem em outro módulo
(kills de troca, aberturas) têm de bater exatamente com ele.
"""
from __future__ import annotations

import json
from pathlib import Path

import polars as pl
import pytest

from metrics.constantes import JANELA_DE_TRADE_S
from metrics.impacto import (CATEGORIAS_DE_IMPACTO, ROTULOS, TAXAS_DE_IMPACTO, TEMPO_DA_TROCA, _aberturas_por_round,
                             _situacoes_por_round, _trocas, para_a_pagina)

RAIZ = Path(__file__).resolve().parent.parent
PROCESSED = RAIZ / "data" / "processed"


def _kill(rn, tick, atk, atk_side, vit, vit_side, weapon="ak47"):
    return {"round_num": rn, "tick": tick, "attacker_steamid": atk, "attacker_side": atk_side,
            "victim_steamid": vit, "victim_side": vit_side, "weapon": weapon}


def _kills(linhas):
    return pl.DataFrame(linhas, schema={"round_num": pl.UInt32, "tick": pl.Int64, "attacker_steamid": pl.UInt64,
                                        "attacker_side": pl.String, "victim_steamid": pl.UInt64,
                                        "victim_side": pl.String, "weapon": pl.String})


def test_a_abertura_e_a_primeira_kill_em_inimigo_e_conta_por_lado():
    k = _kills([_kill(1, 100, 1, "ct", 2, "ct"),       # fogo amigo não abre
                _kill(1, 200, 3, "t", 1, "ct"),        # abertura: 3 (TR) vence, 1 (CT) perde
                _kill(1, 300, 4, "ct", 3, "t")])
    a = _aberturas_por_round(k).sort("steamid")
    assert a.to_dicts() == [{"round_num": 1, "steamid": 1, "side": "ct", "venceu_abertura": False},
                            {"round_num": 1, "steamid": 3, "side": "t", "venceu_abertura": True}]


def test_a_troca_conta_uma_vez_por_kill_com_o_tempo_ate_a_morte_mais_recente():
    # 9 (TR) mata 1 e 2 (CT); 3 (CT) mata 9 meio segundo depois da segunda morte
    k = _kills([_kill(1, 1000, 9, "t", 1, "ct"), _kill(1, 1064, 9, "t", 2, "ct"), _kill(1, 1096, 3, "ct", 9, "t")])
    t = _trocas(k, 64).to_dicts()
    assert t == [{"round_num": 1, "steamid": 3, "segundos_da_troca": 0.5}]


def test_pos_plant_so_conta_quem_estava_vivo_no_plant_e_kills_depois_dele():
    rounds = pl.DataFrame({"round_num": [1], "bomb_plant": [500], "end": [900], "winner": ["t"]},
                          schema={"round_num": pl.UInt32, "bomb_plant": pl.Int64, "end": pl.Int32, "winner": pl.String})
    presentes = pl.DataFrame({"round_num": [1, 1, 1], "steamid": [1, 2, 3], "side": ["t", "t", "ct"]},
                             schema={"round_num": pl.UInt32, "steamid": pl.UInt64, "side": pl.String})
    k = _kills([_kill(1, 400, 3, "ct", 2, "t"),           # 2 morre ANTES do plant: fora
                _kill(1, 600, 1, "t", 3, "ct")])          # 1 mata depois do plant
    s = _situacoes_por_round(k, rounds, presentes).sort("steamid").to_dicts()
    assert [r["steamid"] for r in s] == [1, 3]
    um = s[0]
    assert um["kills_depois_do_plant"] == 1 and um["venceu"] and um["sobreviveu"]
    assert s[1]["side"] == "ct" and not s[1]["venceu"] and not s[1]["sobreviveu"]


def test_toda_metrica_tem_rotulo_e_grupo_e_a_pagina_recebe_o_texto_do_python():
    chaves = [c for c, _, _ in TAXAS_DE_IMPACTO] + [TEMPO_DA_TROCA]
    assert set(chaves) == set(ROTULOS) == {c for cs in CATEGORIAS_DE_IMPACTO.values() for c in cs}
    pg = para_a_pagina()
    assert pg["titulo"] and pg["texto"]
    # design-B3 (entrega-sala-de-demo §7.2): todos os grupos abrem fechados; antes a Utilidade abria aberta
    assert [g["nome"] for g in pg["grupos"] if g["aberto"]] == []


# --- invariantes no corpus -----------------------------------------------------

def _corpus():
    arquivos = sorted(PROCESSED.glob("match_*/impacto_summary.parquet"))
    if not arquivos:
        pytest.skip("sem o processado com impacto")
    return arquivos


def test_dano_de_utilidade_nao_passa_do_dano_total():
    for f in _corpus():
        imp = pl.read_parquet(f).select("steamid", (pl.col("dano_de_he") + pl.col("dano_de_molotov")).alias("util"))
        adr = pl.read_parquet(f.parent / "adr_summary.parquet").select("steamid", "total_damage")
        ruins = imp.join(adr, on="steamid").filter(pl.col("util") > pl.col("total_damage") + 1e-9)
        assert ruins.height == 0, (f.parent.name, ruins)


def test_cegueira_nao_passa_da_duracao_dos_rounds_vezes_os_cinco_inimigos():
    for f in _corpus():
        meta = json.loads((f.parent / "match_meta.json").read_text(encoding="utf-8"))
        r = pl.read_parquet(f.parent / "rounds.parquet")
        teto = float(((r["end"] - r["freeze_end"]) / meta.get("tickrate", 64)).sum()) * 5
        imp = pl.read_parquet(f)
        assert (imp["segundos_de_cegueira"] <= teto).all(), f.parent.name


def test_contagens_batem_com_os_modulos_que_ja_as_tinham():
    for f in _corpus():
        imp = pl.read_parquet(f)
        tk = pl.read_parquet(f.parent / "trade_kills_summary.parquet").select("steamid", "total_trade_kills")
        j = imp.join(tk, on="steamid", how="left")
        assert (j["trocas_feitas"] == j["total_trade_kills"].fill_null(0)).all(), f.parent.name
        ins = json.loads((f.parent / "insights.json").read_text(encoding="utf-8"))
        aberturas = {p["steamid"]: p["opening_kills"] for p in ins["players"]}
        for r in imp.iter_rows(named=True):
            assert r["aberturas_vencidas_tr"] + r["aberturas_vencidas_ct"] == aberturas.get(r["steamid"], 0), f.parent.name
        # um duelo de abertura por round com kill: vitórias = derrotas, somadas no time todo
        assert imp["aberturas_vencidas_tr"].sum() + imp["aberturas_vencidas_ct"].sum() == \
            (imp["duelos_de_abertura_tr"].sum() + imp["duelos_de_abertura_ct"].sum()) / 2


def test_situacoes_e_trocas_ficam_dentro_dos_limites_do_jogo():
    for f in _corpus():
        imp = pl.read_parquet(f)
        r = pl.read_parquet(f.parent / "rounds.parquet")
        plants = r.filter(pl.col("bomb_plant").is_not_null()).height
        assert (imp["rounds_vivo_no_plant_tr"] <= plants).all() and (imp["rounds_vivo_no_plant_ct"] <= plants).all()
        assert (imp["pos_plant_vencidos"] <= imp["rounds_vivo_no_plant_tr"]).all()
        assert (imp["retakes_vencidos"] <= imp["rounds_vivo_no_plant_ct"]).all()
        tempos = imp[TEMPO_DA_TROCA].drop_nulls()
        assert ((tempos > 0) & (tempos <= JANELA_DE_TRADE_S)).all(), f.parent.name


def test_o_perfil_traz_as_metricas_novas_com_bruto_regua_e_amostra():
    f = PROCESSED / "match_01" / "player_profile.parquet"
    if not f.exists():
        pytest.skip("sem o processado")
    p = pl.read_parquet(f)
    for c in [c for c, _, _ in TAXAS_DE_IMPACTO]:
        for sufixo in ("", "_n", "_d", "_ref", "_fraco"):
            assert c + sufixo in p.columns, c + sufixo


# --- economia (7.2.3): grupos de compra da regra 8i ----------------------------

def test_os_grupos_de_compra_sao_a_tabela_da_8i_sem_limiar_novo():
    from metrics.economia import ROUND_DE_PISTOLA, grupo_de_compra
    from metrics.rating import GRUPOS
    esperado = {
        ("pistola_inicial", False): "eco", ("pistola_melhorada", False): "eco",
        ("pistola_inicial", True): ROUND_DE_PISTOLA, ("pistola_melhorada", True): "forca",
        ("smg_shotgun", True): "forca", ("smg_shotgun", False): "forca",
        ("rifle_t2", True): "forca", ("rifle_t2", False): "forca",
        ("rifle_t1", False): "forca", ("sniper", False): "forca",
        ("rifle_t1", True): "cheia", ("sniper", True): "cheia",
    }
    assert {(g, c) for g in GRUPOS for c in (True, False)} == set(esperado)   # toda classe da 8i coberta
    for (g, c), grupo in esperado.items():
        assert grupo_de_compra(g, c) == grupo, (g, c)


def test_o_empate_da_8i_divide_o_round_entre_os_grupos():
    from metrics.economia import grupos_de_compra
    compra = pl.DataFrame({
        "round_num": [5] * 10,
        "steamid": list(range(1, 11)),
        # time A: dois de rifle, dois de pistola melhorada, um de SMG, todos com colete (empate rifle x pistola)
        "inventory": [["AK-47"], ["AK-47"], ["Desert Eagle"], ["Desert Eagle"], ["MP9"],
                      ["M4A4"]] + [["M4A4"]] * 4,
        "armor_value": [100] * 10,
    })
    team_of = {i: ("A" if i <= 5 else "B") for i in range(1, 11)}
    g = grupos_de_compra(compra, team_of)
    a = {r["grupo_compra"]: r["peso"] for r in g.filter(pl.col("time") == "A").iter_rows(named=True)}
    b = {r["grupo_compra"]: r["peso"] for r in g.filter(pl.col("time") == "B").iter_rows(named=True)}
    assert a == {"cheia": 0.5, "forca": 0.5} and b == {"cheia": 1.0}


def test_economia_fica_dentro_dos_limites_do_jogo():
    for f in _corpus():
        imp = pl.read_parquet(f)
        if "rounds_cheia" not in imp.columns:
            pytest.skip("processado sem a economia (VERSAO_DAS_METRICAS < 21)")
        perfil = pl.read_parquet(f.parent / "player_profile.parquet").select("steamid", "rounds_jogados")
        j = imp.join(perfil, on="steamid")
        soma = j["rounds_eco"] + j["rounds_forca"] + j["rounds_cheia"]
        assert ((soma <= j["rounds_jogados"] + 1e-9)).all(), f.parent.name
        for g in ("eco", "forca", "cheia"):
            assert (j[f"rounds_inteiros_{g}"].fill_null(0) <= j[f"rounds_{g}"] + 1e-9).all(), (f.parent.name, g)
            assert (j[f"kast_rounds_{g}"] <= j[f"rounds_{g}"] + 1e-9).all()
        assert (imp["rounds_contra_cheia"] + imp["rounds_contra_eco"] <= j["rounds_jogados"] + 1e-9).all()
