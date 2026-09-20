"""
Testes do round decisivo por probabilidade de vitória, e do round mais
impressionante.

Os dois andam juntos neste arquivo de propósito: o que se quer travar é
justamente que eles são perguntas SEPARADAS e que o código aguenta os dois
resultados possíveis -- serem o mesmo round e serem rounds diferentes.
"""
from __future__ import annotations

import polars as pl
import pytest

from metrics.round_spectacle import (
    MIN_PONTOS_IMPRESSIONANTE,
    PESO_CLUTCH_BASE,
    PESO_CLUTCH_POR_INIMIGO_EXTRA,
    round_spectacle,
)
from metrics.win_probability import (
    MAX_PRORROGACOES_MODELADAS,
    _alvo_efetivo,
    MR12,
    MR15,
    curva_da_partida,
    detecta_formato,
    probabilidade_de_vitoria,
    round_decisivo,
    win_probability,
    wpa_minimo,
)

TICKRATE = 64


def _progressao(vencedores: list[str]) -> list[dict]:
    """Progressão de placar sintética a partir da sequência de vencedores."""
    a = b = 0
    out = []
    for i, w in enumerate(vencedores, start=1):
        if w == "A":
            a += 1
        else:
            b += 1
        out.append({"round": i, "winner_team": w, "reason": "t_killed",
                    "score_a": a, "score_b": b, "bomb_planted": False})
    return out


# --- O modelo ---------------------------------------------------------------

@pytest.mark.parametrize("n", [0, 1, 5, 9, 11, 12])
def test_empate_vale_meio_a_meio_em_qualquer_placar(n):
    """No modelo neutro, empate é 50/50 por construção -- em 0-0 e em 12-12.

    Se algum empate sair diferente de 0,5, o modelo está assimétrico entre os
    dois times, e toda a leitura de decisividade fica enviesada para um lado.
    """
    assert probabilidade_de_vitoria(n, n, MR12) == pytest.approx(0.5)


def test_match_point_e_o_melhor_estado_que_o_time_podia_estar():
    """Estar em match point é melhor que qualquer estado que leve até ele.

    A formulação importa: "maior que qualquer estado anterior" tomada ao pé da
    letra é FALSA e o teste pega isso -- 12-10 também é match point e vale mais
    que 12-11, porque o adversário precisa de três rounds em vez de dois. O que
    tem que valer é a monotonicidade: ganhar round nunca piora, perder round
    nunca melhora, e para uma mesma derrota acumulada o match point é o topo.
    """
    for b in range(12):
        no_match_point = probabilidade_de_vitoria(12, b, MR12)
        anteriores = [probabilidade_de_vitoria(a, b, MR12) for a in range(12)]
        assert no_match_point > max(anteriores)

    # monotonicidade nos dois eixos, que é o que sustenta a afirmação acima
    for a in range(12):
        for b in range(12):
            assert probabilidade_de_vitoria(a + 1, b, MR12) > probabilidade_de_vitoria(a, b, MR12)
            assert probabilidade_de_vitoria(a, b + 1, MR12) < probabilidade_de_vitoria(a, b, MR12)


def test_o_mesmo_resultado_pesa_mais_em_11_11_do_que_em_3_11():
    """É a propriedade central: alavancagem é do ESTADO, não do time.

    Ganhar um round em 11-11 muda a partida; ganhar o mesmo round perdendo de
    3-11 quase não muda nada. Isso substitui o antigo bônus de "placar
    apertado", que era um peso inventado para produzir este efeito à mão.
    """
    apertado = probabilidade_de_vitoria(12, 11, MR12) - probabilidade_de_vitoria(11, 11, MR12)
    resolvido = probabilidade_de_vitoria(4, 11, MR12) - probabilidade_de_vitoria(3, 11, MR12)
    assert apertado > resolvido
    assert apertado > 10 * resolvido  # não é "um pouco maior": é outra ordem


def test_a_soma_das_variacoes_leva_de_meio_ate_o_desfecho():
    """Pega erro de sinal e de estado de uma vez.

    Se a curva estiver deslocada de um round, ou se o wpa do time B tiver o
    sinal trocado, a soma não fecha em 1,0 nem em 0,0 -- e um erro desses
    passaria despercebido olhando só o round eleito.
    """
    venceu_a = _progressao(["A"] * 13 + ["B"] * 9)
    curva = curva_da_partida(venceu_a, MR12)
    assert 0.5 + curva["wpa_a"].sum() == pytest.approx(1.0)
    assert 0.5 + curva["wpa_b"].sum() == pytest.approx(0.0)

    venceu_b = _progressao(["B"] * 13 + ["A"] * 9)
    curva_b = curva_da_partida(venceu_b, MR12)
    assert 0.5 + curva_b["wpa_a"].sum() == pytest.approx(0.0)


def test_partida_de_placar_largo_nao_tem_round_decisivo():
    """13-3: nenhum round decidiu nada, e dizer isso é o resultado certo.

    A diferença se construiu ao longo do jogo. Eleger "o" round aqui inventaria
    uma virada que a partida não teve -- era exatamente o que a soma de pontos
    fazia, porque sempre existe um máximo.
    """
    prog = _progressao(["A", "A", "B", "A", "A", "A", "B", "A", "A", "A", "B",
                        "A", "A", "A", "A", "A"])
    _, resumo = win_probability(prog, MR12)
    assert resumo["decisivo"] is None
    # e mesmo sem decisivo a saída continua expondo os candidatos, para dar pra
    # auditar a decisão em vez de só receber um None
    assert len(resumo["top"]) == 3
    assert resumo["maior_wpa"] < resumo["minimo_exigido"]


def test_ganhar_o_round_em_12_12_nao_decide_a_partida():
    """Em 12-12 o round seguinte NÃO vale a partida: abre a prorrogação.

    REGRESSÃO: com o alvo fixo em 13, 13-12 era vitória e esse round sozinho
    levava de 50% a 100% -- o maior salto possível. Era o mesmo defeito que
    fazia a curva de uma partida de prorrogação fechar em 100% para o time
    ERRADO (ver `_valor`). Com a prorrogação modelada, 13-12 é o primeiro round
    do OT e vale 65,6%: quem vence precisa de mais três.
    """
    assert probabilidade_de_vitoria(12, 12, MR12) == pytest.approx(0.5)
    assert probabilidade_de_vitoria(13, 12, MR12) == pytest.approx(0.65625)
    assert probabilidade_de_vitoria(16, 12, MR12) == pytest.approx(1.0)
    # e o maior salto por round deixou de ser 0,50: como todo empate abre outra
    # prorrogação, nenhum round leva de 50% a 100% sozinho
    maior = max(
        abs(probabilidade_de_vitoria(a + 1, b, MR12) - probabilidade_de_vitoria(a, b, MR12))
        for a in range(0, 20) for b in range(0, 20)
        if probabilidade_de_vitoria(a, b, MR12) not in (0.0, 1.0)
    )
    assert maior == pytest.approx(0.25)


def test_a_prorrogacao_tem_fundo_em_vez_de_recursao_infinita():
    """A cadeia de prorrogações é infinita; a conta precisa parar em algum lugar.

    Chegar ao começo da MAX_PRORROGACOES_MODELADAS-ésima exige tantos empates
    seguidos que o estado vale 0,5 -- e 0,5 num empate é a resposta certa. O que
    este teste trava é que ela PARE: sem o fundo, `_valor` estoura
    RecursionError e a página da partida não renderiza.
    """
    alvo, n = _alvo_efetivo(24, 24, MR12.rounds_para_vencer)
    assert n >= MAX_PRORROGACOES_MODELADAS
    assert probabilidade_de_vitoria(24, 24, MR12) == pytest.approx(0.5)
    # e o alvo cresce de 4 em 4 a cada prorrogação, a partir de 13
    assert [_alvo_efetivo(x, x, 13)[0] for x in (11, 12, 15, 18)] == [13, 16, 19, 22]


def test_empate_no_topo_e_declarado_em_vez_de_escondido():
    """Dois rounds de peso equivalente não viram uma escolha silenciosa."""
    prog = _progressao(["A", "B"] * 11 + ["A", "A"])
    _, resumo = win_probability(prog, MR12)
    assert resumo["empate_no_topo"] is True


def test_o_piso_do_decisivo_sai_do_formato_e_nao_de_um_numero_solto():
    """O mínimo é derivado do round mais barato possível, e muda com o formato."""
    assert wpa_minimo(MR12) > wpa_minimo(MR15)  # MR15 é mais longo: cada round pesa menos
    base = probabilidade_de_vitoria(1, 0, MR12) - probabilidade_de_vitoria(0, 0, MR12)
    assert wpa_minimo(MR12) == pytest.approx(1.5 * base)


# --- Detecção de formato ----------------------------------------------------

def _ticks_com_troca_em(round_da_troca: int) -> pl.DataFrame:
    linhas = []
    for rn in range(1, round_da_troca + 3):
        lado_a = "t" if rn < round_da_troca else "ct"
        for sid in range(1, 6):
            linhas.append({"round_num": rn, "tick": rn * 100, "steamid": sid, "side": lado_a})
        for sid in range(11, 16):
            linhas.append({"round_num": rn, "tick": rn * 100, "steamid": sid,
                           "side": "ct" if lado_a == "t" else "t"})
    return pl.DataFrame(linhas).with_columns(pl.col("round_num").cast(pl.UInt32))


@pytest.mark.parametrize("troca,esperado", [(13, "MR12"), (16, "MR15")])
def test_o_formato_sai_da_troca_de_lado_e_nao_de_um_padrao_assumido(troca, esperado):
    rounds = pl.DataFrame({"round_num": list(range(1, troca + 2))})
    assert detecta_formato(rounds, _ticks_com_troca_em(troca)).nome == esperado


# --- Round impressionante ---------------------------------------------------

def _rounds_sinteticos(n: int) -> pl.DataFrame:
    return pl.DataFrame(
        {"round_num": list(range(1, n + 1)),
         "reason": ["t_killed"] * n,
         "bomb_plant": [None] * n},
        schema_overrides={"bomb_plant": pl.Int64},
    ).with_columns(pl.col("round_num").cast(pl.UInt32))


def _kills_vazias() -> pl.DataFrame:
    return pl.DataFrame(
        schema={"round_num": pl.UInt32, "tick": pl.Int64,
                "attacker_steamid": pl.Int64, "victim_steamid": pl.Int64}
    )


def test_o_clutch_pesa_mais_quanto_maior_o_x_do_1vx():
    """1v4 não é "um pouco melhor" que 1v2: a chance de converter despenca."""
    def pontos(contra: int) -> float:
        sit = {1: {"winner_team": "A", "clutch_player": "x", "clutch_against": contra,
                   "multikill_count": 0, "worst_deficit_overcome": 0, "opening": None}}
        pr, _ = round_spectacle(sit, _rounds_sinteticos(1), _kills_vazias(), None, {}, TICKRATE)
        return float(pr["pontos"][0])

    assert pontos(2) == pytest.approx(PESO_CLUTCH_BASE)
    assert pontos(4) == pytest.approx(PESO_CLUTCH_BASE + 2 * PESO_CLUTCH_POR_INIMIGO_EXTRA)
    assert pontos(5) > pontos(4) > pontos(3) > pontos(2)


def test_round_sem_nada_de_notavel_nao_vira_o_mais_impressionante():
    """Piso existe para não eleger o menos sem graça de uma partida sem graça."""
    sit = {
        rn: {"winner_team": "A", "clutch_player": None, "clutch_against": 0,
             "multikill_count": 0, "worst_deficit_overcome": 0, "opening": None}
        for rn in range(1, 6)
    }
    _, resumo = round_spectacle(sit, _rounds_sinteticos(5), _kills_vazias(), None, {}, TICKRATE)
    assert resumo["impressionante"] is None
    assert resumo["maior_pontuacao"] < MIN_PONTOS_IMPRESSIONANTE


def test_o_impressionante_e_o_decisivo_podem_ser_rounds_diferentes():
    """O caso que motivou separar os dois módulos.

    Partida decidida no fim (o round 24 leva de 75% a 100%) mas com o clutch
    de 1v4 lá no round 2, quando o placar ainda não significava nada. O código
    tem que devolver rounds diferentes, sem que um contamine o outro.
    """
    prog = _progressao(["A", "B"] * 10 + ["A", "A", "B", "A"])
    _, wp = win_probability(prog, MR12)

    sit = {
        p["round"]: {"winner_team": p["winner_team"], "clutch_player": None,
                     "clutch_against": 0, "multikill_count": 0,
                     "worst_deficit_overcome": 0, "opening": None}
        for p in prog
    }
    sit[2].update({"clutch_player": "donk666", "clutch_against": 4})
    _, esp = round_spectacle(sit, _rounds_sinteticos(len(prog)), _kills_vazias(), None, {}, TICKRATE)

    assert wp["decisivo"]["round"] == 24
    assert esp["impressionante"]["round"] == 2
    assert esp["impressionante"]["round"] != wp["decisivo"]["round"]


def test_o_impressionante_e_o_decisivo_podem_ser_o_mesmo_round():
    """O outro caso: o clutch aconteceu justamente no round que valeu a partida."""
    prog = _progressao(["A", "B"] * 10 + ["A", "A", "B", "A"])
    _, wp = win_probability(prog, MR12)

    sit = {
        p["round"]: {"winner_team": p["winner_team"], "clutch_player": None,
                     "clutch_against": 0, "multikill_count": 0,
                     "worst_deficit_overcome": 0, "opening": None}
        for p in prog
    }
    sit[24].update({"clutch_player": "donk666", "clutch_against": 4})
    _, esp = round_spectacle(sit, _rounds_sinteticos(len(prog)), _kills_vazias(), None, {}, TICKRATE)

    assert esp["impressionante"]["round"] == wp["decisivo"]["round"] == 24


def test_componente_que_nao_pontuou_nao_aparece_no_card():
    """Mesma regra da decisão 18: ausência não se descreve como presença.

    "multikill: 0" num card diz que houve multikill de zero kills.
    """
    sit = {1: {"winner_team": "A", "clutch_player": "x", "clutch_against": 3,
               "multikill_count": 0, "worst_deficit_overcome": 0, "opening": None}}
    _, resumo = round_spectacle(sit, _rounds_sinteticos(1), _kills_vazias(), None, {}, TICKRATE)
    nomes = [c["componente"] for c in resumo["impressionante"]["componentes"]]
    assert nomes == ["clutch"]


def test_curva_vazia_nao_estoura():
    """Partida sem round nenhum devolve 'sem decisivo', não exceção."""
    assert round_decisivo(pl.DataFrame(), MR12)["decisivo"] is None


# --- Texto ------------------------------------------------------------------
# As frases são montadas por pedaços, e é aí que o português quebra: a
# concordância entre preposição e artigo não sobrevive a `f"{a} {b}"` ingênuo.

def test_preposicao_contrai_com_artigo_definido():
    from scripts.narrative import com_de

    assert com_de("o Time B na frente por 12-11") == "do Time B na frente por 12-11"
    assert com_de("a própria liderança por 12-11") == "da própria liderança por 12-11"
    # indefinido não contrai na escrita padrão
    assert com_de("um empate em 9-9") == "de um empate em 9-9"


def test_o_nome_do_time_nao_e_minusculado_nem_repetido():
    """REGRESSÃO dupla, do mesmo `.lower()` na frase inteira.

    Primeiro sintoma: "a partir de time b na frente". Segundo, depois do
    conserto: "Levou o Time B ... a partir do Time B na frente", que repete o
    sujeito. Quem liderava e venceu vira "a própria liderança".
    """
    from scripts.narrative import contexto_placar_sintagma

    lider_venceu = {"score_a": 11, "score_b": 13, "winner_team": "B"}
    assert contexto_placar_sintagma(lider_venceu) == "a própria liderança por 12-11"

    lider_perdeu = {"score_a": 12, "score_b": 12, "winner_team": "B"}
    assert contexto_placar_sintagma(lider_perdeu) == "o Time A na frente por 12-11"


def test_relogio_da_bomba_usa_virgula_decimal():
    """O resto da interface é pt-BR; "1.6s" no meio da frase lê como erro."""
    sit = {1: {"winner_team": "A", "clutch_player": None, "clutch_against": 0,
               "multikill_count": 0, "worst_deficit_overcome": 0, "opening": None}}
    rounds = pl.DataFrame(
        {"round_num": [1], "reason": ["bomb_defused"], "bomb_plant": [1000]}
    ).with_columns(pl.col("round_num").cast(pl.UInt32))
    bomb = pl.DataFrame(
        {"round_num": [1], "tick": [1000 + int(38.4 * TICKRATE)], "event": ["defuse"]}
    ).with_columns(pl.col("round_num").cast(pl.UInt32))

    _, resumo = round_spectacle(sit, rounds, _kills_vazias(), bomb, {}, TICKRATE)
    texto = resumo["impressionante"]["componentes"][0]["texto"]
    assert "1,6s" in texto and "1.6" not in texto
