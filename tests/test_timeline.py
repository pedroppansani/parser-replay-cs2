"""
Testes do timeline da autópsia de round e da formatação de dinheiro.

O bug que originou este arquivo: um card mostrava "-69,0s — PoisonLilies perdeu
a abertura / morreu para PoisonLilies". Dois sintomas, uma causa: mortes
ocorridas DENTRO do freeze time entravam na tabela de kills do round. Como a
origem do tempo é o fim do freeze, o tempo saía negativo; e a linha dessas mortes
traz `attacker_steamid == victim_steamid`, então a vítima aparecia como o próprio
matador.

Os quatro primeiros testes varrem os dados reais de `data/processed/`. Eles
falham se o defeito voltar em QUALQUER partida processada — é a rede que um
teste sintético não dá.
"""
from __future__ import annotations

import json
from pathlib import Path

import polars as pl
import pytest

from metrics.formatting import format_clock, format_money
from metrics.round_breakdown import CAUDA_POS_ROUND_S, HALFTIME_ROUND, analyze_round
from parsing.parser import kills_do_round_jogado

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PROCESSED = PROJECT_ROOT / "data" / "processed"

PARTIDAS = sorted(d.name for d in PROCESSED.glob("match_*") if (d / "breakdown.json").exists())
precisa_de_dados = pytest.mark.skipif(not PARTIDAS, reason="nenhuma partida processada")


def _breakdown(match_id: str) -> list[dict]:
    return json.loads((PROCESSED / match_id / "breakdown.json").read_text(encoding="utf-8"))


def _rounds(match_id: str) -> dict[int, dict]:
    tabela = pl.read_parquet(PROCESSED / match_id / "rounds.parquet")
    return {int(r["round_num"]): r for r in tabela.iter_rows(named=True)}


# --- Varredura dos dados reais ----------------------------------------------

@precisa_de_dados
@pytest.mark.parametrize("match_id", PARTIDAS)
def test_nenhuma_entrada_de_timeline_tem_tempo_negativo(match_id):
    """A origem é o fim do freeze time, então negativo é impossível."""
    ruins = [
        (b["round"], m["kind"], m["t"])
        for b in _breakdown(match_id)
        for m in b["moments"]
        if m["t"] < 0
    ]
    assert not ruins, f"{match_id}: entradas com tempo negativo: {ruins}"


@precisa_de_dados
@pytest.mark.parametrize("match_id", PARTIDAS)
def test_nenhuma_entrada_tem_vitima_igual_ao_matador(match_id):
    """Ninguém se mata na abertura do round."""
    ruins = [
        (b["round"], m["kind"], m["who"])
        for b in _breakdown(match_id)
        for m in b["moments"]
        if m.get("who") is not None and m.get("who") == m.get("by")
    ]
    assert not ruins, f"{match_id}: vítima igual ao matador: {ruins}"


@precisa_de_dados
@pytest.mark.parametrize("match_id", PARTIDAS)
def test_tick_do_evento_cai_dentro_da_janela_do_round(match_id):
    """O clique navega pelo tick: ele precisa estar em [freeze_end, end + cauda]."""
    bordas = _rounds(match_id)
    ruins = []
    for b in _breakdown(match_id):
        r = bordas[b["round"]]
        inicio = int(r["freeze_end"])
        fim = int(r["end"]) + int(CAUDA_POS_ROUND_S * 64)
        for m in b["moments"]:
            if not (inicio <= m["tick"] <= fim):
                ruins.append((b["round"], m["kind"], m["tick"], inicio, fim))
    assert not ruins, f"{match_id}: ticks fora da janela: {ruins}"


@precisa_de_dados
@pytest.mark.parametrize("match_id", PARTIDAS)
def test_nenhum_tempo_passa_da_duracao_do_round_mais_a_cauda(match_id):
    bordas = _rounds(match_id)
    ruins = []
    for b in _breakdown(match_id):
        r = bordas[b["round"]]
        limite = (int(r["end"]) - int(r["freeze_end"])) / 64 + CAUDA_POS_ROUND_S
        for m in b["moments"]:
            if m["t"] > limite:
                ruins.append((b["round"], m["kind"], m["t"], round(limite, 1)))
    assert not ruins, f"{match_id}: tempos acima da duração do round: {ruins}"


@precisa_de_dados
def test_exatamente_um_round_e_marcado_como_ultimo():
    for match_id in PARTIDAS:
        b = _breakdown(match_id)
        ultimos = [x["round"] for x in b if x["ultimo_round"]]
        assert len(ultimos) == 1, f"{match_id}: {ultimos}"
        assert ultimos[0] == max(x["round"] for x in b)


# --- Filtro na origem --------------------------------------------------------

def _kills(linhas: list[dict]) -> pl.DataFrame:
    return pl.DataFrame(linhas).with_columns(pl.col("round_num").cast(pl.UInt32))


def test_filtro_descarta_morte_dentro_do_freeze_time():
    """REGRESSÃO: a morte do tempo parado entrava e produzia os dois sintomas."""
    kills = _kills([
        {"round_num": 1, "tick": 6517, "attacker_steamid": 7, "victim_steamid": 7},
        {"round_num": 1, "tick": 12273, "attacker_steamid": 1, "victim_steamid": 2},
    ])
    rounds = pl.DataFrame({"round_num": [1], "freeze_end": [10935]}).with_columns(
        pl.col("round_num").cast(pl.UInt32)
    )
    limpo = kills_do_round_jogado(kills, rounds)

    assert limpo.height == 1
    assert limpo["tick"].to_list() == [12273]


def test_filtro_mantem_a_morte_depois_do_fim_do_round():
    """Ainda dá pra morrer depois do round decidido: essas são do round certo."""
    kills = _kills([
        {"round_num": 1, "tick": 15000, "attacker_steamid": 1, "victim_steamid": 2},
    ])
    rounds = pl.DataFrame({"round_num": [1], "freeze_end": [10935]}).with_columns(
        pl.col("round_num").cast(pl.UInt32)
    )
    assert kills_do_round_jogado(kills, rounds).height == 1


# --- Casos sintéticos do timeline -------------------------------------------

def _cenario(mortes: list[dict], round_row: dict) -> dict:
    """Um round com dois times de 5 e as mortes pedidas."""
    team_of = {**{i: "A" for i in range(1, 6)}, **{i: "B" for i in range(11, 16)}}
    rn = int(round_row["round_num"])  # o round do cenário, não um 1 fixo
    kills = pl.DataFrame(
        [
            {
                "round_num": rn, "tick": m["tick"],
                "attacker_steamid": m.get("attacker"), "victim_steamid": m["victim"],
                "attacker_name": m.get("attacker_name"), "victim_name": m["victim_name"],
                "victim_X": 0.0, "victim_Y": 0.0, "weapon": m.get("weapon", "ak47"),
            }
            for m in mortes
        ]
    ).with_columns(pl.col("round_num").cast(pl.UInt32))

    ticks = pl.DataFrame(
        {
            "round_num": [rn] * 10,
            "tick": [round_row["freeze_end"]] * 10,
            "steamid": list(range(1, 6)) + list(range(11, 16)),
            "name": [f"p{i}" for i in range(1, 6)] + [f"q{i}" for i in range(11, 16)],
            "side": ["t"] * 5 + ["ct"] * 5,
            "X": [0.0] * 10, "Y": [0.0] * 10, "is_alive": [True] * 10,
            "current_equip_value": [4000] * 10,
        }
    ).with_columns(pl.col("round_num").cast(pl.UInt32))

    def side_of_team(team, rn):
        return "t" if team == "A" else "ct"

    return analyze_round(
        round_row, kills, ticks, None, team_of, side_of_team, tickrate=64, ultimo_round=24
    )


def _morte(breakdown: dict) -> dict:
    """O momento que veio de uma morte.

    Não é `moments[0]`: momentos de contexto (round sem plant, sem utility)
    entram com o tick do início do round e ordenam antes de qualquer kill.
    """
    de_morte = [m for m in breakdown["moments"]
                if m["kind"] in ("abertura_perdida", "morte_isolada", "virada_numerica")]
    assert de_morte, f"nenhum momento de morte em {[m['kind'] for m in breakdown['moments']]}"
    return de_morte[0]


def _round_row(**extra) -> dict:
    base = {
        "round_num": 1, "start": 1000, "freeze_end": 2280, "end": 8000,
        "official_end": 8448, "winner": "ct", "reason": "t_killed", "bomb_plant": None,
    }
    base.update(extra)
    return base


def test_evento_no_ultimo_round_sem_official_end_e_datado_e_marcado():
    """O último round costuma vir sem official_end porque a partida acaba junto."""
    b = _cenario(
        [{"tick": 3000, "attacker": 11, "victim": 1,
          "attacker_name": "q11", "victim_name": "p1"}],
        _round_row(round_num=24, official_end=None),
    )
    assert b["ultimo_round"] is True
    m = _morte(b)
    assert m["t"] == pytest.approx((3000 - 2280) / 64, abs=0.06)  # o módulo arredonda para uma casa decimal
    assert m["t"] > 0


def test_evento_na_janela_pos_round_sai_marcado_e_com_tempo_positivo():
    b = _cenario(
        [{"tick": 8200, "attacker": 11, "victim": 1,
          "attacker_name": "q11", "victim_name": "p1"}],
        _round_row(),
    )
    m = _morte(b)
    assert m["pos_round"] is True
    assert m["t"] > 0
    assert m["t"] == pytest.approx((8200 - 2280) / 64, abs=0.06)  # o módulo arredonda para uma casa decimal


def test_evento_dentro_do_round_nao_e_marcado_como_pos_round():
    b = _cenario(
        [{"tick": 3000, "attacker": 11, "victim": 1,
          "attacker_name": "q11", "victim_name": "p1"}],
        _round_row(),
    )
    assert _morte(b)["pos_round"] is False


def test_morte_sem_atacante_nao_ganha_o_nome_da_vitima():
    """Sem atacante, o texto diz o que aconteceu — nunca o nome de alguém."""
    b = _cenario(
        [{"tick": 3000, "attacker": None, "victim": 1,
          "attacker_name": None, "victim_name": "p1", "weapon": "world"}],
        _round_row(),
    )
    m = _morte(b)
    assert m["by"] is None
    assert "p1" not in m["causa"]
    assert "mapa" in m["causa"]


def test_morte_pela_bomba_diz_que_foi_a_bomba():
    b = _cenario(
        [{"tick": 3000, "attacker": None, "victim": 1,
          "attacker_name": None, "victim_name": "p1", "weapon": "planted_c4"}],
        _round_row(),
    )
    assert _morte(b)["causa"] == "morreu para a bomba"


def test_evento_antes_do_freeze_end_estoura_em_vez_de_renderizar():
    """Depois do conserto, negativo é bug novo: o build tem que falhar."""
    with pytest.raises(ValueError, match="anterior ao fim do freeze time"):
        _cenario(
            [{"tick": 1500, "attacker": 11, "victim": 1,
              "attacker_name": "q11", "victim_name": "p1"}],
            _round_row(),
        )


def test_fim_de_primeira_metade_e_marcado():
    b = _cenario(
        [{"tick": 3000, "attacker": 11, "victim": 1,
          "attacker_name": "q11", "victim_name": "p1"}],
        _round_row(round_num=HALFTIME_ROUND),
    )
    assert b["fim_de_metade"] is True


# --- Dinheiro ---------------------------------------------------------------

def test_dinheiro_sai_com_simbolo_e_separador_brasileiro():
    assert format_money(960) == "960$"
    assert format_money(3750) == "3.750$"
    assert format_money(16000) == "16.000$"


def test_dinheiro_zero_e_valor_e_ausente_e_traco():
    """0$ é "não comprou"; — é "não medi". A diferença importa."""
    assert format_money(0) == "0$"
    assert format_money(None) == "—"


def test_relogio_em_minutos_e_segundos():
    assert format_clock(69) == "1:09"
    assert format_clock(5) == "0:05"
    assert format_clock(125) == "2:05"


def test_relogio_recusa_tempo_negativo():
    with pytest.raises(ValueError, match="tempo negativo"):
        format_clock(-69)


@precisa_de_dados
def test_contexto_de_economia_mostra_os_dois_lados():
    """960$ sozinho não diz nada sem saber com quanto o adversário entrou."""
    achou = False
    for match_id in PARTIDAS:
        for b in _breakdown(match_id):
            if not b["eco"]:
                continue
            achou = True
            assert b["eco_text"], f"{match_id} round {b['round']}: sem texto de economia"
            assert "$" in b["eco_text"]
            if b["equip_value_winner"] is not None:
                assert "adversário" in b["eco_text"]
    assert achou, "nenhum round de economia nas partidas processadas"
