"""
Perfil do jogador: a frequência de cada comportamento nos rounds DELE.

Por que este módulo existe, e por que ele não é o clustering:

O agrupamento de estilos (clustering/playstyle.py) responde "que tipos de round
existem". As médias que ele produz — "distância média do time 1.100u", "8 regiões
distintas" — descrevem um GRUPO DE ROUNDS e não pertencem a jogador nenhum, porque
os rounds de um mesmo jogador se espalham por todos os grupos (medido: todo jogador
visita 3 ou 4 dos 4 grupos numa única partida).

Aqui o mesmo dado é olhado pelo outro eixo: por jogador, em que fração dos rounds
dele cada comportamento aconteceu. "Puxa AWP em 40% dos rounds", "joga longe do
time em 60%". Isso é perfil: compara jogador com jogador e é o insumo natural do
sistema de funções.

Três regras que o módulo inteiro respeita, porque sem elas a tabela vira ruído:

1. **Toda taxa vem com o bruto.** Cada métrica devolve `<nome>` (a taxa),
   `<nome>_n` (numerador) e `<nome>_d` (denominador). Com 22 rounds, 41% e 50%
   são o mesmo número na prática, e mostrar só o percentual inventa precisão.

2. **Toda taxa vem com referência.** `<nome>_ref` é a mediana dos OUTROS
   jogadores da partida. "60% longe do time" não diz nada sozinho; contra uma
   mediana de 55% diz que é normal, contra 20% diz que é o retrato do jogador.

3. **Amostra pequena não vira conclusão.** `<nome>_fraco` marca a célula quando
   o denominador não sustenta uma taxa. Vale principalmente para clutch e
   abertura de AWP, que têm poucos eventos por partida.

E uma quarta, específica de CS: **lado importa**. Distância do time, ancoragem e
contato cedo mudam muito entre CT e TR. As métricas sensíveis a isso saem também
em versão `_ct` e `_t`, e a referência delas é calculada dentro do lado.

Convenção do projeto: devolve `(per_match, summary)` — uma linha por
(jogador, partida) e o acumulado do jogador em todas as partidas processadas. A
tabela round a round, que é onde a validação manual acontece, sai por
`round_flags()`.
"""
from __future__ import annotations

import polars as pl

from metrics.timing import detect_tickrate

# --- Limiares de calibração -------------------------------------------------

# Raio dentro do qual um companheiro conta como "por perto". 600 unidades é o
# alcance em que dois jogadores ainda se apoiam: dá para trocar a morte do outro
# dentro da janela de 5s e para cobrir o mesmo ângulo. Acima disso cada um está
# jogando o próprio duelo, que é o que "isolado" quer dizer.
RAIO_COMPANHEIRO = 600.0

# Fração do round vivo que o jogador precisa passar sem companheiro no raio para
# o round contar como isolado. Metade é o mínimo honesto: quem ficou sozinho em
# 3 de 10 amostras estava de passagem, não jogando separado.
FRACAO_ISOLAMENTO = 0.50

# Ancorado: ficou num lugar só. Duas condições, porque cada uma sozinha erra —
# poucas regiões também acontece em round curto, e deslocamento líquido baixo
# também acontece em quem sai e volta (jiggle). Os valores saem da distribuição
# real: a mediana é 5,1 regiões e ~490u de deslocamento líquido.
MAX_REGIOES_ANCORADO = 4
MAX_DESLOCAMENTO_ANCORADO = 400.0

# Rotacionando: o oposto. 7+ regiões é o quartil de cima da distribuição.
MIN_REGIOES_ROTACIONANDO = 7

# Contato cedo: quantos segundos depois do fim do freeze time. 15s é o tempo de
# uma execução chegar ao site na maioria dos mapas; contato antes disso é
# abertura ou peek de informação, não o meio do round.
SEGUNDOS_CONTATO_CEDO = 15.0

# Janela de trade, a mesma das métricas básicas do projeto.
JANELA_TRADE_S = 5.0

# Fração do time que precisa estar de rifle para a arma pior de um jogador
# contar como economia sacrificada. Abaixo disso é eco do time inteiro.
FRACAO_TIME_DE_RIFLE = 0.60

# Rounds mínimos para uma taxa por round ser exibida como taxa. Abaixo disso a
# interface mostra o bruto e marca amostra fraca. 8 rounds é o ponto em que um
# evento a mais ou a menos deixa de mover a taxa em mais de 12 pontos.
MIN_ROUNDS_PARA_TAXA = 8

# Eventos mínimos para taxas cujo denominador não é "rounds jogados" (kills de
# AWP, mortes trocadas, conversão de clutch). 4 é baixo de propósito: clutch tem
# ~2 tentativas por jogador por partida, e o piso existe para marcar a célula,
# não para escondê-la.
MIN_EVENTOS_PARA_TAXA = 4

# O que conta como cada classe de arma. Nomes de exibição, como vêm no demo em
# `active_weapon_name` ("AK-47", não "ak47"); a tabela de kills usa o codinome
# minúsculo ("awp"), e por isso as duas listas existem.
RIFLES = {"AK-47", "M4A1-S", "M4A4", "Galil AR", "FAMAS", "AUG", "SG 553",
          "AWP", "SSG 08", "SCAR-20", "G3SG1"}
SMGS = {"MP9", "MAC-10", "MP5-SD", "UMP-45", "P90", "MP7", "PP-Bizon"}
PISTOLAS = {"Glock-18", "USP-S", "P2000", "P250", "Five-SeveN", "Tec-9",
            "CZ75-Auto", "Dual Berettas", "Desert Eagle", "R8 Revolver"}
AWP_NO_DEMO = "AWP"
AWP_NA_TABELA_DE_KILLS = "awp"

# Round em que os lados trocam (MR12).
HALFTIME_ROUND = 12


# --- Blocos de fato por round -----------------------------------------------

def distancia_do_companheiro_mais_proximo(positions: pl.DataFrame) -> pl.DataFrame:
    """Por (round, jogador): distância média ao companheiro MAIS PRÓXIMO e o
    quanto do round ele passou sem ninguém no raio.

    Não é a distância ao centro de massa do time, que é o que
    `positioning.player_position_profile` mede. A diferença importa: num time
    espalhado em três frentes, todo mundo fica longe do centroide sem que
    ninguém esteja sozinho. Para "isolado" o que vale é o vizinho mais próximo.
    """
    a = positions.select(["round_num", "tick", "side", "steamid", "X", "Y"])
    b = a.select(
        ["round_num", "tick", "side",
         pl.col("steamid").alias("outro"), pl.col("X").alias("ox"), pl.col("Y").alias("oy")]
    )

    pares = a.join(b, on=["round_num", "tick", "side"], how="inner").filter(
        pl.col("steamid") != pl.col("outro")
    )
    if pares.height == 0:
        return pl.DataFrame(
            schema={"round_num": pl.UInt32, "steamid": pl.UInt64,
                    "dist_vizinho_media": pl.Float64, "frac_tempo_isolado": pl.Float64}
        )

    por_tick = (
        pares.with_columns(
            (((pl.col("X") - pl.col("ox")) ** 2 + (pl.col("Y") - pl.col("oy")) ** 2).sqrt())
            .alias("d")
        )
        .group_by(["round_num", "tick", "steamid"])
        .agg(pl.col("d").min().alias("dist_vizinho"))
    )

    return (
        por_tick.group_by(["round_num", "steamid"])
        .agg(
            pl.col("dist_vizinho").mean().alias("dist_vizinho_media"),
            (pl.col("dist_vizinho") > RAIO_COMPANHEIRO).mean().alias("frac_tempo_isolado"),
        )
        .sort(["round_num", "steamid"])
    )


def deslocamento_no_round(positions: pl.DataFrame) -> pl.DataFrame:
    """Deslocamento LÍQUIDO (início ao fim) e número de regiões distintas.

    O líquido, e não a distância percorrida, é o que separa "ficou num lugar só"
    de "saiu e voltou" — mesma escolha da classificação peek/hold (decisão 1 do
    CLAUDE.md).
    """
    ordenado = positions.sort(["round_num", "steamid", "tick"])
    extremos = ordenado.group_by(["round_num", "steamid"]).agg(
        pl.col("X").first().alias("x0"), pl.col("Y").first().alias("y0"),
        pl.col("X").last().alias("x1"), pl.col("Y").last().alias("y1"),
        pl.col("place").n_unique().alias("regioes"),
    )
    return extremos.with_columns(
        (((pl.col("x1") - pl.col("x0")) ** 2 + (pl.col("y1") - pl.col("y0")) ** 2).sqrt())
        .alias("deslocamento_liquido")
    ).select(["round_num", "steamid", "deslocamento_liquido", "regioes"])


def fatos_de_arma(ticks: pl.DataFrame, kills: pl.DataFrame) -> pl.DataFrame:
    """Por (round, jogador): teve AWP na mão, arma primária e economia sacrificada."""
    vivos = ticks.filter(pl.col("is_alive"))

    teve_awp = (
        vivos.filter(pl.col("active_weapon_name") == AWP_NO_DEMO)
        .select(["round_num", "steamid"])
        .unique()
        .with_columns(pl.lit(True).alias("teve_awp"))
    )

    # A arma primária é a mais EMPUNHADA no round: no fim do freeze time o
    # jogador costuma estar com a faca, e olhar aquele instante classifica errado.
    primaria = (
        vivos.filter(pl.col("active_weapon_name").is_in(list(RIFLES | SMGS | PISTOLAS)))
        .group_by(["round_num", "steamid", "side", "active_weapon_name"])
        .len()
        .sort("len", descending=True)
        .group_by(["round_num", "steamid"], maintain_order=True)
        .first()
        .select(["round_num", "steamid", "side",
                 pl.col("active_weapon_name").alias("arma_primaria")])
    )

    primaria = primaria.with_columns(
        pl.col("arma_primaria").is_in(list(RIFLES)).alias("de_rifle"),
        pl.col("arma_primaria").is_in(list(SMGS | PISTOLAS)).alias("de_smg_ou_pistola"),
    ).with_columns(
        pl.col("de_rifle").mean().over(["round_num", "side"]).alias("frac_time_de_rifle")
    ).with_columns(
        (
            pl.col("de_smg_ou_pistola")
            & (pl.col("frac_time_de_rifle") >= FRACAO_TIME_DE_RIFLE)
        ).alias("arma_pior_que_o_time")
    )

    # Abertura de AWP: a primeira kill do round foi dele, de AWP.
    primeira_kill = (
        kills.sort("tick")
        .group_by("round_num")
        .first()
        .select(
            pl.col("round_num").cast(pl.UInt32),
            pl.col("attacker_steamid").alias("steamid"),
            pl.col("weapon").alias("arma_da_abertura"),
        )
        .filter(pl.col("steamid").is_not_null())
        .with_columns(
            (pl.col("arma_da_abertura").str.to_lowercase() == AWP_NA_TABELA_DE_KILLS)
            .alias("abertura_de_awp")
        )
        .select(["round_num", "steamid", "abertura_de_awp"])
    )

    return (
        primaria.join(teve_awp, on=["round_num", "steamid"], how="left")
        .join(primeira_kill, on=["round_num", "steamid"], how="left")
        .with_columns(
            pl.col("teve_awp").fill_null(False),
            pl.col("abertura_de_awp").fill_null(False),
        )
    )


def fatos_de_contato(features: pl.DataFrame, tickrate: int) -> pl.DataFrame:
    """Por (round, jogador): contato cedo, contato tarde e quem abriu pro time.

    `contato_tarde` inclui quem NÃO teve contato nenhum: o round em que o jogador
    não encostou no adversário é a forma extrema de encostar depois do time, e
    jogá-lo fora faria a taxa descrever só os rounds em que ele brigou.
    """
    base = features.select(
        ["round_num", "steamid", "side", "time_of_first_contact_s"]
    ).with_columns(pl.col("round_num").cast(pl.UInt32))

    com_posto = base.with_columns(
        pl.col("time_of_first_contact_s").rank("min").over(["round_num", "side"]).alias("posto"),
        pl.col("time_of_first_contact_s").min().over(["round_num", "side"]).alias("primeiro_do_time"),
    ).with_columns(
        # Empate no primeiro lugar não é abertura de ninguém: acontece quando uma
        # granada pega vários do time no mesmo tick (decisão 17 do CLAUDE.md).
        pl.col("posto").eq(1).sum().over(["round_num", "side"]).alias("empatados")
    )

    return com_posto.with_columns(
        (
            pl.col("time_of_first_contact_s").is_not_null()
            & (pl.col("time_of_first_contact_s") <= SEGUNDOS_CONTATO_CEDO)
        ).alias("contato_cedo"),
        (
            pl.col("time_of_first_contact_s").is_null()
            | (pl.col("time_of_first_contact_s") > pl.col("primeiro_do_time"))
        ).alias("contato_tarde"),
        (
            (pl.col("posto") == 1)
            & (pl.col("empatados") == 1)
            & pl.col("time_of_first_contact_s").is_not_null()
        ).alias("primeiro_contato_do_time"),
    ).select(
        ["round_num", "steamid", "side", "time_of_first_contact_s",
         "contato_cedo", "contato_tarde", "primeiro_contato_do_time"]
    )


def area_diferente_do_time(player_areas: pl.DataFrame) -> pl.DataFrame:
    """Por (round, jogador): ele estava numa área diferente da maioria do time.

    A maioria é calculada sobre o RESTO do time, não sobre o time inteiro: se o
    próprio jogador entra na conta, num round dividido ele puxa a maioria para si
    e a métrica se esconde.
    """
    vazio = pl.DataFrame(
        schema={"round_num": pl.UInt32, "steamid": pl.UInt64, "area_diferente": pl.Boolean}
    )
    if player_areas.height == 0 or "area" not in player_areas.columns:
        return vazio

    base = player_areas.select(["round_num", "steamid", "side", "area"])
    companheiros = base.join(
        base.select(
            ["round_num", "side",
             pl.col("steamid").alias("outro"), pl.col("area").alias("area_outro")]
        ),
        on=["round_num", "side"],
        how="inner",
    ).filter(pl.col("steamid") != pl.col("outro"))

    if companheiros.height == 0:
        return vazio

    contagem = companheiros.group_by(["round_num", "steamid", "area_outro"]).agg(
        pl.len().alias("n")
    )
    maioria = (
        contagem.with_columns(
            pl.col("n").max().over(["round_num", "steamid"]).alias("maior"),
            pl.len().over(["round_num", "steamid", "n"]).alias("empatados"),
        )
        .filter(pl.col("n") == pl.col("maior"))
        # Empate no resto do time = o time não se juntou em lugar nenhum, e aí
        # "diferente do time" não quer dizer nada. O round sai da conta.
        .with_columns(
            pl.when(pl.col("empatados") > 1).then(None).otherwise(pl.col("area_outro")).alias("area_time")
        )
        .select(["round_num", "steamid", "area_time"])
        .unique(subset=["round_num", "steamid"])
    )

    return (
        base.join(maioria, on=["round_num", "steamid"], how="left")
        .with_columns(
            pl.when(pl.col("area_time").is_null())
            .then(False)
            .otherwise(pl.col("area") != pl.col("area_time"))
            .alias("area_diferente")
        )
        .select(["round_num", "steamid", "area_diferente"])
    )


def round_flags(
    features: pl.DataFrame,
    positions: pl.DataFrame,
    ticks: pl.DataFrame,
    kills: pl.DataFrame,
    player_areas: pl.DataFrame,
    clutch_round: pl.DataFrame,
    tickrate: int,
) -> pl.DataFrame:
    """Uma linha por (round, jogador) com um booleano por comportamento.

    É a tabela onde a validação manual acontece: uma taxa de 41% não diz QUAIS
    rounds entraram na conta, e é olhando estes 22 booleanos que dá para
    discordar dela.
    """
    vizinho = distancia_do_companheiro_mais_proximo(positions)
    desloc = deslocamento_no_round(positions)
    armas = fatos_de_arma(ticks, kills)
    contato = fatos_de_contato(features, tickrate)
    areas = area_diferente_do_time(player_areas)

    base = features.select(
        ["round_num", "steamid", "name", "side", "survived", "was_traded", "trade_kills"]
    ).with_columns(
        pl.col("round_num").cast(pl.UInt32),
        pl.col("survived").cast(pl.Boolean),
        pl.col("was_traded").cast(pl.Boolean),
    )

    kills_no_round = (
        kills.select(
            pl.col("round_num").cast(pl.UInt32),
            pl.col("attacker_steamid").alias("steamid"),
            pl.col("weapon").str.to_lowercase().alias("arma"),
        )
        .filter(pl.col("steamid").is_not_null())
        .group_by(["round_num", "steamid"])
        .agg(
            pl.len().alias("kills_no_round"),
            (pl.col("arma") == AWP_NA_TABELA_DE_KILLS).sum().alias("kills_de_awp_no_round"),
        )
    )

    # Assistências: a coluna existe no demo e o projeto nunca tinha usado. Sem
    # ela o painel mostrava kills e mortes e deixava um terço do K/A/D de fora.
    assists_no_round = (
        kills.select(
            pl.col("round_num").cast(pl.UInt32),
            pl.col("assister_steamid").alias("steamid"),
        )
        .filter(pl.col("steamid").is_not_null())
        .group_by(["round_num", "steamid"])
        .agg(pl.len().alias("assists_no_round"))
        if "assister_steamid" in kills.columns
        else pl.DataFrame(schema={"round_num": pl.UInt32, "steamid": pl.UInt64,
                                  "assists_no_round": pl.UInt32})
    )

    clutch = (
        clutch_round.select(["round_num", "steamid", "won"])
        .with_columns(pl.col("round_num").cast(pl.UInt32), pl.lit(True).alias("em_clutch"))
        .rename({"won": "clutch_convertido"})
        if clutch_round.height
        else pl.DataFrame(
            schema={"round_num": pl.UInt32, "steamid": pl.UInt64,
                    "clutch_convertido": pl.Boolean, "em_clutch": pl.Boolean}
        )
    )

    flags = (
        base.join(vizinho, on=["round_num", "steamid"], how="left")
        .join(desloc, on=["round_num", "steamid"], how="left")
        .join(armas.drop("side"), on=["round_num", "steamid"], how="left")
        .join(contato.drop("side"), on=["round_num", "steamid"], how="left")
        .join(areas, on=["round_num", "steamid"], how="left")
        .join(kills_no_round, on=["round_num", "steamid"], how="left")
        .join(assists_no_round, on=["round_num", "steamid"], how="left")
        .join(clutch, on=["round_num", "steamid"], how="left")
        .with_columns(
            pl.col("kills_no_round").fill_null(0),
            pl.col("assists_no_round").fill_null(0),
            pl.col("kills_de_awp_no_round").fill_null(0),
            pl.col("em_clutch").fill_null(False),
            pl.col("clutch_convertido").fill_null(False),
            pl.col("teve_awp").fill_null(False),
            pl.col("abertura_de_awp").fill_null(False),
            pl.col("arma_pior_que_o_time").fill_null(False),
            pl.col("area_diferente").fill_null(False),
            pl.col("frac_tempo_isolado").fill_null(0.0),
        )
    )

    # "Longe do time" é relativo à PARTIDA e ao LADO: CT e TR têm distâncias
    # naturalmente diferentes, e um limiar fixo em unidades classificaria o lado
    # inteiro de um jeito só.
    #
    # Mas a mediana SOZINHA não serve, e um teste sintético pegou isso: corte na
    # mediana marca metade dos rounds como "longe" por construção, inclusive num
    # time em que todo mundo joga colado -- basta ser marginalmente menos colado
    # que os outros. Por isso vale também o piso absoluto: com um companheiro
    # dentro do raio de apoio, o jogador não está jogando longe do time em
    # leitura nenhuma. É o mesmo desenho dos pisos de função (liderar o recorte E
    # passar de um mínimo).
    flags = flags.with_columns(
        pl.col("dist_vizinho_media").median().over("side").alias("mediana_do_lado")
    ).with_columns(
        (
            (pl.col("dist_vizinho_media") > pl.col("mediana_do_lado"))
            & (pl.col("dist_vizinho_media") > RAIO_COMPANHEIRO)
        ).fill_null(False).alias("longe_do_time"),
        (pl.col("frac_tempo_isolado") >= FRACAO_ISOLAMENTO).alias("isolado"),
        (
            (pl.col("regioes") <= MAX_REGIOES_ANCORADO)
            & (pl.col("deslocamento_liquido") <= MAX_DESLOCAMENTO_ANCORADO)
        ).fill_null(False).alias("ancorado"),
        (pl.col("regioes") >= MIN_REGIOES_ROTACIONANDO).fill_null(False).alias("rotacionando"),
        (~pl.col("survived")).alias("morreu"),
        (pl.col("trade_kills").fill_null(0) > 0).alias("fez_trade_kill"),
    )

    # Lurk é a CONJUNÇÃO das três, não qualquer uma sozinha: ficar isolado num
    # round de retake não é lurk, encostar tarde por ter nascido longe não é
    # lurk, e estar noutra área porque rotacionou também não. Lurk é jogar outra
    # parte do mapa, sozinho, chegando ao contato depois do time.
    return flags.with_columns(
        (pl.col("isolado") & pl.col("contato_tarde") & pl.col("area_diferente")).alias("lurk")
    ).sort(["steamid", "round_num"])


# --- Agregação por jogador --------------------------------------------------

# Cada entrada: (chave da taxa, coluna booleana, se a taxa sai também por lado).
# A lista é a fonte da verdade: métrica nova entra aqui e aparece sozinha na
# tabela, na referência e na marca de amostra fraca.
TAXAS_POR_ROUND = [
    ("pct_rounds_longe_do_time", "longe_do_time", True),
    ("pct_rounds_isolado", "isolado", True),
    ("pct_rounds_ancorado", "ancorado", True),
    ("pct_rounds_rotacionando", "rotacionando", True),
    ("pct_rounds_com_awp", "teve_awp", False),
    ("pct_rounds_abertura_awp", "abertura_de_awp", False),
    ("pct_rounds_smg_ou_pistola_com_time_de_rifle", "arma_pior_que_o_time", False),
    ("pct_rounds_contato_cedo", "contato_cedo", True),
    ("pct_rounds_contato_tarde", "contato_tarde", True),
    ("pct_rounds_primeiro_contato_do_time", "primeiro_contato_do_time", True),
    ("pct_rounds_sobreviveu", "survived", False),
    ("pct_rounds_trade_kill", "fez_trade_kill", False),
    ("pct_rounds_em_clutch", "em_clutch", False),
    ("pct_rounds_lurk", "lurk", False),
]

CATEGORIAS = {
    "Posicionamento": ["pct_rounds_longe_do_time", "pct_rounds_isolado",
                       "pct_rounds_ancorado", "pct_rounds_rotacionando"],
    "Arma e abertura": ["pct_rounds_com_awp", "pct_kills_de_awp",
                        "pct_rounds_abertura_awp",
                        "pct_rounds_smg_ou_pistola_com_time_de_rifle"],
    "Tempo e contato": ["pct_rounds_contato_cedo", "pct_rounds_contato_tarde",
                        "pct_rounds_primeiro_contato_do_time", "tempo_mediano_ate_contato_s"],
    "Resultado e trade": ["pct_rounds_sobreviveu", "pct_mortes_trocadas",
                          "pct_rounds_trade_kill", "pct_rounds_em_clutch",
                          "taxa_conversao_clutch"],
    "Lurk": ["pct_rounds_lurk"],
}


def _taxa(n: pl.Expr, d: pl.Expr) -> pl.Expr:
    """Taxa que devolve null (e não 0) quando o denominador é zero.

    Zero significaria "medi e deu zero"; null significa "não havia o que medir".
    Um AWPer sem nenhuma kill não tem 0% de kills de AWP: ele não tem a taxa.
    """
    return pl.when(d > 0).then(n / d).otherwise(None)


def _agrega(flags: pl.DataFrame, chaves: list[str]) -> pl.DataFrame:
    """Numeradores e denominadores de todas as taxas, para um dado agrupamento."""
    agg = [pl.len().alias("rounds_jogados")]

    for chave, coluna, _ in TAXAS_POR_ROUND:
        agg.append(pl.col(coluna).sum().alias(f"{chave}_n"))

    agg += [
        pl.col("kills_no_round").sum().alias("kills_totais"),
        pl.col("kills_de_awp_no_round").sum().alias("kills_de_awp"),
        pl.col("assists_no_round").sum().alias("assistencias"),
        pl.col("morreu").sum().alias("mortes"),
        (pl.col("was_traded") & pl.col("morreu")).sum().alias("mortes_trocadas"),
        pl.col("em_clutch").sum().alias("clutch_tentativas"),
        (pl.col("clutch_convertido") & pl.col("em_clutch")).sum().alias("clutch_convertidos"),
        pl.col("time_of_first_contact_s").median().alias("tempo_mediano_ate_contato_s"),
        pl.col("contato_cedo").count().alias("_ignora"),
    ]

    fora = flags.group_by(chaves).agg(agg).drop("_ignora")

    # Denominadores: quase todas as taxas são sobre rounds jogados; as três de
    # baixo têm denominador próprio, e é por isso que elas aparecem sempre
    # acompanhadas dele na interface.
    expr = []
    for chave, _, _ in TAXAS_POR_ROUND:
        expr.append(pl.col("rounds_jogados").alias(f"{chave}_d"))
    fora = fora.with_columns(expr)

    fora = fora.with_columns(
        pl.col("kills_totais").alias("pct_kills_de_awp_d"),
        pl.col("kills_de_awp").alias("pct_kills_de_awp_n"),
        pl.col("mortes").alias("pct_mortes_trocadas_d"),
        pl.col("mortes_trocadas").alias("pct_mortes_trocadas_n"),
        pl.col("clutch_tentativas").alias("taxa_conversao_clutch_d"),
        pl.col("clutch_convertidos").alias("taxa_conversao_clutch_n"),
    )

    todas = [c for c, _, _ in TAXAS_POR_ROUND] + [
        "pct_kills_de_awp", "pct_mortes_trocadas", "taxa_conversao_clutch"
    ]
    return fora.with_columns(
        [_taxa(pl.col(f"{c}_n"), pl.col(f"{c}_d")).alias(c) for c in todas]
    )


# Concentração mínima num grupo comportamental para ele contar como dominante.
# Com 4 grupos, o acaso daria 25% a cada um; 40% é meio caminho entre o acaso e
# a metade dos rounds. Abaixo disso o jogador é versátil, e dizer "sem grupo
# dominante" é informação real — não falha da métrica.
CONCENTRACAO_MINIMA_GRUPO = 0.40

TAXAS_TODAS = [c for c, _, _ in TAXAS_POR_ROUND] + [
    "pct_kills_de_awp", "pct_mortes_trocadas", "taxa_conversao_clutch"
]

# Taxas cujo denominador NÃO é "rounds jogados" e por isso usam o piso de
# eventos, mais baixo, em vez do piso de rounds.
TAXAS_POR_EVENTO = ("pct_kills_de_awp", "pct_mortes_trocadas", "taxa_conversao_clutch")


def _por_lado(flags: pl.DataFrame) -> pl.DataFrame:
    """As taxas sensíveis a lado, em colunas `_ct` e `_t`.

    Um jogador troca de lado no intervalo, então a taxa "por lado" é sobre os
    rounds em que ele estava naquele lado — não sobre a partida inteira.
    """
    sensiveis = [c for c, _, por_lado in TAXAS_POR_ROUND if por_lado]
    por_lado = _agrega(flags, ["steamid", "side"])

    saida = None
    for lado in ("ct", "t"):
        recorte = por_lado.filter(pl.col("side") == lado)
        cols = ["steamid", pl.col("rounds_jogados").alias(f"rounds_{lado}")]
        for c in sensiveis:
            cols += [
                pl.col(c).alias(f"{c}_{lado}"),
                pl.col(f"{c}_n").alias(f"{c}_{lado}_n"),
                pl.col(f"{c}_d").alias(f"{c}_{lado}_d"),
            ]
        recorte = recorte.select(cols)
        saida = recorte if saida is None else saida.join(recorte, on="steamid", how="full", coalesce=True)
    return saida


def _com_referencia(df: pl.DataFrame, colunas: list[str]) -> pl.DataFrame:
    """Para cada taxa, a mediana dos OUTROS jogadores do mesmo recorte.

    Leave-one-out de propósito: comparar o jogador com uma mediana que inclui ele
    próprio puxa a referência na direção dele, e num grupo de 10 isso não é
    desprezível. Sem referência, "60% longe do time" não diz se é muito ou pouco.
    """
    ids = df["steamid"].to_list()
    novas: dict[str, list[float | None]] = {}

    for col in colunas:
        if col not in df.columns:
            continue
        valores = df[col].to_list()
        ref: list[float | None] = []
        for i in range(len(ids)):
            outros = [v for j, v in enumerate(valores) if j != i and v is not None]
            if not outros:
                ref.append(None)
                continue
            outros.sort()
            meio = len(outros) // 2
            ref.append(
                outros[meio] if len(outros) % 2 else (outros[meio - 1] + outros[meio]) / 2
            )
        novas[f"{col}_ref"] = ref

    return df.with_columns([pl.Series(k, v) for k, v in novas.items()]) if novas else df


def _marca_amostra_fraca(df: pl.DataFrame, colunas: list[str]) -> pl.DataFrame:
    """`<taxa>_fraco`: o denominador não sustenta uma porcentagem.

    A célula marcada continua mostrando o bruto — o que não pode acontecer é uma
    taxa de 100% saída de 1 tentativa parecer tão firme quanto uma de 60% saída
    de 20. É o caso de clutch e de abertura de AWP em quase toda partida.
    """
    expr = []
    for col in colunas:
        den = f"{col}_d"
        if col not in df.columns or den not in df.columns:
            continue
        piso = MIN_EVENTOS_PARA_TAXA if col in TAXAS_POR_EVENTO else MIN_ROUNDS_PARA_TAXA
        expr.append((pl.col(den) < piso).alias(f"{col}_fraco"))
    return df.with_columns(expr) if expr else df


def mistura_de_grupos(cluster_assignments: pl.DataFrame) -> pl.DataFrame:
    """Em que grupo comportamental os rounds do jogador mais caem, e quão concentrado.

    Liga o perfil (por jogador) ao agrupamento (por round). `grupo_dominante` é
    null quando nenhum grupo passa de CONCENTRACAO_MINIMA_GRUPO: jogador que se
    espalha pelos quatro é versátil, e inventar um dominante para ele seria
    transformar empate em conclusão.
    """
    vazio = pl.DataFrame(
        schema={"steamid": pl.UInt64, "grupo_dominante": pl.Int32,
                "grupo_dominante_n": pl.UInt32, "grupo_dominante_d": pl.UInt32,
                "grupo_concentracao": pl.Float64}
    )
    if cluster_assignments.height == 0 or "cluster" not in cluster_assignments.columns:
        return vazio

    total = cluster_assignments.group_by("steamid").agg(pl.len().alias("grupo_dominante_d"))
    por_grupo = cluster_assignments.group_by(["steamid", "cluster"]).agg(pl.len().alias("n"))

    topo = (
        por_grupo.sort(["n", "cluster"], descending=[True, False])
        .group_by("steamid", maintain_order=True)
        .first()
        .join(total, on="steamid", how="left")
        .with_columns((pl.col("n") / pl.col("grupo_dominante_d")).alias("grupo_concentracao"))
    )

    resumo = topo.select(
        "steamid",
        pl.when(pl.col("grupo_concentracao") >= CONCENTRACAO_MINIMA_GRUPO)
        .then(pl.col("cluster"))
        .otherwise(None)
        .cast(pl.Int32)
        .alias("grupo_dominante"),
        pl.col("n").cast(pl.UInt32).alias("grupo_dominante_n"),
        pl.col("grupo_dominante_d").cast(pl.UInt32),
        pl.col("grupo_concentracao"),
    )

    # A contagem por grupo vai junto porque o acumulado entre partidas precisa
    # dela: somar só o `grupo_dominante_n` somaria as contagens de grupos
    # DIFERENTES (o dominante de uma partida não é o da outra) e produziria um
    # número que não é a contagem de nada.
    largo = por_grupo.with_columns(
        ("grupo_" + pl.col("cluster").cast(pl.String) + "_n").alias("coluna")
    ).pivot(on="coluna", index="steamid", values="n").fill_null(0)

    return resumo.join(largo, on="steamid", how="left")


def player_profile(
    features: pl.DataFrame,
    positions: pl.DataFrame,
    ticks: pl.DataFrame,
    kills: pl.DataFrame,
    rounds: pl.DataFrame,
    player_areas: pl.DataFrame,
    clutch_round: pl.DataFrame,
    cluster_assignments: pl.DataFrame | None = None,
    match_id: str = "",
) -> tuple[pl.DataFrame, pl.DataFrame]:
    """Perfil de uma partida. Devolve (per_match, round_flags).

    O tickrate NÃO é assumido: sai de `metrics.timing.detect_tickrate`, que o
    detecta pelo timer da bomba. Foi um 128 hardcodado que produziu o bug de
    tempo que o projeto inteiro carrega como cicatriz.
    """
    tickrate = int(detect_tickrate(rounds, ticks)["tickrate"])
    flags = round_flags(
        features, positions, ticks, kills, player_areas, clutch_round, tickrate
    )

    por_jogador = _agrega(flags, ["steamid", "name"])
    por_lado = _por_lado(flags)

    perfil = por_jogador.join(por_lado, on="steamid", how="left")
    if cluster_assignments is not None:
        perfil = perfil.join(mistura_de_grupos(cluster_assignments), on="steamid", how="left")

    sensiveis = [c for c, _, por_l in TAXAS_POR_ROUND if por_l]
    colunas_ref = TAXAS_TODAS + [f"{c}_{lado}" for c in sensiveis for lado in ("ct", "t")]

    perfil = _com_referencia(perfil, colunas_ref)
    perfil = _marca_amostra_fraca(perfil, TAXAS_TODAS)
    perfil = perfil.with_columns(
        pl.lit(match_id).alias("match_id"),
        pl.lit(tickrate).alias("tickrate"),
        pl.lit(1, dtype=pl.UInt32).alias("partidas"),
    )
    return perfil.sort("name"), flags


def accumulate(perfis: list[pl.DataFrame]) -> pl.DataFrame:
    """Soma os perfis de várias partidas num perfil por jogador.

    Soma NUMERADORES E DENOMINADORES e recalcula a taxa — não tira média das
    taxas. Média de taxas dá o mesmo peso a uma partida de 16 rounds e a uma de
    30, e o perfil passa a descrever as partidas em vez do jogador.
    """
    if not perfis:
        return pl.DataFrame()

    todos = pl.concat(perfis, how="diagonal")
    colunas = todos.columns

    agg = [
        pl.col("name").last(),
        pl.col("partidas").sum().alias("partidas"),
        pl.col("rounds_jogados").sum().alias("rounds_jogados"),
    ]
    numeros = [c for c in colunas if c.endswith(("_n", "_d")) or c in
               ("kills_totais", "kills_de_awp", "assistencias", "mortes", "mortes_trocadas",
                "clutch_tentativas", "clutch_convertidos", "rounds_ct", "rounds_t",
                "grupo_dominante_n", "grupo_dominante_d")]
    agg += [pl.col(c).sum().alias(c) for c in dict.fromkeys(numeros)]
    # A mediana do tempo até o contato é a mediana das medianas: a exata pediria
    # guardar todos os rounds, e a diferença entre as duas não muda leitura.
    if "tempo_mediano_ate_contato_s" in colunas:
        agg.append(pl.col("tempo_mediano_ate_contato_s").median())

    somado = todos.group_by("steamid").agg(agg)

    sensiveis = [c for c, _, por_l in TAXAS_POR_ROUND if por_l]
    recalcular = TAXAS_TODAS + [f"{c}_{lado}" for c in sensiveis for lado in ("ct", "t")]
    somado = somado.with_columns(
        [
            _taxa(pl.col(f"{c}_n"), pl.col(f"{c}_d")).alias(c)
            for c in recalcular
            if f"{c}_n" in somado.columns and f"{c}_d" in somado.columns
        ]
    )

    somado = _recalcula_grupo_dominante(somado)
    somado = _com_referencia(somado, recalcular)
    somado = _marca_amostra_fraca(somado, TAXAS_TODAS)
    return somado.sort("name")


def _recalcula_grupo_dominante(somado: pl.DataFrame) -> pl.DataFrame:
    """Refaz o grupo dominante a partir das contagens somadas.

    Sem isto a coluna `grupo_dominante` simplesmente não existia no acumulado, e
    a interface mostrava "sem grupo dominante" para TODO mundo -- um texto
    plausível, que é exatamente o tipo de erro que não aparece sozinho.
    """
    colunas = [c for c in somado.columns if c.startswith("grupo_") and c.endswith("_n")
               and c != "grupo_dominante_n"]
    if not colunas:
        return somado

    total = pl.sum_horizontal([pl.col(c) for c in colunas])
    maior = pl.max_horizontal([pl.col(c) for c in colunas])

    # qual coluna tem o máximo: a primeira que empata com ele, em ordem de grupo
    qual = pl.lit(None, dtype=pl.Int32)
    for c in sorted(colunas, key=lambda x: int(x.split("_")[1]), reverse=True):
        numero = int(c.split("_")[1])
        qual = pl.when(pl.col(c) == maior).then(pl.lit(numero, dtype=pl.Int32)).otherwise(qual)

    return somado.with_columns(
        total.cast(pl.UInt32).alias("grupo_dominante_d"),
        maior.cast(pl.UInt32).alias("grupo_dominante_n"),
        qual.alias("_grupo_top"),
    ).with_columns(
        pl.when(pl.col("grupo_dominante_d") > 0)
        .then(pl.col("grupo_dominante_n") / pl.col("grupo_dominante_d"))
        .otherwise(None)
        .alias("grupo_concentracao")
    ).with_columns(
        pl.when(pl.col("grupo_concentracao") >= CONCENTRACAO_MINIMA_GRUPO)
        .then(pl.col("_grupo_top"))
        .otherwise(None)
        .alias("grupo_dominante")
    ).drop("_grupo_top")
