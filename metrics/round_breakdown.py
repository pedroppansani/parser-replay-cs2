"""
Autópsia do round: o que custou o round para quem perdeu.

O que este módulo faz e o que ele NÃO faz — a distinção importa mais aqui do que
em qualquer outra métrica do projeto:

FAZ: identifica momentos OBSERVÁVEIS que a literatura competitiva associa a
perder rounds, e os coloca em ordem cronológica com a evidência de cada um:
morrer na abertura sem ser trocado, morrer isolado longe do time, o instante em
que a desvantagem numérica virou irreversível, perder sem gastar utility,
perder o pós-plant.

NÃO FAZ: dizer que a rotação foi errada, que o call foi ruim ou que o jogador
devia estar em outro lugar. Isso exige saber o que o time combinou e o que o
adversário mostrou — informação que não está no demo. O que sai daqui é
"aconteceu isto, nesta ordem, e isto costuma custar round"; o julgamento de
*por que* aconteceu é de quem entende do jogo.

Por isso cada momento vem com tick e posição: dá pra clicar e assistir no
replay em vez de confiar no rótulo.

ORIGEM DO TEMPO — declarada aqui porque a interface mostra segundos e um número
sem referência não se audita: **t = 0 é o FIM DO FREEZE TIME** (`freeze_end`),
que é quando o round começa a ser jogado. Não é o `start` do round (que inclui o
tempo parado) nem o `official_end` do anterior.

Consequência: tempo negativo é IMPOSSÍVEL por construção. Se aparecer, é evento
que não pertence ao round, e o módulo levanta erro em vez de renderizar o
número estranho. Um evento pode legitimamente cair DEPOIS do fim do round (ainda
dá pra morrer nos segundos seguintes) — esse sai marcado como pós-round, com
tempo positivo contado do mesmo zero.
"""
from __future__ import annotations

import numpy as np
import polars as pl

from metrics.formatting import format_money

# Janela para considerar uma morte "trocada" — mesma do resto do projeto.
TRADE_WINDOW_SECONDS = 5.0

# Distância (unidades) até o companheiro vivo mais próximo no instante da morte.
# Acima disso, ninguém tinha como trocar: a morte foi isolada. ~600u é cerca de
# 3 segundos de corrida, o tempo típico de uma troca acontecer.
ISOLATION_DISTANCE = 600.0

# Abaixo deste valor de equipamento médio, o round é de economia: perder não
# indica erro de execução, e a autópsia diz isso em vez de apontar culpados.
#
# 2000$ é o ponto em que o time não tem rifle para todo mundo: um AK custa 2700 e
# um M4 3100, então uma média abaixo de 2000 significa que parte do time entrou
# de pistola ou SMG. Acima disso a derrota já é comparável à do adversário.
ECO_EQUIP_VALUE = 2000

# Diferença de equipamento a partir da qual vale dizer que um lado entrou muito
# pior que o outro. 1500$ é a distância entre uma pistola com colete e um rifle:
# abaixo disso os dois times brigam com armas comparáveis.
DIFERENCA_EQUIP_RELEVANTE = 1500

# Round em que os lados trocam (MR12). O último round de cada metade tem a mesma
# pegadinha de fronteira do último da partida e por isso é marcado.
HALFTIME_ROUND = 12

# Quanto tempo depois do fim do round um evento ainda conta como do round. O
# replay já estende a janela pela mesma razão (TAIL_TICKS em export_replay).
CAUDA_POS_ROUND_S = 8.0


def distance_phrase(dist: float) -> str:
    """Traduz a distância até o companheiro mais próximo para linguagem de jogo.

    O número cru em unidades do Source não diz nada para quem lê ("morreu a
    1000u" não é uma frase que alguém fala sobre CS). As faixas abaixo saem da
    própria escala do jogo: ~600u é o alcance em que uma troca ainda acontece,
    e acima de ~1500u o jogador está efetivamente em outra parte do mapa.
    O valor exato continua no dado, para auditoria.
    """
    if dist < 900:
        return "longe do companheiro mais próximo"
    if dist < 1500:
        return "muito longe do time"
    return "isolado, sem ninguém por perto"


def _alive_timeline(kills: pl.DataFrame, team_of: dict[int, str]) -> list[dict]:
    """Sequência de mortes do round com a contagem de vivos depois de cada uma."""
    alive = {"A": 5, "B": 5}
    out = []
    for k in kills.sort("tick").iter_rows(named=True):
        vt = team_of.get(k["victim_steamid"])
        if vt is None:
            continue
        alive[vt] -= 1
        out.append({**k, "alive_A": alive["A"], "alive_B": alive["B"]})
    return out


def _nearest_teammate_distance(
    ticks: pl.DataFrame, round_num: int, tick: int, steamid: int, team_of: dict[int, str]
) -> float | None:
    """Distância até o companheiro vivo mais próximo no instante da morte."""
    snap = ticks.filter((pl.col("round_num") == round_num) & (pl.col("tick") == tick))
    if snap.height == 0:
        near = ticks.filter(
            (pl.col("round_num") == round_num)
            & (pl.col("tick") >= tick - 8)
            & (pl.col("tick") <= tick + 8)
        )
        if near.height == 0:
            return None
        snap = near.filter(pl.col("tick") == near["tick"][0])

    me = snap.filter(pl.col("steamid") == steamid)
    if me.height == 0:
        return None
    my_team = team_of.get(steamid)
    mates = snap.filter(
        (pl.col("steamid") != steamid)
        & pl.col("is_alive")
        & pl.col("steamid").map_elements(lambda s: team_of.get(s) == my_team, return_dtype=pl.Boolean)
    )
    if mates.height == 0:
        return None

    dx = mates["X"].to_numpy() - me["X"][0]
    dy = mates["Y"].to_numpy() - me["Y"][0]
    return float(np.min(np.sqrt(dx**2 + dy**2)))


def _segundos(tick: int, t0: int, tickrate: int, contexto: str) -> float:
    """Segundos desde o fim do freeze time. Negativo é erro, não caso a tratar."""
    delta = int(tick) - t0
    if delta < 0:
        raise ValueError(
            f"{contexto}: evento no tick {tick} é anterior ao fim do freeze time "
            f"({t0}), {delta / tickrate:.1f}s antes do round começar a ser jogado. "
            "Isso não é arredondamento — o evento não pertence a este round. Rode "
            "`py -3.12 -m scripts.debug_timeline` e veja parsing.kills_do_round_jogado."
        )
    return round(delta / tickrate, 1)


def _quem_matou(kill: dict) -> tuple[str | None, str]:
    """Nome de quem matou e a frase da causa.

    Morte sem atacante (queda, bomba, dano de zona) vem com `attacker_steamid`
    nulo, e o demo às vezes preenche o atacante com a PRÓPRIA VÍTIMA. Nos dois
    casos o nome não pode aparecer como matador: "morreu para si mesmo" descreve
    um bug, não um round. Sem atacante, o texto diz o que de fato aconteceu.
    """
    atacante = kill.get("attacker_steamid")
    vitima = kill.get("victim_steamid")
    arma = (kill.get("weapon") or "").lower()

    if atacante is None or atacante == vitima:
        if arma in ("planted_c4", "c4"):
            return None, "morreu para a bomba"
        if arma in ("world", ""):
            return None, "morreu para o mapa — queda ou dano de zona"
        return None, "morreu sem atacante registrado"
    return kill.get("attacker_name"), "morreu para " + str(kill.get("attacker_name"))


def analyze_round(
    round_row: dict,
    kills: pl.DataFrame,
    ticks: pl.DataFrame,
    grenades: pl.DataFrame | None,
    team_of: dict[int, str],
    side_of_team,
    tickrate: int = 64,
    ultimo_round: int | None = None,
) -> dict:
    """Monta a autópsia de um round para o time que perdeu."""
    rn = int(round_row["round_num"])
    t0 = int(round_row["freeze_end"])
    TICKRATE = tickrate  # nome curto, usado nas contas abaixo
    winner = "A" if round_row["winner"] == side_of_team("A", rn) else "B"
    loser = "B" if winner == "A" else "A"

    rk = kills.filter(pl.col("round_num") == rn)
    timeline = _alive_timeline(rk, team_of)
    window = TRADE_WINDOW_SECONDS * TICKRATE

    # steamid -> nick, para poder nomear quem sobrou vivo (e não só quem morreu)
    roster = ticks.filter(pl.col("round_num") == rn).group_by("steamid").agg(pl.col("name").first())
    names = {int(r["steamid"]): r["name"] for r in roster.iter_rows(named=True)}

    moments = []
    tags = []

    # --- contexto econômico: round de eco não é erro de execução ---
    loser_side = side_of_team(loser, rn)
    winner_side = "ct" if loser_side == "t" else "t"

    def equip_medio(lado: str) -> float | None:
        recorte = ticks.filter(
            (pl.col("round_num") == rn)
            & (pl.col("tick") <= t0 + 2 * TICKRATE)
            & (pl.col("side") == lado)
        )
        if recorte.height == 0:
            return None
        por_jogador = recorte.group_by("steamid").agg(
            pl.col("current_equip_value").max().alias("v")
        )
        return float(por_jogador["v"].mean() or 0)

    # Os DOIS lados, porque "960$" sozinho não diz nada: 960 contra 1.200 é um
    # round parelho de pistola; 960 contra 4.500 é outra história, e antes disso
    # o texto tratava os dois igual.
    equip = equip_medio(loser_side)
    equip_winner = equip_medio(winner_side)
    is_eco = equip is not None and equip < ECO_EQUIP_VALUE
    diferenca = (
        None if equip is None or equip_winner is None else round(equip_winner - equip)
    )
    if is_eco:
        tags.append("round de economia")

    # --- morte de abertura ---
    if timeline:
        first = timeline[0]
        victim_team = team_of.get(first["victim_steamid"])
        traded = any(
            t["tick"] > first["tick"]
            and t["tick"] - first["tick"] <= window
            and t["victim_steamid"] == first["attacker_steamid"]
            for t in timeline
        )
        if victim_team == loser:
            moments.append(
                {
                    "tick": int(first["tick"]),
                    "t": _segundos(first["tick"], t0, TICKRATE, f"round {rn}, abertura"),
                    "kind": "abertura_perdida",
                    "who": first["victim_name"],
                    "by": _quem_matou(first)[0],
                    "causa": _quem_matou(first)[1],
                    "traded": bool(traded),
                    "x": int(round(first["victim_X"])) if first["victim_X"] is not None else None,
                    "y": int(round(first["victim_Y"])) if first["victim_Y"] is not None else None,
                    "text": "perdeu a abertura" + ("" if traded else " e ninguém trocou"),
                }
            )
            tags.append("abertura perdida" + ("" if traded else " sem troca"))

    # --- mortes sem troca e mortes isoladas ---
    untraded = 0
    for k in timeline:
        if team_of.get(k["victim_steamid"]) != loser:
            continue
        traded = any(
            t["tick"] > k["tick"]
            and t["tick"] - k["tick"] <= window
            and t["victim_steamid"] == k["attacker_steamid"]
            for t in timeline
        )
        dist = _nearest_teammate_distance(ticks, rn, int(k["tick"]), int(k["victim_steamid"]), team_of)
        isolated = dist is not None and dist > ISOLATION_DISTANCE

        if not traded:
            untraded += 1
        if not traded and isolated:
            moments.append(
                {
                    "tick": int(k["tick"]),
                    "t": _segundos(k["tick"], t0, TICKRATE, f"round {rn}, morte isolada"),
                    "kind": "morte_isolada",
                    "who": k["victim_name"],
                    "by": _quem_matou(k)[0],
                    "causa": _quem_matou(k)[1],
                    "distance": round(dist),
                    "x": int(round(k["victim_X"])) if k["victim_X"] is not None else None,
                    "y": int(round(k["victim_Y"])) if k["victim_Y"] is not None else None,
                    "text": "morreu " + distance_phrase(dist) + " — sem troca possível",
                }
            )

    if untraded >= 2:
        tags.append(str(untraded) + " mortes sem troca")

    # --- instante em que a desvantagem virou irreversível ---
    for i, k in enumerate(timeline):
        deficit_from_here = all(
            (t["alive_A"] < t["alive_B"] if loser == "A" else t["alive_B"] < t["alive_A"])
            for t in timeline[i:]
        )
        loser_alive = k["alive_A"] if loser == "A" else k["alive_B"]
        winner_alive = k["alive_B"] if loser == "A" else k["alive_A"]
        # loser_alive >= 1: a última morte do round sempre satisfaz "ficou em
        # desvantagem e não recuperou", mas dizer "ficou em 0v1" não informa
        # nada — o round já tinha acabado ali.
        if deficit_from_here and loser_alive < winner_alive and loser_alive >= 1:
            # Quem "fica em 1v2" é quem SOBROU vivo, não quem acabou de morrer.
            # Nomear a vítima da kill aqui produzia a frase errada.
            dead_so_far = {t["victim_steamid"] for t in timeline[: i + 1]}
            survivors = [
                names.get(sid, str(sid))
                for sid, tm in team_of.items()
                if tm == loser and sid not in dead_so_far
            ]
            score = str(loser_alive) + "v" + str(winner_alive)
            if len(survivors) == 1:
                who, text = survivors[0], "ficou sozinho no " + score + " e não recuperou mais"
            else:
                who, text = None, "o time ficou em " + score + " e não recuperou mais"

            moments.append(
                {
                    "tick": int(k["tick"]),
                    "t": _segundos(k["tick"], t0, TICKRATE, f"round {rn}, virada numérica"),
                    "kind": "virada_numerica",
                    "who": who,
                    "by": _quem_matou(k)[0],
                    "causa": _quem_matou(k)[1],
                    "victim": k["victim_name"],
                    "survivors": survivors,
                    "score": score,
                    "x": int(round(k["victim_X"])) if k["victim_X"] is not None else None,
                    "y": int(round(k["victim_Y"])) if k["victim_Y"] is not None else None,
                    "text": text,
                }
            )
            break

    # --- utility gasta antes de a coisa desandar ---
    if grenades is not None:
        turning = next((m for m in moments if m["kind"] == "virada_numerica"), None)
        limit = turning["tick"] if turning else 10**9
        loser_names = {p for p, t in team_of.items() if t == loser}
        thrown = grenades.filter(
            (pl.col("round_num") == rn)
            & (pl.col("tick") <= limit)
            & pl.col("thrower_steamid").is_in(list(loser_names))
        )["entity_id"].n_unique()
        if thrown == 0 and not is_eco:
            tags.append("perdeu sem gastar utility")
            moments.append(
                {
                    "tick": t0,
                    "t": 0.0,
                    "kind": "sem_utility",
                    "text": "nenhuma granada do time até a desvantagem se firmar",
                }
            )

    # --- contexto da bomba ---
    planted = round_row["bomb_plant"] is not None
    if loser_side == "t" and not planted:
        tags.append("não chegou a plantar")
        moments.append({"tick": t0, "t": 0.0, "kind": "sem_plant", "text": "o round acabou sem a bomba ser plantada"})
    if loser_side == "ct" and planted and round_row["reason"] == "bomb_exploded":
        tags.append("perdeu o pós-plant")
        moments.append(
            {
                "tick": int(round_row["bomb_plant"]),
                "t": round((int(round_row["bomb_plant"]) - t0) / TICKRATE, 1),
                "kind": "pos_plant",
                "text": "bomba plantada e retake não aconteceu",
            }
        )

    moments.sort(key=lambda m: m["tick"])

    # Pós-round: o tempo continua contado do mesmo zero e continua positivo. O
    # que muda é a leitura — "morreu aos 1:42, depois do round decidido" não é a
    # mesma coisa que morrer durante a disputa.
    fim = int(round_row["end"])
    for m in moments:
        m["pos_round"] = bool(m["tick"] > fim)

    # O último round da partida e o último de cada metade têm fronteira
    # diferente dos demais (o da partida costuma vir sem `official_end`, porque a
    # partida acaba junto). Fica explícito na saída para aparecer na leitura.
    eh_ultimo = ultimo_round is not None and rn == int(ultimo_round)
    eh_fim_de_metade = rn == HALFTIME_ROUND

    # O texto muda com a DIFERENÇA, não só com o valor absoluto. Medido nas 9
    # partidas: dos 56 rounds abaixo do limiar de eco, 18 são round de pistola em
    # que os dois times entraram igualmente pobres — ali "perder é esperado" não
    # se sustenta, porque o adversário tinha o mesmo. Antes os dois casos saíam
    # com a mesma frase.
    contexto_eco = None
    if is_eco:
        contexto_eco = (
            "Round de economia: o time entrou com " + format_money(equip)
            + " de equipamento médio"
        )
        if equip_winner is None:
            contexto_eco += ". O que vale olhar é quanto dano o time conseguiu tirar."
        elif diferenca is not None and diferenca >= DIFERENCA_EQUIP_RELEVANTE:
            contexto_eco += (
                " contra " + format_money(equip_winner) + " do adversário, "
                + format_money(diferenca) + " de diferença. Perder aqui é esperado, e o "
                "que vale olhar é quanto dano o time conseguiu tirar."
            )
        else:
            contexto_eco += (
                " contra " + format_money(equip_winner) + " do adversário. Os dois "
                "entraram com equipamento parecido, então a economia não explica a "
                "derrota — o round foi decidido no confronto."
            )

    return {
        "round": rn,
        "loser_team": loser,
        "loser_side": loser_side,
        "winner_team": winner,
        "eco": bool(is_eco),
        "equip_value": round(equip) if equip is not None else None,
        "equip_value_winner": round(equip_winner) if equip_winner is not None else None,
        "equip_diff": diferenca,
        "eco_text": contexto_eco,
        "untraded_deaths": untraded,
        "ultimo_round": eh_ultimo,
        "fim_de_metade": eh_fim_de_metade,
        "freeze_end": t0,
        "end": fim,
        "tags": tags,
        "moments": moments,
    }


def build_breakdowns(
    rounds: pl.DataFrame,
    kills: pl.DataFrame,
    ticks: pl.DataFrame,
    grenades: pl.DataFrame | None,
    team_of: dict[int, str],
    side_of_team,
    tickrate: int = 64,
) -> list[dict]:
    """Autópsia de todos os rounds da partida."""
    ultimo = int(rounds["round_num"].max())
    return [
        analyze_round(r, kills, ticks, grenades, team_of, side_of_team, tickrate, ultimo)
        for r in rounds.iter_rows(named=True)
    ]
