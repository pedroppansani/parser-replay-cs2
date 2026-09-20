"""
Validador da paleta dos gráficos: ΔE2000 entre todos os pares, em visão normal
e em daltonismo, mais o contraste no fundo branco.

    py -3.12 -m scripts.valida_paleta                     # a paleta em uso
    py -3.12 -m scripts.valida_paleta "#0b6b4a" "#4a3aa7"  # compara candidatos

POR QUE EXISTE
--------------
Cor de gráfico é decisão de leitura, não de gosto, e o olho de quem escolhe não
enxerga o que um daltônico enxerga. A decisão 10 do CLAUDE.md já foi revista uma
vez por causa disso: o registro dizia que "esmeralda" estava reprovada, quando o
reprovado era o esmeralda CLARO -- o defeito era luminância, não matiz, e a
diferença só apareceu porque os números foram refeitos.

CRITÉRIOS (os mesmos da decisão 10):
  - pior par em dicromacia: ΔE2000 >= DELTA_E_MINIMO_DALTONICO
  - contraste da cor no branco: >= CONTRASTE_MINIMO (WCAG para elemento gráfico)

LIMITE DO MODELO, e ele importa: a simulação de dicromacia é Viénot, Brettel e
Mollon (1999), em LMS. Ela APROXIMA protanopia e deuteranopia; não cobre
tritanopia nem visão anômala (protanomalia, deuteranomalia), que são mais
comuns que a dicromacia completa. Passar aqui é piso, não certificado.
"""
from __future__ import annotations

import itertools
import math
import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
TEMPLATE = RAIZ / "dashboard" / "web" / "template.html"

# Alvos da decisão 10. Não são deste script: são do projeto.
DELTA_E_MINIMO_DALTONICO = 8.0
CONTRASTE_MINIMO = 3.0

# Viénot, Brettel e Mollon (1999): RGB linear -> LMS, projeção do eixo que o
# cone ausente não distingue, e volta.
RGB_PARA_LMS = [[17.8824, 43.5161, 4.11935],
                [3.45565, 27.1554, 3.86714],
                [0.0299566, 0.184309, 1.46709]]
LMS_PARA_RGB = [[0.0809445, -0.130504, 0.116721],
                [-0.0102485, 0.0540194, -0.113615],
                [-0.000365294, -0.00412163, 0.693513]]
DICROMACIAS = {
    "protanopia": [[0, 2.02344, -2.52581], [0, 1, 0], [0, 0, 1]],
    "deuteranopia": [[1, 0, 0], [0.494207, 0, 1.24827], [0, 0, 1]],
}


# --- Cor ---------------------------------------------------------------------

def hex_para_rgb(cor: str) -> tuple[float, float, float]:
    h = cor.lstrip("#")
    return tuple(int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))  # type: ignore[return-value]


def _linear(c: float) -> float:
    """sRGB -> linear. A conta de luz acontece em linear; em sRGB dá errado."""
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def _srgb(c: float) -> float:
    return 12.92 * c if c <= 0.0031308 else 1.055 * c ** (1 / 2.4) - 0.055


def luminancia(rgb) -> float:
    r, g, b = (_linear(c) for c in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contraste(a: str, b: str) -> float:
    """Razão de contraste WCAG entre duas cores."""
    la, lb = luminancia(hex_para_rgb(a)), luminancia(hex_para_rgb(b))
    return (max(la, lb) + 0.05) / (min(la, lb) + 0.05)


def rgb_para_lab(rgb) -> tuple[float, float, float]:
    r, g, b = (_linear(c) for c in rgb)
    x = (r * 0.4124 + g * 0.3576 + b * 0.1805) / 0.95047
    y = r * 0.2126 + g * 0.7152 + b * 0.0722
    z = (r * 0.0193 + g * 0.1192 + b * 0.9505) / 1.08883
    f = lambda t: t ** (1 / 3) if t > 0.008856 else 7.787 * t + 16 / 116  # noqa: E731
    fx, fy, fz = f(x), f(y), f(z)
    return (116 * fy - 16, 500 * (fx - fy), 200 * (fy - fz))


def delta_e_2000(lab1, lab2) -> float:
    """CIEDE2000. Distância perceptual: ~1 é o limiar do que o olho separa."""
    l1, a1, b1 = lab1
    l2, a2, b2 = lab2
    c1, c2 = math.hypot(a1, b1), math.hypot(a2, b2)
    cb = (c1 + c2) / 2
    g = 0.5 * (1 - math.sqrt(cb ** 7 / (cb ** 7 + 25 ** 7))) if cb else 0.5
    a1p, a2p = (1 + g) * a1, (1 + g) * a2
    c1p, c2p = math.hypot(a1p, b1), math.hypot(a2p, b2)
    h1p = math.degrees(math.atan2(b1, a1p)) % 360
    h2p = math.degrees(math.atan2(b2, a2p)) % 360
    dlp, dcp = l2 - l1, c2p - c1p
    dhp = 0 if c1p * c2p == 0 else ((h2p - h1p + 180) % 360) - 180
    dHp = 2 * math.sqrt(c1p * c2p) * math.sin(math.radians(dhp) / 2)
    lbp, cbp = (l1 + l2) / 2, (c1p + c2p) / 2
    if c1p * c2p == 0:
        hbp = h1p + h2p
    else:
        hbp = ((h1p + h2p + 360) / 2) if abs(h1p - h2p) > 180 else (h1p + h2p) / 2
    t = (1 - 0.17 * math.cos(math.radians(hbp - 30))
         + 0.24 * math.cos(math.radians(2 * hbp))
         + 0.32 * math.cos(math.radians(3 * hbp + 6))
         - 0.20 * math.cos(math.radians(4 * hbp - 63)))
    sl = 1 + 0.015 * (lbp - 50) ** 2 / math.sqrt(20 + (lbp - 50) ** 2)
    sc, sh = 1 + 0.045 * cbp, 1 + 0.015 * cbp * t
    rt = (-2 * math.sqrt(cbp ** 7 / (cbp ** 7 + 25 ** 7))
          * math.sin(math.radians(60 * math.exp(-(((hbp - 275) / 25) ** 2)))))
    return math.sqrt((dlp / sl) ** 2 + (dcp / sc) ** 2 + (dHp / sh) ** 2
                     + rt * (dcp / sc) * (dHp / sh))


def _multiplica(m, v):
    return [sum(m[i][j] * v[j] for j in range(3)) for i in range(3)]


def simula_dicromacia(cor: str, tipo: str):
    """Como a cor aparece para quem tem protanopia ou deuteranopia."""
    rgb = [_linear(c) for c in hex_para_rgb(cor)]
    fora = _multiplica(LMS_PARA_RGB, _multiplica(DICROMACIAS[tipo],
                                                 _multiplica(RGB_PARA_LMS, rgb)))
    return tuple(min(1.0, max(0.0, _srgb(c))) for c in fora)


# --- Avaliação ---------------------------------------------------------------

def paleta_em_uso() -> dict[str, str]:
    """Lê as cores dos gráficos do próprio template.

    O script nunca valida uma paleta diferente da que está no ar -- paleta
    copiada à mão para dentro do validador é o jeito clássico de aprovar uma
    cor que a página não usa.
    """
    texto = TEMPLATE.read_text(encoding="utf-8")
    cores: dict[str, str] = {}
    for var, rotulo in (("ct", "A_azul"), ("t", "B_laranja"), ("dec", "decisivo")):
        m = re.search(rf"^\s*--{var}:\s*(#[0-9a-fA-F]{{6}});", texto, re.M)
        if m:
            cores[rotulo] = m.group(1)
    return cores


def avalia(rotulo: str, cores: dict[str, str], cor_avaliada: str) -> bool:
    """Imprime a linha de uma paleta e devolve se ela passa nos dois critérios."""
    lab = {k: rgb_para_lab(hex_para_rgb(v)) for k, v in cores.items()}
    pares = list(itertools.combinations(cores, 2))
    pior_normal = min((delta_e_2000(lab[a], lab[b]), f"{a} x {b}") for a, b in pares)

    piores = []
    for tipo in DICROMACIAS:
        labs = {k: rgb_para_lab(simula_dicromacia(v, tipo)) for k, v in cores.items()}
        piores.append(min((delta_e_2000(labs[a], labs[b]), f"{a} x {b} ({tipo})")
                          for a, b in pares))
    dalt, par_dalt = min(piores)

    razao = contraste(cor_avaliada, "#ffffff")
    passa = dalt >= DELTA_E_MINIMO_DALTONICO and razao >= CONTRASTE_MINIMO
    print(f"{rotulo:<12} {cor_avaliada:<9} "
          f"dE normal {pior_normal[0]:>5.1f} [{pior_normal[1]}]  "
          f"dE daltonico {dalt:>5.1f} [{par_dalt}]  "
          f"contraste {razao:>4.2f}:1  {'PASSA' if passa else 'FALHA'}")
    return passa


def main() -> None:
    base = paleta_em_uso()
    print("paleta em uso (lida de "
          f"{TEMPLATE.relative_to(RAIZ).as_posix()}): "
          + ", ".join(f"{k} {v}" for k, v in base.items()))
    print(f"criterios: dE daltonico >= {DELTA_E_MINIMO_DALTONICO}, "
          f"contraste no branco >= {CONTRASTE_MINIMO}:1")
    print()

    candidatos = sys.argv[1:]
    if not candidatos:
        avalia("em uso", base, base["decisivo"])
        return
    # candidato substitui só a cor do round decisivo; as dos times são fixas
    fixas = {k: v for k, v in base.items() if k != "decisivo"}
    for cor in candidatos:
        avalia("candidato", {**fixas, "decisivo": cor}, cor)


if __name__ == "__main__":
    main()
