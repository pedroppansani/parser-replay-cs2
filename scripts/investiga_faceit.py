"""Investigação FACEIT (decisão 21a): os neutros por tolerância vêm do tick?

EXPLORATÓRIO. Não muda a produção. As demos de FACEIT não gravam
`grenade_thrown`: o tick da soltura vem da ancoragem geométrica, que nas demos
de campeonato acerta o tick exato em 39,7% e ±1 em 87,9% (decisão 21c). A
hipótese: é esse erro de tick que deixa a FACEIT com mais neutros por
tolerância (build 14178: 3,2% contra 0,1-0,5%).

Regras testadas -- cada uma aplicada IGUAL a todos os arremessos (escolher o
tick por arremesso não vale):
  ancoragem-1, ancoragem, ancoragem+1   a soltura da ancoragem deslocada
  projetil, projetil-1                  o tick do primeiro ponto do projétil
                                        (nas demos de campeonato ele é a
                                        soltura em 100%)

Dois quadros:
  1. FACEIT (partidas sem grenade_thrown): contra a regra de hoje (ancoragem),
     quantos neutros por tolerância ganham botão, quantos rotulados TROCAM de
     botão (piora) e quantos perdem o botão;
  2. CONTROLE com gabarito: nas partidas com a força lida da demo (rota B), o
     grenade_thrown é ignorado de propósito -- a condição da FACEIT -- e o
     botão de cada regra é conferido contra o botão LIDO.

Uso:
    py -3.12 -m scripts.investiga_faceit
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

import numpy as np
import polars as pl

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))
import metrics.grenade_throws as gt  # noqa: E402
from parsing.parser import TABELAS_DA_VERDADE, load_interim  # noqa: E402

INTERIM = RAIZ / "data" / "interim"
PROCESSED = RAIZ / "data" / "processed"
REGRAS = ("ancoragem-1", "ancoragem", "ancoragem+1", "projetil-1", "projetil")
ATUAL = "ancoragem"
GUARDA = "vetor incoerente com o voo"
_ancora_original = gt.ancora_arremessos


def _com_regra(regra: str):
    """`ancora_arremessos` com a soltura trocada pela regra, mira e pés relidos."""
    base, _, d = regra.partition("-") if "-" in regra else regra.partition("+")
    delta = (-1 if "-" in regra else 1) * int(d) if d else 0

    def ancora(lancamentos, tk, tickrate, offset_mao=None):
        saida, offset = _ancora_original(lancamentos, tk, tickrate, offset_mao)
        if regra == ATUAL:
            return saida, offset
        nova = []
        for a in saida:
            if a.get("tick_soltura") is None:
                nova.append(a)
                continue
            t = (int(a["tick_soltura"]) if base == "ancoragem" else int(a["tick_primeiro"])) + delta
            i = tk.indices(a["steamid"], np.array([t], dtype=np.int64))
            dj = tk.por_jogador.get(int(a["steamid"]))
            if i is None or dj is None:
                nova.append({**a, "tick_soltura": None})
                continue
            nova.append({**a, "tick_soltura": t, "pos_soltura": dj["pos"][i[0]].copy(),
                         "pitch": float(dj["pitch"][i[0]]), "yaw": float(dj["yaw"][i[0]])})
        return nova, offset
    return ancora


def arremessos(partida: str, regra: str) -> pl.DataFrame:
    """Os arremessos de uma partida SEM o grenade_thrown e sem a verdade da demo."""
    t = load_interim(INTERIM, partida)
    t["rounds"] = pl.read_parquet(PROCESSED / partida / "rounds.parquet")
    t = {k: v for k, v in t.items() if k not in TABELAS_DA_VERDADE + ("grenade_thrown",)}
    gt.ancora_arremessos = _com_regra(regra)
    try:
        pr, _ = gt.grenade_throws(t, 64)
    finally:
        gt.ancora_arremessos = _ancora_original
    return pr


def motivo(r: dict) -> str:
    if r["botao"] is not None:
        return "botão"
    if r["estado_vertical"] == GUARDA:
        return "guarda do voo"
    if r["velocidade_arremesso"] is not None:
        return "tolerância"
    return str(r["estado_vertical"])


def partidas() -> tuple[list[str], list[str]]:
    faceit, controle = [], []
    for d in sorted(INTERIM.iterdir()):
        if not d.is_dir() or not (PROCESSED / d.name / "rounds.parquet").exists():
            continue
        if all((d / f"{n}.parquet").exists() for n in TABELAS_DA_VERDADE):
            controle.append(d.name)
        elif not (d / "grenade_thrown.parquet").exists():
            faceit.append(d.name)
    return faceit, controle


def quadro_faceit(lista: list[str]) -> dict:
    tot = {r: Counter() for r in REGRAS}
    trocas = {r: [] for r in REGRAS}
    por_partida = {}
    for p in lista:
        base = {(r["round_num"], r["entity_id"], r["tick_primeiro"]): r for r in arremessos(p, ATUAL).iter_rows(named=True)}
        por_partida[p] = Counter(motivo(r) for r in base.values())
        for regra in REGRAS:
            for r in arremessos(p, regra).iter_rows(named=True):
                a = base.get((r["round_num"], r["entity_id"], r["tick_primeiro"]))
                if a is None:
                    continue
                c = tot[regra]
                c["arremessos"] += 1
                c[f"motivo: {motivo(r)}"] += 1
                if a["botao"] is not None and r["botao"] is not None and a["botao"] != r["botao"]:
                    c["TROCA de botão (piora)"] += 1
                    trocas[regra].append(f"{p}:{r['round_num']}:{r['entity_id']} {a['botao']}->{r['botao']}")
                elif a["botao"] is not None and r["botao"] is None:
                    c[f"perdeu o botão: {motivo(r)}"] += 1
                elif a["botao"] is None and r["botao"] is not None:
                    c[f"ganhou botão (era {motivo(a)})"] += 1
    return {"total": tot, "trocas": trocas, "por_partida": por_partida}


def quadro_controle(lista: list[str]) -> dict:
    tot = {r: Counter() for r in REGRAS}
    for p in lista:
        lidos = pl.read_parquet(INTERIM / p / "arremessos_demo.parquet")
        # o projétil nasce no tick_primeiro (o primeiro ponto É o tick da soltura oficial)
        gab = {(r["entity_id"], r["tick"]): gt.botao_da_forca_lida(r["forca"]) for r in lidos.iter_rows(named=True)}
        for regra in REGRAS:
            for r in arremessos(p, regra).iter_rows(named=True):
                b = gab.get((r["entity_id"], r["tick_primeiro"]))
                if b is None:
                    continue
                c = tot[regra]
                c["com gabarito"] += 1
                if r["botao"] is None:
                    c[f"neutro: {motivo(r)}"] += 1
                else:
                    c["rotulados"] += 1
                    c["certos" if r["botao"] == b else "ERRADOS"] += 1
                if r["tick_soltura"] is not None:
                    c[f"tick - projétil = {int(r['tick_soltura']) - int(r['tick_primeiro']):+d}"] += 1
    return tot


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    faceit, controle = partidas()
    print(f"FACEIT (sem grenade_thrown): {faceit}")
    print(f"controle (força lida da demo): {controle}\n")
    f = quadro_faceit(faceit)
    print("== 1. FACEIT, cada regra contra a de hoje (ancoragem)")
    chaves = sorted({k for c in f["total"].values() for k in c})
    print("| | " + " | ".join(REGRAS) + " |\n|---|" + "---|" * len(REGRAS))
    for k in chaves:
        print(f"| {k} | " + " | ".join(str(f["total"][r][k]) for r in REGRAS) + " |")
    for r in REGRAS:
        if f["trocas"][r]:
            print(f"  trocas com {r}: {f['trocas'][r][:15]}")
    print("\n  hoje, por partida:", {p: dict(c) for p, c in f["por_partida"].items()})
    c = quadro_controle(controle)
    print("\n== 2. CONTROLE: mesma condição (sem grenade_thrown), botão conferido contra o LIDO")
    chaves = sorted({k for x in c.values() for k in x})
    print("| | " + " | ".join(REGRAS) + " |\n|---|" + "---|" * len(REGRAS))
    for k in chaves:
        print(f"| {k} | " + " | ".join(str(c[r][k]) for r in REGRAS) + " |")
    (RAIZ / "data" / "reference" / "investigacao_faceit.json").write_text(json.dumps(
        {"faceit": faceit, "controle": controle,
         "faceit_total": {r: dict(v) for r, v in f["total"].items()}, "faceit_trocas": f["trocas"],
         "controle_total": {r: dict(v) for r, v in c.items()}}, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
