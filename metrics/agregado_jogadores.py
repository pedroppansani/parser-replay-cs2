"""Visão agregada por jogador no corpus, para a página jogadores.html (fase 7, item 7.3).

JUSTIFICATIVA. A página da partida mostra só os números daquela partida, com a
régua anônima do corpus (decisão 30). Comparar jogadores ENTRE partidas é outra
pergunta e vive em lugar separado e explícito: esta página. Três regras:

- IDENTIDADE É O STEAMID (decisão 25). O nome é o de exibição de
  `metrics.identidade` (o nick mais frequente); o mesmo jogador com dois nicks é
  uma linha só.
- O NÚMERO DE UM JOGADOR É A RAZÃO DAS SOMAS das partidas dele (numerador e
  denominador somados), não a média das taxas: uma partida de 30 rounds pesa
  mais que uma de 16, como deve.
- QUEM TEM POUCAS PARTIDAS É PUXADO PARA A MÉDIA DA FUNÇÃO DELE, e a página diz
  quanto. O peso do próprio jogador é m / (m + k), com m = partidas e k por
  métrica estimado no corpus: k = (variância dentro do jogador, partida a
  partida) / (variância entre jogadores). É o encolhimento empírico de sempre
  (normal-normal); com k = 3, quem tem 1 partida fica com 25% do próprio número
  e quem tem 20 com 87%.

O intervalo é bootstrap por PARTIDA (reamostra as partidas do jogador), feito no
navegador para o recorte escolhido (mapa, lado) com semente fixa.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import polars as pl

from metrics.identidade import nome_de_exibicao
from metrics.impacto import ROTULOS as ROTULOS_DE_IMPACTO
from metrics.impacto import CATEGORIAS_DE_IMPACTO, TEMPO_DA_TROCA
from metrics.player_profile import CATEGORIAS, ROTULOS_DAS_TAXAS, TAXAS_POR_ROUND

RAIZ = Path(__file__).resolve().parents[1]
PROCESSED = RAIZ / "data" / "processed"
MANIFESTO = RAIZ / "data" / "manifest.json"

# Partidas mínimas para um jogador entrar na estimativa da variância DENTRO do
# jogador (com uma partida só não há variação a medir).
MIN_PARTIDAS_PARA_VARIANCIA = 2
# Nº de reamostragens do bootstrap no navegador e a semente (decisão 28: o mesmo
# recorte dá o mesmo intervalo em qualquer abertura da página).
N_BOOTSTRAP = 400
SEMENTE_BOOTSTRAP = 20261004

LADOS = [c for c, _, por_lado in TAXAS_POR_ROUND if por_lado]


def metricas() -> list[dict]:
    """A lista de métricas da página, na ordem dos grupos, com rótulo e formato."""
    saida = [
        {"chave": "rating", "rotulo": "Rating", "formato": "num2", "grupo": "Placar", "lado": False},
        {"chave": "adr", "rotulo": "ADR", "formato": "num1", "grupo": "Placar", "lado": False},
        {"chave": "kast", "rotulo": "KAST", "formato": "pct", "grupo": "Placar", "lado": False},
    ]
    for grupo, chaves in CATEGORIAS.items():
        for c in chaves:
            if c in ROTULOS_DAS_TAXAS:
                saida.append({"chave": c, "rotulo": ROTULOS_DAS_TAXAS[c], "formato": "pct", "grupo": grupo,
                              "lado": c in LADOS})
    for grupo, chaves in CATEGORIAS_DE_IMPACTO.items():
        for c in chaves:
            if c == TEMPO_DA_TROCA:      # mediana por partida, sem numerador: fica fora do agregado
                continue
            rot, fmt, _ = ROTULOS_DE_IMPACTO[c]
            saida.append({"chave": c, "rotulo": rot, "formato": fmt, "grupo": grupo, "lado": False})
    return saida


def linhas_por_partida(pasta: Path = PROCESSED) -> pl.DataFrame:
    """Uma linha por (partida, steamid): numerador e denominador de cada métrica,
    também por lado onde existe, mais mapa, origem e o rótulo de função."""
    manifesto = json.loads(MANIFESTO.read_text(encoding="utf-8")).get("partidas", {}) if MANIFESTO.exists() else {}
    partes = []
    for d in sorted(pasta.glob("match_*")):
        f = d / "player_profile.parquet"
        if not f.exists() or not (d / "insights.json").exists():
            continue
        perfil = pl.read_parquet(f)
        ins = json.loads((d / "insights.json").read_text(encoding="utf-8"))
        rating = {p["steamid"]: p.get("rating") for p in ins["players"]}
        adr = pl.read_parquet(d / "adr_summary.parquet").select("steamid", "total_damage", "rounds_played")
        kast = pl.read_parquet(d / "kast_summary.parquet").select("steamid", "kast_rounds")
        papeis = pl.read_parquet(d / "player_roles.parquet").select("steamid", "role")
        meta = json.loads((d / "match_meta.json").read_text(encoding="utf-8"))
        cols = ["steamid", "name"]
        for m in metricas():
            c = m["chave"]
            if c in ("rating", "adr", "kast"):
                continue
            for suf in ("", "_ct", "_t") if m["lado"] else ("",):
                for nd in ("_n", "_d"):
                    if f"{c}{suf}{nd}" in perfil.columns:
                        cols.append(f"{c}{suf}{nd}")
        t = (perfil.select(cols)
             .join(adr, on="steamid", how="left").join(kast, on="steamid", how="left")
             .join(papeis, on="steamid", how="left")
             .with_columns(
                 pl.lit(d.name).alias("match_id"), pl.lit(meta.get("map_name", "")).alias("mapa"),
                 pl.lit((manifesto.get(d.name) or {}).get("origem") or "").alias("origem"),
                 pl.col("steamid").replace_strict(rating, default=None, return_dtype=pl.Float64).alias("_rating"))
             .with_columns(
                 (pl.col("_rating") * pl.col("rounds_played")).alias("rating_n"),
                 pl.when(pl.col("_rating").is_not_null()).then(pl.col("rounds_played")).alias("rating_d"),
                 pl.col("total_damage").cast(pl.Float64).alias("adr_n"),
                 pl.col("rounds_played").cast(pl.Float64).alias("adr_d"),
                 pl.col("kast_rounds").cast(pl.Float64).alias("kast_n"),
                 pl.col("rounds_played").cast(pl.Float64).alias("kast_d"))
             .drop("_rating", "total_damage", "kast_rounds"))
        partes.append(t)
    return pl.concat(partes, how="diagonal_relaxed") if partes else pl.DataFrame()


def funcao_por_jogador(linhas: pl.DataFrame) -> dict[int, str]:
    """A função do jogador no corpus: o rótulo principal mais frequente nas
    partidas dele (empate: o de ordem alfabética), ou 'sem função dominante'."""
    saida = {}
    for (s,), g in linhas.group_by(["steamid"], maintain_order=True):
        papeis = [r for r in g["role"].to_list() if r]
        if not papeis:
            saida[int(s)] = "sem função dominante"
            continue
        cont: dict[str, int] = {}
        for r in papeis:
            cont[r] = cont.get(r, 0) + 1
        topo = max(cont.values())
        saida[int(s)] = sorted(r for r, n in cont.items() if n == topo)[0]
    return saida


def k_de_encolhimento(linhas: pl.DataFrame, chave: str) -> float | None:
    """k = variância dentro do jogador / variância entre jogadores (método dos momentos).

    Usa a razão por partida (n/d) dos jogadores com pelo menos
    MIN_PARTIDAS_PARA_VARIANCIA partidas. Sem variação entre jogadores (k
    infinito) devolve None: a página então mostra só a média da função."""
    n, d = f"{chave}_n", f"{chave}_d"
    if n not in linhas.columns or d not in linhas.columns:
        return None
    x = linhas.filter(pl.col(d) > 0).select("steamid", (pl.col(n) / pl.col(d)).alias("x"))
    por = x.group_by("steamid", maintain_order=True).agg(pl.col("x").var().alias("v"), pl.col("x").mean().alias("m"),
                                                         pl.len().alias("q"))
    multi = por.filter(pl.col("q") >= MIN_PARTIDAS_PARA_VARIANCIA)
    if multi.height < 3:
        return None
    dentro = float(multi["v"].mean())
    q_medio = float(multi["q"].mean())
    entre = float(multi["m"].var()) - dentro / q_medio
    if not np.isfinite(entre) or entre <= 0:
        return None
    return round(dentro / entre, 3)


def encolhe(valor: float, media_da_funcao: float, partidas: int, k: float | None) -> float:
    """O valor puxado para a média da função: peso m / (m + k) para o jogador."""
    if k is None:
        return media_da_funcao
    w = partidas / (partidas + k)
    return w * valor + (1 - w) * media_da_funcao


def para_a_pagina(pasta: Path = PROCESSED) -> dict:
    """Tudo o que a página precisa, compacto: métricas, jogadores, k e as linhas."""
    linhas = linhas_por_partida(pasta)
    ms = metricas()
    nomes = dict(nome_de_exibicao(linhas.select("steamid", "name", "match_id")).iter_rows())
    funcao = funcao_por_jogador(linhas)
    ids = sorted({int(s) for s in linhas["steamid"].to_list()}, key=lambda s: (nomes.get(s, "").lower(), s))
    idx = {s: i for i, s in enumerate(ids)}
    mapas = sorted(set(linhas["mapa"].to_list()))
    chaves = []
    for m in ms:
        chaves += [m["chave"]] + ([f"{m['chave']}_ct", f"{m['chave']}_t"] if m["lado"] else [])
    k = {c: k_de_encolhimento(linhas, c) for c in chaves}

    def num(v):
        return None if v is None else round(float(v), 3)

    registros = []
    for r in linhas.iter_rows(named=True):
        registros.append([idx[int(r["steamid"])], mapas.index(r["mapa"]), r["match_id"], r["origem"]]
                         + [[num(r.get(f"{c}_n")), num(r.get(f"{c}_d"))] for c in chaves])
    jogadores = []
    for s in ids:
        g = linhas.filter(pl.col("steamid") == s)
        jogadores.append({"steamid": str(s), "nome": nomes.get(s, str(s)), "funcao": funcao[s],
                          "partidas": g.height, "rounds": int(g["rounds_played"].sum())})
    return {"metricas": ms, "chaves": chaves, "k": k, "mapas": mapas, "jogadores": jogadores,
            "linhas": registros, "n_bootstrap": N_BOOTSTRAP, "semente": SEMENTE_BOOTSTRAP}
