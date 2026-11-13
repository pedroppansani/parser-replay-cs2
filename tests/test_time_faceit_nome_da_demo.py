"""Decisão 65: o time da FACEIT usa o nome que a demo grava ("team_t1ltedbot" -> "Time de t1ltedbot"), sem o prefixo `team_`.
Sem nome, com nome vazio ou genérico, vale a reserva da decisão 28 (o primeiro nick em ordem alfabética, sem caixa).
O mesmo nome aparece na lista de Partidas e nos cartões da landing, no cabeçalho, no Perfil, no Reescrever e no cartão do arremesso real da C4
(todos leem de `build_web_page._nome_do_lado`)."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from metrics.times import nick_do_nome_da_demo, nome_do_time_faceit

RAIZ = Path(__file__).resolve().parent.parent

NICKS = ["rol1ng-", "Z_o_R_o", "donk666", "_AmadeuS", "t1ltedbot"]          # a reserva dá "Time de _AmadeuS"

# os 18 times das 9 partidas da FACEIT: (nome que a demo grava, o que o site mostra)
ESPERADO = {
    "match_01": ("Time de t1ltedbot", "Time de HLEB"),
    "match_02": ("Time de lilpeepfan-", "Time de Krimbo"),
    "match_03": ("Time de lilpeepfan-", "Time de zecco"),
    "match_04": ("Time de somehxw", "Time de D0KT0R3N"),
    "match_05": ("Time de Olajida", "Time de lilpeepfan-"),
    "match_06": ("Time de xKacpersky", "Time de ar1sFLXR"),
    "match_07": ("Time de Krabeni", "Time de xKacpersky"),
    "match_08": ("Time de Ahuniwip", "Time de lilpeepfan-"),
    "match_09": ("Time de lemight", "Time de Magnojezzz"),
}


def test_o_nome_vem_da_demo_sem_o_prefixo_team():
    assert nome_do_time_faceit("team_t1ltedbot", NICKS) == "Time de t1ltedbot"
    assert nick_do_nome_da_demo("team_lilpeepfan-") == "lilpeepfan-"
    assert nick_do_nome_da_demo("  TEAM_Krimbo ") == "Krimbo"                  # prefixo sem caixa e com espaço
    assert nick_do_nome_da_demo("Krimbo") == "Krimbo"                          # sem prefixo: o nome inteiro
    assert nick_do_nome_da_demo("team_team_x") == "team_x"                     # só o primeiro prefixo sai


@pytest.mark.parametrize("nome", [None, "", "   ", "team_", "team", "Team", "CT", "t", "Terrorists", "Counter-Terrorists", "team_ct"])
def test_sem_nome_ou_com_nome_vazio_ou_generico_vale_a_reserva_da_decisao_28(nome):
    assert nick_do_nome_da_demo(nome) == ""
    assert nome_do_time_faceit(nome, NICKS) == "Time de _AmadeuS"              # o primeiro nick em ordem alfabética, sem caixa
    assert nome_do_time_faceit(nome, []) == ""                                 # sem nick nenhum: sem nome (quem chama põe "Lado A")


def test_o_nome_da_demo_ganha_da_reserva_mesmo_com_outros_nicks_antes_na_ordem():
    assert nome_do_time_faceit("team_zed", ["adam", "zed"]) == "Time de zed"


def _manifesto():
    p = RAIZ / "data" / "manifest.json"
    if not p.exists():
        pytest.skip("sem data/manifest.json")
    return json.loads(p.read_text(encoding="utf-8"))["partidas"]


@pytest.mark.parametrize("partida", sorted(ESPERADO))
def test_as_nove_partidas_da_faceit_mostram_o_nome_novo_em_todos_os_lugares(partida):
    from scripts.build_reescrever import dados_da_pagina
    from scripts.build_site import match_summary, times_das_partidas
    from scripts.build_web_page import cabecalho_da_partida
    manifesto = _manifesto()
    if partida not in manifesto or not (RAIZ / "data" / "processed" / partida / "web_payload.json").exists():
        pytest.skip("partida fora do corpus local")
    a, b = ESPERADO[partida]
    cab = cabecalho_da_partida(partida)
    assert [cab["lados"][s]["nome"] for s in "AB"] == [a, b]                                       # o cabeçalho (e o Perfil, que lê dele)
    m = match_summary(partida)
    assert [m["lados"][s]["nome"] for s in "AB"] == [a, b]                                         # a lista de Partidas e os cartões da landing
    assert times_das_partidas([m])[partida] == f"{a} × {b}"                                        # o cartão do arremesso real (C4)
    (p,) = dados_da_pagina([m], {"partidas": {}})["partidas"]
    assert [x["nome"] for x in p["lados"]] == [a, b]                                               # o Reescrever
    for s in "AB":                                                                                 # o nome da demo é de um jogador do lado, como o site mostra
        nome_demo = manifesto[partida]["times"][s]["nome"]
        payload = json.loads((RAIZ / "data" / "processed" / partida / "web_payload.json").read_text(encoding="utf-8"))
        assert nick_do_nome_da_demo(nome_demo) in payload["match"]["rosters"][s]


def test_o_nome_do_evento_continua_na_tabela_e_o_krakow_aparece_certo():
    from scripts.build_web_page import nome_do_evento
    assert nome_do_evento("iem-krakw-2026") == "IEM Kraków 2026"
