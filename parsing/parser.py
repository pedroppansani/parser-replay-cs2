"""
Wrapper fino em cima do awpy.Demo.

Por que esse módulo existe (e não só chamar awpy.Demo direto no dashboard/notebook):
  - Centraliza qual conjunto de tabelas brutas a gente usa (rounds, kills, damages, ticks).
  - Padroniza a persistência em parquet: parsear um .dem de 200MB demora ~15s e consome
    bastante CPU, então a gente faz isso uma vez e reaproveita os dados processados.
  - Separa claramente "dados crus do awpy" (data/interim/) de "métricas calculadas"
    (data/processed/) -- só o segundo é leve o suficiente pra ir pro repositório/dashboard
    público. Ver README para a lógica completa de por que separamos assim.
"""
from __future__ import annotations

import json
from pathlib import Path

import polars as pl
from awpy import Demo
from awpy.parsers.rounds import apply_round_num

# Ticks é tratado à parte das outras tabelas porque é MUITO maior (uma linha por
# jogador por snapshot de tick -- ~1 milhão de linhas num BO1 de 22 rounds) e nem
# toda métrica da Fase 1 precisa dele (só KAST, pra saber quem sobreviveu o round).
EVENT_TABLES = ("rounds", "kills", "damages", "shots", "grenades")
ALL_TABLES = EVENT_TABLES + ("ticks",)

# `player_blind` não está na lista padrão do awpy, e é o único lugar do demo que
# diz QUEM ficou cego, POR QUANTO TEMPO e POR CULPA DE QUEM. Sem ele, flash só
# aparece como um ponto voando no mapa: dá pra ver a granada, não o efeito dela.
EXTRA_EVENTS = ["player_blind"]

# Eventos de detonação: o awpy monta tabelas prontas pra smoke e inferno (que têm
# duração), mas flash e HE detonam num instante e ficam só nos eventos crus. São
# eles que dizem ONDE a granada explodiu de fato -- a trajetória sozinha termina
# no último sample antes da explosão, que pode ser metros antes.
GRENADE_EVENT_TABLES = (
    "player_blind",
    "flashbang_detonate",
    "hegrenade_detonate",
    "smokegrenade_detonate",
    "inferno_startburn",
)

# Propriedades por jogador que a gente extrai de cada tick. A Fase 1 só precisava
# de posição e vida; as métricas autorais da Fase 2 precisam de mais:
#   pitch/yaw           -> crosshair placement (pra onde a mira estava apontando)
#   active_weapon_name  -> detectar quem estava de AWP na mão naquele momento
#   is_scoped/zoom_lvl  -> AWP segurando ângulo (scopado parado) vs. peek
#   flash_duration      -> descartar amostras de mira com o jogador cego (a mira
#                          de quem está flashado não diz nada sobre disciplina)
#   is_walking          -> estado de movimento (andando de shift vs. correndo)
PLAYER_PROPS = [
    "pitch",
    "yaw",
    "active_weapon_name",
    "is_alive",
    "is_scoped",
    "zoom_lvl",
    "flash_duration",
    "is_walking",
    "armor_value",
    "current_equip_value",
]


def parse_demo(
    dem_path: Path | str,
    tickrate: int = 128,
    verbose: bool = False,
    player_props: list[str] | None = None,
) -> Demo:
    """Parseia um .dem e devolve o objeto Demo do awpy com as tabelas já populadas."""
    dem_path = Path(dem_path)
    if not dem_path.exists():
        raise FileNotFoundError(f"Demo não encontrado: {dem_path}")

    demo = Demo(path=dem_path, tickrate=tickrate, verbose=verbose)
    demo.parse(
        events=demo.default_events + EXTRA_EVENTS,
        player_props=player_props if player_props is not None else PLAYER_PROPS,
    )
    return demo


def grenade_event_tables(demo: Demo) -> dict[str, pl.DataFrame]:
    """Eventos crus de granada, já com round_num aplicado.

    Vêm de `demo.events` (o dict de eventos brutos) e não de propriedades prontas
    do awpy, então chegam sem round_num -- é aqui que ele é colado, pra quem
    consumir não precisar refazer o casamento por faixa de tick.
    """
    out: dict[str, pl.DataFrame] = {}
    for name in GRENADE_EVENT_TABLES:
        df = demo.events.get(name)
        if df is None or df.height == 0:
            continue
        out[name] = apply_round_num(df=df, rounds_df=demo.rounds, tick_col="tick").filter(
            pl.col("round_num").is_not_null()
        )
    return out


def save_interim(demo: Demo, interim_dir: Path | str, match_id: str) -> dict[str, Path]:
    """
    Salva as tabelas brutas do awpy (rounds/kills/damages/ticks) como parquet.

    Isso fica em data/interim/ -- NÃO vai pro git (é pesado, principalmente ticks).
    Serve só pra eu poder reabrir os dados crus localmente sem reparsear o .dem
    toda vez que eu ajustar uma métrica.
    """
    match_dir = Path(interim_dir) / match_id
    match_dir.mkdir(parents=True, exist_ok=True)

    tables = {
        "rounds": demo.rounds,
        "kills": demo.kills,
        "damages": demo.damages,
        "shots": demo.shots,
        "grenades": demo.grenades,
        "bomb": demo.bomb,
        "smokes": demo.smokes,
        "infernos": demo.infernos,
        "ticks": demo.ticks,
    }
    tables.update(grenade_event_tables(demo))

    paths: dict[str, Path] = {}
    for name, df in tables.items():
        p = match_dir / f"{name}.parquet"
        df.write_parquet(p)
        paths[name] = p

    header_path = match_dir / "header.json"
    header_path.write_text(json.dumps(demo.header, default=str, ensure_ascii=False, indent=2))
    paths["header"] = header_path

    return paths


def load_interim(interim_dir: Path | str, match_id: str) -> dict[str, pl.DataFrame]:
    """Recarrega as tabelas brutas salvas por save_interim, sem precisar do .dem de novo."""
    match_dir = Path(interim_dir) / match_id
    tables = {name: pl.read_parquet(match_dir / f"{name}.parquet") for name in ALL_TABLES}

    # Opcionais: um parse antigo (ou uma partida sem nenhuma flash) pode não ter
    # esses arquivos, e as métricas de utility tratam ausência como zero.
    for name in GRENADE_EVENT_TABLES + ("smokes", "infernos", "bomb"):
        path = match_dir / f"{name}.parquet"
        if path.exists():
            tables[name] = pl.read_parquet(path)
    return tables
