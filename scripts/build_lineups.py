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
from metrics.timing import detect_tickrate  # noqa: E402
from parsing.parser import load_interim  # noqa: E402

INTERIM = PROJECT_ROOT / "data" / "interim"
PROCESSED = PROJECT_ROOT / "data" / "processed"
LINEUPS_DIR = PROJECT_ROOT / "data" / "lineups"

# Versão do formato do arquivo da biblioteca. A página recusa versão que não
# conhece.
FORMATO_LINEUPS = 1

# Tempo de voo (do soltar até a detonação) acima disto não é voo de verdade, é o casamento errado com outra granada: vira nulo
# (a maior smoke do corpus voa 10,2 s; o limite dá folga sem aceitar os 65 s que o casamento errado do molotov chegou a dar).
MAX_VOO_S = 15.0

# a detonação de cada tipo na demo: a tabela e a coluna do entity_id (o molotov não tem: o fogo é outra entidade, ver tempos_e_lado)
DETONACAO_POR_TIPO = {"he": "hegrenade_detonate", "flash": "flashbang_detonate", "smoke": "smokegrenade_detonate"}


def tempos_e_lado(t: dict, pr: pl.DataFrame, tr: int) -> pl.DataFrame:
    """Para cada arremesso: o lado de quem lançou e os tempos reais da demo (nulo quando a demo não diz).

    - `lado` ("ct" ou "t"): o da pessoa no tick da soltura (`ticks.side`).
    - `voo_s`: do soltar até a detonação (he, flash e smoke: o evento de detonação com o mesmo entity_id, o primeiro depois de soltar,
      porque o entity_id é reaproveitado na partida; molotov: o início do fogo, casado por quem lançou, round e o primeiro fogo depois
      de soltar, porque o fogo é outra entidade). Acima de MAX_VOO_S ou negativo: nulo.
    - `efeito_s`: só o molotov (início e fim do fogo na demo). A smoke não tem tick de fim na demo (`end_tick` vazio), então fica nulo
      e quem usar a smoke usa a constante do projeto (`DURACAO_SMOKE_S`); he e flash são instantâneos e ficam nulos.
    """
    lado = (
        t["ticks"].select(pl.col("steamid").cast(pl.Int64), "tick", "side").drop_nulls().unique(subset=["steamid", "tick"], keep="first", maintain_order=True)
        .sort("tick")
    )
    alvo = pr.select("round_num", "entity_id", pl.col("steamid").cast(pl.Int64), "tick_soltura").drop_nulls("tick_soltura").sort("tick_soltura")
    alvo = alvo.join_asof(lado, left_on="tick_soltura", right_on="tick", by="steamid", strategy="nearest", check_sortedness=False)
    deton: dict = {}
    for tipo, tabela in DETONACAO_POR_TIPO.items():
        if tabela in t:
            for ent, tk in t[tabela].select("entityid", "tick").iter_rows():
                deton.setdefault((tipo, ent), []).append(tk)
    fogos: dict = {}
    if "infernos" in t:
        for sid, rd, ini, fim in t["infernos"].select("thrower_steamid", "round_num", "start_tick", "end_tick").iter_rows():
            fogos.setdefault((sid, rd), []).append((ini, fim))
    tipos = {(r["round_num"], r["entity_id"]): r["kind"] for r in pr.iter_rows(named=True)}
    linhas = []
    for r in alvo.iter_rows(named=True):
        tipo, s = tipos[(r["round_num"], r["entity_id"])], r["tick_soltura"]
        det, efeito = None, None
        if tipo == "molotov":
            cand = [f for f in fogos.get((r["steamid"], r["round_num"]), []) if f[0] is not None and f[0] >= s]
            if cand:
                ini, fim = min(cand, key=lambda f: f[0])
                det = ini
                efeito = None if fim is None else round((fim - ini) / tr, 2)
        elif tipo in DETONACAO_POR_TIPO:
            cand = [x for x in deton.get((tipo, r["entity_id"]), []) if x >= s]
            det = min(cand) if cand else None
        voo = None if det is None else round((det - s) / tr, 2)
        if voo is not None and not 0 <= voo <= MAX_VOO_S:
            voo, efeito = None, None
        linhas.append({"round_num": r["round_num"], "entity_id": r["entity_id"], "lado": r["side"], "voo_s": voo, "efeito_s": efeito})
    return pl.DataFrame(linhas, schema={"round_num": pl.Int64, "entity_id": pl.Int64, "lado": pl.Utf8, "voo_s": pl.Float64, "efeito_s": pl.Float64})


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
        tr = int(detect_tickrate(t["rounds"], t["ticks"])["tickrate"])   # o da demo
        pr, _ = grenade_throws(t, tr)
        if pr.height == 0:
            continue
        fr = t["rounds"].select("round_num", pl.col("freeze_end").alias("_fe"))
        tempos = tempos_e_lado(t, pr, tr)
        partes.append(
            pr.join(fr, on="round_num", how="left")
            .join(tempos, on=["round_num", "entity_id"], how="left")
            .with_columns(
                pl.lit(d.name).alias("match_id"),
                pl.lit(meta["map_name"]).alias("mapa"),
                ((pl.col("tick_soltura") - pl.col("_fe")) / tr).alias("segundos_no_round"),
            )
            .drop("_fe")
        )
    return pl.concat(partes, how="diagonal_relaxed") if partes else pl.DataFrame()


def _entrada(r: dict) -> dict:
    # força e botão AFIRMADOS pela rotina do jogo medida no gabarito (decisão
    # 21a); sem botão (neutro), a velocidade vai marcada como estimativa
    forca = r["forca"]
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
        "velocidade_estimada": True,
        "estado_vertical": r["estado_vertical"],
        "postura": r["postura"],
        "movimento": r["movimento"],
        "no_ar": r["no_ar"],
        # de onde veio cada afirmação (rota B): "lido" da demo ou "inferido"
        # pela rotina do jogo -- a ficha mostra, nunca mistura em silêncio
        "fontes": {"botao": r.get("fonte_do_botao"), "postura": r.get("fonte_da_postura"),
                   "no_ar": r.get("fonte_do_no_ar"), "origem": r.get("fonte_da_origem")},
        "jogador": r["thrower"],
        "partida": r["match_id"],
        "round": r["round_num"],
        "segundos_no_round": None if seg is None else round(seg, 1),
        # Reescrever (R0): o lado de quem lançou e os tempos reais da demo (nulo = a demo não diz; ver tempos_e_lado)
        "lado": r["lado"],
        "voo_s": r["voo_s"],
        "efeito_s": r["efeito_s"],
    }


def biblioteca_do_mapa(df: pl.DataFrame, mapa: str) -> dict:
    m = df.filter(pl.col("mapa") == mapa)
    exatos = m.filter(pl.col("reproducao_exata") & pl.col("tick_soltura").is_not_null()
                      & pl.col("x").is_not_null() & pl.col("x_final").is_not_null())
    v = exatos["velocidade_arremesso"].drop_nulls().to_numpy()
    grupos = grupos_de_forca(v)          # só diagnóstico (decisão 5): o rótulo vem do botão
    entradas = [_entrada(r) for r in
                exatos.sort(["match_id", "round_num", "tick_soltura", "entity_id"]).iter_rows(named=True)]
    return {
        "formato": "biblioteca-de-arremessos",
        "versao": FORMATO_LINEUPS,
        "mapa": mapa,
        "partidas": int(m["match_id"].n_unique()),
        "arremessos_no_corpus": int(m.height),
        "arremessos_exatos": len(entradas),
        "grupos_de_forca": [{"centro": round(c, 0), "n": n} for c, n in grupos],
        "rotulos_confirmados": True,          # rótulo pelo botão medido no gabarito
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
