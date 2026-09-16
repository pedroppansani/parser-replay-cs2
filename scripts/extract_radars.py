"""
Extrai os radares oficiais dos mapas direto da instalação local do CS2.

Por que isso existe: o painel precisa de uma imagem de radar e da tabela que
converte coordenada de jogo em pixel. O CDN do awpy responde 404 há um tempo, e
um radar baixado de fórum vem recortado/redimensionado, o que obriga a calibrar
por tentativa e erro. Mas quem tem o CS2 instalado já tem as duas coisas em
disco, oficiais:

  panorama/images/overheadmaps/<mapa>_radar_psd.vtex_c   a imagem
  resource/overviews/<mapa>.txt                          pos_x, pos_y, scale

Usar a calibração da Valve elimina o encaixe heurístico do `prepare_radar.py`:
a conversão passa a ser exata, e não "a que melhor sobrepôs a nuvem de posições".

Os .txt também trazem `verticalsections` nos mapas de dois andares (Nuke,
Vertigo, Train): é a altura Z que separa os níveis, e é por isso que existe um
radar `_lower` separado. Sem isso, A e B da Nuke se sobrepõem no mapa 2D.

Formato do .vtex_c: cabeçalho de recurso do Source 2 (blocos RED2/DATA) e, logo
depois do cabeçalho, os mips comprimidos em LZ4.

Uso:
    python -m scripts.extract_radars                 # todos os mapas conhecidos
    python -m scripts.extract_radars de_mirage de_nuke
"""
from __future__ import annotations

import argparse
import base64
import json
import re
import struct
from io import BytesIO
from pathlib import Path

import lz4.block
import vpk
from PIL import Image

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RADAR_DIR = PROJECT_ROOT / "assets" / "radars"

# Caminhos padrão da instalação do Steam no Windows. O script aceita --cs2 para
# quem tem a biblioteca em outro disco.
DEFAULT_CS2 = Path(
    r"C:\Program Files (x86)\Steam\steamapps\common\Counter-Strike Global Offensive"
)

OVERHEAD = "panorama/images/overheadmaps/{name}_radar_psd.vtex_c"
OVERVIEW_TXT = "resource/overviews/{name}.txt"

# Formatos de imagem do Source 2. Os radares atuais são BGRA8888, mas mapas
# antigos (cs_italy) ainda estão em DXT, então os blocos comprimidos também
# entram — senão o script falha justamente nos mapas legados.
FMT_RGBA8888 = 4
FMT_BGRA8888 = 28
FMT_DXT1 = 1
FMT_DXT5 = 2
FMT_BC7 = 20


# ---------------------------------------------------------------------------
# Leitura do .vtex_c
# ---------------------------------------------------------------------------

def _blocks(raw: bytes) -> dict[str, tuple[int, int]]:
    """Tabela de blocos do recurso: nome -> (offset absoluto, tamanho)."""
    _size, _hver, _ver, block_off, block_count = struct.unpack_from("<IHHII", raw, 0)
    out: dict[str, tuple[int, int]] = {}
    pos = 8 + block_off
    for _ in range(block_count):
        btype = raw[pos:pos + 4].decode("ascii")
        off, size = struct.unpack_from("<II", raw, pos + 4)
        out[btype] = (pos + 4 + off, size)
        pos += 12
    return out


def decode_vtex(raw: bytes) -> Image.Image:
    """Devolve o mip 0 do .vtex_c como imagem RGBA."""
    header_size = struct.unpack_from("<I", raw, 0)[0]
    data_off, _ = _blocks(raw)["DATA"]

    width, height, _depth = struct.unpack_from("<HHH", raw, data_off + 20)
    img_fmt, mip_count = struct.unpack_from("<BB", raw, data_off + 26)
    _picmip, extra_off, extra_count = struct.unpack_from("<III", raw, data_off + 28)

    if img_fmt not in (FMT_BGRA8888, FMT_RGBA8888, FMT_DXT1, FMT_DXT5, FMT_BC7):
        raise ValueError(f"formato de imagem não suportado: {img_fmt}")

    # Extra data: procuramos COMPRESSED_MIP_SIZE (tipo 4), que lista o tamanho
    # comprimido de cada mip. Sem ela, os mips estão crus.
    compressed_mips: list[int] | None = None
    base = data_off + 32  # onde o campo extraDataOffset é lido
    pos = base + extra_off
    for i in range(extra_count):
        etype, eoff, _esize = struct.unpack_from("<III", raw, pos + i * 12)
        if etype == 4:
            entry = pos + i * 12 + 4 + eoff
            _int1, _int2, n_mips = struct.unpack_from("<III", raw, entry)
            compressed_mips = list(
                struct.unpack_from(f"<{n_mips}I", raw, entry + 12)
            )

    # Formato comprimido em blocos de 4x4: o tamanho do mip não é
    # largura*altura*4, e sim o número de blocos vezes o tamanho do bloco.
    blocks_wide = max(1, (width + 3) // 4)
    blocks_high = max(1, (height + 3) // 4)
    if img_fmt == FMT_DXT1:
        mip0_size = blocks_wide * blocks_high * 8
    elif img_fmt in (FMT_DXT5, FMT_BC7):
        mip0_size = blocks_wide * blocks_high * 16
    else:
        mip0_size = width * height * 4

    # Os mips ficam depois do cabeçalho, do MENOR para o MAIOR — o mip 0 é o
    # último bloco do arquivo.
    if compressed_mips:
        offset = header_size
        offsets = []
        for size in compressed_mips:
            offsets.append((offset, size))
            offset += size
        mip0_off, mip0_comp = offsets[0] if mip_count == 1 else offsets[-1]
        chunk = raw[mip0_off:mip0_off + mip0_comp]
        pixels = (
            chunk if mip0_comp == mip0_size
            else lz4.block.decompress(chunk, uncompressed_size=mip0_size)
        )
    else:
        pixels = raw[header_size:header_size + mip0_size]

    if img_fmt in (FMT_DXT1, FMT_DXT5, FMT_BC7):
        import texture2ddecoder

        decoder = {
            FMT_DXT1: texture2ddecoder.decode_bc1,
            FMT_DXT5: texture2ddecoder.decode_bc3,
            FMT_BC7: texture2ddecoder.decode_bc7,
        }[img_fmt]
        pixels = decoder(bytes(pixels), width, height)
        mode = "BGRA"
    else:
        mode = "BGRA" if img_fmt == FMT_BGRA8888 else "RGBA"

    return Image.frombytes("RGBA", (width, height), bytes(pixels), "raw", mode)


# ---------------------------------------------------------------------------
# Leitura do overview .txt (calibração oficial)
# ---------------------------------------------------------------------------

def parse_overview(text: str) -> dict:
    """Extrai pos_x, pos_y, scale e as seções verticais do .txt da Valve."""
    def num(key: str) -> float | None:
        m = re.search(rf'"{key}"\s+"(-?[\d.]+)"', text)
        return float(m.group(1)) if m else None

    out: dict = {"pos_x": num("pos_x"), "pos_y": num("pos_y"), "scale": num("scale")}

    # Mapas de dois andares declaram as faixas de altura de cada nível. É a
    # informação que separa, por exemplo, o A (em cima) do B (embaixo) na Nuke.
    sections: dict[str, dict[str, float]] = {}
    block = re.search(r'"verticalsections"\s*\{(.*?)\n\t\}', text, re.S)
    if block:
        for name, body in re.findall(r'"(\w+)"[^{]*\{(.*?)\}', block.group(1), re.S):
            amax = re.search(r'"AltitudeMax"\s+"(-?[\d.]+)"', body)
            amin = re.search(r'"AltitudeMin"\s+"(-?[\d.]+)"', body)
            if amax and amin:
                sections[name] = {"max": float(amax.group(1)), "min": float(amin.group(1))}
    if sections:
        out["vertical_sections"] = sections
    return out


# ---------------------------------------------------------------------------

def build(map_name: str, pak: vpk.VPKFile, quiet: bool = False) -> Path | None:
    try:
        raw = pak[OVERHEAD.format(name=map_name)].read()
    except KeyError:
        if not quiet:
            print(f"{map_name}: sem radar no VPK")
        return None

    try:
        txt = pak[OVERVIEW_TXT.format(name=map_name)].read().decode("utf-8", "replace")
    except KeyError:
        print(f"{map_name}: sem overview .txt (calibração) -- pulando")
        return None

    cal = parse_overview(txt)
    if cal["pos_x"] is None or cal["scale"] is None:
        print(f"{map_name}: .txt sem pos_x/scale -- pulando")
        return None

    img = decode_vtex(raw)

    # A tabela da Valve diz: pixel = (mundo - pos) / scale, com pos_x/pos_y no
    # canto superior esquerdo. O painel trabalha com px por unidade e origem,
    # então é só inverter a escala. A imagem oficial é sempre 1024x1024.
    scale_px_per_unit = img.width / (1024 * cal["scale"])

    layers: dict[str, str] = {}
    for section in (cal.get("vertical_sections") or {}):
        if section == "default":
            continue
        try:
            sub = pak[OVERHEAD.format(name=f"{map_name}_{section}")].read()
        except KeyError:
            continue
        layers[section] = _data_uri(decode_vtex(sub))

    RADAR_DIR.mkdir(parents=True, exist_ok=True)
    img.save(RADAR_DIR / f"{map_name}.png")

    meta = {
        "map": map_name,
        "width": img.width,
        "height": img.height,
        "scale_px_per_unit": scale_px_per_unit,
        "origin_x": cal["pos_x"],
        "origin_y": cal["pos_y"],
        "source": "cs2_local_install",
        "image": _data_uri(img),
    }
    if cal.get("vertical_sections"):
        meta["vertical_sections"] = cal["vertical_sections"]
    if layers:
        meta["layers"] = layers

    out = RADAR_DIR / f"{map_name}.json"
    out.write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")

    niveis = f" · {len(layers)} nível(is) extra" if layers else ""
    print(
        f"{map_name}: {img.width}x{img.height}  escala {scale_px_per_unit:.5f} px/unidade  "
        f"origem ({cal['pos_x']:.0f}, {cal['pos_y']:.0f}){niveis}"
    )
    return out


def _data_uri(img: Image.Image) -> str:
    buf = BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode("ascii")


def discover_maps(pak: vpk.VPKFile) -> list[str]:
    """Todo mapa que tem overview no jogo, descoberto do próprio VPK.

    Lista fixa envelhece: mapa novo entra no competitivo e o painel fica sem
    radar até alguém lembrar de editar o script.
    """
    found = []
    for path in pak:
        if path.startswith("resource/overviews/") and path.endswith(".txt"):
            name = path.rsplit("/", 1)[-1][:-4]
            if name != "workshop_preview":
                found.append(name)
    return sorted(found)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Extrai radares e calibração oficiais da instalação local do CS2."
    )
    parser.add_argument("maps", nargs="*", default=None, help="mapas (default: todos os do jogo)")
    parser.add_argument("--cs2", type=Path, default=DEFAULT_CS2, help="pasta de instalação do CS2")
    args = parser.parse_args()

    pak_path = args.cs2 / "game" / "csgo" / "pak01_dir.vpk"
    if not pak_path.exists():
        raise SystemExit(
            f"Não achei o CS2 em {args.cs2}.\n"
            "Passe o caminho com --cs2 (a pasta que contém game/csgo/pak01_dir.vpk)."
        )

    pak = vpk.open(str(pak_path))
    for name in (args.maps or discover_maps(pak)):
        try:
            build(name, pak, quiet=bool(args.maps))
        except Exception as exc:  # um mapa com formato novo não derruba o resto
            print(f"{name}: FALHOU ({type(exc).__name__}: {exc})")


if __name__ == "__main__":
    main()
