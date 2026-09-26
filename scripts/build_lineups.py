"""
Biblioteca de ARREMESSOS REAIS por mapa, para a prancheta tática.

Cada entrada é um arremesso que aconteceu numa partida do corpus, com o que é
preciso para repetir: posição dos pés, ângulo, força (e o botão), postura,
movimento e o comando de console. Só entra arremesso com reprodução EXATA
(`motivo_aproximado` vazio, decisão 21): lineup errado é pior que nenhum,
porque o cara treina o arremesso errado.

POR QUE UM ARQUIVO VERSIONADO, E NÃO GERADO NO SITE
---------------------------------------------------
O arremesso sai de `metrics/grenade_throws.py`, que precisa das tabelas brutas
de `data/interim/` (trajetória do projétil, ticks do jogador). O interim não vai
para o git (é pesado demais), e o site é montado no GitHub Actions a partir do
que está versionado. Então a biblioteca é gerada AQUI, na máquina que tem o
interim, e gravada em `data/lineups/<mapa>.json` -- a mesma lógica de
`data/processed/`.

Uso:
    py -3.12 -m scripts.build_lineups
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import polars as pl

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from metrics.grenade_throws import (  # noqa: E402
    BOTAO_DA_FORCA, COMANDO_CONFERIDO_NO_JOGO, ROTULOS_FORCA, comando_de_console,
    grenade_throws, grupos_de_forca, rotula_forca,
)
from parsing.parser import load_interim  # noqa: E402

INTERIM = PROJECT_ROOT / "data" / "interim"
PROCESSED = PROJECT_ROOT / "data" / "processed"
LINEUPS_DIR = PROJECT_ROOT / "data" / "lineups"

# Versão do formato do arquivo da biblioteca. A página recusa versão que não
# conhece.
FORMATO_LINEUPS = 1

TICKRATE_PADRAO = 64


def _tickrate(match_id: str) -> int:
    meta = json.loads((PROCESSED / match_id / "match_meta.json").read_text(encoding="utf-8"))
    return int(meta.get("tickrate") or TICKRATE_PADRAO)


def arremessos_do_corpus() -> pl.DataFrame:
    """Todos os arremessos das partidas com interim, com mapa, tempo e jogador."""
    partes = []
    for d in sorted(INTERIM.glob("match_*")):
        proc = PROCESSED / d.name
        if not (proc / "match_meta.json").exists() or not (d / "grenades.parquet").exists():
            continue
        meta = json.loads((proc / "match_meta.json").read_text(encoding="utf-8"))
        t = load_interim(INTERIM, d.name)
        t["rounds"] = pl.read_parquet(proc / "rounds.parquet")
        tr = _tickrate(d.name)
        pr, _ = grenade_throws(t, tr)
        if pr.height == 0:
            continue
        fr = t["rounds"].select("round_num", pl.col("freeze_end").alias("_fe"))
        partes.append(
            pr.join(fr, on="round_num", how="left")
            .with_columns(
                pl.lit(d.name).alias("match_id"),
                pl.lit(meta["map_name"]).alias("mapa"),
                ((pl.col("tick_soltura") - pl.col("_fe")) / tr).alias("segundos_no_round"),
            )
            .drop("_fe")
        )
    return pl.concat(partes, how="diagonal_relaxed") if partes else pl.DataFrame()


def _entrada(r: dict, grupos: list) -> dict:
    forca = rotula_forca(r["velocidade_arremesso"], grupos)
    seg = r["segundos_no_round"]
    return {
        "id": f"{r['match_id']}:{r['round_num']}:{r['entity_id']}",
        "arma": r["kind"],
        "origem": [round(r["x"], 2), round(r["y"], 2), round(r["z"], 2)],
        "destino": [round(r["x_final"], 1), round(r["y_final"], 1), round(r["z_final"], 1)],
        "pitch": round(r["pitch"], 2),
        "yaw": round(r["yaw"], 2),
        "comando": comando_de_console(r["x"], r["y"], r["z"], r["pitch"], r["yaw"]),
        "forca": forca,
        # o botão só sai quando a força tem um dos três rótulos confirmados;
        # grupo neutro ("força A") não diz qual botão, e inventar seria pior
        "botao": BOTAO_DA_FORCA.get(forca),
        "velocidade": round(r["velocidade_arremesso"], 0) if r["velocidade_arremesso"] is not None else None,
        "postura": r["postura"],
        "movimento": r["movimento"],
        "no_ar": r["no_ar"],
        "jogador": r["thrower"],
        "partida": r["match_id"],
        "round": r["round_num"],
        "segundos_no_round": None if seg is None else round(seg, 1),
    }


def biblioteca_do_mapa(df: pl.DataFrame, mapa: str) -> dict:
    m = df.filter(pl.col("mapa") == mapa)
    exatos = m.filter(pl.col("reproducao_exata") & pl.col("tick_soltura").is_not_null()
                      & pl.col("x").is_not_null() & pl.col("x_final").is_not_null())
    v = exatos["velocidade_arremesso"].drop_nulls().to_numpy()
    grupos = grupos_de_forca(v)
    entradas = [_entrada(r, grupos) for r in
                exatos.sort(["match_id", "round_num", "tick_soltura", "entity_id"]).iter_rows(named=True)]
    return {
        "formato": "biblioteca-de-arremessos",
        "versao": FORMATO_LINEUPS,
        "mapa": mapa,
        "partidas": int(m["match_id"].n_unique()),
        "arremessos_no_corpus": int(m.height),
        "arremessos_exatos": len(entradas),
        "grupos_de_forca": [{"centro": round(c, 0), "n": n, "rotulo": rotula_forca(c, grupos)} for c, n in grupos],
        "rotulos_confirmados": len(grupos) == len(ROTULOS_FORCA),
        "comando_conferido_no_jogo": COMANDO_CONFERIDO_NO_JOGO,
        "arremessos": entradas,
    }


def main() -> None:
    df = arremessos_do_corpus()
    LINEUPS_DIR.mkdir(parents=True, exist_ok=True)
    for mapa in sorted(df["mapa"].unique(maintain_order=True).to_list()):
        bib = biblioteca_do_mapa(df, mapa)
        saida = LINEUPS_DIR / f"{mapa}.json"
        saida.write_text(json.dumps(bib, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
        print(f"{mapa}: {bib['arremessos_exatos']} exatos de {bib['arremessos_no_corpus']} "
              f"em {bib['partidas']} partidas; grupos de força {[g['centro'] for g in bib['grupos_de_forca']]} "
              f"-> {saida.stat().st_size / 1024:.0f} KB")


if __name__ == "__main__":
    main()
