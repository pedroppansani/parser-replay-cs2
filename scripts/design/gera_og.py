"""Imagens de compartilhamento 1200x630 (entrega-v2-goatdemo §9, decisão 48; plano v2-0 §4.6), geradas NO BUILD.

Reescrita em Pillow do `gera_og.py` do protótipo (que usa Playwright e não roda no job de build do CI): mesma
composição (fundo do escuro violeta, marca no alto à esquerda, texto, mapa em pontos à direita). Uma por partida
(placar, times, mapa, evento e a linha do decisor, tudo dado que o build já tem; dúvida 7) e uma da landing.
Sem agente e sem marca da Valve; o mapa só como máscara de pontos (`gera_pontos`).

- Texto com as instâncias ESTÁTICAS da Geist (600, 400) e da Geist Mono (500) em `fontes_og/` (geradas uma vez por
  `gera_fontes.py`, OFL junto).
- A marca (cabra C + wordmark, cujas letras são polilinhas de SVG) é o PNG pré-renderizado `marca_og.png`, versionado;
  `py -3.12 -m scripts.design.gera_og --marca` o refaz (precisa do Chrome; NÃO roda no build).
- Determinística: mesma entrada, mesmos bytes; o PNG sai sem nenhum bloco de metadado (só IHDR, IDAT e IEND).
"""
from __future__ import annotations

import io
import sys
from functools import lru_cache
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from scripts.design.gera_pontos import RADARS, mascara

AQUI = Path(__file__).resolve().parent
FONTES = AQUI / "fontes_og"
MARCA_PNG = AQUI / "marca_og.png"
LARGURA, ALTURA = 1200, 630
# cores do bloco escuro violeta do tokens.css (--fundo, --tinta da marca do protótipo, --tinta-2, --borda), as mesmas
# do gera_og.py do protótipo
FUNDO, TINTA, TINTA_2, PONTOS = (4, 6, 28), (255, 255, 255), (180, 180, 187), (106, 108, 160)
X, COLUNA = 72, 560            # margem e largura do texto (protótipo: left 72, width 560)
MAPA_CAIXA = (600, 35, 560)    # x, y e lado do mapa em pontos (protótipo: right 40, top 35, 560 x 560)


@lru_cache(maxsize=None)
def _fonte(nome: str, tamanho: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(FONTES / f"{nome}.ttf"), tamanho)


@lru_cache(maxsize=None)
def _pontos(mapa: str) -> Image.Image | None:
    """A máscara do mapa em L, já no tamanho da caixa (a mesma de gera_pontos, reamostrada como o navegador faz no protótipo)."""
    if not mapa or not (RADARS / f"{mapa}.json").exists():
        return None
    alfa = Image.open(io.BytesIO(mascara(mapa))).getchannel("A")
    return alfa.resize((MAPA_CAIXA[2], MAPA_CAIXA[2]), Image.LANCZOS)


def cabe(texto: str, fonte: ImageFont.FreeTypeFont, largura: int) -> str:
    """O texto inteiro se couber; senão cortado com reticências (nenhuma linha passa da coluna)."""
    if fonte.getlength(texto) <= largura:
        return texto
    while texto and fonte.getlength(texto + "…") > largura:
        texto = texto[:-1]
    return texto.rstrip() + "…"


def _base(mapa: str | None) -> tuple[Image.Image, ImageDraw.ImageDraw]:
    im = Image.new("RGB", (LARGURA, ALTURA), FUNDO)
    pts = _pontos(mapa) if mapa else None
    if pts is not None:
        x, y, _ = MAPA_CAIXA
        im.paste(Image.new("RGB", pts.size, PONTOS), (x, y), pts)
    marca = Image.open(MARCA_PNG).convert("RGBA")
    im.paste(marca, (X, 72), marca)
    return im, ImageDraw.Draw(im)


def _png(im: Image.Image) -> bytes:
    # paleta adaptativa: o desenho tem poucas cores (fundo, pontos, texto e o antisserrilhado); sem pnginfo nenhum
    buf = io.BytesIO()
    im.quantize(colors=64, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE).save(buf, "PNG", optimize=True)
    return buf.getvalue()


def imagem_da_partida(mapa: str | None, nomes: tuple[str, str], placar: tuple, venceu: str | None,
                      linhas: list[str]) -> bytes:
    """Os dois times em duas linhas (nome à esquerda, pontos à direita, como o card da landing; quem perdeu em
    --tinta-2) e embaixo até duas linhas pequenas (mapa e evento; a frase do decisor)."""
    im, d = _base(mapa)
    nums = ["" if p is None else str(p) for p in placar]

    def sobra(t: int) -> bool:   # os dois nomes cabem inteiros ao lado do número neste tamanho
        return all(_fonte("Geist-600", t).getlength(n) <= COLUNA - _fonte("GeistMono-500", t).getlength(p) - 24
                   for n, p in zip(nomes, nums))
    # o nome encolhe até 44 px antes de ser cortado com reticências
    t = next((t for t in (60, 54, 48) if sobra(t)), 44)
    nome_f, num_f, peq = _fonte("Geist-600", t), _fonte("GeistMono-500", t), _fonte("Geist-400", 30)
    y = 172
    for lado, nome, num in zip("AB", nomes, nums):
        cor = TINTA if venceu in (None, lado) else TINTA_2
        largura_num = num_f.getlength(num)
        d.text((X, y), cabe(nome, nome_f, int(COLUNA - largura_num - 24)), font=nome_f, fill=cor)
        d.text((X + COLUNA - largura_num, y), num, font=num_f, fill=cor)
        y += 80
    y += 28
    for linha in linhas[:2]:
        if linha:
            d.text((X, y), cabe(linha, peq, COLUNA), font=peq, fill=TINTA_2)
            y += 44
    return _png(im)


def imagem_da_landing(mapa: str | None, titulo: str, subtitulo: str) -> bytes:
    """Título grande (quebra na vírgula, como o protótipo) e o subtítulo embaixo."""
    im, d = _base(mapa)
    grande, peq = _fonte("Geist-600", 64), _fonte("Geist-400", 30)
    y = 160
    for parte in titulo.replace(", ", ",\n").split("\n"):
        d.text((X, y), cabe(parte, grande, COLUNA), font=grande, fill=TINTA)
        y += 68
    d.text((X, y + 28), cabe(subtitulo, peq, COLUNA), font=peq, fill=TINTA_2)
    return _png(im)


def _gera_marca() -> None:
    """Refaz `marca_og.png`: a cabra C (52 px) e o wordmark com a mira (44 px de altura), brancos, fundo transparente,
    como no gera_og.py do protótipo. Precisa do Playwright e do Chrome; não roda no build."""
    from playwright.sync_api import sync_playwright
    marca = AQUI.parents[1] / "dashboard" / "web" / "marca"
    wm = (marca / "goatdemo.svg").read_text(encoding="utf-8").replace("<svg ", '<svg style="height:44px;width:auto" ', 1)
    cabra = (marca / "cabra-c.svg").read_text(encoding="utf-8").replace("<svg ", '<svg style="width:52px;height:52px" ', 1)
    html = (f'<!doctype html><meta charset=utf-8><style>html,body{{margin:0;background:transparent;color:#fff}}'
            f'.l{{display:inline-flex;gap:16px;align-items:center}}</style><div class=l>{cabra}{wm}</div>')
    with sync_playwright() as pw:
        b = pw.chromium.launch(channel="chrome")
        pg = b.new_page(viewport={"width": 600, "height": 100})
        pg.set_content(html)
        png = pg.locator(".l").screenshot(omit_background=True)
        b.close()
    im = Image.open(io.BytesIO(png)).convert("RGBA")
    buf = io.BytesIO()
    im.save(buf, "PNG", optimize=True)
    MARCA_PNG.write_bytes(buf.getvalue())
    print(MARCA_PNG, im.size, len(buf.getvalue()), "bytes")


if __name__ == "__main__":
    if sys.argv[1:] == ["--marca"]:
        _gera_marca()
    else:
        print(__doc__)
