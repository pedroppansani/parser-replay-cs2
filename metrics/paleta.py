"""
Validador da paleta (versão 2, direção visual "Sala de demo", decisão 44): ΔE2000 entre as cores
que aparecem juntas, em visão normal e em daltonismo, e o contraste de cada cor contra os fundos
do tema onde ela aparece.

    py -3.12 -m metrics.paleta                     # a paleta em uso (dashboard/web/tokens.css)
    py -3.12 -m metrics.paleta "#2fae7c" "#4a3aa7"  # candidatos para a cor do round decisivo

POR QUE EXISTE
--------------
Cor de gráfico é decisão de leitura, não de gosto, e o olho de quem escolhe não
enxerga o que um daltônico enxerga. A decisão 10 do CLAUDE.md já foi revista uma
vez por causa disso: o registro dizia que "esmeralda" estava reprovada, quando o
reprovado era o esmeralda CLARO -- o defeito era luminância, não matiz, e a
diferença só apareceu porque os números foram refeitos.

CRITÉRIOS (entrega-sala-de-demo §9; as contas de cor não mudaram, só o que é medido):
  - contraste contra os FUNDOS do tema (FUNDOS), cada cor só onde aparece (PALETA):
    >= 4,5:1 para cor de TEXTO e >= 3:1 para cor de MARCA (peça, ícone, barra, borda de
    controle, foco); texto escuro sobre cor sólida entra como texto
  - daltonismo, por GRUPO de cores que aparecem juntas (GRUPOS): pior par em dicromacia
    com ΔE2000 >= DELTA_E_MINIMO_DALTONICO
  - os pares nomeados (PARES_NOMEADOS) sempre impressos, nas três visões

A paleta é LIDA do arquivo de tokens (nunca copiada à mão para cá): validar uma paleta diferente
da que está no ar é o jeito clássico de aprovar uma cor que a página não usa. A saída com os
tokens atuais está fixada em tests/fixtures/paleta_v2_saida.txt (a da §9.2 do documento).

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
TOKENS = RAIZ / "dashboard" / "web" / "tokens.css"

# Alvos da decisão 10. Não são deste script: são do projeto.
DELTA_E_MINIMO_DALTONICO = 8.0
# Contraste mínimo por papel da cor (WCAG 1.4.3 e 1.4.11; fonte: entrega-sala-de-demo §9.1).
LIMIAR = {"texto": 4.5, "marca": 3.0}

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

# Fundos do tema: token -> onde aparece (fonte: entrega-sala-de-demo §9.1).
FUNDOS = {
    "fundo": "página",
    "superficie": "cards e painéis",
    "superficie-2": "elevado: hover, aba ativa, popover, aviso",
    "radar": "canvas do mapa (peças e granadas)",
    "tl-fundo": "linha do tempo (replay e prancheta)",
}

# token, papel, fundos onde aparece. Texto escuro sobre cor sólida (ficha, botão, "venceu")
# entra como "texto", com o fundo sendo a própria cor sólida.
PALETA = [
    ("tinta",      "texto", ["fundo", "superficie", "superficie-2", "radar", "tl-fundo"]),
    ("tinta-2",    "texto", ["fundo", "superficie", "superficie-2", "tl-fundo"]),
    ("apagado",    "texto", ["fundo", "superficie", "superficie-2", "tl-fundo"]),
    ("borda",      "marca", ["fundo", "superficie", "superficie-2"]),
    ("ct",         "marca", ["fundo", "superficie", "radar", "tl-fundo"]),
    ("ct-texto",   "texto", ["fundo", "superficie", "superficie-2"]),
    ("tr",         "marca", ["fundo", "superficie", "radar", "tl-fundo"]),
    ("tr-texto",   "texto", ["fundo", "superficie", "superficie-2"]),
    ("decisivo",   "texto", ["fundo", "superficie", "superficie-2", "tl-fundo"]),
    ("smoke",      "marca", ["radar", "tl-fundo"]),
    ("flash",      "marca", ["radar", "tl-fundo"]),
    ("he",         "marca", ["radar", "tl-fundo"]),
    ("molotov",    "marca", ["radar", "tl-fundo"]),
    ("aviso",      "texto", ["superficie", "superficie-2", "radar", "tl-fundo"]),
    ("erro",       "texto", ["fundo", "superficie", "superficie-2"]),
    ("foco",       "marca", ["fundo", "superficie", "superficie-2", "radar", "tl-fundo"]),
    ("fundo",      "texto", ["ct", "tr", "decisivo", "aviso", "tinta"]),
]

# Grupos de cores que aparecem juntas (o ΔE é medido por grupo).
GRUPOS = {
    "graficos (decisao 10)": ["ct", "tr", "decisivo"],
    "radar e linha do tempo": ["ct", "tr", "decisivo", "smoke", "flash", "he", "molotov", "aviso"],
    "estados no painel": ["ct-texto", "tr-texto", "decisivo", "aviso", "erro"],
}
PARES_NOMEADOS = [("molotov", "tr"), ("molotov", "decisivo")]

# Os três tokens que formam a paleta dos gráficos da partida (decisão 10).
TOKENS_DOS_GRAFICOS = (("ct", "A_azul"), ("tr", "B_laranja"), ("decisivo", "decisivo"))


def le_tokens(caminho: Path = TOKENS) -> dict[str, str]:
    """Os tokens de cor do arquivo de estilo: linhas `--nome: #hex;` (um token por linha)."""
    texto = caminho.read_text(encoding="utf-8")
    return {m.group(1): m.group(2).lower()
            for m in re.finditer(r"^\s*--([a-z0-9-]+):\s*(#[0-9a-fA-F]{6})\s*;", texto, re.M)}


def paleta_em_uso() -> dict[str, str]:
    """As cores dos gráficos da partida (CT, TR e decisivo), lidas dos tokens."""
    tk = le_tokens()
    return {rotulo: tk[token] for token, rotulo in TOKENS_DOS_GRAFICOS if token in tk}


def _labs(cor: str) -> dict:
    return {"normal": rgb_para_lab(hex_para_rgb(cor)),
            **{t: rgb_para_lab(simula_dicromacia(cor, t)) for t in DICROMACIAS}}


def avalia(tk: dict[str, str], rotulo_da_origem: str) -> tuple[list[str], int]:
    """O relatório completo (as linhas) e quantas verificações falharam."""
    linhas = [f"tokens lidos de {rotulo_da_origem}: {len(tk)}",
              f"criterios: texto >= {LIMIAR['texto']}:1 e marca >= {LIMIAR['marca']}:1 contra os fundos onde a cor aparece; "
              f"dE daltonico >= {DELTA_E_MINIMO_DALTONICO} no pior par de cada grupo",
              "fundos: " + ", ".join(f"{k} {tk[k]} ({v})" for k, v in FUNDOS.items()), ""]
    falhas = 0

    linhas.append("== CONTRASTE ==")
    for nome, tipo, fundos in PALETA:
        lim = LIMIAR[tipo]
        medidas = [(f, contraste(tk[nome], tk[f])) for f in fundos]
        ok = min(r for _, r in medidas) >= lim
        falhas += not ok
        linhas.append(f"{nome:<13}{tk[nome]:<9}{tipo:<6}>= {lim:<4} "
                      + "  ".join(f"{f} {r:5.2f}" for f, r in medidas)
                      + f"   {'PASSA' if ok else 'FALHA'}")
    linhas.append("")

    linhas.append("== DALTONISMO (pior par de cada grupo) ==")
    for grupo, nomes in GRUPOS.items():
        labs = {n: _labs(tk[n]) for n in nomes}
        pares = list(itertools.combinations(nomes, 2))
        normal = min((delta_e_2000(labs[a]["normal"], labs[b]["normal"]), f"{a} x {b}") for a, b in pares)
        dalt = min((delta_e_2000(labs[a][t], labs[b][t]), f"{a} x {b} ({t})")
                   for a, b in pares for t in DICROMACIAS)
        ok = dalt[0] >= DELTA_E_MINIMO_DALTONICO
        falhas += not ok
        linhas.append(f"{grupo:<26} dE normal {normal[0]:5.1f} [{normal[1]}]  "
                      f"dE daltonico {dalt[0]:5.1f} [{dalt[1]}]  {'PASSA' if ok else 'FALHA'}")
    linhas.append("")

    linhas.append("== PARES NOMEADOS ==")
    for a, b in PARES_NOMEADOS:
        la, lb = _labs(tk[a]), _labs(tk[b])
        vals = {t: delta_e_2000(la[t], lb[t]) for t in la}
        ok = min(vals[t] for t in DICROMACIAS) >= DELTA_E_MINIMO_DALTONICO
        falhas += not ok
        linhas.append(f"{a} {tk[a]} x {b} {tk[b]}: "
                      + "  ".join(f"{t} {d:5.1f}" for t, d in vals.items())
                      + f"   {'PASSA' if ok else 'FALHA'}")
    linhas.append("")
    linhas.append("RESULTADO: " + ("PASSA" if falhas == 0 else f"FALHA ({falhas})"))
    return linhas, falhas


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    tk = le_tokens()
    origem = TOKENS.relative_to(RAIZ).as_posix()
    if not argv:
        linhas, falhas = avalia(tk, origem)
        print("\n".join(linhas))
        return 0 if falhas == 0 else 1
    # candidatos: cada um substitui só a cor do round decisivo; as demais são as dos tokens
    total = 0
    for cor in argv:
        print(f"== candidato para --decisivo: {cor}")
        linhas, falhas = avalia({**tk, "decisivo": cor.lower()}, origem)
        print("\n".join(linhas))
        print()
        total += falhas
    return 0 if total == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
