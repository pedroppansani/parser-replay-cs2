"""
Testes do modelo da prancheta tática (metrics/tactics.py) e da biblioteca de
arremessos reais (scripts/build_lineups.py).

O que importa provar no modelo é o que o deixa pronto para mais de um usuário:
a mesma lista de operações dá o mesmo estado em qualquer ordem de chegada, e
duas cópias editadas em paralelo convergem ao mesclar.
"""
from __future__ import annotations

import json
import random
from pathlib import Path

import pytest

from metrics.tactics import (
    FORMATO, IDENTIFICADOR, TaticaInvalida, aplica, mescla, posicao_no_passo, valida,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _op(seq, tipo, autor="pedro", **dados):
    return {"id": f"op{seq:04d}{autor}", "seq": seq, "autor": autor, "em": "2026-09-26T00:00:00Z",
            "tipo": tipo, **dados}


def _doc(ops, contador=None):
    return {"formato": IDENTIFICADOR, "versao": FORMATO, "id": "tatica001", "mapa": "de_mirage",
            "criada_por": "pedro", "criada_em": "2026-09-26T00:00:00Z", "calibracao": "abc",
            "contador": contador if contador is not None else max((o["seq"] for o in ops), default=0),
            "operacoes": ops}


def _base():
    return [
        _op(1, "renomeia", titulo="Execução B"),
        _op(2, "cria_passo", passo="p1", titulo="posições"),
        _op(3, "cria_passo", passo="p2", titulo="entrada"),
        _op(4, "cria_peca", peca="ct1", lado="ct", rotulo="1", passo="p1", x=100.0, y=200.0),
        _op(5, "move_peca", peca="ct1", passo="p2", x=300.0, y=250.0),
        _op(6, "cria_granada", granada="g1", arma="smoke", passo="p2",
            origem=[0.0, 0.0], destino=[500.0, 500.0], arremesso=None),
    ]


def test_o_estado_sai_do_log_e_a_peca_guarda_posicao_por_passo():
    e = aplica(_base())
    assert e["titulo"] == "Execução B"
    assert [p["passo"] for p in e["passos"]] == ["p1", "p2"]
    ct1 = e["pecas"]["ct1"]
    assert posicao_no_passo(ct1, e["passos"], 0) == [100.0, 200.0]
    assert posicao_no_passo(ct1, e["passos"], 1) == [300.0, 250.0]
    assert e["granadas"]["g1"]["arma"] == "smoke"


def test_a_ordem_de_chegada_nao_muda_o_estado():
    ops = _base()
    esperado = aplica(ops)
    rng = random.Random(0)
    for _ in range(20):
        embaralhado = ops[:]
        rng.shuffle(embaralhado)
        assert aplica(embaralhado) == esperado


def test_duas_copias_editadas_em_paralelo_convergem():
    """Pedro e outro autor partem do mesmo log e editam sem se ver. Mesclar nos
    dois sentidos dá o MESMO documento e o mesmo estado; nada se perde."""
    comum = _base()
    a = _doc(comum + [_op(7, "move_peca", autor="pedro", peca="ct1", passo="p2", x=10.0, y=10.0)])
    b = _doc(comum + [_op(7, "move_peca", autor="ana", peca="ct1", passo="p2", x=90.0, y=90.0),
                      _op(8, "renomeia", autor="ana", titulo="Execução B rápida")])
    ab, ba = mescla(a, b), mescla(b, a)
    assert [o["id"] for o in ab["operacoes"]] == [o["id"] for o in ba["operacoes"]]
    assert aplica(ab["operacoes"]) == aplica(ba["operacoes"])
    assert len(ab["operacoes"]) == len(comum) + 3          # nada sumiu
    assert ab["contador"] == 8
    e = aplica(ab["operacoes"])
    # conflito no mesmo seq: vence o maior (seq, autor, id) -- "pedro" > "ana"
    assert posicao_no_passo(e["pecas"]["ct1"], e["passos"], 1) == [10.0, 10.0]
    assert e["titulo"] == "Execução B rápida"


def test_remover_passo_leva_posicoes_e_granadas_dele():
    e = aplica(_base() + [_op(7, "remove_passo", passo="p2")])
    assert [p["passo"] for p in e["passos"]] == ["p1"]
    assert e["pecas"]["ct1"]["posicoes"] == {"p1": [100.0, 200.0]}
    assert e["granadas"] == {}


def test_arrastar_a_granada_desfaz_o_arremesso_real():
    """Com a granada movida à mão, o comando de console deixa de valer: mantê-lo
    seria afirmar um lineup que não é mais aquele."""
    real = {"id": "match_01:3:900", "comando": "setpos 1 2 3; setang 4 5 0",
            "origem": [1, 2, 3], "destino": [9, 9, 9], "pitch": 4, "yaw": 5}
    ops = _base() + [_op(7, "cria_granada", granada="g2", arma="smoke", passo="p1",
                         origem=[1.0, 2.0], destino=[9.0, 9.0], arremesso=real)]
    assert aplica(ops)["granadas"]["g2"]["arremesso"] == real
    ops.append(_op(8, "move_granada", granada="g2", origem=[1.0, 2.0], destino=[50.0, 50.0]))
    assert aplica(ops)["granadas"]["g2"]["arremesso"] is None


def test_operacao_sobre_coisa_removida_e_ignorada():
    """Numa mescla, o 'mover' de um pode chegar depois do 'remover' do outro."""
    e = aplica(_base() + [_op(7, "remove_peca", peca="ct1"),
                          _op(8, "move_peca", peca="ct1", passo="p1", x=1.0, y=1.0)])
    assert "ct1" not in e["pecas"]


@pytest.mark.parametrize("estraga, trecho", [
    (lambda d: d.update(formato="outro"), "não é um arquivo"),
    (lambda d: d.update(versao=99), "versão 99"),
    (lambda d: d.update(contador=1), "contador"),
    (lambda d: d["operacoes"].append(dict(d["operacoes"][0])), "repetida"),
    (lambda d: d["operacoes"].append(_op(50, "teleporta")), "desconhecida"),
    (lambda d: d["operacoes"].append(_op(51, "cria_granada", granada="x", arma="bazuca", passo="p1",
                                         origem=[0, 0], destino=[1, 1])), "granada desconhecida"),
    (lambda d: d["operacoes"].append(_op(52, "cria_granada", granada="x", arma="smoke", passo="p1",
                                         origem=[0, 0], destino=[1, 1], arremesso={"id": "a"})), "arremesso real"),
])
def test_arquivo_estragado_e_recusado(estraga, trecho):
    d = _doc(_base())
    estraga(d)
    if trecho != "contador":
        d["contador"] = max(d["contador"], max(o["seq"] for o in d["operacoes"]))
    with pytest.raises(TaticaInvalida, match=trecho):
        valida(d)


def test_calibracao_diferente_e_recusada():
    with pytest.raises(TaticaInvalida, match="calibração"):
        valida(_doc(_base()), calibracoes={"de_mirage": "outra"})
    assert valida(_doc(_base()), calibracoes={"de_mirage": "abc"})["titulo"] == "Execução B"


# --- Biblioteca de arremessos reais ---------------------------------------------

def _biblioteca(mapa="de_mirage"):
    p = PROJECT_ROOT / "data" / "lineups" / f"{mapa}.json"
    if not p.exists():
        pytest.skip("biblioteca de arremessos não gerada (scripts/build_lineups.py)")
    return json.loads(p.read_text(encoding="utf-8"))


def test_a_biblioteca_so_tem_arremesso_com_comando_e_destino():
    bib = _biblioteca()
    assert bib["formato"] == "biblioteca-de-arremessos" and bib["arremessos"]
    for r in bib["arremessos"][:500]:
        assert r["comando"].startswith("setpos ") and "; setang " in r["comando"]
        assert len(r["origem"]) == 3 and len(r["destino"]) == 3
        # o comando é o da posição e do ângulo gravados na própria entrada
        x, y, z = (float(v) for v in r["comando"].split(";")[0].split()[1:])
        assert (round(x, 2), round(y, 2), round(z, 2)) == tuple(r["origem"])


def test_o_botao_so_sai_com_os_tres_rotulos_confirmados():
    """Grupo neutro ("força A") não diz qual botão; inventar seria pior."""
    for mapa in ("de_mirage", "de_nuke"):
        bib = _biblioteca(mapa)
        for r in bib["arremessos"]:
            if r["forca"] in ("curto", "médio", "longo"):
                assert r["botao"] is not None
            else:
                assert r["botao"] is None


def test_o_comando_e_o_mesmo_do_material_de_calibracao():
    from metrics.grenade_throws import comando_de_console
    assert comando_de_console(-655.0, -1159.123, -166.0, 4.5, -127.125) == \
        "setpos -655.00 -1159.12 -166.00; setang 4.50 -127.12 0"


# --- Formato 2 (etapa 2) ------------------------------------------------------

FIXTURES = PROJECT_ROOT / "tests" / "fixtures"


def test_a_fixture_v1_migra_para_o_estado_v1_mais_os_padroes():
    """A versão 1 é migrada em memória: nenhuma operação muda, e o estado é o da
    fixture (gerado pelo código antigo) acrescido só dos campos novos."""
    from metrics.tactics import DURACAO_PADRAO_S, VIDA_PADRAO_GRANADA, migra

    doc = json.loads((FIXTURES / "tatica_v1.json").read_text(encoding="utf-8"))
    esperado_v1 = json.loads((FIXTURES / "tatica_v1_estado.json").read_text(encoding="utf-8"))
    assert doc["versao"] == 1
    assert migra(doc)["operacoes"] == doc["operacoes"] and migra(doc)["versao"] == FORMATO
    e = valida(doc)
    assert e["tracos"] == {}
    for p in e["passos"]:
        assert p.pop("duracao_s") == DURACAO_PADRAO_S
    for p in e["pecas"].values():
        assert p.pop("direcoes") == {}
        assert p.pop("niveis") == {k: 0 for k, v in p["posicoes"].items() if v is not None}
        assert len(p.pop("criada_em_ordem")) == 3
    for g in e["granadas"].values():
        assert g.pop("nivel") == 0
        assert g.pop("dura_passos") == VIDA_PADRAO_GRANADA[g["arma"]]
        assert len(g.pop("criada_em_ordem")) == 3
    e.pop("tracos")
    assert e == esperado_v1


def _op2(seq, tipo, autor="pedro", **d):
    return {"id": f"op{seq:04d}{autor}", "seq": seq, "autor": autor, "em": "2026-09-26T00:00:00Z", "tipo": tipo, **d}


REAL = {"id": "match_01:3:900", "comando": "setpos 1 2 3; setang 4 5 0",
        "origem": [1, 2, 3], "destino": [9, 9, 9], "pitch": 4, "yaw": 5}


def test_anular_cria_peca_some_com_a_peca_e_reativar_devolve_tudo():
    ops = _base() + [_op2(7, "gira_peca", peca="ct1", passo="p2", yaw=90.0), _op2(8, "anula", alvo="op0004pedro")]
    assert "ct1" not in aplica(ops)["pecas"]
    e2 = aplica(ops + [_op2(9, "reativa", alvo="op0004pedro")])
    assert e2["pecas"]["ct1"]["posicoes"] == {"p1": [100.0, 200.0], "p2": [300.0, 250.0]}
    assert e2["pecas"]["ct1"]["direcoes"] == {"p2": 90.0}


def test_anular_remove_peca_devolve_a_peca_com_todo_o_historico():
    antes = aplica(_base())["pecas"]["ct1"]
    ops = _base() + [_op2(7, "remove_peca", peca="ct1"), _op2(8, "anula", alvo="op0007pedro")]
    assert aplica(ops)["pecas"]["ct1"] == antes


def test_anular_move_granada_devolve_o_arremesso_real():
    ops = _base() + [
        _op2(7, "cria_granada", granada="g2", arma="smoke", passo="p1", origem=[1.0, 2.0], destino=[9.0, 9.0], arremesso=REAL),
        _op2(8, "move_granada", granada="g2", origem=[1.0, 2.0], destino=[50.0, 50.0]),
    ]
    assert aplica(ops)["granadas"]["g2"]["arremesso"] is None
    g = aplica(ops + [_op2(9, "anula", alvo="op0008pedro")])["granadas"]["g2"]
    assert g["arremesso"] == REAL and g["destino"] == [9.0, 9.0]


def test_anula_de_outro_autor_nao_vale_e_e_apontada():
    from metrics.tactics import problemas
    ops = _base() + [_op2(7, "anula", autor="ana", alvo="op0004pedro")]
    assert "ct1" in aplica(ops)["pecas"]
    assert any("cada um só desfaz" in p for p in problemas(_doc(ops)))


def test_mescla_com_anula_de_dois_autores_converge():
    """Pedro e Ana desfazem coisas próprias em paralelo; as duas ordens de
    mescla dão o mesmo estado."""
    comum = _base() + [_op2(7, "cria_peca", autor="ana", peca="t1", lado="t", rotulo="1", passo="p1", x=5.0, y=5.0)]
    a = _doc(comum + [_op2(8, "anula", autor="pedro", alvo="op0005pedro")])
    b = _doc(comum + [_op2(8, "anula", autor="ana", alvo="op0007ana"),
                      _op2(9, "reativa", autor="ana", alvo="op0007ana"),
                      _op2(10, "anula", autor="ana", alvo="op0007ana")])
    ab, ba = mescla(a, b), mescla(b, a)
    assert aplica(ab["operacoes"]) == aplica(ba["operacoes"])
    e = aplica(ab["operacoes"])
    assert "t1" not in e["pecas"]                                               # a última da Ana foi anula
    assert posicao_no_passo(e["pecas"]["ct1"], e["passos"], 1) == [100.0, 200.0]  # o move foi desfeito


def test_problemas_devolve_todos_os_defeitos_e_valida_leva_todos():
    from metrics.tactics import problemas
    ops = _base() + [
        _op2(7, "gira_peca", peca="ct1", passo="p1", yaw=400.0),
        _op2(8, "define_vida", alvo="g1", dura_passos=0),
        _op2(9, "define_duracao", passo="p1", segundos=0),
        _op2(10, "cria_traco", traco="s1", passo="p1", ferramenta="pincel", cor="verde", espessura=3, pontos=[[0, 0]]),
        _op2(11, "cria_peca", peca="ct2", lado="ct", rotulo="2", passo="p1", x=0.0, y=0.0, nivel=1),
        _op2(12, "anula", alvo="op0011pedro"), _op2(13, "anula", alvo="op0012pedro"),
    ]
    ps = problemas(_doc(ops))
    for trecho in ("yaw 400.0 fora de [0, 360)", "dura_passos 0", "duração 0", "ferramenta 'pincel'",
                   "cor 'verde'", "espessura 3", "nivel 1 num mapa de um andar", "mira outra anula"):
        assert any(trecho in p for p in ps), (trecho, ps)
    with pytest.raises(TaticaInvalida) as erro:
        valida(_doc(ops))
    assert all(p in str(erro.value) for p in ps)


def test_nivel_vale_nos_mapas_de_dois_andares():
    from metrics.tactics import problemas
    doc = _doc(_base() + [_op2(7, "cria_peca", peca="ct2", lado="ct", rotulo="2", passo="p1", x=0.0, y=0.0, nivel=1)])
    doc["mapa"] = "de_nuke"
    assert not problemas(doc)
    doc["operacoes"][-1]["nivel"] = 2
    assert any("nivel 2 num mapa de 2 andares" in p for p in problemas(doc))


def _tres_passos(*extra):
    return [_op2(1, "cria_passo", passo="p1", titulo=""), _op2(2, "cria_passo", passo="p2", titulo=""),
            _op2(3, "cria_passo", passo="p3", titulo=""), *extra]


CENTRO = [0.0, 0.0]


def test_vida_util_smoke_ate_o_fim_flash_so_no_seu_passo():
    from metrics.tactics import quadro_do_passo
    ops = _tres_passos(
        _op2(4, "cria_granada", granada="s", arma="smoke", passo="p1", origem=[0, 0], destino=[1, 1]),
        _op2(5, "cria_granada", granada="f", arma="flash", passo="p2", origem=[0, 0], destino=[1, 1]))
    e = aplica(ops)
    q = [quadro_do_passo(e, i, CENTRO) for i in range(3)]
    assert [("s" in x["granadas"], "f" in x["granadas"]) for x in q] == [(True, False), (True, True), (True, False)]
    assert q[0]["granadas"]["s"]["nasceu_neste_passo"] and not q[2]["granadas"]["s"]["nasceu_neste_passo"]


def test_remover_passo_intermediario_mantem_a_contagem_da_vida():
    """dura_passos conta passos, não guarda o id do passo final: remover um
    passo no meio encurta a linha do tempo, e a conta continua certa."""
    from metrics.tactics import quadro_do_passo
    ops = _tres_passos(_op2(4, "cria_passo", passo="p4", titulo=""),
                       _op2(5, "cria_granada", granada="m", arma="molotov", passo="p1", origem=[0, 0], destino=[1, 1], dura_passos=2),
                       _op2(6, "remove_passo", passo="p2"))
    e = aplica(ops)
    assert [p["passo"] for p in e["passos"]] == ["p1", "p3", "p4"]
    assert ["m" in quadro_do_passo(e, i, CENTRO)["granadas"] for i in range(3)] == [True, True, False]


def test_quadro_heranca_tira_peca_e_direcao_padrao():
    from metrics.tactics import direcao_padrao, quadro_do_passo
    ops = _tres_passos(
        _op2(4, "cria_peca", peca="a", lado="t", rotulo="1", passo="p1", x=100.0, y=0.0),
        _op2(5, "gira_peca", peca="a", passo="p2", yaw=45.0),
        _op2(6, "tira_peca", peca="a", passo="p3"),
        _op2(7, "cria_peca", peca="b", lado="t", rotulo="2", passo="p1", x=0.0, y=0.0, yaw=10.0, nivel=0))
    e = aplica(ops)
    q = [quadro_do_passo(e, i, [0.0, 100.0]) for i in range(3)]
    a0 = q[0]["pecas"]["a"]
    assert a0["direcao_padrao"] and a0["yaw"] == direcao_padrao(100.0, 0.0, [0.0, 100.0]) == 135.0
    assert q[1]["pecas"]["a"]["yaw"] == 45.0 and not q[1]["pecas"]["a"]["direcao_padrao"]
    assert (q[1]["pecas"]["a"]["x"], q[1]["pecas"]["a"]["y"]) == (100.0, 0.0)     # herdada
    assert "a" not in q[2]["pecas"]                                              # tirada
    assert q[2]["pecas"]["b"]["yaw"] == 10.0                                     # yaw do cria_peca, herdado
    e2 = aplica(ops + [_op2(8, "move_peca", peca="a", passo="p3", x=1.0, y=1.0)])
    assert "a" in quadro_do_passo(e2, 2, CENTRO)["pecas"]                        # volta com move_peca


def test_ordem_de_criacao_segue_o_log():
    from metrics.tactics import ordem_de_criacao
    ops = _tres_passos(
        _op2(4, "cria_traco", traco="t1", passo="p2", ferramenta="seta", cor="#eb6834", espessura=4, pontos=[[0, 0], [5, 5]]),
        _op2(5, "cria_granada", granada="g", arma="smoke", passo="p1", origem=[0, 0], destino=[1, 1]),
        _op2(6, "cria_traco", traco="t0", passo="p1", ferramenta="caneta", cor="#eb6834", espessura=2, pontos=[[0, 0]]))
    assert [x["id"] for x in ordem_de_criacao(aplica(ops))] == ["t1", "g", "t0"]


def test_as_listas_do_traco_na_prancheta_batem_com_as_da_anotacao():
    from metrics.annotations import ESPESSURAS, FERRAMENTAS
    js = (PROJECT_ROOT / "dashboard" / "web" / "tactics.js").read_text(encoding="utf-8")
    assert f"var ESPESSURAS = {list(ESPESSURAS)};" in js
    ini = js.index("var FERRAMENTAS_TRACO = ")
    lista = json.loads(js[ini:js.index("];", ini) + 1].split("=", 1)[1])
    assert sorted(lista) == sorted(FERRAMENTAS)
    assert f"var FORMATO = {FORMATO};" in js
