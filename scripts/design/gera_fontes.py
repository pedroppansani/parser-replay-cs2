"""Gera as fontes do site: Geist e Geist Mono em woff2, subconjunto latino (decisão 48; entrega-v2-goatdemo §3.1).

NÃO roda no build nem nos testes: precisa do `fontTools` (fora do requirements.txt). Os woff2 gerados ficam
versionados em `dashboard/web/fontes/` e o build só os copia para `docs/fontes/` e `preview/fontes/`.
Copiado do protótipo da v2 (`gera_fontes.py`), só com a pasta de saída trocada.

Origem: o pacote npm oficial `geist` (Vercel, github.com/vercel/geist-font), versão 1.7.2, licença SIL OFL 1.1.
    npm pack geist@1.7.2   (num diretório vazio)   &&   tar -xzf geist-1.7.2.tgz
    py -3.12 -m pip install fonttools brotli
    py -3.12 -m scripts.design.gera_fontes <pasta/package>
Saída em dashboard/web/fontes/: geist-latin.woff2 (variável, eixo wght limitado a 400..600; 17.852 bytes na
entrega), geist-mono-latin.woff2 (variável, wght 400..600, só o necessário para número; 8.560 bytes) e OFL.txt
(a licença, copiada sem mudança). Os @font-face de fallback saem de `scripts/design/mede_fallback.py`.
"""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

SAIDA = Path(__file__).resolve().parent.parent.parent / "dashboard" / "web" / "fontes"

# latim: ASCII, Latin-1 (á é í ó ú ã õ ç à â ê ô ü...), aspas e travessões, reticências, ×, −, setas simples, €, ™
LATIM = ("U+0020-007E,U+00A0-00FF,U+0131,U+0152-0153,U+02C6,U+02DA,U+02DC,U+2013-2014,U+2018-201A,U+201C-201E,"
         "U+2022,U+2026,U+2039-203A,U+20AC,U+2122,U+2190-2193,U+2212,U+00D7")
# mono só em número: dígitos, sinais, separadores e as poucas letras de "27 de 36", "1:14", "R12", "s", "x"
MONO = "U+0020-007E,U+00A0,U+00D7,U+2009,U+202F,U+2212,U+2013,U+2026"


def faz(origem: Path, destino: Path, unicodes: str, faixa: tuple[int, int]) -> int:
    from fontTools import subset
    from fontTools.ttLib import TTFont
    from fontTools.varLib import instancer
    f = TTFont(origem, lazy=False)
    opts = subset.Options()
    opts.flavor = None
    opts.layout_features = ["kern", "liga", "tnum", "calt", "ccmp", "locl", "mark", "mkmk"]
    opts.name_IDs = ["*"]
    opts.notdef_outline = True
    opts.drop_tables += ["DSIG"]
    s = subset.Subsetter(opts)
    s.populate(unicodes=subset.parse_unicodes(unicodes))
    s.subset(f)
    f = instancer.instantiateVariableFont(f, {"wght": faixa})
    f.flavor = "woff2"
    f.save(destino)
    return destino.stat().st_size


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 1:
        print(__doc__)
        return 2
    pacote = Path(argv[0]).resolve()
    SAIDA.mkdir(parents=True, exist_ok=True)
    a = faz(pacote / "dist/fonts/geist-sans/Geist-Variable.ttf", SAIDA / "geist-latin.woff2", LATIM, (400, 600))
    b = faz(pacote / "dist/fonts/geist-mono/GeistMono-Variable.ttf", SAIDA / "geist-mono-latin.woff2", MONO, (400, 600))
    shutil.copyfile(pacote / "LICENSE.txt", SAIDA / "OFL.txt")
    print(f"geist-latin.woff2 {a} bytes; geist-mono-latin.woff2 {b} bytes; OFL.txt copiado")
    return 0


if __name__ == "__main__":
    sys.exit(main())
