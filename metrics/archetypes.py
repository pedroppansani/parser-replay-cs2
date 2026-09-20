"""
Papéis nomeados: o que cada jogador FAZ, com a evidência que sustenta o rótulo.

Este módulo substitui o índice "carrega piano" antigo, que era `esforço −
recompensa`. Aquela fórmula estava errada por construção: quem tem recompensa
baixa vence a subtração, e recompensa baixa é, na maior parte das vezes, jogar
mal. Ela elegia o pior jogador da partida e colava nele um rótulo que significa
outra coisa.

Carrega piano é quem SE SACRIFICA E O TIME LUCRA COM ISSO. Por isso o índice
aqui é um PRODUTO, não uma diferença: esforço alto multiplicado por benefício ao
time. Produto zera quando qualquer um dos dois lados zera, que é exatamente o que
a definição exige — quem morre cedo sem gerar nada não é carrega piano, e quem
gera muito sem se expor também não é.

Os papéis NÃO são exclusivos: cada um é um índice independente e o mesmo jogador
pode pontuar em vários. Um AWPer pode ser carry; um âncora pode ser camper.

Sobre a escala dos índices: cada componente vira um PERCENTIL contra a
distribuição do conjunto das partidas (`archetype_reference.json`, ajustado por
scripts/fit_archetype_reference.py, mesmo padrão do global_model.json do
clustering). Isso responde "o quanto este jogador se destaca NESTE papel
comparado ao que é normal nele", que é a pergunta do card de destaque — e não
"quem é o maior desta partida", que numa partida ruim elegeria alguém mediano.
Sem o arquivo de referência, cai para normalização dentro da própria partida e
avisa.

Convenção do projeto: devolve (per_round, summary).
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import polars as pl

from metrics.awp_metrics import HOLD_MAX_DISPLACEMENT, PRE_ENGAGEMENT_WINDOW_SECONDS
from metrics.geometry import horizontal_distance

PROJECT_ROOT = Path(__file__).resolve().parent.parent
REFERENCE_FILE = PROJECT_ROOT / "metrics" / "archetype_reference.json"

# --- Limiares de calibração -------------------------------------------------

# Janela de trade, a mesma das métricas básicas: se o companheiro morreu e você
# não matou quem o matou em 5s, você não trocou aquela morte.
TRADE_WINDOW_SECONDS = 5.0

# Distância até o companheiro que morreu para a morte ser considerada "do seu
# lado". Além disso o jogador está jogando outra parte do mapa e não tinha como
# trocar -- cobrá-lo seria transformar posicionamento em acusação. 900u é a
# ordem de grandeza de um duelo apoiável: dá para chegar no trade dentro da
# janela sem atravessar o mapa.
BAIT_MAX_DISTANCE = 900.0

# Repick: reaparecer no mesmo ângulo. Reusa a assinatura de jiggle que
# awp_metrics já mede (decisão 1 do CLAUDE.md) -- distância percorrida alta com
# deslocamento LÍQUIDO baixo. O deslocamento líquido baixo é o mesmo limiar do
# hold; o que distingue repick de ficar parado é ter andado no meio.
REPICK_MIN_PATH = 250.0
REPICK_MIN_RATIO = 3.0  # percorreu 3x mais do que saiu do lugar
# Distância do ponto inicial que conta como ter SAÍDO do ângulo. Um passo
# lateral de peek no CS2 é de 60 a 100u; 40u separa balançar a mira parado
# de sair de verdade.
REPICK_SAIDA_MIN = 40.0
# Armas cuja morte não é duelo: o desfecho "morreu para utility" é categoria
# própria e fica fora de qualquer taxa de duelo.
UTILITY_LETAL = {"hegrenade", "inferno", "molotov", "incgrenade", "flashbang", "decoy"}

# Mínimo de situações de último vivo para o "rei do NT" aparecer. Nas 9 partidas
# são 182 tentativas em 187 rounds, ~2 por jogador por partida: sem um mínimo, o
# índice premiaria quem teve UMA situação e não converteu.
MIN_CLUTCH_ATTEMPTS = 3

# Peso de cada tentativa de clutch no índice do rei do NT: o próprio X do 1vX
# (`clutch_peso` em _junta_clutch). Perder um 1v1 é quase moeda (pesa 1); sobrar
# num 1v3 e perder é a situação que define quem "sempre fica sozinho no quase
# clutch" (pesa 3). Linear no X, sem constante escolhida -- o X já é a medida da
# dificuldade. A CONTAGEM de clutch (a que bate com a HLTV) não usa peso nenhum.

# Mínimo de rounds com AWP na mão para o papel de AWPer existir. Abaixo disso é
# AWP de round de força.
MIN_AWP_ROUNDS = 4

# Kills no round que caracterizam multikill, igual ao usado nos insights.
MULTIKILL_MIN = 3

# --- Eixo carrega piano <-> baiter ------------------------------------------
#
# Os dois são o MESMO eixo visto das duas pontas: quem paga a conta para o time
# colher, e quem deixa o time pagar a conta dele. Um jogador não pode ser os dois
# na mesma partida -- por isso é UM índice contínuo com sinal, e os rótulos saem
# das duas pontas:
#
#   sacrifice_index = percentil(sacrifício com retorno)
#                   - percentil(mortes de companheiro por perto sem troca, por round)
#
# de -1 (baiter) a +1 (carrega piano). O que separa carrega piano de jogador
# ruim é o RETORNO: os dois morrem abrindo o round, mas só no primeiro o time
# colhe. Medido nas 52 partidas (520 jogador-partidas): pagar a conta SEM
# retorno correlaciona -0,31 com o rating; pagar COM retorno, -0,05 --
# independente de jogar bem ou mal, que é o que o papel tem que ser.

# Janela em que uma flash ainda explica a kill do companheiro que veio depois.
# A mesma do crédito de flash no Round Swing (metrics/rating.py).
SEGUNDOS_FLASH_RETORNO = 3.0

# A isca é comparada DENTRO DA FUNÇÃO. Jogar de trás e não trocar de perto é a
# função do AWPer e do âncora, não oportunismo -- medido, 56% dos rótulos de
# baiter iam para AWPers, que são 18% dos jogador-partidas. A referência de cada
# função sai do CORPUS inteiro (1 ou 2 AWPers por partida seriam ruído), e a
# comparação é ROUND A ROUND pelo contexto daquele round: quem puxa AWP em
# alguns rounds é comparado como AWPer só neles.
MIN_ROUNDS_FUNCAO_NA_REFERENCIA = 100
CONTEXTO_SEM_FUNCAO = "sem_funcao"

# Pisos do eixo. 0,5 = meia distribuição de diferença entre as duas pontas (por
# exemplo, quartil de cima no sacrifício e quartil de baixo na isca). Medido no
# corpus: 91 jogador-partidas do lado do piano e 86 do lado do baiter, de 520.
# Ponto de calibração do Pedro -- ver scripts/calibration_report.py.
PISO_CARREGA_PIANO = 0.5
PISO_BAITER = -0.5


# --- Fatos por round --------------------------------------------------------

def round_facts(
    features: pl.DataFrame,
    grenades: pl.DataFrame,
    rounds: pl.DataFrame,
    positions: pl.DataFrame,
) -> pl.DataFrame:
    """Uma linha por (round, jogador) com o que os papéis precisam.

    Quase tudo já existe em `cluster_features` (dano, kills, trades, sobreviveu,
    foi trocado, tempo até o contato). O que este passo acrescenta é: se o round
    foi vencido, quem foi o primeiro do time a encostar no adversário, e quanto
    o jogador andou no round.
    """
    vencedor = rounds.select(
        pl.col("round_num").cast(pl.UInt32), pl.col("winner").alias("winner_side")
    )

    # Distância percorrida no round, das amostras de posição. É o que separa
    # camper (fica) de quem roda o mapa; `distinct_places` sozinho não separa,
    # porque dá pra andar muito dentro de duas regiões grandes.
    andou = (
        positions.sort(["round_num", "steamid", "tick"])
        .with_columns(
            (pl.col("X") - pl.col("X").shift(1).over(["round_num", "steamid"])).alias("dx"),
            (pl.col("Y") - pl.col("Y").shift(1).over(["round_num", "steamid"])).alias("dy"),
        )
        .with_columns((pl.col("dx") ** 2 + pl.col("dy") ** 2).sqrt().alias("passo"))
        .group_by(["round_num", "steamid"])
        .agg(pl.col("passo").sum().alias("path_distance_round"))
    )

    gren = grenades.select(
        ["round_num", "steamid", "enemy_blind_seconds", "utility_damage", "nades_thrown"]
    ).rename({"utility_damage": "utility_damage_gren"})

    # `cluster_features` guarda survived/was_traded como 0.0/1.0 (o clustering
    # precisa deles numericos). Aqui eles voltam a ser booleanos, senao qualquer
    # negacao estoura -- "dtype Float64 not supported in 'not' operation".
    features = features.with_columns(
        pl.col("survived").cast(pl.Boolean),
        pl.col("was_traded").cast(pl.Boolean),
    )

    facts = (
        features.join(vencedor, on="round_num", how="left")
        .join(andou, on=["round_num", "steamid"], how="left")
        .join(gren, on=["round_num", "steamid"], how="left")
        .with_columns(
            (pl.col("side") == pl.col("winner_side")).alias("round_won"),
            pl.col("path_distance_round").fill_null(0.0),
            pl.col("enemy_blind_seconds").fill_null(0.0),
            pl.col("nades_thrown").fill_null(0),
        )
    )

    # Primeiro do próprio time a tomar contato no round. A comparação é dentro do
    # time e dentro do round: "encostou antes dos companheiros" é a definição de
    # entry que o projeto usa (decisão 13 do CLAUDE.md).
    facts = facts.with_columns(
        pl.col("time_of_first_contact_s")
        .rank("min")
        .over(["round_num", "side"])
        .alias("posto_contato")
    ).with_columns(
        # Quantos companheiros empataram no primeiro lugar. Empate acontece
        # quando uma granada só pega vários do time no MESMO tick: medido, são
        # 24 de 374 lados-round nas 9 partidas, um deles com quatro jogadores
        # empatados em 10,359375s. Marcar os quatro como quem abriu o round
        # infla a métrica de entry de todo mundo -- ninguém abriu nada ali.
        pl.col("posto_contato").eq(1).sum().over(["round_num", "side"]).alias("empatados_no_primeiro")
    ).with_columns(
        (
            (pl.col("posto_contato") == 1)
            & (pl.col("empatados_no_primeiro") == 1)
            & pl.col("time_of_first_contact_s").is_not_null()
        ).alias("first_contact_of_team")
    )

    return facts.sort(["round_num", "steamid"])


def bait_events(
    kills: pl.DataFrame,
    ticks: pl.DataFrame,
    team_of: dict[int, str],
    tickrate: int = 64,
    max_distance: float = BAIT_MAX_DISTANCE,
    trade_window_seconds: float = TRADE_WINDOW_SECONDS,
) -> pl.DataFrame:
    """Mortes de companheiro com um jogador vivo e perto que não trocou.

    Uma linha por (round, jogador observado, morte de companheiro observada).
    `traded` diz se ele vingou aquela morte dentro da janela.

    O filtro de distância existe pra não transformar posicionamento em acusação:
    quem estava do outro lado do mapa não tinha como trocar, e contá-lo como
    quem "deixou morrer" seria medir o mapa, não a intenção.
    """
    janela = int(trade_window_seconds * tickrate)

    mortes = kills.select(
        pl.col("round_num").cast(pl.UInt32),
        pl.col("tick").alias("death_tick"),
        pl.col("victim_steamid"),
        pl.col("attacker_steamid").alias("killer_steamid"),
        pl.col("victim_X"), pl.col("victim_Y"),
    ).filter(pl.col("victim_steamid").is_not_null())

    if mortes.height == 0:
        return pl.DataFrame(
            schema={"round_num": pl.UInt32, "steamid": pl.UInt64, "death_tick": pl.Int64,
                    "victim_steamid": pl.UInt64, "distance": pl.Float64, "traded": pl.Boolean}
        )

    # Posição de todo mundo no tick de cada morte: uma linha por (morte, jogador).
    pos_na_morte = ticks.select(
        ["round_num", "tick", "steamid", "X", "Y", "is_alive"]
    ).join(
        mortes.select(["round_num", "death_tick"]).unique(),
        left_on=["round_num", "tick"],
        right_on=["round_num", "death_tick"],
        how="inner",
    ).rename({"tick": "death_tick"})

    candidatos = (
        mortes.join(pos_na_morte, on=["round_num", "death_tick"], how="inner")
        .filter(
            pl.col("is_alive")
            & (pl.col("steamid") != pl.col("victim_steamid"))
        )
        .with_columns(
            pl.col("steamid").map_elements(lambda s: team_of.get(s), return_dtype=pl.String).alias("time"),
            pl.col("victim_steamid").map_elements(lambda s: team_of.get(s), return_dtype=pl.String).alias("time_vitima"),
        )
        .filter(pl.col("time").is_not_null() & (pl.col("time") == pl.col("time_vitima")))
    )

    if candidatos.height == 0:
        return pl.DataFrame(
            schema={"round_num": pl.UInt32, "steamid": pl.UInt64, "death_tick": pl.Int64,
                    "victim_steamid": pl.UInt64, "distance": pl.Float64, "traded": pl.Boolean}
        )

    candidatos = candidatos.with_columns(
        (
            (pl.col("X") - pl.col("victim_X")) ** 2 + (pl.col("Y") - pl.col("victim_Y")) ** 2
        ).sqrt().alias("distance")
    ).filter(pl.col("distance") <= max_distance)

    # Trocou aquela morte? Matou o assassino do companheiro dentro da janela.
    vinganças = kills.select(
        pl.col("round_num").cast(pl.UInt32),
        pl.col("attacker_steamid").alias("steamid"),
        pl.col("victim_steamid").alias("killer_steamid"),
        pl.col("tick").alias("revenge_tick"),
    )

    com_troca = (
        candidatos.join(vinganças, on=["round_num", "steamid", "killer_steamid"], how="left")
        .with_columns(
            (
                pl.col("revenge_tick").is_not_null()
                & (pl.col("revenge_tick") > pl.col("death_tick"))
                & (pl.col("revenge_tick") <= pl.col("death_tick") + janela)
            ).alias("traded")
        )
        .group_by(["round_num", "steamid", "death_tick", "victim_steamid"])
        .agg(pl.col("distance").first(), pl.col("traded").any())
    )

    return com_troca.sort(["round_num", "death_tick", "steamid"])


def repick_engagements(styles: pl.DataFrame) -> pl.DataFrame:
    """Assinatura de JIGGLE: andou bastante e terminou perto de onde comecou.

    E so a primeira metade do criterio. Jiggle sozinho NAO e repick (decisao 1:
    sair e voltar e jogar um angulo) -- o que faz o repick e o que aconteceu no
    angulo no meio do caminho, e isso e `marca_repick`.
    """
    if styles.height == 0:
        return styles.with_columns(pl.lit(False).alias("jiggle"))

    return styles.with_columns(
        (
            pl.col("net_displacement").is_not_null()
            & (pl.col("net_displacement") < HOLD_MAX_DISPLACEMENT)
            & (pl.col("path_distance") >= REPICK_MIN_PATH)
            & (pl.col("path_distance") >= REPICK_MIN_RATIO * pl.col("net_displacement").clip(1.0))
        ).alias("jiggle")
    )


def marca_repick(
    styles: pl.DataFrame, ticks: pl.DataFrame, kills: pl.DataFrame,
    damages: pl.DataFrame | None, shots: pl.DataFrame | None, tickrate: int = 64,
) -> pl.DataFrame:
    """Repick = retomar um angulo que foi CONTESTADO.

    A identificacao tem duas partes, e nenhuma basta sozinha:

    1. a assinatura de jiggle (`repick_engagements`): saiu do angulo e voltou;
    2. **aconteceu alguma coisa naquele angulo entre sair e voltar** -- ele
       atirou, causou ou sofreu dano, ou alguem morreu por perto.

    Sem a segunda, e jiggle: dos 10 casos que o Pedro conferiu, 9 tinham UMA
    saida e volta sem nada no meio. Com ela, um repick de uma saida so continua
    valendo -- e o caso de quem volta para pegar o refrag depois de o companheiro
    cair. O numero de saidas vira sinal de QUALIDADE (`saidas`), nao criterio.

    O DESFECHO fica em coluna separada e nao entra na identificacao: a causa da
    morte e resultado, e morrer para uma granada nao desfaz o repick que
    aconteceu antes. Morte por utility e categoria propria, fora de qualquer
    taxa de duelo.
    """
    marcados = repick_engagements(styles)
    vazio = {"repick": pl.Boolean, "saidas": pl.Int32, "evento_no_angulo": pl.Utf8, "desfecho": pl.Utf8}
    if marcados.height == 0 or "engagement_tick" not in marcados.columns:
        return marcados.with_columns([pl.lit(None, dtype=t).alias(c) for c, t in vazio.items()])

    janela = int(PRE_ENGAGEMENT_WINDOW_SECONDS * tickrate)
    pos = {}
    for (rn, sid), g in ticks.select("round_num", "steamid", "tick", "X", "Y").sort("tick").group_by(
            ["round_num", "steamid"]):
        pos[(int(rn), int(sid))] = (
            g["tick"].to_numpy(), g["X"].to_numpy().astype(float), g["Y"].to_numpy().astype(float))

    def _por_round(df, colunas):
        fora = {}
        if df is None or df.height == 0 or not set(colunas) <= set(df.columns):
            return fora
        for (rn,), g in df.select(["round_num", *colunas]).group_by("round_num"):
            fora[int(rn)] = g
        return fora

    dano_por_round = _por_round(damages, ["tick", "attacker_steamid", "victim_steamid"])
    tiro_por_round = _por_round(shots, ["tick", "player_steamid"])
    kills_por_round = _por_round(
        kills, ["tick", "victim_X", "victim_Y", "weapon", "attacker_steamid", "victim_steamid"])

    linhas = []
    for r in marcados.iter_rows(named=True):
        rn, sid, tk = int(r["round_num"]), int(r["steamid"]), int(r["engagement_tick"])
        evento, saidas = None, 0
        if r["jiggle"] and (rn, sid) in pos:
            t, xs, ys = pos[(rn, sid)]
            dentro = (t >= tk - janela) & (t <= tk)
            t, xs, ys = t[dentro], xs[dentro], ys[dentro]
            if t.size >= 2:
                d = np.hypot(xs - xs[0], ys - ys[0])
                intervalos, fora, t_ini = [], False, None
                for i, v in enumerate(d):
                    if not fora and v > REPICK_SAIDA_MIN:
                        fora, t_ini, saidas = True, t[i], saidas + 1
                    elif fora and v < REPICK_SAIDA_MIN / 2:
                        intervalos.append((t_ini, t[i]))
                        fora = False
                if fora:  # saiu e a briga aconteceu antes de ele voltar
                    intervalos.append((t_ini, t[-1]))
                for a, b in intervalos:
                    g = dano_por_round.get(rn)
                    if g is not None and g.filter(
                            (pl.col("tick") >= a) & (pl.col("tick") <= b)
                            & ((pl.col("attacker_steamid") == sid) | (pl.col("victim_steamid") == sid))).height:
                        evento = "dano"
                        break
                    g = tiro_por_round.get(rn)
                    if g is not None and g.filter(
                            (pl.col("tick") >= a) & (pl.col("tick") <= b) & (pl.col("player_steamid") == sid)).height:
                        evento = "tiro"
                        break
                    g = kills_por_round.get(rn)
                    if g is not None:
                        perto = g.filter((pl.col("tick") >= a) & (pl.col("tick") <= b))
                        if perto.height:
                            j = int(np.argmin(np.abs(t - float(perto["tick"][0]))))
                            dist = np.hypot(perto["victim_X"].to_numpy().astype(float) - xs[j],
                                            perto["victim_Y"].to_numpy().astype(float) - ys[j])
                            if bool((dist <= BAIT_MAX_DISTANCE).any()):
                                evento = "morte por perto"
                                break
        desfecho = None
        g = kills_por_round.get(rn)
        if g is not None:
            for k in g.filter(pl.col("tick") == tk).iter_rows(named=True):
                if k["attacker_steamid"] == sid:
                    desfecho = "ganhou o duelo"
                elif k["victim_steamid"] == sid:
                    desfecho = "morreu para utility" if k["weapon"] in UTILITY_LETAL else "perdeu o duelo"
        linhas.append({"repick": bool(r["jiggle"] and evento), "saidas": saidas,
                       "evento_no_angulo": evento, "desfecho": desfecho})

    return pl.concat([marcados, pl.DataFrame(linhas, schema=vazio)], how="horizontal")


# --- Referência de escala ---------------------------------------------------

def load_reference(path: Path = REFERENCE_FILE) -> dict | None:
    """Quantis de cada componente no conjunto das partidas, ou None."""
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def percentil(valor: float | None, quantis: list[float] | None) -> float:
    """Posição de `valor` na distribuição de referência, de 0 a 1.

    Percentil e não z-score porque os componentes são assimétricos (dano de
    utility, clutches, picks de abertura têm cauda longa) e um z-score deixaria
    um único jogador extremo achatar todos os outros.
    """
    if valor is None or quantis is None or not quantis:
        return 0.0
    arr = np.asarray(quantis, dtype=float)
    return float(np.searchsorted(arr, float(valor), side="right") / len(arr))


# --- Sinais de economia (a forma ECO do carrega piano) ----------------------

# Nomes de exibição, como vêm no demo (`active_weapon_name`): "AK-47", não
# "ak47". Descobri isso na marra -- a primeira versão usou os codenames e casou
# zero linha em 9 partidas, o que passaria como "ninguém joga de SMG".
SMGS = {"MP9", "MAC-10", "MP5-SD", "UMP-45", "P90", "MP7", "PP-Bizon"}
RIFLES = {"AK-47", "M4A1-S", "M4A4", "Galil AR", "FAMAS", "AUG", "SG 553",
          "AWP", "SSG 08", "SCAR-20", "G3SG1"}

# Fração do time que precisa estar de rifle para a SMG de um jogador contar como
# sacrifício de economia. Abaixo disso é round de eco do time inteiro, e aí a SMG
# não é sacrifício de ninguém em particular.
TEAM_RIFLE_FRACTION = 0.60

# Quanto abaixo da média do próprio time, em dólares de equipamento, conta como
# ter comprado menos para o companheiro comprar mais. Medido em match_01: o
# quartil de baixo do desvio fica em -280, e quem fica sistematicamente abaixo
# aparece com média de -300 a -400.
UNDERBUY_DELTA = -400.0


def economy_signals(ticks: pl.DataFrame, rounds: pl.DataFrame) -> pl.DataFrame:
    """Equipamento de cada jogador contra a média do PRÓPRIO TIME no mesmo round.

    A comparação é interna e por round de propósito: o que interessa não é ter
    pouco dinheiro (o time inteiro tem, em round de eco), é ter menos que os
    companheiros no mesmo round -- que é a assinatura de quem abriu mão para o
    outro comprar.

    A arma primária é a mais EMPUNHADA no round, não a do fim do freeze time: no
    freeze o jogador costuma estar com a faca ou a pistola na mão, e uma versão
    anterior disto contou zero SMG em 9 partidas por causa disso.
    """
    alvo = rounds.select(["round_num", "freeze_end"])

    compra = (
        ticks.join(alvo, on="round_num", how="inner")
        .filter(pl.col("tick") >= pl.col("freeze_end"))
        .sort("tick")
        .group_by(["round_num", "steamid"])
        .first()
        .select(
            ["round_num", "steamid", "name", "side",
             # o awpy devolve este campo como UInt32 em 7 das 9 partidas e
             # Float64 nas outras 2 (depende de a demo ter tick sem o valor).
             # Normalizar aqui deixa o schema de saída estável -- sem isso,
             # empilhar as partidas para qualquer análise do conjunto estoura.
             pl.col("current_equip_value").cast(pl.Float64)]
        )
    )

    primaria = (
        ticks.filter(
            pl.col("is_alive") & pl.col("active_weapon_name").is_in(list(SMGS | RIFLES))
        )
        .group_by(["round_num", "steamid", "active_weapon_name"])
        .len()
        .sort("len", descending=True)
        .group_by(["round_num", "steamid"], maintain_order=True)
        .first()
        .select(["round_num", "steamid", pl.col("active_weapon_name").alias("primary_weapon")])
    )

    eco = (
        compra.join(primaria, on=["round_num", "steamid"], how="left")
        .with_columns(
            pl.col("current_equip_value").mean().over(["round_num", "side"]).alias("team_equip_mean"),
            pl.col("primary_weapon").is_in(list(SMGS)).fill_null(False).alias("is_smg"),
            pl.col("primary_weapon").is_in(list(RIFLES)).fill_null(False).alias("is_rifle"),
        )
        .with_columns(
            (pl.col("current_equip_value") - pl.col("team_equip_mean")).alias("equip_delta"),
            pl.col("is_rifle").mean().over(["round_num", "side"]).alias("team_frac_rifle"),
        )
        .with_columns(
            (
                (pl.col("equip_delta") <= UNDERBUY_DELTA)
                | (pl.col("is_smg") & (pl.col("team_frac_rifle") >= TEAM_RIFLE_FRACTION))
            ).alias("eco_sacrifice")
        )
    )
    return eco.select(
        ["round_num", "steamid", "current_equip_value", "team_equip_mean", "equip_delta",
         "primary_weapon", "is_smg", "team_frac_rifle", "eco_sacrifice"]
    )


def solo_hold_signals(player_areas: pl.DataFrame) -> pl.DataFrame:
    """Rounds de CT em que o jogador ficou SOZINHO na área que jogou.

    É a forma CT do carrega piano: segurar um bombsite sem companheiro enquanto o
    time joga em outro lugar. Quem está sozinho na área entra em desvantagem
    numérica por construção -- não precisa contar inimigos pra saber que um
    jogador contra a execução de um time está em minoria.
    """
    if player_areas.height == 0:
        return pl.DataFrame(
            schema={"round_num": pl.UInt32, "steamid": pl.UInt64, "alone_in_area": pl.Boolean}
        )

    return (
        player_areas.with_columns(
            pl.len().over(["round_num", "side", "area"]).alias("na_area")
        )
        .with_columns(((pl.col("side") == "ct") & (pl.col("na_area") == 1)).alias("alone_in_area"))
        .select(["round_num", "steamid", "alone_in_area"])
    )


def flash_convertida(
    blinds: pl.DataFrame | None, kills: pl.DataFrame, tickrate: int = 64,
    janela_s: float = SEGUNDOS_FLASH_RETORNO,
) -> pl.DataFrame:
    """Rounds em que o jogador cegou um inimigo que um COMPANHEIRO matou logo depois.

    É a terceira forma de o time colher do sacrifício (além de vencer o round e
    de trocar a morte): a utility dele virou kill de outro. A kill do próprio
    arremessador não conta aqui -- essa já é dele, não retorno para o time.
    Cegueira de companheiro também não: cegar o próprio time não ajuda ninguém.
    """
    vazio = pl.DataFrame(schema={"round_num": pl.UInt32, "steamid": pl.UInt64, "flash_convertida": pl.Boolean})
    if blinds is None or blinds.height == 0 or kills.height == 0:
        return vazio
    cegas = blinds.filter(
        pl.col("attacker_steamid").is_not_null() & (pl.col("attacker_side") != pl.col("user_side"))
    ).select(
        pl.col("round_num").cast(pl.UInt32), pl.col("tick").alias("tick_flash"),
        pl.col("attacker_steamid").cast(pl.UInt64).alias("steamid"), pl.col("attacker_side").alias("lado"),
        pl.col("user_steamid").cast(pl.UInt64).alias("vitima"),
    )
    mortes = kills.filter(pl.col("attacker_steamid").is_not_null()).select(
        pl.col("round_num").cast(pl.UInt32), pl.col("tick").alias("tick_kill"),
        pl.col("victim_steamid").cast(pl.UInt64).alias("vitima"),
        pl.col("attacker_steamid").cast(pl.UInt64).alias("matador"), pl.col("attacker_side").alias("lado_matador"),
    )
    janela = int(janela_s * tickrate)
    conv = (
        cegas.join(mortes, on=["round_num", "vitima"], how="inner")
        .filter(
            (pl.col("tick_kill") >= pl.col("tick_flash"))
            & (pl.col("tick_kill") - pl.col("tick_flash") <= janela)
            & (pl.col("matador") != pl.col("steamid"))
            & (pl.col("lado_matador") == pl.col("lado"))
        )
        .select("round_num", "steamid").unique()
        .with_columns(pl.lit(True).alias("flash_convertida"))
    )
    return conv if conv.height else vazio


# --- Componentes por jogador ------------------------------------------------

# Todo componente bruto que entra em algum índice. A lista é explícita porque é
# ela que o arquivo de referência precisa cobrir -- componente novo sem entrada
# na referência cai em percentil 0 e some do índice em silêncio.
COMPONENTES = [
    "first_contact_share", "util_per_round", "frac_entering_fight", "death_rate",
    "traded_death_share", "piano_t_share", "piano_ct_share", "piano_eco_share",
    "damage_share", "kill_share", "multikill_rounds", "clutch_wins",
    "distinct_places_mean", "path_per_round", "repick_share",
    "awp_round_share", "awp_conversion", "awp_opening_picks",
    "bait_no_trade_share", "bait_untraded_per_round", "bait_return_per_opp", "survival_rate",
    "clutch_attempts", "clutch_conversion", "clutch_damage_per_attempt",
    "sacrificio_share", "clutch_peso", "isca_relativa",
]


def player_components(
    facts: pl.DataFrame,
    eco: pl.DataFrame,
    solo: pl.DataFrame,
    bait: pl.DataFrame,
    repick: pl.DataFrame,
    clutch_round: pl.DataFrame,
    awp_summary: pl.DataFrame | None,
    team_of: dict[int, str],
    flash_conv: pl.DataFrame | None = None,
    funcoes_round: pl.DataFrame | None = None,
    isca_por_funcao: dict | None = None,
) -> tuple[pl.DataFrame, pl.DataFrame]:
    """Devolve (per_round, componentes): os fatos round a round e o agregado.

    Os componentes saem em unidade CRUA (fração de rounds, dólares, unidades de
    mapa). A conversão para escala comparável acontece só em `archetype_indices`,
    contra a referência do conjunto -- assim a tabela por jogador continua
    auditável em número de jogo, que é o que permite discordar do índice.
    """
    if flash_conv is None or flash_conv.height == 0:
        flash_conv = pl.DataFrame(schema={"round_num": pl.UInt32, "steamid": pl.UInt64, "flash_convertida": pl.Boolean})
    per_round = (
        facts.join(eco, on=["round_num", "steamid"], how="left")
        .join(solo, on=["round_num", "steamid"], how="left")
        .join(flash_conv.with_columns(pl.col("round_num").cast(facts.schema["round_num"]),
                                      pl.col("steamid").cast(facts.schema["steamid"])),
              on=["round_num", "steamid"], how="left")
        .with_columns(
            pl.col("eco_sacrifice").fill_null(False),
            pl.col("alone_in_area").fill_null(False),
            pl.col("flash_convertida").fill_null(False),
            pl.col("steamid")
            .map_elements(lambda s: team_of.get(s), return_dtype=pl.String)
            .alias("team"),
        )
        .with_columns(
            # As três formas do carrega piano. O que une as três é a segunda
            # metade: o time converteu o round em que ele pagou a conta.
            (
                (pl.col("side") == "t")
                & pl.col("first_contact_of_team")
                & ~pl.col("survived")
            ).alias("piano_t_paid_raw"),
            (
                (pl.col("side") == "ct") & pl.col("alone_in_area") & ~pl.col("survived")
            ).alias("piano_ct_paid_raw"),
            pl.col("eco_sacrifice").alias("piano_eco_paid_raw"),
        )
        .with_columns(
            # "O time colheu", igual para as três formas: venceu o round, vingou
            # a morte dele, ou matou alguém que ele cegou (a utility virou kill
            # de outro). A troca e a flash valem mesmo em round perdido: são o
            # benefício imediato de ele ter pago a conta.
            (pl.col("round_won") | pl.col("was_traded") | pl.col("flash_convertida")).alias("time_colheu"),
        )
        .with_columns(
            (pl.col("piano_t_paid_raw") & pl.col("time_colheu")).alias("piano_t"),
            (pl.col("piano_ct_paid_raw") & pl.col("time_colheu")).alias("piano_ct"),
            (pl.col("piano_eco_paid_raw") & pl.col("time_colheu")).alias("piano_eco"),
            (pl.col("piano_t_paid_raw") | pl.col("piano_ct_paid_raw") | pl.col("piano_eco_paid_raw")).alias("pagou"),
        )
        .with_columns(
            # o round conta UMA vez mesmo se ele pagou de duas formas nele
            (pl.col("pagou") & pl.col("time_colheu")).alias("sacrificio"),
            (pl.col("pagou") & ~pl.col("time_colheu")).alias("pagou_sem_retorno"),
        )
    )

    # --- função estrutural do round e isca comparada dentro dela -----------
    if funcoes_round is not None and funcoes_round.height:
        f = funcoes_round.select(
            pl.col("round_num").cast(per_round.schema["round_num"]),
            pl.col("steamid").cast(per_round.schema["steamid"]),
            pl.col("funcao").fill_null(CONTEXTO_SEM_FUNCAO).alias("funcao_do_round"),
        )
        per_round = per_round.join(f, on=["round_num", "steamid"], how="left").with_columns(
            pl.col("funcao_do_round").fill_null(CONTEXTO_SEM_FUNCAO))
    else:
        per_round = per_round.with_columns(pl.lit(CONTEXTO_SEM_FUNCAO).alias("funcao_do_round"))

    if bait.height:
        isca_round = (bait.filter(~pl.col("traded")).group_by(["round_num", "steamid"])
                      .agg(pl.len().alias("isca_no_round")))
        per_round = per_round.join(
            isca_round.select(pl.col("round_num").cast(per_round.schema["round_num"]),
                              pl.col("steamid").cast(per_round.schema["steamid"]), "isca_no_round"),
            on=["round_num", "steamid"], how="left")
    per_round = per_round.with_columns(
        pl.col("isca_no_round").fill_null(0) if "isca_no_round" in per_round.columns
        else pl.lit(0).alias("isca_no_round"))
    # o esperado daquele contexto; sem referência, 1,0 (a isca relativa vira a crua)
    esperado = (isca_por_funcao or {})
    per_round = per_round.with_columns(
        pl.col("funcao_do_round").map_elements(
            lambda f: float(esperado.get(f, esperado.get("_geral", 0.0)) or 0.0),
            return_dtype=pl.Float64).alias("isca_esperada_do_round"))

    rounds_por_lado = per_round.group_by(["steamid", "side"]).agg(pl.len().alias("n"))
    t_rounds = rounds_por_lado.filter(pl.col("side") == "t").select(
        ["steamid", pl.col("n").alias("t_rounds")]
    )
    ct_rounds = rounds_por_lado.filter(pl.col("side") == "ct").select(
        ["steamid", pl.col("n").alias("ct_rounds")]
    )

    base = per_round.group_by(["steamid", "name", "team"]).agg(
        pl.len().alias("rounds_played"),
        pl.col("first_contact_of_team").mean().alias("first_contact_share"),
        (pl.col("enemy_blind_seconds") + pl.col("utility_damage")).mean().alias("util_per_round"),
        pl.col("frac_entering_fight").mean().alias("frac_entering_fight"),
        pl.col("survived").mean().alias("survival_rate"),
        pl.col("was_traded").filter(~pl.col("survived")).mean().alias("traded_death_share"),
        pl.col("damage").sum().alias("total_damage"),
        pl.col("kills").sum().alias("total_kills"),
        (pl.col("kills") >= MULTIKILL_MIN).sum().alias("multikill_rounds"),
        pl.col("distinct_places").mean().alias("distinct_places_mean"),
        pl.col("path_distance_round").mean().alias("path_per_round"),
        pl.col("piano_t").sum().alias("piano_t_rounds"),
        pl.col("piano_ct").sum().alias("piano_ct_rounds"),
        pl.col("piano_eco").sum().alias("piano_eco_rounds"),
        pl.col("eco_sacrifice").sum().alias("eco_sacrifice_rounds"),
        pl.col("pagou").sum().alias("pagou_rounds"),
        pl.col("sacrificio").sum().alias("sacrificio_rounds"),
        pl.col("sacrificio").mean().alias("sacrificio_share"),
        pl.col("pagou_sem_retorno").sum().alias("pagou_sem_retorno_rounds"),
        (pl.col("sacrificio") & pl.col("flash_convertida")).sum().alias("sacrificio_com_flash_rounds"),
        pl.col("isca_no_round").sum().alias("isca_observada"),
        pl.col("isca_esperada_do_round").sum().alias("isca_esperada"),
    )

    # Fatias do time: dano e kills do jogador sobre o total do próprio time. E a
    # traducao direta de "levar o time nas costas" -- e por ser fracao do time,
    # não sofre com partida de placar alto ou baixo.
    totais_time = base.group_by("team").agg(
        pl.col("total_damage").sum().alias("team_damage"),
        pl.col("total_kills").sum().alias("team_kills"),
    )

    comp = (
        base.join(totais_time, on="team", how="left")
        .join(t_rounds, on="steamid", how="left")
        .join(ct_rounds, on="steamid", how="left")
        .with_columns(
            pl.col("t_rounds").fill_null(0), pl.col("ct_rounds").fill_null(0),
            pl.col("traded_death_share").fill_null(0.0),
        )
        .with_columns(
            (pl.col("total_damage") / pl.col("team_damage")).alias("damage_share"),
            (pl.col("total_kills") / pl.col("team_kills")).alias("kill_share"),
            (1.0 - pl.col("survival_rate")).alias("death_rate"),
            pl.when(pl.col("t_rounds") > 0)
            .then(pl.col("piano_t_rounds") / pl.col("t_rounds"))
            .otherwise(0.0)
            .alias("piano_t_share"),
            pl.when(pl.col("ct_rounds") > 0)
            .then(pl.col("piano_ct_rounds") / pl.col("ct_rounds"))
            .otherwise(0.0)
            .alias("piano_ct_share"),
            (pl.col("piano_eco_rounds") / pl.col("rounds_played")).alias("piano_eco_share"),
        )
    )

    comp = comp.with_columns(
        pl.when(pl.col("isca_esperada") > 0)
        .then(pl.col("isca_observada") / pl.col("isca_esperada"))
        .otherwise(1.0)
        .alias("isca_relativa")
    )
    comp = _junta_repick(comp, repick)
    comp = _junta_bait(comp, bait)
    comp = _junta_clutch(comp, clutch_round)
    comp = _junta_awp(comp, awp_summary)

    return per_round, comp


def _junta_repick(comp: pl.DataFrame, repick: pl.DataFrame) -> pl.DataFrame:
    """Fracao dos engajamentos do jogador com assinatura de repick."""
    if repick.height == 0 or "repick" not in repick.columns:
        return comp.with_columns(
            pl.lit(0.0).alias("repick_share"), pl.lit(0, dtype=pl.UInt32).alias("engagements")
        )
    agg = repick.group_by("steamid").agg(
        pl.len().cast(pl.UInt32).alias("engagements"),
        pl.col("repick").mean().alias("repick_share"),
    )
    return comp.join(agg, on="steamid", how="left").with_columns(
        pl.col("repick_share").fill_null(0.0), pl.col("engagements").fill_null(0)
    )


def _junta_bait(comp: pl.DataFrame, bait: pl.DataFrame) -> pl.DataFrame:
    """Oportunidades de troca perto de um companheiro morto, e o que saiu delas."""
    if bait.height == 0:
        return comp.with_columns(
            pl.lit(0, dtype=pl.UInt32).alias("bait_opportunities"),
            pl.lit(0.0).alias("bait_no_trade_share"),
            pl.lit(0.0).alias("bait_return_per_opp"),
            pl.lit(0.0).alias("bait_untraded_per_round"),
        )
    agg = bait.group_by("steamid").agg(
        pl.len().cast(pl.UInt32).alias("bait_opportunities"),
        (~pl.col("traded")).mean().alias("bait_no_trade_share"),
    )
    comp = comp.join(agg, on="steamid", how="left").with_columns(
        pl.col("bait_opportunities").fill_null(0), pl.col("bait_no_trade_share").fill_null(0.0)
    )
    # Retorno: kills por oportunidade. E o "muitas vezes sem conseguir nada" da
    # definição -- fica como evidencia ao lado do indice, não como multiplicador,
    # porque o que define o papel e o comportamento, não o aproveitamento.
    #
    # O indice usa `bait_untraded_per_round`, não a fracao: não trocar e o normal
    # (mediana de 0,84 nas 9 partidas), então a fracao quase não separa ninguem e
    # ainda faria a evidencia soar como acusação em cima de um número médio. O
    # que varia de verdade e QUANTAS vezes por round ele esta por perto de um
    # companheiro caindo sem que a troca venha.
    return comp.with_columns(
        pl.when(pl.col("bait_opportunities") > 0)
        .then(pl.col("total_kills") / pl.col("bait_opportunities"))
        .otherwise(0.0)
        .alias("bait_return_per_opp"),
        (
            pl.col("bait_opportunities") * pl.col("bait_no_trade_share")
            / pl.col("rounds_played")
        ).alias("bait_untraded_per_round"),
    )


def _junta_clutch(comp: pl.DataFrame, clutch_round: pl.DataFrame) -> pl.DataFrame:
    """Tentativas de último vivo, conversão e dano produzido dentro delas.

    Além da contagem (a que bate com o 1vsX da HLTV), cada tentativa pesa o X do
    1vX em `clutch_peso` e `clutch_peso_perdido` -- é esse peso que o rei do NT
    usa (ver o comentário do peso pelo X, no topo). `clutch_por_x` guarda a quebra para a frase.
    """
    if clutch_round.height == 0:
        return comp.with_columns(
            pl.lit(0, dtype=pl.UInt32).alias("clutch_attempts"),
            pl.lit(0, dtype=pl.UInt32).alias("clutch_wins"),
            pl.lit(0.0).alias("clutch_conversion"),
            pl.lit(0.0).alias("clutch_damage_per_attempt"),
            pl.lit(0.0).alias("clutch_peso"),
            pl.lit(0.0).alias("clutch_peso_perdido"),
            pl.lit("").alias("clutch_por_x"),
        )
    tem_dano = "damage_in_clutch" in clutch_round.columns
    x = pl.col("enemies_alive").cast(pl.Float64)
    agg = clutch_round.group_by("steamid").agg(
        pl.len().cast(pl.UInt32).alias("clutch_attempts"),
        pl.col("won").sum().cast(pl.UInt32).alias("clutch_wins"),
        (
            pl.col("damage_in_clutch").mean() if tem_dano else pl.lit(0.0)
        ).alias("clutch_damage_per_attempt"),
        x.sum().alias("clutch_peso"),
        x.filter(~pl.col("won")).sum().alias("clutch_peso_perdido"),
    )
    # "1v1: 1/3, 1v2: 0/2" -- convertidas / tentativas em cada X
    por_x = (
        clutch_round.group_by("steamid", "enemies_alive")
        .agg(pl.len().alias("n"), pl.col("won").sum().alias("v"))
        .sort("enemies_alive")
        .with_columns(("1v" + pl.col("enemies_alive").cast(pl.Utf8) + ": "
                       + pl.col("v").cast(pl.Utf8) + "/" + pl.col("n").cast(pl.Utf8)).alias("t"))
        .group_by("steamid", maintain_order=True).agg(pl.col("t").str.join(", ").alias("clutch_por_x"))
    )
    return (
        comp.join(agg, on="steamid", how="left")
        .join(por_x, on="steamid", how="left")
        .with_columns(
            pl.col("clutch_attempts").fill_null(0),
            pl.col("clutch_wins").fill_null(0),
            pl.col("clutch_damage_per_attempt").fill_null(0.0),
            pl.col("clutch_peso").fill_null(0.0),
            pl.col("clutch_peso_perdido").fill_null(0.0),
            pl.col("clutch_por_x").fill_null(""),
        )
        .with_columns(
            pl.when(pl.col("clutch_attempts") > 0)
            .then(pl.col("clutch_wins") / pl.col("clutch_attempts"))
            .otherwise(0.0)
            .alias("clutch_conversion")
        )
    )


def _junta_awp(comp: pl.DataFrame, awp_summary: pl.DataFrame | None) -> pl.DataFrame:
    """Rounds com AWP na mao, conversão da primeira briga e picks de abertura."""
    vazio = comp.with_columns(
        pl.lit(0, dtype=pl.Int64).alias("awp_rounds"),
        pl.lit(0.0).alias("awp_round_share"),
        pl.lit(0.0).alias("awp_conversion"),
        pl.lit(0, dtype=pl.Int64).alias("awp_opening_picks"),
    )
    if awp_summary is None or awp_summary.height == 0:
        return vazio
    necessarias = {"steamid", "awp_rounds", "engagement_conversion_pct", "opening_picks"}
    if not necessarias.issubset(set(awp_summary.columns)):
        return vazio

    agg = awp_summary.select(
        [
            "steamid",
            pl.col("awp_rounds").cast(pl.Int64),
            pl.col("engagement_conversion_pct").alias("awp_conversion"),
            pl.col("opening_picks").cast(pl.Int64).alias("awp_opening_picks"),
        ]
    )
    return (
        comp.join(agg, on="steamid", how="left")
        .with_columns(
            pl.col("awp_rounds").fill_null(0),
            pl.col("awp_conversion").fill_null(0.0),
            pl.col("awp_opening_picks").fill_null(0),
        )
        .with_columns((pl.col("awp_rounds") / pl.col("rounds_played")).alias("awp_round_share"))
    )


# --- Indices dos papeis -----------------------------------------------------

# Metadados de cada papel: o rotulo que aparece no card e a frase curta que
# explica o que ele significa. O texto e DESCRITIVO em todos, inclusive nos
# criticos (mochila, baiter): o card descreve comportamento, nunca julga a
# pessoa. "Foi mal" não e destaque -- ver `pick_highlight`.
PAPEIS = {
    "carrega_piano": (
        "Carrega piano",
        "assume o custo e o time colhe",
    ),
    "carry": (
        "Carry",
        "leva o time nas costas",
    ),
    "awper": (
        "AWPer",
        "jogou de AWP e produziu com ela",
    ),
    "rei_do_nt": (
        "Rei do NT",
        "chega muito em último vivo e quase não converte",
    ),
    "camper": (
        "Camper",
        "poucas regiões por round, quase não se desloca",
    ),
    "repick": (
        "Repick",
        "reaparece no mesmo ângulo em vez de ocupar espaço",
    ),
    "baiter": (
        "Joga atras da morte alheia",
        "companheiro cai por perto e a troca não vem",
    ),
    "mochila": (
        "Carregado",
        "pouco esforço e pouco impacto no round",
    ),
}


def _percentis(valores, quantis: list[float] | None) -> list[float]:
    """Percentil de cada valor contra a referencia, ou dentro da própria partida."""
    brutos = [None if v is None else float(v) for v in valores]
    if quantis:
        return [percentil(v, quantis) for v in brutos]

    # Sem referencia: posicao dentro da própria partida. E o melhor que da pra
    # fazer, e e pior de proposito -- numa partida em que ninguem se destacou,
    # alguem ainda fica em 1,0. Quem chama avisa.
    validos = sorted(v for v in brutos if v is not None)
    if not validos:
        return [0.0 for _ in brutos]
    return [
        0.0 if v is None else (sum(1 for x in validos if x <= v) / len(validos))
        for v in brutos
    ]


def _media(*colunas: list[float]) -> list[float]:
    return [sum(vals) / len(vals) for vals in zip(*colunas)]


def archetype_indices(
    components: pl.DataFrame, reference: dict | None = None
) -> pl.DataFrame:
    """Um indice por papel para cada jogador, com a evidencia que o sustenta.

    Cada componente bruto vira percentil contra a referencia do conjunto (ver o
    topo do modulo). Os indices sao combinacoes explicitas desses percentis:

    - carrega_piano e baiter: as duas pontas do MESMO eixo, `sacrifice_index`
      (ver PISO_CARREGA_PIANO). O lado positivo são os rounds em que ele pagou
      a conta (entry de T, solo hold de CT, sacrificio de economia) E o time
      colheu; o negativo, as mortes de companheiro por perto sem troca. Nao e
      uma formula de entry -- um jogador pode ser carrega piano a partida
      inteira sem nunca ter sido o primeiro a morrer.
    - carry: fatia de dano, fatia de kills, multikills e clutches convertidos.
    - mochila: esforco baixo E impacto baixo, como produto dos dois complementos.
    - rei_do_nt: muitas tentativas de ultimo vivo, producao alta dentro delas e
      conversao baixa. So existe acima de MIN_CLUTCH_ATTEMPTS.
    - camper: poucas regioes distintas E pouco deslocamento, como produto.
    - repick: fracao de engajamentos com a assinatura de jiggle.
    - awper: fatia de rounds com AWP vezes o que produziu com ela. So existe
      acima de MIN_AWP_ROUNDS.
    """
    if components.height == 0:
        return components

    quantis = (reference or {}).get("quantis", {})
    pct = {
        nome: _percentis(components[nome].to_list(), quantis.get(nome))
        for nome in COMPONENTES
        if nome in components.columns
    }

    zeros = [0.0] * components.height

    def p(nome: str) -> list[float]:
        return pct.get(nome, zeros)

    esforco = _media(
        p("first_contact_share"), p("util_per_round"),
        p("frac_entering_fight"), p("death_rate"),
    )
    impacto = _media(p("damage_share"), p("kill_share"))

    # O carrega piano soma as tres formas ANTES do percentil: as tres são a
    # mesma moeda (fracao de rounds em que ele pagou e o time colheu), então
    # somar em unidade crua e legitimo e preserva quem faz um pouco de cada.
    piano_bruto = [
        a + b + c
        for a, b, c in zip(
            components["piano_t_share"].to_list(),
            components["piano_ct_share"].to_list(),
            components["piano_eco_share"].to_list(),
        )
    ]
    # Eixo único carrega piano <-> baiter (ver PISO_CARREGA_PIANO). Cada ponta só
    # recebe índice além do próprio piso, então os dois rótulos nunca caem no
    # mesmo jogador -- por construção, não por desempate.
    eixo = [s - b for s, b in zip(p("sacrificio_share"), p("isca_relativa"))]
    piano = [e if e >= PISO_CARREGA_PIANO else 0.0 for e in eixo]
    baiter = [-e if e <= PISO_BAITER else 0.0 for e in eixo]

    carry = _media(p("damage_share"), p("kill_share"), p("multikill_rounds"), p("clutch_wins"))
    mochila = [(1 - e) * (1 - i) for e, i in zip(esforco, impacto)]
    camper = [
        (1 - d) * (1 - c)
        for d, c in zip(p("distinct_places_mean"), p("path_per_round"))
    ]

    # Rei do NT: muitas tentativas PONDERADAS PELO X, produção alta dentro delas,
    # e a fração do peso que foi perdida. Um 1v1 perdido quase não move o índice;
    # um 1v3 perdido move três vezes mais (peso pelo X, ver o topo do módulo).
    tentativas = components["clutch_attempts"].to_list()
    peso = components["clutch_peso"].to_list() if "clutch_peso" in components.columns else [0.0] * components.height
    perdido = (components["clutch_peso_perdido"].to_list()
               if "clutch_peso_perdido" in components.columns else [0.0] * components.height)
    rei_nt = [
        0.0 if t < MIN_CLUTCH_ATTEMPTS or not w else a * d * (pp / w)
        for t, w, pp, a, d in zip(tentativas, peso, perdido, p("clutch_peso"), p("clutch_damage_per_attempt"))
    ]

    awp_rounds = components["awp_rounds"].to_list()
    produz = _media(p("awp_conversion"), p("awp_opening_picks"))
    awper = [
        0.0 if r < MIN_AWP_ROUNDS else s * q
        for r, s, q in zip(awp_rounds, p("awp_round_share"), produz)
    ]

    return components.with_columns(
        pl.Series("piano_total_share", piano_bruto),
        pl.Series("sacrifice_index", eixo),
        pl.Series("effort_pct", esforco),
        pl.Series("impact_pct", impacto),
        pl.Series("idx_carrega_piano", piano),
        pl.Series("idx_carry", carry),
        pl.Series("idx_mochila", mochila),
        pl.Series("idx_camper", camper),
        pl.Series("idx_repick", p("repick_share")),
        pl.Series("idx_baiter", baiter),
        pl.Series("idx_rei_do_nt", rei_nt),
        pl.Series("idx_awper", awper),
    )


def piano_form(row: dict) -> str | None:
    """Qual das tres formas do carrega piano pesou mais para este jogador.

    Existe porque o card precisa dizer COMO ele pagou a conta: entrar e morrer
    abrindo espaco, segurar bomb sozinho, ou abrir mao de arma. Sem isso o
    rotulo vira generico e o leitor nao consegue conferir no replay.
    """
    formas = {
        "entrada": row.get("piano_t_share") or 0.0,
        "solo no bomb": row.get("piano_ct_share") or 0.0,
        "economia": row.get("piano_eco_share") or 0.0,
    }
    maior = max(formas, key=lambda k: formas[k])
    return maior if formas[maior] > 0 else None


def _plural(n: float, singular: str, plural: str) -> str:
    """"1 round" e "3 rounds". Detalhe pequeno que denuncia texto gerado."""
    n = int(n)
    return f"{n} {singular if n == 1 else plural}"


def evidencia(papel: str, row: dict) -> str:
    """Frase curta de evidência, só com o que existe naquela partida.

    Regra do projeto: campo que não existe some da frase. Uma frase curta e
    verdadeira vale mais que uma completa e inventada.

    Papel sem sustentação nenhuma devolve string VAZIA, e não uma frase com
    zeros. "AWP na mão em 0 rounds" descreve a ausência do papel como se fosse o
    papel -- foi o que uma varredura das 720 frases possíveis (8 papéis x 90
    jogador-partidas) encontrou em 74 casos. Hoje eles não chegam à tela porque
    `pick_highlight` ignora índice zero, mas a frase não pode depender disso.
    """
    pedacos: list[str] = []

    if papel == "carrega_piano":
        forma = piano_form(row)
        if forma is None:
            return ""
        if forma == "entrada":
            pedacos.append(
                "abriu o contato do time e morreu em "
                + _plural(row["piano_t_rounds"], "round convertido", "rounds convertidos")
            )
        elif forma == "solo no bomb":
            pedacos.append(
                "segurou bomb sozinho e caiu em "
                + _plural(row["piano_ct_rounds"], "round que o time ganhou",
                          "rounds que o time ganhou")
            )
        elif forma == "economia":
            pedacos.append(
                "jogou "
                + _plural(row["eco_sacrifice_rounds"], "round", "rounds")
                + " com menos equipamento que o time"
            )
        # o retorno é o que separa carrega piano de quem só morreu cedo
        if row.get("pagou_rounds"):
            pedacos.append(f"o time colheu em {int(row.get('sacrificio_rounds') or 0)} dos "
                           + _plural(row["pagou_rounds"], "round em que ele pagou", "rounds em que ele pagou"))
        if row.get("traded_death_share"):
            pedacos.append(f"{row['traded_death_share'] * 100:.0f}% das mortes dele foram trocadas")

    elif papel == "carry":
        pedacos.append(f"{row['damage_share'] * 100:.0f}% do dano do time")
        if row.get("multikill_rounds"):
            pedacos.append(_plural(row["multikill_rounds"], "round de multikill",
                                   "rounds de multikill"))
        if row.get("clutch_wins"):
            pedacos.append(_plural(row["clutch_wins"], "clutch fechado", "clutches fechados"))

    elif papel == "awper":
        if not row.get("awp_rounds"):
            return ""
        pedacos.append("AWP na mão em " + _plural(row["awp_rounds"], "round", "rounds"))
        if row.get("awp_conversion"):
            pedacos.append(f"{row['awp_conversion']:.0f}% de conversão na primeira briga")
        if row.get("awp_opening_picks"):
            pedacos.append(_plural(row["awp_opening_picks"], "pick de abertura",
                                   "picks de abertura"))

    elif papel == "rei_do_nt":
        if not row.get("clutch_attempts"):
            return ""
        # contagem e conversão SEMPRE juntas; a quebra por X quando existe
        pedacos.append("ficou por último " + _plural(row["clutch_attempts"], "vez", "vezes")
                       + f", {_plural(row['clutch_wins'], 'convertida', 'convertidas')}"
                       + f" ({row['clutch_wins'] / row['clutch_attempts'] * 100:.0f}%)")
        if row.get("clutch_por_x"):
            pedacos.append(row["clutch_por_x"])
        if row.get("clutch_damage_per_attempt"):
            pedacos.append(f"média de {row['clutch_damage_per_attempt']:.0f} de dano em cada")

    elif papel == "camper":
        pedacos.append(f"{row['distinct_places_mean']:.1f} regiões por round")
        pedacos.append(f"{row['path_per_round']:.0f}u percorridas")

    elif papel == "repick":
        if not row.get("repick_share"):
            return ""
        pedacos.append(f"{row['repick_share'] * 100:.0f}% dos engajamentos saindo e voltando")
        if row.get("engagements"):
            pedacos.append("em " + _plural(row["engagements"], "briga", "brigas"))

    elif papel == "baiter":
        if not row.get("bait_opportunities"):
            return ""
        # A frase conta o que aconteceu, sem adjetivo: quantas vezes um
        # companheiro caiu perto dele sem a troca vir, e o que ele tirou disso.
        pedacos.append(
            _plural(row["bait_opportunities"], "morte de companheiro", "mortes de companheiro")
            + f" a menos de {BAIT_MAX_DISTANCE:.0f}u dele"
        )
        pedacos.append(f"sobreviveu a {row['survival_rate'] * 100:.0f}% dos rounds")
        if row.get("bait_return_per_opp") is not None:
            pedacos.append(f"{row['bait_return_per_opp']:.1f} kill por situação")

    elif papel == "mochila":
        pedacos.append(f"{row['damage_share'] * 100:.0f}% do dano do time")
        pedacos.append(f"sobreviveu a {row['survival_rate'] * 100:.0f}% dos rounds")

    return ", ".join(p for p in pedacos if p)


# Papeis que descrevem o jogador por baixo. Nao são proibidos no card de
# destaque -- um mochila extremo E o retrato daquela partida -- mas so entram
# quando o indice e alto de verdade, porque "foi mal" não e destaque.
PAPEIS_CRITICOS = ("mochila", "baiter", "rei_do_nt")

# O quanto um papel critico precisa estar acima do normal para virar destaque.
# 0,85 = entre os 15% mais marcantes daquele papel no conjunto das partidas.
LIMIAR_CRITICO = 0.85


def pick_highlight(
    indices: pl.DataFrame,
    excluir_steamid: int | None = None,
    excluir_papeis: tuple[str, ...] = ("carry",),
) -> dict | None:
    """Escolhe quem vai no card da direita: o jogador que exemplifica um papel
    com MAIS FORCA, comparado ao que e normal naquele papel.

    O criterio e o proprio indice, porque ele ja e um percentil contra a
    distribuicao do conjunto -- 0,9 em camper e 0,9 em AWPer querem dizer a
    mesma coisa ("entre os 10% mais marcantes naquele papel"), e por isso podem
    competir na mesma escala. NAO ha ordem de preferencia entre papeis: se o
    carrega piano da partida foi mediano e teve um AWPer dominante, ganha o
    AWPer.

    `excluir_steamid` tira quem ja aparece no card da esquerda, e
    `excluir_papeis` tira o PAPEL daquele card -- sem isso os dois destaques da
    partida saem como "carry" e a aba conta a mesma coisa duas vezes.
    """
    candidatos = []
    for row in indices.iter_rows(named=True):
        if excluir_steamid is not None and row["steamid"] == excluir_steamid:
            continue
        for papel in PAPEIS:
            if papel in excluir_papeis:
                continue
            valor = row.get(f"idx_{papel}") or 0.0
            if valor <= 0:
                continue
            if papel in PAPEIS_CRITICOS and valor < LIMIAR_CRITICO:
                continue
            candidatos.append(
                {
                    "steamid": row["steamid"],
                    "name": row["name"],
                    "team": row["team"],
                    "role": papel,
                    "label": PAPEIS[papel][0],
                    "meaning": PAPEIS[papel][1],
                    "index": float(valor),
                    "evidence": evidencia(papel, row),
                }
            )

    if not candidatos:
        return None
    return max(candidatos, key=lambda c: c["index"])


# --- Orquestracao -----------------------------------------------------------

def engagement_ticks(kills: pl.DataFrame) -> pl.DataFrame:
    """Brigas resolvidas em que cada jogador esteve: as que ele matou e as que morreu.

    Usar kills (e nao a tabela de tiros) mantem o custo baixo e cobre os dois
    lados do duelo. Usar so as kills dele enviesaria o repick para as vezes em
    que o jiggle deu certo.
    """
    def lado(col: str) -> pl.DataFrame:
        return kills.select(
            pl.col("round_num").cast(pl.UInt32),
            pl.col(col).alias("steamid"),
            pl.col("tick").alias("engagement_tick"),
        )

    return (
        pl.concat([lado("attacker_steamid"), lado("victim_steamid")])
        .filter(pl.col("steamid").is_not_null())
        .unique()
        .sort(["round_num", "engagement_tick"])
    )


def compute_for_match(
    tables: dict,
    outputs: dict,
    positions: pl.DataFrame,
    player_areas: pl.DataFrame,
    team_of: dict[int, str],
    winner_team_of_round: dict[int, str],
    tickrate: int = 64,
    reference: dict | None = None,
) -> tuple[pl.DataFrame, pl.DataFrame]:
    """Monta todos os papeis de uma partida. Devolve (per_round, summary).

    Existe para o pipeline (scripts/process_demo.py) e o ajuste da referencia
    (scripts/fit_archetype_reference.py) rodarem exatamente o mesmo caminho --
    referencia ajustada por um caminho diferente do que a gera seria uma escala
    que nao corresponde ao que o painel mostra.
    """
    from metrics.awp_metrics import classify_engagement_style
    from metrics.clutch import add_damage_in_clutch, clutch_situations

    ticks, kills, rounds = tables["ticks"], tables["kills"], tables["rounds"]

    facts = round_facts(outputs["cluster_features"], outputs["grenades_per_round"], rounds, positions)
    eco = economy_signals(ticks, rounds)
    solo = solo_hold_signals(player_areas)
    bait = bait_events(kills, ticks, team_of, tickrate=tickrate)

    styles = classify_engagement_style(engagement_ticks(kills), ticks, tickrate=tickrate)
    repick = marca_repick(styles, ticks, kills, tables.get("damages"), tables.get("shots"), tickrate)

    clutch_round, _ = clutch_situations(kills, rounds, team_of, winner_team_of_round)
    clutch_round = add_damage_in_clutch(clutch_round, tables["damages"], team_of)

    flash = flash_convertida(tables.get("player_blind"), kills, tickrate=tickrate)

    per_round, comp = player_components(
        facts, eco, solo, bait, repick, clutch_round, outputs.get("awp_summary"), team_of, flash,
        funcoes_round=outputs.get("structural_roles"),
        isca_por_funcao=(reference or {}).get("isca_por_funcao"),
    )
    summary = archetype_indices(comp, reference)
    return per_round, summary


def build_reference(componentes: pl.DataFrame, n_quantis: int = 100) -> dict:
    """Quantis de cada componente no conjunto das partidas.

    Guarda os quantis e nao a amostra inteira: o arquivo fica pequeno e legivel
    no diff, e o percentil sai de uma busca binaria. `piano_total_share` entra
    junto porque o indice de carrega piano e calculado sobre a soma das tres
    formas, nao sobre cada uma.
    """
    quantis: dict[str, list[float]] = {}
    alvos = [c for c in (*COMPONENTES, "piano_total_share") if c in componentes.columns]
    passos = [i / n_quantis for i in range(1, n_quantis + 1)]

    for nome in alvos:
        serie = componentes[nome].drop_nulls()
        if serie.len() == 0:
            continue
        quantis[nome] = [float(serie.quantile(q) or 0.0) for q in passos]

    return {
        "versao": 1,
        "n_jogador_partidas": int(componentes.height),
        "quantis": quantis,
    }
