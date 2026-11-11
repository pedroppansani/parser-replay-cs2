"""A tabela dos tempos reais de corrida por mapa (C3, decisão 64): `data/tempos/<mapa>.json`, feita das partidas do corpus (`data/interim`).

    py -3.12 -m scripts.build_tempos [mapa ...]

Os dados são derivados e vão para o git (como `data/lineups`); o build do site só os lê. A conta está em `metrics/tempos_de_corrida.py`.
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np
import polars as pl

from metrics.map_areas import floor_split_z
from metrics.tactics import VELOCIDADE_U_S
from metrics.tempos_de_corrida import (MIN_CASOS, MIN_PARTIDAS, RAIO_AREAS, RAIO_ORIGEM, RAIO_PONTOS, fator_do_mapa, pares)
from scripts.build_lineups import INTERIM, PROCESSED, detect_tickrate, load_interim
from scripts.comandos_contexto import contexto

RAIZ = Path(__file__).resolve().parent.parent
PASTA = RAIZ / "data" / "tempos"
PASSO = 8
VERSAO = 1


def arquivo_dos_tempos(mapa: str) -> Path:
    return PASTA / f"{mapa}.json"


def _arredonda(v: float) -> int:
    return int(math.floor(v + 0.5))      # como o Math.round do leitor


def rastros(mapa: str) -> list[dict]:
    """Um rastro por jogador vivo e round valendo, de 8 em 8 ticks (a 64 ticks/s; o passo escala com a taxa da partida)."""
    saida = []
    for d in sorted(INTERIM.glob("match_*")):
        meta = PROCESSED / d.name / "match_meta.json"
        if not meta.exists() or json.loads(meta.read_text(encoding="utf-8"))["map_name"] != mapa:
            continue
        t = load_interim(INTERIM, d.name)
        rounds = pl.read_parquet(PROCESSED / d.name / "rounds.parquet")
        tr = int(detect_tickrate(rounds, t["ticks"])["tickrate"]); passo = max(1, round(PASSO * tr / 64))
        janela = {r["round_num"]: (r["freeze_end"], r["end"]) for r in rounds.iter_rows(named=True) if r["freeze_end"] is not None and r["end"] is not None}
        tk = (t["ticks"].filter((pl.col("tick") % passo == 0) & pl.col("is_alive")).select("tick", "round_num", "steamid", "X", "Y", "Z", "is_walking", "ducking")
              .sort("steamid", "round_num", "tick"))
        for (sid, rd), g in tk.group_by(["steamid", "round_num"], maintain_order=True):
            if rd not in janela:
                continue
            g = g.filter((pl.col("tick") >= janela[rd][0]) & (pl.col("tick") <= janela[rd][1]))
            if g.height < 4:
                continue
            saida.append({"partida": d.name, "tick": g["tick"].to_numpy(), "x": g["X"].to_numpy().astype(float), "y": g["Y"].to_numpy().astype(float),
                          "z": g["Z"].to_numpy().astype(float), "walk": g["is_walking"].fill_null(False).to_numpy().astype(float),
                          "duck": g["ducking"].fill_null(False).to_numpy().astype(float), "tr": tr, "passo": passo})
    return saida


def nos_de_pontos(pontos: list[dict]) -> list[dict]:
    """Os pontos do Pedro agrupados como o leitor agrupa (mesmo nome? não: mesma ÁREA da demo e mesmo ANDAR = um alvo, no ponto do meio).
    A chave é a lista ordenada dos números dos pontos ("3" ou "3+5"), o mesmo que o leitor monta de `alvo.ids`."""
    grupos: dict[str, list[dict]] = {}
    for p in pontos:
        grupos.setdefault(f"g|{p['nome']}|{p['lugar']}|{p['andar']}" if p["lugar"] else f"i|{p['id']}", []).append(p)
    nos = []
    for g in grupos.values():
        idx = sorted(int(p["id"].split(":")[1]) for p in g)
        nos.append({"chave": "+".join(str(i) for i in idx), "x": _arredonda(sum(p["x"] for p in g) / len(g)), "y": _arredonda(sum(p["y"] for p in g) / len(g)),
                    "membros": [(p["x"], p["y"]) for p in g], "andar": g[0]["andar"] if g[0]["andar"] in ("cima", "baixo") else ""})
    return nos


def nos_de_areas(areas: list[dict]) -> list[dict]:
    return [{"chave": a["nome"], "x": a["x"], "y": a["y"], "membros": [(a["x"], a["y"])], "andar": a["andar"] if a["andar"] in ("cima", "baixo") else ""} for a in areas]


def tabela(mapa: str) -> dict | None:
    rs = rastros(mapa)
    ctx = contexto(mapa, so_conferidos=True)
    if not rs or not (ctx["pontos"] or ctx["areas"]):
        return None
    corte = floor_split_z(mapa)
    v = VELOCIDADE_U_S[("rifle", "correndo")]
    areas = nos_de_areas(ctx["areas"]); pontos = nos_de_pontos(ctx["pontos"])
    par_a = pares(rs, areas, RAIO_AREAS, corte) if areas else {}
    par_p = pares(rs, pontos, RAIO_PONTOS, corte) if pontos else {}
    usados = sorted({i for k in par_p for i in k})
    saida = {"versao": VERSAO, "mapa": mapa, "partidas": len({r["partida"] for r in rs}), "velocidade_de_referencia": v,
             "raio_pontos": RAIO_PONTOS, "raio_areas": RAIO_AREAS, "raio_origem": RAIO_ORIGEM, "minimo_casos": MIN_CASOS, "minimo_partidas": MIN_PARTIDAS,
             "fator": fator_do_mapa([("pontos", par_p, pontos), ("áreas", par_a, areas)], v),
             "nos": [[pontos[i]["chave"], pontos[i]["x"], pontos[i]["y"], pontos[i]["andar"]] for i in usados],
             "pontos": [[pontos[a]["chave"], pontos[b]["chave"], r["p25"], r["mediana"], r["p75"], r["casos"], r["partidas"]] for (a, b), r in sorted(par_p.items())],
             "areas": [[areas[a]["chave"], areas[b]["chave"], r["p25"], r["mediana"], r["p75"], r["casos"], r["partidas"]] for (a, b), r in sorted(par_a.items())]}
    return saida


def main() -> None:
    PASTA.mkdir(parents=True, exist_ok=True)
    mapas = sys.argv[1:] or sorted({json.loads((PROCESSED / d.name / "match_meta.json").read_text(encoding="utf-8"))["map_name"]
                                    for d in INTERIM.glob("match_*") if (PROCESSED / d.name / "match_meta.json").exists()})
    for mapa in mapas:
        t = tabela(mapa)
        if t is None or not (t["pontos"] or t["areas"]):
            arquivo_dos_tempos(mapa).unlink(missing_ok=True)
            print(f"{mapa}: sem tabela (sem lugares, sem pontos conferidos ou sem par com amostra)")
            continue
        arquivo_dos_tempos(mapa).write_text(json.dumps(t, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
        f = t["fator"]
        print(f"{mapa}: {t['partidas']} partidas, {len(t['pontos'])} pares de pontos, {len(t['areas'])} de áreas, fator {f['valor']} ({f['fonte']}, {f['pares']} pares"
              + (f"; erro mediano da reta {f['erro_reta_s']} s, corrigida {f['erro_corrigido_s']} s, validada {f['erro_validado_s']} s" if f["valor"] else "") + ")", flush=True)


if __name__ == "__main__":
    main()
