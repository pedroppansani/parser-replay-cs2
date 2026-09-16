"""
Partição do mapa em áreas macro (A / Mid / B), derivada dos dados.

Para que serve: as métricas de âncora e de lurk não são sobre distância, são
sobre QUAL PARTE DO MAPA o jogador está jogando. "Âncora" é quem fica fixo num
bombsite mesmo quando a leitura do round aponta pro outro; "lurker" é o T que
está em Mid ou no B enquanto o time executa o A. Nenhuma das duas dá pra medir
com `avg_distance_from_team`: um CT parado no B e um CT parado no A podem estar à
mesma distância do time, e são coisas opostas.

Os callouts do demo (`place`) são finos demais pra isso -- "PalaceAlley" e
"Stairs" são o mesmo lado do mapa, e um jogador que anda de um pro outro não
mudou de área. Então cada callout é agrupado numa das três áreas macro.

Como o agrupamento é derivado, e não escrito à mão mapa por mapa:

1. O centróide 3D de cada bombsite vem dos PLANTS do próprio demo (`bomb`, com a
   coluna `bombsite`), que é a informação mais direta possível de onde o site
   fica. Se um site não foi plantado na partida, cai pro centróide do callout
   homônimo (`BombsiteA` / `BombsiteB`).
2. O centróide de cada callout vem das posições dos jogadores vivos.
3. O callout vai pra área do site mais próximo. "Mid" não é uma área desenhada:
   é o que sobra quando o callout está a distâncias parecidas dos dois sites
   (dentro de `MID_MARGIN`), que é exatamente o que "meio" quer dizer.

Um mapa de dois andares (Nuke, Vertigo, Train) quebraria a regra acima, porque os
dois sites ficam quase na mesma vertical: em de_nuke, sem correção, TODO callout
fica equidistante e o mapa inteiro viraria "Mid" -- inclusive o próprio
BombsiteB. A correção usa a mesma informação que o radar oficial do jogo usa pra
desenhar dois andares (`vertical_sections` nos assets extraídos por
scripts/extract_radars.py): quando o mapa tem andares, a diferença de altura pesa
`Z_WEIGHT_TWO_FLOOR` vezes mais na distância. Não é um chute: é dizer que subir
um andar te afasta de um site muito mais do que andar o mesmo tanto no plano.

Ainda assim, a derivação da Nuke é a mais discutível das nove partidas -- é o
tipo de caso que `MANUAL_PLACE_AREAS` existe pra resolver. Rode
`py -3.12 -m scripts.show_map_areas` pra ver a tabela derivada de cada mapa.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import polars as pl

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RADAR_DIR = PROJECT_ROOT / "assets" / "radars"

# Faixa de "empate" entre os dois sites. O valor é a fração da distância total:
# 0,10 significa que um callout entre 40% e 60% do caminho é Mid. Mais estreito
# que isso e o meio do mapa desaparece, dividido entre A e B; mais largo e um
# callout claramente de um site vira Mid.
MID_MARGIN = 0.10

# Peso da altura nos mapas de dois andares. Ver a explicação no topo do módulo.
# Com peso 1 (nenhuma correção) de_nuke classifica o próprio BombsiteB como Mid.
Z_WEIGHT_TWO_FLOOR = 5.0

# Override do julgamento de mapa, no mesmo espírito de MANUAL_ENTRY_ANGLES.
# Formato: {"de_nuke": {"Vents": "B", "Observation": "Mid"}}
# A derivação acerta os mapas de um andar; a Nuke é onde o conhecimento de jogo
# provavelmente discorda dela.
MANUAL_PLACE_AREAS: dict[str, dict[str, str]] = {}

AREA_A = "A"
AREA_B = "B"
AREA_MID = "Mid"
# Spawn não é área de jogo, é onde todo mundo nasce. Ele fica de fora da conta em
# vez de virar A, B ou Mid: geometricamente o CTSpawn da Ancient cai do lado do A
# (razão 0,38), então contá-lo faria TODO CT "ter passado pelo A" em todo round,
# e a medição de quem não sai do próprio bombsite zerava para o time inteiro --
# inclusive para quem ficou 12 de 12 rounds dentro do B.
AREA_SPAWN = "Spawn"

# Callouts de spawn. Os nomes vêm dos place names do CS2 e são estáveis entre
# mapas (CTSpawn / TSpawn); a checagem é por sufixo pra pegar variações.
SPAWN_SUFFIX = "spawn"


def _radar_meta(map_name: str) -> dict:
    """Metadados do radar extraído do jogo, ou {} se o mapa não foi extraído.

    Ausência é caso legítimo: os assets são opcionais (ver README) e só o corte
    de andar depende deles. Sem eles, um mapa de dois andares é tratado como de
    um andar -- e é por isso que a função avisa quem chama, em vez de assumir.
    """
    path = RADAR_DIR / f"{map_name}.json"
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def floor_split_z(map_name: str) -> float | None:
    """Altura que separa os andares, ou None num mapa de um andar só."""
    sections = _radar_meta(map_name).get("vertical_sections") or {}
    lower = sections.get("lower")
    if not lower:
        return None
    return float(lower["max"])


def site_centroids(bomb: pl.DataFrame, positions: pl.DataFrame) -> dict[str, np.ndarray]:
    """Centróide 3D de cada bombsite, dos plants e, na falta deles, do callout."""
    sites: dict[str, np.ndarray] = {}

    if bomb is not None and bomb.height and "bombsite" in bomb.columns:
        plants = (
            bomb.filter(pl.col("bombsite").is_not_null())
            .group_by("bombsite")
            .agg(pl.col("X").mean(), pl.col("Y").mean(), pl.col("Z").mean())
        )
        for row in plants.iter_rows(named=True):
            sites[row["bombsite"]] = np.array([row["X"], row["Y"], row["Z"]], dtype=float)

    # Fallback: um site nunca plantado na partida (acontece -- time que só foi
    # pra um lado) ainda tem callout, e o callout já é a região do site.
    for nome in ("BombsiteA", "BombsiteB"):
        if nome in sites:
            continue
        row = positions.filter(pl.col("place") == nome)
        if row.height:
            sites[nome] = np.array(
                [row["X"].mean(), row["Y"].mean(), row["Z"].mean()], dtype=float
            )
    return sites


def place_centroids(positions: pl.DataFrame) -> pl.DataFrame:
    """Centróide de cada callout, pelas posições amostradas dos jogadores vivos."""
    return (
        positions.filter(pl.col("place").is_not_null() & (pl.col("place") != ""))
        .group_by("place")
        .agg(
            pl.len().alias("n_samples"),
            pl.col("X").mean(),
            pl.col("Y").mean(),
            pl.col("Z").mean(),
        )
        .sort("n_samples", descending=True)
    )


def derive_place_areas(
    positions: pl.DataFrame,
    bomb: pl.DataFrame,
    map_name: str,
    mid_margin: float = MID_MARGIN,
) -> pl.DataFrame:
    """Uma linha por callout: área macro, a razão de distância que decidiu e a origem.

    `area_ratio` fica na saída de propósito: é ele que permite discordar da
    classificação olhando o número (0,5 = equidistante dos dois sites), e é o que
    `scripts/show_map_areas.py` mostra pra revisão manual.
    """
    centroids = place_centroids(positions)
    sites = site_centroids(bomb, positions)

    faltando = [s for s in ("BombsiteA", "BombsiteB") if s not in sites]
    if faltando:
        # Sem os dois sites não existe eixo A-B: devolver tudo como Mid seria
        # inventar um resultado. Quem chama trata a tabela vazia como "não sei".
        return pl.DataFrame(
            schema={
                "place": pl.String, "area": pl.String, "area_ratio": pl.Float64,
                "n_samples": pl.UInt32, "source": pl.String,
            }
        )

    split = floor_split_z(map_name)
    peso_z = Z_WEIGHT_TWO_FLOOR if split is not None else 1.0
    escala = np.array([1.0, 1.0, peso_z])
    manual = MANUAL_PLACE_AREAS.get(map_name, {})

    linhas = []
    for row in centroids.iter_rows(named=True):
        ponto = np.array([row["X"], row["Y"], row["Z"]], dtype=float)
        d_a = float(np.linalg.norm((ponto - sites["BombsiteA"]) * escala))
        d_b = float(np.linalg.norm((ponto - sites["BombsiteB"]) * escala))
        total = d_a + d_b
        ratio = 0.5 if total == 0 else d_a / total

        if row["place"].lower().endswith(SPAWN_SUFFIX):
            area = AREA_SPAWN
        elif ratio < 0.5 - mid_margin:
            area = AREA_A
        elif ratio > 0.5 + mid_margin:
            area = AREA_B
        else:
            area = AREA_MID

        source = "derivado"
        if row["place"] in manual:
            area = manual[row["place"]]
            source = "manual"

        linhas.append(
            {
                "place": row["place"],
                "area": area,
                "area_ratio": round(ratio, 3),
                "n_samples": row["n_samples"],
                "source": source,
            }
        )

    return pl.DataFrame(linhas).sort("area_ratio")


def area_lookup(place_areas: pl.DataFrame) -> dict[str, str]:
    """Mapa callout -> área, pra usar como dicionário de tradução."""
    return dict(zip(place_areas["place"].to_list(), place_areas["area"].to_list()))
