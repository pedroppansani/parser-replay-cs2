"""
Testes do perfil por jogador.

O que está sendo travado aqui são os contratos que tornam a tabela legível, e não
só os números: taxa sempre com o bruto ao lado, amostra pequena marcada, e lado
calculado sobre os rounds certos. Uma taxa sem denominador é a forma mais fácil
de o painel mentir sem errar conta nenhuma.
"""
from __future__ import annotations

from pathlib import Path

import polars as pl
import pytest

from scripts.narrative import (
    FRASES_PERFIL,
    MAX_CARACTERISTICAS,
    descreve_jogador,
)
from metrics.player_profile import (
    CONCENTRACAO_MINIMA_GRUPO,
    MIN_EVENTOS_PARA_TAXA,
    RAIO_COMPANHEIRO,
    TAXAS_TODAS,
    accumulate,
    distancia_do_companheiro_mais_proximo,
    mistura_de_grupos,
    player_profile,
)

HALFTIME = 12
TICKS_POR_AMOSTRA = 64


def _rounds(n: int) -> pl.DataFrame:
    """Rounds sintéticos. Sem explosão de bomba de propósito: a detecção de
    tickrate cai na velocidade dos jogadores e, na falta dela, no default de 64 —
    que é o tickrate real destes demos. O que não pode acontecer é 128 aparecer.
    """
    return pl.DataFrame(
        {
            "round_num": list(range(1, n + 1)),
            "freeze_end": [i * 10_000 for i in range(1, n + 1)],
            "end": [i * 10_000 + 5_000 for i in range(1, n + 1)],
            "bomb_plant": [None] * n,
            "reason": ["ct_killed"] * n,
            "winner": ["ct"] * n,
        },
        schema_overrides={"bomb_plant": pl.Int64},
    ).with_columns(pl.col("round_num").cast(pl.UInt32))


def _cenario(
    n_rounds: int = 20,
    lado_por_round=None,
    distancia_do_alvo: float = 100.0,
    arma_do_alvo: str = "AK-47",
    contato_do_alvo: float = 20.0,
):
    """Monta um time de 5 onde o jogador 1 é o "alvo" do teste.

    Os outros quatro ficam juntos na origem; o alvo fica a `distancia_do_alvo`
    deles. Assim dá pra pedir "colado no time" ou "isolado" mexendo num número só.
    """
    lado_por_round = lado_por_round or {r: "ct" for r in range(1, n_rounds + 1)}
    pos, tick_rows, feat = [], [], []

    for r in range(1, n_rounds + 1):
        lado = lado_por_round[r]
        for amostra in range(10):
            tick = r * 10_000 + amostra * TICKS_POR_AMOSTRA
            for sid in range(1, 6):
                x = distancia_do_alvo if sid == 1 else 0.0
                y = 0.0 if sid == 1 else float(sid * 10)
                pos.append({"round_num": r, "tick": tick, "side": lado, "steamid": sid,
                            "name": f"p{sid}", "X": x, "Y": y, "Z": 0.0,
                            "place": "A" if sid == 1 else "B"})
                tick_rows.append({"round_num": r, "tick": tick, "steamid": sid,
                                  "name": f"p{sid}", "side": lado, "X": x, "Y": y, "Z": 0.0,
                                  "is_alive": True,
                                  "active_weapon_name": arma_do_alvo if sid == 1 else "AK-47",
                                  "current_equip_value": 4000})
        for sid in range(1, 6):
            feat.append({"round_num": r, "steamid": sid, "name": f"p{sid}", "side": lado,
                         "survived": 1.0 if sid == 1 else 0.0, "was_traded": 0.0,
                         "trade_kills": 0,
                         "time_of_first_contact_s": contato_do_alvo if sid == 1 else 30.0})

    def df(rows, chave="round_num"):
        return pl.DataFrame(rows).with_columns(pl.col(chave).cast(pl.UInt32))

    kills = pl.DataFrame(
        {"round_num": [1], "tick": [10_100], "attacker_steamid": [2],
         "victim_steamid": [3], "weapon": ["ak47"]}
    ).with_columns(pl.col("round_num").cast(pl.UInt32))

    areas = df([{"round_num": r, "steamid": sid, "side": lado_por_round[r],
                 "area": "A" if sid == 1 else "B"}
                for r in range(1, n_rounds + 1) for sid in range(1, 6)])

    vazio_clutch = pl.DataFrame(
        schema={"round_num": pl.UInt32, "steamid": pl.Int64, "won": pl.Boolean}
    )
    return df(pos), df(tick_rows), df(feat), kills, _rounds(n_rounds), areas, vazio_clutch


def _perfil(**kwargs):
    pos, ticks, feat, kills, rounds, areas, clutch = _cenario(**kwargs)
    return player_profile(feat, pos, ticks, kills, rounds, areas, clutch, match_id="t")


# --- Posicionamento ---------------------------------------------------------

def test_quem_fica_colado_no_time_nao_sai_como_longe_do_time():
    """O teste que o enunciado pede: colado no time não vira "joga longe"."""
    perfil, _ = _perfil(distancia_do_alvo=50.0)
    alvo = perfil.filter(pl.col("name") == "p1").row(0, named=True)

    assert alvo["pct_rounds_longe_do_time"] == 0.0
    assert alvo["pct_rounds_isolado"] == 0.0


def test_quem_joga_fora_do_raio_sai_como_isolado():
    """Controle do teste acima: se ninguém sai isolado, o de cima não mede nada."""
    perfil, _ = _perfil(distancia_do_alvo=RAIO_COMPANHEIRO + 400)
    alvo = perfil.filter(pl.col("name") == "p1").row(0, named=True)

    assert alvo["pct_rounds_isolado"] == 1.0
    assert alvo["pct_rounds_longe_do_time"] == 1.0


def test_distancia_e_do_companheiro_mais_proximo_e_nao_do_centroide():
    """Num time espalhado, todo mundo fica longe do centro sem estar sozinho."""
    pos = pl.DataFrame(
        {
            "round_num": [1] * 3, "tick": [100] * 3, "side": ["ct"] * 3,
            "steamid": [1, 2, 3],
            "X": [0.0, 100.0, 5000.0], "Y": [0.0, 0.0, 0.0],
        }
    ).with_columns(pl.col("round_num").cast(pl.UInt32))

    d = distancia_do_companheiro_mais_proximo(pos)
    por_id = dict(zip(d["steamid"].to_list(), d["dist_vizinho_media"].to_list()))

    # 1 e 2 estão a 100u um do outro, ainda que o centroide esteja longe dos dois
    assert por_id[1] == pytest.approx(100.0)
    assert por_id[2] == pytest.approx(100.0)
    assert por_id[3] == pytest.approx(4900.0)


# --- Amostra fraca ----------------------------------------------------------

def test_um_clutch_em_uma_tentativa_nao_vira_cem_por_cento_firme():
    """O teste que o enunciado pede: 1 de 1 tem que sair marcado."""
    pos, ticks, feat, kills, rounds, areas, _ = _cenario()
    clutch = pl.DataFrame(
        {"round_num": [1], "steamid": [1], "won": [True]}
    ).with_columns(pl.col("round_num").cast(pl.UInt32))

    perfil, _ = player_profile(feat, pos, ticks, kills, rounds, areas, clutch, match_id="t")
    alvo = perfil.filter(pl.col("name") == "p1").row(0, named=True)

    assert alvo["taxa_conversao_clutch"] == 1.0
    assert alvo["taxa_conversao_clutch_d"] == 1
    assert alvo["taxa_conversao_clutch_fraco"] is True
    assert MIN_EVENTOS_PARA_TAXA > 1


def test_denominador_suficiente_nao_marca_amostra_fraca():
    pos, ticks, feat, kills, rounds, areas, _ = _cenario()
    n = MIN_EVENTOS_PARA_TAXA + 2
    clutch = pl.DataFrame(
        {"round_num": list(range(1, n + 1)), "steamid": [1] * n, "won": [True] * n}
    ).with_columns(pl.col("round_num").cast(pl.UInt32))

    perfil, _ = player_profile(feat, pos, ticks, kills, rounds, areas, clutch, match_id="t")
    alvo = perfil.filter(pl.col("name") == "p1").row(0, named=True)
    assert alvo["taxa_conversao_clutch_fraco"] is False


def test_toda_taxa_vem_com_numerador_e_denominador():
    """Sem o bruto ao lado, 41% e 50% em 22 rounds parecem números diferentes."""
    perfil, _ = _perfil()
    for taxa in TAXAS_TODAS:
        assert taxa in perfil.columns, taxa
        assert f"{taxa}_n" in perfil.columns, f"{taxa}_n"
        assert f"{taxa}_d" in perfil.columns, f"{taxa}_d"
        assert f"{taxa}_ref" in perfil.columns, f"{taxa}_ref"
        assert f"{taxa}_fraco" in perfil.columns, f"{taxa}_fraco"


def test_sem_regua_de_corpus_a_referencia_exclui_o_proprio_jogador(monkeypatch):
    """Nível 3 da regra dos três níveis: sem régua de corpus, cai na mediana dos
    outros jogadores DESTA partida -- e mediana que inclui o próprio jogador
    puxaria a referência na direção dele."""
    import metrics.player_profile as pp

    monkeypatch.setattr(pp, "REGUA_FILE", Path("nao-existe-perfil_reference.json"))
    perfil, _ = _perfil(distancia_do_alvo=RAIO_COMPANHEIRO + 400)
    alvo = perfil.filter(pl.col("name") == "p1").row(0, named=True)

    # o alvo é o único isolado; a mediana dos OUTROS quatro tem que ser 0
    assert alvo["pct_rounds_isolado"] == 1.0
    assert alvo["pct_rounds_isolado_ref"] == 0.0
    assert alvo["regua_origem"] == "partida", "sem régua de corpus, a origem tem de estar marcada"


def test_com_regua_de_corpus_a_referencia_nao_depende_de_quem_jogou_a_partida(monkeypatch, tmp_path):
    """Nível 2: a régua é a distribuição agregada e ANÔNIMA do corpus.

    A mediana dos outros nove responde "ele está acima dos adversários de hoje",
    e o mesmo 100% vira destaque ou banalidade conforme quem entrou em quadra.
    """
    import json

    import metrics.player_profile as pp

    arq = tmp_path / "perfil_reference.json"
    arq.write_text(json.dumps({"n_partidas": 52, "n_jogador_partidas": 520,
                               "medianas": {"pct_rounds_isolado": 0.42}}), encoding="utf-8")
    monkeypatch.setattr(pp, "REGUA_FILE", arq)
    perfil, _ = _perfil(distancia_do_alvo=RAIO_COMPANHEIRO + 400)
    alvo = perfil.filter(pl.col("name") == "p1").row(0, named=True)

    assert alvo["pct_rounds_isolado_ref"] == 0.42, "a régua do corpus não foi usada"
    assert alvo["regua_partidas"] == 52 and alvo["regua_jogador_partidas"] == 520
    # e a régua NÃO é o número do jogador: o dele continua vindo só desta partida
    assert alvo["pct_rounds_isolado"] == 1.0


# --- Grupos comportamentais -------------------------------------------------

def test_rounds_distribuidos_nos_grupos_somam_o_total_do_jogador():
    """O teste que o enunciado pede."""
    atribuicoes = pl.DataFrame(
        {
            "round_num": list(range(1, 21)),
            "steamid": [1] * 20,
            "cluster": [0] * 9 + [1] * 6 + [2] * 5,
        }
    ).with_columns(pl.col("round_num").cast(pl.UInt32))

    m = mistura_de_grupos(atribuicoes).row(0, named=True)
    assert m["grupo_dominante_d"] == 20
    assert m["grupo_dominante"] == 0
    assert m["grupo_dominante_n"] == 9
    assert m["grupo_concentracao"] == pytest.approx(9 / 20)


def test_jogador_espalhado_fica_sem_grupo_dominante():
    """Versátil é informação real, não falha da métrica."""
    atribuicoes = pl.DataFrame(
        {
            "round_num": list(range(1, 21)),
            "steamid": [1] * 20,
            "cluster": [0] * 6 + [1] * 5 + [2] * 5 + [3] * 4,
        }
    ).with_columns(pl.col("round_num").cast(pl.UInt32))

    m = mistura_de_grupos(atribuicoes).row(0, named=True)
    assert m["grupo_dominante"] is None
    assert m["grupo_concentracao"] < CONCENTRACAO_MINIMA_GRUPO


def test_grupo_dominante_sobrevive_ao_acumulado():
    """REGRESSÃO: a coluna sumia na soma e o acumulado dizia "sem grupo
    dominante" para TODO mundo — texto plausível, e por isso invisível.

    Também trava o motivo de a contagem por grupo ser guardada inteira: somar só
    o `grupo_dominante_n` somaria as contagens de grupos DIFERENTES, já que o
    dominante de uma partida não é o da outra.
    """
    def perfil_com(cluster_por_round, match):
        pos, ticks, feat, kills, rounds, areas, clutch = _cenario(n_rounds=len(cluster_por_round))
        atrib = pl.DataFrame(
            {
                "round_num": list(range(1, len(cluster_por_round) + 1)),
                "steamid": [1] * len(cluster_por_round),
                "cluster": cluster_por_round,
            }
        ).with_columns(pl.col("round_num").cast(pl.UInt32))
        perfil, _ = player_profile(
            feat, pos, ticks, kills, rounds, areas, clutch,
            cluster_assignments=atrib, match_id=match,
        )
        return perfil

    # partida 1: domina o grupo 0; partida 2: domina o grupo 1, e com mais rounds
    p1 = perfil_com([0] * 8 + [1] * 2, "m1")
    p2 = perfil_com([1] * 14 + [0] * 6, "m2")

    somado = accumulate([p1, p2])
    alvo = somado.filter(pl.col("name") == "p1").row(0, named=True)

    # 14 rounds no grupo 1 contra 14 no grupo 0... o desempate é pelo maior,
    # e o total tem que ser a soma de todos os rounds com grupo
    assert alvo["grupo_dominante_d"] == 30
    assert alvo["grupo_dominante_n"] == 16  # grupo 1: 2 + 14
    assert alvo["grupo_dominante"] == 1
    assert alvo["grupo_concentracao"] == pytest.approx(16 / 30)


# --- Lado -------------------------------------------------------------------

def test_taxas_por_lado_usam_os_rounds_daquele_lado():
    """O teste que o enunciado pede: troca de lado no intervalo (round 12).

    O jogador joga de TR nos 12 primeiros rounds e de CT nos 8 seguintes, e só
    encosta cedo no adversário na metade de TR. A taxa de CT tem que ser zero, e
    os denominadores têm que bater com os rounds de cada lado — não com os 20.
    """
    n = 20
    lados = {r: ("t" if r <= HALFTIME else "ct") for r in range(1, n + 1)}
    pos, ticks, feat, kills, rounds, areas, clutch = _cenario(
        n_rounds=n, lado_por_round=lados
    )
    # contato cedo só nos rounds de TR
    feat = feat.with_columns(
        pl.when((pl.col("steamid") == 1) & (pl.col("round_num") <= HALFTIME))
        .then(5.0)
        .otherwise(pl.col("time_of_first_contact_s"))
        .alias("time_of_first_contact_s")
    )

    perfil, _ = player_profile(feat, pos, ticks, kills, rounds, areas, clutch, match_id="t")
    alvo = perfil.filter(pl.col("name") == "p1").row(0, named=True)

    assert alvo["rounds_t"] == HALFTIME
    assert alvo["rounds_ct"] == n - HALFTIME
    assert alvo["pct_rounds_contato_cedo_t_d"] == HALFTIME
    assert alvo["pct_rounds_contato_cedo_ct_d"] == n - HALFTIME
    assert alvo["pct_rounds_contato_cedo_t"] == 1.0
    assert alvo["pct_rounds_contato_cedo_ct"] == 0.0


# --- Acumulado entre partidas -----------------------------------------------

def test_acumulado_soma_bruto_e_nao_tira_media_de_taxas():
    """Média de taxas daria o mesmo peso a uma partida de 16 e a uma de 30."""
    p1, _ = _perfil(n_rounds=10, distancia_do_alvo=RAIO_COMPANHEIRO + 400)
    p2, _ = _perfil(n_rounds=30, distancia_do_alvo=50.0)
    p2 = p2.with_columns(pl.lit("t2").alias("match_id"))

    somado = accumulate([p1, p2])
    alvo = somado.filter(pl.col("name") == "p1").row(0, named=True)

    assert alvo["partidas"] == 2
    assert alvo["rounds_jogados"] == 40
    assert alvo["pct_rounds_isolado_n"] == 10
    assert alvo["pct_rounds_isolado_d"] == 40
    # média das taxas daria 0,5; a conta certa dá 10/40
    assert alvo["pct_rounds_isolado"] == pytest.approx(0.25)


def test_tickrate_vem_da_deteccao_e_nunca_e_128():
    perfil, _ = _perfil()
    assert perfil["tickrate"][0] == 64


# --- Como o jogador joga, em texto ------------------------------------------

def _perfil_cru(**valores) -> dict:
    """Perfil mínimo com todas as colunas que `descreve_jogador` consulta."""
    base = {"name": "alvo", "rounds_jogados": 20, "partidas": 1}
    for chave in FRASES_PERFIL:
        base[chave] = 0.2
        base[f"{chave}_n"] = 4
        base[f"{chave}_d"] = 20
        base[f"{chave}_ref"] = 0.2
        base[f"{chave}_fraco"] = False
    base.update(valores)
    return base


def test_resumo_diz_em_quantos_rounds_cada_coisa_aconteceu():
    """Sem a contagem, o leitor precisa descer até os chips para saber se são
    6 de 18 ou 17 de 18."""
    p = _perfil_cru(
        pct_rounds_lurk=0.4, pct_rounds_lurk_n=8, pct_rounds_lurk_ref=0.1
    )
    d = descreve_jogador(p)
    assert "faz lurk em 8 rounds" in d["resumo"]


def test_contagem_usa_a_unidade_certa_de_cada_denominador():
    """Nem toda taxa é sobre rounds: kills de AWP se contam em kills."""
    p = _perfil_cru(
        pct_kills_de_awp=0.5, pct_kills_de_awp_n=6, pct_kills_de_awp_d=12,
        pct_kills_de_awp_ref=0.05,
    )
    d = descreve_jogador(p)
    # o denominador entra porque não é o total de rounds, que a frase já abriu
    assert "mata de AWP em 6 de 12 kills" in d["resumo"]
    assert "6 rounds" not in d["resumo"]


def test_singular_quando_a_contagem_e_um():
    p = _perfil_cru(
        pct_rounds_abertura_awp=0.05, pct_rounds_abertura_awp_n=1,
        pct_rounds_abertura_awp_ref=0.0, pct_rounds_abertura_awp_d=20,
    )
    d = descreve_jogador(p)
    # a diferença precisa passar da margem para a característica existir
    if d["caracteristicas"]:
        assert "em 1 round" in d["resumo"]
        assert "em 1 rounds" not in d["resumo"]


def test_caracteristica_invertida_conta_o_complemento():
    """REGRESSÃO: "joga colado no time" sai da taxa de LONGE estar baixa.

    O número que sustenta a frase é `d - n`. Exibir o `n` ali mostrava a
    contagem do comportamento OPOSTO ao que a frase afirma — e o chip da
    interface mostrava o mesmo número errado.
    """
    p = _perfil_cru(
        pct_rounds_longe_do_time=0.10, pct_rounds_longe_do_time_n=2,
        pct_rounds_longe_do_time_d=20, pct_rounds_longe_do_time_ref=0.60,
    )
    d = descreve_jogador(p)
    traco = [c for c in d["caracteristicas"] if c["chave"] == "pct_rounds_longe_do_time"][0]

    assert traco["texto"] == "joga colado no time"
    assert traco["n"] == 18            # 20 - 2, e não 2
    assert traco["taxa"] == pytest.approx(0.9)
    assert traco["ref"] == pytest.approx(0.4)   # complemento de 0,60
    assert "joga colado no time em 18 rounds" in d["resumo"]


def test_amostra_fraca_nao_vira_afirmacao():
    """Marcada como fraca é marcada por um motivo: não sustenta a frase."""
    p = _perfil_cru(
        taxa_conversao_clutch=1.0, taxa_conversao_clutch_n=1,
        taxa_conversao_clutch_d=1, taxa_conversao_clutch_ref=0.1,
        taxa_conversao_clutch_fraco=True,
    )
    d = descreve_jogador(p)
    assert all(c["chave"] != "taxa_conversao_clutch" for c in d["caracteristicas"])


def test_jogador_sem_nada_fora_da_curva_nao_ganha_traco_inventado():
    d = descreve_jogador(_perfil_cru())
    assert d["caracteristicas"] == []
    assert "não se afasta da mediana" in d["resumo"]
    assert "None" not in d["resumo"]


def test_resumo_lista_no_maximo_o_teto_de_caracteristicas():
    """A lista inteira seria a própria tabela de novo."""
    valores = {}
    for chave in FRASES_PERFIL:
        valores[chave] = 0.9
        valores[f"{chave}_n"] = 18
        valores[f"{chave}_ref"] = 0.1
    d = descreve_jogador(_perfil_cru(**valores))
    assert len(d["caracteristicas"]) == MAX_CARACTERISTICAS
    assert d["resumo"].count(" e ") >= 1


# --- Cards de estilo (quem joga em cada grupo) ------------------------------

def test_card_de_estilo_ordena_pela_fracao_dos_proprios_rounds_e_mostra_o_bruto():
    """7 de 10 (70%) vem antes de 8 de 20 (40%): o peso é no jogador, não na contagem."""
    from metrics.player_profile import CONCENTRACAO_MINIMA_GRUPO, cards_de_estilo

    linhas = []
    for sid, nome, n_rounds, no_grupo0 in ((1, "a", 10, 7), (2, "b", 20, 8), (3, "c", 12, 3)):
        for rn in range(1, n_rounds + 1):
            # o resto dos rounds espalhado pelos grupos 1, 2 e 3
            linhas.append({"steamid": sid, "name": nome, "round_num": rn,
                           "cluster": 0 if rn <= no_grupo0 else 1 + rn % 3})
    cards = cards_de_estilo(pl.DataFrame(linhas))
    g0 = next(g for g in cards["grupos"] if g["cluster"] == 0)
    assert [j["name"] for j in g0["jogadores"]] == ["a", "b", "c"]
    assert g0["jogadores"][0]["texto"] == "7 de 10 rounds — 70%"
    assert g0["jogadores"][0]["dominante"] and CONCENTRACAO_MINIMA_GRUPO <= 0.70
    # c tem 3 de 12 no grupo 0 e o resto espalhado: nenhum grupo passa do piso
    assert "c" in cards["sem_grupo_dominante"]
    assert "c" in cards["nota"]


def test_card_de_estilo_sem_agrupamento_nao_estoura():
    from metrics.player_profile import cards_de_estilo

    assert cards_de_estilo(pl.DataFrame())["grupos"] == []
