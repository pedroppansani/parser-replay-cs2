"""Nenhum caminho de reserva age em silêncio (auditoria, item 4.4).

Cada fallback virou uma marca `modo_degradado` com o motivo, e a interface
esconde o número afetado. Nenhum rótulo negativo sai de dado ausente.
"""
from __future__ import annotations

import json
from pathlib import Path

import polars as pl
import pytest

import metrics.rating as r
from metrics.archetypes import archetype_indices

RAIZ = Path(__file__).resolve().parent.parent
INTERIM = RAIZ / "data" / "interim"
PARTIDA = "match_01"


@pytest.fixture(scope="module")
def contexto():
    from tests.test_rating import _contexto
    if not (INTERIM / PARTIDA / "kills.parquet").exists():
        pytest.skip("sem o interim da match_01")
    return _contexto(PARTIDA)


def test_sem_modelo_passado_o_rating_usa_o_global_da_referencia(contexto):
    """Antes, `modelo=None` treinava um modelo SÓ naquela partida (a decisão 11 proíbe)."""
    tabelas, team_of, venc, kast = contexto
    ref = r.carrega_referencia()
    _, com_global = r.rating(tabelas, team_of, venc, kast, 64, referencia=ref,
                             modelo=r.ModeloDeRound.da_referencia(ref["modelo_de_round"]))
    _, sem_passar = r.rating(tabelas, team_of, venc, kast, 64, referencia=ref)
    a = {j["steamid"]: j["rating"] for j in com_global["jogadores"]}
    b = {j["steamid"]: j["rating"] for j in sem_passar["jogadores"]}
    assert a == b
    assert not any("modelo de round" in m for m in sem_passar["modo_degradado"])


def test_sem_referencia_o_modelo_da_partida_e_declarado(contexto):
    tabelas, team_of, venc, kast = contexto
    _, resumo = r.rating(tabelas, team_of, venc, kast, 64, referencia=None)
    assert any("modelo de round treinado só nesta partida" in m for m in resumo["modo_degradado"])


def test_com_poucos_eventos_e_sem_modelo_global_o_swing_neutro_e_declarado(contexto):
    tabelas, team_of, venc, kast = contexto
    poucos = {**tabelas, "rounds": tabelas["rounds"].head(2), "kills": tabelas["kills"].filter(pl.col("round_num") <= 2)}
    _, resumo = r.rating(poucos, team_of, venc, kast, 64, referencia=None)
    assert any("sem modelo de round" in m for m in resumo["modo_degradado"])


def test_sem_a_compra_a_economia_da_partida_e_declarada(contexto):
    tabelas, team_of, venc, kast = contexto
    _, resumo = r.rating({**tabelas, "compra": None}, team_of, venc, kast, 64, referencia=r.carrega_referencia())
    assert resumo["fonte_da_economia"] == "partida"
    assert any("economia estimada só nesta partida" in m for m in resumo["modo_degradado"])


def test_no_caminho_normal_nada_e_degradado():
    for f in sorted((RAIZ / "data" / "processed").glob("match_*/insights.json"))[:60]:
        info = json.loads(f.read_text(encoding="utf-8"))["rating_info"]
        assert info.get("modo_degradado") == [] and info.get("texto_degradado") == "", f.parent.name


def test_time_sem_equipamento_nao_vira_dois_cts():
    """O padrão era (0, "ct") para os DOIS times: sem dado, o round tinha dois CTs."""
    lados = {r._equip_do_time({}, 3, t)[1] for t in ("A", "B")}
    assert lados == {"ct", "t"}
    assert r._equip_do_time({(3, "A"): (4200.0, "t")}, 3, "A") == (4200.0, "t")


def _componentes(**trocas):
    base = {"steamid": 1, "funcao_dominante": None, "clutch_attempts": 0, "awp_rounds": 0}
    from metrics.archetypes import COMPONENTES
    linha = {**base, **{c: 0.5 for c in COMPONENTES}, "piano_t_share": 0.0, "piano_ct_share": 0.0,
             "piano_eco_share": 0.0, "sacrificio_share": 0.1, "isca_share": 0.1, **trocas}
    return pl.DataFrame([linha], infer_schema_length=None)


def test_dado_ausente_nao_vira_rotulo_de_carregado():
    """Percentil de valor nulo é 0, e mochila = (1 - esforço) x (1 - impacto):
    quem não tinha o dado saía com a nota MÁXIMA de "Carregado"."""
    completo = archetype_indices(_componentes()).row(0, named=True)
    assert completo["idx_mochila"] is not None and completo["modo_degradado"] is None
    sem = archetype_indices(_componentes(damage_share=None, kill_share=None)).row(0, named=True)
    assert sem["idx_mochila"] is None
    assert "mochila" in sem["modo_degradado"]
    sem_camper = archetype_indices(_componentes(path_per_round=None)).row(0, named=True)
    assert sem_camper["idx_camper"] is None and sem_camper["idx_mochila"] is not None


sync_api = pytest.importorskip("playwright.sync_api")

from tests.test_tactics_browser import navegador  # noqa: E402,F401  (fixture)


def test_a_pagina_esconde_o_rating_degradado_e_diz_o_motivo(navegador, tmp_path):
    from scripts.build_web_page import build_html
    orig = RAIZ / "data" / "processed" / "match_23"
    if not (orig / "web_payload.json").exists():
        pytest.skip("sem o processado da match_23")
    base = tmp_path / "dados"
    base.mkdir()
    for arq in ("replay.json", "breakdown.json", "match_meta.json"):
        (base / arq).write_text((orig / arq).read_text(encoding="utf-8"), encoding="utf-8")
    payload = json.loads((orig / "web_payload.json").read_text(encoding="utf-8"))
    motivo = "Rating não mostrado nesta partida: economia estimada só nesta partida."
    payload["rating_info"] = {**payload["rating_info"], "modo_degradado": ["x"], "texto_degradado": motivo}
    (base / "web_payload.json").write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    pagina = tmp_path / "p.html"
    pagina.write_text(build_html("match_23", base=base), encoding="utf-8")
    pg = navegador.new_page(viewport={"width": 1300, "height": 900})
    pg.goto(pagina.as_uri())
    pg.click('[role=tab][data-tab="jogadores"]')
    assert pg.text_content("#rating-degradado") == motivo
    assert pg.locator(".prow .rt").count() == 0            # nenhuma célula de rating
    pg.close()
