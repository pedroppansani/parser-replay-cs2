"""
Métricas de utility (Fase 4): o que cada granada de fato produziu.

Por que esse módulo existe separado do `basic_metrics.calculate_utility_damage`:
aquela métrica responde "quanto de dano de granada o jogador fez", e dano é a
parte MENOS importante da utility em nível competitivo. A flash que cega dois
defensores por 2s não aparece em lugar nenhum num número de dano, e é ela que
ganha o round. Molotov que tira um jogador de um ângulo também causa 0 de dano
na maioria das vezes -- o efeito é o espaço, não o HP.

Fonte de dados: o evento `player_blind` do demo, que o awpy não parseia por
padrão (ver `parsing/parser.EXTRA_EVENTS`). É o único lugar que diz QUEM ficou
cego, POR QUANTO TEMPO e POR CULPA DE QUEM.

Decisões de jogo registradas aqui:

1. Flash curta não é flash. Abaixo de EFFECTIVE_BLIND_SECONDS o inimigo virou a
   tempo ou pegou a borda do cone -- ele perde o HUD, não a briga. Contar essas
   como "inimigo cegado" infla o número de quem joga flash de qualquer jeito. O
   tempo cru continua reportado à parte, então nada fica escondido.

2. Team flash e self flash NÃO são descontados do número de inimigos cegados.
   São erros diferentes com custos diferentes (cegar o próprio entry mata o
   round; se autocegar é problema só seu), e somar tudo num "saldo" apagaria os
   dois. Ficam em colunas próprias.

3. Flash assist exige que a vítima ainda estivesse cega pela MINHA flash quando
   morreu. Não é "morreu perto da minha flash": é a janela de cegueira daquele
   evento específico, com uma folga curta (ver FLASH_ASSIST_GRACE_SECONDS).

4. Matar você mesmo um inimigo que a sua flash cegou não é assist, é kill --
   mas é um comportamento diferente de quem flasha pro time entrar. As duas
   coisas ficam em colunas separadas (`flash_assists` e `flash_kills`).

5. Flash que não cegou ninguém é reportada como fato, sem virar nota. Pop flash
   em espaço vazio pra negar um peek é jogada válida e não deixa rastro no
   demo -- transformar isso em "utility desperdiçada" seria dar nota pra uma
   coisa que os dados não distinguem.
"""
from __future__ import annotations

import polars as pl

from metrics.basic_metrics import enemy_damages

# Classes de entidade do demo -> categoria legível.
#
# SÓ projéteis entram aqui, e isso é a correção mais importante do módulo. A
# tabela `grenades` do awpy mistura duas coisas com nomes quase iguais:
#
#   CFlashbangProjectile  -> a flash que foi ARREMESSADA e está voando
#   CFlashbang            -> a flash PARADA NO INVENTÁRIO, cuja posição é a do
#                            jogador que a está carregando, do começo do round
#                            até ele jogar (ou morrer com ela na mão)
#
# Contar as duas classes como "granada jogada" inflava o número de arremessos em
# ~2,5x (965 entidades contra 388 arremessos reais na partida de teste) e, no
# replay, desenhava um ponto colorido seguindo cada jogador o round inteiro,
# como se todo mundo estivesse com uma granada no ar o tempo todo.
#
# Validação: a contagem de projéteis bate exatamente com os eventos de detonação
# do demo (88 CFlashbangProjectile = 88 flashbang_detonate; 102
# CHEGrenadeProjectile = 102 hegrenade_detonate). Há teste travando isso.
PROJECTILE_KIND = {
    "CHEGrenadeProjectile": "he",
    "CFlashbangProjectile": "flash",
    "CSmokeGrenadeProjectile": "smoke",
    "CMolotovProjectile": "molotov",
    "CDecoyProjectile": "decoy",
}

KIND_ORDER = ("flash", "smoke", "molotov", "he", "decoy")

# Dano de granada, separado por tipo. O awpy reporta fogo como "inferno" no
# player_hurt, independente de ter vindo de molotov ou incendiária.
HE_WEAPONS = {"hegrenade"}
FIRE_WEAPONS = {"inferno", "molotov", "incgrenade"}

# Abaixo disso o inimigo perde o HUD, não a briga -- ver decisão 1 no topo.
# Leetify usa faixa parecida pra separar flash "efetiva"; deixei como constante
# porque é ponto de calibração, não verdade absoluta.
EFFECTIVE_BLIND_SECONDS = 1.0

# Folga depois do fim da cegueira pra kill ainda contar como assist. A visão não
# volta instantaneamente: o branco desaparece progressivamente, e quem acabou de
# levar flash ainda está reposicionando a mira nos primeiros instantes.
FLASH_ASSIST_GRACE_SECONDS = 0.5


def _empty_kind_columns() -> list[pl.Expr]:
    return [pl.lit(0, dtype=pl.Int32).alias(f"{k}_thrown") for k in KIND_ORDER]


def grenades_thrown(grenades: pl.DataFrame, roster: pl.DataFrame) -> pl.DataFrame:
    """Quantas granadas de cada tipo o jogador jogou, por round.

    Conta ENTIDADES (uma linha por granada), não samples de trajetória: a tabela
    `grenades` do awpy tem uma linha por posição amostrada, então contar linhas
    contaria a mesma granada dezenas de vezes. E conta só projéteis -- ver a nota
    em PROJECTILE_KIND sobre granada carregada vs. granada arremessada.

    Usa a trajetória e não os eventos de detonação de propósito -- granada
    lançada por quem morre no ar existe na trajetória e é uma decisão de jogo
    tomada, mesmo que o efeito tenha sido perdido.
    """
    base = roster.select(["round_num", "steamid", "name"]).unique(maintain_order=True)

    if grenades is None or grenades.height == 0:
        return base.with_columns(_empty_kind_columns()).sort(["steamid", "round_num"])

    per_entity = (
        grenades.group_by(["round_num", "entity_id"], maintain_order=True)
        .agg(
            pl.col("thrower_steamid").first().alias("steamid"),
            pl.col("grenade_type").first().alias("grenade_type"),
        )
        .with_columns(
            pl.col("grenade_type")
            .replace_strict(PROJECTILE_KIND, default=None)
            .alias("kind")
        )
        .filter(pl.col("kind").is_not_null())
    )

    counts = (
        per_entity.group_by(["round_num", "steamid", "kind"], maintain_order=True)
        .agg(pl.len().alias("n"))
        .pivot(on="kind", index=["round_num", "steamid"], values="n")
    )

    out = base.join(counts, on=["round_num", "steamid"], how="left")
    for kind in KIND_ORDER:
        col = pl.col(kind).fill_null(0) if kind in out.columns else pl.lit(0)
        out = out.with_columns(col.cast(pl.Int32).alias(f"{kind}_thrown"))

    return out.select(
        ["round_num", "steamid", "name"] + [f"{k}_thrown" for k in KIND_ORDER]
    ).sort(["steamid", "round_num"])


def flash_impact(
    player_blind: pl.DataFrame | None,
    kills: pl.DataFrame,
    roster: pl.DataFrame,
    tickrate: int = 128,
) -> pl.DataFrame:
    """Efeito das flashes de cada jogador, por round.

    Colunas devolvidas (todas por round, por jogador que ARREMESSOU):
      enemies_flashed       inimigos cegados acima do limiar efetivo
      enemy_blind_seconds   soma do tempo de cegueira imposto a inimigos
      teammates_flashed     companheiros cegados acima do limiar (custo, não ganho)
      team_blind_seconds    soma do tempo de cegueira imposto ao próprio time
      self_blind_seconds    tempo que o jogador se cegou sozinho
      flash_assists         inimigo morto por um COMPANHEIRO enquanto cego por mim
      flash_kills           inimigo morto por MIM enquanto cego pela minha flash
    """
    base = roster.select(["round_num", "steamid", "name"]).unique(maintain_order=True)
    zero = base.with_columns(
        pl.lit(0, dtype=pl.Int32).alias("enemies_flashed"),
        pl.lit(0.0).alias("enemy_blind_seconds"),
        pl.lit(0, dtype=pl.Int32).alias("teammates_flashed"),
        pl.lit(0.0).alias("team_blind_seconds"),
        pl.lit(0.0).alias("self_blind_seconds"),
        pl.lit(0, dtype=pl.Int32).alias("flash_assists"),
        pl.lit(0, dtype=pl.Int32).alias("flash_kills"),
    )

    if player_blind is None or player_blind.height == 0:
        return zero.sort(["steamid", "round_num"])

    blinds = player_blind.filter(
        pl.col("attacker_steamid").is_not_null() & pl.col("user_steamid").is_not_null()
    ).select(
        pl.col("round_num"),
        pl.col("tick"),
        pl.col("attacker_steamid").alias("steamid"),
        pl.col("attacker_side"),
        pl.col("user_steamid").alias("victim_steamid"),
        pl.col("user_side").alias("victim_side"),
        pl.col("blind_duration").cast(pl.Float64),
    ).with_columns(
        (pl.col("steamid") == pl.col("victim_steamid")).alias("is_self"),
        (pl.col("attacker_side") == pl.col("victim_side")).alias("same_side"),
    )

    effective = pl.col("blind_duration") >= EFFECTIVE_BLIND_SECONDS
    on_enemy = ~pl.col("same_side")
    on_mate = pl.col("same_side") & ~pl.col("is_self")

    agg = (
        blinds.group_by(["round_num", "steamid"], maintain_order=True)
        .agg(
            (on_enemy & effective).sum().cast(pl.Int32).alias("enemies_flashed"),
            pl.when(on_enemy).then(pl.col("blind_duration")).otherwise(0.0).sum().alias("enemy_blind_seconds"),
            (on_mate & effective).sum().cast(pl.Int32).alias("teammates_flashed"),
            pl.when(on_mate).then(pl.col("blind_duration")).otherwise(0.0).sum().alias("team_blind_seconds"),
            pl.when(pl.col("is_self")).then(pl.col("blind_duration")).otherwise(0.0).sum().alias("self_blind_seconds"),
        )
    )

    assists = _flash_assists(blinds, kills, tickrate)

    return (
        base.join(agg, on=["round_num", "steamid"], how="left")
        .join(assists, on=["round_num", "steamid"], how="left")
        .with_columns(
            pl.col("enemies_flashed").fill_null(0).cast(pl.Int32),
            pl.col("enemy_blind_seconds").fill_null(0.0),
            pl.col("teammates_flashed").fill_null(0).cast(pl.Int32),
            pl.col("team_blind_seconds").fill_null(0.0),
            pl.col("self_blind_seconds").fill_null(0.0),
            pl.col("flash_assists").fill_null(0).cast(pl.Int32),
            pl.col("flash_kills").fill_null(0).cast(pl.Int32),
        )
        .sort(["steamid", "round_num"])
    )


def _flash_assists(blinds: pl.DataFrame, kills: pl.DataFrame, tickrate: int) -> pl.DataFrame:
    """Kills que aconteceram com a vítima ainda cega pela flash de alguém.

    Casa cada morte com os eventos de cegueira DAQUELA vítima naquele round cuja
    janela (início + duração + folga) ainda cobria o tick da morte. Separar por
    quem matou é o que distingue assist (o time aproveitou) de kill (o próprio
    flasher aproveitou).
    """
    grace = FLASH_ASSIST_GRACE_SECONDS * tickrate

    enemy_kills = kills.filter(
        pl.col("attacker_steamid").is_not_null()
        & pl.col("victim_steamid").is_not_null()
        & (pl.col("attacker_side") != pl.col("victim_side"))
    ).select(
        pl.col("round_num"),
        pl.col("tick").alias("kill_tick"),
        pl.col("attacker_steamid").alias("killer_steamid"),
        pl.col("victim_steamid"),
    )

    matched = (
        blinds.filter(~pl.col("same_side"))
        .join(enemy_kills, on=["round_num", "victim_steamid"], how="inner")
        .filter(
            (pl.col("kill_tick") >= pl.col("tick"))
            & (pl.col("kill_tick") <= pl.col("tick") + pl.col("blind_duration") * tickrate + grace)
        )
        # a mesma morte pode casar com mais de uma flash (duas pessoas flasharam o
        # mesmo inimigo); cada flasher leva o crédito uma vez só por morte
        .unique(subset=["round_num", "steamid", "victim_steamid", "kill_tick"], maintain_order=True, keep="first")
    )

    return (
        matched.group_by(["round_num", "steamid"], maintain_order=True)
        .agg(
            (pl.col("killer_steamid") != pl.col("steamid")).sum().cast(pl.Int32).alias("flash_assists"),
            (pl.col("killer_steamid") == pl.col("steamid")).sum().cast(pl.Int32).alias("flash_kills"),
        )
    )


def utility_damage_split(damages: pl.DataFrame, roster: pl.DataFrame) -> pl.DataFrame:
    """Dano de granada separado entre HE e fogo, por round.

    O agregado (HE + fogo) já existe em `basic_metrics`; a separação importa
    porque as duas armas jogam papéis diferentes: HE é dano de execução e de
    chip, molotov é negação de espaço que às vezes cobra dano de quem insiste.
    """
    base = roster.select(["round_num", "steamid", "name"]).unique(maintain_order=True)

    by_weapon = (
        enemy_damages(damages)
        .filter(pl.col("weapon").is_in(HE_WEAPONS | FIRE_WEAPONS))
        .with_columns(
            pl.when(pl.col("weapon").is_in(HE_WEAPONS))
            .then(pl.lit("he_damage"))
            .otherwise(pl.lit("fire_damage"))
            .alias("bucket")
        )
        .group_by(["round_num", "attacker_steamid", "bucket"], maintain_order=True)
        .agg(pl.col("dmg_health_real").sum().alias("dmg"))
        .rename({"attacker_steamid": "steamid"})
        .pivot(on="bucket", index=["round_num", "steamid"], values="dmg")
    )

    out = base.join(by_weapon, on=["round_num", "steamid"], how="left")
    for col in ("he_damage", "fire_damage"):
        expr = pl.col(col).fill_null(0) if col in out.columns else pl.lit(0)
        out = out.with_columns(expr.cast(pl.Int64).alias(col))

    return out.select(["round_num", "steamid", "name", "he_damage", "fire_damage"]).sort(
        ["steamid", "round_num"]
    )


def first_utility_time(
    grenades: pl.DataFrame, rounds: pl.DataFrame, roster: pl.DataFrame, tickrate: int = 128
) -> pl.DataFrame:
    """Segundos entre o fim do freeze time e a primeira granada do jogador no round.

    Separa quem abre a execução com utility de quem guarda granada pro retake ou
    pro final do round. Null = não jogou nenhuma granada naquele round.

    Só projéteis: a granada carregada no inventário existe desde o começo do
    round, e considerá-la daria "primeira utility" sempre negativa (antes do fim
    do freeze time), que foi exatamente o sintoma que revelou a mistura.
    """
    base = roster.select(["round_num", "steamid"]).unique(maintain_order=True)

    if grenades is None or grenades.height == 0:
        return base.with_columns(pl.lit(None, dtype=pl.Float64).alias("first_utility_s"))

    firsts = (
        grenades.filter(pl.col("grenade_type").is_in(list(PROJECTILE_KIND)))
        .group_by(["round_num", "thrower_steamid"], maintain_order=True)
        .agg(pl.col("tick").min().alias("first_tick"))
        .rename({"thrower_steamid": "steamid"})
        .join(rounds.select(["round_num", "freeze_end"]), on="round_num", how="left")
        .with_columns(((pl.col("first_tick") - pl.col("freeze_end")) / tickrate).alias("first_utility_s"))
        .select(["round_num", "steamid", "first_utility_s"])
    )

    return base.join(firsts, on=["round_num", "steamid"], how="left")


def compute_grenade_metrics(
    tables: dict[str, pl.DataFrame], roster: pl.DataFrame, tickrate: int = 128
) -> tuple[pl.DataFrame, pl.DataFrame]:
    """Junta tudo numa tabela por (round, jogador) e no agregado da partida."""
    grenades = tables.get("grenades")

    per_round = (
        grenades_thrown(grenades, roster)
        .join(
            flash_impact(tables.get("player_blind"), tables["kills"], roster, tickrate).drop("name"),
            on=["round_num", "steamid"],
            how="left",
        )
        .join(utility_damage_split(tables["damages"], roster).drop("name"), on=["round_num", "steamid"], how="left")
        .join(first_utility_time(grenades, tables["rounds"], roster, tickrate), on=["round_num", "steamid"], how="left")
        .with_columns(
            (pl.sum_horizontal(f"{k}_thrown" for k in KIND_ORDER)).cast(pl.Int32).alias("nades_thrown"),
            (pl.col("he_damage") + pl.col("fire_damage")).alias("utility_damage"),
        )
    )

    rounds_played = per_round["round_num"].n_unique()

    summary = (
        per_round.group_by(["steamid", "name"], maintain_order=True)
        .agg(
            pl.col("nades_thrown").sum().alias("nades_thrown"),
            *[pl.col(f"{k}_thrown").sum().alias(f"{k}_thrown") for k in KIND_ORDER],
            pl.col("enemies_flashed").sum().alias("enemies_flashed"),
            pl.col("enemy_blind_seconds").sum().alias("enemy_blind_seconds"),
            pl.col("teammates_flashed").sum().alias("teammates_flashed"),
            pl.col("team_blind_seconds").sum().alias("team_blind_seconds"),
            pl.col("self_blind_seconds").sum().alias("self_blind_seconds"),
            pl.col("flash_assists").sum().alias("flash_assists"),
            pl.col("flash_kills").sum().alias("flash_kills"),
            pl.col("he_damage").sum().alias("he_damage"),
            pl.col("fire_damage").sum().alias("fire_damage"),
            pl.col("utility_damage").sum().alias("utility_damage"),
            pl.col("first_utility_s").median().alias("median_first_utility_s"),
            pl.col("round_num").n_unique().alias("rounds_played"),
        )
        .with_columns(
            (pl.col("nades_thrown") / pl.col("rounds_played")).alias("nades_per_round"),
            (pl.col("utility_damage") / pl.col("rounds_played")).alias("utility_damage_per_round"),
            # tempo de cegueira imposto a inimigo por flash arremessada: é a
            # medida de PONTARIA de flash. Quem joga muita flash e cega pouco
            # aparece aqui, e não no total bruto.
            pl.when(pl.col("flash_thrown") > 0)
            .then(pl.col("enemy_blind_seconds") / pl.col("flash_thrown"))
            .otherwise(None)
            .alias("blind_seconds_per_flash"),
        )
        .sort("enemy_blind_seconds", descending=True)
    )

    return per_round, summary.with_columns(pl.lit(rounds_played).alias("match_rounds"))
