"""
Testes dos papéis nomeados e das frases geradas a partir deles.

Dois dos testes aqui travam bugs que existiam de verdade:

- o índice de carrega piano era `esforço − recompensa`, e portanto elegia quem
  tinha recompensa baixa — ou seja, quem jogou mal. Há teste garantindo que um
  jogador que se expõe e NÃO traz benefício ao time não pontua no papel;
- as frases dos cards eram texto fixo escrito para a match_01. Há teste
  garantindo que campo ausente some da frase em vez de virar "None".
"""
from __future__ import annotations

import polars as pl
import pytest

from metrics.archetypes import (
    BAIT_MAX_DISTANCE,
    LIMIAR_CRITICO,
    MIN_AWP_ROUNDS,
    MIN_CLUTCH_ATTEMPTS,
    REPICK_MIN_PATH,
    TEAM_RIFLE_FRACTION,
    UNDERBUY_DELTA,
    archetype_indices,
    bait_events,
    economy_signals,
    evidencia,
    pick_highlight,
    piano_form,
    repick_engagements,
    solo_hold_signals,
)
from scripts.narrative import (
    contexto_placar,
    criterio_e_vice,
    historia_round_decisivo,
    manchete,
)


# --- Repick -----------------------------------------------------------------

def _styles(linhas: list[tuple[float, float]]) -> pl.DataFrame:
    return pl.DataFrame(
        {
            "round_num": list(range(1, len(linhas) + 1)),
            "steamid": [1] * len(linhas),
            "net_displacement": [n for n, _ in linhas],
            "path_distance": [p for _, p in linhas],
        }
    )


def test_repick_e_andar_muito_e_voltar_pro_mesmo_lugar():
    """A assinatura de jiggle: percorreu muito, saiu pouco do lugar."""
    marcado = repick_engagements(_styles([(30.0, 600.0)]))
    assert marcado["repick"].to_list() == [True]


def test_ficar_parado_nao_e_repick():
    """Deslocamento baixo E distância percorrida baixa é hold, não repick."""
    marcado = repick_engagements(_styles([(20.0, 40.0)]))
    assert marcado["repick"].to_list() == [False]


def test_avancar_espaco_nao_e_repick():
    """Quem percorreu muito e TERMINOU longe avançou, não reapareceu no ângulo."""
    marcado = repick_engagements(_styles([(800.0, 900.0)]))
    assert marcado["repick"].to_list() == [False]
    assert REPICK_MIN_PATH < 900.0, "fixture precisa passar do piso de percurso"


# --- Economia (a forma ECO do carrega piano) --------------------------------

def _ticks_eco(linhas: list[dict]) -> pl.DataFrame:
    registros = []
    for linha in linhas:
        for tick in (100, 101):
            registros.append(
                {
                    "round_num": 1, "tick": tick, "steamid": linha["steamid"],
                    "name": linha["name"], "side": linha["side"],
                    "current_equip_value": linha["equip"], "is_alive": True,
                    "active_weapon_name": linha["arma"],
                }
            )
    return pl.DataFrame(registros).with_columns(pl.col("round_num").cast(pl.UInt32))


def _rounds_um() -> pl.DataFrame:
    return pl.DataFrame({"round_num": [1], "freeze_end": [100]}).with_columns(
        pl.col("round_num").cast(pl.UInt32)
    )


def test_comprar_muito_menos_que_o_time_conta_como_sacrificio():
    ticks = _ticks_eco(
        [
            {"steamid": 1, "name": "pobre", "side": "t", "equip": 1000, "arma": "AK-47"},
            {"steamid": 2, "name": "b", "side": "t", "equip": 4500, "arma": "AK-47"},
            {"steamid": 3, "name": "c", "side": "t", "equip": 4500, "arma": "AK-47"},
        ]
    )
    eco = economy_signals(ticks, _rounds_um())
    por_id = dict(zip(eco["steamid"].to_list(), eco["eco_sacrifice"].to_list()))
    assert por_id[1] is True
    assert por_id[2] is False
    assert eco.filter(pl.col("steamid") == 1)["equip_delta"][0] <= UNDERBUY_DELTA


def test_smg_com_time_de_rifle_conta_mesmo_sem_diferenca_de_grana():
    """Ficar com a arma pior é sacrifício ainda que o valor total não caia tanto."""
    ticks = _ticks_eco(
        [
            {"steamid": 1, "name": "smg", "side": "t", "equip": 4200, "arma": "MAC-10"},
            {"steamid": 2, "name": "b", "side": "t", "equip": 4300, "arma": "AK-47"},
            {"steamid": 3, "name": "c", "side": "t", "equip": 4300, "arma": "AK-47"},
        ]
    )
    eco = economy_signals(ticks, _rounds_um())
    linha = eco.filter(pl.col("steamid") == 1).row(0, named=True)
    assert linha["is_smg"] is True
    assert linha["team_frac_rifle"] >= TEAM_RIFLE_FRACTION
    assert linha["eco_sacrifice"] is True


def test_round_de_eco_do_time_inteiro_nao_e_sacrificio_de_ninguem():
    """Se todos estão de SMG, ninguém abriu mão de nada pelo outro."""
    ticks = _ticks_eco(
        [
            {"steamid": i, "name": f"p{i}", "side": "t", "equip": 1500, "arma": "MAC-10"}
            for i in (1, 2, 3)
        ]
    )
    eco = economy_signals(ticks, _rounds_um())
    assert eco["eco_sacrifice"].sum() == 0


def test_arma_primaria_e_a_mais_empunhada_e_nao_a_do_freeze_end():
    """REGRESSÃO: no freeze time o jogador costuma estar com faca ou pistola.

    A primeira versão disto olhava o fim do freeze e classificou ZERO SMG em 9
    partidas -- um resultado plausível o bastante pra passar despercebido.
    """
    registros = []
    for tick, arma in ((100, "Desert Eagle"), (101, "MP9"), (102, "MP9")):
        registros.append(
            {"round_num": 1, "tick": tick, "steamid": 1, "name": "a", "side": "t",
             "current_equip_value": 2000, "is_alive": True, "active_weapon_name": arma}
        )
    ticks = pl.DataFrame(registros).with_columns(pl.col("round_num").cast(pl.UInt32))
    eco = economy_signals(ticks, _rounds_um())
    assert eco["primary_weapon"].to_list() == ["MP9"]


# --- Primeiro contato do time -----------------------------------------------

def _facts_contato(tempos: list[float | None]) -> pl.DataFrame:
    """Um round, um lado, N jogadores, com o tempo até o contato de cada um."""
    n = len(tempos)
    features = pl.DataFrame(
        {
            "round_num": [1] * n, "steamid": list(range(1, n + 1)),
            "name": [f"p{i}" for i in range(1, n + 1)], "side": ["t"] * n,
            "damage": [0] * n, "utility_damage": [0] * n, "kills": [0] * n,
            "trade_kills": [0] * n, "distinct_places": [4] * n,
            "frac_entering_fight": [0.1] * n, "survived": [0.0] * n,
            "was_traded": [0.0] * n, "time_of_first_contact_s": tempos,
        }
    ).with_columns(pl.col("round_num").cast(pl.UInt32))
    grenades = pl.DataFrame(
        {"round_num": [1] * n, "steamid": list(range(1, n + 1)),
         "enemy_blind_seconds": [0.0] * n, "utility_damage": [0] * n, "nades_thrown": [0] * n}
    ).with_columns(pl.col("round_num").cast(pl.UInt32))
    rounds = pl.DataFrame({"round_num": [1], "winner": ["t"]}).with_columns(
        pl.col("round_num").cast(pl.UInt32)
    )
    positions = pl.DataFrame(
        {"round_num": [1] * n, "steamid": list(range(1, n + 1)), "tick": [0] * n,
         "X": [0.0] * n, "Y": [0.0] * n}
    ).with_columns(pl.col("round_num").cast(pl.UInt32))
    from metrics.archetypes import round_facts
    return round_facts(features, grenades, rounds, positions)


def test_quem_encosta_primeiro_sozinho_e_o_entry():
    facts = _facts_contato([10.0, 20.0, 30.0])
    assert facts.sort("steamid")["first_contact_of_team"].to_list() == [True, False, False]


def test_empate_no_primeiro_contato_nao_e_abertura_de_ninguem():
    """REGRESSÃO: uma granada pegando o time todo no mesmo tick.

    Medido nas 9 partidas: 24 de 374 lados-round têm empate no primeiro lugar,
    um deles com QUATRO jogadores em 10,359375s -- os quatro eram contados como
    quem abriu o round, inflando o entry do time inteiro. Ninguém abriu nada ali.
    """
    facts = _facts_contato([10.0, 10.0, 10.0, 10.0, 80.0])
    assert facts["first_contact_of_team"].sum() == 0


def test_lado_sem_contato_nenhum_nao_gera_entry():
    facts = _facts_contato([None, None, None])
    assert facts["first_contact_of_team"].sum() == 0


# --- Solo hold (a forma CT do carrega piano) --------------------------------

def test_sozinho_no_site_so_conta_para_ct():
    areas = pl.DataFrame(
        {
            "round_num": [1, 1, 1],
            "steamid": [1, 2, 3],
            "side": ["ct", "ct", "t"],
            "area": ["B", "A", "B"],
        }
    ).with_columns(pl.col("round_num").cast(pl.UInt32))

    solo = solo_hold_signals(areas)
    por_id = dict(zip(solo["steamid"].to_list(), solo["alone_in_area"].to_list()))
    assert por_id[1] is True   # único CT no B
    assert por_id[2] is True   # único CT no A
    assert por_id[3] is False  # é T, não ancora bomb nenhum


# --- Baiter -----------------------------------------------------------------

def _cena_bait(distancia: float, trocou: bool) -> pl.DataFrame:
    """Companheiro morre no tick 100; o observado está a `distancia` dele."""
    kills = [
        {"round_num": 1, "tick": 100, "attacker_steamid": 99, "victim_steamid": 2,
         "victim_X": 0.0, "victim_Y": 0.0},
    ]
    if trocou:
        kills.append(
            {"round_num": 1, "tick": 140, "attacker_steamid": 1, "victim_steamid": 99,
             "victim_X": 0.0, "victim_Y": 0.0}
        )
    k = pl.DataFrame(kills).with_columns(pl.col("round_num").cast(pl.UInt32))

    ticks = pl.DataFrame(
        {
            "round_num": [1, 1],
            "tick": [100, 100],
            "steamid": [1, 2],
            "X": [distancia, 0.0],
            "Y": [0.0, 0.0],
            "is_alive": [True, True],
        }
    ).with_columns(pl.col("round_num").cast(pl.UInt32))
    return bait_events(k, ticks, {1: "A", 2: "A", 99: "B"})


def test_companheiro_caindo_perto_sem_troca_vira_oportunidade():
    ev = _cena_bait(distancia=300.0, trocou=False)
    assert ev.height == 1
    assert ev["traded"].to_list() == [False]


def test_trocar_a_morte_do_companheiro_nao_conta_contra_o_jogador():
    ev = _cena_bait(distancia=300.0, trocou=True)
    assert ev["traded"].to_list() == [True]


def test_quem_estava_do_outro_lado_do_mapa_fica_de_fora():
    """O filtro de distância existe pra não transformar posicionamento em acusação."""
    ev = _cena_bait(distancia=BAIT_MAX_DISTANCE + 500, trocou=False)
    assert ev.height == 0


# --- Índices ----------------------------------------------------------------

def _componentes(**valores) -> pl.DataFrame:
    """Dois jogadores: o do teste e um neutro, pro percentil ter com quem comparar."""
    base = {
        "steamid": [1, 2], "name": ["alvo", "neutro"], "team": ["A", "A"],
        "rounds_played": [20, 20],
        "first_contact_share": [0.2, 0.2], "util_per_round": [4.0, 4.0],
        "frac_entering_fight": [0.17, 0.17], "death_rate": [0.7, 0.7],
        "traded_death_share": [0.2, 0.2],
        "piano_t_share": [0.0, 0.0], "piano_ct_share": [0.0, 0.0],
        "piano_eco_share": [0.0, 0.0],
        "piano_t_rounds": [0, 0], "piano_ct_rounds": [0, 0],
        "piano_eco_rounds": [0, 0], "eco_sacrifice_rounds": [0, 0],
        "damage_share": [0.2, 0.2], "kill_share": [0.2, 0.2],
        "multikill_rounds": [1, 1], "clutch_wins": [0, 0],
        "distinct_places_mean": [5.4, 5.4], "path_per_round": [5280.0, 5280.0],
        "repick_share": [0.05, 0.05], "engagements": [40, 40],
        "awp_round_share": [0.0, 0.0], "awp_conversion": [0.0, 0.0],
        "awp_opening_picks": [0, 0], "awp_rounds": [0, 0],
        "bait_no_trade_share": [0.84, 0.84], "bait_untraded_per_round": [0.57, 0.57],
        "bait_return_per_opp": [1.0, 1.0], "bait_opportunities": [10, 10],
        "survival_rate": [0.29, 0.29],
        "clutch_attempts": [2, 2], "clutch_conversion": [0.0, 0.0],
        "clutch_damage_per_attempt": [50.0, 50.0],
    }
    for chave, valor in valores.items():
        base[chave] = [valor, base[chave][1]]
    return pl.DataFrame(base)


def test_esforco_sem_beneficio_ao_time_nao_e_carrega_piano():
    """O bug que este módulo existe pra corrigir.

    O índice antigo era `esforço − recompensa`, então quem se expunha e não
    produzia nada VENCIA o ranking. Aqui as três formas do papel exigem que o
    time tenha colhido: sem round convertido, `piano_*_share` é zero e o índice
    não sobe, por mais que o jogador morra cedo e gaste utility.
    """
    exposto = _componentes(
        first_contact_share=0.5, death_rate=0.95, util_per_round=12.0,
        damage_share=0.05, kill_share=0.05,
    )
    idx = archetype_indices(exposto, reference=None)
    alvo = idx.filter(pl.col("name") == "alvo").row(0, named=True)
    neutro = idx.filter(pl.col("name") == "neutro").row(0, named=True)
    assert alvo["idx_carrega_piano"] <= neutro["idx_carrega_piano"]


def test_as_tres_formas_somam_no_mesmo_indice():
    """Um jogador pode ser carrega piano sem nunca ter entrado primeiro."""
    so_economia = _componentes(piano_eco_share=0.5)
    idx = archetype_indices(so_economia, reference=None)
    alvo = idx.filter(pl.col("name") == "alvo").row(0, named=True)
    assert alvo["idx_carrega_piano"] > 0
    assert alvo["piano_total_share"] == pytest.approx(0.5)


def test_piano_form_nomeia_a_forma_dominante():
    assert piano_form({"piano_t_share": 0.3, "piano_ct_share": 0.0, "piano_eco_share": 0.1}) == "entrada"
    assert piano_form({"piano_t_share": 0.0, "piano_ct_share": 0.2, "piano_eco_share": 0.1}) == "solo no bomb"
    assert piano_form({"piano_t_share": 0.0, "piano_ct_share": 0.0, "piano_eco_share": 0.0}) is None


def test_rei_do_nt_exige_um_minimo_de_tentativas():
    """Com uma situação só, "nunca converte" não significa nada."""
    poucas = _componentes(clutch_attempts=MIN_CLUTCH_ATTEMPTS - 1, clutch_damage_per_attempt=200.0)
    idx = archetype_indices(poucas, reference=None)
    assert idx.filter(pl.col("name") == "alvo")["idx_rei_do_nt"][0] == 0.0

    muitas = _componentes(clutch_attempts=MIN_CLUTCH_ATTEMPTS + 3, clutch_damage_per_attempt=200.0)
    idx = archetype_indices(muitas, reference=None)
    assert idx.filter(pl.col("name") == "alvo")["idx_rei_do_nt"][0] > 0.0


def test_awper_exige_rounds_com_awp_na_mao():
    eventual = _componentes(awp_rounds=MIN_AWP_ROUNDS - 1, awp_round_share=0.1, awp_conversion=100.0)
    idx = archetype_indices(eventual, reference=None)
    assert idx.filter(pl.col("name") == "alvo")["idx_awper"][0] == 0.0


# --- Card de destaque -------------------------------------------------------

def _indices_para_destaque(**valores) -> pl.DataFrame:
    linhas = {
        "steamid": [1, 2], "name": ["a", "b"], "team": ["A", "B"],
        "idx_carry": [0.9, 0.1], "idx_carrega_piano": [0.0, 0.0],
        "idx_camper": [0.0, 0.0], "idx_repick": [0.0, 0.0], "idx_awper": [0.0, 0.0],
        "idx_mochila": [0.0, 0.0], "idx_baiter": [0.0, 0.0], "idx_rei_do_nt": [0.0, 0.0],
        "distinct_places_mean": [5.0, 5.0], "path_per_round": [5000.0, 5000.0],
        "damage_share": [0.2, 0.2], "survival_rate": [0.3, 0.3],
        "multikill_rounds": [1, 1], "clutch_wins": [0, 0],
        "repick_share": [0.1, 0.1], "engagements": [40, 40],
        "bait_opportunities": [5, 5], "bait_return_per_opp": [1.0, 1.0],
        "awp_rounds": [0, 0], "awp_conversion": [0.0, 0.0], "awp_opening_picks": [0, 0],
        "clutch_attempts": [2, 2],
        "clutch_damage_per_attempt": [50.0, 50.0],
        "piano_t_rounds": [0, 0], "piano_ct_rounds": [0, 0], "piano_eco_rounds": [0, 0],
        "eco_sacrifice_rounds": [0, 0], "traded_death_share": [0.2, 0.2],
        "piano_t_share": [0.0, 0.0], "piano_ct_share": [0.0, 0.0], "piano_eco_share": [0.0, 0.0],
    }
    for chave, valor in valores.items():
        linhas[chave] = [linhas[chave][0], valor]
    return pl.DataFrame(linhas)


def test_destaque_nao_repete_o_papel_do_card_da_esquerda():
    """Os dois cards saindo como "carry" contariam a mesma coisa duas vezes."""
    idx = _indices_para_destaque(idx_carry=0.99)
    escolhido = pick_highlight(idx, excluir_steamid=1)
    assert escolhido is None or escolhido["role"] != "carry"


def test_destaque_escolhe_o_papel_mais_marcante_e_nao_uma_ordem_fixa():
    """Se o AWPer foi mais marcante que o carrega piano, ganha o AWPer."""
    idx = _indices_para_destaque(idx_awper=0.95, idx_carrega_piano=0.40)
    escolhido = pick_highlight(idx, excluir_steamid=1)
    assert escolhido["role"] == "awper"

    idx = _indices_para_destaque(idx_awper=0.30, idx_carrega_piano=0.93)
    escolhido = pick_highlight(idx, excluir_steamid=1)
    assert escolhido["role"] == "carrega_piano"


def test_jogar_mal_nao_vira_destaque_sozinho():
    """"Foi mal" não é destaque: papel crítico só entra quando é extremo."""
    morno = _indices_para_destaque(idx_mochila=LIMIAR_CRITICO - 0.2)
    assert pick_highlight(morno, excluir_steamid=1) is None

    extremo = _indices_para_destaque(idx_mochila=LIMIAR_CRITICO + 0.1)
    escolhido = pick_highlight(extremo, excluir_steamid=1)
    assert escolhido["role"] == "mochila"


def test_partida_sem_ninguem_marcante_nao_inventa_destaque():
    assert pick_highlight(_indices_para_destaque(), excluir_steamid=1) is None


# --- Frases -----------------------------------------------------------------

def test_frase_do_round_decisivo_some_com_o_que_nao_existe():
    """REGRESSÃO: a frase era fixa e citava nick e placar de outra partida."""
    magro = {
        "round": 7, "winner_team": "A", "reason": "t_killed",
        "score_a": 4, "score_b": 3, "clutch_player": None, "clutch_against": 0,
        "multikill_player": None, "multikill_count": 0,
        "worst_deficit_overcome": 0, "opening": None,
    }
    frase = historia_round_decisivo(magro)
    assert "None" not in frase
    assert "0 kills" not in frase
    assert "1v0" not in frase
    assert frase.endswith(".")
    assert "Empate em 3-3" in frase


def test_frase_usa_o_clutch_quando_ele_existe():
    com_clutch = {
        "round": 7, "winner_team": "A", "reason": "bomb_defused",
        "score_a": 4, "score_b": 3, "clutch_player": "fulano", "clutch_against": 3,
        "multikill_player": None, "multikill_count": 0,
        "worst_deficit_overcome": 0, "opening": None,
    }
    frase = historia_round_decisivo(com_clutch)
    assert "fulano fechou o 1v3" in frase


def test_ponto_sem_volta_so_e_dito_no_round_certo():
    info = {
        "round": 7, "winner_team": "A", "reason": "t_killed", "score_a": 4, "score_b": 3,
        "clutch_player": None, "clutch_against": 0, "multikill_player": None,
        "multikill_count": 0, "worst_deficit_overcome": 0, "opening": None,
    }
    assert "não é mais devolvida" in historia_round_decisivo(info, ponto_sem_volta=7)
    assert "não é mais devolvida" not in historia_round_decisivo(info, ponto_sem_volta=12)


def test_primeiro_round_nao_tem_contexto_de_placar():
    assert contexto_placar({"score_a": 1, "score_b": 0, "winner_team": "A"}) is None


def test_criterio_sem_segundo_colocado_nao_cita_round_nenhum():
    decisivo = {"round": 1, "importance": 10}
    texto = criterio_e_vice([decisivo], decisivo)
    assert "vem em segundo" not in texto
    assert texto.endswith(".")


def test_evidencia_omite_campo_ausente():
    """Um AWPer sem pick de abertura não deve ganhar "0 picks de abertura"."""
    row = {"awp_rounds": 8, "awp_conversion": 0.0, "awp_opening_picks": 0}
    texto = evidencia("awper", row)
    assert "AWP na mão em 8 rounds" in texto
    assert "abertura" not in texto
    assert "0%" not in texto


@pytest.mark.parametrize(
    "papel,row",
    [
        ("awper", {"awp_rounds": 0, "awp_conversion": 0.0, "awp_opening_picks": 0}),
        ("rei_do_nt", {"clutch_attempts": 0, "clutch_wins": 0, "clutch_damage_per_attempt": 0.0}),
        ("repick", {"repick_share": 0.0, "engagements": 0}),
        ("baiter", {"bait_opportunities": 0, "survival_rate": 0.3, "bait_return_per_opp": 0.0}),
        ("carrega_piano", {"piano_t_share": 0.0, "piano_ct_share": 0.0, "piano_eco_share": 0.0,
                           "piano_t_rounds": 0, "piano_ct_rounds": 0, "eco_sacrifice_rounds": 0,
                           "traded_death_share": 0.0}),
    ],
)
def test_papel_sem_sustentacao_nao_gera_frase(papel, row):
    """REGRESSÃO: "AWP na mão em 0 rounds" descreve a ausência do papel como papel.

    Uma varredura das 720 frases possíveis (8 papéis x 90 jogador-partidas)
    achou 74 casos assim. Não chegavam à tela porque pick_highlight ignora
    índice zero — mas a frase não pode depender disso.
    """
    assert evidencia(papel, row) == ""


def test_manchete_sem_nada_notavel_devolve_none():
    vazio = {
        "clutch_player": None, "multikill_player": None, "multikill_count": 0,
        "worst_deficit_overcome": 0, "opening": None, "winner_team": "A",
    }
    assert manchete(vazio) is None
