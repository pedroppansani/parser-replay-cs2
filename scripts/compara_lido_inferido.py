"""Lido x inferido: o teste permanente da rota A nas partidas com a verdade da demo.

Para cada partida cujo interim tem as tabelas da rota B (arremessos_demo e
movimento), calcula os arremessos duas vezes:
  - LIDO: como a produção faz (a demo vence onde grava);
  - INFERIDO: com as tabelas novas RETIRADAS de propósito -- a rota A pura.
e mede, por partida, a concordância entre os dois onde o inferido afirma algo.
É a validação contínua da rota A (e da guarda do voo): toda demo nova que
entrar com .dem aumenta esta amostra.

Uso:
    py -3.12 -m scripts.compara_lido_inferido            # todas as partidas com a verdade da demo
    py -3.12 -m scripts.compara_lido_inferido match_23
    py -3.12 -m scripts.compara_lido_inferido --verdade <pasta> ...  # tabelas novas de outra pasta (ensaio)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import polars as pl

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))
from metrics.grenade_throws import grenade_throws  # noqa: E402
from parsing.parser import TABELAS_DA_VERDADE, load_interim  # noqa: E402

INTERIM = RAIZ / "data" / "interim"
PROCESSED = RAIZ / "data" / "processed"


def partidas_com_verdade(pasta: Path = INTERIM) -> list[str]:
    return sorted(d.name for d in pasta.iterdir()
                  if d.is_dir() and all((d / f"{n}.parquet").exists() for n in TABELAS_DA_VERDADE))


def _tickrate(partida: str) -> int:
    meta = PROCESSED / partida / "match_meta.json"
    if meta.exists():
        return int(json.loads(meta.read_text(encoding="utf-8")).get("tickrate", 64) or 64)
    return 64


def compara(partida: str, verdade: Path | None = None) -> dict:
    """Concordância lido x inferido numa partida (contagens, não só taxas)."""
    t = load_interim(INTERIM, partida)
    if verdade is not None:
        for n in TABELAS_DA_VERDADE:
            t[n] = pl.read_parquet(Path(verdade) / partida / f"{n}.parquet")
    if (PROCESSED / partida / "rounds.parquet").exists():
        t["rounds"] = pl.read_parquet(PROCESSED / partida / "rounds.parquet")
    tr = _tickrate(partida)
    lido, _ = grenade_throws(t, tr)
    inferido, _ = grenade_throws({k: v for k, v in t.items() if k not in TABELAS_DA_VERDADE}, tr)
    chave = ["round_num", "entity_id", "tick_soltura"]
    j = lido.join(inferido, on=chave, how="inner", suffix="_inf")

    def conta(campo: str) -> dict:
        s = j.filter((pl.col(f"fonte_do_{campo}" if campo != "postura" else "fonte_da_postura") == "lido")
                     & pl.col(f"{campo}_inf").is_not_null() & pl.col(campo).is_not_null())
        ok = s.filter(pl.col(campo) == pl.col(f"{campo}_inf"))
        return {"n": s.height, "iguais": ok.height,
                "diferentes": [f"{partida}:{r['round_num']}:{r['entity_id']}" for r in
                               s.filter(pl.col(campo) != pl.col(f"{campo}_inf")).iter_rows(named=True)]}

    o = j.filter((pl.col("fonte_da_origem") == "lido") & pl.col("x_saida_inf").is_not_null())
    dist = np.sqrt(((o.select("x_saida", "y_saida", "z_saida").to_numpy()
                     - o.select("x_saida_inf", "y_saida_inf", "z_saida_inf").to_numpy()) ** 2).sum(axis=1))
    return {
        "partida": partida, "arremessos": lido.height,
        "fonte_lida": {c: int((lido[c] == "lido").sum()) for c in
                       ("fonte_do_botao", "fonte_da_postura", "fonte_do_no_ar", "fonte_da_origem")},
        "botao": conta("botao"), "no_ar": conta("no_ar"), "postura": conta("postura"),
        # só com o que o inferido afirma: neutro não é discordância
        "neutros_no_inferido": {"botao": int(j.filter(pl.col("botao_inf").is_null()).height),
                                "postura": int(j.filter(pl.col("postura_inf").is_null()).height),
                                "no_ar": int(j.filter(pl.col("no_ar_inf").is_null()).height)},
        "origem": {"n": int(dist.size),
                   "mediana": None if not dist.size else round(float(np.median(dist)), 4),
                   "p99": None if not dist.size else round(float(np.percentile(dist, 99)), 4),
                   "maxima": None if not dist.size else round(float(dist.max()), 4)},
    }


def main(args: list[str]) -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    verdade = None
    if args[:1] == ["--verdade"]:
        verdade, args = Path(args[1]), args[2:]
    partidas = args or partidas_com_verdade(verdade or INTERIM)
    print("| partida | arremessos | botão | no ar | postura | neutros do inferido (botão/postura/no ar) | origem: mediana / p99 / máx (u) |")
    print("|---|---|---|---|---|---|---|")
    for p in partidas:
        r = compara(p, verdade)
        f = lambda c: f"{r[c]['iguais']}/{r[c]['n']} ({r[c]['iguais'] / r[c]['n']:.2%})" if r[c]["n"] else "-"  # noqa: E731
        n = r["neutros_no_inferido"]
        print(f"| {p} | {r['arremessos']} | {f('botao')} | {f('no_ar')} | {f('postura')} | "
              f"{n['botao']}/{n['postura']}/{n['no_ar']} | {r['origem']['mediana']} / {r['origem']['p99']} / {r['origem']['maxima']} |")
        for c in ("botao", "no_ar", "postura"):
            if r[c]["diferentes"]:
                print(f"    {c} diferentes: {r[c]['diferentes'][:12]}")


if __name__ == "__main__":
    main(sys.argv[1:])
