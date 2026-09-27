"""Rota A, passo 3: verificações que NÃO mudam a produção (item 7, 2026-09-27).

Uso:
    py -3.12 -m scripts.verifica_rota_a      # corpus inteiro, a partir do interim

Monta uma tabela por arremesso com as regras propostas da rota A (queda livre
pela segunda diferença, decolagem pela parábola, janela do jump-throw, estado
vertical ambíguo, botão com tolerância de 21 u/s) e imprime:
  - decisão 2: os arremessos soltos de 14 a 18 ticks depois da decolagem, e
    qual vz (fixa ou real) acerta cada um;
  - neutros por regra e por tolerância, e a cobertura;
  - decisão 4: a caracterização dos que ficam neutros SÓ pela tolerância 21;
  - decisão 6: a margem da altura de saída contra o corte de postura,
    separando quem subiu recentemente.
"""
import json, sys, pickle
from pathlib import Path
import numpy as np, polars as pl
sys.stdout.reconfigure(encoding="utf-8")
R = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(R))
import metrics.grenade_throws as gt
import scripts.investiga_props_arremesso as ip
from parsing.parser import load_interim

T = 64; G = -800 / T ** 2
VEL = {0.0: 202.5, 0.5: 438.7, 1.0: 675.0}


def u_lanc(p, y):
    p2 = np.radians(-10 + p * (80 / 90 if p < 0 else 100 / 90)); y = np.radians(y)
    return np.array([np.cos(p2) * np.cos(y), np.cos(p2) * np.sin(y), -np.sin(p2)])


linhas = []
for d in sorted((R / "data/interim").glob("match_*")):
    t = load_interim(R / "data/interim", d.name)
    tk = gt._Ticks(t["ticks"])
    build = json.loads((d / "header.json").read_text(encoding="utf-8"))["patch_version"]
    for a in ip.arremessos_da_partida(d.name):
        ts = int(a["tick_soltura"])
        idx = tk.indices(a["steamid"], np.arange(ts - 64, ts + 2, dtype=np.int64))
        if idx is None:
            continue
        P = tk.por_jogador[int(a["steamid"])]["pos"][idx]
        z = P[:, 2]
        d2 = z[2:] - 2 * z[1:-1] + z[:-2]
        i = len(d2) - 2; n = 0
        while i >= 0 and abs(d2[i] - G) < 0.05:
            n += 1; i -= 1
        v = (P[-1] - P[-3]) * T / 2
        tau_dec = vz_dec = vz_t = None
        if n >= 1:
            k0 = len(z) - 2 - n
            tau = (np.arange(k0, len(z)) - (len(z) - 2)) / T
            b_, c_ = np.polyfit(tau, z[k0:] + 400 * tau ** 2, 1)
            vz_t = b_
            if k0 >= 1:
                disc = b_ * b_ - 1600 * (z[k0 - 1] - c_)
                if disc >= 0:
                    tau_dec = (b_ - np.sqrt(disc)) / 800
                    vz_dec = b_ - 800 * tau_dec
        linhas.append({"partida": d.name, "build": build, "arma": a["kind"], "round": a["round_num"], "entity_id": a["entity_id"],
                       "n_ar": n, "vx": v[0], "vy": v[1], "vz": v[2], "vp": a["vp"].tolist(), "pitch": a["pitch"], "yaw": a["yaw"],
                       "tau_dec": tau_dec, "vz_dec": vz_dec, "vz_t": vz_t,
                       "p1": a["traj"][0].tolist(), "pes": np.asarray(a["pos_soltura"], float).tolist(),
                       "z_rel": (z - z[-2]).tolist(), "xy": P[:, :2].tolist(),
                       "subida16": float(np.ptp(z[-18:-1])), "subida64": float(np.ptp(z[:-1])),
                       "altura_modulo": a.get("altura_olhos")})




from collections import Counter
import numpy as np
sys.stdout.reconfigure(encoding="utf-8")
L = linhas
T = 64
VEL = {0.0: 202.5, 0.5: 438.7, 1.0: 675.0}
VZ_PULO, MEIO = 298.868, 800 / 128
TOL = 21
H_PE, H_AG = 63.31, 45.55
CORTE = (H_PE + H_AG) / 2


def u_lanc(p, y):
    p2 = np.radians(-10 + p * (80 / 90 if p < 0 else 100 / 90)); y = np.radians(y)
    return np.array([np.cos(p2) * np.cos(y), np.cos(p2) * np.sin(y), -np.sin(p2)])


def vh_em(x, k):
    J = np.array(x["xy"]); n = len(J); kk = (n - 2) + k
    i0 = int(np.floor(kk)); f = kk - i0
    if not (1 <= i0 < n - 2): return None
    return ((J[i0 + 1] - J[i0 - 1]) * 32) * (1 - f) + ((J[i0 + 2] - J[i0]) * 32) * f


def estado(x):
    """(regra, vz, vh) -- regra é o motivo quando neutro."""
    vh = np.array([x["vx"], x["vy"]])
    if x["n_ar"] == 0:
        if abs(x["vz"]) >= 60 and False:
            pass
        # estado vertical ambíguo: vz alta sem parábola formada
        if x["vz"] >= 150:
            return "ambíguo: vz alta sem parábola", None, None
        return "chão", 0.0, vh
    if x["tau_dec"] is None:
        return "ambíguo: queda sem decolagem na janela", None, None
    if abs(x["vz_dec"] + MEIO - VZ_PULO) > 10:
        return "ambíguo: parábola com vz de decolagem fora da faixa", None, None
    t = -x["tau_dec"] * T
    if t < 5.5:
        return "janela 0-5", None, None
    if t <= 13.5:
        v = vh_em(x, (x["tau_dec"] + 0.1) * T - 0.5)
        return "regra fixa 6-13", VZ_PULO - 80, (vh if v is None else v)
    if t < 18.5:
        return "janela 14-18", None, None
    return "vz real 19+", x["vz"], vh


for x in L:
    x["regra"], vz, vh = estado(x)
    x["t_dec"] = None if x["tau_dec"] is None else -x["tau_dec"] * T
    vp = np.array(x["vp"])
    x["rel_real"] = float(np.linalg.norm(vp - 1.25 * np.array([x["vx"], x["vy"], x["vz"]])))
    x["rel_fixa"] = float(np.linalg.norm(vp - 1.25 * np.array([x["vx"], x["vy"], VZ_PULO - 80])))
    if vz is None:
        x["rel"] = None; x["botao"] = None
    else:
        x["rel"] = float(np.linalg.norm(vp - 1.25 * np.array([vh[0], vh[1], vz])))
        c = min(VEL, key=lambda b: abs(VEL[b] - x["rel"]))
        x["dist"] = abs(VEL[c] - x["rel"])
        x["botao"] = c if x["dist"] <= TOL else None
        x["botao118"] = c if x["dist"] <= 118 else None

print("== decisão 2: os casos de 14 a 18 ticks desde a decolagem")
for x in sorted([x for x in L if x["regra"] == "janela 14-18"], key=lambda x: x["t_dec"]):
    d = lambda r: min(abs(r - c) for c in VEL.values())
    melhor = "regra fixa" if d(x["rel_fixa"]) < d(x["rel_real"]) else "vz real"
    print(f"  {x['partida']} r{x['round']:>2} e{x['entity_id']}: {x['t_dec']:5.2f} ticks | distância ao botão: regra fixa {d(x['rel_fixa']):6.1f}, vz real {d(x['rel_real']):6.1f} -> {melhor}")

print("\n== neutros por regra (corpus)")
print("  ", Counter(x["regra"] for x in L if x["botao"] is None and x["regra"] not in ("chão", "regra fixa 6-13", "vz real 19+")))
print("   neutros por tolerância (fora de 21 u/s):", sum(1 for x in L if x["rel"] is not None and x["botao"] is None))
print("   cobertura:", f"{sum(x['botao'] is not None for x in L) / len(L):.2%}", "de", len(L))

print("\n== decisão 4: os que ficam neutros SÓ pela tolerância 21 (tinham botão com 118)")
S = [x for x in L if x["rel"] is not None and x["botao"] is None and x.get("botao118") is not None]
print("  n =", len(S))
print("  estado:", Counter(x["regra"] for x in S))
mov = lambda x: "parado" if np.hypot(x["vx"], x["vy"]) < 70 else "em movimento"
print("  movimento:", Counter(mov(x) for x in S))
print("  arma:", Counter(x["arma"] for x in S))
print("  build:", Counter(x["build"] for x in S).most_common())
print("  partidas (top 8):", Counter(x["partida"] for x in S).most_common(8))
print("  ticks desde a decolagem (no ar):", Counter(int(round(x["t_dec"])) for x in S if x["t_dec"] is not None).most_common())
print("  botão mais próximo:", Counter(x["botao118"] for x in S))
# concentração relativa: fração dos neutros por partida contra o total de arremessos da partida
tot = Counter(x["partida"] for x in L)
fr = sorted(((c / tot[p], p, c, tot[p]) for p, c in Counter(x["partida"] for x in S).items()), reverse=True)[:6]
print("  maior fração por partida:", [(p, f"{f:.1%}", f"{c}/{n}") for f, p, c, n in fr])
print("  fração média:", f"{len(S) / len(L):.2%}")
bs = Counter(x["build"] for x in L)
print("  fração por build:", sorted(((b, f"{c / bs[b]:.2%}") for b, c in Counter(x["build"] for x in S).items()), key=lambda t: t[1], reverse=True))
armas = Counter(x["arma"] for x in L)
print("  fração por arma:", {a: f"{c / armas[a]:.2%}" for a, c in Counter(x["arma"] for x in S).items()})
chao_mov = [x for x in S if x["regra"] == "chão"]
print("  no chão: velocidade horizontal p50", round(float(np.median([np.hypot(x['vx'], x['vy']) for x in chao_mov])), 0),
      "| vz p5/p50/p95", np.percentile([x["vz"] for x in chao_mov], [5, 50, 95]).round(0))

print("\n== decisão 6: margem da postura (altura corrigida pelo botão contra o corte de", round(CORTE, 2), "u)")
Hs = []
for x in L:
    if x["botao"] is None or x["regra"] not in ("chão", "regra fixa 6-13", "vz real 19+"): continue
    u = u_lanc(x["pitch"], x["yaw"])
    if x["regra"] == "regra fixa 6-13":
        t01 = x["tau_dec"] + 0.1
        zref = x["pes"][2] + 0 + (x["z_rel"][-2]) + x["vz_t"] * t01 - 400 * t01 ** 2   # z(t)=pés da tabela; z_rel é relativo a z(t)
        zt = x["p1"][2] - (x["pes"][2] + x["vz"] / 64)  # não usado
        # z da tabela na soltura = pés do evento (t-1) + vz/64
        z_sol = x["pes"][2] + x["vz"] / 64
        zref = z_sol + x["vz_t"] * t01 - 400 * t01 ** 2
    else:
        zref = x["pes"][2] + x["vz"] / 64
    H = x["p1"][2] - zref - 16 * u[2] - 12 * (x["botao"] - 1)
    Hs.append((H, x["subida16"], x["subida64"], x["regra"]))
H = np.array([h[0] for h in Hs]); s16 = np.array([h[1] for h in Hs]); s64 = np.array([h[2] for h in Hs])
pe = H > CORTE
print(f"  em pé pela regra: {pe.sum()} | agachado: {(~pe).sum()}")
for nome, m in (("sem subida recente (64 ticks < 8u)", s64 < 8), ("com subida recente (64 ticks >= 8u)", s64 >= 8)):
    mm = pe & m
    print(f"  {nome}: n={mm.sum()} menor distância ao corte {np.min(H[mm] - CORTE):.2f}u | "
          f"a menos de 3u do corte: {np.sum(mm & (H - CORTE < 3))} | p1 {np.percentile(H[mm] - CORTE, 1):.2f}")
mm = ~pe
print(f"  agachados: menor distância ao corte (por baixo) {np.min(CORTE - H[mm]):.2f}u | a menos de 3u: {np.sum(mm & (CORTE - H < 3))}")
print("  histograma perto do corte (H - corte), todos:", np.histogram(H - CORTE, bins=[-6, -3, -1, 0, 1, 3, 6])[0].tolist(), "bins [-6,-3,-1,0,1,3,6]")

