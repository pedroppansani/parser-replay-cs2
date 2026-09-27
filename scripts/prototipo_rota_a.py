"""Protótipo da rota A (item 7), medido no gabarito versionado da match_23.

EXPLORATÓRIO: não toca a produção. A inferência usa só o bloco 'entrada' do
gabarito (o que a produção tem sem o .dem) e compara com o bloco 'demo' (o que
o jogo gravou). Imprime a curva de "no ar", a decolagem estimada, a altura de
saída, a tolerância do botão e as cinco metas da rota A.

Uso:
    py -3.12 -m scripts.prototipo_rota_a

Resultado em 2026-09-27 (relatório ao Pedro): botão 431/431 com 3 neutros;
no ar 433/434; postura no chão 329/329; velocidade < 5 u/s 412/434 (94,9%);
posição de saída < 1 u 293/434 (67,5%) -- as duas últimas ABAIXO da meta.
"""
import json, sys
from pathlib import Path
import numpy as np
sys.stdout.reconfigure(encoding="utf-8")
G = __import__("json").loads(__import__("gzip").decompress((Path(__file__).resolve().parents[1] / "tests/fixtures/gabarito_arremessos_match_23.json.gz").read_bytes()))
A = G["arremessos"]
T = 64
g_t = -800.0 / T ** 2


def botao_gravado(f):
    return round(f * 2) / 2


def u_lanc(pitch, yaw):
    p = np.radians(-10 + pitch * (80 / 90 if pitch < 0 else 100 / 90)); y = np.radians(yaw)
    return np.array([np.cos(p) * np.cos(y), np.cos(p) * np.sin(y), -np.sin(p)])


def queda_livre(z, tol):
    """z = alturas dos pés de t-64 .. t+1. Devolve quantos ticks seguidos, terminando
    na soltura, têm segunda diferença igual à gravidade (|d2 - g| < tol)."""
    z = np.asarray(z)
    d2 = z[2:] - 2 * z[1:-1] + z[:-2]      # d2[i] centrado em z[i+1]
    i = len(d2) - 2                          # centrado em t (z[-2])
    n = 0
    while i >= 0 and abs(d2[i] - g_t) < tol:
        n += 1; i -= 1
    return n


for a in A:
    e = a["entrada"]; d = a["demo"]
    pv = np.array(e["pos_vizinhos"])
    a["v"] = (pv[1] - pv[0]) * T / 2
    a["u2"] = u_lanc(e["pitch"], e["yaw"])
    pp = np.array(e["proj_pontos"]); pt = e["proj_ticks"]
    a["vp"] = (pp[1] - pp[0]) / ((pt[1] - pt[0]) / T)
    a["b_rec"] = botao_gravado(d["forca"])

# ---- 1. no ar: curva contra m_hGroundEntity
print("== no ar pela queda livre (>= N ticks com d2 = g), contra m_hGroundEntity")
for tol in (0.005, 0.01, 0.02, 0.05, 0.1, 0.2):
    for nmin in (1, 2, 3):
        pred = [queda_livre(a["entrada"]["z_janela"], tol) >= nmin for a in A]
        real = [not a["demo"]["no_chao"] for a in A]
        ac = np.mean([p == r for p, r in zip(pred, real)])
        fp = sum(p and not r for p, r in zip(pred, real)); fn = sum(r and not p for p, r in zip(pred, real))
        print(f"  tol {tol:5.3f} N>={nmin}: acerto {ac:.4f} ({sum(p == r for p, r in zip(pred, real))}/{len(A)}) falso ar {fp} falso chão {fn}")

TOL = 0.05
for a in A:
    a["n_ar"] = queda_livre(a["entrada"]["z_janela"], TOL)
    a["ar"] = a["n_ar"] >= 1
for a in A:
    if a["ar"] == a["demo"]["no_chao"]:
        z = a["entrada"]["z_janela"]; d2 = np.diff(z, 2)
        print("ERRO no ar:", a["id"], "demo no_chao", a["demo"]["no_chao"], "z últimos", [round(x, 2) for x in z[-8:]], "d2", [round(x, 3) for x in d2[-6:]], "pulo há", a["entrada"]["tick_soltura"] - (a["demo"]["tick_do_pulo"] or 0))

print("\n== decolagem: tick em que a parábola começa, e a vz de decolagem estimada")
for a in A:
    if not a["ar"]:
        continue
    z = np.asarray(a["entrada"]["z_janela"])
    n = a["n_ar"]
    # d2 centrado em t, t-1, ..., t-n+1 bate com g -> os pontos z[t-n .. t+1] estão na parábola
    k_ini = len(z) - 2 - n            # índice do primeiro ponto da parábola (tick t-n)
    tt = np.arange(k_ini, len(z)) - (len(z) - 2)      # tempo em ticks relativo à soltura
    zz = z[k_ini:]
    # ajuste com g fixo: z + g/2 τ² = a + b τ
    tau = tt / T
    y = zz + 400.0 * tau ** 2
    b, c = np.polyfit(tau, y, 1)
    a["vz_t"] = b                              # vz na soltura pela parábola
    z_chao = z[k_ini - 1] if k_ini >= 1 else None   # último tick antes da parábola (no chão)
    a["z_chao"] = z_chao
    # instante da decolagem: onde a parábola cruza a altura do chão (antes de k_ini)
    # z(τ) = c + b τ - 400 τ² = z_chao -> raiz menor
    if z_chao is not None:
        disc = b * b - 4 * 400.0 * (z_chao - c)
        a["tau_dec"] = (b - np.sqrt(disc)) / (2 * 400.0) if disc >= 0 else None
        a["vz_dec"] = None if a["tau_dec"] is None else b - 800.0 * a["tau_dec"]
    a["ticks_dec_rec"] = a["entrada"]["tick_soltura"] - a["demo"]["tick_do_pulo"] if a["demo"]["tick_do_pulo"] else None
ar = [a for a in A if a["ar"] and not a["demo"]["no_chao"]]
print("  vz de decolagem estimada:", np.percentile([a["vz_dec"] for a in ar if a.get("vz_dec") is not None], [5, 25, 50, 75, 95]).round(2))
print("  gravada:", sorted(set(round(a["demo"]["vz_decolagem"], 2) for a in ar)))
err = [(a["vz_dec"] - a["demo"]["vz_decolagem"]) for a in ar if a.get("vz_dec") is not None]
print("  estimada - gravada:", np.percentile(err, [5, 25, 50, 75, 95]).round(2))
errt = [(-a["tau_dec"] * T - a["ticks_dec_rec"]) for a in ar if a.get("tau_dec") is not None]
print("  instante da decolagem (ticks antes da soltura) estimado - gravado:", np.percentile(errt, [5, 25, 50, 75, 95]).round(3))
for a in ar:
    if a.get("vz_dec") is not None and a["demo"]["vz_decolagem"] > 300:
        print("   pulo de 301,99:", a["id"], "estimada", round(a["vz_dec"], 2), "duck", a["demo"]["duck_amount"])

print("\n== altura de saída no ar (botão 1): referências candidatas")
def q(v, c=2):
    v = np.asarray([x for x in v if x is not None and np.isfinite(x)])
    return f"{np.median(v):.{c}f} [p5 {np.percentile(v,5):.{c}f} p25 {np.percentile(v,25):.{c}f} p75 {np.percentile(v,75):.{c}f} p95 {np.percentile(v,95):.{c}f}] n={v.size}" if v.size else "-"
for a in ar:
    if a.get("tau_dec") is None: continue
    p0 = np.array(a["demo"]["p0"]); z = np.asarray(a["entrada"]["z_janela"])
    base = p0[2] - 16 * a["u2"][2]
    a["M1"] = base - a["z_chao"]
    t01 = a["tau_dec"] + 0.1
    # parábola ajustada: z(τ) = c + b τ - 400 τ² ; recupero c pelo ponto da soltura
    b = a["vz_t"]; c = z[-2]
    a["M2"] = base - (c + b * t01 - 400 * t01 ** 2)
    a["M3"] = base - z[-2]
    a["M4"] = base - (z[-2] + a["v"][2] / 64)
    # horizontal: pés do evento + 1 tick de velocidade + 16 u'
    a["hz"] = np.linalg.norm(p0[:2] - (np.array(a["entrada"]["pes"][:2]) + a["v"][:2] / 64 + 16 * a["u2"][:2]))
for duck in (0, 1):
    s = [a for a in ar if a.get("M1") is not None and a["b_rec"] == 1.0 and (a["demo"]["duck_amount"] >= 1 if duck else a["demo"]["duck_amount"] == 0)]
    print(f" duck {duck}: M1 chão da decolagem {q([a['M1'] for a in s])}")
    print(f"         M2 parábola em decolagem+0,1s {q([a['M2'] for a in s])}")
    print(f"         M3 pés na soltura {q([a['M3'] for a in s])}")
    print(f"         horizontal (pés evento + v/64 + 16u') {q([a['hz'] for a in s], 3)}")

print("\n== horizontal no ar com os pés em decolagem + 0,1 s")
for a in ar:
    if a.get("tau_dec") is None: continue
    p0 = np.array(a["demo"]["p0"])
    x = np.array(a["entrada"]["pes"][:2]) + a["v"][:2] * (1 / 64 + a["tau_dec"] + 0.1)
    a["hz2"] = np.linalg.norm(p0[:2] - (x + 16 * a["u2"][:2]))
for duck in (0, 1):
    s = [a for a in ar if a.get("hz2") is not None and (a["demo"]["duck_amount"] >= 1 if duck else a["demo"]["duck_amount"] == 0)]
    print(f" duck {duck}: erro horizontal {q([a['hz2'] for a in s], 3)}")
    print("   piores:", [(a["id"], round(a["hz2"], 2), round(-a["tau_dec"] * 64, 2)) for a in sorted(s, key=lambda a: -a["hz2"])[:5]])

print("\n== horizontal no ar pela janela de x,y interpolada em decolagem + 0,1 s")
G2 = __import__("json").loads(__import__("gzip").decompress((Path(__file__).resolve().parents[1] / "tests/fixtures/gabarito_arremessos_match_23.json.gz").read_bytes()))
xy = {a["id"]: np.array(a["entrada"]["xy_janela"]) for a in G2["arremessos"]}
for a in ar:
    if a.get("tau_dec") is None: continue
    J = xy[a["id"]]; n = len(J)
    t_alvo = (n - 2) + (a["tau_dec"] + 0.1) * 64          # índice fracionário (n-2 = soltura)
    for nome, off in (("t_alvo", 0.0), ("t_alvo+1", 1.0), ("t_alvo-1", -1.0)):
        k = t_alvo + off
        i0 = int(np.floor(k)); f = k - i0
        if 0 <= i0 < n - 1:
            pxy = J[i0] * (1 - f) + J[i0 + 1] * f
            a["hz_" + nome] = float(np.linalg.norm(np.array(a["demo"]["p0"][:2]) - (pxy + 16 * a["u2"][:2])))
for nome in ("t_alvo-1", "t_alvo", "t_alvo+1"):
    s = [a for a in ar if a.get("hz_" + nome) is not None]
    print(f"  {nome}: {q([a['hz_' + nome] for a in s], 3)}")

print("\n== varredura do instante (índice da tabela = soltura + (τ_dec + 0,1 s)·64 + δ)")
def erro_h(a, k, modo):
    J = xy[a["id"]]; n = len(J)
    if modo == "interp":
        i0 = int(np.floor(k)); f = k - i0
        if not (0 <= i0 < n - 1): return None
        pxy = J[i0] * (1 - f) + J[i0 + 1] * f
    else:
        i = int(np.floor(k)) if modo == "floor" else int(np.ceil(k)) if modo == "ceil" else int(np.round(k))
        if not (0 <= i < n): return None
        pxy = J[i]
    return float(np.linalg.norm(np.array(a["demo"]["p0"][:2]) - (pxy + 16 * a["u2"][:2])))
mov = [a for a in ar if a.get("tau_dec") is not None and np.linalg.norm(a["v"][:2]) > 30]
print("  (só quem se movia na horizontal, n =", len(mov), ")")
for modo in ("interp", "floor", "ceil", "round"):
    for d in np.arange(-2.0, 0.51, 0.25):
        e = [erro_h(a, (len(xy[a['id']]) - 2) + (a["tau_dec"] + 0.1) * 64 + d, modo) for a in mov]
        e = [x for x in e if x is not None]
        print(f"  {modo:6s} δ {d:+.2f}: mediana {np.median(e):.3f} p95 {np.percentile(e,95):.3f} <1u {np.mean(np.array(e)<1):.1%}")

print("\n\n=========== AS CINCO METAS (inferência só com 'entrada') ===========")
VEL = {0.0: 202.5, 0.5: 438.7, 1.0: 675.0}
H_PE, H_AG = 63.31, 45.55
VZ_PULO = 298.868
for a in A:
    if a["ar"] and a.get("tau_dec") is not None:
        a["vz_usada"] = VZ_PULO - 80.0
    elif a["ar"]:
        a["vz_usada"] = a["v"][2]          # queda sem decolagem na janela: sem regra
    else:
        a["vz_usada"] = 0.0
    vj = np.array([a["v"][0], a["v"][1], a["vz_usada"]])
    a["rel"] = float(np.linalg.norm(a["vp"] - 1.25 * vj))
# ---- botão: curva de tolerância
print("\n== BOTÃO: tolerância x acerto x cobertura")
curva = []
for tol in (5, 10, 15, 20, 30, 40, 50, 60, 80, 100, 118):
    rot = []
    for a in A:
        c = min(VEL, key=lambda b: abs(VEL[b] - a["rel"]))
        rot.append(c if abs(VEL[c] - a["rel"]) <= tol else None)
    com = [(r, a["b_rec"]) for r, a in zip(rot, A) if r is not None]
    ac = np.mean([r == b for r, b in com]); cob = len(com) / len(A)
    curva.append((tol, ac, cob, len(com), sum(r == b for r, b in com)))
    print(f"  tol {tol:4d}: acerto {ac:.4f} ({sum(r == b for r, b in com)}/{len(com)}) cobertura {cob:.1%}")
tol_b = max(t for t, ac, *_ in curva if ac >= 0.99)
print("  tolerância escolhida (maior com acerto >= 99%):", tol_b)
for a in A:
    c = min(VEL, key=lambda b: abs(VEL[b] - a["rel"]))
    a["b"] = c if abs(VEL[c] - a["rel"]) <= tol_b else None
neut = [a for a in A if a["b"] is None]
print("  neutros:", [(a["id"], round(a["rel"], 1), a["b_rec"], "ar" if a["ar"] else "chão") for a in neut])
err = [a for a in A if a["b"] is not None and a["b"] != a["b_rec"]]
print("  errados:", [(a["id"], round(a["rel"], 1), a["b"], a["b_rec"]) for a in err])
# ---- no ar
ok_ar = sum(a["ar"] != a["demo"]["no_chao"] for a in A)
esc = [a for a in A if a["demo"]["no_chao"] and abs(a["v"][2]) >= 60]
print(f"\n== NO AR: {ok_ar}/{len(A)} = {ok_ar/len(A):.4f}; escada/rampa (|vz|>=60 no chão) corretos: {sum(not a['ar'] for a in esc)}/{len(esc)}")
# ---- postura
print("\n== POSTURA (duck 0 x 1)")
for a in A:
    pp = np.array(a["entrada"]["proj_pontos"]); p0e = pp[0]      # primeiro ponto = tick da soltura (100%)
    b = a["b"] if a["b"] is not None else 1.0
    if a["ar"] and a.get("tau_dec") is not None:
        z = np.asarray(a["entrada"]["z_janela"]); t01 = a["tau_dec"] + 0.1
        zref = z[-2] + a["vz_t"] * t01 - 400 * t01 ** 2
    else:
        zref = a["entrada"]["pes"][2] + a["v"][2] / 64
    a["H_est"] = p0e[2] - zref - 16 * a["u2"][2] - 12 * (b - 1)
    a["agachado"] = a["H_est"] < (H_PE + H_AG) / 2
for onde, f in (("chão", lambda a: a["demo"]["no_chao"]), ("ar", lambda a: not a["demo"]["no_chao"])):
    s = [a for a in A if f(a) and a["demo"]["duck_amount"] in (0.0, 1.0)]
    ok = sum(a["agachado"] == (a["demo"]["duck_amount"] == 1.0) for a in s)
    print(f"  {onde}: {ok}/{len(s)} = {ok/len(s):.4f} (parcial excluído: {sum(1 for a in A if f(a) and 0 < a['demo']['duck_amount'] < 1)})")
    for a in s:
        if a["agachado"] != (a["demo"]["duck_amount"] == 1.0):
            print(f"     erro {a['id']:17s} H_est {a['H_est']:6.2f} duck {a['demo']['duck_amount']} botão {a['b']} vz {a['v'][2]:6.1f} vh {np.linalg.norm(a['v'][:2]):4.0f}")
# ---- posição de saída
print("\n== POSIÇÃO DE SAÍDA calculada x m_vInitialPosition")
def p0_calc(a):
    b = a["b"] if a["b"] is not None else 1.0
    H = (H_AG if a["agachado"] else H_PE) + 12 * (b - 1)
    if a["ar"] and a.get("tau_dec") is not None:
        J = xy[a["id"]]; n = len(J); k = (n - 2) + (a["tau_dec"] + 0.1) * 64 - 0.5
        i0 = int(np.floor(k)); f = k - i0
        pxy = J[i0] * (1 - f) + J[i0 + 1] * f
        z = np.asarray(a["entrada"]["z_janela"]); t01 = a["tau_dec"] + 0.1
        zref = z[-2] + a["vz_t"] * t01 - 400 * t01 ** 2
        pes = np.array([pxy[0], pxy[1], zref])
    else:
        pes = np.array(a["entrada"]["pes"]) + a["v"] / 64
    return pes + np.array([0, 0, H]) + 16 * a["u2"]
e = np.array([np.linalg.norm(p0_calc(a) - np.array(a["demo"]["p0"])) for a in A])
print(f"  todos: mediana {np.median(e):.3f} p95 {np.percentile(e,95):.3f} <1u {np.mean(e<1):.1%}")
for onde, f in (("chão", lambda a: a["demo"]["no_chao"]), ("ar", lambda a: not a["demo"]["no_chao"])):
    ee = np.array([np.linalg.norm(p0_calc(a) - np.array(a["demo"]["p0"])) for a in A if f(a)])
    print(f"  {onde}: mediana {np.median(ee):.3f} p95 {np.percentile(ee,95):.3f} <1u {np.mean(ee<1):.1%} (n={ee.size})")
ev = np.array([np.linalg.norm((p0_calc(a) - np.array(a["demo"]["p0"]))[2]) for a in A])
eh = np.array([np.linalg.norm((p0_calc(a) - np.array(a["demo"]["p0"]))[:2]) for a in A])
print(f"  só vertical <1u {np.mean(ev<1):.1%} | só horizontal <1u {np.mean(eh<1):.1%}")
# ---- velocidade
print("\n== VELOCIDADE calculada x m_vInitialVelocity")
ev = []
for a in A:
    b = a["b"] if a["b"] is not None else a["b_rec"]
    vj = np.array([a["v"][0], a["v"][1], a["vz_usada"]])
    ev.append(np.linalg.norm(VEL[b] * a["u2"] + 1.25 * vj - np.array(a["demo"]["v0"])))
ev = np.array(ev)
print(f"  todos: mediana {np.median(ev):.3f} p95 {np.percentile(ev,95):.3f} <5 u/s {np.mean(ev<5):.1%}")
for onde, f in (("chão", lambda a: a["demo"]["no_chao"]), ("ar", lambda a: not a["demo"]["no_chao"])):
    m = np.array([f(a) for a in A])
    print(f"  {onde}: mediana {np.median(ev[m]):.3f} p95 {np.percentile(ev[m],95):.3f} <5 u/s {np.mean(ev[m]<5):.1%}")
print("  piores:", sorted([(round(float(x), 1), a["id"], "ar" if a["ar"] else "chão") for x, a in zip(ev, A)], reverse=True)[:8])

print("\n== decomposição do erro de velocidade no CHÃO")
ch = [a for a in A if a["demo"]["no_chao"] and a["b"] is not None]
for a in ch:
    v0 = np.array(a["demo"]["v0"]); vj = np.array([a["v"][0], a["v"][1], 0.0])
    w = v0 - 1.25 * vj
    a["S_med"] = np.linalg.norm(w)
    a["ang"] = np.degrees(np.arccos(np.clip(w @ a["u2"] / np.linalg.norm(w), -1, 1)))
    a["ev"] = np.linalg.norm(VEL[a["b"]] * a["u2"] + 1.25 * vj - v0)
    a["vh"] = np.linalg.norm(a["v"][:2])
    a["pw"] = -np.degrees(np.arcsin(w[2] / np.linalg.norm(w)))
print("  |v0 - 1,25 vj| - S(botão):", q([a["S_med"] - VEL[a["b"]] for a in ch]))
print("  ângulo entre (v0 - 1,25 vj) e u':", q([a["ang"] for a in ch], 3))
for lo, hi in ((0, 5), (5, 100), (100, 200), (200, 300)):
    s = [a for a in ch if lo <= a["vh"] < hi]
    if s: print(f"  vh [{lo},{hi}): erro {q([a['ev'] for a in s])} | ângulo {q([a['ang'] for a in s], 3)}")
for lo, hi in ((-90, -30), (-30, -10), (-10, 0), (0, 10), (10, 90)):
    s = [a for a in ch if lo <= a["entrada"]["pitch"] < hi and a["vh"] < 5]
    if s: print(f"  parado, pitch [{lo},{hi}): pitch lanç - previsto {q([a['pw'] - (-10 + a['entrada']['pitch']*(80/90 if a['entrada']['pitch'] < 0 else 100/90)) for a in s], 3)}")

print("\n== NO AR: velocidade horizontal na soltura x em decolagem + 0,1 s")
def vh_em(a, dt_ticks):
    J = xy[a["id"]]; n = len(J)
    k = (n - 2) + dt_ticks
    i0 = int(np.floor(k)); f = k - i0
    if not (1 <= i0 < n - 2): return None
    # velocidade por diferença central interpolada
    v0 = (J[i0 + 1] - J[i0 - 1]) * 32; v1 = (J[i0 + 2] - J[i0]) * 32
    return v0 * (1 - f) + v1 * f
for nome, fn in (("soltura", lambda a: a["v"][:2]), ("dec+0,1s", lambda a: vh_em(a, (a["tau_dec"] + 0.1) * 64)),
                 ("dec+0,1s-0,5t", lambda a: vh_em(a, (a["tau_dec"] + 0.1) * 64 - 0.5)), ("dec+0,1s-1t", lambda a: vh_em(a, (a["tau_dec"] + 0.1) * 64 - 1))):
    ee = []
    for a in A:
        if not (a["ar"] and a.get("tau_dec") is not None and a["b"] is not None): continue
        vh = fn(a)
        if vh is None: continue
        vj = np.array([vh[0], vh[1], a["vz_usada"]])
        ee.append(np.linalg.norm(VEL[a["b"]] * a["u2"] + 1.25 * vj - np.array(a["demo"]["v0"])))
    ee = np.array(ee)
    print(f"  {nome:14s}: mediana {np.median(ee):.3f} p95 {np.percentile(ee,95):.3f} <5 u/s {np.mean(ee<5):.1%} n={ee.size}")
for a in A:
    if a["id"] in ("match_23:16:81", "match_23:21:502", "match_23:6:158", "match_23:12:181", "match_23:6:505"):
        print("  ", a["id"], "ar" if a["ar"] else "chão", "n_ar", a["n_ar"], "ticks do pulo (gravado)", a["ticks_dec_rec"], "τ_dec estimado (ticks)", None if a.get("tau_dec") is None else round(-a["tau_dec"] * 64, 2), "vz usada", round(a["vz_usada"], 1), "botão", a["b"], a["b_rec"])

print("\n\n=========== FECHAMENTO (melhores variantes medidas) ===========")
ev, casos_v = [], []
for a in A:
    b = a["b"] if a["b"] is not None else a["b_rec"]
    vh = a["v"][:2]
    if a["ar"] and a.get("tau_dec") is not None:
        x = vh_em(a, (a["tau_dec"] + 0.1) * 64 - 0.5)
        if x is not None: vh = x
    vj = np.array([vh[0], vh[1], a["vz_usada"]])
    e = float(np.linalg.norm(VEL[b] * a["u2"] + 1.25 * vj - np.array(a["demo"]["v0"])))
    ev.append(e)
    if e >= 5: casos_v.append((round(e, 1), a["id"], "ar" if not a["demo"]["no_chao"] else "chão", a["b"], a["b_rec"]))
ev = np.array(ev)
print(f"VELOCIDADE: {np.sum(ev<5)}/{len(ev)} = {np.mean(ev<5):.1%} < 5 u/s | mediana {np.median(ev):.3f} p95 {np.percentile(ev,95):.3f}")
print("  casos >= 5 u/s:", len(casos_v)); [print("   ", c) for c in sorted(casos_v, reverse=True)]
ep, casos_p = [], []
for a in A:
    d = p0_calc(a) - np.array(a["demo"]["p0"])
    ep.append(np.linalg.norm(d))
    if np.linalg.norm(d) >= 1:
        casos_p.append((a["demo"]["no_chao"], abs(d[2]) >= 1, np.linalg.norm(d[:2]) >= 1))
ep = np.array(ep)
print(f"\nPOSIÇÃO: {np.sum(ep<1)}/{len(ep)} = {np.mean(ep<1):.1%} < 1 u | mediana {np.median(ep):.3f} p95 {np.percentile(ep,95):.3f}")
from collections import Counter
print("  falhas por (no chão, vertical>=1, horizontal>=1):", Counter(casos_p))
# vertical no chão, parado, em pé, botão 1: quanto da cauda
st = [a for a in A if a["demo"]["no_chao"] and a["b_rec"] == 1.0 and a["demo"]["duck_amount"] == 0 and np.linalg.norm(a["v"]) < 5]
dz = np.array([(p0_calc(a) - np.array(a["demo"]["p0"]))[2] for a in st])
print(f"  chão, parado, em pé, botão 1 (n={len(st)}): vertical |erro|<1 {np.mean(np.abs(dz)<1):.1%}; erro p5 {np.percentile(dz,5):.2f} mediana {np.median(dz):.2f} p95 {np.percentile(dz,95):.2f}")
