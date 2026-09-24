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

# Rounds em que O TIME teve AWP mínimos para confiar na taxa "a AWP do time era
# dele". É o DENOMINADOR da métrica, e por isso não reusa o MIN_AWP_ROUNDS de
# metrics/archetypes.py: aquele mede os rounds com a AWP na mão DELE (o
# numerador) e existe para dizer se o papel de AWPer existe -- "abaixo disso é
# AWP de round de força". Mesmo valor, finalidade diferente. Medido: 40 dos 430
# jogador-partidas profissionais têm menos de 5 rounds de AWP no time, e é ali
# que a taxa vira 0 ou 1 com três rounds (decisão do Pedro, 2026-09-24).
MIN_ROUNDS_AWP_DO_TIME = 4

# Quanto o jogador precisa estar ACIMA do esperado da função para ser lurker.
# 1,5x é o mesmo fator com que o projeto ancora outros pisos ao acaso ou ao
# ruído (round decisivo 1,5x o round mais barato, bottom frag 1,5 desvios
# medianos, entry 1,5x o acaso). Medido nas 43 profissionais: 94 -> 42 rótulos,
# 4 novos; dos 64 rótulos de líderes de hoje, 22 saem por amostra e 4 por
# ficarem abaixo de 1,5x.
PISO_LURK_RELATIVO = 1.5

# Rounds SEM AWP mínimos para afirmar lurk. 8 é o mesmo mínimo que o projeto já
# usa para afirmar uma taxa de jogador (player_profile.MIN_ROUNDS_PARA_TAXA);
# abaixo disso a linha sai como dado insuficiente. O m0NESY da match_20 tem 6.
MIN_ROUNDS_SEM_AWP = 8

# Taxa ESPERADA de "fora da área do time" por função estrutural, nos rounds sem
# AWP. Medida no corpus (43 partidas profissionais, 2026-09-24); função com
# menos de 100 rounds e round sem função reconhecida caem no padrão. Refazer
# quando o corpus crescer -- `py -3.12 -m scripts.proposta_pisos` mostra a
# distribuição, e há teste que recalcula e falha se a tabela envelhecer.
OFF_TEAM_ESPERADO_POR_FUNCAO = {"trader": 0.175, "suporte": 0.203, "entry": 0.291}
OFF_TEAM_ESPERADO_SEM_FUNCAO = 0.232
OFF_TEAM_ESPERADO_PADRAO = 0.302

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
    coluna_amostra  coluna com o tamanho da amostra que sustenta a métrica
    minimo_amostra  abaixo disso a função não é afirmada -- é DADO INSUFICIENTE,
                não "não qualifica" (a diferença importa: o primeiro é silêncio
                por falta de base, o segundo é uma medição que disse não)
    evidencia   frase a partir da linha inteira, quando a taxa sozinha não conta
                a história (decisão 7a: taxa sempre com o bruto)
    """

    key: str
    label: str
    column: str
    high_is: bool
    floor: float
    priority: int
    phrase: Callable[[float], str]
    coluna_amostra: str | None = None
    minimo_amostra: int = 0
    evidencia: Callable[[dict], str] | None = None


TRAIT_SPECS: list[Trait] = [
    # AWP primeiro porque é a função mais definida por equipamento: quem pega a
    # AWP muda o que o time pode fazer no round, e isso não é ambíguo no demo.
    Trait(
        key="awp",
        label="AWPer",
        column="awp_share",
        high_is=True,
        floor=0.25,  # PISO NA ESCALA ANTIGA -- recalibrar (os métodos sugerem ~0,55)
        priority=1,
        phrase=lambda v: f"a AWP do time era dele em {v * 100:.0f}% dos rounds com AWP",
        coluna_amostra="awp_rounds_do_time",
        minimo_amostra=MIN_ROUNDS_AWP_DO_TIME,
        evidencia=lambda r: (
            f"a AWP do time era dele em {r['awp_share'] * 100:.0f}% dos rounds com AWP "
            f"({round(r['awp_share'] * r['awp_rounds_do_time'])} de {r['awp_rounds_do_time']})"
        ),
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
    # O lurker é medido em DOIS consertos (decisão do Pedro, 2026-09-24):
    #
    # 1. SEM os rounds em que ele carregava a AWP. Segurar um ângulo longe do
    #    time com a AWP é o trabalho do AWPer, não lurk -- era assim que o
    #    m0NESY, cujo título é "AWPer, AWP na mão em 63% dos rounds", ganhava
    #    "Lurker" como característica secundária (match_32).
    # 2. RELATIVO à função estrutural daqueles rounds, não à média do elenco
    #    (princípio da decisão 15c). Entry e suporte jogam fora da área do time
    #    com frequências diferentes, e comparar todo mundo contra a mesma régua
    #    transforma função em atitude.
    #
    # A régua NÃO usa a própria função "lurker" como referência: ela é definida
    # por jogar em outra área (decisão 12), tem taxa esperada 0,97, e dividir um
    # lurker de verdade por 0,97 faria ele perder o rótulo. Rounds classificados
    # como lurker caem na taxa geral.
    Trait(
        key="lurk",
        label="Lurker",
        column="off_team_relativo",
        high_is=True,
        floor=PISO_LURK_RELATIVO,
        priority=4,
        phrase=lambda v: f"jogou fora da área do time {v:.1f}x o esperado da função",
        coluna_amostra="n_rounds_sem_awp",
        minimo_amostra=MIN_ROUNDS_SEM_AWP,
        evidencia=lambda r: (
            f"fora da área do time em {r['off_team_share_sem_awp'] * 100:.0f}% dos rounds sem AWP "
            f"({round(r['off_team_share_sem_awp'] * r['n_rounds_sem_awp'])} de {r['n_rounds_sem_awp']}), "
            f"{r['off_team_relativo']:.1f}x o esperado da função"
        ),
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
        .group_by("steamid", maintain_order=True)
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


def awp_do_time(outputs: dict[str, pl.DataFrame], times: pl.DataFrame) -> pl.DataFrame:
    """Dos rounds em que O TIME teve AWP, em quantos ela era dele.

    Devolve (steamid, awp_rounds_do_time, awp_share). `times` é (steamid, team).

    POR QUE O DENOMINADOR É ESTE (decisão do Pedro, 2026-09-24): "AWP na mão /
    TODOS os rounds" contava round de save, força e pistola como falha do
    AWPer -- e nem todo round o time tem dinheiro para AWP, mesmo com um AWPer
    titular. Aqui o round de eco simplesmente não entra: se ninguém do time teve
    AWP, o round não faz parte da pergunta. Testadas e descartadas as formas com
    denominador por DINHEIRO (rounds em que ele, ou o time, podia comprar): elas
    contam como falha o round em que o time TINHA dinheiro e escolheu não
    comprar AWP, e nenhuma separa a distribuição (espalhamento dos três métodos
    1,2 a 2,0 contra 0,13 desta, e 0,42 a 0,50 com encolhimento em qualquer K).
    """
    vazio = pl.DataFrame(schema={"steamid": times.schema["steamid"],
                                 "awp_rounds_do_time": pl.UInt32, "awp_share": pl.Float64})
    awp = outputs.get("awp_per_round")
    if awp is None or awp.height == 0 or times.height == 0:
        return vazio
    com_awp = (awp.select("round_num", "steamid").unique(maintain_order=True, keep="first")
               .join(times, on="steamid", how="left"))
    # (round, time) em que alguém do time estava com AWP
    rounds_do_time = com_awp.select("round_num", "team").unique(maintain_order=True, keep="first")
    denominador = (rounds_do_time.group_by("team", maintain_order=True)
                   .agg(pl.len().cast(pl.UInt32).alias("awp_rounds_do_time")))
    numerador = (com_awp.group_by("steamid", maintain_order=True)
                 .agg(pl.len().cast(pl.UInt32).alias("awp_rounds_dele")))
    return (times.join(denominador, on="team", how="left")
            .join(numerador, on="steamid", how="left")
            .with_columns(pl.col("awp_rounds_dele").fill_null(0),
                          pl.col("awp_rounds_do_time").fill_null(0))
            .with_columns(pl.when(pl.col("awp_rounds_do_time") > 0)
                          .then(pl.col("awp_rounds_dele") / pl.col("awp_rounds_do_time"))
                          .otherwise(0.0).alias("awp_share"))
            .select("steamid", "awp_rounds_do_time", "awp_share"))


def lurk_relativo(outputs: dict[str, pl.DataFrame]) -> pl.DataFrame:
    """Lurk medido SEM os rounds com AWP e RELATIVO à função estrutural.

    Devolve (steamid, off_team_share_sem_awp, n_rounds_sem_awp,
    off_team_esperado, off_team_relativo). Sem alguma das tabelas de origem,
    devolve vazio -- e a função simplesmente não é atribuída, como já acontece
    quando o mapa não permite localizar os bombsites.
    """
    lurk = outputs.get("lurk_per_round")
    if lurk is None or lurk.height == 0 or "off_team" not in lurk.columns:
        return pl.DataFrame(schema={"steamid": pl.UInt64, "off_team_share_sem_awp": pl.Float64,
                                    "n_rounds_sem_awp": pl.UInt32, "off_team_esperado": pl.Float64,
                                    "off_team_relativo": pl.Float64})
    awp = outputs.get("awp_per_round")
    com_awp = (awp.select("round_num", "steamid").unique(maintain_order=True, keep="first")
               .with_columns(pl.lit(True).alias("com_awp"))
               if awp is not None and awp.height else
               pl.DataFrame(schema={"round_num": lurk.schema["round_num"], "steamid": lurk.schema["steamid"],
                                    "com_awp": pl.Boolean}))
    est = outputs.get("structural_roles")
    funcoes = (est.select("round_num", "steamid", "funcao")
               if est is not None and "funcao" in est.columns else
               pl.DataFrame(schema={"round_num": lurk.schema["round_num"], "steamid": lurk.schema["steamid"],
                                    "funcao": pl.String}))
    base = (lurk.select("round_num", "steamid", "off_team")
            .join(com_awp, on=["round_num", "steamid"], how="left")
            .with_columns(pl.col("com_awp").fill_null(False))
            .join(funcoes, on=["round_num", "steamid"], how="left")
            .filter(~pl.col("com_awp") & pl.col("off_team").is_not_null()))
    if base.height == 0:
        return lurk.select("steamid").unique(maintain_order=True, keep="first").with_columns(
            pl.lit(None, dtype=pl.Float64).alias("off_team_share_sem_awp"),
            pl.lit(0, dtype=pl.UInt32).alias("n_rounds_sem_awp"),
            pl.lit(None, dtype=pl.Float64).alias("off_team_esperado"),
            pl.lit(None, dtype=pl.Float64).alias("off_team_relativo"))
    esperado = (pl.when(pl.col("funcao").is_null()).then(pl.lit(OFF_TEAM_ESPERADO_SEM_FUNCAO))
                .otherwise(pl.col("funcao").replace_strict(OFF_TEAM_ESPERADO_POR_FUNCAO,
                                                           default=OFF_TEAM_ESPERADO_PADRAO,
                                                           return_dtype=pl.Float64)))
    return (base.with_columns(esperado.alias("esp"))
            .group_by("steamid", maintain_order=True)
            .agg(pl.col("off_team").mean().alias("off_team_share_sem_awp"),
                 pl.len().cast(pl.UInt32).alias("n_rounds_sem_awp"),
                 pl.col("esp").mean().alias("off_team_esperado"))
            .with_columns((pl.col("off_team_share_sem_awp") / pl.col("off_team_esperado")).alias("off_team_relativo")))


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
        .group_by(["steamid", "name", "team"], maintain_order=True)
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
        # Empate no primeiro lugar não é abertura de ninguém: acontece quando
        # uma granada pega vários do time no mesmo tick, e marcar todos infla o
        # entry do time inteiro. Medido: 24 de 374 lados-round nas 9 partidas.
        .with_columns(
            pl.col("rk").eq(1).sum().over(["round_num", "team"]).alias("empatados")
        )
        .group_by("steamid", maintain_order=True)
        .agg(
            ((pl.col("rk") == 1) & (pl.col("empatados") == 1))
            .mean()
            .alias("first_contact_share")
        )
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
        .join(lurk_relativo(outputs), on="steamid", how="left")
        .with_columns(
            pl.col("awp_rounds").fill_null(0),
            pl.col("first_contact_share").fill_null(0.0),
            pl.when(pl.col("total_kills") > 0)
            .then(pl.col("total_trade_kills") / pl.col("total_kills"))
            .otherwise(0.0)
            .alias("trade_share"),
        )
        # a forma antiga (AWP na mão / todos os rounds) continua na tabela como
        # informação, mas não é mais o que define a função -- ela dilui o AWPer
        # com round de eco (ver awp_do_time)
        .with_columns((pl.col("awp_rounds") / rounds_played).alias("awp_share_todos_rounds"))
        .join(awp_do_time(outputs, per_player.select("steamid", "team")), on="steamid", how="left")
        .with_columns(pl.col("awp_share").fill_null(0.0),
                      pl.col("awp_rounds_do_time").fill_null(0))
        .sort(["team", "name"])
    )


def _evidencia(spec: Trait, linha: dict) -> str:
    if spec.evidencia is not None:
        try:
            return spec.evidencia(linha)
        except KeyError:
            pass
    return spec.phrase(float(linha[spec.column]))


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
        # Amostra mínima: abaixo dela a função não é afirmada por DADO
        # INSUFICIENTE. Não é o mesmo que não qualificar -- e é por isso que o
        # corte vem depois do piso, não dentro dele.
        if spec.coluna_amostra and spec.coluna_amostra in qualified.columns:
            qualified = qualified.filter(
                pl.col(spec.coluna_amostra).fill_null(0) >= spec.minimo_amostra)
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
                    # A evidência detalhada usa colunas auxiliares (o bruto da
                    # taxa). Num frame que não as tem -- métrica de origem
                    # ausente nesta partida --, cai na frase simples em vez de
                    # quebrar: a função continua atribuída, só com menos detalhe.
                    "evidence": _evidencia(spec, row),
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
