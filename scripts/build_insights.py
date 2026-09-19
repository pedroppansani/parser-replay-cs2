"""
Insights da partida: round decisivo, round mais impressionante, MVP e
"carrega piano".

As duas primeiras perguntas eram UMA só e somavam pontos inventados num score
único. Foram separadas, porque "que round mais mudou o resultado" e "que round
foi mais impressionante de assistir" não são a mesma pergunta:

- **decisivo** sai de `metrics/win_probability.py`, por variação da chance de
  vencer a partida. Não tem peso nenhum -- ponto sem retorno, déficit e placar
  apertado caem da matemática;
- **impressionante** sai de `metrics/round_spectacle.py`, onde pesos relativos
  são legítimos porque a pergunta é subjetiva, e ficam todos expostos no card.

A economia entra como LEITURA ao lado do round decisivo, nunca como peso: um
round perdido em eco era esperado, um round perdido com equipamento superior
custou mais do que o placar mostra.

Gera `data/processed/<match_id>/insights.json`, consumido pelo dashboard.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import polars as pl

from parsing.parser import dano_real_no_mesmo_tick, eventos_do_round_jogado, kills_do_round_jogado
from metrics.archetypes import (
    PAPEIS,
    compute_for_match,
    evidencia,
    load_reference,
    pick_highlight,
)
from metrics.clutch import clutch_situations
from metrics.player_profile import player_profile
from metrics.rating import PESOS_FILE, ModeloDeRound, carrega_referencia
from metrics.rating import rating as calcula_rating
from metrics.positioning import position_samples
from metrics.match_highlights import match_highlights
from metrics.round_spectacle import round_spectacle
# side_of_team é reexportado daqui: build_breakdown e fit_rating importam deste
# módulo. A regra em si (inclusive a prorrogação) vive em metrics/sides.py.
from metrics.sides import REGULATION_HALF as HALFTIME_ROUND, side_of_team  # noqa: F401
from metrics.structural_roles import FUNCOES
from metrics.timing import detect_tickrate
from metrics.win_probability import detecta_formato, win_probability
from scripts.narrative import (
    criterio_do_decisivo,
    historia_destaque,
    historia_mvp,
    historia_papel,
    historia_round_decisivo,
    historia_round_impressionante,
    historia_sem_round_decisivo,
    leitura_economica,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent


# ---------------------------------------------------------------------------
# Times reais (o lado troca no intervalo; o time, não)
# ---------------------------------------------------------------------------

def resolve_teams(ticks: pl.DataFrame) -> tuple[dict[int, str], dict[str, list[str]]]:
    """Mapeia cada jogador ao time real, usando os lados do primeiro round.

    Sem isso, um placar por lado ("ct 13 x t 9") mistura os dois times, porque
    quem era CT no primeiro tempo é T no segundo.
    """
    first = (
        ticks.filter(pl.col("round_num") == 1)
        .sort("tick")
        .group_by("steamid")
        .agg(pl.col("name").first(), pl.col("side").first())
    )
    team_of_player: dict[int, str] = {}
    rosters: dict[str, list[str]] = {"A": [], "B": []}
    for row in first.iter_rows(named=True):
        # Time A = quem começou de T; Time B = quem começou de CT.
        team = "A" if row["side"] == "t" else "B"
        team_of_player[row["steamid"]] = team
        rosters[team].append(row["name"])
    return team_of_player, rosters


def score_progression(rounds: pl.DataFrame) -> list[dict]:
    """Placar acumulado por TIME round a round."""
    a = b = 0
    out = []
    for row in rounds.iter_rows(named=True):
        rn = row["round_num"]
        winner_team = "A" if row["winner"] == side_of_team("A", rn) else "B"
        if winner_team == "A":
            a += 1
        else:
            b += 1
        out.append(
            {
                "round": int(rn),
                "winner_team": winner_team,
                "reason": row["reason"],
                "score_a": a,
                "score_b": b,
                "bomb_planted": row["bomb_plant"] is not None,
            }
        )
    return out


# ---------------------------------------------------------------------------
# Round decisivo
# ---------------------------------------------------------------------------

def round_situations(kills: pl.DataFrame, rounds: pl.DataFrame, team_of: dict[int, str]) -> dict[int, dict]:
    """Reconstrói, round a round, como a vantagem numérica evoluiu.

    Serve pra três coisas: achar clutch (último vivo que ganha), achar virada
    em desvantagem numérica, e achar quem abriu o round.
    """
    out: dict[int, dict] = {}

    for row in rounds.iter_rows(named=True):
        rn = int(row["round_num"])
        alive = {"A": 5, "B": 5}
        rk = kills.filter(pl.col("round_num") == rn).sort("tick")

        winner_team = "A" if row["winner"] == side_of_team("A", rn) else "B"
        loser_team = "B" if winner_team == "A" else "A"

        worst_deficit = 0  # maior desvantagem numérica que o vencedor superou
        clutch_player = None
        clutch_against = 0
        opening = None

        for kill in rk.iter_rows(named=True):
            victim_team = team_of.get(kill["victim_steamid"])
            attacker_team = team_of.get(kill["attacker_steamid"])
            # A abertura é o primeiro duelo ganho contra o ADVERSÁRIO. Morte por
            # fogo amigo, bomba ou queda antes dela tira alguém do round mas
            # não é abertura de ninguém -- nem abertura perdida para o outro time.
            if (opening is None and attacker_team is not None
                    and victim_team is not None and attacker_team != victim_team):
                opening = {
                    "player": kill["attacker_name"],
                    "team": attacker_team,
                    "victim": kill["victim_name"],
                    "weapon": kill["weapon"],
                }
            if victim_team is None:
                continue
            alive[victim_team] -= 1

            deficit = alive[loser_team] - alive[winner_team]
            worst_deficit = max(worst_deficit, deficit)

            # clutch: vencedor ficou com 1 vivo contra 2+ e ainda ganhou
            if alive[winner_team] == 1 and alive[loser_team] >= 2 and clutch_player is None:
                survivors = set(team_of) - set(
                    rk.filter(pl.col("tick") <= kill["tick"])["victim_steamid"].to_list()
                )
                team_survivors = [s for s in survivors if team_of.get(s) == winner_team]
                if len(team_survivors) == 1:
                    sid = team_survivors[0]
                    name_row = kills.filter(pl.col("attacker_steamid") == sid)
                    clutch_player = (
                        name_row["attacker_name"][0] if name_row.height else str(sid)
                    )
                    clutch_against = alive[loser_team]

        # multikill: quem mais matou no round, quando passa de 2 kills
        by_killer: dict[str, int] = {}
        for kill in rk.iter_rows(named=True):
            if team_of.get(kill["attacker_steamid"]) and kill["attacker_name"]:
                if team_of.get(kill["attacker_steamid"]) != team_of.get(kill["victim_steamid"]):
                    by_killer[kill["attacker_name"]] = by_killer.get(kill["attacker_name"], 0) + 1
        top_killer, top_kills = (None, 0)
        if by_killer:
            top_killer, top_kills = max(by_killer.items(), key=lambda kv: kv[1])

        out[rn] = {
            "winner_team": winner_team,
            "worst_deficit_overcome": int(worst_deficit),
            "clutch_player": clutch_player,
            "clutch_against": int(clutch_against),
            "opening": opening,
            "multikill_player": top_killer if top_kills >= 3 else None,
            "multikill_count": int(top_kills) if top_kills >= 3 else 0,
        }
    return out


def contexto_economico(
    ticks: pl.DataFrame, rn: int, vencedor: str, tickrate: int
) -> dict:
    """Equipamento médio dos dois times no round, para LER o resultado.

    Deliberadamente fora do score de decisividade: se o dinheiro entrasse na
    conta que elege o round, a decisividade passaria a depender de quanto os
    times tinham, e isso é outra pergunta. Aqui ele só explica o que o placar
    não explica -- perder com equipamento superior custa mais que perder em eco.

    Amostra nos dois primeiros segundos de jogo, a mesma janela que
    `metrics/round_breakdown.py` usa: depois disso o valor já reflete arma
    trocada e compra do chão.
    """
    perdedor = "B" if vencedor == "A" else "A"
    inicio = ticks.filter(pl.col("round_num") == rn)["tick"].min()
    if inicio is None:
        return {"equip_vencedor": None, "equip_perdedor": None,
                "perdedor_estava_melhor": False}

    def medio(time: str) -> float | None:
        lado = side_of_team(time, rn)
        recorte = ticks.filter(
            (pl.col("round_num") == rn)
            & (pl.col("tick") <= inicio + 2 * tickrate)
            & (pl.col("side") == lado)
        )
        if recorte.height == 0:
            return None
        por_jogador = recorte.group_by("steamid").agg(
            pl.col("current_equip_value").max().alias("v")
        )
        return float(por_jogador["v"].mean() or 0)

    ev, ep = medio(vencedor), medio(perdedor)
    return {
        "equip_vencedor": ev,
        "equip_perdedor": ep,
        # "igual ou superior": empatar em equipamento e perder também não tem
        # desculpa de economia.
        "perdedor_estava_melhor": ev is not None and ep is not None and ep >= ev,
    }


# ---------------------------------------------------------------------------
# MVP e "carrega piano"
# ---------------------------------------------------------------------------

def _norm(df: pl.DataFrame, col: str, invert: bool = False) -> pl.Expr:
    """Normaliza uma coluna pro intervalo 0-1 dentro da partida."""
    lo, hi = df[col].min(), df[col].max()
    if lo is None or hi is None or hi == lo:
        return pl.lit(0.5)
    expr = (pl.col(col) - lo) / (hi - lo)
    return (1 - expr) if invert else expr


def build_player_indices(
    basic: dict[str, pl.DataFrame],
    crosshair: pl.DataFrame,
    position: pl.DataFrame,
    features: pl.DataFrame,
    situations: dict[int, dict],
    team_of: dict[int, str],
) -> pl.DataFrame:
    """Monta a tabela por jogador com os dois índices.

    MVP — impacto que decide rounds:
        ADR, KAST, kills de abertura e clutches. Pesos declarados abaixo.

    Os papéis nomeados (carrega piano, carry, camper, repick, AWPer...) NÃO
    estão aqui: vivem em metrics/archetypes.py, com escala ajustada no conjunto
    das partidas. Esta função ficou só com o índice de MVP, que alimenta o anel
    do card.
    """
    adr = basic["adr_summary"].select(["steamid", "name", "adr"])
    kast = basic["kast_summary"].select(["steamid", "kast_pct"])
    util = basic["utility_damage_summary"].select(["steamid", "total_utility_damage", "utility_damage_per_round"])
    trades = basic["trade_kills_summary"].select(["steamid", "total_kills", "total_trade_kills"])

    openings: dict[str, int] = {}
    clutches: dict[str, int] = {}
    for sit in situations.values():
        op = sit.get("opening")
        if op:
            openings[op["player"]] = openings.get(op["player"], 0) + 1
        if sit.get("clutch_player"):
            clutches[sit["clutch_player"]] = clutches.get(sit["clutch_player"], 0) + 1

    per_player_round = features.group_by(["steamid"]).agg(
        pl.col("time_of_first_contact_s").median().alias("median_first_contact_s"),
        pl.col("survived").mean().alias("survival_rate"),
    )

    ch = crosshair.select(["steamid", "crosshair_score", "frac_entering_fight"])
    pos = (
        position.group_by("steamid")
        .agg(pl.col("avg_distance_from_team").mean().alias("avg_distance_from_team"))
    )

    df = (
        adr.join(kast, on="steamid", how="left")
        .join(util, on="steamid", how="left")
        .join(trades, on="steamid", how="left")
        .join(per_player_round, on="steamid", how="left")
        .join(ch, on="steamid", how="left")
        .join(pos, on="steamid", how="left")
        .with_columns(
            pl.col("name").map_elements(lambda n: openings.get(n, 0), return_dtype=pl.Int32).alias("opening_kills"),
            pl.col("name").map_elements(lambda n: clutches.get(n, 0), return_dtype=pl.Int32).alias("clutches"),
            pl.col("steamid").map_elements(lambda s: team_of.get(s, "?"), return_dtype=pl.String).alias("team"),
        )
    )

    # --- MVP: 40% ADR, 30% KAST, 20% aberturas, 10% clutches ---
    df = df.with_columns(
        (
            0.40 * _norm(df, "adr")
            + 0.30 * _norm(df, "kast_pct")
            + 0.20 * _norm(df, "opening_kills")
            + 0.10 * _norm(df, "clutches")
        ).alias("mvp_index")
    )

    # O índice de "carrega piano" que existia aqui era `esforço − recompensa`, e
    # estava errado por construção: quem tem recompensa baixa vence a subtração,
    # e recompensa baixa é, quase sempre, jogar mal. A fórmula elegia o pior
    # jogador e colava nele um rótulo que significa outra coisa. O papel agora
    # vive em metrics/archetypes.py, onde é um PRODUTO de esforço por benefício
    # ao time, e tem três formas (entrada de T, solo hold de CT, sacrifício de
    # economia) em vez de uma fórmula de entry.
    return df.sort("mvp_index", descending=True)


# ---------------------------------------------------------------------------

# Fração dos rounds da partida abaixo da qual o rating do jogador aparece como
# amostra fraca na página. 3/4: quem entrou no lugar de alguém no meio do segundo
# tempo tem um número que não compara com o dos outros dez.
FRACAO_MINIMA_DE_ROUNDS = 0.75


def _rating_da_partida(tabelas, interim, rounds, team_of, vencedor_por_round, kast, tickrate):
    """(informação do rating para a página, {steamid: rating do jogador})."""
    referencia = carrega_referencia()
    modelo = ModeloDeRound.da_referencia((referencia or {}).get("modelo_de_round"))
    blind = interim / "player_blind.parquet"
    entrada = {
        **tabelas,
        "player_blind": (eventos_do_round_jogado(pl.read_parquet(blind), rounds)
                         if blind.exists() else None),
        "compra": (pl.read_parquet(interim / "compra.parquet")
                   if (interim / "compra.parquet").exists() else None),
    }
    _, resumo = calcula_rating(entrada, team_of, vencedor_por_round, kast, tickrate,
                               referencia=referencia, modelo=modelo)
    por_jogador = {
        j["steamid"]: {
            "rating": round(float(j["rating"]), 2),
            # Numa partida todos jogam o mesmo número de rounds, e o piso do
            # rating (MIN_ROUNDS_CONFIAVEL, pensado para o agregado) apagaria o
            # número de todo mundo. Aqui a marca é para quem jogou bem MENOS
            # que a partida: substituição, queda de conexão.
            "rating_amostra_fraca": bool(j["rounds"] < FRACAO_MINIMA_DE_ROUNDS * rounds.height),
            # os seis sub-ratings já na escala do rating (1,00 = média), para o
            # perfil mostrar de onde o número veio
            "rating_sub": {n: round(float(j[f"norm_{n}"]), 2) for n in resumo["pesos"]},
        }
        for j in resumo["jogadores"]
    }
    validacao = {}
    if PESOS_FILE.exists():
        v = json.loads(PESOS_FILE.read_text(encoding="utf-8")).get("validacao", {})
        fora = v.get("fora_da_amostra", {})
        validacao = {"partidas": v.get("partidas"), "erro_medio": fora.get("erro_medio_absoluto"),
                     "correlacao": fora.get("correlacao")}
    info = {
        "rotulo": resumo["rotulo"],
        "texto": (
            "Implementação própria da metodologia publicada do Rating 3.0 da HLTV — não é o "
            "número oficial. Pesos "
            + ("ajustados contra os ratings oficiais de " + str(validacao["partidas"]) + " partidas "
               "(erro médio de " + f"{validacao['erro_medio']:.2f}".replace(".", ",") + " fora da amostra)"
               if validacao.get("partidas") else "provisórios")
            + "."
        ),
        "origem_dos_pesos": resumo["origem_dos_pesos"],
        "pesos_desatualizados": resumo["pesos_desatualizados"],
        "validacao": validacao,
    }
    return info, por_jogador


def build(match_id: str) -> Path:
    processed = PROJECT_ROOT / "data" / "processed" / match_id
    interim = PROJECT_ROOT / "data" / "interim" / match_id

    rounds = pl.read_parquet(processed / "rounds.parquet")
    kills = pl.read_parquet(interim / "kills.parquet")
    # mortes do tempo parado não pertencem a round nenhum (ver parsing.parser)
    kills = kills_do_round_jogado(kills, rounds)
    ticks = pl.read_parquet(interim / "ticks.parquet")

    basic = {
        n: pl.read_parquet(processed / f"{n}.parquet")
        for n in [
            "adr_summary",
            "kast_summary",
            "utility_damage_summary",
            "trade_kills_summary",
            "adr_per_round",
            "kast_per_round",
        ]
    }
    crosshair = pl.read_parquet(processed / "crosshair_summary.parquet")
    ch_round = pl.read_parquet(processed / "crosshair_per_round.parquet")
    crosshair = crosshair.join(
        ch_round.group_by("steamid").agg(pl.col("frac_entering_fight").mean()),
        on="steamid",
        how="left",
    )
    position = pl.read_parquet(processed / "position_profile.parquet")
    features = pl.read_parquet(processed / "cluster_features.parquet")

    team_of, rosters = resolve_teams(ticks)
    progression = score_progression(rounds)
    situations = round_situations(kills, rounds, team_of)
    players = build_player_indices(basic, crosshair, position, features, situations, team_of)

    # --- Round decisivo: variação da probabilidade de vitória --------------
    # O formato sai da própria demo (a troca de lado), e não de um MR12 assumido.
    tickrate = detect_tickrate(rounds, ticks)["tickrate"]
    formato = detecta_formato(rounds, ticks)
    if formato.intervalo != HALFTIME_ROUND:
        # O resto do projeto ainda tem HALFTIME_ROUND fixo em 12 espalhado em
        # sete módulos. Enquanto isso não for unificado, discordância entre o
        # formato detectado e a constante é avisada em vez de ignorada -- o
        # placar por TIME depende dela e sairia trocado em silêncio.
        print(
            f"  aviso: formato detectado {formato.nome} (intervalo no round "
            f"{formato.intervalo}), mas HALFTIME_ROUND vale {HALFTIME_ROUND}"
        )
    curva, wp_resumo = win_probability(progression, formato)

    # --- Round mais impressionante: pergunta separada, card separado -------
    _, espetaculo = round_spectacle(
        situations, rounds, kills, pl.read_parquet(interim / "bomb.parquet")
        if (interim / "bomb.parquet").exists() else None,
        team_of, tickrate,
    )

    # --- Papeis nomeados (metrics/archetypes.py) ---
    tabelas = {
        "ticks": ticks,
        "kills": kills,
        "rounds": rounds,
        "damages": eventos_do_round_jogado(dano_real_no_mesmo_tick(pl.read_parquet(interim / "damages.parquet")), rounds),
    }
    saidas = {
        "cluster_features": features,
        "grenades_per_round": pl.read_parquet(processed / "grenades_per_round.parquet"),
        "awp_summary": pl.read_parquet(processed / "awp_summary.parquet"),
    }
    areas_path = processed / "player_round_areas.parquet"
    areas = pl.read_parquet(areas_path) if areas_path.exists() else pl.DataFrame()
    positions = position_samples(ticks, rounds)
    vencedor_por_round = {
        int(r["round_num"]): ("A" if r["winner"] == side_of_team("A", int(r["round_num"])) else "B")
        for r in rounds.iter_rows(named=True)
    }

    # --- Rating (metrics/rating.py) ---
    # Implementação própria da metodologia publicada do Rating 3.0, com os pesos
    # ajustados contra os ratings oficiais (metrics/rating_weights.json) e o
    # modelo de round GLOBAL reconstruído da referência -- nunca um modelo
    # treinado só nesta partida (decisão 11).
    rating_info, rating_por_jogador = _rating_da_partida(
        tabelas, interim, rounds, team_of, vencedor_por_round, basic["kast_summary"], tickrate)

    # --- Perfil por jogador (metrics/player_profile.py) ---
    # Este é o outro eixo do mesmo dado: o agrupamento diz que TIPOS de round
    # existem, o perfil diz com que frequência cada jogador faz cada coisa. As
    # médias de um grupo não pertencem a jogador nenhum -- os rounds de um mesmo
    # jogador se espalham por todos os grupos.
    clutch_round, _ = clutch_situations(kills, rounds, team_of, vencedor_por_round)
    perfil, perfil_rounds = player_profile(
        features,
        positions,
        ticks,
        kills,
        rounds,
        areas,
        clutch_round,
        cluster_assignments=pl.read_parquet(processed / "cluster_assignments.parquet"),
        match_id=match_id,
    )
    perfil.write_parquet(processed / "player_profile.parquet")
    perfil_rounds.write_parquet(processed / "player_profile_rounds.parquet")

    # --- Os dois cards de jogador da aba de leitura -----------------------
    # A seção tem estrutura fixa: round decisivo em cima, MVP à esquerda e o
    # outro destaque à direita. Ver metrics/match_highlights.py.
    funcao_por_steamid = {}
    caminho_funcoes = processed / "structural_roles_summary.parquet"
    estruturais = pl.read_parquet(caminho_funcoes) if caminho_funcoes.exists() else None
    if estruturais is not None:
        # a função exibida no card do MVP é a do lado em que ele jogou mais
        melhor = estruturais.filter(pl.col("funcao").is_not_null()).sort(
            "rounds_na_funcao", descending=True
        )
        for linha in melhor.iter_rows(named=True):
            funcao_por_steamid.setdefault(
                int(linha["steamid"]), FUNCOES[linha["funcao"]][0]
            )

    referencia = load_reference()
    papeis_round, papeis = compute_for_match(
        tabelas, saidas, positions, areas, team_of, vencedor_por_round, reference=referencia
    )
    # Convenção do projeto: o round a round é persistido junto do agregado, porque
    # é nele que a validação manual acontece. Um índice de papel plausível pode
    # esconder lógica errada em rounds específicos.
    papeis_round.write_parquet(processed / "archetypes_per_round.parquet")
    papeis.write_parquet(processed / "archetypes_summary.parquet")

    # Card da esquerda: quem levou o time nas costas. Card da direita: quem
    # exemplificou COM MAIS FORCA algum dos outros papeis -- nao um slot fixo.
    time_vencedor = "A" if progression[-1]["score_a"] > progression[-1]["score_b"] else "B"
    candidatos_destaque, cards = match_highlights(
        players, papeis, estruturais, funcao_por_steamid, time_vencedor
    )
    mvp_card = cards["mvp"]
    destaque_card = cards["destaque"]

    # O sistema antigo de cards (carry + pick_highlight) continua alimentando o
    # payload porque outras telas leem essas chaves; o que mudou é QUEM aparece
    # nos dois cards da aba de leitura.
    carry = papeis.sort("idx_carry", descending=True).row(0, named=True)
    destaque = pick_highlight(papeis, excluir_steamid=carry["steamid"])

    meta = json.loads((processed / "match_meta.json").read_text(encoding="utf-8"))
    final = progression[-1]

    # O tooltip do gráfico de placar lê daqui: progressão + o que aconteceu no
    # round. Antes esta lista carregava junto o `importance` do esquema de
    # pontos; ele saiu, e nada no site dependia dele além do próprio card.
    rounds_scored = [{**p, **situations.get(p["round"], {})} for p in progression]

    # O round decisivo é a linha da curva enriquecida com o que aconteceu nele.
    # Pode ser None, e isso é RESULTADO: numa partida de placar largo nenhum
    # round decidiu nada, e o card diz exatamente isso.
    dec = wp_resumo["decisivo"]
    decisive_round = None
    economia = None
    if dec is not None:
        rn = int(dec["round"])
        por_round = {p["round"]: p for p in progression}
        decisive_round = {**por_round.get(rn, {}), **situations.get(rn, {}), **dec}
        economia = contexto_economico(ticks, rn, dec["winner_team"], tickrate)

    payload = {
        "match": {
            # Identidade da PARTIDA, e nao do mapa. As anotacoes desenhadas sao
            # guardadas por partida; sem isto, duas partidas na mesma Mirage
            # dividiriam a mesma chave e o rabisco de uma apareceria na outra.
            "match_id": match_id,
            "map": meta.get("map_name"),
            "rounds": len(progression),
            "score_a": final["score_a"],
            "score_b": final["score_b"],
            "rosters": rosters,
            "halftime": HALFTIME_ROUND,
            "formato": formato.nome,
        },
        "progression": progression,
        "decisive_round": decisive_round,
        # A curva inteira: é ela que o gráfico de probabilidade de vitória desenha.
        "win_probability": {
            "curve": curva.to_dicts(),
            "top": wp_resumo["top"],
            "empate_no_topo": wp_resumo["empate_no_topo"],
            "maior_wpa": wp_resumo["maior_wpa"],
            "minimo_exigido": wp_resumo["minimo_exigido"],
        },
        "spectacle_round": espetaculo["impressionante"],
        "mvp_card": mvp_card,
        "highlight_card": destaque_card,
        # a tabela de candidatos vai junto para dar pra auditar por que um
        # destaque venceu o outro -- mesma razão de o decisivo expor os 3 maiores
        "highlight_candidates": candidatos_destaque.head(8).to_dicts(),
        "economy_decisive": economia,
        "rounds_scored": rounds_scored,
        "players": [{**p, **rating_por_jogador.get(p["steamid"], {})} for p in players.to_dicts()],
        "rating_info": rating_info,
        "archetypes": papeis.to_dicts(),
        "player_profile": perfil.to_dicts(),
        "reference_fitted": referencia is not None,
        "carry": {
            "steamid": carry["steamid"],
            "name": carry["name"],
            "team": carry["team"],
            "index": carry["idx_carry"],
            "evidence": evidencia("carry", carry),
        },
        "highlight": destaque,
        # As frases dos cards saem daqui prontas. O template so imprime -- ver o
        # cabecalho de scripts/narrative.py sobre por que elas nao sao montadas
        # em JavaScript.
        "narrative": {
            "decisive": (
                historia_round_decisivo(decisive_round, dec)
                if dec is not None
                else historia_sem_round_decisivo(
                    wp_resumo, (final["score_a"], final["score_b"])
                )
            ),
            "criterion": criterio_do_decisivo(wp_resumo),
            "mvp_card": historia_mvp(mvp_card),
            "highlight_card": historia_destaque(destaque_card),
            "spectacle": historia_round_impressionante(
                espetaculo, dec["round"] if dec else None
            ),
            "economy": (
                leitura_economica(
                    economia["equip_vencedor"], economia["equip_perdedor"],
                    economia["perdedor_estava_melhor"],
                )
                if economia
                else None
            ),
            "carry": historia_papel(
                PAPEIS["carry"][0], carry["name"],
                evidencia("carry", carry), PAPEIS["carry"][1],
            ),
            "highlight": (
                historia_papel(
                    destaque["label"], destaque["name"],
                    destaque["evidence"], destaque["meaning"],
                )
                if destaque
                else None
            ),
        },
    }

    out = processed / "insights.json"
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description="Gera os insights da partida (round decisivo, MVP, carrega piano).")
    parser.add_argument("match_id", type=str)
    args = parser.parse_args()
    print(f"Insights salvos em: {build(args.match_id)}")


if __name__ == "__main__":
    main()
