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

# `player_blind` NÃO está na lista padrão de eventos do awpy, e é o único lugar
# do demo que diz QUEM ficou cego, POR QUANTO TEMPO e POR CULPA DE QUEM. Sem
# ele, flash vira só um ponto voando no mapa: dá pra ver a granada, não o efeito
# — e toda métrica de utility que depende de cegueira zera em silêncio.
EXTRA_EVENTS = ["player_blind"]

# Eventos de detonação. O awpy monta tabela pronta pra smoke e inferno (que têm
# duração), mas flash e HE detonam num instante e ficam só nos eventos crus. São
# eles que dizem ONDE a granada explodiu: a trajetória termina no último sample
# antes da explosão, que a 4 Hz pode estar metros atrás.
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
    tickrate: int = 64,
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
    # O round de faca sai AQUI, antes de gravar: todo leitor do interim (as
    # métricas, o replay, a calibração do rating) recebe a partida já sem ele.
    tables, faca = remove_round_de_faca(tables)

    paths: dict[str, Path] = {}
    for name, df in tables.items():
        p = match_dir / f"{name}.parquet"
        df.write_parquet(p)
        paths[name] = p

    header = dict(demo.header)
    if faca:
        header["round_de_faca_removido"] = True
    header_path = match_dir / "header.json"
    header_path.write_text(json.dumps(header, default=str, ensure_ascii=False, indent=2))
    paths["header"] = header_path

    return paths


# ---------------------------------------------------------------------------
# Round de faca
# ---------------------------------------------------------------------------
#
# Em partida profissional o lado é decidido num round de faca antes do jogo, e
# algumas demos gravam esse round. O awpy o entrega como round 1, e ele quebra
# duas coisas de uma vez:
#   - a regra de lados (metrics/sides.py) supõe que o round 1 é o primeiro da
#     partida. Depois da faca o vencedor escolhe o lado, então os lados do
#     round 1 NÃO são os do primeiro tempo: Vitality x Spirit (Mirage) saiu
#     15-9 em 24 rounds, placar impossível -- o certo é 13-10;
#   - as estatísticas: as kills de faca entram no K-D de quem não jogou round
#     nenhum ainda.
#
# Critério: é o PRIMEIRO round, houve dano, e nenhum dano foi de arma de fogo.
# Um round de pistola sempre tem dano de pistola; medido nas partidas do corpus,
# o único round 1 sem dano de arma de fogo é o de faca, com 20 danos de faca.
# Um round de faca sem dano nenhum não é detectado -- ele acaba por eliminação,
# então não acontece na prática.

_FACA = r"(?i)knife|bayonet"


def round_de_faca(tables: dict[str, pl.DataFrame]) -> int | None:
    """Número do round de faca, se a partida começa com um. Senão None."""
    damages = tables.get("damages")
    rounds = tables.get("rounds")
    if damages is None or rounds is None or rounds.height == 0 or "weapon" not in damages.columns:
        return None
    primeiro = int(rounds["round_num"].min())
    armas = damages.filter(pl.col("round_num") == primeiro)["weapon"].cast(pl.Utf8)
    if armas.len() == 0 or not armas.str.contains(_FACA).all():
        return None
    return primeiro


def remove_round_de_faca(tables: dict[str, pl.DataFrame]) -> tuple[dict[str, pl.DataFrame], bool]:
    """Tira o round de faca de TODAS as tabelas e renumera os rounds seguintes.

    Renumerar é o que importa: a regra de lados e a numeração que o usuário vê
    ("round 1") têm que começar no primeiro round jogado de verdade.
    """
    faca = round_de_faca(tables)
    if faca is None:
        return tables, False
    limpo = {}
    for nome, df in tables.items():
        if df is None or "round_num" not in df.columns:
            limpo[nome] = df
            continue
        tipo = df.schema["round_num"]
        limpo[nome] = (
            df.filter(pl.col("round_num").is_null() | (pl.col("round_num") != faca))
            .with_columns(
                pl.when(pl.col("round_num") > faca)
                .then(pl.col("round_num") - 1)
                .otherwise(pl.col("round_num"))
                .cast(tipo)
                .alias("round_num")
            )
        )
    return limpo, True


# Colunas que guardam TICK em alguma tabela do interim. Na tabela de rounds as
# fronteiras do round têm nome próprio; nas de fumaça/fogo, início e fim.
_TICK_COLUMNS = {"tick", "start_tick", "end_tick", "start", "freeze_end", "end", "official_end", "bomb_plant"}


def merge_interim(interim_dir: Path | str, part_ids: list[str], dest_id: str) -> Path:
    """Funde as partes de uma demo dividida pelo GOTV num interim só.

    Quando o servidor reinicia no meio do mapa, o GOTV grava duas demos
    ("...-p1.dem", "...-p2.dem"). Cada uma recomeça a contagem de tick e de
    round do zero, e processadas separadamente viram duas "partidas" com placar
    falso -- o Overpass de FURIA x Vitality aparecia como 7-5 e 8-3 em vez de
    13-10. Para a HLTV é um mapa só, e é contra o mapa inteiro que o rating é
    calibrado.

    Cada parte depois da primeira é deslocada para depois da anterior: tick
    pelo maior tick já visto, round_num pelo maior round. `entity_id` não
    precisa de deslocamento -- toda agregação por entidade também agrupa por
    round, e os rounds não se repetem mais depois do deslocamento.

    A continuidade (mesmos jogadores, lados trocados no intervalo) é conferida
    por quem chama; aqui a ordem das partes é a ordem da lista.
    """
    interim_dir = Path(interim_dir)
    dest = interim_dir / dest_id
    dest.mkdir(parents=True, exist_ok=True)

    nomes = sorted({p.stem for pid in part_ids for p in (interim_dir / pid).glob("*.parquet")})
    fundido: dict[str, list[pl.DataFrame]] = {n: [] for n in nomes}
    desloc_tick, desloc_round = 0, 0

    for pid in part_ids:
        partes = {n: pl.read_parquet(interim_dir / pid / f"{n}.parquet")
                  for n in nomes if (interim_dir / pid / f"{n}.parquet").exists()}
        maior_tick, maior_round = 0, 0
        for nome, df in partes.items():
            ajustes = []
            for col in df.columns:
                if col in _TICK_COLUMNS and df[col].dtype.is_numeric():
                    ajustes.append((pl.col(col) + desloc_tick).cast(df[col].dtype).alias(col))
                    maior_tick = max(maior_tick, int(df[col].max() or 0))
            if "round_num" in df.columns:
                ajustes.append((pl.col("round_num") + desloc_round).cast(df["round_num"].dtype).alias("round_num"))
                maior_round = max(maior_round, int(df["round_num"].max() or 0))
            fundido[nome].append(df.with_columns(ajustes) if ajustes else df)
        desloc_tick += maior_tick + 1
        desloc_round += maior_round

    for nome, pedacos in fundido.items():
        if pedacos:
            pl.concat(pedacos, how="diagonal_relaxed").write_parquet(dest / f"{nome}.parquet")

    header = json.loads((interim_dir / part_ids[0] / "header.json").read_text(encoding="utf-8"))
    header["merged_from_parts"] = len(part_ids)
    (dest / "header.json").write_text(json.dumps(header, ensure_ascii=False, indent=2), encoding="utf-8")
    return dest


def load_interim(interim_dir: Path | str, match_id: str) -> dict[str, pl.DataFrame]:
    """Recarrega as tabelas brutas salvas por save_interim, sem precisar do .dem de novo."""
    match_dir = Path(interim_dir) / match_id
    tables = {name: pl.read_parquet(match_dir / f"{name}.parquet") for name in ALL_TABLES}

    # Opcionais: um parse antigo (ou uma partida sem nenhuma flash) pode não ter
    # esses arquivos, e as métricas de utility tratam ausência como zero. Sem
    # carregá-los aqui, porém, a ausência é SEMPRE — foi assim que as métricas de
    # flash zeraram sem ninguém perceber.
    for name in GRENADE_EVENT_TABLES + ("smokes", "infernos", "bomb"):
        path = match_dir / f"{name}.parquet"
        if path.exists():
            tables[name] = pl.read_parquet(path)

    # Limpeza obrigatória: mortes do tempo parado não pertencem a round nenhum.
    # Fica aqui para que TODO consumidor de --from-interim receba o dado limpo
    # sem precisar lembrar de filtrar (ver kills_do_round_jogado).
    tables["kills"] = kills_do_round_jogado(tables["kills"], tables["rounds"])
    return tables


# ---------------------------------------------------------------------------
# Limpeza: eventos que caem fora do round jogado
# ---------------------------------------------------------------------------
#
# O demo registra mortes no intervalo entre o `start` do round e o fim do freeze
# time. Não são warmup (o `is_warmup_period` já terminou antes do primeiro
# `start`): são jogadores se matando ou caindo do mapa no tempo parado, o que
# acontece bastante no período pré-partida do FACEIT -- em match_08 o freeze do
# round 1 dura 93 segundos, contra 20 dos demais.
#
# Elas não pertencem a round nenhum, e deixá-las entrar produziu dois sintomas
# ao mesmo tempo: timestamp negativo no timeline (-69,0s, contado a partir do
# fim do freeze) e jogador ganhando +1 kill por se matar, porque a linha traz
# `attacker_steamid == victim_steamid`.
#
# Medido nas 9 partidas: 11 mortes antes do freeze_end, 4 delas com vítima igual
# ao atacante.
#
# A cauda DEPOIS do fim do round fica: dá pra morrer nos segundos seguintes ao
# round ser decidido, e essas mortes são do round certo. EXCETO no round que
# fecha a metade: dali o jogo vai para o intervalo, e o que acontece depois do
# fim dele não pertence a round nenhum. Caso real: a bomba explodiu depois do
# fim do round 12 e matou quem estava perto (donk em match_24, ropz em
# match_26). A HLTV não conta essas mortes; nos outros rounds conta (6 de 6
# casos conferidos contra o K-D oficial). Decisão do Pedro: não contar.
# Medido nas 52 partidas: são as duas únicas mortes depois do fim de um round
# de intervalo.


def _rounds_de_intervalo(rounds: pl.DataFrame) -> list[int]:
    """Rounds depois dos quais os times trocam de lado (o intervalo).

    Sai da regra de lados, não de um número fixo: no MR12 é o 12, e na
    prorrogação é o do meio de cada uma (27, 33...). A virada de uma
    prorrogação para a outra não tem troca e não entra.
    """
    from metrics.sides import side_of_team

    nums = rounds["round_num"].drop_nulls().to_list()
    if not nums:
        return []
    ultimo = max(nums)
    return [int(rn) for rn in nums
            if rn < ultimo and side_of_team("A", int(rn)) != side_of_team("A", int(rn) + 1)]


def kills_do_round_jogado(kills: pl.DataFrame, rounds: pl.DataFrame) -> pl.DataFrame:
    """Descarta as mortes que não pertencem ao round jogado: as anteriores ao
    fim do freeze time e as posteriores ao fim de um round de intervalo.

    Este é o filtro que todo consumidor de `kills` deve aplicar. Está aqui, no
    módulo de parsing, porque é limpeza de dado bruto e não decisão de métrica --
    nenhuma métrica do projeto quer contar uma morte do tempo parado.
    """
    if kills.height == 0 or "round_num" not in kills.columns:
        return kills

    intervalo = _rounds_de_intervalo(rounds) if "end" in rounds.columns else []
    # fim que vale só nos rounds de intervalo; nos outros a cauda fica
    fim_do_intervalo = (
        pl.when(pl.col("round_num").is_in(intervalo)).then(pl.col("end")).otherwise(None)
        if intervalo else pl.lit(None, dtype=pl.Int64)
    )
    limites = rounds.select(
        pl.col("round_num").cast(kills.schema["round_num"]),
        pl.col("freeze_end"),
        fim_do_intervalo.alias("_fim_do_intervalo"),
    )
    return (
        kills.join(limites, on="round_num", how="left")
        .filter(pl.col("freeze_end").is_null() | (pl.col("tick") >= pl.col("freeze_end")))
        .filter(pl.col("_fim_do_intervalo").is_null() | (pl.col("tick") <= pl.col("_fim_do_intervalo")))
        .drop(["freeze_end", "_fim_do_intervalo"])
    )
