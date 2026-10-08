"""Extrai para uma pasta os PNG dos radares locais (`assets/radars/`) no formato que os
scripts de medição leem: `<mapa>_<andar>.png`.

    py -3.12 -m scripts.design.extrai_radares [pasta]

No design, os radares eram baixados do site no ar; aqui são os do próprio projeto (são os
mesmos que o build embute nas páginas). Sem argumento, usa uma pasta temporária e imprime o caminho.
"""
import sys
from pathlib import Path

from scripts.design._comum import extrai_radares

if __name__ == "__main__":
    pasta = extrai_radares(Path(sys.argv[1]) if len(sys.argv) > 1 else None)
    print(pasta)
    for f in sorted(pasta.glob("*.png")):
        print(" ", f.name, f.stat().st_size)
