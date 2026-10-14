"""A referência da aba Perfil por (lado, função) (fase 12b): célula, queda para o lado inteiro, nunca os
dois lados juntos, régua anônima e as métricas de ponto forte recalculadas por lado."""
from __future__ import annotations

import json
from pathlib import Path

import polars as pl
import pytest

from leitura import perfil_erros as PE
from metrics import erros as E

RAIZ = Path(__file__).resolve().parent.parent


def _ref(n_lurker_tr: int) -> dict:
    """Régua sintética: TR e CT bem diferentes, para qualquer mistura de lados aparecer."""
    t = E.NAO_TROCOU
    return {"min_ref_lado_funcao": 20,
            "erros": {t: {"t": {"lurker": {"n": n_lurker_tr, "hist": {"1": n_lurker_tr}},
                                E.TODAS: {"n": 520, "hist": {"4": 520}}},
                          "ct": {"ancora": {"n": 100, "hist": {"9": 100}}, E.TODAS: {"n": 520, "hist": {"8": 520}}}}}}


def _ocs(lado: str) -> list[dict]:
    return [{"nivel": E.EXPLICITO, "motivo": "m", "dwpa": -0.01, "round_num": r, "tick": r, "segundos": 5.0,
             "side": lado} for r in (2, 5)]


def test_lurker_de_tr_e_comparado_com_lurkers_de_tr():
    m = PE._ponto_a_melhorar(E.NAO_TROCOU, _ocs("t"), 15, _ref(33), "lurker", False, "t")
    assert m["referencia"].startswith("referência: quem joga lurker no TR")
    assert m["referencia"].endswith("a mediana é 1; o normal vai até 1") and m["lado_rotulo"] == "no TR"


def test_celula_pequena_cai_no_tr_inteiro_e_nunca_no_ct():
    m = PE._ponto_a_melhorar(E.NAO_TROCOU, _ocs("t"), 15, _ref(19), "lurker", False, "t")
    assert m["referencia"] == ("referência: todos os jogadores de TR (poucos lurkers no corpus); a mediana é 4; "
                               "o normal vai até 4")
    assert "CT" not in m["referencia"] and "8" not in m["referencia"] and "9" not in m["referencia"]


def test_a_celula_do_outro_lado_nunca_serve():
    # lurker não existe no CT da régua: vale o CT inteiro, nunca o TR
    celula, escopo = E.escolhe_celula(_ref(33), "erros", E.NAO_TROCOU, "ct", "lurker")
    assert escopo == "lado" and celula["hist"] == {"8": 520}
    celula, escopo = E.escolhe_celula(_ref(33), "erros", E.NAO_TROCOU, "t", "lurker")
    assert escopo == "funcao" and celula["n"] == 33
    assert E.escolhe_celula(_ref(33), "erros", E.NAO_TROCOU, "t", None)[1] == "lado"
    assert E.escolhe_celula(None, "erros", E.NAO_TROCOU, "t", "lurker") == (None, None)


def test_sem_funcao_o_texto_diz_que_a_referencia_e_o_lado():
    m = PE._ponto_a_melhorar(E.NAO_TROCOU, _ocs("ct"), 15, _ref(33), None, False, "ct")
    assert m["referencia"] == ("referência: todos os jogadores de CT (sem função definida neste lado); a mediana é 8; "
                               "o normal vai até 8")


def test_percentil_do_histograma():
    assert E.percentil_do_histograma({"0": 2, "4": 2}, 50) == 2.0
    assert E.percentil_do_histograma({"3": 5}, 75) == 3.0
    assert E.percentil_do_histograma({}, 50) is None


# --- A régua gravada ---------------------------------------------------------------------------------

def _gravada() -> dict:
    return json.loads(E.REFERENCIA_FILE.read_text(encoding="utf-8"))


def test_a_regua_gravada_e_por_lado_e_anonima():
    ref = _gravada()
    texto = json.dumps(ref, ensure_ascii=False)
    assert "7656119" not in texto                                   # nenhum steamid
    assert ref["min_ref_lado_funcao"] == E.MIN_REF_LADO_FUNCAO
    por = ref["jogador_lados_por_celula"]
    assert set(por) == {"ct", "t"}
    assert not {"lurker", "entry", "trader", "suporte"} & set(por["ct"])         # funções de TR nunca no CT
    assert not {"ancora", "rotativo", "coringa"} & set(por["t"])                  # funções de CT nunca no TR
    for lado in ("ct", "t"):
        todas = por[lado][E.TODAS]
        assert todas >= sum(n for f, n in por[lado].items() if f != E.TODAS)    # o resto: sem função (empate)
        for tipo in E.TIPOS:
            assert sum(ref["erros"][tipo][lado][E.TODAS]["hist"].values()) == todas


def test_so_a_celula_pequena_cai_no_lado_inteiro():
    ref = _gravada()
    pequenas = {(lado, f) for lado, cel in ref["jogador_lados_por_celula"].items() for f, n in cel.items()
                if f != E.TODAS and n < E.MIN_REF_LADO_FUNCAO}
    assert pequenas == {("t", "suporte")}


# --- Métricas de ponto forte por lado -----------------------------------------------------------------

def test_metricas_por_lado_somam_o_resumo_da_partida():
    base = RAIZ / "data" / "processed" / "match_47"
    if not (base / "impacto_per_round.parquet").exists():
        pytest.skip("sem a partida processada")
    por_lado = E.metricas_por_lado(pl.read_parquet(base / "player_profile_rounds.parquet"),
                                   pl.read_parquet(base / "impacto_per_round.parquet"))
    for r in pl.read_parquet(base / "player_profile.parquet").iter_rows(named=True):
        for chave, _, _ in E.METRICAS_DE_PONTO_FORTE:
            n = sum((por_lado.get((int(r["steamid"]), lado), {}).get(chave) or (0, 0, 0))[1] for lado in E.LADOS)
            d = sum((por_lado.get((int(r["steamid"]), lado), {}).get(chave) or (0, 0, 0))[2] for lado in E.LADOS)
            assert n == pytest.approx(r.get(f"{chave}_n") or 0) and d == pytest.approx(r.get(f"{chave}_d") or 0), chave


def test_situacao_de_um_lado_so_existe_nesse_lado():
    base = RAIZ / "data" / "processed" / "match_47"
    if not (base / "impacto_per_round.parquet").exists():
        pytest.skip("sem a partida processada")
    por_lado = E.metricas_por_lado(pl.read_parquet(base / "player_profile_rounds.parquet"),
                                   pl.read_parquet(base / "impacto_per_round.parquet"))
    for (_, lado), m in por_lado.items():
        if lado == "ct":
            assert not {"pct_pos_plant_vencidos", "kills_por_pos_plant", "pct_aberturas_vencidas_tr"} & set(m)
        else:
            assert not {"pct_retakes_vencidos", "kills_por_retake", "pct_aberturas_vencidas_ct"} & set(m)


# --- O bloco da página ---------------------------------------------------------------------------------

def test_o_card_diz_o_lado_e_os_lados_nao_se_misturam():
    b = _bloco_da_partida()
    achou_lado = False
    for j in b["jogadores"]:
        for m in j["melhorar"]:
            assert m["lado_rotulo"] in ("no CT", "no TR")
            achou_lado = True
            assert ("TR" in m["referencia"]) == (m["lado"] == "t") or m["referencia"] == ""
            assert ("CT" in m["referencia"]) == (m["lado"] == "ct") or m["referencia"] == ""
        for f in j["fortes"]:
            assert f["lado"] in ("ct", "t")
            assert ("TR" in f["referencia"]) == (f["lado"] == "t")
    assert achou_lado


# --- Acima do normal (fase 12b, item 4) -----------------------------------------------------------------

def test_so_vira_ponto_acima_do_percentil_75_e_com_duas_ocorrencias():
    celula = {"n": 100, "hist": {"0": 25, "1": 25, "2": 25, "3": 15, "4": 10}}      # p75 = 2,25 (interpolado)
    assert E.PERCENTIL_PONTO_A_MELHORAR == 75
    assert E.percentil_do_histograma(celula["hist"], 75) == 2.25
    assert not E.acima_do_normal(2, celula)          # igual ao percentil: dentro do normal
    assert E.acima_do_normal(3, celula)
    assert not E.acima_do_normal(1, {"n": 5, "hist": {"0": 5}})                # abaixo de 2, mesmo acima do p75 (0)
    assert E.acima_do_normal(2, {"n": 5, "hist": {"0": 5}})
    assert E.acima_do_normal(2, None) and not E.acima_do_normal(1, None)       # sem régua, só o mínimo
    assert E.acima_do_normal(3, celula, percentil=90) is False                 # p90 = 3: sobe a barra
    assert E.acima_do_normal(3, celula, percentil=50) is True


def test_o_bloco_so_publica_acima_do_normal_e_o_resto_vai_para_detalhes():
    b = _bloco_da_partida()
    ref = _gravada()
    for j in b["jogadores"]:
        for m in j["melhorar"]:
            assert len(m["chips"]) >= E.MIN_OCORRENCIAS_PARA_PONTO and len(m["chips"]) > m["limite"]
        for u in j["uma_vez"]:
            assert u["motivo"]
    vazios = [j for j in b["jogadores"] if not j["melhorar"]]
    assert vazios and all(j["melhorar_vazio"] == "Nada acima do normal para a função nesta partida" for j in vazios)


def test_o_limite_do_card_e_o_p75_da_celula_escolhida():
    m = PE._ponto_a_melhorar(E.NAO_TROCOU, _ocs("t") + _ocs("t"), 15, _ref(33), "lurker", False, "t")
    assert m["limite"] == 1.0 and m["referencia"].endswith("o normal vai até 1")
    m = PE._ponto_a_melhorar(E.NAO_TROCOU, _ocs("t") + _ocs("t"), 15, _ref(19), "lurker", False, "t")
    assert m["limite"] == 4.0                                             # o TR inteiro, não o lurker nem o CT


def test_o_publicado_usa_os_fortes_por_lado():
    """Fase 16a: com `FORTES_POR_LADO_PUBLICADOS` ligada, a aba Perfil publicada (erros em validação) tem os
    pontos fortes e o resumo calculados por (lado, função), com `lado` nos cards e os textos novos; o cálculo
    é o mesmo da prévia (a fonte é `_pontos_fortes`)."""
    from scripts.build_web_page import cabecalho_da_partida
    assert E.FORTES_POR_LADO_PUBLICADOS is True
    base = RAIZ / "data" / "processed" / "match_47"
    if not (base / E.ARQUIVO).exists() or not (base / "web_payload.json").exists():
        pytest.skip("sem as ocorrências gravadas da partida")
    payload = json.loads((base / "web_payload.json").read_text(encoding="utf-8"))
    cab = cabecalho_da_partida("match_47", base)
    pub = PE.bloco_da_partida(base, payload, cab)
    previa = PE.bloco_da_partida(base, payload, cab, preview=True)
    assert pub["estado"] == "em_validacao" and pub["textos"] == PE.TEXTOS
    assert pub["textos"]["nenhum_erro"] == "Nada acima do normal para a função nesta partida"
    ref = E.carrega_referencia()
    perfis = {int(p["steamid"]): p for p in payload["player_profile"]}
    por_lado = E.metricas_por_lado(pl.read_parquet(base / "player_profile_rounds.parquet"),
                                   pl.read_parquet(base / "impacto_per_round.parquet"))
    for j in pub["jogadores"]:
        assert j["melhorar"] == [] and j["uma_vez"] == []
        assert all(f["lado"] in ("ct", "t") and f["referencia"].startswith("referência: ") for f in j["fortes"])
    for j in pub["jogadores"]:
        sid = next(s for s, p in perfis.items() if p["name"] == j["name"])
        funcao_do_lado = {r["side"]: (None if r.get("texto_empate") else r.get("funcao"))
                          for r in payload["structural_roles"] if int(r["steamid"]) == sid}
        esperado, _ = PE._pontos_fortes(perfis[sid], {lado: v for (s, lado), v in por_lado.items() if s == sid},
                                        funcao_do_lado, ref)
        assert j["fortes"] == esperado
    assert [j["fortes"] for j in pub["jogadores"]] == [j["fortes"] for j in previa["jogadores"]]
    assert previa["textos"] == PE.TEXTOS


def _bloco_da_partida() -> dict:
    from scripts.build_web_page import cabecalho_da_partida
    base = RAIZ / "data" / "processed" / "match_47"
    if not (base / E.ARQUIVO).exists() or not (base / "web_payload.json").exists():
        pytest.skip("sem as ocorrências gravadas da partida")
    payload = json.loads((base / "web_payload.json").read_text(encoding="utf-8"))
    return PE.bloco_da_partida(base, payload, cabecalho_da_partida("match_47", base), preview=True)
