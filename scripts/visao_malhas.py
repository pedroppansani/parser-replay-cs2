"""Baixa a colisão dos mapas do corpus e grava no formato .tri do awpy 2.0.2 (fase 18, item 18.1).

    py -3.12 -m scripts.visao_malhas              # baixa, confere e converte (grava em ~/.awpy/tris)
    py -3.12 -m scripts.visao_malhas --confere    # só confere os .tri gravados contra o registro

POR QUE NÃO `awpy get tris`. O awpy 2.0.2 baixa os .tri de https://awpycs.com/<patch>/tris.zip, e o
servidor responde 403 (conferido em 2026-10-15, também para maps.zip e navs.zip). O mesmo autor passou
a publicar os dados dos mapas no repositório `pnxenopoulos/awpy-data` (releases do GitHub, um por versão
do cliente do CS2), num formato compacto (`.mesh`: cabeçalho "AWMH", versão 1, n de vértices, n de
triângulos, os vértices em float32 e os índices em uint32). Este script baixa UMA versão fixa
(`VERSAO_AWPY_DATA`), confere o sha256 do zip contra o manifest dela, e escreve cada mapa como .tri
(9 float32 por triângulo, o formato que `awpy.visibility.VisibilityChecker.read_tri_file` lê) em
`~/.awpy/tris/`, o diretório do awpy 2.0.2. O sha256 de cada .tri vai para `metrics/visao_malhas.json`
(versionado): o pipeline recusa uma malha diferente (`metrics.visao.carrega_malha`).

A malha é a do cliente da versão escolhida (outubro de 2026), não a da data de cada demo: uma mudança
de mapa entre a demo e essa versão muda a linha de visão naquele trecho. A conferência contra a
visibilidade gravada nas demos que existem no disco está na nota da fonte de visão.

Dado público do mapa; nenhum dado de partida é gravado aqui.
"""
from __future__ import annotations

import hashlib
import io
import json
import struct
import sys
import tempfile
import urllib.request
import zipfile
from pathlib import Path

import numpy as np

from metrics import visao

VERSAO_AWPY_DATA = "2000932"            # release de 2026-10-15 (patch 1.41.9.1, build 25947352)
SHA256_GEOMETRY_ZIP = "06ab94c50e6024162a6b322cd28af660f80da2558c68a093e4fac0e9385ac216"
URL = "https://github.com/pnxenopoulos/awpy-data/releases/download/{versao}/{nome}"
# Os mapas com partida no corpus (data/manifest.json).
MAPAS = ("de_ancient", "de_anubis", "de_dust2", "de_inferno", "de_mirage", "de_nuke", "de_overpass", "de_train")


def _baixa(nome: str) -> bytes:
    req = urllib.request.Request(URL.format(versao=VERSAO_AWPY_DATA, nome=nome), headers={"User-Agent": "awpy"})
    with urllib.request.urlopen(req, timeout=300) as r:  # noqa: S310 (host fixo)
        return r.read()


def mesh_para_triangulos(dados: bytes) -> np.ndarray:
    """(n, 3, 3) float32 a partir de um .mesh do awpy-data."""
    magica, versao, nv, nt = struct.unpack_from("<4sIII", dados, 0)
    if magica != b"AWMH" or versao != 1:
        raise ValueError(f"cabeçalho inesperado: {magica!r} v{versao}")
    if len(dados) != 16 + 12 * nv + 12 * nt:
        raise ValueError("tamanho do .mesh não confere com o cabeçalho")
    vert = np.frombuffer(dados, dtype="<f4", count=3 * nv, offset=16).reshape(nv, 3)
    idx = np.frombuffer(dados, dtype="<u4", count=3 * nt, offset=16 + 12 * nv).reshape(nt, 3)
    if idx.size and int(idx.max()) >= nv:
        raise ValueError("índice de vértice fora da faixa")
    return vert[idx]


def grava(destino: Path = visao.TRIS_DIR) -> dict:
    zip_bytes = _baixa("geometry.zip")
    h = hashlib.sha256(zip_bytes).hexdigest()
    if h != SHA256_GEOMETRY_ZIP:
        raise SystemExit(f"geometry.zip com sha256 {h}, esperado {SHA256_GEOMETRY_ZIP}")
    destino.mkdir(parents=True, exist_ok=True)
    reg = {"_leia_isto": ("Malhas de colisão dos mapas (fase 18, metrics/visao.py). Geradas por "
                          "`py -3.12 -m scripts.visao_malhas` a partir do awpy-data; o .tri fica em ~/.awpy/tris."),
           "fonte": URL.format(versao=VERSAO_AWPY_DATA, nome="geometry.zip"),
           "versao_awpy_data": VERSAO_AWPY_DATA, "sha256_geometry_zip": SHA256_GEOMETRY_ZIP, "mapas": {}}
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as z:
        for mapa in MAPAS:
            dados = z.read(f"{mapa}.mesh")
            tri = mesh_para_triangulos(dados).astype("<f4")
            with tempfile.NamedTemporaryFile(delete=False, dir=destino, suffix=".part") as f:
                f.write(tri.tobytes())
                tmp = Path(f.name)
            final = destino / f"{mapa}.tri"
            tmp.replace(final)
            reg["mapas"][mapa] = {"triangulos": int(tri.shape[0]),
                                  "sha256_mesh": hashlib.sha256(dados).hexdigest(),
                                  "sha256_tri": visao.sha256(final)}
            print(f"{mapa}: {tri.shape[0]} triângulos -> {final}")
    visao.REGISTRO_DAS_MALHAS.write_text(json.dumps(reg, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return reg


def confere(destino: Path = visao.TRIS_DIR) -> bool:
    reg = visao.registro().get("mapas") or {}
    ok = True
    for mapa in MAPAS:
        caminho = destino / f"{mapa}.tri"
        bate = caminho.exists() and visao.sha256(caminho) == (reg.get(mapa) or {}).get("sha256_tri")
        ok &= bate
        print(f"{mapa}: {'ok' if bate else 'FALTA OU DIFERENTE'}")
    return ok


def main(argv: list[str]) -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    if "--confere" in argv:
        return 0 if confere() else 1
    grava()
    return 0 if confere() else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
