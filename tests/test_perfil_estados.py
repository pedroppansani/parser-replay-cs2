"""Estados da aba Perfil (fase 16a, §19.1 item 9): o dado degradado mostra o ▲ em vez de esconder os cards."""
from __future__ import annotations

from leitura import perfil_erros as PE


def _payload(degradado: bool) -> dict:
    return {"player_profile": [{"steamid": 1, "name": "nomad", "rounds_jogados": 20}],
            "players": [{"steamid": 1, "team": "A", "rating": 1.1}], "structural_roles": [],
            "rating_info": {"modo_degradado": ["economia estimada só nesta partida"] if degradado else []}}


def test_sem_a_tabela_de_erros_o_aviso_leva_o_triangulo_e_os_jogadores_continuam():
    b = PE.bloco(_payload(False), None)
    assert b["degradado"] == "▲ sem a tabela de erros desta partida"
    assert [j["name"] for j in b["jogadores"]] == ["nomad"]            # o card do jogador não some


def test_rating_degradado_diz_o_motivo_com_o_triangulo():
    b = PE.bloco(_payload(True), None)
    assert b["degradado"].startswith("▲ ") and "degradado" in b["degradado"]
    assert [j["name"] for j in b["jogadores"]] == ["nomad"]

