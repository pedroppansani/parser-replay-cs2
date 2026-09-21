"""
Crosshair placement (Fase 2) -- a métrica mais dependente de julgamento de jogo.

O que NÃO fazemos aqui, de propósito: calcular só "distância angular até o
inimigo mais próximo". Esse número pune exatamente o comportamento que se quer
em nível competitivo -- pré-mirar o ângulo por onde o inimigo VAI aparecer, antes
dele aparecer. Quem pré-mira bem passa a maior parte do tempo com o inimigo
longe da mira (porque o inimigo ainda nem entrou no ângulo) e ainda assim está
fazendo a coisa certa.

Então o score aqui tem três componentes, aplicados conforme a situação:

1. ALTURA DA MIRA (sempre vale, tenha inimigo ou não)
   A mira tem que estar na linha da cabeça. Mirar no chão é o erro clássico que
   custa o tempo de reação subindo a mira; mirar no céu é raro mas acontece
   depois de pular/cair. Em terreno plano, mira na altura da cabeça significa
   pitch ≈ 0 (a altura dos olhos e da cabeça do inimigo são ~a mesma).
   Como não temos a malha de navegação do mapa (o download dos assets do awpy
   exige rede liberada), o "nível correto" é estimado de duas formas:
     - referência por região: a mediana do pitch dos atacantes NAS KILLS daquela
       região do mapa. Isso absorve a inclinação real do terreno (rampa do
       ancient, por exemplo) sem precisar de geometria do mapa;
     - fallback plano: quando a região não tem kills suficientes, usa 0°.

2. DIREÇÃO NA ENTRADA DA BRIGA
   Só faz sentido cobrar "mira no inimigo" quando o jogador estava efetivamente
   entrando numa briga. Um inimigo a 1200u atrás de uma parede não devia ser
   cobrado -- e essa é a diferença entre essa métrica e um contador ingênuo de
   distância angular.
   Como não temos raycast de visibilidade (a malha de navegação do awpy exige
   download que o ambiente não libera), uso o comportamento como proxy de
   contato: a amostra só entra nesse componente se o jogador atirou, causou ou
   tomou dano dentro dos próximos `CONTACT_WINDOW_SECONDS`. Ou seja, mede-se o
   placement no caminho PRA briga -- que é exatamente o que importa.
   (Medido na prática: sem esse filtro, o erro angular mediano até o "inimigo
   mais próximo" fica em 36-117° mesmo entre profissionais, porque na maior parte
   do tempo o inimigo mais próximo não está visível. Com o filtro, o número passa
   a descrever briga de verdade.)

3. CRÉDITO DE PRÉ-FIRE (quando NÃO há inimigo em alcance)
   Se a mira está alinhada com um ângulo de entrada conhecido daquela região
   (ver metrics/map_angles.py), a amostra conta como placement BOM, não como
   "mira sem alvo". É esse componente que separa essa métrica de um contador
   ingênuo de distância angular.

Amostras descartadas (não dizem nada sobre disciplina de mira): jogador morto,
cego de flash, com faca/granada/bomba na mão, ou ainda no freeze time.

Todos os pesos e limiares são constantes nomeadas -- são justamente os botões
que eu vou girar comparando com demos que eu conheço.
"""
from __future__ import annotations

import numpy as np
import polars as pl

from metrics.geometry import (
    EYE_HEIGHT_STANDING,
    HEAD_HEIGHT,
    angle_between,
    horizontal_distance,
    pitch_to_target,
    view_vector,
    yaw_difference,
    yaw_to_target,
)
from metrics.map_angles import (
    DEFAULT_ANGLE_TOLERANCE_DEG,
    MIN_KILLS_FOR_DERIVED_ANGLE,
    build_angle_lookup,
    entry_angles_for_map,
)

# A cada quantos ticks tiramos uma amostra de mira. 16 ticks = 8 amostras por
# segundo a 128 tick: resolução suficiente pra capturar o placement enquanto o
# jogador se move, sem gerar milhões de linhas redundantes.
SAMPLE_EVERY_N_TICKS = 16

# Distância (unidades) dentro da qual um inimigo é considerado "em alcance de
# briga". ~1500u cobre as brigas normais de mapa; acima disso o inimigo
# geralmente nem está visível e cobrar mira nele seria injusto.
MAX_ENGAGEMENT_DISTANCE = 1500.0

# Janela (segundos) depois da amostra dentro da qual precisa haver um evento de
# contato do próprio jogador (tiro, dano causado ou dano sofrido) pra a amostra
# contar como "entrando na briga". 1s cobre o tempo entre pré-mirar o ângulo e
# o tiro sair, sem transformar o round inteiro em "briga".
CONTACT_WINDOW_SECONDS = 1.0

# Tolerâncias do componente de altura (graus de pitch).
# Até 5° do nível da cabeça = placement bom (em 500u de distância, 5° ≈ 44u de
# erro vertical, ainda dentro do corpo do inimigo).
PITCH_GOOD_DEG = 5.0
PITCH_BAD_DEG = 20.0  # a partir daqui, score de altura zera

# Tolerâncias do componente de direção quando há inimigo em alcance.
YAW_GOOD_DEG = 10.0
YAW_BAD_DEG = 60.0

# Flash acima disso (segundos restantes de cegueira) invalida a amostra.
MAX_FLASH_DURATION = 0.5

# Armas que não contam como "mirando" (faca, granadas, bomba).
NON_AIMING_WEAPONS = {
    "Knife",
    "Bayonet",
    "Flip Knife",
    "Karambit",
    "M9 Bayonet",
    "Butterfly Knife",
    "Skeleton Knife",
    "Stiletto Knife",
    "HE Grenade",
    "Flashbang",
    "Smoke Grenade",
    "Molotov",
    "Incendiary Grenade",
    "Decoy Grenade",
    "C4 Explosive",
}

# Peso de cada componente no score final da amostra.
WEIGHT_HEIGHT = 0.4
WEIGHT_DIRECTION = 0.6


def _linear_score(error: np.ndarray, good: float, bad: float) -> np.ndarray:
    """1.0 quando o erro é <= `good`, 0.0 quando >= `bad`, linear no meio."""
    return np.clip((bad - np.abs(error)) / (bad - good), 0.0, 1.0)


def build_pitch_reference(kills: pl.DataFrame, min_kills: int = MIN_KILLS_FOR_DERIVED_ANGLE) -> dict[str, float]:
    """Pitch de referência por região do mapa: a mediana do pitch dos atacantes
    nas kills daquela região.

    É o jeito de absorver a inclinação real do terreno sem ter a geometria do
    mapa: se as kills na rampa acontecem com pitch mediano de +7°, então +7° é o
    "nível da cabeça" efetivo naquela região, não 0°.
    """
    k = kills.filter(
        pl.col("attacker_place").is_not_null()
        & pl.col("attacker_pitch").is_not_null()
        & (~pl.col("weapon").is_in(["inferno", "planted_c4", "hegrenade"]))
    )
    if k.height == 0:
        return {}

    ref = (
        k.group_by("attacker_place", maintain_order=True)
        .agg(pl.col("attacker_pitch").median().alias("ref_pitch"), pl.len().alias("n"))
        .filter(pl.col("n") >= min_kills)
    )
    return {row["attacker_place"]: float(row["ref_pitch"]) for row in ref.iter_rows(named=True)}


def sample_aim_states(
    ticks: pl.DataFrame,
    rounds: pl.DataFrame,
    sample_every: int = SAMPLE_EVERY_N_TICKS,
) -> pl.DataFrame:
    """Seleciona os ticks que viram amostra de mira, já filtrando o que não conta."""
    in_play = rounds.select(["round_num", "freeze_end", "end"])

    return (
        ticks.join(in_play, on="round_num", how="inner")
        .filter(
            (pl.col("tick") >= pl.col("freeze_end"))
            & (pl.col("tick") <= pl.col("end"))
            & (pl.col("tick") % sample_every == 0)
            & pl.col("is_alive")
            & pl.col("pitch").is_not_null()
            & pl.col("yaw").is_not_null()
            & (pl.col("flash_duration").fill_null(0.0) <= MAX_FLASH_DURATION)
            & (~pl.col("active_weapon_name").is_in(NON_AIMING_WEAPONS))
            & pl.col("active_weapon_name").is_not_null()
        )
        .select(
            [
                "round_num",
                "tick",
                "steamid",
                "name",
                "side",
                "place",
                "X",
                "Y",
                "Z",
                "pitch",
                "yaw",
                "active_weapon_name",
            ]
        )
    )


def _nearest_enemy_per_sample(samples: pl.DataFrame, ticks: pl.DataFrame) -> pl.DataFrame:
    """Pra cada amostra, acha o inimigo vivo mais próximo naquele mesmo tick.

    Feito com um join por tick + filtro de lado oposto, e depois o mínimo de
    distância por amostra. É a operação mais pesada do módulo; por isso as
    amostras são espaçadas (SAMPLE_EVERY_N_TICKS).
    """
    enemies = ticks.filter(pl.col("is_alive")).select(
        [
            "round_num",
            "tick",
            pl.col("steamid").alias("enemy_steamid"),
            pl.col("side").alias("enemy_side"),
            pl.col("X").alias("enemy_X"),
            pl.col("Y").alias("enemy_Y"),
            pl.col("Z").alias("enemy_Z"),
        ]
    )

    joined = samples.join(enemies, on=["round_num", "tick"], how="left").filter(
        pl.col("enemy_side") != pl.col("side")
    )

    joined = joined.with_columns(
        (
            (pl.col("enemy_X") - pl.col("X")) ** 2
            + (pl.col("enemy_Y") - pl.col("Y")) ** 2
            + (pl.col("enemy_Z") - pl.col("Z")) ** 2
        )
        .sqrt()
        .alias("enemy_distance")
    )

    nearest = (
        joined.sort("enemy_distance")
        .group_by(["round_num", "tick", "steamid"], maintain_order=True)
        .agg(
            pl.col("enemy_X").first(),
            pl.col("enemy_Y").first(),
            pl.col("enemy_Z").first(),
            pl.col("enemy_distance").first(),
        )
    )

    return samples.join(nearest, on=["round_num", "tick", "steamid"], how="left")


def add_contact_window_flag(
    samples: pl.DataFrame,
    shots: pl.DataFrame,
    damages: pl.DataFrame,
    window_seconds: float = CONTACT_WINDOW_SECONDS,
    tickrate: int = 64,
) -> pl.DataFrame:
    """Marca as amostras que estão na janela que antecede um contato do jogador.

    Contato = o jogador atirou, causou dano ou tomou dano. É o proxy de "a briga
    aconteceu de verdade aqui", usado no lugar de visibilidade real.
    """
    window_ticks = int(window_seconds * tickrate)

    contact_events = pl.concat(
        [
            shots.select(
                pl.col("round_num"),
                pl.col("player_steamid").alias("steamid"),
                pl.col("tick").alias("contact_tick"),
            ),
            damages.filter(pl.col("attacker_steamid").is_not_null()).select(
                pl.col("round_num"),
                pl.col("attacker_steamid").alias("steamid"),
                pl.col("tick").alias("contact_tick"),
            ),
            damages.filter(pl.col("victim_steamid").is_not_null()).select(
                pl.col("round_num"),
                pl.col("victim_steamid").alias("steamid"),
                pl.col("tick").alias("contact_tick"),
            ),
        ],
        how="vertical",
    ).unique(maintain_order=True)

    # join_asof precisa das duas tabelas ordenadas pela chave temporal: pra cada
    # amostra, acha o próximo contato daquele jogador naquele round.
    samples_sorted = samples.sort("tick")
    contacts_sorted = contact_events.sort("contact_tick")

    joined = samples_sorted.join_asof(
        contacts_sorted,
        left_on="tick",
        right_on="contact_tick",
        by=["round_num", "steamid"],
        strategy="forward",
    )

    return joined.with_columns(
        (
            pl.col("contact_tick").is_not_null()
            & ((pl.col("contact_tick") - pl.col("tick")) <= window_ticks)
        ).alias("in_contact_window")
    )


def score_samples(
    samples: pl.DataFrame,
    pitch_reference: dict[str, float],
    angle_lookup: dict[tuple[str, str], np.ndarray],
    angle_tolerance: float = DEFAULT_ANGLE_TOLERANCE_DEG,
) -> pl.DataFrame:
    """Calcula os componentes do score de cada amostra.

    Colunas produzidas (todas ficam no output pra auditoria round a round):
      - `pitch_error_deg`: quanto a mira está fora do nível de cabeça da região
        (assinado: positivo = mira abaixo do nível, i.e. olhando pro chão)
      - `height_score`: 0-1 derivado do acima
      - `has_enemy_in_range`: se havia inimigo vivo dentro do alcance de briga
      - `enemy_aim_error_deg`: erro angular até a cabeça do inimigo (só quando há)
      - `prefire_match_deg`: distância até o ângulo de entrada mais próximo da
        região (só quando NÃO há inimigo em alcance)
      - `direction_score`: 0-1, vindo do inimigo quando há, ou do pré-fire quando não há
      - `crosshair_score`: combinação ponderada final, 0-100
    """
    n = samples.height
    if n == 0:
        return samples

    pitch = samples["pitch"].to_numpy().astype(float)
    yaw = samples["yaw"].to_numpy().astype(float)
    places = samples["place"].to_list()
    sides = samples["side"].to_list()

    # --- componente 1: altura da mira ---
    ref = np.array([pitch_reference.get(p, 0.0) for p in places], dtype=float)
    pitch_error = pitch - ref  # positivo = mirando mais pra baixo que a referência
    height_score = _linear_score(pitch_error, PITCH_GOOD_DEG, PITCH_BAD_DEG)

    # --- componente 2: direção na entrada da briga ---
    # Exige inimigo em alcance E contato real do jogador logo em seguida. Sem o
    # segundo filtro, a métrica vira "distância até o inimigo mais próximo",
    # que é justamente o que não queremos (ver docstring do módulo).
    dist = samples["enemy_distance"].to_numpy().astype(float)
    in_contact = samples["in_contact_window"].to_numpy().astype(bool)
    has_enemy = np.isfinite(dist) & (dist <= MAX_ENGAGEMENT_DISTANCE) & in_contact

    sx = samples["X"].to_numpy().astype(float)
    sy = samples["Y"].to_numpy().astype(float)
    sz = samples["Z"].to_numpy().astype(float) + EYE_HEIGHT_STANDING
    ex = np.nan_to_num(samples["enemy_X"].to_numpy().astype(float))
    ey = np.nan_to_num(samples["enemy_Y"].to_numpy().astype(float))
    ez = np.nan_to_num(samples["enemy_Z"].to_numpy().astype(float)) + HEAD_HEIGHT

    aim_vec = view_vector(pitch, yaw)
    to_enemy = np.stack([ex - sx, ey - sy, ez - sz], axis=-1)
    enemy_err = angle_between(aim_vec, to_enemy)
    enemy_err = np.where(has_enemy, enemy_err, np.nan)

    # --- componente 3: crédito de pré-fire (sem inimigo em alcance) ---
    prefire_match = np.full(n, np.nan)
    for i in range(n):
        if has_enemy[i]:
            continue
        angles = angle_lookup.get((places[i], sides[i]))
        if angles is None or angles.size == 0:
            continue
        prefire_match[i] = float(np.min(yaw_difference(np.full(angles.shape, yaw[i]), angles)))

    direction_score = np.zeros(n)
    # com inimigo: quão perto a mira está dele
    direction_score = np.where(
        has_enemy, _linear_score(np.nan_to_num(enemy_err, nan=999.0), YAW_GOOD_DEG, YAW_BAD_DEG), direction_score
    )
    # sem inimigo: quão perto a mira está de um ângulo de entrada conhecido
    prefire_score = _linear_score(np.nan_to_num(prefire_match, nan=999.0), angle_tolerance, angle_tolerance * 3)
    # amostras sem inimigo E sem ângulo conhecido na região ficam neutras (0.5):
    # não dá pra afirmar que o placement estava certo nem errado sem referência.
    no_reference = (~has_enemy) & np.isnan(prefire_match)
    direction_score = np.where(~has_enemy, np.where(no_reference, 0.5, prefire_score), direction_score)

    crosshair_score = 100.0 * (WEIGHT_HEIGHT * height_score + WEIGHT_DIRECTION * direction_score)

    return samples.with_columns(
        pl.Series("pitch_error_deg", pitch_error),
        pl.Series("height_score", height_score),
        pl.Series("has_enemy_in_range", has_enemy),
        # fill_nan(None) porque NaN em polars propaga pra dentro de median()/mean():
        # essas duas colunas são nulas por construção na maior parte das linhas
        # (cada amostra entra ou no componente de inimigo ou no de pré-fire).
        pl.Series("enemy_aim_error_deg", enemy_err).fill_nan(None),
        pl.Series("prefire_match_deg", prefire_match).fill_nan(None),
        pl.Series("direction_score", direction_score),
        pl.Series("crosshair_score", crosshair_score),
    )


def calculate_crosshair_metrics(
    tables: dict[str, pl.DataFrame],
    map_name: str,
    sample_every: int = SAMPLE_EVERY_N_TICKS,
) -> tuple[pl.DataFrame, pl.DataFrame, pl.DataFrame]:
    """Roda o pipeline completo de crosshair placement.

    Retorna (per_round, summary, samples):
      - samples: uma linha por amostra de mira (bruto, pra auditar de verdade)
      - per_round: média por jogador/round
      - summary: média por jogador na partida
    """
    ticks, kills, rounds = tables["ticks"], tables["kills"], tables["rounds"]

    pitch_reference = build_pitch_reference(kills)
    angles = entry_angles_for_map(map_name, kills)
    angle_lookup = build_angle_lookup(angles)

    samples = sample_aim_states(ticks, rounds, sample_every)
    samples = _nearest_enemy_per_sample(samples, ticks)
    samples = add_contact_window_flag(samples, tables["shots"], tables["damages"])
    samples = score_samples(samples, pitch_reference, angle_lookup)

    per_round = (
        samples.group_by(["round_num", "steamid", "name"], maintain_order=True)
        .agg(
            pl.col("crosshair_score").mean().alias("crosshair_score"),
            pl.col("height_score").mean().alias("height_score"),
            pl.col("direction_score").mean().alias("direction_score"),
            pl.col("pitch_error_deg").median().alias("median_pitch_error_deg"),
            pl.col("has_enemy_in_range").mean().alias("frac_entering_fight"),
            pl.col("enemy_aim_error_deg").median().alias("median_enemy_aim_error_deg"),
            pl.col("prefire_match_deg").median().alias("median_prefire_match_deg"),
            pl.len().alias("n_samples"),
        )
        .sort(["steamid", "round_num"])
    )

    summary = (
        samples.group_by(["steamid", "name"], maintain_order=True)
        .agg(
            pl.col("crosshair_score").mean().alias("crosshair_score"),
            pl.col("height_score").mean().alias("height_score"),
            pl.col("direction_score").mean().alias("direction_score"),
            pl.col("pitch_error_deg").median().alias("median_pitch_error_deg"),
            pl.col("enemy_aim_error_deg").median().alias("median_enemy_aim_error_deg"),
            pl.col("prefire_match_deg").median().alias("median_prefire_match_deg"),
            pl.col("has_enemy_in_range").sum().alias("n_fight_samples"),
            pl.len().alias("n_samples"),
        )
        .sort("crosshair_score", descending=True)
    )

    return per_round, summary, samples
