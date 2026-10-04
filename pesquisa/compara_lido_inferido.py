"""Lido x inferido: o teste permanente da rota A nas partidas com a verdade da demo.

Para cada partida cujo interim tem as tabelas da rota B (arremessos_demo e
movimento), calcula os arremessos duas vezes:
  - LIDO: como a produção faz (a demo vence onde grava);
  - INFERIDO: com as tabelas novas RETIRADAS de propósito -- a rota A pura.
e mede, por partida, a concordância entre os dois onde o inferido afirma algo.
É a validação contínua da rota A (e da guarda do voo): toda demo nova que
entrar com .dem aumenta esta amostra.

Uso:
    py -3.12 -m pesquisa.compara_lido_inferido            # todas as partidas com a verdade da demo
    py -3.12 -m pesquisa.compara_lido_inferido match_23
    py -3.12 -m pesquisa.compara_lido_inferido --verdade <pasta> ...  # tabelas novas de outra pasta (ensaio)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import polars as pl

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))
from metrics.verdade_do_arremesso import INTERIM, compara, partidas_com_verdade  # noqa: E402,F401


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
