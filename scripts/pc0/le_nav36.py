"""PC0: lê um `.nav` do CS2 versão 36 com o leitor do awpy 2.0.2 (que só aceita 30 a 35), tratando a 36 como a 35 e conferindo que o arquivo é consumido até o último byte."""
from __future__ import annotations

import struct
from pathlib import Path

from awpy.nav import Nav


def le(path: Path, versao_do_leitor: int = 35) -> tuple[Nav, int, int]:
    """Devolve (nav, bytes_lidos, bytes_do_arquivo). `bytes_lidos == bytes_do_arquivo` diz que a estrutura da 36 é a da 35."""
    with open(path, "rb") as f:
        magic, versao, sub, unk1 = struct.unpack("4I", f.read(16))
        assert magic == Nav.MAGIC, hex(magic)
        v = versao_do_leitor
        polygons = Nav._read_polygons(f, v) if v >= 31 else None
        if v >= 32:
            f.read(4)
        if v >= 35:
            f.read(4)
        areas = Nav._read_areas(f, polygons, v)
        fim = f.tell()
        resto = len(f.read())
    return Nav(version=versao, sub_version=sub, areas=areas, is_analyzed=bool(unk1 & 1)), fim, fim + resto


if __name__ == "__main__":
    import os
    import sys
    pasta = Path(os.environ["LOCALAPPDATA"]) / "Temp" / "pc0" / "navs"
    for p in sorted(pasta.glob("*.nav")):
        try:
            n, lidos, total = le(p)
            zs = [a.centroid.z for a in n.areas.values()]
            lig = sum(len(a.connections) for a in n.areas.values())
            print(f"{p.stem}: v{n.version}.{n.sub_version}; {len(n.areas)} áreas; {lig} ligações; z {min(zs):.0f}..{max(zs):.0f}; lidos {lidos} de {total} bytes")
        except Exception as e:      # noqa: BLE001
            print(p.stem, "ERRO", type(e).__name__, str(e)[:100])
