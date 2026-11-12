"""RS1: o Round Swing por jogador em p.p. por round, só exposto (`metrics/round_swing_jogador.py`, campo `round_swing` do `insights.json`, `data/player_profiles/round_swing.json`).

O modelo, a divisão do crédito e o rating não mudam: os testes abaixo conferem a conservação do crédito, a média e o erro padrão contra um recálculo independente (numpy,
sem o módulo), as marcas de 30 e de 100 rounds e que o número do insights é o do rating."""
from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import polars as pl
import pytest

from metrics.round_swing_jogador import MIN_ROUNDS_PARA_MOSTRAR, ROUNDS_ESTAVEL, agrega, do_jogador, marcas

RAIZ = Path(__file__).resolve().parent.parent
PARTIDAS = ["match_43", "match_38", "match_30"]


def _interim(m):
    if not (RAIZ / "data" / "interim" / m / "kills.parquet").exists():
        pytest.skip("sem interim")


# --- as marcas ------------------------------------------------------------------------------------------------------------------

def test_as_marcas_de_30_e_de_100_rounds():
    assert (MIN_ROUNDS_PARA_MOSTRAR, ROUNDS_ESTAVEL) == (30, 100)
    assert marcas(29) == {"poucos_rounds": True, "estavel": False}
    assert marcas(30) == {"poucos_rounds": False, "estavel": False}
    assert marcas(99) == {"poucos_rounds": False, "estavel": False}
    assert marcas(100) == {"poucos_rounds": False, "estavel": True}
    assert marcas(0)["poucos_rounds"] is True


# --- a média e o erro padrão (recálculo independente) ---------------------------------------------------------------------------------

def _bloco_de_uma_serie(serie):
    s = np.asarray(serie, dtype=float)
    return do_jogador(len(s), float(s.sum()), float((s ** 2).sum()))


@pytest.mark.parametrize("n", [2, 22, 30, 99, 100, 250])
def test_media_e_erro_padrao_batem_com_numpy(n):
    rng = np.random.default_rng(n)
    serie = rng.normal(1.0, 20.0, size=n)
    b = _bloco_de_uma_serie(serie)
    assert b["rounds"] == n
    assert b["pp_por_round"] == round(float(serie.mean()), 2)
    assert b["erro_padrao_pp"] == round(float(serie.std(ddof=1) / math.sqrt(n)), 2)


def test_o_agregado_entre_partidas_e_a_razao_das_somas_nao_a_media_das_medias():
    rng = np.random.default_rng(7)
    a, b = rng.normal(2.0, 18.0, size=16), rng.normal(-1.0, 22.0, size=30)           # uma partida de 16 rounds e uma de 30
    ag = agrega([(1, _bloco_de_uma_serie(a)), (1, _bloco_de_uma_serie(b))])[1]
    junto = np.concatenate([a, b])
    assert ag["rounds"] == 46 and ag["partidas"] == 2
    assert ag["pp_por_round"] == round(float(junto.mean()), 2) and ag["pp_por_round"] != round(float((a.mean() + b.mean()) / 2), 2)
    assert abs(ag["erro_padrao_pp"] - float(junto.std(ddof=1) / math.sqrt(46))) < 0.011       # as somas guardam a variância de um round, com a precisão gravada
    assert ag["poucos_rounds"] is False and ag["estavel"] is False


def test_um_round_so_nao_tem_erro_padrao_e_zero_rounds_nao_tem_numero():
    assert do_jogador(1, 5.0, 25.0)["erro_padrao_pp"] is None
    z = do_jogador(0, 0.0, 0.0)
    assert z["pp_por_round"] is None and z["poucos_rounds"] is True


# --- o campo no insights.json bate com o rating e com um recálculo independente ---------------------------------------------------

@pytest.mark.parametrize("match_id", PARTIDAS)
def test_o_campo_do_insights_bate_com_o_rating_e_com_o_recalculo_independente(match_id):
    _interim(match_id)
    from metrics.rating import ModeloDeRound, carrega_referencia, rating
    from scripts.fit_rating import carrega_partida, tickrate_da_partida

    ins = json.loads((RAIZ / "data" / "processed" / match_id / "insights.json").read_text(encoding="utf-8"))
    assert all("round_swing" in p for p in ins["players"]), "reprocesse: o campo round_swing ainda não está no insights"
    ref = carrega_referencia()
    t, team_of, venc, kast = carrega_partida(match_id)
    per_round, resumo = rating(t, team_of, venc, kast, tickrate_da_partida(t), referencia=ref,
                               modelo=ModeloDeRound.da_referencia((ref or {}).get("modelo_de_round")))
    jogados = {int(j["steamid"]): int(j["rounds"]) for j in resumo["jogadores"]}
    por_jogador = {int(p["steamid"]): p for p in ins["players"]}
    for sid, n in jogados.items():
        rs = per_round.filter(pl.col("steamid") == sid)
        serie = np.zeros(n)
        serie[:rs.height] = 100 * rs["swing"].to_numpy()                          # o round sem evento do jogador vale zero e entra no denominador
        b = por_jogador[sid]["round_swing"]
        assert b["rounds"] == n
        assert abs(b["pp_por_round"] - serie.mean()) < 0.006, (sid, b, serie.mean())
        assert abs(b["erro_padrao_pp"] - serie.std(ddof=1) / math.sqrt(n)) < 0.006
        sub = next(j for j in resumo["jogadores"] if int(j["steamid"]) == sid)["sub_round_swing"]
        assert abs(b["pp_por_round"] - 100 * sub) < 0.006                          # é o mesmo número do sub-rating, antes da razão
        assert por_jogador[sid]["rating_sub"]["round_swing"] is not None


# --- a conservação do crédito -------------------------------------------------------------------------------------------------

@pytest.mark.parametrize("match_id", PARTIDAS)
def test_o_credito_de_cada_round_fecha_com_a_variacao_da_chance_menos_o_que_nao_tem_dono(match_id, monkeypatch):
    """Em cada round, o total do time que VENCEU = (a variação de cada kill, com sinal: + se matou, − se um dos seus morreu) + o salto final até 100%.
    As variações são as que o modelo calculou (registradas na chamada); o que não tem dono (a bomba plantada e o tempo que passam entre uma kill e a seguinte)
    não entra em nenhuma variação e portanto não entra no crédito de ninguém. Os dez jogadores somam zero (salvo morte sem matador inimigo)."""
    _interim(match_id)
    import metrics.rating as R
    from scripts.fit_rating import carrega_partida

    deltas: dict[int, list[tuple[str, float]]] = {}
    atual = {"rn": None}
    original = R._delta_da_kill

    def espia(modelo, antes, vivos, ben, adv, dif, bomba, ct, tempos):
        d = original(modelo, antes, vivos, ben, adv, dif, bomba, ct, tempos)
        deltas.setdefault(atual["rn"], []).append((ben, d))
        return d

    t, team_of, venc, _ = carrega_partida(match_id)
    modelo = R.ModeloDeRound.da_referencia((R.carrega_referencia() or {}).get("modelo_de_round"))
    grupos = R.grupo_do_round(t["ticks"], t["rounds"])
    fim = dict(t["rounds"].select("round_num", "end").iter_rows())
    k = t["kills"]
    sem_matador = {int(r["round_num"]) for r in k.iter_rows(named=True)
                   if r["tick"] < fim[r["round_num"]] and r.get("weapon") != "planted_c4"
                   and (r["attacker_steamid"] is None or r["attacker_side"] == r["victim_side"])}
    monkeypatch.setattr(R, "_delta_da_kill", espia)
    from scripts.fit_rating import tickrate_da_partida
    tr = tickrate_da_partida(t)
    # uma chamada por round: o espião sabe de que round é cada variação
    por_round = {}
    for rn in sorted(int(x) for x in k["round_num"].unique().to_list()):
        atual["rn"] = rn
        sw = R.swing_por_evento(k.filter(pl.col("round_num") == rn), t["damages"].filter(pl.col("round_num") == rn),
                                None if t["player_blind"] is None else t["player_blind"].filter(pl.col("round_num") == rn),
                                t["rounds"], grupos, modelo, team_of, venc, tr)
        por_round[rn] = sw
    for rn, sw in por_round.items():
        if rn in sem_matador or venc.get(rn) not in ("A", "B"):
            continue
        total = {"A": 0.0, "B": 0.0}
        for sid, s in sw.group_by("steamid", maintain_order=True).agg(pl.col("swing").sum()).iter_rows():
            total[team_of[sid]] += s
        assert abs(total["A"] + total["B"]) < 1e-9, f"round {rn}: os dois times não somam zero"
        w = venc[rn]
        creditado = sum(d if ben == w else -d for ben, d in deltas.get(rn, []))
        salto = total[w] - creditado
        assert -1e-9 <= salto <= 1.0 + 1e-9, f"round {rn}: sobrou {salto} entre o crédito das kills e o total do vencedor (o salto final vai de 0 a 1)"


def test_o_insights_de_todas_as_partidas_tem_o_campo_e_a_soma_do_time_nao_e_inventada():
    """Em cada partida o campo existe para todo jogador, os rounds jogados são os do jogador e as médias dos dez somam zero ponderadas pelos rounds (salvo as mortes sem matador)."""
    arqs = sorted((RAIZ / "data" / "processed").glob("match_*/insights.json"))
    if not arqs:
        pytest.skip("nenhuma partida processada")
    for a in arqs:
        ins = json.loads(a.read_text(encoding="utf-8"))
        assert all("round_swing" in p for p in ins["players"]), f"{a.parent.name}: sem o campo (reprocesse)"
        soma = sum(p["round_swing"]["soma_pp"] for p in ins["players"])
        assert abs(soma) < 0.05 * ins["match"].get("rounds", 30) + 25, (a.parent.name, soma)     # folga das mortes sem matador inimigo
