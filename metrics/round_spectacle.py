"""
Round mais impressionante da partida.

Por que é um módulo SEPARADO de `win_probability`
-------------------------------------------------
"Que round mais mudou o resultado da partida" e "que round foi mais impressionante
de assistir" não são a mesma pergunta, e somar as duas num score só produz uma
resposta que não serve para nenhuma das duas. Um clutch de 1v3 num placar de
3-13 é lindo e não decidiu nada; um round banal ganho em 11-11 decidiu muito e
não tem clutch nenhum.

Então: `win_probability` responde a primeira, sem peso nenhum, porque ela tem
resposta objetiva. Este módulo responde a segunda -- e aqui pesos relativos são
LEGÍTIMOS, porque a pergunta é subjetiva por natureza. O que não é legítimo é
escondê-los: cada peso é uma constante nomeada aqui em cima, e a saída diz
quais componentes pontuaram em cada round, para dar pra recalibrar olhando o
caso concreto em vez de discutir número no abstrato.

Os dois rounds podem ser diferentes, e quando são, essa própria diferença é
informação boa: "o round mais bonito da partida não mudou nada" é uma frase
honesta e interessante.
"""
from __future__ import annotations

import polars as pl

from metrics.timing import C4_TIMER_SECONDS

# ---------------------------------------------------------------------------
# Pesos dos componentes
#
# Escala arbitrada em 0-100 para o round "perfeito" ser improvável mas possível.
# Todos são discutíveis DE PROPÓSITO -- é a natureza da pergunta. O que a
# saída garante é que dá pra ver qual componente pontuou e recalibrar.
# ---------------------------------------------------------------------------

# Clutch convertido. O peso cresce com o X do 1vX porque 1v4 não é "um pouco
# melhor" que 1v2: a chance de converter despenca a cada inimigo a mais. Base
# mais incremento por inimigo acima de dois (o mínimo que o projeto considera
# clutch, ver metrics/clutch.py).
PESO_CLUTCH_BASE = 26.0
PESO_CLUTCH_POR_INIMIGO_EXTRA = 11.0

# Multikill. Vale por kill A PARTIR da terceira, porque 2 kills num round é
# rotina e não impressiona ninguém.
MIN_KILLS_MULTIKILL = 3
PESO_POR_KILL_ACIMA_DE_DOIS = 8.0

# Round ganho em desvantagem numérica. Igual ao clutch, o peso é por jogador de
# diferença: virar um 2v4 é outra coisa que virar um 4v5.
MIN_DEFICIT_RELEVANTE = 2
PESO_POR_JOGADOR_DE_DEFICIT = 9.0

# Desarme no limite do tempo. "No limite" é definido pelo timer da bomba do
# próprio jogo (40s, de metrics/timing.py): desarmar faltando menos de 5s é
# desarmar com o beep contínuo tocando, e é a imagem clássica do jogo.
SEGUNDOS_DEFUSE_NO_LIMITE = 5.0
PESO_DEFUSE_NO_LIMITE = 20.0

# Abertura que virou o round inteiro: o time que abriu o placar do round venceu
# sem perder mais que um jogador depois disso. Não é sobre a kill em si -- é
# sobre a vantagem ter sido convertida sem sustos, que é o que "a abertura
# decidiu" significa.
MAX_MORTES_APOS_ABERTURA_LIMPA = 1
PESO_ABERTURA_QUE_VIROU_ROUND = 12.0

# Abaixo disto o round não teve nada digno de nota, e o card diz isso em vez de
# eleger o menos sem graça. Uma abertura limpa sozinha (12) fica abaixo do piso:
# é o round comum do CS, não um destaque.
MIN_PONTOS_IMPRESSIONANTE = 20.0


def _ticks_de_defuse(bomb: pl.DataFrame | None) -> dict[int, int]:
    """Tick do desarme em cada round que terminou desarmado."""
    if bomb is None or bomb.height == 0 or "event" not in bomb.columns:
        return {}
    d = (
        bomb.filter(pl.col("event") == "defuse")
        .group_by("round_num")
        .agg(pl.col("tick").min())
    )
    return {int(r["round_num"]): int(r["tick"]) for r in d.iter_rows(named=True)}


def _mortes_do_vencedor_apos_a_abertura(
    kills: pl.DataFrame, rn: int, time_da_abertura: str, team_of: dict[int, str]
) -> int:
    """Quantos jogadores o time que abriu perdeu DEPOIS da primeira kill."""
    rk = kills.filter(pl.col("round_num") == rn).sort("tick")
    if rk.height <= 1:
        return 0
    return sum(
        1
        for k in rk.slice(1).iter_rows(named=True)
        if team_of.get(k["victim_steamid"]) == time_da_abertura
    )


def pontua_round(
    rn: int,
    situacao: dict,
    round_row: dict,
    kills: pl.DataFrame,
    team_of: dict[int, str],
    tick_defuse: int | None,
    tickrate: int,
) -> tuple[float, list[dict]]:
    """Pontuação de espetáculo de um round e os componentes que a formaram.

    Devolve a lista de componentes com nome, pontos e texto -- é ela que vai
    para o card. Componente que não pontuou simplesmente não entra, em vez de
    entrar com zero: card com "multikill: 0" descreve a ausência como se fosse
    presença (mesmo princípio da decisão 18 do CLAUDE.md).
    """
    componentes: list[dict] = []

    # --- clutch convertido ----------------------------------------------
    contra = int(situacao.get("clutch_against") or 0)
    if situacao.get("clutch_player") and contra >= 2:
        pontos = PESO_CLUTCH_BASE + PESO_CLUTCH_POR_INIMIGO_EXTRA * (contra - 2)
        componentes.append({
            "componente": "clutch",
            "pontos": pontos,
            "texto": f"clutch de {situacao['clutch_player']} em 1v{contra}",
        })

    # --- multikill --------------------------------------------------------
    n_kills = int(situacao.get("multikill_count") or 0)
    if n_kills >= MIN_KILLS_MULTIKILL:
        pontos = PESO_POR_KILL_ACIMA_DE_DOIS * (n_kills - 2)
        componentes.append({
            "componente": "multikill",
            "pontos": pontos,
            "texto": f"{n_kills}K de {situacao['multikill_player']}",
        })

    # --- virada em desvantagem numérica -----------------------------------
    deficit = int(situacao.get("worst_deficit_overcome") or 0)
    if deficit >= MIN_DEFICIT_RELEVANTE:
        pontos = PESO_POR_JOGADOR_DE_DEFICIT * deficit
        componentes.append({
            "componente": "desvantagem",
            "pontos": pontos,
            "texto": f"virou com {deficit} jogadores a menos",
        })

    # --- desarme no limite -------------------------------------------------
    plant = round_row.get("bomb_plant")
    if round_row.get("reason") == "bomb_defused" and plant is not None and tick_defuse:
        restante = C4_TIMER_SECONDS - (tick_defuse - int(plant)) / tickrate
        if 0 <= restante <= SEGUNDOS_DEFUSE_NO_LIMITE:
            componentes.append({
                "componente": "defuse_no_limite",
                "pontos": PESO_DEFUSE_NO_LIMITE,
                # vírgula decimal: o resto da interface é em português e
                # "1.6s" no meio de uma frase em pt-BR lê como erro de digitação
                "texto": (
                    "desarme com "
                    + f"{restante:.1f}".replace(".", ",")
                    + "s no relógio da bomba"
                ),
            })

    # --- abertura que virou o round inteiro --------------------------------
    abertura = situacao.get("opening")
    if abertura and abertura.get("team") == situacao.get("winner_team"):
        perdidos = _mortes_do_vencedor_apos_a_abertura(
            kills, rn, abertura["team"], team_of
        )
        if perdidos <= MAX_MORTES_APOS_ABERTURA_LIMPA:
            componentes.append({
                "componente": "abertura_limpa",
                "pontos": PESO_ABERTURA_QUE_VIROU_ROUND,
                "texto": (
                    f"{abertura['player']} abriu o round e o time fechou "
                    + ("sem perder ninguém" if perdidos == 0 else "perdendo só um")
                ),
            })

    return sum(c["pontos"] for c in componentes), componentes


def round_spectacle(
    situacoes: dict[int, dict],
    rounds: pl.DataFrame,
    kills: pl.DataFrame,
    bomb: pl.DataFrame | None,
    team_of: dict[int, str],
    tickrate: int,
) -> tuple[pl.DataFrame, dict]:
    """Contrato do projeto: `(per_round, summary)`.

    `situacoes` é a saída de `scripts.build_insights.round_situations` -- clutch,
    déficit superado, abertura e multikill já reconstruídos round a round. Este
    módulo não recalcula nada disso; ele só decide o que vale quanto.
    """
    defuses = _ticks_de_defuse(bomb)

    linhas = []
    componentes_por_round: dict[int, list[dict]] = {}
    for row in rounds.iter_rows(named=True):
        rn = int(row["round_num"])
        situacao = situacoes.get(rn, {})
        pontos, componentes = pontua_round(
            rn, situacao, row, kills, team_of, defuses.get(rn), tickrate
        )
        componentes_por_round[rn] = componentes
        linhas.append({
            "round": rn,
            "pontos": pontos,
            "n_componentes": len(componentes),
            "componentes": ", ".join(c["componente"] for c in componentes),
        })

    per_round = pl.DataFrame(
        linhas,
        schema={"round": pl.Int64, "pontos": pl.Float64,
                "n_componentes": pl.Int64, "componentes": pl.String},
    )
    if per_round.height == 0:
        return per_round, {"impressionante": None, "minimo_exigido": MIN_PONTOS_IMPRESSIONANTE}

    melhor = per_round.sort(["pontos", "round"], descending=[True, False]).row(0, named=True)
    if melhor["pontos"] < MIN_PONTOS_IMPRESSIONANTE:
        return per_round, {
            "impressionante": None,
            "maior_pontuacao": float(melhor["pontos"]),
            "minimo_exigido": MIN_PONTOS_IMPRESSIONANTE,
        }

    rn = int(melhor["round"])
    return per_round, {
        "impressionante": {
            "round": rn,
            "pontos": float(melhor["pontos"]),
            "componentes": componentes_por_round[rn],
            "winner_team": situacoes.get(rn, {}).get("winner_team"),
        },
        "maior_pontuacao": float(melhor["pontos"]),
        "minimo_exigido": MIN_PONTOS_IMPRESSIONANTE,
    }
