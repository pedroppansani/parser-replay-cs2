"""
Cópia de agente-pipeline/converte_agente.py do protótipo (v2-3, decisão 48). NÃO roda no build e NENHUM teste o importa
(importa onnxruntime, cv2 e rembg, fora do requirements). Roda à mão, só quando a fonte ou os parâmetros mudarem; os
parâmetros e o sha256 de cada saída ficam em dashboard/web/agentes.manifesto.json.

Agente em listras, ESTILO GATO, versão final do pipeline (rodada final, 2026-10-16). Sem profundidade: o Depth Anything saiu.
A versão anterior (com profundidade e a TRV1) está no commit 2962bdb do Iriun e congelada em prototipos/parser-cs2-v2/agentes/TRV1/.

    py -3.12 -B converte_agente.py <video> --nome TR --lado tr --corte-y 590 --ini 0.6 --fim 4.1 --ref 2.5 --fecho cruzado \
        --arma "260,305;380,355;420,420;470,385;575,440;625,462" --arma-neg "410,270;370,150;420,520" --maos "300,360;520,400" \
        --saida <pasta>

O que faz, nesta ordem:
 1. PRIVACIDADE: cada quadro é cortado em y < --corte-y NA MEMÓRIA logo depois de decodificado (cartão do jogador / texto da
    tela ficam abaixo). Nenhum quadro bruto vai para o disco.
 2. 30 fps (1 de cada 2 quadros do vídeo de 60 fps). Recorte do agente (rembg isnet-general-use), maior pedaço, mediana de 3.
 3. Arma: SlimSAM-77 por pontos no quadro de referência, acompanhada por ECC (rotação + translação). Mãos: SlimSAM por um ponto.
 4. Tom: bilateral + CLAHE (rosto 1,6x; pernas 1,75x com grade fina: a calça não vira massa preta) + equalização dentro do agente.
    Suavizado no TEMPO (gaussiana de 1,5 quadro = média efetiva de ~5) antes de virar tom; tons com histerese (não piscam).
 5. Loop: "cruzado" = loop de L segundos que fecha com transição cruzada nos últimos C segundos (o campo de tom e o recorte se
    misturam, antes de virar linha); "vai-e-volta" = a janela é tocada para a frente e para trás com aceleração e desaceleração
    suaves (cosseno), sem parada seca.
 6. Linhas retas, 4 tons da tinta (opacidade sobre o fundo), espessura por tom com mínimo em px de tela; buracos claros do rosto
    viram falhas limpas; arma inteira sempre no tom mais escuro (cada coluna da arma ganha a linha mais próxima: o cano não some
    entre duas linhas); mãos escurecidas onde pedido (--maos-escuras); NENHUMA linha fora da silhueta.
 7. Saída: agente-<nome>.js (segmentos com tom e espessura, sem fetch), quadro fixo em SVG, folha de prévia, GIF, medidas.
"""
from __future__ import annotations
import argparse, base64, gzip, json, math, os, sys, time
from pathlib import Path
sys.dont_write_bytecode = True
import numpy as np, cv2, imageio_ffmpeg, onnxruntime as ort
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage
from rembg import new_session, remove

ap = argparse.ArgumentParser()
ap.add_argument("video"); ap.add_argument("--nome", required=True); ap.add_argument("--lado", required=True, choices=["ct", "tr"])
ap.add_argument("--corte-y", type=int, required=True); ap.add_argument("--ini", type=float, required=True); ap.add_argument("--fim", type=float, required=True)
ap.add_argument("--ref", type=float, required=True); ap.add_argument("--fecho", choices=["cruzado", "vai-e-volta"], required=True)
ap.add_argument("--cruz", type=float, default=0.4); ap.add_argument("--arma", required=True); ap.add_argument("--arma-neg", default="")
ap.add_argument("--maos", default=""); ap.add_argument("--maos-escuras", action="store_true")
ap.add_argument("--linhas", type=int, default=77); ap.add_argument("--aspecto", type=float, default=0.95)
ap.add_argument("--lentes", default=""); ap.add_argument("--filtro", default=""); ap.add_argument("--lente-mais", type=int, default=0, help="px a mais em volta da elipse da lente (o SlimSAM pega só o vidro, não o aro)"); ap.add_argument("--cabeca", type=int, default=0, help="linhas da cabeça (de cima): lentes em falha, filtro em acento, contorno fechado")
ap.add_argument("--corpo-de", default="", help=".js já entregue: as linhas abaixo da cabeça saem dele, byte a byte")
ap.add_argument("--suave", type=float, default=1.5); ap.add_argument("--lento", type=float, default=1.15); ap.add_argument("--saida", required=True); ap.add_argument("--conferir", default="")
A = ap.parse_args()
# PRIVACIDADE (entrega-v2-goatdemo §6): o cartão do jogador fica abaixo do corte; TR em y < 590, CT-A em y < 545.
CORTE_MAXIMO_Y = {"tr": 590, "ct": 545}
if A.corte_y > CORTE_MAXIMO_Y[A.lado]:
    raise SystemExit(f"--corte-y {A.corte_y} passa do corte de privacidade do {A.lado.upper()} ({CORTE_MAXIMO_Y[A.lado]})")
OUT = Path(A.saida); OUT.mkdir(parents=True, exist_ok=True)
MOD = Path(os.path.expanduser("~/.cache/modelos-goat")); FPS = 30
pts = lambda s: [tuple(int(v) for v in p.split(",")) for p in s.split(";") if p.strip()]
log = []
def diz(*s):
    t = " ".join(str(x) for x in s); print(t, flush=True); log.append(t)

# ------------------------------------------------ 1-2. quadros (cortados na memória) e recorte do agente
extra = A.cruz if A.fecho == "cruzado" else 0.0
r = imageio_ffmpeg.read_frames(A.video); meta = next(r); w, h = meta["size"]; fps_v = meta["fps"]; passo_v = round(fps_v / FPS)
quadros, tempos = [], []
try:
    for n, buf in enumerate(r):
        t = n / fps_v
        if t > A.fim + extra + 1e-6: break
        if t < A.ini - 1e-6 or n % passo_v: continue
        quadros.append(np.frombuffer(buf, np.uint8).reshape(h, w, 3)[:A.corte_y].copy()); tempos.append(t)   # PRIVACIDADE
finally:
    r.close()
NQ = len(quadros); iref = int(np.argmin([abs(t - A.ref) for t in tempos]))
diz(f"[{A.nome}] {Path(A.video).name}: {tempos[0]:.2f}–{tempos[-1]:.2f} s, {NQ} quadros a {FPS} fps; corte de privacidade y < {A.corte_y}; referência {tempos[iref]:.2f} s")
ses = new_session("isnet-general-use"); alf = []
for q in quadros:
    m = np.asarray(remove(Image.fromarray(q), session=ses, only_mask=True), np.float32) / 255
    lab, nl = ndimage.label(m > 0.5)
    if nl > 1: m = m * ndimage.binary_dilation(lab == 1 + int(np.argmax(ndimage.sum(np.ones_like(m), lab, range(1, nl + 1)))), iterations=2)
    alf.append(m)
alf = np.stack(alf); alf = np.median(np.stack([np.roll(alf, 1, 0), alf, np.roll(alf, -1, 0)]), axis=0)
alf = np.stack([ndimage.grey_erosion(a, size=(3, 3)) for a in alf])

# ------------------------------------------------ 3. arma e mãos (SlimSAM-77)
MEAN, STD = np.array([.485, .456, .406], np.float32), np.array([.229, .224, .225], np.float32)
enc = ort.InferenceSession(str(MOD / "slimsam-77-uniform" / "vision_encoder.onnx"), providers=["CPUExecutionProvider"])
dec = ort.InferenceSession(str(MOD / "slimsam-77-uniform" / "prompt_encoder_mask_decoder.onnx"), providers=["CPUExecutionProvider"])
_emb = {}
def sam(i, pos, neg):
    q = quadros[i]; hh, ww = q.shape[:2]; s = 1024 / max(hh, ww); nh, nw = round(hh * s), round(ww * s)
    if i not in _emb:
        x = (cv2.resize(q, (nw, nh), interpolation=cv2.INTER_LINEAR).astype(np.float32) / 255 - MEAN) / STD
        pad = np.zeros((1024, 1024, 3), np.float32); pad[:nh, :nw] = x
        _emb[i] = enc.run(None, {"pixel_values": pad.transpose(2, 0, 1)[None]})
    emb, pemb = _emb[i]
    p = np.array([[a * s, b * s] for a, b in pos + neg], np.float32)[None, None]; l = np.array([1] * len(pos) + [0] * len(neg), np.int64)[None, None]
    iou, masks = dec.run(None, {"input_points": p, "input_labels": l, "image_embeddings": emb, "image_positional_embeddings": pemb})
    cands = []
    for k in range(3):
        mk = cv2.resize(masks[0, 0, k], (1024, 1024), interpolation=cv2.INTER_LINEAR)[:nh, :nw] > 0
        cobre = sum(bool(mk[int(b * s), int(a * s)]) for a, b in pos)
        cands.append((cobre, iou[0, 0, k] > 0.6, -mk.sum(), k))
    k = max(cands)[3]
    m = cv2.resize(masks[0, 0, k], (1024, 1024), interpolation=cv2.INTER_LINEAR)[:nh, :nw]
    return cv2.resize(m, (ww, hh), interpolation=cv2.INTER_LINEAR) > 0, float(iou[0, 0, k])

def acompanha(ref_m, dil=4):
    """leva a máscara do quadro de referência para os outros por ECC (rotação + translação do cinza dentro dela)"""
    cref = cv2.GaussianBlur(cv2.cvtColor(quadros[iref], cv2.COLOR_RGB2GRAY), (0, 0), 1.0).astype(np.float32) / 255
    mk = ndimage.binary_dilation(ref_m, iterations=dil).astype(np.uint8); out = []; Hh, Ww = ref_m.shape
    for i in range(NQ):
        if i == iref: out.append(ref_m.copy()); continue
        alvo = cv2.GaussianBlur(cv2.cvtColor(quadros[i], cv2.COLOR_RGB2GRAY), (0, 0), 1.0).astype(np.float32) / 255
        Wm = np.eye(2, 3, dtype=np.float32)
        try: _, Wm = cv2.findTransformECC(cref, alvo, Wm, cv2.MOTION_EUCLIDEAN, (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 200, 1e-5), mk, 5)
        except cv2.error: pass
        out.append(cv2.warpAffine(ref_m.astype(np.uint8), Wm, (Ww, Hh), flags=cv2.INTER_NEAREST) > 0)
    return out

ARMA, NEG, MAOS = pts(A.arma), pts(A.arma_neg), pts(A.maos)
# arma primeiro (as mãos entram como pontos negativos); fica todo pedaço que contém um ponto positivo (o cano passa por baixo da mão)
arma_ref, iou_a = sam(iref, ARMA, NEG + MAOS)
arma_ref &= alf[iref] > 0.3
arma_ref = ndimage.binary_closing(arma_ref, iterations=2)
lb, nb = ndimage.label(arma_ref)
manter = {int(lb[y_, x_]) for x_, y_ in ARMA if lb[y_, x_] > 0}
arma_ref = np.isin(lb, list(manter)) if manter else arma_ref
# mãos: um ponto em cada, sem nada da arma
maos_ref = np.zeros(quadros[0].shape[:2], bool)
for pm in MAOS:
    mm, _ = sam(iref, [pm], ARMA)
    mm &= ~ndimage.binary_dilation(arma_ref, iterations=1)
    lb2, nb2 = ndimage.label(mm)
    if nb2 and lb2[pm[1], pm[0]]: mm = lb2 == lb2[pm[1], pm[0]]
    if mm.sum() < 12000: maos_ref |= mm
armas = acompanha(arma_ref); maos = acompanha(maos_ref)
# cabeça (CT): lentes e filtro da máscara de gás. A forma vem do dado (SlimSAM por um ponto em cada peça; elipse ajustada ao contorno do
# SlimSAM, para a falha ficar redonda) e acompanha a cabeça quadro a quadro por ECC (a região da cabeça inteira, que tem textura).
LENTES, FILTRO = pts(A.lentes), pts(A.filtro)
def elipse_do_sam(pt, neg):
    mm, iou_ = sam(iref, [pt], neg + ARMA)
    lb_, nb_ = ndimage.label(mm)
    if not nb_ or not lb_[pt[1], pt[0]]: return np.zeros_like(mm)
    mm = lb_ == lb_[pt[1], pt[0]]
    cs, _ = cv2.findContours(mm.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE); c = max(cs, key=cv2.contourArea)
    out = np.zeros(mm.shape, np.uint8)
    if len(c) >= 5: cv2.ellipse(out, cv2.fitEllipse(c), 1, -1)
    else: out = mm.astype(np.uint8)
    diz(f"   peça em {pt}: SlimSAM IoU {iou_:.2f}, {int(mm.sum())} px, elipse {int(out.sum())} px")
    return out > 0
lente_ref = np.zeros_like(arma_ref); filtro_ref = np.zeros_like(arma_ref)
for k_, pt in enumerate(LENTES): lente_ref |= elipse_do_sam(pt, [q for j_, q in enumerate(LENTES) if j_ != k_] + FILTRO)
if A.lente_mais: lente_ref = ndimage.binary_dilation(lente_ref, iterations=A.lente_mais)
for pt in FILTRO: filtro_ref |= elipse_do_sam(pt, LENTES)
if A.lentes or A.filtro:
    regiao = ndimage.binary_dilation(lente_ref | filtro_ref, iterations=30)
    lentes_q = acompanha(lente_ref, 30); filtros_q = acompanha(filtro_ref, 30)
else:
    lentes_q = filtros_q = [np.zeros_like(arma_ref)] * NQ
diz(f"arma: SlimSAM-77 com {len(ARMA)} pontos no quadro de referência (IoU {iou_a:.2f}, {int(arma_ref.sum())} px), acompanhada por ECC; mãos: {int(maos_ref.sum())} px")
if A.conferir:
    Path(A.conferir).mkdir(parents=True, exist_ok=True)
    for i in sorted({0, iref, NQ - 1}):
        q = quadros[i].copy()
        for mk, cor in ((armas[i], (255, 0, 255)), (maos[i], (0, 255, 255)), (lentes_q[i], (255, 255, 0)), (filtros_q[i], (0, 255, 0))):
            cs, _ = cv2.findContours(mk.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE); cv2.drawContours(q, cs, -1, cor, 2)
        Image.fromarray(q).save(Path(A.conferir) / f"{A.nome}-arma-maos-{tempos[i]:.2f}s.png")   # já cortado acima do cartão/texto

# ------------------------------------------------ caixa comum 3/4
uni = (alf > 0.5).any(0); ys, xs = np.where(uni); y0, x0, x1 = ys.min(), xs.min(), xs.max() + 1; y1 = A.corte_y
folga = round(0.08 * (y1 - y0)); by0 = y0 - folga; H0 = y1 - by0; W0 = round(H0 * A.aspecto); bx0 = round((x0 + x1) / 2 - W0 / 2)
cabe = (x1 - x0) + 2 * folga <= W0
diz(f"caixa 3/4: agente {x1 - x0}x{y1 - y0} px, folga {folga} px, caixa {W0}x{H0} (aspecto {A.aspecto}) -> {'arma e corpo cabem' if cabe else 'NÃO CABE: aumentar o aspecto'}")
PAD = 800
def caixa(arr):
    a = np.pad(arr, [(PAD, PAD), (PAD, PAD)] + ([(0, 0)] if arr.ndim == 3 else []))
    return a[by0 + PAD:by0 + PAD + H0, bx0 + PAD:bx0 + PAD + W0]
topo = folga; alt_ag = y1 - y0

# ------------------------------------------------ 4. campo de tom por quadro (na grade das linhas), suavizado no tempo
L = A.linhas; GX = 240                                      # grade: L linhas x GX colunas (x em u8 no formato)
SUBY = 8                                                    # amostras por linha na vertical (para a arma e para a borda)
def campo(i):
    rgb = caixa(quadros[i]); a = caixa(alf[i]); cinza = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY); dentro = a > 0.5
    base = cinza.copy(); base[~dentro] = int(np.median(cinza[dentro]))
    g = cv2.bilateralFilter(base, 15, 90, 9)
    g8 = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(6, 6)).apply(g)
    c0, c1 = topo, topo + int(0.22 * alt_ag)
    g8[c0:c1] = cv2.createCLAHE(clipLimit=3.2, tileGridSize=(4, 4)).apply(g[c0:c1])                 # rosto
    p0 = topo + int(0.62 * alt_ag)
    g8[p0:] = cv2.createCLAHE(clipLimit=3.5, tileGridSize=(3, 6)).apply(g[p0:])                     # pernas: calça com contraste local
    gg = g8.astype(np.float32) / 255
    am = np.sort(gg[dentro]); esc = 1 - np.searchsorted(am, gg).astype(np.float32) / am.size
    E = cv2.resize(esc, (GX, L * SUBY), interpolation=cv2.INTER_AREA)
    Al = cv2.resize(a, (GX, L * SUBY), interpolation=cv2.INTER_AREA)
    Ar = cv2.resize(caixa(armas[i]).astype(np.float32), (GX, L * SUBY), interpolation=cv2.INTER_AREA)
    Mo = cv2.resize(caixa(maos[i]).astype(np.float32), (GX, L * SUBY), interpolation=cv2.INTER_AREA)
    Le = cv2.resize(caixa(lentes_q[i]).astype(np.float32), (GX, L * SUBY), interpolation=cv2.INTER_AREA)
    Fi = cv2.resize(caixa(filtros_q[i]).astype(np.float32), (GX, L * SUBY), interpolation=cv2.INTER_AREA)
    return E, Al, Ar, Mo, Le, Fi
t0 = time.time()
C = [campo(i) for i in range(NQ)]
E = np.stack([c[0] for c in C]); AL = np.stack([c[1] for c in C]); AR = np.stack([c[2] for c in C]); MO = np.stack([c[3] for c in C]); LE = np.stack([c[4] for c in C]); FI = np.stack([c[5] for c in C])
diz(f"campos de tom: {NQ} quadros em {time.time() - t0:.0f} s")

# ------------------------------------------------ 5. loop
def suaviza(X, ciclo):
    return ndimage.gaussian_filter1d(X, sigma=A.suave, axis=0, mode="wrap" if ciclo else "nearest")
if A.fecho == "cruzado":
    Cc = int(round(A.cruz * FPS)); cand = range(int(3.0 * FPS), NQ - Cc + 1)
    custo = {n_: float(np.abs(E[:Cc] - E[n_:n_ + Cc]).mean() + 2 * np.abs(AL[:Cc] - AL[n_:n_ + Cc]).mean() + 2 * np.abs(AR[:Cc] - AR[n_:n_ + Cc]).mean()) for n_ in cand}
    Nl = min(custo, key=custo.get)
    diz(f"comprimento do loop escolhido pela costura mais parecida entre 3,0 e {(NQ - Cc) / FPS:.2f} s: {Nl / FPS:.2f} s (custo {custo[Nl]:.4f}; pior {max(custo.values()):.4f})")
    def cruza(X):
        out = X[:Nl].copy()
        for k in range(Cc):
            wgt = 0.5 - 0.5 * math.cos(math.pi * k / Cc)              # 0 -> 1, suave
            out[k] = wgt * X[k] + (1 - wgt) * X[k + Nl]             # o começo vem do que segue o fim: fecha sem salto
        return out
    def sdf(m):
        m = m > 0.5
        return ndimage.distance_transform_edt(m) - ndimage.distance_transform_edt(~m)
    def cruza_mascara(X):
        # o contorno se move aos poucos (campo de distância com sinal), em vez de trocar de forma de uma vez no meio da transição
        out = X[:Nl].copy()
        for k in range(Cc):
            wgt = 0.5 - 0.5 * math.cos(math.pi * k / Cc)
            d_ = wgt * sdf(X[k]) + (1 - wgt) * sdf(X[k + Nl])
            out[k] = 1 / (1 + np.exp(-d_ * 2.0))
        return out
    E, MO = cruza(E), cruza(MO); AL, AR = cruza_mascara(AL), cruza_mascara(AR); LE, FI = cruza_mascara(LE), cruza_mascara(FI)
    E, AL = suaviza(E, True), suaviza(AL, True)
    ORDEM = list(range(Nl)); QUAD = Nl
    forma = f"loop de {Nl / FPS:.2f} s fechado com transição cruzada nos {Cc / FPS:.2f} s finais"
else:
    E, AL = suaviza(E, False), suaviza(AL, False)
    Nw = NQ; Tc = int(round(2 * (Nw - 1) * A.lento))                 # ciclo um pouco mais longo que o vai e volta puro (desacelera nas pontas)
    meia = Tc // 2
    pos = [(Nw - 1) * (0.5 - 0.5 * math.cos(math.pi * k / meia)) for k in range(meia + 1)]   # 0 -> Nw-1 com aceleração e desaceleração
    def amostra(X):
        out = []
        for p in pos:
            a_, b_ = int(math.floor(p)), min(Nw - 1, int(math.floor(p)) + 1); f = p - a_
            out.append((1 - f) * X[a_] + f * X[b_])
        return np.stack(out)
    E, AL, AR, MO, LE, FI = amostra(E), amostra(AL), amostra(AR), amostra(MO), amostra(LE), amostra(FI)
    QUAD = len(pos); ORDEM = list(range(QUAD)) + list(range(QUAD - 2, 0, -1))
    forma = f"vai-e-volta suave (cosseno) de uma janela de {(Nw - 1) / FPS:.2f} s: ciclo de {len(ORDEM) / FPS:.2f} s, {QUAD} quadros guardados"
diz("loop:", forma)

# ------------------------------------------------ 6. linhas: tom com histerese, falhas do rosto, arma inteira, sem nada fora da silhueta
TINTA = np.array([10, 10, 10]); BR = np.array([255, 255, 255])
OPAC = [0.60, 0.74, 0.88, 1.0]
TONS = [tuple(int(round(v)) for v in BR - o * (BR - TINTA)) for o in OPAC]
ESP = [0.42, 0.48, 0.56, 0.66, 0.0]            # espessura por tom (fração do passo); 4 = arma fina (só a mínima em px)
LIM = [0.30, 0.52, 0.74]                       # cortes de tom no campo "escuro" (0 claro .. 1 escuro)
HIST = 0.04
def niveis(Ef, prev):
    n = np.digitize(Ef, LIM)
    if prev is None: return n
    # histerese: só muda de tom se passar do corte com folga
    sobe = (n > prev) & (Ef < np.take(np.array(LIM + [9]), prev) + HIST)
    desce = (n < prev) & (Ef > np.take(np.array([-9] + LIM), prev) - HIST)
    return np.where(sobe | desce, prev, n)
segs_q = []; prev = None
AQ = 3 if A.fecho == "cruzado" else 0           # no loop cruzado, 3 quadros de aquecimento: a histerese fecha o ciclo sem salto
for kq, f in enumerate(list(range(QUAD - AQ, QUAD)) + list(range(QUAD))):
    Ef = E[f].reshape(L, SUBY, GX); Af = AL[f].reshape(L, SUBY, GX); Rf = AR[f].reshape(L, SUBY, GX); Mf = MO[f].reshape(L, SUBY, GX); Lf = LE[f].reshape(L, SUBY, GX); Ff = FI[f].reshape(L, SUBY, GX)
    e = Ef.mean(1); dentro = Af.mean(1) > 0.5
    dentro_lin = Af[:, 1:SUBY - 1].min(1) > 0.5                              # a linha só existe onde a máscara cobre a espessura dela
    dentro_lin = ndimage.binary_erosion(dentro_lin, structure=np.ones((1, 3)))   # e 1 coluna de folga dos lados (nada encosta para fora)
    if A.maos_escuras:                                                      # CT-A: luvas quase brancas -> tom escuro, preservando os dedos
        mao = Mf.mean(1) > 0.4
        e = np.where(mao, 0.62 + 0.38 * e, e)
    n = niveis(e, prev); prev = n
    if kq < AQ: continue
    # rosto: buracos claros (olhos e boca da balaclava, lentes) viram falhas limpas
    rosto = np.zeros_like(dentro); r0 = int(topo / H0 * L); r1 = int((topo + 0.22 * alt_ag) / H0 * L); rosto[r0:r1] = True
    falha = rosto & dentro & (e < 0.22)
    falha = ndimage.binary_opening(falha, structure=np.ones((1, 2))); falha = ndimage.binary_closing(falha, structure=np.ones((1, 3)))
    liga = dentro_lin & (e >= 0.06) & ~falha
    # arma: inteira, no tom mais escuro; cada coluna da arma liga a linha mais próxima do centro da arma naquela coluna
    arma_l = (Rf.max(1) > 0.25)
    col_arma = Rf > 0.25; OFF = np.zeros((L, GX), int)
    for x in np.where(col_arma.any(axis=(0, 1)))[0]:
        yy = np.where(col_arma[:, :, x].reshape(-1))[0]
        if yy.size == 0: continue
        grupos = np.split(yy, np.where(np.diff(yy) > 1)[0] + 1)
        for gr in grupos:
            rr_ = int(gr.mean() // SUBY); arma_l[rr_, x] = True
            OFF[rr_, x] = int(np.clip(round((gr.mean() - (rr_ * SUBY + SUBY / 2 - 0.5)) / SUBY * 16), -15, 15))   # a linha fina vai no centro real da arma
    ext = (Rf > 0.25).sum(1) / SUBY                                         # altura da arma dentro da faixa de cada linha
    grossa_ok = (Rf[:, SUBY // 2 - 2:SUBY // 2 + 3].min(1) > 0.25) | dentro_lin   # a linha grossa só onde a arma (ou o corpo) cobre a espessura dela
    liga |= arma_l; n = np.where(arma_l, np.where((ext < ESP[3]) | ~grossa_ok, 4, 3), n)   # 4 = escuro na espessura mínima (cano, massa, ponta)
    OFF = np.where(n == 4, OFF, 0); COD = n + 8 * (OFF + 16)                # byte do segmento: tom (3 bits) + deslocamento vertical (5 bits)
    # aparo: célula da arma só fica se a máscara (arma ou corpo) cobre a espessura dela naquela coluna
    cob = (Rf > 0.02) | (Af > 0.5)
    sub_c = np.clip((np.arange(L)[:, None] * SUBY + SUBY // 2 + np.round(OFF / 16 * SUBY)).astype(int) - np.arange(L)[:, None] * SUBY, 1, SUBY - 2)
    fina_ok = np.take_along_axis(cob, sub_c[:, None, :], 1)[:, 0] & np.take_along_axis(cob, (sub_c - 1)[:, None, :], 1)[:, 0] & np.take_along_axis(cob, (sub_c + 1)[:, None, :], 1)[:, 0]
    grossa_cob = cob[:, SUBY // 2 - 3:SUBY // 2 + 4].all(1)
    liga &= ~((n == 4) & ~fina_ok) & ~((n == 3) & arma_l & ~grossa_cob & ~dentro_lin)
    # sem nada fora da silhueta: o que não é arma e não está dentro sai; segmento menor que 3 colunas sai
    arma_l &= ndimage.binary_erosion(Rf.max(1) > 0.25, structure=np.ones((1, 3))) | dentro_lin
    liga &= (dentro_lin | arma_l)
    if A.cabeca:
        hr = A.cabeca
        lente = Lf.mean(1) > 0.5; filtro = (Ff.mean(1) > 0.5) & dentro_lin
        lente[hr:] = False; filtro[hr:] = False
        lente &= ndimage.binary_erosion(dentro_lin, structure=np.ones((1, 13)))    # as lentes nunca abrem o contorno da cabeça: 6 colunas de borda ficam acesas
        # contorno fechado: emenda falhas curtas (até 3 colunas) fora das lentes e tira manchas soltas (menos de 12 células)
        # o capacete é escuro no jogo: dentro da silhueta da cabeça a linha existe sempre (contorno fechado) e nunca é mais clara que o 2º tom
        cap = np.zeros_like(dentro_lin); cap[:hr] = dentro_lin[:hr] & ~arma_l[:hr]
        liga |= cap & ~lente
        COD = np.where(cap, np.maximum(n, 1) + 8 * 16, COD)
        borda = cap & ~ndimage.binary_erosion(cap, structure=np.ones((1, 9)))       # o contorno da cabeça no 3º tom: fecha o capacete
        COD = np.where(borda, np.maximum(n, 2) + 8 * 16, COD)
        fech = ndimage.binary_closing(liga, structure=np.ones((1, 4))) & dentro_lin & ~lente & ~falha
        liga[:hr] = fech[:hr]
        lb3, nb3 = ndimage.label(liga[:hr], structure=np.ones((3, 3)))
        for c3 in range(1, nb3 + 1):
            if (lb3 == c3).sum() < 12: liga[:hr][lb3 == c3] = False
        liga[:hr] &= ~lente[:hr]                                   # lentes: duas falhas claras e redondas
        liga[:hr] |= filtro[:hr]; COD = np.where(filtro, 3 + 8 * 16, COD)   # filtro: acento escuro curto (tom mais escuro)
    segs = []
    for rr in range(L):
        lin, x = [], 0
        while x < GX:
            if not liga[rr, x]: x += 1; continue
            x0_ = x; tn = COD[rr, x]
            while x < GX and liga[rr, x] and COD[rr, x] == tn: x += 1
            lin.append([x0_, x - x0_, int(tn)])
        # emenda falha de 1 coluna entre segmentos do mesmo tom; descarta < 3 colunas (exceto arma)
        jun = []
        for sg in lin:
            if jun and sg[0] - (jun[-1][0] + jun[-1][1]) <= 1 and sg[2] == jun[-1][2]: jun[-1][1] = sg[0] + sg[1] - jun[-1][0]
            else: jun.append(sg)
        segs.append([sg for sg in jun if sg[1] >= 3 or ((sg[2] & 7) >= 3 and arma_l[rr, sg[0]:sg[0] + sg[1]].any())])
    segs_q.append(segs)
if A.corpo_de:
    # as linhas abaixo da cabeça saem, byte a byte, do .js já entregue (mesmo vídeo, mesma ordem de quadros): corpo, arma, mãos, loop e tons não mudam
    ant = json.loads(Path(A.corpo_de).read_text(encoding="utf-8").split("]=", 1)[1].rsplit(";", 1)[0]); bb = base64.b64decode(ant["d"]); pp = 0
    assert ant["quadros"] == QUAD and ant["linhas"] == L, "o .js entregue não tem o mesmo número de quadros/linhas"
    for kq in range(QUAD):
        for rr in range(L):
            n_ = bb[pp]; pp += 1; fim_ = 0; lin_ = []
            for _ in range(n_): x_ = fim_ + bb[pp]; ln_ = bb[pp + 1]; lin_.append([x_, ln_, bb[pp + 2]]); fim_ = x_ + ln_; pp += 3
            if rr >= A.cabeca: segs_q[kq][rr] = lin_
nseg = sum(len(l) for q in segs_q for l in q)
diz(f"linhas: {L} retas, {GX} colunas; 4 tons {['#%02x%02x%02x' % t for t in TONS]} (tinta a {', '.join(f'{int(o * 100)}%' for o in OPAC)}); {nseg} segmentos em {QUAD} quadros ({nseg / QUAD:.0f}/quadro)")

# ------------------------------------------------ 7. formato, prévia, medidas
b = bytearray()
for q in segs_q:
    for l in q:
        b.append(len(l)); fim = 0
        for x0_, ln, tn in l: b += bytes([x0_ - fim, ln, tn]); fim = x0_ + ln
dados = {"l": GX, "linhas": L, "codigo": "byte3 = tom (bits 0-2; 4 = arma fina) + 8 x (deslocamento + 16), deslocamento em 1/16 do passo", "esp": ESP, "opac": OPAC, "fps": FPS, "quadros": QUAD, "ordem": "direta" if A.fecho == "cruzado" else "vai-e-volta",
         "aspecto": A.aspecto, "d": base64.b64encode(bytes(b)).decode()}
js = (f"/* agente {A.nome} em listras (estilo gato): gerado por agente-pipeline/converte_agente.py a partir da gravação do menu do CS2 (conteúdo do jogo da Valve,"
      f" uso sem fins comerciais). NÃO editar à mão. */\n(window.AGENTES=window.AGENTES||{{}})[{json.dumps(A.nome)}]={json.dumps(dados, separators=(',', ':'))};\n")
(OUT / f"agente-{A.nome.lower()}.js").write_text(js, encoding="utf-8")
gz = len(gzip.compress(js.encode(), 9))

def desenha(q, H, so_tom=None):
    """o MESMO desenho do tocador da landing: retângulos por segmento, tom e espessura do formato, mínimo de 1,2 px"""
    S = 4; W = round(H * A.aspecto); Ws, Hs = W * S, H * S
    im = Image.new("RGB", (Ws, Hs), (255, 255, 255)); dr = ImageDraw.Draw(im); passo = Hs / L; sx = Ws / GX
    for tn in range(5):
        if so_tom is not None and tn != so_tom: continue
        esp = max(ESP[tn] * passo, 1.2 * S)
        for rr, l in enumerate(q):
            yc = (rr + 0.5) * passo
            for x0_, ln, cod in l:
                t2, off = cod & 7, (cod >> 3) - 16; y_ = yc + off / 16 * passo
                if t2 == tn: dr.rectangle([x0_ * sx, y_ - esp / 2, (x0_ + ln) * sx - 1, y_ + esp / 2], fill=TONS[min(tn, 3)])
    return im.resize((W, H), Image.LANCZOS)

def mascara_px(f, H):
    W = round(H * A.aspecto); a = cv2.resize(AL[f], (W, H), interpolation=cv2.INTER_AREA) > 0.5
    ar = cv2.resize(AR[f], (W, H), interpolation=cv2.INTER_AREA) > 0.02     # qualquer pedaço da arma no pixel (o cano é mais fino que 1 px a 120)
    return a | ar
# medidas: (a) nada fora da silhueta dilatada em 1 px; (b) contraste da linha mais clara a 200 px; (c) arma fecha; (d) tinta que muda
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "validacao")); import paleta_original_copia as v1
fora = {}
for H in (120, 200, 320):
    im = np.asarray(desenha(segs_q[0], H).convert("L")); mk = ndimage.binary_dilation(mascara_px(0, H), iterations=1)
    fora[H] = int(((im < 180) & ~mk).sum())          # tinta de verdade (o antisserrilhado de meio pixel não conta)
    yy_, xx_ = np.where((im < 180) & ~mk)
    if yy_.size: diz(f"   fora a {H} px: {list(zip(xx_.tolist(), yy_.tolist()))[:8]} (perto da arma: {bool((ndimage.binary_dilation(cv2.resize(AR[0], (round(H * A.aspecto), H), interpolation=cv2.INTER_AREA) > 0.25, iterations=4)[yy_, xx_]).any())})")
cl = np.asarray(desenha(segs_q[0], 200, so_tom=0).convert("L"), np.float32); lb, nb = ndimage.label(cl < 250)
mins = np.array(ndimage.minimum(cl, lb, range(1, nb + 1))); tam = np.array(ndimage.sum(np.ones_like(cl), lb, range(1, nb + 1)))
pior = int(round(np.percentile(mins[tam >= 3], 95))); c200 = v1.contraste("#%02x%02x%02x" % (pior, pior, pior), "#ffffff")
fecha = {}
for H in (120, 200, 320):
    W = round(H * A.aspecto); im = np.asarray(desenha(segs_q[0], H).convert("L")) < 200
    ar = cv2.resize(AR[0], (W, H), interpolation=cv2.INTER_AREA) > 0.25
    yy, xx = np.where(ar); c = np.stack([xx, yy], 1).astype(np.float32); mu = c.mean(0); _, _, vt = np.linalg.svd(c - mu, full_matrices=False)
    proj = (c - mu) @ vt[0]; lo, hi = proj.min(), proj.max(); nb_ = max(10, int(hi - lo))
    tinta_ar = im & ndimage.binary_dilation(ar, iterations=1); yy2, xx2 = np.where(tinta_ar)
    pj = ((np.stack([xx2, yy2], 1).astype(np.float32) - mu) @ vt[0])
    cob = np.unique(np.clip(((pj - lo) / (hi - lo) * nb_).astype(int), 0, nb_ - 1)).size / nb_
    fecha[H] = cob
quadros320 = [desenha(segs_q[k], 320) for k in range(QUAD)]
arrs = [np.asarray(q.convert("L"), np.float32) / 255 for q in quadros320]
seq = [arrs[k] for k in ORDEM] + [arrs[ORDEM[0]]]
mud = [float(np.abs(seq[k + 1] - seq[k]).sum() / max(1e-6, (1 - seq[k]).sum())) for k in range(len(seq) - 1)]
diz(f"maiores mudanças de tinta (quadro da sequência: fração): {sorted([(k, round(m, 3)) for k, m in enumerate(mud)], key=lambda t: -t[1])[:5]}")
diz(f"nada fora da silhueta (pixels de tinta, mais escuros que #b4b4b4, fora da máscara dilatada em 1 px): 120 px {fora[120]} · 200 px {fora[200]} · 320 px {fora[320]} pixels")
diz(f"linha mais clara desenhada a 200 px: #{pior:02x}{pior:02x}{pior:02x} = {c200:.2f}:1 contra #ffffff -> {'PASSA' if c200 >= 3 else 'FALHA'} 3:1")
diz(f"arma fecha da coronha à ponta (fração do comprimento com tinta): 120 px {fecha[120]:.0%} · 200 px {fecha[200]:.0%} · 320 px {fecha[320]:.0%}")
diz(f"tinta que muda entre quadros seguidos (a 320 px, ciclo inteiro, inclusive a volta do loop): média {np.mean(mud):.1%}, máximo {np.max(mud):.1%}")
diz(f"peso: agente-{A.nome.lower()}.js {len(js)} bytes ({gz} gzip) · orçamento 120 KB: {'PASSA' if gz <= 120_000 else 'ESTOURA'}")
# GIF (30 fps, o ciclo inteiro) e quadro fixo em SVG (quadro 0)
pal = [q.convert("P", palette=Image.ADAPTIVE, colors=8) for q in [quadros320[k] for k in ORDEM]]
pal[0].save(OUT / f"agente-{A.nome.lower()}.gif", save_all=True, append_images=pal[1:], duration=33, loop=0, optimize=True)
svg = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {GX} {L * 10}" preserveAspectRatio="none">']
for tn in range(5):
    d_ = []
    for rr, l in enumerate(segs_q[0]):
        for x0_, ln, cod in l:
            t2, off = cod & 7, (cod >> 3) - 16
            if t2 == tn: hh_ = max(ESP[tn] * 10, 3.0); d_.append(f"M{x0_} {(rr + 0.5 + off / 16) * 10 - hh_ / 2:.1f}h{ln}v{hh_:.1f}h-{ln}z")
    svg.append(f'<path fill="currentColor" fill-opacity="{OPAC[min(tn, 3)]}" d="{"".join(d_)}"/>')
svg.append("</svg>"); (OUT / f"agente-{A.nome.lower()}-quadro.svg").write_text("".join(svg), encoding="utf-8")
for H in (120, 200, 320): desenha(segs_q[0], H).save(OUT / f"previa-{A.nome.lower()}-{H}.png")
med = dict(nome=A.nome, video=Path(A.video).name, janela=[A.ini, A.fim], ref=A.ref, fecho=A.fecho, forma=forma, quadros=QUAD, ciclo_s=len(ORDEM) / FPS,
           js=len(js), js_gzip=gz, fora_px=fora, contraste_200=round(c200, 2), arma_fecha=fecha, tinta_muda_media=round(float(np.mean(mud)), 4),
           tinta_muda_max=round(float(np.max(mud)), 4), linhas=L, colunas=GX, tons=OPAC, esp=ESP, corte_y=A.corte_y, aspecto=A.aspecto,
           arma_pts=A.arma, maos_pts=A.maos, maos_escuras=A.maos_escuras, arma_neg=A.arma_neg, suave=A.suave, lento=A.lento)
json.dump(med, open(OUT / f"medidas-{A.nome.lower()}.json", "w", encoding="utf-8"), indent=1, ensure_ascii=False)
(OUT / f"registro-{A.nome.lower()}.txt").write_text("\n".join(log) + "\n", encoding="utf-8")
