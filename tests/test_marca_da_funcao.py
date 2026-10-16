"""A marca "(tendência)" da função dominante pela chance ao acaso (cartão 2 do Pedro, decisão 39).

Uma marca só, com dois motivos: a reamostragem instável (fase 12) OU a chance ao acaso gravada fora do
alfa. A função continua aparecendo e nenhum rótulo muda; o motivo vai na dica (`title`)."""
from __future__ import annotations

import json
from pathlib import Path

import polars as pl
import pytest

from leitura import marca_da_funcao as MF
from metrics import structural_roles as sr

RAIZ = Path(__file__).resolve().parent.parent


def test_a_dica_diz_o_motivo_ou_os_dois():
    assert sr.dica_da_tendencia(12, 0.09, 0.95) == (
        "Função dominante neste lado, mas com 12 rounds pode ser acaso (chance de 9%)")
    assert sr.dica_da_tendencia(12, 0.01, 0.61) == (
        "Função dominante neste lado, mas se mantém em 61% das reamostragens dos rounds")
    assert sr.dica_da_tendencia(10, 0.892626, 0.64) == (
        "Função dominante neste lado, mas com 10 rounds pode ser acaso (chance de 89%) "
        "e se mantém em 64% das reamostragens dos rounds")
    assert sr.dica_da_tendencia(12, 0.01, 0.95) == ""
    assert sr.dica_da_tendencia(12, None, None) == ""


def test_a_chance_perto_do_corte_ganha_uma_casa():
    # 6 de 12 no CT: 0,0544 escrito "5%" não se leria como acima de 5%
    assert sr.dica_da_tendencia(12, sr.chance_ao_acaso(6, 12, "ct"), None).endswith("(chance de 5,4%)")


def test_so_a_funcao_dominante_ganha_marca():
    from tests.test_structural_roles import _por_round_sintetico
    resumo = pl.concat([
        sr.resume_por_lado(_por_round_sintetico({"entry": 4}, n=12)),          # 4 de 12 no TR: acaso
        sr.resume_por_lado(_por_round_sintetico({"entry": 10}, n=12)).with_columns(pl.lit(2, dtype=pl.UInt64).alias("steamid")),
    ], how="vertical_relaxed")
    marca = sr.marca_da_funcao(resumo, pl.DataFrame(schema={"steamid": pl.UInt64, "side": pl.String,
                                                            "funcao": pl.String, "estabilidade": pl.Float64}))
    sid1 = int(resumo["steamid"][0])
    assert set(marca) == {(sid1, "t")} and marca[(sid1, "t")]["funcao"] == "entry"
    assert "pode ser acaso" in marca[(sid1, "t")]["dica"]


def test_aplica_poe_a_mesma_marca_sem_mudar_a_etiqueta_sem_marca():
    payload = {"player_profile": [{"name": "a", "steamid": 1}, {"name": "b", "steamid": 2}]}
    perfil = {"jogadores": [
        {"name": "a", "funcoes": [{"lado": "CT", "texto": "Âncora", "tendencia": False, "neutro": False},
                                  {"lado": "TR", "texto": "sem função definida", "tendencia": False, "neutro": True}]},
        {"name": "b", "funcoes": [{"lado": "TR", "texto": "Lurker (tendência)", "tendencia": True, "neutro": True}]}]}
    marca = {(1, "ct"): {"funcao": "ancora", "dica": "x"}, (1, "t"): {"funcao": "entry", "dica": "y"},
             (2, "t"): {"funcao": "lurker", "dica": "z"}}
    MF.aplica(perfil, payload, marca)
    a, b = perfil["jogadores"]
    assert a["funcoes"][0] == {"lado": "CT", "texto": "Âncora (tendência)", "tendencia": True, "neutro": True, "dica": "x"}
    assert a["funcoes"][1] == {"lado": "TR", "texto": "sem função definida", "tendencia": False, "neutro": True}
    assert b["funcoes"][0]["texto"] == "Lurker (tendência)" and b["funcoes"][0]["dica"] == "z"
    assert MF.aplica(None, payload, marca) is None


def test_na_partida_real_a_marca_vai_ao_bloco_da_pagina():
    """match_52: ZywOo AWPer de CT em 6 de 12 rounds (chance 5,4%) sai "AWPer (tendência)"."""
    base = RAIZ / "data" / "processed" / "match_52"
    if not (base / "structural_roles.parquet").exists() or not (base / "web_payload.json").exists():
        pytest.skip("sem a partida processada")
    from scripts.build_web_page import dados_da_pagina
    perfil = dados_da_pagina("match_52")["perfil"]
    zywoo = next(j for j in perfil["jogadores"] if j["name"] == "ZywOo")
    ct = next(f for f in zywoo["funcoes"] if f["lado"] == "CT")
    assert ct["texto"] == "AWPer (tendência)" and ct["tendencia"] and ct["neutro"]
    assert ct["dica"].startswith("Função dominante neste lado, mas com 12 rounds pode ser acaso (chance de 5,4%)")
    # o resumo gravado não muda: a função continua a mesma
    resumo = pl.read_parquet(base / "structural_roles_summary.parquet")
    assert resumo.filter((pl.col("name") == "ZywOo") & (pl.col("side") == "ct"))["funcao"].to_list() == ["awper"]
    payload = json.loads((base / "web_payload.json").read_text(encoding="utf-8"))
    assert any(r["name"] == "ZywOo" and r["side"] == "ct" and r["funcao"] == "awper" for r in payload["structural_roles"])
