"""
Funções ESTRUTURAIS: qual é o trabalho do jogador no round.

Este módulo e o de traços comportamentais (`metrics/archetypes.py`) medem coisas
diferentes e não se misturam:

- **Função estrutural (aqui)**: qual é o trabalho dele. Âncora, entry, lurker,
  suporte. Depende do LADO e sai de posição e tempo.
- **Traço comportamental (lá)**: como ele executa esse trabalho. Um âncora pode
  ser carrega piano ou baiter; um entry pode ser carry ou mochila.

As duas leituras são independentes e nunca colapsam num ranking único.

UNIDADE DE ANÁLISE: a função é atribuída por (jogador, round), igual ao
clustering. A função do jogador na partida é a DOMINANTE nos rounds daquele lado,
sempre exibida com a concentração ("âncora em 9 de 12 rounds de CT"). Quem ancora
em 9 e rotaciona em 3 não é "âncora e ponto", e é essa nuance que o painel mostra.

LADO: funções de CT só são avaliadas nos rounds de CT do jogador e vice-versa. O
intervalo é no round 12 e os lados nunca se misturam, nem no cálculo nem na
referência.

Isto NÃO conflita com a decisão 8 do CLAUDE.md. Aquela proíbe o KMeans batizar
grupo que ele descobriu sozinho. Aqui as funções são definidas A PRIORI por
critério de jogo explícito — cada uma com os sinais que a caracterizam escritos
antes de olhar o dado — e o código só mede quem se encaixa. Descobrir um grupo e
batizá-lo é uma coisa; medir um critério declarado é outra.

IGL NUNCA é atribuído automaticamente. Quem chama o time não deixa rastro no
demo: o áudio existe (`parse_voice` devolve 124 mil pacotes por partida), mas sem
transcrição só dá para medir TEMPO DE FALA, e tempo de fala não acha o capitão —
medido, o jogador com 32% de toda a voz de uma partida era o astro do time, não
quem chamava. O rótulo de IGL vem de `roles_manual.json`, preenchido à mão.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import polars as pl

from metrics.map_areas import AREA_A, AREA_B, area_lookup, derive_place_areas
from metrics.player_profile import distancia_do_companheiro_mais_proximo
from metrics.positioning import position_samples, setup_snapshot
from metrics.timing import detect_tickrate

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# IGL e qualquer outra função que o dado não sustenta vivem aqui, preenchidas à
# mão. O código LÊ este arquivo e nunca escreve nele — há teste travando isso.
ROLES_MANUAL_FILE = PROJECT_ROOT / "roles_manual.json"

# Round em que os lados trocam (MR12).
HALFTIME_ROUND = 12

# --- Limiares de calibração -------------------------------------------------
# Os quatro primeiros saem da distribuição real das 9 partidas (881 rounds de CT).

# Dispersão do início: mediana da distância entre onde o jogador começou cada
# round e o começo MEDIANO dele naquele lado. Distribuição no CT: p25 142,
# mediana 251, p75 428, p90 596 unidades.
DISPERSAO_INICIO_CONSISTENTE = 300.0   # abaixo: começa sempre no mesmo lugar
DISPERSAO_INICIO_VARIADA = 450.0       # acima: não tem posição fixa (coringa)

# Distância entre onde começou o round e onde tomou o primeiro contato.
# Distribuição no CT: p25 174, mediana 473, p75 968 unidades.
DIST_CONTATO_PERTO = 350.0             # brigou onde começou (âncora)
DIST_CONTATO_LONGE = 800.0             # foi brigar longe dali (rotativo)

# Ancoragem dentro do round: poucas regiões e pouco deslocamento líquido.
MAX_REGIOES_ANCORA = 4
MAX_DESLOCAMENTO_ANCORA = 400.0

# Rotativo atravessa muitas regiões.
MIN_REGIOES_ROTATIVO = 6

# Raio em que um companheiro conta como "por perto" — o mesmo do perfil, que é o
# alcance em que uma troca ainda acontece.
RAIO_COMPANHEIRO = 600.0
FRACAO_ISOLAMENTO = 0.50

# Entry: contato cedo. 15s é o tempo de uma execução chegar ao site na maioria
# dos mapas; contato antes disso é abertura, não meio de round.
SEGUNDOS_CONTATO_CEDO = 15.0

# Entry exige que o time TENHA VINDO ATRÁS: pelo menos um companheiro chega à
# mesma área dele dentro desta janela. Sem isso é jogada individual ou lurker
# perdido, não entrada.
SEGUNDOS_TIME_ATRAS = 6.0

# Suporte: a utility precede a kill do companheiro nesta janela. 4s é o tempo em
# que uma flash ainda está cegando e uma smoke ainda está subindo.
SEGUNDOS_UTILITY_ANTES_DA_KILL = 4.0

# Trader: o quanto ele pode estar atrás do entry e ainda ser quem entra JUNTO.
# É o mesmo raio de apoio do resto do projeto -- a distância em que ainda dá para
# trocar a morte dentro da janela de 5s. Mais que isso e ele não entrou junto:
# chegou depois.
RAIO_ATRAS_DO_ENTRY = 600.0

# Janela de trade do projeto inteiro.
JANELA_TRADE_S = 5.0

# AWPer: a arma tem que ser consistente, não evento isolado. Um rifler que pega a
# AWP largada do adversário em 2 de 24 rounds não é AWPer.
MIN_ROUNDS_COM_SNIPER = 4
MIN_SHARE_SNIPER_PRINCIPAL = 0.30      # o AWPer do time
MIN_SHARE_SNIPER_SECUNDARIO = 0.15     # o segundo que puxa quando sobra dinheiro

# Snipers do CS2. Nomes de exibição (ticks) e codinomes (tabela de kills) são
# diferentes, por isso as duas listas.
SNIPERS_NO_DEMO = {"AWP", "SSG 08", "SCAR-20", "G3SG1"}
SNIPERS_NA_TABELA_DE_KILLS = {"awp", "ssg08", "scar20", "g3sg1"}

# Pontuação mínima para o round receber uma função. Abaixo disso o round fica
# SEM FUNÇÃO DEFINIDA, que é resultado válido: nem todo round tem um trabalho
# reconhecível, e forçar todo mundo numa caixinha é inventar.
PISO_PONTUACAO = 0.45

# Rounds mínimos num lado para a função da partida ser afirmada. Abaixo disso o
# perfil sai marcado como amostra insuficiente em vez de afirmar.
MIN_ROUNDS_POR_LADO = 6

# Funções e em que lado cada uma existe. AWPer vale nos dois.
FUNCOES = {
    "awper": ("AWPer", None),
    "ancora": ("Âncora", "ct"),
    "coringa": ("Coringa", "ct"),
    "rotativo": ("Rotativo", "ct"),
    "entry": ("Entry fragger", "t"),
    "trader": ("Trader", "t"),
    "lurker": ("Lurker", "t"),
    "suporte": ("Suporte", "t"),
}


def carrega_roles_manual(path: Path = ROLES_MANUAL_FILE) -> dict:
    """Funções atribuídas à mão (IGL). O código só LÊ este arquivo."""
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


# --- Fatos por round --------------------------------------------------------

def _primeiro_contato(damages: pl.DataFrame) -> pl.DataFrame:
    """Tick do primeiro contato de cada jogador em cada round.

    Contato = causou ou sofreu dano, a mesma definição que o resto do projeto
    usa (ver clustering/playstyle.first_contact_per_player_round).
    """
    lados = [
        damages.select(
            pl.col("round_num").cast(pl.UInt32),
            pl.col(col).alias("steamid"),
            pl.col("tick"),
        )
        for col in ("attacker_steamid", "victim_steamid")
    ]
    return (
        pl.concat(lados)
        .filter(pl.col("steamid").is_not_null())
        .group_by(["round_num", "steamid"], maintain_order=True)
        .agg(pl.col("tick").min().alias("tick_contato"))
    )


# A "posição inicial" é a de SETUP, não a do tick exato do fim do freeze.
#
# Medido: no instante em que o freeze acaba todos os CTs ainda estão no spawn.
# Usar aquele tick zera a dispersão de todo mundo, tira todos do bombsite e
# manda 859 dos 935 rounds de CT para "rotativo" -- a classificação inteira
# colapsa numa função só. `positioning.setup_snapshot` tira a foto
# SETUP_SECONDS_AFTER_FREEZE (10s) depois, que é quando o time já ocupou as
# posições e ainda não houve contato. É essa a posição que a leitura de jogo
# chama de "onde ele começa o round".


def _posicao_no_contato(positions: pl.DataFrame, contatos: pl.DataFrame) -> pl.DataFrame:
    """Onde o jogador estava quando tomou o primeiro contato.

    Pega a amostra de posição mais próxima do tick do contato: as posições são
    amostradas a 1 Hz e o contato acontece num tick qualquer.
    """
    return (
        positions.join(contatos, on=["round_num", "steamid"], how="inner")
        .with_columns((pl.col("tick") - pl.col("tick_contato")).abs().alias("dt"))
        .sort("dt")
        .group_by(["round_num", "steamid"], maintain_order=True)
        .first()
        .select(
            ["round_num", "steamid",
             pl.col("X").alias("contato_x"), pl.col("Y").alias("contato_y"),
             pl.col("place").alias("contato_place")]
        )
    )


def _time_veio_atras(
    positions: pl.DataFrame,
    contatos: pl.DataFrame,
    area_de: dict[str, str],
    tickrate: int,
) -> pl.DataFrame:
    """Um companheiro chegou à área do jogador logo depois do contato dele?

    É o que separa entry de jogada individual: entrar primeiro com o time vindo
    atrás é abrir espaço; entrar primeiro com o time do outro lado do mapa é
    lurker perdido.
    """
    janela = int(SEGUNDOS_TIME_ATRAS * tickrate)

    com_area = positions.with_columns(
        pl.col("place").replace_strict(area_de, default=None).alias("area")
    )

    # área do jogador no instante do contato
    minha = (
        com_area.join(contatos, on=["round_num", "steamid"], how="inner")
        .with_columns((pl.col("tick") - pl.col("tick_contato")).abs().alias("dt"))
        .sort("dt")
        .group_by(["round_num", "steamid"], maintain_order=True)
        .first()
        .select(["round_num", "steamid", "side", "tick_contato", pl.col("area").alias("minha_area")])
        .filter(pl.col("minha_area").is_not_null())
    )

    if minha.height == 0:
        return pl.DataFrame(
            schema={"round_num": pl.UInt32, "steamid": pl.UInt64, "time_veio_atras": pl.Boolean}
        )

    companheiros = com_area.select(
        ["round_num", "side", "tick",
         pl.col("steamid").alias("outro"), pl.col("area").alias("area_outro")]
    )

    chegou = (
        minha.join(companheiros, on=["round_num", "side"], how="inner")
        .filter(
            (pl.col("outro") != pl.col("steamid"))
            & (pl.col("area_outro") == pl.col("minha_area"))
            & (pl.col("tick") >= pl.col("tick_contato"))
            & (pl.col("tick") <= pl.col("tick_contato") + janela)
        )
        .select(["round_num", "steamid"])
        .unique(maintain_order=True)
        .with_columns(pl.lit(True).alias("time_veio_atras"))
    )

    return minha.select(["round_num", "steamid"]).join(
        chegou, on=["round_num", "steamid"], how="left"
    ).with_columns(pl.col("time_veio_atras").fill_null(False))


def _sinais_de_sniper(ticks: pl.DataFrame, kills: pl.DataFrame) -> pl.DataFrame:
    """Sniper na mão no round, e se a abertura do round foi dele com sniper."""
    com_sniper = (
        ticks.filter(
            pl.col("is_alive") & pl.col("active_weapon_name").is_in(list(SNIPERS_NO_DEMO))
        )
        .select(["round_num", "steamid"])
        .unique(maintain_order=True)
        .with_columns(pl.lit(True).alias("sniper_na_mao"))
    )

    abertura = (
        kills.sort("tick")
        .group_by("round_num", maintain_order=True)
        .first()
        .select(
            pl.col("round_num").cast(pl.UInt32),
            pl.col("attacker_steamid").alias("steamid"),
            pl.col("weapon").str.to_lowercase().alias("arma_abertura"),
        )
        .filter(pl.col("steamid").is_not_null())
        .with_columns(
            pl.col("arma_abertura").is_in(list(SNIPERS_NA_TABELA_DE_KILLS)).alias("abertura_de_sniper")
        )
        .select(["round_num", "steamid", "abertura_de_sniper"])
    )

    kills_sniper = (
        kills.with_columns(pl.col("weapon").str.to_lowercase().alias("arma"))
        .filter(
            pl.col("attacker_steamid").is_not_null()
            & pl.col("arma").is_in(list(SNIPERS_NA_TABELA_DE_KILLS))
        )
        .group_by([pl.col("round_num").cast(pl.UInt32), pl.col("attacker_steamid").alias("steamid")], maintain_order=True)
        .agg(pl.len().cast(pl.Int32).alias("kills_de_sniper_no_round"))
    )

    return com_sniper, abertura, kills_sniper


def _sinais_de_trader(
    fatos_parciais: pl.DataFrame,
    positions: pl.DataFrame,
    kills: pl.DataFrame,
    tickrate: int,
) -> pl.DataFrame:
    """Quem entrou JUNTO com o entry e quem trocou a morte dele.

    O trader é o segundo homem da entrada: ele vai atrás do entry para que a
    morte do entry não seja de graça. Duas medidas, e a primeira é a que
    identifica a função:

    `perto_do_entry` -- distância até o entry do time no instante em que o entry
    tomou o primeiro contato. É isso que "entra junto" quer dizer, e é o que
    separa o trader de quem chegou depois.

    `trocou_o_entry` -- matou quem matou o entry dentro da janela de trade. É o
    resultado da função, não a identificação dela: trader que tentou e não
    conseguiu continua sendo o trader daquele round, do mesmo jeito que um entry
    que perde a abertura continua sendo entry.
    """
    vazio = pl.DataFrame(
        schema={"round_num": pl.UInt32, "steamid": pl.UInt64,
                "dist_do_entry": pl.Float64, "trocou_o_entry": pl.Boolean}
    )

    entries = fatos_parciais.filter(pl.col("primeiro_contato_do_time")).select(
        ["round_num", "side",
         pl.col("steamid").alias("entry_id"),
         pl.col("tick_contato").alias("tick_entry")]
    )
    if entries.height == 0:
        return vazio

    # posição de todo mundo no instante do contato do entry
    pos_no_instante = (
        positions.join(entries, on=["round_num", "side"], how="inner")
        .with_columns((pl.col("tick") - pl.col("tick_entry")).abs().alias("dt"))
        .sort("dt")
        .group_by(["round_num", "steamid", "entry_id"], maintain_order=True)
        .first()
        .select(["round_num", "steamid", "entry_id", "tick_entry", "X", "Y"])
    )

    do_entry = pos_no_instante.filter(pl.col("steamid") == pl.col("entry_id")).select(
        ["round_num", "entry_id", pl.col("X").alias("ex"), pl.col("Y").alias("ey")]
    )

    distancias = (
        pos_no_instante.join(do_entry, on=["round_num", "entry_id"], how="inner")
        .filter(pl.col("steamid") != pl.col("entry_id"))
        .with_columns(
            (((pl.col("X") - pl.col("ex")) ** 2 + (pl.col("Y") - pl.col("ey")) ** 2).sqrt())
            .alias("dist_do_entry")
        )
        .select(["round_num", "steamid", "entry_id", "tick_entry", "dist_do_entry"])
    )

    # quem matou o entry, e quem vingou dentro da janela
    janela = int(JANELA_TRADE_S * tickrate)
    mortes = kills.select(
        pl.col("round_num").cast(pl.UInt32), "tick",
        pl.col("attacker_steamid").alias("matador"),
        pl.col("victim_steamid").alias("morto"),
    ).filter(pl.col("matador").is_not_null() & pl.col("morto").is_not_null())

    morte_do_entry = (
        mortes.join(
            entries.select(["round_num", "entry_id"]), on="round_num", how="inner"
        )
        .filter(pl.col("morto") == pl.col("entry_id"))
        .sort("tick")
        .group_by(["round_num", "entry_id"], maintain_order=True)
        .first()
        .select(
            ["round_num", "entry_id",
             pl.col("matador").alias("algoz"), pl.col("tick").alias("tick_morte_entry")]
        )
    )

    vingou = (
        mortes.join(morte_do_entry, on="round_num", how="inner")
        .filter(
            (pl.col("morto") == pl.col("algoz"))
            & (pl.col("tick") > pl.col("tick_morte_entry"))
            & (pl.col("tick") <= pl.col("tick_morte_entry") + janela)
        )
        .select(["round_num", pl.col("matador").alias("steamid")])
        .unique(maintain_order=True)
        .with_columns(pl.lit(True).alias("trocou_o_entry"))
    )

    return (
        distancias.join(vingou, on=["round_num", "steamid"], how="left")
        .with_columns(pl.col("trocou_o_entry").fill_null(False))
        .select(["round_num", "steamid", "dist_do_entry", "trocou_o_entry"])
    )


def _sinais_de_suporte(
    grenades: pl.DataFrame | None,
    player_blind: pl.DataFrame | None,
    kills: pl.DataFrame,
    team_of: dict[int, str],
    tickrate: int,
) -> pl.DataFrame:
    """Utility que ANTECEDE kill de companheiro — o sinal mais direto do suporte.

    A tabela de cegueira existe no projeto (`player_blind`, usada por
    metrics/grenades.py) e diz quem ficou cego, por quanto tempo e por culpa de
    quem. Uma flash que cega um inimigo e é seguida da kill de um companheiro
    naquele inimigo é utility que criou a kill do outro — que é a definição do
    papel.
    """
    vazio = pl.DataFrame(
        schema={"round_num": pl.UInt32, "steamid": pl.UInt64, "utility_virou_kill": pl.Int32}
    )
    if player_blind is None or player_blind.height == 0:
        return vazio

    janela = int(SEGUNDOS_UTILITY_ANTES_DA_KILL * tickrate)
    cols = set(player_blind.columns)
    quem_cegou = "attacker_steamid" if "attacker_steamid" in cols else None
    quem_ficou = "user_steamid" if "user_steamid" in cols else None
    if quem_cegou is None or quem_ficou is None:
        return vazio

    cegueiras = player_blind.select(
        pl.col("round_num").cast(pl.UInt32),
        pl.col(quem_cegou).alias("lancador"),
        pl.col(quem_ficou).alias("cegado"),
        pl.col("tick").alias("tick_cegueira"),
    ).filter(pl.col("lancador").is_not_null() & pl.col("cegado").is_not_null())

    mortes = kills.select(
        pl.col("round_num").cast(pl.UInt32),
        pl.col("attacker_steamid").alias("matador"),
        pl.col("victim_steamid").alias("morto"),
        pl.col("tick").alias("tick_kill"),
    ).filter(pl.col("matador").is_not_null() & pl.col("morto").is_not_null())

    junto = (
        cegueiras.join(mortes, on="round_num", how="inner")
        .filter(
            (pl.col("morto") == pl.col("cegado"))
            & (pl.col("tick_kill") >= pl.col("tick_cegueira"))
            & (pl.col("tick_kill") <= pl.col("tick_cegueira") + janela)
            & (pl.col("matador") != pl.col("lancador"))
        )
        .with_columns(
            pl.col("lancador").map_elements(lambda s: team_of.get(s), return_dtype=pl.String).alias("time_lancador"),
            pl.col("matador").map_elements(lambda s: team_of.get(s), return_dtype=pl.String).alias("time_matador"),
        )
        .filter(pl.col("time_lancador") == pl.col("time_matador"))
    )

    if junto.height == 0:
        return vazio
    return (
        junto.group_by(["round_num", "lancador"], maintain_order=True)
        .agg(pl.len().cast(pl.Int32).alias("utility_virou_kill"))
        .rename({"lancador": "steamid"})
    )


# --- Tabela de fatos --------------------------------------------------------

def fatos_por_round(
    tables: dict[str, pl.DataFrame],
    team_of: dict[int, str],
    map_name: str,
    tickrate: int,
) -> pl.DataFrame:
    """Uma linha por (round, jogador) com tudo que as funções precisam.

    Reaproveita o que já existe no projeto em vez de recalcular: as amostras de
    posição e o snapshot de setup vêm de `metrics/positioning.py`, a partição do
    mapa de `metrics/map_areas.py` e a distância ao companheiro mais próximo de
    `metrics/player_profile.py`.
    """
    ticks, kills, rounds = tables["ticks"], tables["kills"], tables["rounds"]
    damages = tables["damages"]

    positions = position_samples(ticks, rounds)
    setup = setup_snapshot(ticks, rounds, tickrate=tickrate)
    areas_tab = derive_place_areas(positions, tables.get("bomb"), map_name)
    area_de = area_lookup(areas_tab)

    contatos = _primeiro_contato(damages)
    pos_contato = _posicao_no_contato(positions, contatos)
    atras = _time_veio_atras(positions, contatos, area_de, tickrate)
    vizinho = distancia_do_companheiro_mais_proximo(positions)
    com_sniper, abertura, kills_sniper = _sinais_de_sniper(ticks, kills)
    suporte = _sinais_de_suporte(
        tables.get("grenades"), tables.get("player_blind"), kills, team_of, tickrate
    )

    # deslocamento líquido e regiões distintas no round
    ordenado = positions.sort(["round_num", "steamid", "tick"])
    movimento = ordenado.group_by(["round_num", "steamid"], maintain_order=True).agg(
        pl.col("X").first().alias("x0"), pl.col("Y").first().alias("y0"),
        pl.col("X").last().alias("x1"), pl.col("Y").last().alias("y1"),
        pl.col("place").n_unique().alias("regioes"),
    ).with_columns(
        (((pl.col("x1") - pl.col("x0")) ** 2 + (pl.col("y1") - pl.col("y0")) ** 2).sqrt())
        .alias("deslocamento_liquido")
    ).select(["round_num", "steamid", "regioes", "deslocamento_liquido"])

    # área dominante do round e área da maioria do time (para o lurker)
    com_area = positions.with_columns(
        pl.col("place").replace_strict(area_de, default=None).alias("area")
    ).filter(pl.col("area").is_not_null())
    dominante = (
        com_area.group_by(["round_num", "steamid", "side", "area"], maintain_order=True).agg(pl.len().alias("n"))
        .sort(["n", "area"], descending=[True, False])
        .group_by(["round_num", "steamid"], maintain_order=True)
        .first()
        .select(["round_num", "steamid", "side", pl.col("area").alias("area_dominante")])
    )
    do_time = (
        dominante.group_by(["round_num", "side", "area_dominante"], maintain_order=True).agg(pl.len().alias("n"))
        .sort(["n", "area_dominante"], descending=[True, False])
        .group_by(["round_num", "side"], maintain_order=True)
        .first()
        .select(["round_num", "side", pl.col("area_dominante").alias("area_do_time")])
    )

    # equipamento contra a média do time
    equip = (
        ticks.join(rounds.select(["round_num", "freeze_end"]), on="round_num", how="inner")
        .filter(pl.col("tick") >= pl.col("freeze_end"))
        .sort("tick")
        .group_by(["round_num", "steamid"], maintain_order=True)
        .first()
        .select(["round_num", "steamid", "side", pl.col("current_equip_value").cast(pl.Float64)])
        .with_columns(
            pl.col("current_equip_value").mean().over(["round_num", "side"]).alias("equip_do_time")
        )
        .with_columns(
            (pl.col("current_equip_value") - pl.col("equip_do_time")).alias("equip_delta")
        )
        .select(["round_num", "steamid", "current_equip_value", "equip_delta"])
    )

    # utility lançada e cegueira imposta, por round
    gren = tables.get("grenades")
    utility = (
        gren.filter(pl.col("thrower_steamid").is_not_null())
        .group_by([pl.col("round_num").cast(pl.UInt32), pl.col("thrower_steamid").alias("steamid")], maintain_order=True)
        .agg(pl.col("entity_id").n_unique().cast(pl.Int32).alias("granadas"))
        if gren is not None and gren.height and "thrower_steamid" in gren.columns
        else pl.DataFrame(schema={"round_num": pl.UInt32, "steamid": pl.UInt64, "granadas": pl.Int32})
    )

    # trade: vingou a morte de um companheiro dentro da janela
    janela_trade = int(JANELA_TRADE_S * tickrate)
    base_k = kills.select(
        pl.col("round_num").cast(pl.UInt32), "tick",
        pl.col("attacker_steamid").alias("matador"),
        pl.col("victim_steamid").alias("morto"),
    ).filter(pl.col("matador").is_not_null() & pl.col("morto").is_not_null())
    trades = (
        base_k.join(
            base_k.select(
                ["round_num", pl.col("tick").alias("tick_antes"),
                 pl.col("matador").alias("algoz"), pl.col("morto").alias("companheiro")]
            ),
            on="round_num", how="inner",
        )
        .filter(
            (pl.col("morto") == pl.col("algoz"))
            & (pl.col("tick") > pl.col("tick_antes"))
            & (pl.col("tick") <= pl.col("tick_antes") + janela_trade)
        )
        .with_columns(
            pl.col("matador").map_elements(lambda s: team_of.get(s), return_dtype=pl.String).alias("tm"),
            pl.col("companheiro").map_elements(lambda s: team_of.get(s), return_dtype=pl.String).alias("tc"),
        )
        .filter(pl.col("tm") == pl.col("tc"))
        .group_by(["round_num", "matador"], maintain_order=True)
        .agg(pl.len().cast(pl.Int32).alias("trades_feitos"))
        .rename({"matador": "steamid"})
    )

    base = (
        setup.select(
            ["round_num", "steamid", "name", "side",
             pl.col("X").alias("inicio_x"), pl.col("Y").alias("inicio_y"),
             pl.col("place").alias("inicio_place")]
        )
        .with_columns(
            pl.col("inicio_place").replace_strict(area_de, default=None).alias("inicio_area"),
            pl.col("inicio_place").str.contains("(?i)bombsite").fill_null(False).alias("inicio_no_site"),
        )
        .join(contatos, on=["round_num", "steamid"], how="left")
        .join(pos_contato, on=["round_num", "steamid"], how="left")
        .join(atras, on=["round_num", "steamid"], how="left")
        .join(vizinho, on=["round_num", "steamid"], how="left")
        .join(movimento, on=["round_num", "steamid"], how="left")
        .join(dominante.drop("side"), on=["round_num", "steamid"], how="left")
        .join(equip, on=["round_num", "steamid"], how="left")
        .join(utility, on=["round_num", "steamid"], how="left")
        .join(trades, on=["round_num", "steamid"], how="left")
        .join(suporte, on=["round_num", "steamid"], how="left")
        .join(com_sniper, on=["round_num", "steamid"], how="left")
        .join(abertura, on=["round_num", "steamid"], how="left")
        .join(kills_sniper, on=["round_num", "steamid"], how="left")
    )
    base = base.join(do_time, on=["round_num", "side"], how="left")

    freeze = rounds.select(["round_num", "freeze_end"])
    base = base.join(freeze, on="round_num", how="left").with_columns(
        pl.col("granadas").fill_null(0),
        pl.col("trades_feitos").fill_null(0),
        pl.col("utility_virou_kill").fill_null(0),
        pl.col("kills_de_sniper_no_round").fill_null(0),
        pl.col("sniper_na_mao").fill_null(False),
        pl.col("abertura_de_sniper").fill_null(False),
        pl.col("time_veio_atras").fill_null(False),
        pl.col("frac_tempo_isolado").fill_null(0.0),
    )

    base = base.with_columns(
        (
            ((pl.col("contato_x") - pl.col("inicio_x")) ** 2
             + (pl.col("contato_y") - pl.col("inicio_y")) ** 2).sqrt()
        ).alias("dist_inicio_contato"),
        ((pl.col("tick_contato") - pl.col("freeze_end")) / tickrate).alias("segundos_ate_contato"),
        (pl.col("frac_tempo_isolado") >= FRACAO_ISOLAMENTO).alias("isolado"),
        (
            pl.col("area_dominante").is_not_null()
            & pl.col("area_do_time").is_not_null()
            & (pl.col("area_dominante") != pl.col("area_do_time"))
        ).alias("area_diferente_do_time"),
    ).with_columns(
        pl.col("segundos_ate_contato")
        .rank("min")
        .over(["round_num", "side"])
        .alias("posto_contato"),
        pl.col("segundos_ate_contato").min().over(["round_num", "side"]).alias("primeiro_do_time_s"),
    ).with_columns(
        # empate no primeiro lugar não é abertura de ninguém (decisão 17)
        pl.col("posto_contato").eq(1).sum().over(["round_num", "side"]).alias("empatados"),
    ).with_columns(
        (
            (pl.col("posto_contato") == 1)
            & (pl.col("empatados") == 1)
            & pl.col("segundos_ate_contato").is_not_null()
        ).alias("primeiro_contato_do_time"),
        (
            pl.col("segundos_ate_contato").is_null()
            | (pl.col("segundos_ate_contato") > pl.col("primeiro_do_time_s"))
        ).alias("contato_tardio"),
    )

    # Segundo passo: o trader se define EM RELACAO ao entry, e so da pra saber
    # quem foi o entry depois de ranquear o contato de todo mundo. Por isso este
    # bloco vem aqui e nao junto dos outros sinais la em cima.
    trader = _sinais_de_trader(base, positions, kills, tickrate)

    return (
        base.join(trader, on=["round_num", "steamid"], how="left")
        .with_columns(pl.col("trocou_o_entry").fill_null(False))
        .sort(["round_num", "steamid"])
    )


def dispersao_do_inicio(fatos: pl.DataFrame) -> pl.DataFrame:
    """Por (jogador, lado): o quanto a posição inicial dele varia entre rounds.

    É a dimensão que separa coringa de âncora e rotativo, e ela é do JOGADOR e
    não do round -- por isso é calculada aqui e entra na pontuação de cada round.
    Sempre dentro do lado: o mesmo jogador começa em lugares diferentes de CT e
    de TR, e misturar os dois inventaria dispersão em todo mundo.
    """
    linhas = []
    for (sid, side), g in fatos.group_by(["steamid", "side"], maintain_order=True):
        validos = g.filter(pl.col("inicio_x").is_not_null())
        if validos.height == 0:
            continue
        mx = float(validos["inicio_x"].median())
        my = float(validos["inicio_y"].median())
        d = np.sqrt(
            (validos["inicio_x"].to_numpy() - mx) ** 2
            + (validos["inicio_y"].to_numpy() - my) ** 2
        )
        linhas.append(
            {"steamid": sid, "side": side,
             "dispersao_inicio": float(np.median(d)), "rounds_no_lado": validos.height}
        )
    if not linhas:
        return pl.DataFrame(
            schema={"steamid": pl.UInt64, "side": pl.String,
                    "dispersao_inicio": pl.Float64, "rounds_no_lado": pl.Int64}
        )
    return pl.DataFrame(linhas)


def consistencia_de_sniper(fatos: pl.DataFrame) -> pl.DataFrame:
    """Por jogador: em que fração dos rounds ele teve sniper na mão.

    É o antídoto contra o rifler que pegou a AWP largada do adversário em dois
    rounds: a função exige consistência ao longo da partida, não evento isolado.
    """
    return (
        fatos.group_by("steamid", maintain_order=True)
        .agg(
            pl.len().alias("rounds_totais"),
            pl.col("sniper_na_mao").sum().alias("rounds_com_sniper"),
        )
        .with_columns(
            (pl.col("rounds_com_sniper") / pl.col("rounds_totais")).alias("share_sniper")
        )
    )


# --- Pontuação por round ----------------------------------------------------
#
# Cada função vira uma pontuação contínua de 0 a 1, somando componentes nomeados.
# Os pesos estão escritos aqui e não espalhados no código: é a lista que diz o
# que cada função É, e mexer nela é mexer na definição.

def _faixa(valor, baixo: float, alto: float) -> float:
    """0 abaixo de `baixo`, 1 acima de `alto`, rampa linear no meio.

    Rampa e não degrau porque a fronteira entre as funções é contínua: um
    jogador com dispersão de 299 e outro com 301 não são categorias diferentes.
    """
    if valor is None:
        return 0.0
    v = float(valor)
    if alto == baixo:
        return 1.0 if v >= alto else 0.0
    if alto > baixo:
        return max(0.0, min(1.0, (v - baixo) / (alto - baixo)))
    return max(0.0, min(1.0, (baixo - v) / (baixo - alto)))


def pontua_round(linha: dict, dispersao: float | None, share_sniper: float) -> dict[str, float]:
    """Pontuação de cada função para um (jogador, round).

    Só funções do lado certo recebem nota: função de CT em round de TR é zero,
    não um número pequeno. Isso é estrutural, não calibração.
    """
    lado = linha["side"]
    p = {chave: 0.0 for chave in FUNCOES}

    # --- AWPer: vale nos dois lados --------------------------------------
    # A consistência é do JOGADOR (share_sniper); o round só contribui se ele
    # estava de fato com a arma na mão.
    if linha["sniper_na_mao"] and share_sniper >= MIN_SHARE_SNIPER_SECUNDARIO:
        base = 0.55 + 0.35 * _faixa(share_sniper, MIN_SHARE_SNIPER_SECUNDARIO, MIN_SHARE_SNIPER_PRINCIPAL)
        if linha["abertura_de_sniper"]:
            base += 0.10
        if linha["kills_de_sniper_no_round"]:
            base += 0.05
        p["awper"] = min(1.0, base)

    inicio_consistente = _faixa(
        dispersao, DISPERSAO_INICIO_VARIADA, DISPERSAO_INICIO_CONSISTENTE
    )
    inicio_variado = _faixa(dispersao, DISPERSAO_INICIO_CONSISTENTE, DISPERSAO_INICIO_VARIADA)
    perto_do_inicio = _faixa(linha["dist_inicio_contato"], DIST_CONTATO_LONGE, DIST_CONTATO_PERTO)
    longe_do_inicio = _faixa(linha["dist_inicio_contato"], DIST_CONTATO_PERTO, DIST_CONTATO_LONGE)

    if lado == "ct":
        # --- Âncora: começa sempre no mesmo lugar, e esse lugar é o site ----
        if linha["inicio_no_site"]:
            fica = _faixa(linha["regioes"], MAX_REGIOES_ANCORA + 2, MAX_REGIOES_ANCORA)
            parado = _faixa(
                linha["deslocamento_liquido"],
                MAX_DESLOCAMENTO_ANCORA * 2, MAX_DESLOCAMENTO_ANCORA,
            )
            p["ancora"] = (
                0.30 * inicio_consistente + 0.30 * perto_do_inicio
                + 0.20 * fica + 0.20 * parado
            )

        # --- Rotativo: começa sempre no mesmo lugar, mas vai brigar longe ---
        if not linha["inicio_no_site"]:
            atravessa = _faixa(linha["regioes"], MIN_REGIOES_ROTATIVO - 2, MIN_REGIOES_ROTATIVO)
            chega_depois = 1.0 if linha["contato_tardio"] else 0.0
            p["rotativo"] = (
                0.30 * inicio_consistente + 0.35 * longe_do_inicio
                + 0.20 * atravessa + 0.15 * chega_depois
            )

        # --- Coringa: não tem posição fixa ---------------------------------
        fora_do_site = 0.0 if linha["inicio_no_site"] else 1.0
        p["coringa"] = 0.65 * inicio_variado + 0.20 * fora_do_site + 0.15 * longe_do_inicio

    if lado == "t":
        # --- Entry: primeiro a encostar, cedo, e com o time vindo atrás -----
        if linha["primeiro_contato_do_time"] and linha["time_veio_atras"]:
            cedo = _faixa(linha["segundos_ate_contato"], SEGUNDOS_CONTATO_CEDO * 2, SEGUNDOS_CONTATO_CEDO)
            morreu = 0.0 if linha["sobreviveu"] else 1.0
            p["entry"] = 0.55 + 0.30 * cedo + 0.15 * morreu

        # --- Lurker: CONJUNÇÃO das três, não uma delas -----------------------
        if linha["isolado"] and linha["contato_tardio"] and linha["area_diferente_do_time"]:
            atraso = _faixa(
                (linha["segundos_ate_contato"] or 0) - (linha["primeiro_do_time_s"] or 0), 0.0, 20.0
            )
            p["lurker"] = 0.70 + 0.30 * atraso

        # --- Trader: entra JUNTO com o entry pra morte dele nao sair de graca -
        # A proximidade identifica, a troca confirma. Trader que tentou e nao
        # conseguiu continua sendo o trader daquele round, do mesmo jeito que um
        # entry que perde a abertura continua sendo entry -- por isso `trocou`
        # nao e porta de entrada, e peso.
        #
        # Os pesos sao escolhidos pra que PROXIMIDADE SOZINHA (0,40) fique ABAIXO
        # do piso de 0,45: andar perto do entry acontece em qualquer execucao de
        # bomb, e sem ser o segundo no contato nem trocar a morte, isso e o time
        # junto, nao um trader.
        perto = _faixa(linha["dist_do_entry"], RAIO_ATRAS_DO_ENTRY * 2, RAIO_ATRAS_DO_ENTRY)
        if perto > 0.0:
            trocou_entry = 1.0 if linha["trocou_o_entry"] else 0.0
            segundo_no_contato = 1.0 if (linha["posto_contato"] == 2) else 0.0
            p["trader"] = 0.40 * perto + 0.35 * trocou_entry + 0.25 * segundo_no_contato

        # --- Suporte: existe para o outro converter --------------------------
        # O trade SAIU daqui. Trocar a morte do companheiro virou a assinatura do
        # trader, e manter o peso nos dois punha as duas funcoes disputando o
        # mesmo sinal -- o que faz o resumo por lado depender de arredondamento.
        # O que sobra e o que sempre definiu suporte: a utility que abre a
        # entrada e a arma da qual ele abre mao.
        virou_kill = 1.0 if linha["utility_virou_kill"] else 0.0
        util = _faixa(linha["granadas"], 0.0, 3.0)
        dropou = _faixa(linha["equip_delta"], 0.0, -1500.0)
        p["suporte"] = 0.45 * virou_kill + 0.35 * util + 0.20 * dropou

    return p


def pontua(fatos: pl.DataFrame) -> pl.DataFrame:
    """Aplica a pontuação a todos os (jogador, round)."""
    disp = dispersao_do_inicio(fatos)
    snip = consistencia_de_sniper(fatos)

    mapa_disp = {
        (r["steamid"], r["side"]): r["dispersao_inicio"] for r in disp.iter_rows(named=True)
    }
    mapa_snip = {r["steamid"]: r["share_sniper"] for r in snip.iter_rows(named=True)}

    colunas = {chave: [] for chave in FUNCOES}
    for linha in fatos.iter_rows(named=True):
        notas = pontua_round(
            linha,
            mapa_disp.get((linha["steamid"], linha["side"])),
            mapa_snip.get(linha["steamid"], 0.0),
        )
        for chave, v in notas.items():
            colunas[chave].append(round(v, 3))

    return fatos.with_columns(
        [pl.Series(f"pt_{chave}", v) for chave, v in colunas.items()]
    )


# --- Atribuição -------------------------------------------------------------

def atribui_funcao(pontuado: pl.DataFrame) -> pl.DataFrame:
    """A função do round é a de maior pontuação acima do piso.

    Abaixo do piso o round fica SEM FUNÇÃO DEFINIDA. Isso é resultado, não
    lacuna: nem todo round tem um trabalho reconhecível, e forçar todo mundo
    numa caixinha inventaria função onde não houve.
    """
    chaves = list(FUNCOES)
    notas = [pl.col(f"pt_{c}") for c in chaves]

    melhor = pl.max_horizontal(notas)
    qual = pl.lit(None, dtype=pl.String)
    for c in reversed(chaves):
        qual = pl.when(pl.col(f"pt_{c}") == melhor).then(pl.lit(c)).otherwise(qual)

    # AWPer tem PRECEDÊNCIA, não disputa a maior nota. A arma define o que o
    # round pode ser: o time compra em torno dela e a função dele muda o resto do
    # setup. Sem isto, o AWPer do time saía rotulado de coringa nos rounds de CT
    # em que ele varia a posição -- que é justamente o que um AWPer faz.
    funcao = (
        pl.when(pl.col("pt_awper") >= PISO_PONTUACAO)
        .then(pl.lit("awper"))
        .when(melhor >= PISO_PONTUACAO)
        .then(qual)
        .otherwise(None)
    )
    pontuacao = (
        pl.when(pl.col("pt_awper") >= PISO_PONTUACAO)
        .then(pl.col("pt_awper"))
        .otherwise(melhor)
    )

    return pontuado.with_columns(
        pontuacao.alias("pontuacao"),
        funcao.alias("funcao"),
    )


def resume_por_lado(por_round: pl.DataFrame, match_id: str = "") -> pl.DataFrame:
    """Função dominante de cada jogador em cada lado, com a concentração.

    "Âncora em 9 de 12 rounds de CT" e não "âncora e ponto": quem ancora em 9 e
    rotaciona em 3 não é a mesma coisa que quem ancora em 12, e essa nuance é o
    que a interface precisa mostrar.
    """
    com_funcao = por_round.filter(pl.col("funcao").is_not_null())

    total = por_round.group_by(["steamid", "name", "side"], maintain_order=True).agg(
        pl.len().alias("rounds_no_lado")
    )
    if com_funcao.height == 0:
        return total.with_columns(
            pl.lit(None, dtype=pl.String).alias("funcao"),
            pl.lit(0, dtype=pl.UInt32).alias("rounds_na_funcao"),
            pl.lit(None, dtype=pl.Float64).alias("concentracao"),
            pl.lit(True).alias("amostra_fraca"),
            pl.lit(match_id).alias("match_id"),
        )

    por_funcao = com_funcao.group_by(["steamid", "name", "side", "funcao"], maintain_order=True).agg(
        pl.len().cast(pl.UInt32).alias("rounds_na_funcao"),
        pl.col("pontuacao").mean().alias("pontuacao_media"),
    )

    dominante = (
        por_funcao.sort(["rounds_na_funcao", "pontuacao_media"], descending=[True, True])
        .group_by(["steamid", "side"], maintain_order=True)
        .first()
    )

    return (
        total.join(dominante.drop("name"), on=["steamid", "side"], how="left")
        .with_columns(
            pl.col("rounds_na_funcao").fill_null(0),
            (pl.col("rounds_na_funcao") / pl.col("rounds_no_lado")).alias("concentracao"),
            (pl.col("rounds_no_lado") < MIN_ROUNDS_POR_LADO).alias("amostra_fraca"),
            pl.lit(match_id).alias("match_id"),
        )
        .sort(["name", "side"])
    )


def structural_roles(
    tables: dict[str, pl.DataFrame],
    team_of: dict[int, str],
    map_name: str,
    match_id: str = "",
    tickrate: int | None = None,
) -> tuple[pl.DataFrame, pl.DataFrame]:
    """Funções estruturais de uma partida. Devolve (per_round, summary).

    O tickrate é DETECTADO (metrics/timing.py) e nunca assumido: todo sinal de
    tempo daqui depende dele.
    """
    if tickrate is None:
        tickrate = int(detect_tickrate(tables["rounds"], tables.get("ticks"))["tickrate"])

    fatos = fatos_por_round(tables, team_of, map_name, tickrate)

    # `sobreviveu` vem da tabela de kills: quem não aparece como vítima sobreviveu
    mortos = (
        tables["kills"]
        .select(pl.col("round_num").cast(pl.UInt32), pl.col("victim_steamid").alias("steamid"))
        .filter(pl.col("steamid").is_not_null())
        .unique(maintain_order=True)
        .with_columns(pl.lit(False).alias("sobreviveu"))
    )
    fatos = fatos.join(mortos, on=["round_num", "steamid"], how="left").with_columns(
        pl.col("sobreviveu").fill_null(True)
    )

    por_round = atribui_funcao(pontua(fatos)).with_columns(pl.lit(match_id).alias("match_id"))
    return por_round, resume_por_lado(por_round, match_id)


def acumula(resumos: list[pl.DataFrame]) -> pl.DataFrame:
    """Perfil estrutural do jogador somando todas as partidas processadas.

    Soma os rounds por função e recalcula a dominante — não tira média de
    concentração, que daria o mesmo peso a uma partida de 16 rounds e a uma de 30.
    """
    if not resumos:
        return pl.DataFrame()
    return pl.concat(resumos, how="diagonal")
