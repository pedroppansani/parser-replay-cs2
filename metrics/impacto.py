"""Impacto do jogador além do placar: utilidade que rendeu, trocas e situações (fase 7, item 7.2).

JUSTIFICATIVA DE JOGO. A pergunta não é "quantas granadas ele jogou" nem
"quantas kills ele fez", e sim "o que o que ele fez produziu":

- UTILIDADE QUE RENDEU. Uma HE que tira 40 de dois inimigos e uma que cai no
  vazio contam igual em "granadas jogadas". Aqui a granada vale pelo efeito:
  dano por HE e por molotov, inimigos cegados e segundos de cegueira por flash,
  e quantas kills saíram de inimigo cego pela flash dele (a kill dele mesmo ou
  de um companheiro, `metrics/grenades.py`). A cegueira nos PRÓPRIOS
  companheiros conta contra: é a flash que ajudou o adversário.
- TROCAS. Trocar rápido é o que impede o adversário de ganhar o duelo de graça.
  A fração das mortes trocadas e as kills de troca já existem (perfil e
  `basic_metrics`); o que faltava é QUANTO ele demora para trocar, em segundos,
  com a janela de trade única do projeto (`metrics/constantes.py`).
- SITUAÇÕES. Pós-plant (TR defendendo a bomba) e retake (CT) são rounds com
  regra própria: quem está vivo no plant joga outro jogo. Para cada lado: em
  quantos rounds ele estava vivo no plant, quantos o time venceu, quantas kills
  ele fez depois do plant e se sobreviveu. E o duelo de abertura POR LADO:
  abrir de TR (entrar no site) não é o mesmo que abrir de CT (segurar o ângulo).

Contrato do projeto: `(per_round, summary)`. Toda taxa sai com o bruto (`_n`,
`_d`); a régua do corpus e a marca de amostra fraca vêm do perfil
(`metrics/player_profile.py`, decisão 7a), que junta este resumo ao dele.
"""
from __future__ import annotations

import polars as pl

from metrics.basic_metrics import _pares_de_trade
from metrics.constantes import JANELA_DE_TRADE_S

# Cada taxa nova: (chave, numerador, denominador). O denominador é a amostra, e
# é um EVENTO (granadas, trocas, rounds vivo no plant, duelos), não "rounds
# jogados" -- por isso o perfil usa o piso de eventos para marcar amostra fraca.
TAXAS_DE_IMPACTO = [
    # utilidade
    ("dano_por_he", "dano_de_he", "hes_jogadas"),
    ("dano_por_molotov", "dano_de_molotov", "molotovs_jogados"),
    ("inimigos_cegos_por_flash", "inimigos_cegos", "flashes_jogadas"),
    ("segundos_de_cegueira_por_flash", "segundos_de_cegueira", "flashes_jogadas"),
    ("kills_de_flash_por_flash", "kills_de_flash", "flashes_jogadas"),
    ("cegueira_em_companheiros_por_flash", "segundos_de_cegueira_em_companheiros", "flashes_jogadas"),
    # situações (pós-plant = TR vivo no plant; retake = CT vivo no plant)
    ("pct_pos_plant_vencidos", "pos_plant_vencidos", "rounds_vivo_no_plant_tr"),
    ("kills_por_pos_plant", "kills_pos_plant_tr", "rounds_vivo_no_plant_tr"),
    ("pct_pos_plant_sobreviveu", "pos_plant_sobreviveu", "rounds_vivo_no_plant_tr"),
    ("pct_retakes_vencidos", "retakes_vencidos", "rounds_vivo_no_plant_ct"),
    ("kills_por_retake", "kills_pos_plant_ct", "rounds_vivo_no_plant_ct"),
    ("pct_retake_sobreviveu", "retake_sobreviveu", "rounds_vivo_no_plant_ct"),
    ("pct_aberturas_vencidas_tr", "aberturas_vencidas_tr", "duelos_de_abertura_tr"),
    ("pct_aberturas_vencidas_ct", "aberturas_vencidas_ct", "duelos_de_abertura_ct"),
]
# Medida sem numerador/denominador: a mediana, com o número de trocas ao lado.
TEMPO_DA_TROCA = "tempo_mediano_da_troca_s"

CATEGORIAS_DE_IMPACTO = {
    "Utilidade": ["dano_por_he", "dano_por_molotov", "inimigos_cegos_por_flash", "segundos_de_cegueira_por_flash",
                  "kills_de_flash_por_flash", "cegueira_em_companheiros_por_flash"],
    "Trocas": [TEMPO_DA_TROCA],
    "Situações": ["pct_pos_plant_vencidos", "kills_por_pos_plant", "pct_pos_plant_sobreviveu",
                  "pct_retakes_vencidos", "kills_por_retake", "pct_retake_sobreviveu",
                  "pct_aberturas_vencidas_tr", "pct_aberturas_vencidas_ct"],
}
# Métricas em que MAIS é pior (a página não as pinta como destaque positivo).
PIOR_QUANTO_MAIOR = {"cegueira_em_companheiros_por_flash"}


def _utilidade_por_round(granadas: pl.DataFrame) -> pl.DataFrame:
    """Do grenades_per_round: contagens e efeitos por (round, jogador)."""
    return granadas.select(
        "round_num", "steamid",
        pl.col("he_damage").fill_null(0).alias("dano_de_he"),
        pl.col("he_thrown").fill_null(0).alias("hes_jogadas"),
        pl.col("fire_damage").fill_null(0).alias("dano_de_molotov"),
        pl.col("molotov_thrown").fill_null(0).alias("molotovs_jogados"),
        pl.col("enemies_flashed").fill_null(0).alias("inimigos_cegos"),
        pl.col("enemy_blind_seconds").fill_null(0).alias("segundos_de_cegueira"),
        (pl.col("flash_kills").fill_null(0) + pl.col("flash_assists").fill_null(0)).alias("kills_de_flash"),
        pl.col("team_blind_seconds").fill_null(0).alias("segundos_de_cegueira_em_companheiros"),
        pl.col("flash_thrown").fill_null(0).alias("flashes_jogadas"),
    )


def _trocas(kills: pl.DataFrame, tickrate: int) -> pl.DataFrame:
    """(round, quem trocou, segundos entre a morte do companheiro e a troca).

    Uma linha por KILL de troca, como `basic_metrics.identify_trade_kills`: uma
    kill que vinga duas mortes conta uma vez, com o tempo até a mais recente --
    é a ela que o jogador reagiu."""
    pares = _pares_de_trade(kills, JANELA_DE_TRADE_S, tickrate)
    return (pares.group_by("kill_id", maintain_order=True)
            .agg(pl.col("round_num").first(), pl.col("attacker_steamid").first().alias("steamid"),
                 ((pl.col("tick") - pl.col("tick_prev")).min() / tickrate).alias("segundos_da_troca"))
            .drop("kill_id"))


def _situacoes_por_round(kills: pl.DataFrame, rounds: pl.DataFrame, presentes: pl.DataFrame) -> pl.DataFrame:
    """Por (round, jogador): vivo no plant, kills depois do plant, sobreviveu, round vencido."""
    plant = rounds.select("round_num", "bomb_plant", "end", "winner").filter(pl.col("bomb_plant").is_not_null())
    mortes = kills.filter(pl.col("victim_steamid").is_not_null()).select(
        "round_num", pl.col("victim_steamid").alias("steamid"), pl.col("tick").alias("tick_morte"))
    base = (presentes.join(plant, on="round_num", how="inner")
            .join(mortes, on=["round_num", "steamid"], how="left")
            .with_columns((pl.col("tick_morte").is_null() | (pl.col("tick_morte") >= pl.col("bomb_plant")))
                          .alias("vivo_no_plant")))
    inimigas = kills.filter(pl.col("attacker_steamid").is_not_null()
                            & (pl.col("attacker_side") != pl.col("victim_side")))
    depois = (inimigas.join(plant.select("round_num", "bomb_plant"), on="round_num", how="inner")
              .filter(pl.col("tick") >= pl.col("bomb_plant"))
              .group_by(["round_num", "attacker_steamid"], maintain_order=True).len()
              .rename({"attacker_steamid": "steamid", "len": "kills_depois_do_plant"}))
    return (base.filter(pl.col("vivo_no_plant"))
            .join(depois, on=["round_num", "steamid"], how="left")
            .with_columns(pl.col("kills_depois_do_plant").fill_null(0),
                          (pl.col("winner") == pl.col("side")).alias("venceu"),
                          pl.col("tick_morte").is_null().alias("sobreviveu"))
            .select("round_num", "steamid", "side", "kills_depois_do_plant", "venceu", "sobreviveu"))


def _aberturas_por_round(kills: pl.DataFrame) -> pl.DataFrame:
    """O duelo de abertura de cada round: a primeira kill em INIMIGO (fogo amigo e
    bomba não abrem), com quem venceu e quem perdeu e o lado de cada um."""
    inimigas = kills.filter(pl.col("attacker_steamid").is_not_null()
                            & (pl.col("attacker_side") != pl.col("victim_side")))
    primeira = inimigas.sort(["round_num", "tick"]).group_by("round_num", maintain_order=True).first()
    vence = primeira.select("round_num", pl.col("attacker_steamid").alias("steamid"),
                            pl.col("attacker_side").alias("side"), pl.lit(True).alias("venceu_abertura"))
    perde = primeira.select("round_num", pl.col("victim_steamid").alias("steamid"),
                            pl.col("victim_side").alias("side"), pl.lit(False).alias("venceu_abertura"))
    return pl.concat([vence, perde])


def impacto(granadas: pl.DataFrame, kills: pl.DataFrame, rounds: pl.DataFrame,
            presentes: pl.DataFrame, tickrate: int) -> tuple[pl.DataFrame, pl.DataFrame]:
    """(per_round, summary). `presentes` é (round_num, steamid, side) dos rounds que
    cada um jogou; `kills` já vem recortado nos rounds jogados."""
    presentes = presentes.select("round_num", "steamid", "side").unique(maintain_order=True, keep="first")
    ids = presentes.select("steamid").unique(maintain_order=True, keep="first")
    util = _utilidade_por_round(granadas)
    situ = _situacoes_por_round(kills, rounds, presentes)
    aber = _aberturas_por_round(kills)
    troca = _trocas(kills, tickrate)

    por_round = (presentes.join(util, on=["round_num", "steamid"], how="left")
                 .join(situ.drop("side"), on=["round_num", "steamid"], how="left")
                 .join(aber.drop("side"), on=["round_num", "steamid"], how="left")
                 .sort(["round_num", "steamid"]))

    def lado(df, s):
        return df.filter(pl.col("side") == s)

    resumo = (ids
              .join(util.group_by("steamid", maintain_order=True).agg(pl.exclude("round_num").sum()),
                    on="steamid", how="left")
              .join(troca.group_by("steamid", maintain_order=True).agg(
                    pl.col("segundos_da_troca").median().alias(TEMPO_DA_TROCA),
                    pl.len().alias("trocas_feitas")), on="steamid", how="left"))
    for s, sufixo, venceu, sobrev in (("t", "tr", "pos_plant_vencidos", "pos_plant_sobreviveu"),
                                      ("ct", "ct", "retakes_vencidos", "retake_sobreviveu")):
        resumo = resumo.join(lado(situ, s).group_by("steamid", maintain_order=True).agg(
            pl.len().alias(f"rounds_vivo_no_plant_{sufixo}"),
            pl.col("venceu").sum().alias(venceu),
            pl.col("kills_depois_do_plant").sum().alias(f"kills_pos_plant_{sufixo}"),
            pl.col("sobreviveu").sum().alias(sobrev)), on="steamid", how="left")
        resumo = resumo.join(lado(aber, s).group_by("steamid", maintain_order=True).agg(
            pl.len().alias(f"duelos_de_abertura_{sufixo}"),
            pl.col("venceu_abertura").sum().alias(f"aberturas_vencidas_{sufixo}")), on="steamid", how="left")
    contagens = sorted({n for _, n, _ in TAXAS_DE_IMPACTO} | {d for _, _, d in TAXAS_DE_IMPACTO} | {"trocas_feitas"})
    resumo = resumo.with_columns([pl.col(c).fill_null(0) for c in contagens if c in resumo.columns])
    resumo = resumo.with_columns(
        [pl.col(n).cast(pl.Float64).alias(f"{chave}_n") for chave, n, _ in TAXAS_DE_IMPACTO]
        + [pl.col(d).cast(pl.Float64).alias(f"{chave}_d") for chave, _, d in TAXAS_DE_IMPACTO]
        + [pl.when(pl.col(d) > 0).then(pl.col(n) / pl.col(d)).otherwise(None).alias(chave)
           for chave, n, d in TAXAS_DE_IMPACTO]
        + [pl.col("trocas_feitas").cast(pl.Float64).alias(f"{TEMPO_DA_TROCA}_d")]
    )
    return por_round, resumo.sort("steamid")


# --- Como a página mostra (decisão 18: texto do Python) -----------------------
# (rótulo, formato do número, o que o denominador conta -- para o bruto "n de d")
ROTULOS = {
    "dano_por_he": ("Dano por HE", "num1", "HEs"),
    "dano_por_molotov": ("Dano por molotov", "num1", "molotovs"),
    "inimigos_cegos_por_flash": ("Inimigos cegos por flash", "num2", "flashes"),
    "segundos_de_cegueira_por_flash": ("Segundos de cegueira por flash", "num1", "flashes"),
    "kills_de_flash_por_flash": ("Kills em inimigo cego por flash", "num2", "flashes"),
    "cegueira_em_companheiros_por_flash": ("Cegueira nos companheiros por flash (s)", "num1", "flashes"),
    TEMPO_DA_TROCA: ("Tempo mediano da troca (s)", "num2", "trocas"),
    "pct_pos_plant_vencidos": ("Pós-plant vencidos", "pct", "rounds vivo no plant (TR)"),
    "kills_por_pos_plant": ("Kills por pós-plant", "num2", "rounds vivo no plant (TR)"),
    "pct_pos_plant_sobreviveu": ("Sobreviveu ao pós-plant", "pct", "rounds vivo no plant (TR)"),
    "pct_retakes_vencidos": ("Retakes vencidos", "pct", "rounds vivo no plant (CT)"),
    "kills_por_retake": ("Kills por retake", "num2", "rounds vivo no plant (CT)"),
    "pct_retake_sobreviveu": ("Sobreviveu ao retake", "pct", "rounds vivo no plant (CT)"),
    "pct_aberturas_vencidas_tr": ("Duelos de abertura vencidos (TR)", "pct", "duelos de abertura (TR)"),
    "pct_aberturas_vencidas_ct": ("Duelos de abertura vencidos (CT)", "pct", "duelos de abertura (CT)"),
}
# Aberto por padrão: só Utilidade. É o grupo com mais eventos por partida (toda
# granada conta) e o que já estava calculado e nunca tinha ido para a tela.
# Trocas e Situações abrem com um clique: as situações têm poucos casos por
# partida (rounds vivo no plant, um duelo de abertura por round), e quase toda
# célula sai marcada como amostra fraca -- abertas, dominariam a leitura com
# números que não sustentam conclusão.
ABERTOS_POR_PADRAO = {"Utilidade"}
TEXTO_DO_BLOCO = ("O que a utilidade, as trocas e as situações de cada jogador produziram nesta partida. "
                  "Cada número vem com o bruto e com a régua anônima do corpus; amostra pequena aparece "
                  "esmaecida. A cegueira nos companheiros conta contra.")


def para_a_pagina() -> dict:
    """Grupos, rótulos e texto do bloco "Impacto além do placar" da aba Jogadores."""
    return {
        "titulo": "Impacto além do placar",
        "texto": TEXTO_DO_BLOCO,
        "grupos": [
            {"nome": nome, "aberto": nome in ABERTOS_POR_PADRAO,
             "metricas": [{"chave": c, "rotulo": ROTULOS[c][0], "formato": ROTULOS[c][1],
                           "unidade_do_bruto": ROTULOS[c][2], "pior_quanto_maior": c in PIOR_QUANTO_MAIOR}
                          for c in chaves]}
            for nome, chaves in CATEGORIAS_DE_IMPACTO.items()
        ],
    }
