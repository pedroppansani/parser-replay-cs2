"""
Gera a tabela RADAR_AJUSTE (saturação s e brilho b por mapa) e os testes dos estados
da peça contra os radares. É o critério de aceite da fase B2b: a sessão do projeto roda
de novo e tem de obter os mesmos valores.

    py -3.12 -m scripts.design.gera_radar_ajuste             # radares locais (assets/radars/), extraídos numa pasta temporária
    py -3.12 -m scripts.design.gera_radar_ajuste <pasta>     # ou uma pasta com <mapa>_<andar>.png

Adaptação ao repositório: os radares vêm de `assets/radars/` (não são baixados do site) e a
tabela gerada é gravada em `notas/design/radar_ajuste.json`. Fonte: entrega-sala-de-demo §4.1.

Processamento (o mesmo do map_core.js, uma vez na carga):
    L = 0,2126 R + 0,7152 G + 0,0722 B   (sRGB 0-255)
    saída = clamp( b * (L + s * (cor - L)) )
Regra de escolha (decisão do Pedro, 2026-10-04), radar a radar, um par por mapa (o pior dos andares):
    varrer b de 1,00 a 0,50 e s de 1,00 a 0,00, em passos de 0,05; pegar o MAIOR b e, dentro dele,
    a MAIOR s em que TODOS os andares do mapa dão dE2000 >= 8,0 (pior das três visões) entre as
    cores dominantes do radar e TR, decisivo, molotov e HE. Sem par com b >= 0,50: o mapa sai "SEM PAR".
Amostragem: até 120.000 pixels do radar por andar, semente fixa 28 (decisão 28).
"""
import sys, glob, os, json
sys.dont_write_bytecode = True
import numpy as np
from pathlib import Path
from scripts.design import mede_radar as mr
from scripts.design._comum import DESIGN, extrai_radares
import metrics.paleta as v1   # contas de cor do projeto

PASSOS_B = [round(1.00 - 0.05 * i, 2) for i in range(11)]       # 1,00 .. 0,50
PASSOS_S = [round(1.00 - 0.05 * i, 2) for i in range(21)]       # 1,00 .. 0,00
UNICO = (0.40, 0.70)                                            # o valor único da rodada anterior, para comparar
FUNDO_RADAR = "#0f141b"
TOKENS = {"ct": "#4a90e8", "tr": "#e0a23a", "contorno": "#05080b", "halo": "#e8edf2"}

def L_hex(h):
    return mr.lum_wcag(np.array([[int(h[i:i + 2], 16) for i in (1, 3, 5)]], float))[0]

def contr(la, lb):
    return (np.maximum(la, lb) + 0.05) / (np.minimum(la, lb) + 0.05)

def piso(p):
    L = mr.lum_wcag(p); c50 = mr.hexa(p[np.argsort(L)[len(L) // 2]])
    return v1.contraste(c50, FUNDO_RADAR)

def anel_duplo(Lpx):
    """pior pixel do MAIOR dos dois contrastes (contorno escuro, halo claro)"""
    return np.maximum(contr(L_hex(TOKENS["contorno"]), Lpx), contr(L_hex(TOKENS["halo"]), Lpx)).min()

def estados(p):
    """Pior pixel de cada estado da peça, só com a cor do lado (antes) e com o anel duplo (depois)."""
    Lpx = mr.lum_wcag(p); out = {}
    for lado in ("ct", "tr"):
        cor = np.array([int(TOKENS[lado][i:i + 2], 16) for i in (1, 3, 5)], float)
        # fantasma: traço tracejado na cor do lado, sem preenchimento, opaco
        out[f"fantasma {lado}"] = contr(L_hex(TOKENS[lado]), Lpx).min()
        # morta: ✕ na cor do lado a 60% (mistura com o pixel do radar)
        mist = mr.lum_wcag(0.6 * cor[None, :] + 0.4 * p)
        out[f"morta {lado}"] = contr(mist, Lpx).min()
        # outro andar: anel vazado e ▲/▼ na cor do lado a 50% (globalAlpha 0,5 do map_core)
        mist5 = mr.lum_wcag(0.5 * cor[None, :] + 0.5 * p)
        out[f"outro andar {lado}"] = contr(mist5, Lpx).min()
    return out

def main():
    pasta = sys.argv[1] if len(sys.argv) > 1 else str(extrai_radares())
    andares = {}
    for arq in sorted(glob.glob(os.path.join(pasta, "*.png"))):
        nome = os.path.basename(arq)[:-4]; mapa = nome.rsplit("_", 1)[0]
        rgb = mr.carrega(arq)
        if len(rgb) > 120000:
            rgb = rgb[np.random.default_rng(28).choice(len(rgb), 120000, replace=False)]
        andares.setdefault(mapa, []).append((nome, rgb, mr.marcadores(rgb)))

    def pior_de(mapa, s, b):
        return min(mr.pior_de(mr.dominantes(mr.processa(rgb, s, b), g))[0] for _, rgb, g in andares[mapa])

    ajuste, linhas = {}, []
    for mapa in andares:
        par = None
        for b in PASSOS_B:
            for s in PASSOS_S:
                if pior_de(mapa, s, b) >= 8.0:
                    par = (s, b); break
            if par: break
        ajuste[mapa] = par
        for nome, rgb, g in andares[mapa]:
            orig = mr.processa(rgb, 1.0, 1.0)
            d0 = mr.pior_de(mr.dominantes(orig, g))[0]
            un = mr.processa(rgb, *UNICO)
            if par:
                p = mr.processa(rgb, *par); d1 = mr.pior_de(mr.dominantes(p, g))[0]
                linhas.append((mapa, nome, par, d0, d1, piso(orig), piso(un), piso(p), anel_duplo(mr.lum_wcag(p)), estados(p)))
            else:
                linhas.append((mapa, nome, None, d0, None, piso(orig), piso(un), None, None, None))

    print("== RADAR_AJUSTE (um par por mapa; maior b, depois maior s; passos de 0,05; b >= 0,50) ==\n")
    print(f"{'mapa':<9} {'andar':<11} {'s':>5} {'b':>5}  {'pior dE orig -> escolhido':>26}  {'piso x fundo: orig -> 0,40/0,70 -> par':>40}  {'anel duplo':>10}")
    for mapa, nome, par, d0, d1, p0, pu, p1, an, _ in linhas:
        if par:
            print(f"{mapa:<9} {nome:<11} {par[0]:5.2f} {par[1]:5.2f}  {d0:11.1f} -> {d1:5.1f}{'':8}  {p0:14.2f} -> {pu:5.2f} -> {p1:5.2f}{'':9}  {an:10.2f}")
        else:
            print(f"{mapa:<9} {nome:<11}   SEM PAR com b >= 0,50   (dE original {d0:.1f})")
    sem = [m for m, p in ajuste.items() if p is None]
    if sem:
        print("\nPARAR: sem par com brilho >= 0,50 em:", ", ".join(sem)); return 1
    padrao = (min(p[0] for p in ajuste.values()), min(p[1] for p in ajuste.values()))
    print(f"\npar padrão para mapa sem entrada (menor s e menor b da tabela): s {padrao[0]:.2f}, b {padrao[1]:.2f}")

    print("\n== Estados da peça: pior pixel do radar (com o par do mapa) ==")
    print("antes = só a cor do lado (como o map_core desenha hoje); depois = com o anel duplo tracejado/cheio (pior pixel do maior dos dois anéis)\n")
    chaves = list(linhas[0][9].keys())
    print(f"{'andar':<11} " + " ".join(f"{k:>16}" for k in chaves) + f"  {'anel duplo':>10}")
    for mapa, nome, par, d0, d1, p0, pu, p1, an, est in linhas:
        print(f"{nome:<11} " + " ".join(f"{est[k]:16.2f}" for k in chaves) + f"  {an:10.2f}")
    print("\nconstante para o map_core.js:")
    print("RADAR_AJUSTE = " + json.dumps({m: [p[0], p[1]] for m, p in ajuste.items()}, separators=(", ", ": ")) + ";")
    print(f"RADAR_AJUSTE_PADRAO = [{padrao[0]}, {padrao[1]}];")
    json.dump({"ajuste": {m: list(p) for m, p in ajuste.items()}, "padrao": list(padrao)},
              open(DESIGN / "radar_ajuste.json", "w"), indent=1)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
