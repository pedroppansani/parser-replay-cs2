"""
Validador da paleta, versão 2 (especificação do `design`, 2026-10-04).

É a especificação EXECUTÁVEL da mudança pedida em metrics/paleta.py (antes
scripts/valida_paleta.py). Roda FORA do projeto, contra os tokens do protótipo:

    py -3.12 -m scripts.design.paleta_v2 [tokens.css]

SÓ REFERÊNCIA da §9 da entrega (notas/design/entrega-sala-de-demo.md). O validador de
verdade é `metrics/paleta.py` (`py -3.12 -m metrics.paleta`), e a saída dele tem de ser
IDÊNTICA à desta, linha a linha (critério de aceite A8). Padrão: os tokens do protótipo.

O QUE MUDOU EM RELAÇÃO À VERSÃO 1
  1. O contraste deixa de ser medido contra o BRANCO e passa a ser medido contra
     os fundos do tema, cada um com o seu token: página, superfície, superfície
     elevada, radar e linha do tempo.
  2. Cada cor é marcada como TEXTO (limiar 4,5:1) ou MARCA (limiar 3:1: peça,
     ícone, barra, borda de controle, anel de foco) e é medida SÓ contra os
     fundos onde aparece.
  3. O critério de daltonismo NÃO muda: ΔE2000 >= 8 no pior par, protanopia e
     deuteranopia (Viénot, Brettel e Mollon 1999), em cada grupo de cores que
     aparece junto.
  4. Smoke e flash deixam de ser "falha esperada": são medidas contra o radar e
     a linha do tempo, onde aparecem.
  5. Pares nomeados (molotov x TR, molotov x decisivo) são impressos sempre,
     nas três visões.
"""
from __future__ import annotations

import itertools
import re
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import metrics.paleta as v1  # noqa: E402  (as contas de cor do projeto)

DELTA_E_MINIMO_DALTONICO = v1.DELTA_E_MINIMO_DALTONICO   # 8,0: não muda
LIMIAR = {"texto": 4.5, "marca": 3.0}

# Fundos do tema: token -> onde aparece.
FUNDOS = {
    "fundo": "página",
    "superficie": "cards e painéis",
    "superficie-2": "elevado: hover, aba ativa, popover, aviso",
    "radar": "canvas do mapa (peças e granadas)",
    "tl-fundo": "linha do tempo (replay e prancheta)",
}

# token, tipo, fundos onde aparece. Texto sobre cor sólida (ficha, botão) entra
# como "texto" com o fundo sendo a própria cor sólida.
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
    # texto escuro sobre cor sólida: ficha de jogador, botão principal, rótulo "venceu"
    ("fundo",      "texto", ["ct", "tr", "decisivo", "aviso", "tinta"]),
]

# Grupos que aparecem juntos (ΔE por grupo).
GRUPOS = {
    "graficos (decisao 10)": ["ct", "tr", "decisivo"],
    "radar e linha do tempo": ["ct", "tr", "decisivo", "smoke", "flash", "he", "molotov", "aviso"],
    "estados no painel": ["ct-texto", "tr-texto", "decisivo", "aviso", "erro"],
}
PARES_NOMEADOS = [("molotov", "tr"), ("molotov", "decisivo")]


def le_tokens(caminho: Path) -> dict[str, str]:
    texto = caminho.read_text(encoding="utf-8")
    return {m.group(1): m.group(2).lower()
            for m in re.finditer(r"^\s*--([a-z0-9-]+):\s*(#[0-9a-fA-F]{6})\s*;", texto, re.M)}


def _labs(cor: str):
    return {"normal": v1.rgb_para_lab(v1.hex_para_rgb(cor)),
            **{t: v1.rgb_para_lab(v1.simula_dicromacia(cor, t)) for t in v1.DICROMACIAS}}


def main() -> int:
    caminho = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parents[2] / "notas" / "design" / "prototipo" / "tokens.css"
    tk = le_tokens(caminho)
    print(f"tokens lidos de {caminho.name}: {len(tk)}")
    print(f"criterios: texto >= {LIMIAR['texto']}:1 e marca >= {LIMIAR['marca']}:1 contra os fundos onde a cor aparece; "
          f"dE daltonico >= {DELTA_E_MINIMO_DALTONICO} no pior par de cada grupo")
    print("fundos: " + ", ".join(f"{k} {tk[k]} ({v})" for k, v in FUNDOS.items()))
    print()
    falhas = 0

    print("== CONTRASTE ==")
    for nome, tipo, fundos in PALETA:
        lim = LIMIAR[tipo]
        medidas = [(f, v1.contraste(tk[nome], tk[f])) for f in fundos]
        pior = min(r for _, r in medidas)
        ok = pior >= lim
        falhas += not ok
        print(f"{nome:<13}{tk[nome]:<9}{tipo:<6}>= {lim:<4} "
              + "  ".join(f"{f} {r:5.2f}" for f, r in medidas)
              + f"   {'PASSA' if ok else 'FALHA'}")
    print()

    print("== DALTONISMO (pior par de cada grupo) ==")
    for grupo, nomes in GRUPOS.items():
        labs = {n: _labs(tk[n]) for n in nomes}
        pares = list(itertools.combinations(nomes, 2))
        normal = min((v1.delta_e_2000(labs[a]["normal"], labs[b]["normal"]), f"{a} x {b}") for a, b in pares)
        dalt = min((v1.delta_e_2000(labs[a][t], labs[b][t]), f"{a} x {b} ({t})")
                   for a, b in pares for t in v1.DICROMACIAS)
        ok = dalt[0] >= DELTA_E_MINIMO_DALTONICO
        falhas += not ok
        print(f"{grupo:<26} dE normal {normal[0]:5.1f} [{normal[1]}]  "
              f"dE daltonico {dalt[0]:5.1f} [{dalt[1]}]  {'PASSA' if ok else 'FALHA'}")
    print()

    print("== PARES NOMEADOS ==")
    for a, b in PARES_NOMEADOS:
        la, lb = _labs(tk[a]), _labs(tk[b])
        vals = {t: v1.delta_e_2000(la[t], lb[t]) for t in la}
        ok = min(vals[t] for t in v1.DICROMACIAS) >= DELTA_E_MINIMO_DALTONICO
        falhas += not ok
        print(f"{a} {tk[a]} x {b} {tk[b]}: "
              + "  ".join(f"{t} {d:5.1f}" for t, d in vals.items())
              + f"   {'PASSA' if ok else 'FALHA'}")
    print()
    print("RESULTADO:", "PASSA" if falhas == 0 else f"FALHA ({falhas})")
    return 0 if falhas == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
