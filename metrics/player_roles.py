"""
Função de cada jogador na partida (Fase 4), derivada de comportamento medido.

Este módulo é a resposta a uma pergunta diferente da do clustering. O KMeans
agrupa (jogador, round) porque o mesmo atleta é entry num round e âncora no
seguinte — e isso continua valendo. Mas quem olha um time quer saber "o que
esse cara FAZ nessa partida", e essa pergunta é por jogador.

O que este módulo NÃO faz, de propósito:

- Não força um de cada. Não existe regra dizendo que todo time tem 1 AWPer,
  1 entry e 1 suporte: na partida de teste, um dos times não teve AWPer nenhum
  acima do limiar, e dois jogadores não tiveram função dominante. Isso é
  resultado, não falha — o contrário (distribuir rótulos até preencher cinco
  vagas) seria inventar função pra caber num molde.

- Não nomeia cluster nenhum. A nomeação dos clusters continua sendo do Pedro
  (ver clustering/playstyle.py). Aqui o rótulo sai de um limiar explícito sobre
  uma métrica medida, e a evidência numérica anda junto do rótulo em toda
  saída — dá pra discordar do limiar olhando o número ao lado.

- Não deduz IGL. Quem chama o time não deixa rastro no demo: não há áudio, e
  liderança não tem assinatura estatística. Rotular alguém de IGL aqui seria
  chute com cara de métrica.

Como um rótulo é atribuído: o jogador precisa (1) liderar o PRÓPRIO TIME na
métrica daquela função e (2) passar de um piso absoluto. A comparação é dentro
do time porque função é uma divisão interna — "é o que mais joga AWP no time"
descreve um papel; "joga mais AWP que a média dos 10" só descreve a partida.
Quando duas funções se qualificam, vale a de maior prioridade (ver TRAIT_SPECS),
e as outras continuam aparecendo como características.

Os pisos são pontos de calibração, não constantes universais. Foram revistos
sobre 9 partidas (90 jogador-partidas, 18 times-partida) -- foi essa revisão que
mostrou que o piso do entry, herdado da partida de teste, estava fora da escala
do dado e nunca disparava. Os de suporte, âncora e fragger não filtram nada hoje
(18/18 dos líderes passam) e ficaram como estavam de propósito: o piso existe
para barrar rótulo quando o líder não é destacado, e nenhum caso desses
apareceu ainda. Apertá-los agora seria calibrar no ruído de 18 amostras.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import polars as pl

# Rounds por metade (MR12): o lado troca, o time não.
HALFTIME_ROUND = 12

# Override manual: o julgamento do Pedro tem prioridade sobre o limiar, igual ao
# MANUAL_ENTRY_ANGLES em metrics/map_angles.py. Chave = nome do jogador no demo,
# valor = função. Preencher só quando o número disser uma coisa e a partida
# outra -- e o painel marca o rótulo como manual quando vem daqui.
MANUAL_ROLES: dict[str, str] = {}


@dataclass(frozen=True)
class Trait:
    """Uma função possível e a evidência que a sustenta.

    column      métrica que define a função
    high_is     True se um valor ALTO caracteriza a função
    floor       piso absoluto: sem isso, liderar o time não significa nada
                (o menos ruim de um time que não usa AWP não é um AWPer)
    priority    menor = mais definidor; decide qual rótulo vira o título
    """

    key: str
    label: str
    column: str
    high_is: bool
    floor: float
    priority: int
    phrase: Callable[[float], str]


TRAIT_SPECS: list[Trait] = [
    # AWP primeiro porque é a função mais definida por equipamento: quem pega a
    # AWP muda o que o time pode fazer no round, e isso não é ambíguo no demo.
    Trait(
        key="awp",
        label="AWPer",
        column="awp_share",
        high_is=True,
        floor=0.25,  # abaixo disso é AWP eventual de round de força, não função
        priority=1,
        phrase=lambda v: f"AWP na mão em {v * 100:.0f}% dos rounds",
    ),
    # Entra primeiro: em que fração dos rounds ele foi o PRIMEIRO do time a
    # tomar contato.
    #
    # Antes isto era a mediana do próprio tempo até o contato, com piso de 8s --
    # e o rótulo nunca foi atribuído a ninguém em 9 partidas. O motivo é que 8s
    # não existe na escala do dado: o jogador mais rápido de um time tem mediana
    # entre 10,7s e 21,3s. Um piso em segundos também é frágil por construção,
    # porque o tempo até o contato muda com o mapa, com o lado e com o ritmo do
    # adversário -- ele mede o quão rápido a PARTIDA foi, não quem abre.
    #
    # O share é comparativo por definição: independe de o time jogar rápido ou
    # de default lento, e responde à pergunta certa ("é ele que encosta
    # primeiro?"). A correlação com a métrica antiga é de apenas -0,48 nas 9
    # partidas, então não é a mesma coisa com outra roupa.
    Trait(
        key="entry",
        label="Abre o round",
        column="first_contact_share",
        high_is=True,
        # Com 5 jogadores, o acaso daria 0,20 a cada um. O líder de time observado
        # vai de 0,25 a 0,53 (mediana 0,33); 0,32 separa quem abre de fato de quem
        # só foi o menos lento de um time sem entry definido.
        floor=0.32,
        priority=2,
        phrase=lambda v: f"foi o primeiro do time a encostar no adversário em {v * 100:.0f}% dos rounds",
    ),
    # Suporte medido por EFEITO (tempo de cegueira imposto a inimigo), não por
    # granadas jogadas: todo mundo joga granada, poucos cegam alguém com elas.
    Trait(
        key="support",
        label="Suporte de utility",
        column="enemy_blind_seconds",
        high_is=True,
        floor=20.0,
        priority=3,
        phrase=lambda v: f"{v:.0f}s de cegueira imposta a inimigos",
    ),
    # Lurk é jogar OUTRA ÁREA do mapa enquanto o time executa: time indo pro A e
    # ele infiltrando meio ou B. Antes isto era distância média do time, que é
    # outra coisa -- dois CTs em bombsites opostos estão longe um do outro sem
    # que nenhum seja lurker, e um T colado no time num corredor apertado pode
    # estar sozinho na área. A comparação é com o resto do time, round a round
    # (ver metrics/site_roles.py). A distância média continua na tabela como
    # informação, só não define mais a função.
    Trait(
        key="lurk",
        label="Lurker",
        column="off_team_share",
        high_is=True,
        floor=0.40,
        priority=4,
        phrase=lambda v: f"jogou fora da área do time em {v * 100:.0f}% dos rounds de T",
    ),
    # Âncora é ficar fixo no mesmo bombsite, inclusive quando os T indicam o
    # outro lado. Antes isto era contato tardio, que mede o round demorar e não o
    # jogador não rotacionar: um CT que roda duas vezes e chega atrasado na briga
    # tinha o mesmo número de um âncora. `never_left_share` é a fração dos rounds
    # de CT em que ele não rotacionou pro outro bombsite -- `hold_share`, que é a
    # fração dos rounds jogados na área de casa, satura (mediana 1,00 entre os
    # líderes de time) e por isso não serve de critério, mas continua na tabela.
    Trait(
        key="anchor",
        label="Âncora de bomb",
        column="never_left_share",
        high_is=True,
        floor=0.80,
        priority=5,
        phrase=lambda v: f"não rotacionou em {v * 100:.0f}% dos rounds de CT",
    ),
    Trait(
        key="trade",
        label="Segundo homem",
        column="trade_share",
        high_is=True,
        floor=0.35,
        priority=6,
        phrase=lambda v: f"{v * 100:.0f}% das kills foram trade",
    ),
    Trait(
        key="frag",
        label="Principal fragger",
        column="adr",
        high_is=True,
        floor=85.0,
        priority=7,
        phrase=lambda v: f"{v:.0f} de ADR",
    ),
]


def _coluna_opcional(df: pl.DataFrame | None, colunas: list[str]) -> pl.DataFrame:
    """Seleciona colunas de uma tabela que pode não existir nesta partida.

    Devolve uma tabela vazia com o schema certo quando a métrica não foi
    calculada, pra o join a jusante produzir null em vez de estourar. Null e zero
    não são a mesma coisa aqui: null é "não medi", zero é "medi e deu zero", e só
    o primeiro deve impedir a atribuição da função.
    """
    if df is None or df.height == 0 or not all(c in df.columns for c in colunas):
        return pl.DataFrame(schema={"steamid": pl.UInt64})
    return df.select(colunas)


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


def build_signals(
    outputs: dict[str, pl.DataFrame],
    features: pl.DataFrame,
    team_of: dict[int, str],
) -> pl.DataFrame:
    """Uma linha por jogador com as métricas que descrevem função.

    `features` é a matriz do clustering (uma linha por jogador/round), usada aqui
    agregada por jogador -- as duas visões vêm da mesma fonte de propósito, pra
    a aba de estilos e a de funções não contarem histórias diferentes.
    """
    rounds_played = features["round_num"].n_unique()

    per_player = (
        features.with_columns(
            pl.col("steamid")
            .map_elements(lambda s: team_of.get(s, "?"), return_dtype=pl.String)
            .alias("team")
        )
        .group_by(["steamid", "name", "team"])
        .agg(
            pl.col("time_of_first_contact_s").median().alias("median_first_contact_s"),
            pl.col("survived").mean().alias("survival_rate"),
            pl.col("avg_distance_from_team").mean().alias("avg_distance_from_team"),
            pl.col("distinct_places").mean().alias("distinct_places"),
        )
    )

    # Em quantos rounds o jogador foi o PRIMEIRO do time a tomar contato. É a
    # medida direta de quem encosta no adversário antes dos companheiros --
    # complementa a mediana de tempo, que sozinha não diz se ele chegou antes
    # dos outros ou se o time inteiro joga rápido.
    first_contact = (
        features.with_columns(
            pl.col("steamid")
            .map_elements(lambda s: team_of.get(s, "?"), return_dtype=pl.String)
            .alias("team")
        )
        .filter(pl.col("time_of_first_contact_s").is_not_null())
        .with_columns(
            pl.col("time_of_first_contact_s").rank("min").over(["round_num", "team"]).alias("rk")
        )
        .group_by("steamid")
        .agg((pl.col("rk") == 1).mean().alias("first_contact_share"))
    )

    trades = outputs["trade_kills_summary"].select(["steamid", "total_kills", "total_trade_kills"])
    awp = outputs.get("awp_summary")
    awp_sel = (
        awp.select(["steamid", "awp_rounds"])
        if awp is not None and "awp_rounds" in awp.columns
        else pl.DataFrame({"steamid": [], "awp_rounds": []}, schema={"steamid": pl.Int64, "awp_rounds": pl.Int64})
    )

    gren = outputs["grenades_summary"].select(
        ["steamid", "flash_thrown", "enemies_flashed", "enemy_blind_seconds", "team_blind_seconds",
         "flash_assists", "smoke_thrown", "utility_damage", "nades_per_round"]
    )

    # Âncora e lurk vêm de metrics/site_roles.py. Podem faltar (mapa em que não
    # deu pra localizar os dois bombsites): nesse caso a coluna entra vazia e a
    # função simplesmente não é atribuída, que é melhor que atribuir com base em
    # zero -- zero em `hold_share` significaria "nunca ficou no site dele".
    anchor = _coluna_opcional(
        outputs.get("anchor_summary"),
        ["steamid", "home_area", "hold_share", "never_left_share", "no_rotate_share",
         "n_rounds_pressao_outro_lado"],
    )
    lurk = _coluna_opcional(
        outputs.get("lurk_summary"),
        ["steamid", "off_team_share", "n_rounds_time_definido"],
    )

    return (
        per_player.join(first_contact, on="steamid", how="left")
        .join(outputs["adr_summary"].select(["steamid", "adr"]), on="steamid", how="left")
        .join(outputs["kast_summary"].select(["steamid", "kast_pct"]), on="steamid", how="left")
        .join(trades, on="steamid", how="left")
        .join(gren, on="steamid", how="left")
        .join(awp_sel, on="steamid", how="left")
        .join(anchor, on="steamid", how="left")
        .join(lurk, on="steamid", how="left")
        .with_columns(
            pl.col("awp_rounds").fill_null(0),
            pl.col("first_contact_share").fill_null(0.0),
            pl.when(pl.col("total_kills") > 0)
            .then(pl.col("total_trade_kills") / pl.col("total_kills"))
            .otherwise(0.0)
            .alias("trade_share"),
        )
        .with_columns((pl.col("awp_rounds") / rounds_played).alias("awp_share"))
        .sort(["team", "name"])
    )


def assign_traits(signals: pl.DataFrame) -> pl.DataFrame:
    """Uma linha por (jogador, função qualificada), com a evidência numérica.

    Qualifica quem lidera o próprio time na métrica E passa do piso. Jogador sem
    nenhuma função qualificada simplesmente não aparece aqui -- é assim que o
    painel consegue dizer "sem função dominante" em vez de inventar uma.
    """
    rows = []
    for spec in TRAIT_SPECS:
        # A coluna pode não existir quando a métrica de origem não foi calculada
        # nesta partida (ver _coluna_opcional). Função sem medição não é função
        # com valor zero: ela simplesmente não é atribuída.
        if spec.column not in signals.columns:
            continue
        ranked = signals.with_columns(
            pl.col(spec.column)
            .rank("min", descending=spec.high_is)
            .over("team")
            .alias("rk")
        )
        qualified = ranked.filter(
            (pl.col("rk") == 1)
            & pl.col(spec.column).is_not_null()
            & (pl.col(spec.column) >= spec.floor if spec.high_is else pl.col(spec.column) <= spec.floor)
        )
        for row in qualified.iter_rows(named=True):
            rows.append(
                {
                    "steamid": row["steamid"],
                    "name": row["name"],
                    "team": row["team"],
                    "trait": spec.key,
                    "label": spec.label,
                    "priority": spec.priority,
                    "value": float(row[spec.column]),
                    "evidence": spec.phrase(float(row[spec.column])),
                }
            )

    if not rows:
        return pl.DataFrame(
            schema={
                "steamid": pl.Int64, "name": pl.String, "team": pl.String, "trait": pl.String,
                "label": pl.String, "priority": pl.Int64, "value": pl.Float64, "evidence": pl.String,
            }
        )
    return pl.DataFrame(rows).sort(["team", "name", "priority"])


def build_player_roles(
    outputs: dict[str, pl.DataFrame],
    features: pl.DataFrame,
    ticks: pl.DataFrame,
) -> tuple[pl.DataFrame, pl.DataFrame]:
    """Devolve (roles, traits): o rótulo principal de cada jogador e a lista
    completa de características qualificadas.
    """
    team_of, _ = resolve_teams(ticks)
    signals = build_signals(outputs, features, team_of)
    traits = assign_traits(signals)

    headline = (
        traits.sort(["steamid", "priority"])
        .group_by("steamid", maintain_order=True)
        .agg(
            pl.col("label").first().alias("role"),
            pl.col("evidence").first().alias("role_evidence"),
        )
    )

    roles = signals.join(headline, on="steamid", how="left").with_columns(
        pl.col("name")
        .map_elements(lambda n: MANUAL_ROLES.get(n), return_dtype=pl.String)
        .alias("manual_role")
    )

    return (
        roles.with_columns(
            pl.coalesce([pl.col("manual_role"), pl.col("role")]).alias("role"),
            pl.col("manual_role").is_not_null().alias("role_is_manual"),
        ).sort(["team", "name"]),
        traits,
    )
