"""Prancheta no formato 3: o tempo do round é o eixo (fase 8, item 8.1)."""
from __future__ import annotations

import json
import math
from pathlib import Path

import pytest

from metrics.tactics import (DURACAO_EFEITO_S, VELOCIDADE_U_S, VOO_PAVIO_S, aplica, centro_do_radar,
                             estado_no_tempo, funcoes_da_prancheta, linha_do_tempo, posicao_no_tempo, problemas,
                             quadro_do_passo, relogio, velocidade, voo_estimado)

RAIZ = Path(__file__).resolve().parent.parent
FIXTURES = RAIZ / "tests" / "fixtures"
CENTRO = centro_do_radar(json.loads((RAIZ / "assets" / "radars" / "de_mirage.json").read_text(encoding="utf-8")))


def _op(seq, tipo, **d):
    return {"id": f"op{seq:04d}pedro", "seq": seq, "autor": "pedro", "em": "2026-10-04T00:00:00Z", "tipo": tipo, **d}


def _doc(ops, versao=3):
    return {"formato": "prancheta-cs2", "versao": versao, "id": "taticaXYZ", "mapa": "de_mirage",
            "criada_por": "pedro", "criada_em": "2026-10-04T00:00:00Z", "contador": max(o["seq"] for o in ops),
            "operacoes": ops, "calibracao": "x"}


BASE = [_op(1, "renomeia", titulo="t"), _op(2, "cria_passo", passo="p1", titulo="início"),
        _op(3, "cria_peca", peca="ct1", lado="ct", rotulo="1", passo="p1", x=0.0, y=0.0)]


@pytest.mark.parametrize("nome", ["tatica_v1.json", "tatica_v2.json"])
def test_v1_e_v2_migram_e_reproduzem_nos_horarios_dos_passos_o_quadro_do_codigo_antigo(nome):
    """No horário de cada antigo passo (a soma das durações dos anteriores), as
    peças (lugar, andar, yaw) e os traços são os do quadro do passo do código
    antigo. Granadas de pavio (flash, HE) seguem a vida em passos; smoke e
    molotov seguem a duração real do jogo, como o documento manda."""
    doc = json.loads((FIXTURES / nome).read_text(encoding="utf-8"))
    e2, e3 = aplica(doc["operacoes"]), linha_do_tempo(doc["operacoes"], CENTRO)
    assert [m["titulo"] for m in e3["marcos"]] == [p["titulo"] for p in e2["passos"]]
    for k, m in enumerate(e3["marcos"]):
        assert m["t"] == pytest.approx(sum(p["duracao_s"] for p in e2["passos"][:k]))
        antigo, novo = quadro_do_passo(e2, k, CENTRO), estado_no_tempo(e3, m["t"], CENTRO)
        assert {i: (p["x"], p["y"], p["nivel"], p["yaw"]) for i, p in antigo["pecas"].items()} == \
               {i: (p["x"], p["y"], p["nivel"], p["yaw"]) for i, p in novo["pecas"].items()}
        assert sorted(antigo["tracos"]) == sorted(novo["tracos"])
        pavio = lambda gs: sorted(i for i, g in gs.items() if g["arma"] in ("flash", "he", "decoy"))  # noqa: E731
        assert pavio(antigo["granadas"]) == pavio(novo["granadas"])
        for i, g in e3["granadas"].items():
            if g["arma"] in ("smoke", "molotov") and g["t"] <= m["t"] < g["t"] + g["voo_s"] + g["efeito_s"]:
                assert i in novo["granadas"]


def test_caminho_interpola_no_tempo_e_a_direcao_acompanha_o_movimento():
    ops = BASE + [_op(4, "cria_caminho", peca="ct1", pontos=[{"t": 10.0, "x": 0.0, "y": 0.0},
                                                              {"t": 20.0, "x": 100.0, "y": 0.0},
                                                              {"t": 30.0, "x": 100.0, "y": 100.0}])]
    e3 = linha_do_tempo(ops, CENTRO)
    q = estado_no_tempo(e3, 15.0, CENTRO)["pecas"]["ct1"]
    assert (q["x"], q["y"]) == (50.0, 0.0) and q["yaw"] == 0.0 and not q["direcao_padrao"]
    q = estado_no_tempo(e3, 25.0, CENTRO)["pecas"]["ct1"]
    assert (q["x"], q["y"]) == (100.0, 50.0) and q["yaw"] == 90.0
    # depois do último ponto, parado no último lugar
    q = estado_no_tempo(e3, 40.0, CENTRO)["pecas"]["ct1"]
    assert (q["x"], q["y"]) == (100.0, 100.0)


def test_yaw_explicito_no_trecho_vence_o_rumo_e_gira_pelo_caminho_curto():
    ops = BASE + [_op(4, "cria_caminho", peca="ct1", pontos=[{"t": 0.0, "x": 0.0, "y": 0.0, "yaw": 350.0},
                                                              {"t": 10.0, "x": 100.0, "y": 0.0, "yaw": 10.0}])]
    e3 = linha_do_tempo(ops, CENTRO)
    assert estado_no_tempo(e3, 5.0, CENTRO)["pecas"]["ct1"]["yaw"] == pytest.approx(0.0, abs=1e-9)


def test_relogio_do_jogo_e_bomba():
    assert relogio(15.0) == "1:40"
    assert relogio(0.0) == "1:55"
    assert relogio(70.0, plant=60.0) == "0:30"
    ops = BASE + [_op(4, "planta_bomba", t=60.0, x=1.0, y=2.0)]
    e3 = linha_do_tempo(ops, CENTRO)
    assert estado_no_tempo(e3, 59.0, CENTRO)["bomba"] is None
    q = estado_no_tempo(e3, 75.0, CENTRO)
    assert q["bomba"]["t"] == 60.0 and q["relogio"] == "0:25"


def test_granada_com_horario_e_arremessador_voa_abre_o_efeito_real_e_some():
    ops = BASE + [_op(4, "cria_granada", granada="g1", arma="smoke", passo="p1", origem=[0.0, 0.0],
                      destino=[1000.0, 0.0], t=15.0, jogador="ct1")]
    e3 = linha_do_tempo(ops, CENTRO)
    g = e3["granadas"]["g1"]
    assert g["t"] == 15.0 and g["jogador"] == "ct1"
    assert g["voo_s"] == pytest.approx(voo_estimado("smoke", [0, 0], [1000, 0]))
    voo = g["voo_s"]
    assert "g1" not in estado_no_tempo(e3, 14.9, CENTRO)["granadas"]
    assert estado_no_tempo(e3, 15.0 + voo / 2, CENTRO)["granadas"]["g1"]["fase"] == "voo"
    assert estado_no_tempo(e3, 15.0 + voo + 1, CENTRO)["granadas"]["g1"]["fase"] == "efeito"
    assert "g1" not in estado_no_tempo(e3, 15.0 + voo + DURACAO_EFEITO_S["smoke"] + 0.1, CENTRO)["granadas"]


def test_peca_tirada_some_no_horario_do_ponto_fora():
    ops = BASE + [_op(4, "cria_passo", passo="p2", titulo="b"), _op(5, "tira_peca", peca="ct1", passo="p2")]
    e3 = linha_do_tempo(ops, CENTRO)
    assert posicao_no_tempo(e3["pecas"]["ct1"], 1.0) is not None
    assert posicao_no_tempo(e3["pecas"]["ct1"], 2.0) is None


def test_funcao_mexe_na_velocidade_padrao():
    assert velocidade("AWPer") == VELOCIDADE_U_S[("AWP", "correndo")]
    assert velocidade("Suporte") == VELOCIDADE_U_S[("rifle", "correndo")]
    assert velocidade(None, "agachado") < velocidade(None, "andando") < velocidade(None, "correndo")
    ops = BASE + [_op(4, "define_funcao", peca="ct1", funcao="AWPer")]
    assert linha_do_tempo(ops, CENTRO)["pecas"]["ct1"]["funcao"] == "AWPer"
    assert "AWPer" in funcoes_da_prancheta() and "IGL" in funcoes_da_prancheta()


def test_voo_medido_flash_e_he_por_pavio_smoke_e_molotov_pela_distancia():
    assert voo_estimado("flash", [0, 0], [10, 0]) == voo_estimado("he", [0, 0], [3000, 0]) == VOO_PAVIO_S
    assert voo_estimado("smoke", [0, 0], [2000, 0]) > voo_estimado("smoke", [0, 0], [200, 0])
    assert voo_estimado("molotov", [0, 0], [10000, 0]) == 2.0


@pytest.mark.parametrize("extra, trecho", [
    ([_op(4, "cria_caminho", peca="ct1", pontos=[{"t": -1.0, "x": 0.0, "y": 0.0}])], "fora do round"),
    ([_op(4, "cria_caminho", peca="ct1", pontos=[{"t": 5.0, "x": 0.0, "y": 0.0}, {"t": 5.0, "x": 9.0, "y": 0.0}])],
     "dois pontos em t = 5"),
    ([_op(4, "cria_granada", granada="g", arma="he", passo="p1", origem=[0.0, 0.0], destino=[1.0, 1.0], jogador="zz")],
     "arremessador que não existe"),
    ([_op(4, "cria_passo", passo="p2", titulo="b"),
      _op(5, "cria_peca", peca="t1", lado="t", rotulo="1", passo="p2", x=5.0, y=5.0),
      _op(6, "cria_granada", granada="g", arma="he", passo="p1", origem=[5.0, 5.0], destino=[9.0, 9.0], t=0.5, jogador="t1")],
     "antes do primeiro ponto do arremessador"),
    ([_op(4, "define_funcao", peca="ct1", funcao="Mago")], "função fora do vocabulário"),
])
def test_problemas_do_formato_3(extra, trecho):
    erros = problemas(_doc(BASE + extra))
    assert any(trecho in e for e in erros), erros


def test_operacao_do_formato_3_num_arquivo_do_formato_2_e_problema():
    erros = problemas(_doc(BASE + [_op(4, "define_funcao", peca="ct1", funcao="AWPer")], versao=2))
    assert any("operação do formato 3 num arquivo do formato 2" in e for e in erros)


# --- espelho Python <-> JS ----------------------------------------------------

sync_api = pytest.importorskip("playwright.sync_api")

from tests.test_tactics_browser import contexto, interno, navegador, pagina  # noqa: E402,F401  (fixtures)


def _arredonda(v):
    if isinstance(v, float):
        return round(v, 6)
    if isinstance(v, dict):
        return {k: _arredonda(x) for k, x in v.items() if not k.startswith("_")}
    if isinstance(v, list):
        return [_arredonda(x) for x in v]
    return v


SINTETICO = BASE + [
    _op(4, "cria_caminho", peca="ct1", pontos=[{"t": 3.0, "x": 10.0, "y": 0.0}, {"t": 9.0, "x": 10.0, "y": 80.0, "modo": "andando"}]),
    _op(5, "define_funcao", peca="ct1", funcao="AWPer"),
    _op(6, "cria_granada", granada="g1", arma="molotov", passo="p1", origem=[10.0, 80.0], destino=[300.0, 80.0], t=9.0, jogador="ct1"),
    _op(7, "planta_bomba", t=40.0, x=1.0, y=1.0),
    _op(8, "nota_de_evento", alvo="g1", texto="molotov no <b>banana</b>"),
    _op(9, "move_ponto", peca="ct1", ponto="op0004pedro:1", t=8.0, x=12.0, y=80.0),
]


@pytest.mark.parametrize("fonte", ["tatica_v1.json", "tatica_v2.json", "sintetico"])
def test_js_e_python_chegam_a_mesma_linha_do_tempo_e_ao_mesmo_quadro(contexto, pagina, fonte):
    ops = SINTETICO if fonte == "sintetico" else json.loads((FIXTURES / fonte).read_text(encoding="utf-8"))["operacoes"]
    pg = contexto.new_page()
    pg.goto(pagina.as_uri())
    pg.wait_for_function("() => Prancheta._interno.S.estado !== null")
    centro = interno(pg, "I.centro()")
    py = linha_do_tempo(ops, centro)
    js = pg.evaluate("(ops) => Prancheta._interno.taticaNoTempo(ops)", ops)
    assert _arredonda(js) == _arredonda(py)
    for t in (0.0, 1.0, 2.5, 3.0, 6.0, 9.5, 41.0):
        qpy = estado_no_tempo(py, t, centro)
        qjs = pg.evaluate("([ops, t]) => { const I = Prancheta._interno; return I.quadroNoTempo(I.taticaNoTempo(ops), t, I.centro()); }",
                          [ops, t])
        assert _arredonda(qjs) == _arredonda(qpy), t
    assert pg.evaluate("(ops) => Prancheta._interno.problemasNoTempo(Prancheta._interno.taticaNoTempo(ops))", ops) == []
    pg.close()


def test_relogio_do_map_core_e_o_do_python(contexto, pagina):
    pg = contexto.new_page()
    pg.goto(pagina.as_uri())
    for t, plant in ((0.0, None), (15.0, None), (114.9, None), (70.0, 60.0), (101.0, 60.0)):
        assert pg.evaluate(f"MapCore.relogio({t}, {json.dumps(plant)}, null, 115, 40)") == relogio(t, plant), t
    assert math.isclose(VOO_PAVIO_S, pg.evaluate("Prancheta._interno.M3().VOO_PAVIO_S"))
    pg.close()
