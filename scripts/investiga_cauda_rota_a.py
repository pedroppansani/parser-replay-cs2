"""Item 7, rota A: as três investigações da cauda, a tolerância do botão e a
generalização por partida. EXPLORATÓRIO: não toca a produção.

Uso:
    py -3.12 -m scripts.investiga_cauda_rota_a            # gabarito da match_23
    py -3.12 -m scripts.investiga_cauda_rota_a --corpus   # + corpus inteiro (interim)

1. Cauda vertical da posição de saída: o resíduo (medido - calculado) é
   decomposto ao longo de -u' (recuo por obstrução) e na perpendicular, e
   procura-se outro jogador vivo à frente do olho.
2. Erro de velocidade no chão: velocidade do jogador com vários alinhamentos
   no tempo, e a correlação do erro com a aceleração.
3. Falhas no ar: a vz de decolagem estimada pela parábola (mais meio passo de
   gravidade, 800/128) tem de ser compatível com um pulo; e a janela depois da
   decolagem em que o jogo usa a vz fixa (decolagem - 80).
Depois: tolerância = ceil(2 × p99 do erro de velocidade onde o modelo se
aplica), cobertura com ela e com 118, e "no ar" nos três grupos por partida e
por build do jogo (header.json, patch_version).
"""
from __future__ import annotations

import contextlib
import io
import json
import math
import runpy
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
import polars as pl

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

MEIO_PASSO = 800.0 / 128           # meio passo de gravidade na decolagem (medido: -6,22 na mediana)
VZ_PULO = 298.868                  # moda de m_flLastJumpVelocityZ na match_23
LIMITE_VZ_DECOLAGEM = 10.0         # |estimada + meio passo - 298,868|: p99 dos bons 8,57 (n = 93)
JANELA_REGRA_MAX = 13.5            # regra comprovada no gabarito de 6 a 13 ticks
JANELA_VZ_REAL_MIN = 19            # 16:81 (19 ticks) usa a vz real; corpus 19+: 100% com ela
CONF = np.array([198.0, 443.0, 675.0])


class _Mudo(io.StringIO):
    def reconfigure(self, **_):
        pass


def prototipo() -> dict:
    with contextlib.redirect_stdout(_Mudo()):
        return runpy.run_path(str(RAIZ / "scripts/prototipo_rota_a.py"))


def q(v, c=2) -> str:
    v = np.asarray([x for x in v if x is not None and np.isfinite(x)], dtype=float)
    return (f"{np.median(v):.{c}f} [p5 {np.percentile(v, 5):.{c}f} p95 {np.percentile(v, 95):.{c}f}] n={v.size}"
            if v.size else "-")


def pos(a: dict, k: int) -> np.ndarray:
    """Pés na tabela de ticks, k ticks depois da soltura (0 = soltura)."""
    e = a["entrada"]
    i = len(e["z_janela"]) - 2 + k
    return np.array([*e["xy_janela"][i], e["z_janela"][i]])


def investigacao_1(g: dict) -> None:
    A, p0_calc = g["A"], g["p0_calc"]
    ticks = pl.read_parquet(RAIZ / "data/interim/match_23/ticks.parquet").select("tick", "steamid", "X", "Y", "Z", "is_alive")
    ev = pl.read_parquet(RAIZ / "data/interim/match_23/grenade_thrown.parquet").select("tick", "user_steamid", "user_X", "user_Y")
    for onde, filtro in (("chão", lambda a: a["demo"]["no_chao"]), ("ar", lambda a: not a["demo"]["no_chao"])):
        falhas, com_jogador = [], 0
        for a in A:
            if not filtro(a) or 0 < a["demo"]["duck_amount"] < 1:
                continue
            r = np.array(a["demo"]["p0"]) - p0_calc(a)
            if np.linalg.norm(r) < 1:
                continue
            u = a["u2"]
            recuo = float(r @ -u)
            falhas.append((recuo, float(np.linalg.norm(r + recuo * u)), float(r[2]), float(np.linalg.norm(r))))
            e = a["entrada"]
            lin = ev.filter((pl.col("tick") == e["tick_soltura"]) & ((pl.col("user_X") - e["pes"][0]).abs() < 0.01)
                            & ((pl.col("user_Y") - e["pes"][1]).abs() < 0.01))
            olho = p0_calc(a) - 16 * u
            for o in ticks.filter((pl.col("tick") == e["tick_soltura"]) & (pl.col("steamid") != int(lin["user_steamid"][0]))
                                  & pl.col("is_alive")).iter_rows(named=True):
                rel = np.array([o["X"], o["Y"], o["Z"] + 36.0]) - olho
                s = rel @ u
                if 0 <= s <= 38 and np.linalg.norm(rel - s * u) <= 32:
                    com_jogador += 1
                    break
        f = np.array(falhas)
        print(f"  {onde}: erro >= 1u em {len(f)}; recuo ao longo de -u' {q(f[:, 0])}; perpendicular {q(f[:, 1])}")
        print(f"     |vertical|/erro {q(np.abs(f[:, 2]) / f[:, 3], 3)}; vertical negativo {int((f[:, 2] < 0).sum())}/{len(f)}; "
              f"recuo 0-16 com perpendicular < 1: {int(((f[:, 0] >= 0) & (f[:, 0] <= 16.5) & (f[:, 1] < 1)).sum())}; "
              f"com jogador à frente: {com_jogador}")
    # subida recente dos pés (suavização de degrau da câmera)
    ch = [a for a in A if a["demo"]["no_chao"] and a["demo"]["duck_amount"] in (0.0, 1.0)]
    for janela in (16, 64):
        ruim = [np.ptp(np.array(a["entrada"]["z_janela"])[-(janela + 2):-1]) for a in ch
                if np.linalg.norm(np.array(a["demo"]["p0"]) - p0_calc(a)) >= 1]
        bom = [np.ptp(np.array(a["entrada"]["z_janela"])[-(janela + 2):-1]) for a in ch
               if np.linalg.norm(np.array(a["demo"]["p0"]) - p0_calc(a)) < 1]
        print(f"  variação de z dos pés nos {janela} ticks anteriores: falhas {q(ruim)} | passam {q(bom)}")


def investigacao_2(g: dict) -> None:
    A, VEL = g["A"], g["VEL"]
    ch = [a for a in A if a["demo"]["no_chao"] and a["b"] is not None]
    variantes = {"centrada em t (produção)": lambda a: (pos(a, 1) - pos(a, -1)) * 32,
                 "centrada em t-1": lambda a: (pos(a, 0) - pos(a, -2)) * 32,
                 "para trás (t - t-1)": lambda a: (pos(a, 0) - pos(a, -1)) * 64,
                 "para frente (t+1 - t)": lambda a: (pos(a, 1) - pos(a, 0)) * 64}
    for nome, f in variantes.items():
        ev = np.array([np.linalg.norm(VEL[a["b"]] * a["u2"] + 1.25 * np.array([*f(a)[:2], 0.0]) - np.array(a["demo"]["v0"]))
                       for a in ch])
        print(f"  {nome:26s} <5 u/s {np.mean(ev < 5):.1%}  mediana {np.median(ev):.2f}  p95 {np.percentile(ev, 95):.2f}  máx {ev.max():.1f}")
    acc = np.array([np.linalg.norm(((pos(a, 1) - pos(a, 0)) * 64 - (pos(a, 0) - pos(a, -1)) * 64)[:2]) * 64 for a in ch])
    ev = np.array([np.linalg.norm(VEL[a["b"]] * a["u2"] + 1.25 * np.array([*a["v"][:2], 0.0]) - np.array(a["demo"]["v0"])) for a in ch])
    print(f"  correlação erro x aceleração horizontal: {np.corrcoef(acc, ev)[0, 1]:.3f}")


def modelo(a: dict, vh_em) -> tuple:
    """(vz usada, velocidade horizontal, o modelo se aplica?)."""
    if not a["ar"]:
        return 0.0, a["v"][:2], True
    if a.get("tau_dec") is None:
        return None, None, False
    t = -a["tau_dec"] * 64
    if abs(a["vz_dec"] + MEIO_PASSO - VZ_PULO) > LIMITE_VZ_DECOLAGEM:
        return None, None, False
    if t >= JANELA_VZ_REAL_MIN:
        return a["v"][2], a["v"][:2], True
    if t > JANELA_REGRA_MAX:
        return None, None, False
    vh = vh_em(a, (a["tau_dec"] + 0.1) * 64 - 0.5)
    return VZ_PULO - 80.0, (a["v"][:2] if vh is None else vh), True


def investigacao_3_e_tolerancia(g: dict) -> int:
    A, VEL, vh_em = g["A"], g["VEL"], g["vh_em"]
    bons, ruins = [], []
    for a in A:
        if not a["ar"] or a.get("vz_dec") is None:
            continue
        vh = vh_em(a, (a["tau_dec"] + 0.1) * 64 - 0.5)
        vh = a["v"][:2] if vh is None else vh
        e = np.linalg.norm(VEL[a["b_rec"]] * a["u2"] + 1.25 * np.array([*vh, a["vz_usada"]]) - np.array(a["demo"]["v0"]))
        (bons if e < 5 else ruins).append((a["id"], a["vz_dec"] + MEIO_PASSO - VZ_PULO, -a["tau_dec"] * 64, e))
    print(f"  vz de decolagem estimada - 298,868 nos que acertam: {q([x[1] for x in bons])}")
    for x in ruins:
        print(f"    erra: {x[0]} desvio {x[1]:.1f} ticks desde a decolagem {x[2]:.1f} erro {x[3]:.1f}")
    erros = []
    for a in A:
        vz, vh, ok = modelo(a, vh_em)
        a["ok"] = ok
        if ok:
            vj = np.array([*vh, vz])
            erros.append(np.linalg.norm(VEL[a["b_rec"]] * a["u2"] + 1.25 * vj - np.array(a["demo"]["v0"])))
            a["rel2"] = float(np.linalg.norm(a["vp"] - 1.25 * vj))
    erros = np.array(erros)
    tol = math.ceil(2 * np.percentile(erros, 99))
    print(f"  neutros por detecção: {[a['id'] for a in A if not a['ok']]}")
    print(f"  erro de velocidade onde o modelo se aplica: {q(erros)}; p99 {np.percentile(erros, 99):.2f}; <5 u/s {np.mean(erros < 5):.1%}")
    print(f"  TOLERÂNCIA = ceil(2 × p99) = {tol} u/s")
    for t in (tol, 118):
        lab = [a for a in A if a["ok"] and min(abs(a["rel2"] - c) for c in VEL.values()) <= t]
        ac = sum(min(VEL, key=lambda b: abs(VEL[b] - a["rel2"])) == a["b_rec"] for a in lab)
        print(f"  match_23 tol {t:3d}: cobertura {len(lab)}/{len(A)}, acerto {ac}/{len(lab)}")
    return tol


def corpus(tol: int) -> None:
    import scripts.investiga_props_arremesso as ip
    import metrics.grenade_throws as gt
    from parsing.parser import load_interim
    g_tick = -800.0 / 64 ** 2
    C = {0.0: 202.5, 0.5: 438.7, 1.0: 675.0}
    por = defaultdict(list)
    cobertura = {tol: 0, 118: 0}
    total = 0
    for d in sorted((RAIZ / "data/interim").glob("match_*")):
        t = load_interim(RAIZ / "data/interim", d.name)
        tk = gt._Ticks(t["ticks"])
        build = json.loads((d / "header.json").read_text(encoding="utf-8"))["patch_version"]
        for a in ip.arremessos_da_partida(d.name):
            idx = tk.indices(a["steamid"], np.arange(a["tick_soltura"] - 80, a["tick_soltura"] + 2, dtype=np.int64))
            n = 0
            if idx is not None:
                z = tk.por_jogador[int(a["steamid"])]["pos"][idx, 2]
                d2 = z[2:] - 2 * z[1:-1] + z[:-2]
                i = len(d2) - 2
                while i >= 0 and abs(d2[i] - g_tick) < 0.05:
                    n += 1
                    i -= 1
            vj = a["vj"]
            vz = 0.0 if n == 0 else (vj[2] if n >= JANELA_VZ_REAL_MIN else (None if n > JANELA_REGRA_MAX else VZ_PULO - 80))
            depois = None if vz is None else float(np.linalg.norm(a["vp"] - 1.25 * np.array([vj[0], vj[1], vz])))
            total += 1
            for tt in cobertura:
                if depois is not None and min(abs(depois - c) for c in C.values()) <= tt:
                    cobertura[tt] += 1
            if abs(vj[2]) >= gt.VELOCIDADE_VERTICAL_NO_AR:
                antes = float(np.linalg.norm(a["vp"] - 1.25 * vj))
                por[(d.name, build)].append((np.min(np.abs(antes - CONF)) <= 60,
                                             None if depois is None else np.min(np.abs(depois - CONF)) <= 60))
    print(f"  cobertura do botão no corpus: tol {tol} {cobertura[tol] / total:.2%} | tol 118 {cobertura[118] / total:.2%} (n = {total})")
    grupos = defaultdict(lambda: [0, 0, 0])
    for (p, b), v in sorted(por.items()):
        a_ = np.mean([x[0] for x in v])
        d_ = np.mean([x[1] for x in v if x[1] is not None])
        marca = "  <-- PIOROU" if d_ < a_ else ""
        print(f"  {p} build {b}: no ar {len(v)}  {a_:.1%} -> {d_:.1%}{marca}")
        grupos[b][0] += len(v)
        grupos[b][1] += sum(x[0] for x in v)
        grupos[b][2] += sum(x[1] for x in v if x[1] is not None)
    for b, (n, a_, d_) in sorted(grupos.items()):
        print(f"  build {b}: {a_ / n:.1%} -> {d_ / n:.1%} (n = {n})")


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    g = prototipo()
    print("== 1. cauda vertical da posição de saída (hipótese: obstrução)")
    investigacao_1(g)
    print("\n== 2. erro de velocidade no chão (hipótese: tempo)")
    investigacao_2(g)
    print("\n== 3. falhas no ar e tolerância do botão")
    tol = investigacao_3_e_tolerancia(g)
    if sys.argv[1:] == ["--corpus"]:
        print("\n== corpus")
        corpus(tol)


if __name__ == "__main__":
    main()
