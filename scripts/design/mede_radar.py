"""
Mede a dessaturação do radar, mapa a mapa (resposta 1 do fechamento, 2026-10-04).

    py -3.12 -m scripts.design.extrai_radares <pasta>      # PNG dos radares locais (assets/radars)
    py -3.12 -m scripts.design.mede_radar <pasta>

Processamento medido (é o que o map_core.js faz UMA vez, num canvas fora da tela):
    L = 0,2126 R + 0,7152 G + 0,0722 B        (valores sRGB 0-255, por pixel)
    saída = clamp( b * (L + s * (cor - L)) )
s = saturação (1 = original, 0 = cinza); b = brilho (1 = original).

Para cada mapa e cada s:
  - cores dominantes do radar: caixas de 16 níveis por canal com >= 1% dos pixels
    do radar, MAIS os marcadores coloridos do asset (pixels com croma Lab > 30 no
    original: as caixas laranja e verdes), agrupados por matiz;
  - dE2000 de cada cor dominante contra TR, decisivo, molotov e HE, na PIOR das
    três visões (normal, protanopia, deuteranopia) -- critério >= 8,0;
  - contraste de cada marca contra o percentil 95 de luminância do radar -- critério >= 3:1.
"""
import sys, glob, os, colorsys
sys.dont_write_bytecode = True
import numpy as np
from PIL import Image
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
import metrics.paleta as v1  # contas de cor do projeto (as mesmas da cópia usada no design)

ALVOS = {"tr": "#e0a23a", "decisivo": "#2fae7c", "molotov": "#d65d00", "he": "#ff4da6"}
MARCAS = {"ct": "#4a90e8", "tr": "#e0a23a", "smoke": "#d1d9e0", "flash": "#f9f5b8", "he": "#ff4da6",
          "molotov": "#d65d00", "aviso": "#ffea3d", "foco": "#ffffff", "contorno": "#05080b"}
SS = [1.0, 0.9, 0.8, 0.7, 0.6, 0.5, 0.4, 0.35, 0.3, 0.2, 0.1, 0.0]

def hexa(c): return "#%02x%02x%02x" % tuple(int(round(x)) for x in c)
def lab3(h): return [v1.rgb_para_lab(v1.hex_para_rgb(h))] + [v1.rgb_para_lab(v1.simula_dicromacia(h, t)) for t in v1.DICROMACIAS]
LA = {k: lab3(v) for k, v in ALVOS.items()}

def processa(rgb, s, b=1.0):
    L = rgb @ np.array([0.2126, 0.7152, 0.0722])
    return np.clip(b * (L[:, None] + s * (rgb - L[:, None])), 0, 255)

def lum_wcag(rgb):
    c = rgb / 255.0
    lin = np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
    return lin @ np.array([0.2126, 0.7152, 0.0722])

def carrega(arq):
    im = np.asarray(Image.open(arq).convert("RGBA")).astype(float)
    m = im[..., 3] > 128
    return im[..., :3][m]

def marcadores(rgb):
    """Índices dos pixels coloridos do asset (croma Lab > 30), por grupo de matiz."""
    amostra = rgb
    hsv = np.array([colorsys.rgb_to_hsv(*(p / 255)) for p in amostra])
    croma = hsv[:, 1] * hsv[:, 2]
    forte = croma > 0.30
    grupos = {"laranja (bomb)": forte & ((hsv[:, 0] < 0.11) | (hsv[:, 0] > 0.95)),
              "verde (spawn)": forte & (hsv[:, 0] > 0.20) & (hsv[:, 0] < 0.45)}
    return {k: g for k, g in grupos.items() if g.sum() >= 50}

def dominantes(rgbp, grupos):
    q = (rgbp // 16).astype(int)
    chave = q[:, 0] * 256 + q[:, 1] * 16 + q[:, 2]
    vals, cont = np.unique(chave, return_counts=True)
    cores = []
    for v, c in zip(vals, cont):
        if c / len(rgbp) >= 0.01:
            cores.append(("dom", rgbp[chave == v].mean(axis=0)))
    for k, g in grupos.items():
        cores.append((k, rgbp[g].mean(axis=0)))
    return cores

def pior_de(cores):
    pior = (99, "")
    for nome, c in cores:
        lc = lab3(hexa(c))
        for a, la in LA.items():
            d = min(v1.delta_e_2000(lc[i], la[i]) for i in range(3))
            if d < pior[0]: pior = (d, f"{nome} {hexa(c)} x {a}")
    return pior

def main():
    pasta = sys.argv[1] if len(sys.argv) > 1 else "radares"
    arqs = sorted(glob.glob(os.path.join(pasta, "*.png")))
    print("criterio: dE (pior visao) >= 8,0 entre cores dominantes do radar e TR/decisivo/molotov/HE; "
          "marca >= 3:1 contra o P95 de luminancia do radar\n")
    resumo = {}
    for arq in arqs:
        nome = os.path.basename(arq)[:-4]
        rgb = carrega(arq)
        if len(rgb) > 120000: rgb = rgb[np.random.default_rng(28).choice(len(rgb), 120000, replace=False)]  # semente fixa
        grupos = marcadores(rgb)
        print(f"== {nome} ({len(rgb)} px amostrados; marcadores: {', '.join(f'{k} {int(g.sum())} px' for k, g in grupos.items()) or 'nenhum'})")
        print(f"   {'s':>5}  {'pior dE':>8}  {'par':<44} {'P95':>8}  marcas abaixo de 3:1 contra o P95")
        linhas = []
        for s in SS:
            p = processa(rgb, s)
            d, par = pior_de(dominantes(p, grupos))
            L = lum_wcag(p); i95 = np.argsort(L)[int(0.95 * (len(L) - 1))]; c95 = hexa(p[i95])
            falham = [f"{k} {v1.contraste(h, c95):.2f}" for k, h in MARCAS.items() if k != "contorno" and v1.contraste(h, c95) < 3]
            cont = v1.contraste(MARCAS["contorno"], c95)
            linhas.append((s, d, cont, falham))
            print(f"   {s:5.2f}  {d:8.1f}  {par:<44} {c95:>8}  {'; '.join(falham) or '-'}   | contorno x P95 {cont:.2f}")
        ok = [s for s, d, c, f in linhas if d >= 8.0]
        resumo[nome] = (max(ok) if ok else None, linhas)
        print()
    print("== Resumo: maior s (menor dessaturação) com dE >= 8,0, por radar ==")
    for n, (s, _) in resumo.items(): print(f"   {n:<12} {s}")
    valido = [s for s, _ in resumo.values() if s is not None]
    print("   valor único que passa em todos:", min(valido) if len(valido) == len(resumo) else "nenhum")

if __name__ == "__main__":
    main()
