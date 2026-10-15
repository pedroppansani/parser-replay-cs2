"""Os exemplos da seção 7.2 ficam fixados (fase 18, complemento do Pedro; scripts/calibracao/erros_do_jogador.py).

- rodar de novo com as mesmas ocorrências dá os mesmos exemplos (e o mesmo registro);
- um exemplo que deixou de ser ocorrência é trocado, com a data e o motivo; os outros ficam;
- `sortear_de_novo` refaz todos.
"""
from __future__ import annotations

import polars as pl

from metrics import erros as E
from scripts.calibracao import erros_do_jogador as G


def _oc(n_partidas: int = 8, por_partida: int = 4, filtrar: set | None = None) -> pl.DataFrame:
    linhas = []
    for i in range(n_partidas):
        for j in range(por_partida):
            filtro = E.FILTRO_ROUND_DECIDIDO if (f"match_{i:02d}", j) in (filtrar or set()) else None
            linhas.append({"tipo": E.NAO_TROCOU, "match_id": f"match_{i:02d}", "round_num": j + 1, "tick": 1000 * (j + 1),
                           "steamid": 100 + j, "name": f"j{j}", "aliado_steamid": 200 + j, "filtro": filtro})
    return pl.DataFrame(linhas)


def test_rodar_de_novo_mantem_os_exemplos():
    oc = _oc()
    a = G.escolhe_exemplos(oc, {"exemplos": {}}, "2026-10-15")
    b = G.escolhe_exemplos(oc, {"exemplos": a}, "2026-12-01")
    assert a == b
    assert len(a[E.NAO_TROCOU]) == G.EXEMPLOS_POR_TIPO
    por_partida = {}
    for r in a[E.NAO_TROCOU]:
        por_partida[r["partida"]] = por_partida.get(r["partida"], 0) + 1
        assert r["semente"] == G.SEMENTE_DOS_EXEMPLOS and r["data_do_sorteio"] == "2026-10-15"
    assert max(por_partida.values()) <= G.MAX_EXEMPLOS_POR_PARTIDA


def test_so_o_exemplo_que_deixou_de_valer_e_trocado():
    oc = _oc()
    a = G.escolhe_exemplos(oc, {"exemplos": {}}, "2026-10-15")[E.NAO_TROCOU]
    caiu = a[3]
    oc2 = _oc(filtrar={(caiu["partida"], caiu["round"] - 1)})
    b = G.escolhe_exemplos(oc2, {"exemplos": {E.NAO_TROCOU: a}}, "2026-12-01")[E.NAO_TROCOU]
    chaves_a = {G._chave_do_registro(r) for r in a}
    chaves_b = {G._chave_do_registro(r) for r in b}
    assert len(chaves_a - chaves_b) == 1 and len(chaves_b - chaves_a) == 1
    novo = next(r for r in b if G._chave_do_registro(r) not in chaves_a)
    assert novo["substituido_em"] == "2026-12-01" and novo["motivo_da_substituicao"] == E.FILTRO_ROUND_DECIDIDO
    assert novo["substitui"]["partida"] == caiu["partida"] and novo["substitui"]["round"] == caiu["round"]
    # e rodar de novo depois da troca não muda mais nada
    assert G.escolhe_exemplos(oc2, {"exemplos": {E.NAO_TROCOU: b}}, "2027-01-01")[E.NAO_TROCOU] == b


def test_sortear_de_novo_refaz_com_a_data_nova():
    oc = _oc()
    a = G.escolhe_exemplos(oc, {"exemplos": {}}, "2026-10-15")
    c = G.escolhe_exemplos(oc, {"exemplos": a}, "2026-12-01", sortear_de_novo=True)
    assert [G._chave_do_registro(r) for r in c[E.NAO_TROCOU]] == [G._chave_do_registro(r) for r in a[E.NAO_TROCOU]]
    assert all(r["data_do_sorteio"] == "2026-12-01" for r in c[E.NAO_TROCOU])
