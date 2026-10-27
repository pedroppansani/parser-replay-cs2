"""Matriz de pontos do mapa (entrega-v2-goatdemo §9, decisão 48), gerada NO BUILD.

Adaptado do `gera_pontos.py` do protótipo: em vez do PNG do radar (fora do git e ausente no CI), lê a imagem em
base64 de dentro de `assets/radars/<mapa>.json`. A saída é só uma máscara alfa (WebP, ~2 KB), usada no CSS como
`mask-image` em `data:` (em `file://` a máscara por URL de arquivo não é garantida). Determinístico: mesma
entrada, mesmos bytes. Na v2-3 só Dust II e Mirage (as laterais da landing); desde a v2-6, todo mapa
com partida no corpus (o carregamento da partida e a imagem de compartilhamento).

    py -3.12 -m scripts.design.gera_pontos de_mirage saida.webp     # para conferir a olho
"""
from __future__ import annotations

import base64
import io
import json
import sys
from functools import lru_cache
from pathlib import Path

from PIL import Image, ImageDraw

RADARS = Path(__file__).resolve().parents[2] / "assets" / "radars"
CELULAS = 64          # 64x64 pontos (protótipo)
PX_POR_CELULA = 8
ALFA_MINIMO = 40      # célula transparente do radar não vira ponto
LUM_MINIMA = 0.13     # o fundo escuro do radar não vira ponto


@lru_cache(maxsize=None)   # o build pede o mesmo mapa a cada página e a cada imagem
def mascara(mapa: str) -> bytes:
    """A máscara de pontos do radar de `mapa`, em WebP só alfa."""
    radar = json.loads((RADARS / f"{mapa}.json").read_text(encoding="utf-8"))
    im = Image.open(io.BytesIO(base64.b64decode(radar["image"].split(",", 1)[1]))).convert("RGBA")
    lado = max(im.size)
    tela = Image.new("RGBA", (lado, lado), (0, 0, 0, 0))
    tela.paste(im, ((lado - im.width) // 2, (lado - im.height) // 2))
    peq = tela.resize((CELULAS, CELULAS), Image.BOX)
    out = Image.new("L", (CELULAS * PX_POR_CELULA, CELULAS * PX_POR_CELULA), 0)
    d = ImageDraw.Draw(out)
    for j in range(CELULAS):
        for i in range(CELULAS):
            r, g, b, a = peq.getpixel((i, j))
            lum = (0.2126 * r + 0.7152 * g + 0.0722 * b) / 255
            if a < ALFA_MINIMO or lum < LUM_MINIMA:
                continue
            # o radar é escuro com traços claros: o ponto cresce com a luminância, com piso para o miolo não sumir
            raio = (0.18 + 0.82 * min(1, lum * 1.9)) * PX_POR_CELULA * 0.46
            cx, cy = i * PX_POR_CELULA + PX_POR_CELULA / 2, j * PX_POR_CELULA + PX_POR_CELULA / 2
            d.ellipse([cx - raio, cy - raio, cx + raio, cy + raio], fill=255)
    m = Image.new("RGBA", out.size, (255, 255, 255, 0))
    m.putalpha(out)
    buf = io.BytesIO()
    m.save(buf, "WEBP", quality=70, method=6)
    return buf.getvalue()


def data_uri(mapa: str) -> str:
    return "data:image/webp;base64," + base64.b64encode(mascara(mapa)).decode("ascii")


if __name__ == "__main__":
    dados = mascara(sys.argv[1])
    Path(sys.argv[2]).write_bytes(dados)
    print(sys.argv[2], len(dados), "bytes")
