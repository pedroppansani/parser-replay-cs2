"""
Gera a marca GOAT.demo (direção v2, decisão 48; copiado do protótipo `parser-cs2-v2/gera_marca.py`): cabras
geométricas e wordmarks, tudo em SVG de UMA cor (currentColor). Nada de fonte: as letras são polilinhas (cantos em
mitra), desenhadas aqui. Origem própria, nenhum logotipo de terceiros. NÃO roda no build: os SVGs vão prontos para
o repositório. Só a cabra C, o `goatdemo` e o `goatdemo-liso` saem (as cabras A e B e os wordmarks 1 a 3 ficam
como histórico no protótipo).

    py -3.12 -B -m scripts.design.gera_marca     # reescreve dashboard/web/marca/*.svg
"""
from __future__ import annotations
import sys
from pathlib import Path

sys.dont_write_bytecode = True
SAIDA = Path(__file__).resolve().parents[2] / "dashboard" / "web" / "marca"
ENTRAM = ("cabra-c", "goatdemo", "goatdemo-liso")

# ----------------------------------------------------------------------------------------------- cabras (viewBox 64x64)
# A: de frente, simétrica. Chifres em crescente, orelhas retas, barba. Detalhe CS: mira (cruz com centro vazado) entalhada na testa.
CABRA_A = """
<defs><mask id="{p}m" maskUnits="userSpaceOnUse" x="0" y="0" width="64" height="64">
  <rect width="64" height="64" fill="#fff"/>
  <path d="M24 33 L30 35.4 L30 37.6 Z M40 33 L34 35.4 L34 37.6 Z" fill="#000"/>
  <path d="M31.2 22 H32.8 V25 H31.2 Z M31.2 29 H32.8 V32 H31.2 Z M26.5 26.6 H29.5 V28.2 H26.5 Z M34.5 26.6 H37.5 V28.2 H34.5 Z" fill="#000"/>
</mask></defs>
<g mask="url(#{p}m)" fill="currentColor">
  <path d="M27 21 C15 22 6 15 6 3 C12 8 18 9 31 14 Z"/>
  <path d="M37 21 C49 22 58 15 58 3 C52 8 46 9 33 14 Z"/>
  <path d="M20 24 L5 26 L12 34 L21 34 Z"/>
  <path d="M44 24 L59 26 L52 34 L43 34 Z"/>
  <path d="M19 21 L45 21 L41 41 L36 56 L32 63 L28 56 L23 41 Z"/>
</g>
"""
# B: perfil para a esquerda, um chifre longo para trás, barba. Detalhe CS: o olho é uma mira (anel com cruz).
CABRA_B = """
<defs><mask id="{p}m" maskUnits="userSpaceOnUse" x="0" y="0" width="64" height="64">
  <rect width="64" height="64" fill="#fff"/>
  <path d="M33 30.6 A3.4 3.4 0 1 0 33 37.4 A3.4 3.4 0 1 0 33 30.6 Z M33 32.4 A1.6 1.6 0 1 1 33 35.6 A1.6 1.6 0 1 1 33 32.4 Z" fill="#000" fill-rule="evenodd"/>
</mask></defs>
<g mask="url(#{p}m)" fill="currentColor">
  <path d="M38 25 C40 10 52 3 62 7 C54 11 50 19 50 31 Z"/>
  <path d="M47 31 L63 35 L48 42 Z"/>
  <path d="M40 21 L51 29 L52 63 L34 63 L31 55 L22 58 L13 55 L14 45 L28 24 Z"/>
  <path d="M20 57 L18 64 L28 58 Z"/>
</g>
"""
# C: selo hexagonal com a cabra em negativo. Detalhe CS: quatro entalhes no hexágono, como as folgas de uma mira.
CABRA_C = """
<defs><mask id="{p}m" maskUnits="userSpaceOnUse" x="0" y="0" width="64" height="64">
  <rect width="64" height="64" fill="#fff"/>
  <g transform="translate(32 33.5) scale(.66) translate(-32 -32)" fill="#000">
    <path d="M27 21 C15 22 6 15 6 3 C12 8 18 9 31 14 Z"/>
    <path d="M37 21 C49 22 58 15 58 3 C52 8 46 9 33 14 Z"/>
    <path d="M20 24 L5 26 L12 34 L21 34 Z"/>
    <path d="M44 24 L59 26 L52 34 L43 34 Z"/>
    <path d="M19 21 L45 21 L41 41 L36 56 L32 63 L28 56 L23 41 Z"/>
    <path d="M24 33 L30 35.4 L30 37.6 Z M40 33 L34 35.4 L34 37.6 Z" fill="#fff"/>
  </g>
  <path d="M30.6 0 H33.4 V5 H30.6 Z M30.6 59 H33.4 V64 H30.6 Z M0 30.6 H8 V33.4 H0 Z M56 30.6 H64 V33.4 H56 Z" fill="#000"/>
</mask></defs>
<path d="M32 1 L59 16.5 V47.5 L32 63 L5 47.5 V16.5 Z" fill="currentColor" mask="url(#{p}m)"/>
"""
CABRAS = {"cabra-a": ("Frontal", CABRA_A), "cabra-b": ("Perfil", CABRA_B), "cabra-c": ("Pico", CABRA_C)}

# ----------------------------------------------------------------------------------------------- letras (polilinhas)
# grade: x 0..largura, y 0 (ascendente) / 2 (altura-x) .. 6 (linha de base), 8 (descendente)
def fechada(*pts):
    return list(pts) + [pts[0]]

O = fechada((1, 2), (3, 2), (4, 3), (4, 5), (3, 6), (1, 6), (0, 5), (0, 3))
CAIXA_O = fechada((1, 0), (3, 0), (4, 1), (4, 5), (3, 6), (1, 6), (0, 5), (0, 1))
GLIFOS = {
    # maiúsculas
    "G": (4, [[(4, 1), (3, 0), (1, 0), (0, 1), (0, 5), (1, 6), (3, 6), (4, 5), (4, 3), (2, 3)]]),
    "O": (4, [CAIXA_O]),
    "A": (4, [[(0, 6), (0, 1), (1, 0), (3, 0), (4, 1), (4, 6)], [(0, 3), (4, 3)]]),
    "T": (4, [[(0, 0), (4, 0)], [(2, 0), (2, 6)]]),
    # minúsculas
    "g": (4, [[(4, 2), (1, 2), (0, 3), (0, 5), (1, 6), (4, 6)], [(4, 2), (4, 7), (3, 8), (1, 8), (0, 7)]]),
    "o": (4, [O]),
    "a": (4, [[(0, 3), (1, 2), (3, 2), (4, 3), (4, 6)], [(4, 4), (1, 4), (0, 5), (1, 6), (4, 6)]]),
    "t": (4, [[(2, 0), (2, 5), (3, 6), (4, 6)], [(0, 2), (4, 2)]]),
    "p": (4, [[(0, 2), (0, 8)], [(0, 2), (3, 2), (4, 3), (4, 5), (3, 6), (0, 6)]]),
    "e": (4, [[(0, 4), (4, 4), (4, 3), (3, 2), (1, 2), (0, 3), (0, 5), (1, 6), (4, 6)]]),
    "k": (4, [[(0, 0), (0, 6)], [(4, 2), (0, 4.2)], [(1.4, 3.5), (4, 6)]]),
    "r": (3, [[(0, 2), (0, 6)], [(0, 3), (1, 2), (3, 2)]]),
    "u": (4, [[(0, 2), (0, 5), (1, 6), (4, 6)], [(4, 2), (4, 6)]]),
    "n": (4, [[(0, 6), (0, 2)], [(0, 3), (1, 2), (3, 2), (4, 3), (4, 6)]]),
    "d": (4, [[(4, 2), (1, 2), (0, 3), (0, 5), (1, 6), (4, 6)], [(4, 0), (4, 6)]]),
    "m": (7, [[(0, 6), (0, 2)], [(0, 3), (1, 2), (2.5, 2), (3.5, 3), (3.5, 6)], [(3.5, 3), (4.5, 2), (6, 2), (7, 3), (7, 6)]]),
}
PONTO = "."


def monta_texto(texto: str, espessura: float, espaco: float, pontos_peso: float | None = None, extra=None):
    """devolve (caminhos svg, largura, y_min, y_max). Os glifos são desenhados com traço `espessura` em unidades da grade."""
    x = 0.0
    partes: list[str] = []
    for ch in texto:
        if ch == PONTO:
            lado = espessura * 1.35
            partes.append(f'<rect x="{x:.2f}" y="{6 - lado + espessura / 2:.2f}" width="{lado:.2f}" height="{lado:.2f}" fill="currentColor" stroke="none"/>')
            x += lado + espaco
            continue
        larg, tracos = GLIFOS[ch]
        for pl in tracos:
            d = "M" + " L".join(f"{x + px:.2f} {py:.2f}" for px, py in pl)
            partes.append(f'<path d="{d}"/>')
        if extra and ch in extra:
            partes.append(extra[ch](x))
        x += larg + espaco
    return partes, x - espaco


def wordmark(texto: str, espessura: float, espaco: float, extra=None, descende=True):
    partes, larg, = monta_texto(texto, espessura, espaco, extra=extra)
    pad = espessura
    y0, y1 = -pad / 2, (8 if descende else 6) + pad / 2
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{-pad / 2:.2f} {y0:.2f} {larg + pad:.2f} {y1 - y0:.2f}" fill="none" stroke="currentColor" '
        f'stroke-width="{espessura}" stroke-linejoin="miter" stroke-miterlimit="6" stroke-linecap="butt" role="img" aria-label="{texto}">'
        + "".join(partes) + "</svg>"
    )


def mira_no_o(x):
    # detalhe CS no wordmark 3: o "o" de round ganha uma cruz de mira central (4 ticks curtos)
    cx, cy = x + 2, 4
    return (f'<path d="M{cx} {cy - 1.3} V{cy - 0.45} M{cx} {cy + 0.45} V{cy + 1.3} M{cx - 1.3} {cy} H{cx - 0.45} M{cx + 0.45} {cy} H{cx + 1.3}" stroke-width="0.5"/>')



def escreve():
    SAIDA.mkdir(exist_ok=True)
    for nome, (rotulo, corpo) in CABRAS.items():
        svg = f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" role="img" aria-label="Cabra {rotulo}">' + corpo.format(p=nome[-1]) + "</svg>"
        if nome in ENTRAM:
            (SAIDA / f"{nome}.svg").write_text(svg, encoding="utf-8")
    w1 = wordmark("GOAT.demo", 1.35, 1.9, descende=False)
    # v2 (decisão 1 do Pedro, 2026-10-15): GOAT.demo com a mira do wordmark 3 no "O" de GOAT, só de 24 px de altura para cima.
    # O "O" maiúsculo ocupa x = (4 + 1,9) .. +4 e y = 0..6; a mira fica no centro (x + 2, 3), traço 0,55, ticks de 1,05 com folga de 0,5.
    ox, oy = 4 + 1.9 + 2, 3
    mira_O = (f'<path d="M{ox} {oy - 1.55} V{oy - 0.5} M{ox} {oy + 0.5} V{oy + 1.55} M{ox - 1.25} {oy} H{ox - 0.5} M{ox + 0.5} {oy} H{ox + 1.25}" stroke-width="0.55"/>')
    goatdemo = w1.replace("</svg>", mira_O + "</svg>").replace('aria-label="GOAT.demo"', 'aria-label="GOAT.demo"')
    marcas = {"goatdemo": goatdemo, "goatdemo-liso": w1}
    for nome, svg in marcas.items():
        (SAIDA / f"{nome}.svg").write_text(svg, encoding="utf-8")
    return marcas


if __name__ == "__main__":
    m = escreve()
    for k, v in m.items():
        print(k, len(v), "bytes")
