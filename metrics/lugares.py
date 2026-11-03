"""O nome do lugar, para o roteiro da prancheta (fase 8, item 8.5).

O nome vem do campo `place` dos ticks do corpus: o nome que o próprio jogo dá
ao lugar onde o jogador está (dado da demo, em inglês, como o jogo escreve). As
áreas de navegação do awpy não estão nesta máquina (~/.awpy/navs não existe),
então não há outra fonte -- e nome inventado não entra.

A tabela é uma grade sobre o radar: cada célula de `lado` x `lado` pixels do
radar fica com o lugar mais comum dos ticks que caem nela, por andar. Célula
sem tick não tem nome. O lado da célula de cada mapa é medido
(scripts/build_lugares.py, tabela em pesquisa/lugares_no_corpus.py): o de maior
acerto fora da amostra entre os que cabem no limite de peso. Mapa sem medida
fora da amostra (menos de MIN_PARTIDAS partidas) fica sem tabela.
Ver notas/investigacoes/2026-10-04-nome-do-lugar.md.
"""
from __future__ import annotations

import functools
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

import polars as pl

from metrics.map_areas import floor_split_z

PASSO_TICKS = 16                   # 4 amostras por segundo a 64 tick
LADOS_DA_CELULA = (4, 8, 16, 32)   # pixels do radar (1024 de lado)
LIMITE_BYTES = 300 * 1024          # documento da fase 8: acréscimo máximo por mapa
MIN_PARTIDAS = 2                   # uma para montar a tabela, outra para conferir
# Acerto mínimo fora da amostra para um mapa ter nome de lugar (critério do
# Pedro, resposta 4 das fases 7-9): o piso dos mapas aceitos na fase 8, cujo
# menor acerto medido foi 93,4% (Overpass) -- abaixo disso, sem nome.
MIN_ACERTO = 0.93


def amostras(ticks_parquet: Path, radar: dict, mapa: str) -> list[tuple[float, float, int, str]]:
    """(x, y) em pixel do radar, andar (0 em cima) e o lugar, dos jogadores vivos."""
    t = (pl.scan_parquet(ticks_parquet)
         .select("tick", "X", "Y", "Z", "place", "is_alive")
         .filter((pl.col("tick") % PASSO_TICKS == 0) & pl.col("is_alive")
                 & pl.col("place").is_not_null() & (pl.col("place") != ""))
         .collect())
    corte = floor_split_z(mapa)
    px = (t["X"] - radar["origin_x"]) * radar["scale_px_per_unit"]
    py = (radar["origin_y"] - t["Y"]) * radar["scale_px_per_unit"]
    andares = [0 if corte is None or z >= corte else 1 for z in t["Z"].to_list()]
    return list(zip(px.to_list(), py.to_list(), andares, t["place"].to_list()))


def grade(pontos, lado: int) -> dict:
    cont: dict = defaultdict(Counter)
    for x, y, n, p in pontos:
        cont[(n, int(x // lado), int(y // lado))][p] += 1
    # empate de contagem: o nome em ordem alfabética (determinístico)
    return {k: min(c.items(), key=lambda kv: (-kv[1], kv[0]))[0] for k, c in cont.items()}


def tabela_compacta(g: dict, lado: int) -> dict:
    """{lado, nomes, andares: [{linha: [coluna, índice, repetições, ...]}]}: o
    que a página carrega (RLE por linha da grade)."""
    nomes = sorted(set(g.values()))
    ix = {n: i for i, n in enumerate(nomes)}
    por_andar: dict = defaultdict(lambda: defaultdict(dict))
    for (n, cx, cy), p in g.items():
        por_andar[n][cy][cx] = ix[p]
    out = []
    for n in range(max(por_andar) + 1 if por_andar else 0):
        linhas = {}
        for cy in sorted(por_andar[n]):
            cols = por_andar[n][cy]
            rle, ant, ini, rep = [], None, None, 0
            for cx in sorted(cols):
                v = cols[cx]
                if ant is not None and v == ant and cx == ini + rep:
                    rep += 1
                    continue
                if ant is not None:
                    rle += [ini, ant, rep]
                ant, ini, rep = v, cx, 1
            rle += [ini, ant, rep]
            linhas[str(cy)] = rle
        out.append(linhas)
    return {"lado": lado, "nomes": nomes, "andares": out}


def lugar(tabela: dict | None, x_px: float, y_px: float, andar: int) -> str | None:
    """O nome na célula do ponto (pixel do radar), ou None. Espelho de
    `lugarDe` em tactics.js."""
    if not tabela or andar >= len(tabela["andares"]):
        return None
    lado = tabela["lado"]
    cx, cy = int(x_px // lado), int(y_px // lado)
    rle = tabela["andares"][andar].get(str(cy))
    if not rle:
        return None
    for i in range(0, len(rle), 3):
        if rle[i] <= cx < rle[i] + rle[i + 2]:
            return tabela["nomes"][rle[i + 1]]
    return None


def acerto(treino, teste, lado: int) -> float:
    """Fração das amostras de teste cujo lugar a tabela do treino acerta
    (célula vazia conta como erro)."""
    g = grade(treino, lado)
    ok = sum(1 for x, y, n, p in teste if g.get((n, int(x // lado), int(y // lado))) == p)
    return ok / len(teste)


# --- Âncoras dos nomes de lugar no mapa (Fase M, decisão 52) ------------------------------------
ANCORAS_POR_LUGAR = 5          # posições candidatas por nome e andar: o desenho usa a primeira que não cobre nada
SEPARACAO_MINIMA_CELULAS = 6   # candidatas da mesma região ficam a pelo menos 6 células uma da outra


def _celulas_por_nome(tabela: dict, andar: int) -> dict[int, set]:
    por_nome: dict[int, set] = defaultdict(set)
    for cy, rle in tabela["andares"][andar].items():
        for i in range(0, len(rle), 3):
            for cx in range(rle[i], rle[i] + rle[i + 2]):
                por_nome[rle[i + 1]].add((cx, int(cy)))
    return por_nome


def _profundidade(celulas: set) -> dict:
    """Distância de cada célula até a borda da região (em células, 4 vizinhos): a borda vale 1. A âncora do nome fica
    onde a região é mais funda, nunca na beirada."""
    prof = {c: 1 for c in celulas if any((c[0] + dx, c[1] + dy) not in celulas for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)))}
    fronteira = sorted(prof)
    while fronteira:
        proxima = []
        for cx, cy in fronteira:
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                v = (cx + dx, cy + dy)
                if v in celulas and v not in prof:
                    prof[v] = prof[(cx, cy)] + 1
                    proxima.append(v)
        fronteira = sorted(proxima)
    return prof


def rotulos(tabela: dict | None, por_lugar: int = ANCORAS_POR_LUGAR) -> list:
    """Onde pôr o nome de cada lugar: por andar, `[[índice do nome, [[x, y], ...]], ...]` em pixels do radar, ordenado pelo
    índice. As posições candidatas vêm da mais funda da região para as outras (desempate: mais perto do centro, depois linha
    e coluna), separadas por `SEPARACAO_MINIMA_CELULAS`; o nome é o da tabela (o que o jogo escreve), nada é inventado.
    Determinístico. Sem tabela, lista vazia."""
    if not tabela:
        return []
    lado = tabela["lado"]
    saida = []
    for andar in range(len(tabela["andares"])):
        lugares = []
        for ix, celulas in sorted(_celulas_por_nome(tabela, andar).items()):
            prof = _profundidade(celulas)
            cx0 = sum(c[0] for c in celulas) / len(celulas)
            cy0 = sum(c[1] for c in celulas) / len(celulas)
            ordem = sorted(celulas, key=lambda c: (-prof[c], (c[0] - cx0) ** 2 + (c[1] - cy0) ** 2, c[1], c[0]))
            escolhidas: list = []
            for c in ordem:
                if all(max(abs(c[0] - o[0]), abs(c[1] - o[1])) >= SEPARACAO_MINIMA_CELULAS for o in escolhidas):
                    escolhidas.append(c)
                    if len(escolhidas) == por_lugar:
                        break
            lugares.append([ix, [[(c[0] + 0.5) * lado, (c[1] + 0.5) * lado] for c in escolhidas]])
        saida.append(lugares)
    return saida


def texto_do_lugar(nome: str) -> str:
    """Como o nome vai escrito no mapa (Fase M, decisão 52): em caixa alta, com as palavras separadas pelas maiúsculas que o
    PRÓPRIO dado usa ("CTSpawn" vira "CT SPAWN", "SnipersNest" vira "SNIPERS NEST") e o "of" minúsculo colado entre uma
    minúscula e uma maiúscula ("TopofMid" vira "TOP OF MID"). As letras são exatamente as do dado, só com espaço: nada é
    traduzido, inventado nem tem exceção escrita à mão."""
    n = re.sub(r"(?<=[a-z])of(?=[A-Z])", " of ", nome)
    n = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", n)
    n = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1 \2", n)
    return re.sub(r" +", " ", n).strip().upper()


PASTA_DAS_TABELAS = Path(__file__).resolve().parent.parent / "data" / "lugares"


@functools.lru_cache(maxsize=None)
def tabela_do_mapa(mapa: str) -> dict | None:
    """A tabela de lugares gravada do mapa (`data/lugares/<mapa>.json`), ou None se o mapa não tem. As duas páginas (replay e
    prancheta) leem por aqui; quem altera o resultado não deve mexer nele (é compartilhado)."""
    caminho = PASTA_DAS_TABELAS / f"{mapa}.json"
    return json.loads(caminho.read_text(encoding="utf-8")) if caminho.exists() else None


def para_a_prancheta(tabela: dict | None) -> dict | None:
    """A tabela inteira (o roteiro precisa dela) mais as âncoras e o texto dos nomes no mapa."""
    return None if not tabela else {**tabela, "rotulos": rotulos(tabela), "textos": [texto_do_lugar(n) for n in tabela["nomes"]]}


def para_o_replay(tabela: dict | None) -> dict | None:
    """O replay só desenha os nomes: nomes, textos e âncoras, sem a grade."""
    return None if not tabela else {"nomes": tabela["nomes"], "textos": [texto_do_lugar(n) for n in tabela["nomes"]],
                                    "rotulos": rotulos(tabela)}
