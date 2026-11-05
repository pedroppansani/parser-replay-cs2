"""Reescrever R0: o índice pequeno dos rounds sugeridos (leitura/sugeridos.py) e o arquivo docs/sugeridos.json."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from leitura.sugeridos import MAX_ERROS, MAX_MOMENTOS, sugeridos_da_partida
from metrics.erros import TIPOS_DE_ERRO_VALIDADOS

RAIZ = Path(__file__).resolve().parent.parent
ROUNDS = {n: {"freeze_end": 1000, "bomb_plant": None, "end": 9000} for n in range(1, 8)}


def _momento(tick, kind, who):
    return {"tick": tick, "t": (tick - 1000) / 64, "kind": kind, "who": who, "by": "x", "text": f"{kind} {who}"}


def _erro(rn, tipo, dwpa, nome="a", nivel=None):
    return {"tipo": tipo, "round_num": rn, "tick": 2000 + rn, "segundos": 15.0, "relogio": "1:30", "name": nome, "dwpa": dwpa, "nivel": nivel}


def test_decisivo_vem_com_a_frase_do_card_e_sem_instante():
    s = sugeridos_da_partida({"round": 5}, "Levou o Time A de 50% para 75%.", [], [], ROUNDS, 64)
    assert s == [{"round": 5, "motivo": "decisivo", "texto": "Levou o Time A de 50% para 75%.", "jogador": None,
                  "tick": None, "t": None, "relogio": None, "tipo": None}]


def test_momentos_so_com_jogador_um_por_round_pela_prioridade_e_no_maximo_tres():
    bd = [{"round": r, "moments": [_momento(2000 + r, "virada_numerica", None), _momento(3000 + r, "morte_isolada", f"j{r}"),
                                   _momento(2500 + r, "abertura_perdida", f"o{r}")]} for r in (1, 2, 3, 4, 5)]
    bd.append({"round": 6, "moments": [_momento(4000, "sem_plant", "z")]})                   # sem_plant não está na lista
    s = [x for x in sugeridos_da_partida(None, None, bd, [], ROUNDS, 64) if x["motivo"] == "momento"]
    assert len(s) == MAX_MOMENTOS == 3
    assert [(x["round"], x["tipo"], x["jogador"]) for x in s] == [(1, "abertura_perdida", "o1"), (2, "abertura_perdida", "o2"),
                                                                   (3, "abertura_perdida", "o3")]
    assert all(x["relogio"] for x in s)                                                        # o relógio do round vai junto


def test_so_erro_de_tipo_validado_entra_e_os_de_maior_perda_vem_primeiro():
    assert "possivel_bait" not in TIPOS_DE_ERRO_VALIDADOS
    erros = [_erro(1, "possivel_bait", -0.9), _erro(2, "nao_trocou", -0.01), _erro(3, "morreu_sozinho", -0.2, "zy", "depende"),
             _erro(4, "perdeu_a_troca", -0.1, "ab", "explicito"), _erro(4, "nao_trocou", -0.05)]
    s = [x for x in sugeridos_da_partida(None, None, [], erros, ROUNDS, 64) if x["motivo"] == "erro"]
    assert len(s) == MAX_ERROS == 2
    assert [(x["round"], x["jogador"], x["tipo"]) for x in s] == [(3, "zy", "morreu_sozinho"), (4, "ab", "perdeu_a_troca")]
    assert s[0]["texto"] == "Morreu sozinho · erro validado, depende da tática"


def test_o_arquivo_do_site_so_tem_partida_com_sugerido_e_nenhum_tipo_nao_validado():
    from scripts.build_site import indice_de_sugeridos, match_summary
    matches = [m for m in (match_summary(d.name) for d in sorted((RAIZ / "data" / "processed").glob("match_*"))) if m]
    if len(matches) < 3:
        pytest.skip("sem o processado")
    idx = json.loads(json.dumps(indice_de_sugeridos(matches), ensure_ascii=False))
    assert idx["formato"] == "sugeridos-do-reescrever" and idx["partidas"]
    for pid, p in idx["partidas"].items():
        assert p["sugeridos"], pid
        for x in p["sugeridos"]:
            assert x["motivo"] in ("decisivo", "momento", "erro")
            if x["motivo"] == "erro":
                assert x["tipo"] in TIPOS_DE_ERRO_VALIDADOS
            if x["motivo"] != "decisivo":
                assert x["jogador"] and x["tick"] is not None and x["relogio"], (pid, x)
        assert len(p["sugeridos"]) <= 1 + MAX_MOMENTOS + MAX_ERROS
    assert len(json.dumps(idx)) < 400_000                                                       # pequeno de verdade
    assert idx == json.loads(json.dumps(indice_de_sugeridos(matches), ensure_ascii=False))     # determinístico
