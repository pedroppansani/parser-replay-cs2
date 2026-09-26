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
