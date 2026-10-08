"""Peças comuns dos scripts de medição da direção visual "Sala de demo".

Origem: os scripts do `design` (entrega-sala-de-demo §15), adaptados ao repositório:
os radares saem de `assets/radars/` (não são baixados do site), as páginas medidas são
as de `docs/` (geradas por `py -3.12 -m scripts.build_site`) e os caminhos são
relativos à raiz do repositório.
"""
from __future__ import annotations

import base64
import re
import sys
import tempfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
DOCS = RAIZ / "docs"
RADARES = RAIZ / "assets" / "radars"
DESIGN = RAIZ / "notas" / "design"

# os 10 mapas da prancheta (entrega §4.1): 8 com partidas no corpus + Cache e Vertigo
MAPAS = ["ancient", "anubis", "dust2", "inferno", "mirage", "nuke", "overpass", "train", "cache", "vertigo"]

if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))


def chrome(playwright):
    """O Chrome do sistema, como nos testes de navegador; sem ele, o Chromium do Playwright."""
    try:
        return playwright.chromium.launch(channel="chrome")
    except Exception:
        return playwright.chromium.launch()


def url_de(pagina: str) -> str:
    """URL de arquivo de uma página de `docs/` (com o hash, se vier)."""
    nome, _, hash_ = pagina.partition("#")
    return (DOCS / nome).as_uri() + (f"#{hash_}" if hash_ else "")


def extrai_radares(destino: Path | None = None) -> Path:
    """Grava os PNG dos radares locais como `<mapa>_<andar>.png` (andar 0 = `image`;
    o seguinte = `layers`), o formato que `gera_radar_ajuste.py` lê. O radar é o mesmo
    que o build embute nas páginas (`assets/radars/de_<mapa>.json`)."""
    import json
    destino = destino or Path(tempfile.mkdtemp(prefix="radares_"))
    destino.mkdir(parents=True, exist_ok=True)
    for mapa in MAPAS:
        f = RADARES / f"de_{mapa}.json"
        if not f.exists():
            continue
        d = json.loads(f.read_text(encoding="utf-8"))
        imagens = [d["image"]] + list((d.get("layers") or {}).values())
        for i, uri in enumerate(imagens):
            bruto = re.sub(r"^data:image/png;base64,", "", uri)
            (destino / f"{mapa}_{i}.png").write_bytes(base64.b64decode(bruto))
    return destino
