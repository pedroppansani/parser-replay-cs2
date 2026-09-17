"""
Testes dos dois cards de jogador da aba de leitura.

O que estes testes protegem, acima de tudo, são as TRAVAS: bottom frag só com
distância destacada, mochila só com vitória, e nunca o mesmo jogador nos dois
cards. Sem elas, o card da direita vira "o último do placar" -- que é aritmética,
não observação.
"""
from __future__ import annotations

import json
from pathlib import Path

import polars as pl
import pytest

from metrics.match_highlights import (
    LIMIAR_EMPATE_DESTAQUE,
    MIN_DISPERSOES_BOTTOM_FRAG,
    candidato_bottom_frag,
    match_highlights,
    mvp_da_partida,
    outro_destaque,
)
from scripts.narrative import historia_destaque, historia_mvp

PROCESSED = Path("data/processed")


def _players(adrs: list[float], kasts: list[float] | None = None) -> pl.DataFrame:
    n = len(adrs)
    kasts = kasts or [70.0] * n
    return pl.DataFrame({
        "steamid": [1000 + i for i in range(n)],
        "name": [f"jog{i}" for i in range(n)],
        "team": ["A"] * (n // 2) + ["B"] * (n - n // 2),
        "adr": adrs,
        "kast_pct": kasts,
        "opening_kills": [2] * n,
        "clutches": [0] * n,
        "mvp_index": [a / max(adrs) for a in adrs],
    }).with_columns(pl.col("steamid").cast(pl.UInt64))


def _archetypes(players: pl.DataFrame, **idx) -> pl.DataFrame:
    n = players.height
    base = {
        "steamid": players["steamid"], "name": players["name"], "team": players["team"],
        "damage_share": [0.2] * n, "bait_no_trade_share": [0.1] * n,
        "clutch_attempts": [1] * n, "piano_total_share": [0.2] * n,
        "awp_rounds": [0] * n, "distinct_places_mean": [5.0] * n,
        "repick_share": [0.05] * n,
    }
    for papel in ("carrega_piano", "carry", "awper", "rei_do_nt",
                  "camper", "repick", "baiter", "mochila"):
        base[f"idx_{papel}"] = idx.get(papel, [0.1] * n)
    return pl.DataFrame(base)


# --- Trava 1: bottom frag não é "o último" ----------------------------------

def test_cinco_jogadores_parecidos_nao_elegem_bottom_frag():
    """Alguém sempre é o último. Isso é aritmética, não observação.

    Os cinco estão dentro do espalhamento comum: nenhum afundou.
    """
    assert candidato_bottom_frag(_players([88.0, 84.0, 80.0, 76.0, 72.0])) is None


def test_quem_afunda_de_verdade_vira_bottom_frag():
    """Agora sim: o último está muito abaixo do penúltimo."""
    cand = candidato_bottom_frag(_players([88.0, 84.0, 80.0, 76.0, 30.0]))
    assert cand is not None
    assert cand["name"] == "jog4"
    assert cand["dispersoes"] >= MIN_DISPERSOES_BOTTOM_FRAG
    # e ele carrega o número E a referência, senão não poderia renderizar
    assert cand["valor_texto"] and cand["referencia_texto"]


def test_bottom_frag_nao_e_arrastado_por_um_outlier_de_cima():
    """Um jogador muito ACIMA não pode criar um bottom frag lá embaixo.

    Com desvio padrão isso aconteceria: o topo infla a dispersão. Por isso a
    dispersão é medida por desvio absoluto mediano.
    """
    cand = candidato_bottom_frag(_players([200.0, 84.0, 80.0, 76.0, 74.0]))
    assert cand is None


# --- Trava 2: mochila exige vitória -----------------------------------------

def test_mochila_nao_e_eleito_em_time_que_perdeu():
    """Número ruim em time que perdeu é jogador ruim, não mochila.

    "Carregado" quer dizer que o time ganhou EM VOLTA dele. Sem vitória, a
    função não existe e não pode disputar o card.
    """
    players = _players([90.0, 85.0, 80.0, 75.0, 70.0])
    arq = _archetypes(players, mochila=[0.1, 0.1, 0.1, 0.1, 0.99])

    # jog4 está no time B; se B venceu, a mochila entra
    ganhou = outro_destaque(players, arq, None, mvp_steamid=1000, time_vencedor="B")
    assert ganhou is not None and ganhou["funcao"] == "mochila"

    # se B perdeu, não entra
    perdeu = outro_destaque(players, arq, None, mvp_steamid=1000, time_vencedor="A")
    assert perdeu is None or perdeu["funcao"] != "mochila"


# --- Trava 3: nunca repete o MVP --------------------------------------------

def test_o_card_da_direita_nunca_e_o_mvp():
    players = _players([120.0, 85.0, 80.0, 75.0, 70.0])
    # o índice mais alto de todos é justamente o do MVP
    arq = _archetypes(players, camper=[0.99, 0.9, 0.1, 0.1, 0.1])
    _, cards = match_highlights(players, arq, None, {}, "A")
    assert cards["mvp"]["name"] == "jog0"
    assert cards["destaque"] is not None
    assert cards["destaque"]["steamid"] != cards["mvp"]["steamid"]


@pytest.mark.parametrize("match_id", sorted(p.name for p in PROCESSED.glob("match_*")))
def test_no_dado_real_os_dois_cards_sao_pessoas_diferentes(match_id):
    caminho = PROCESSED / match_id / "insights.json"
    if not caminho.exists():
        pytest.skip("sem insights.json")
    d = json.loads(caminho.read_text(encoding="utf-8"))
    if not d.get("mvp_card") or not d.get("highlight_card"):
        pytest.skip("partida sem um dos cards")
    assert d["mvp_card"]["steamid"] != d["highlight_card"]["steamid"]


# --- Trava 5: empate declarado ----------------------------------------------

def test_empate_entre_destaques_e_declarado():
    players = _players([120.0, 85.0, 80.0, 75.0, 70.0])
    arq = _archetypes(
        players,
        camper=[0.1, 0.92, 0.1, 0.1, 0.1],
        repick=[0.1, 0.1, 0.91, 0.1, 0.1],
    )
    d = outro_destaque(players, arq, None, mvp_steamid=1000, time_vencedor="A")
    assert d["equivalente"] is not None
    assert abs(d["index"] - d["equivalente"]["index"]) < LIMIAR_EMPATE_DESTAQUE
    assert "destaque equivalente" in historia_destaque(d)


# --- Trava 6: evidência obrigatória -----------------------------------------

def test_card_negativo_sem_numero_e_sem_referencia_nao_renderiza():
    """Adjetivo sem número atrás não é análise."""
    sem_evidencia = {
        "name": "jog9", "negativo": True, "evidencia": None,
        "label": "Bottom frag", "meaning": "afundou",
    }
    assert historia_destaque(sem_evidencia) == ""

    com_evidencia = {
        "name": "jog9", "negativo": True, "label": "Bottom frag", "meaning": "afundou",
        "evidencia": {"metrica": "de ADR", "valor": "38,0", "referencia": "71,0",
                      "referencia_nome": "jog3", "referencia_rotulo": "segundo pior"},
    }
    frase = historia_destaque(com_evidencia)
    assert "38,0" in frase and "71,0" in frase and "jog3" in frase


@pytest.mark.parametrize("match_id", sorted(p.name for p in PROCESSED.glob("match_*")))
def test_todo_card_negativo_do_dado_real_tem_numero_e_referencia(match_id):
    caminho = PROCESSED / match_id / "insights.json"
    if not caminho.exists():
        pytest.skip("sem insights.json")
    d = json.loads(caminho.read_text(encoding="utf-8"))
    card = d.get("highlight_card")
    if not card or not card.get("negativo"):
        pytest.skip("destaque não é negativo nesta partida")
    ev = card.get("evidencia") or {}
    assert ev.get("valor") and ev.get("referencia")


# --- MVP: componentes e comparação ------------------------------------------

def test_o_mvp_expoe_os_componentes_e_o_melhor_dos_outros():
    """Um número agregado sozinho não deixa conferir nada."""
    players = _players([120.0, 95.0, 80.0, 75.0, 70.0], kasts=[90.0, 70.0, 65.0, 60.0, 55.0])
    mvp = mvp_da_partida(players, {1000: "Entry fragger"})
    assert mvp["name"] == "jog0"
    assert mvp["funcao"] == "Entry fragger"

    adr = [c for c in mvp["componentes"] if c["chave"] == "adr"][0]
    assert adr["lidera"] is True
    assert adr["melhor_dos_outros"] == 95.0
    assert adr["melhor_dos_outros_nome"] == "jog1"

    frase = historia_mvp(mvp)
    assert "120,0" in frase and "95,0" in frase and "jog1" in frase


# --- Trava do texto: nada hardcoded -----------------------------------------

def test_duas_partidas_nao_geram_nenhuma_frase_identica():
    """REGRESSÃO: as frases já foram texto fixo escrito para a match_01.

    Se duas partidas diferentes produzirem a MESMA frase num card, ou o texto
    voltou a ser hardcoded, ou ele parou de usar o dado da partida.
    """
    vistas: dict[str, str] = {}
    for pasta in sorted(PROCESSED.glob("match_*")):
        caminho = pasta / "insights.json"
        if not caminho.exists():
            continue
        d = json.loads(caminho.read_text(encoding="utf-8"))
        for chave in ("mvp_card", "highlight_card"):
            frase = (d.get("narrative") or {}).get(chave)
            if not frase:
                continue
            marca = f"{chave}:{frase}"
            assert marca not in vistas, (
                f"{pasta.name} repete a frase de {vistas[marca]}: {frase!r}"
            )
            vistas[marca] = pasta.name
    assert len(vistas) >= 4, "poucas frases para o teste ter conteúdo"


# --- O gráfico saiu da aba de leitura ---------------------------------------

def test_o_grafico_de_probabilidade_saiu_da_leitura_e_esta_no_placar():
    """A mesma informação duas vezes na mesma página só gasta espaço."""
    html = Path("dashboard/web/template.html").read_text(encoding="utf-8")

    leitura = html[html.index('data-panel="insights"'):html.index('data-panel="rounds"')]
    placar = html[html.index('data-panel="rounds"'):html.index('data-panel="jogadores"')]

    assert 'id="wpchart"' not in leitura
    assert 'id="wpchart"' in placar
    # e a estrutura fixa continua: decisivo, depois os dois cards de jogador
    assert leitura.index('id="decisive"') < leitura.index('id="fig-mvp"')
    assert leitura.index('id="fig-mvp"') < leitura.index('id="fig-destaque"')


# --- Desempate no teto do percentil -----------------------------------------

def test_no_empate_o_destaque_negativo_vence_o_positivo():
    """REGRESSÃO: o empate era resolvido por ordem de inserção na lista.

    O percentil satura -- vários candidatos batem em 0,99-1,00 e a pontuação
    perde resolução justamente no topo. Medido no corpus, o match_03 tinha um
    bottom frag em 1,00 empatado com um repick em 1,00, e vencia quem tivesse
    sido inserido antes. Isso não é critério, é acidente.

    No empate vence o negativo, porque o card da esquerda já é um destaque
    positivo: um segundo positivo repete o tipo de informação, um negativo
    acrescenta.
    """
    players = _players([120.0, 95.0, 90.0, 85.0, 25.0])
    arq = _archetypes(players, repick=[0.1, 1.0, 0.1, 0.1, 0.1])

    d = outro_destaque(players, arq, None, mvp_steamid=1000, time_vencedor="A")
    assert d["funcao"] == "bottom_frag"
    assert d["negativo"] is True
    # e o empate continua sendo declarado
    assert d["equivalente"] is not None


def test_o_desempate_nao_afrouxa_as_travas_do_negativo():
    """Vencer empate é uma coisa; passar na trava é outra.

    Aqui os cinco jogadores estão próximos, então não existe bottom frag -- e o
    desempate não pode inventar um.
    """
    players = _players([100.0, 96.0, 92.0, 88.0, 84.0])
    arq = _archetypes(players, repick=[0.1, 1.0, 0.1, 0.1, 0.1])

    d = outro_destaque(players, arq, None, mvp_steamid=1000, time_vencedor="A")
    assert d["funcao"] != "bottom_frag"
    assert d["negativo"] is False


def test_o_empate_declarado_e_sempre_de_outro_jogador():
    """Dizer que o MESMO sujeito pontuou alto numa segunda função não informa
    que a escolha foi disputada -- e era o que acontecia."""
    players = _players([120.0, 95.0, 90.0, 85.0, 80.0])
    arq = _archetypes(
        players,
        camper=[0.1, 0.98, 0.1, 0.1, 0.1],
        repick=[0.1, 0.97, 0.1, 0.1, 0.1],   # o MESMO jogador em duas funções
    )
    d = outro_destaque(players, arq, None, mvp_steamid=1000, time_vencedor="A")
    if d.get("equivalente"):
        assert d["equivalente"]["name"] != d["name"]
