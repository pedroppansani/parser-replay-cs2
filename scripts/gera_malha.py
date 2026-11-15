"""PC1: deriva da malha de navegação do CS2 (`.nav`) o dado que o site usa para o caminho das peças: os polígonos das áreas e as ligações dirigidas. Decisão 69.

O `.nav` é dado do jogo (Valve): ele NUNCA entra no repositório; só entra o dado derivado, `data/caminhos/malha/<mapa>.json`, com a versão do `.nav` de origem, o sha256 dele e a data.
O build e o CI leem só o arquivo derivado (`scripts/build_caminhos.py`); este script roda no PC do Pedro, onde o jogo está instalado.

Por que um venv à parte: o awpy do projeto (2.0.2) lê `.nav` até a versão 35 e o jogo hoje grava a 36; o awpy 3.3.0 lê a 36. O projeto NÃO muda de awpy.

    py -3.12 -m venv %TEMP%\\awpy3-venv
    %TEMP%\\awpy3-venv\\Scripts\\python.exe -m pip install awpy==3.3.0 vpk==1.4.0
    %TEMP%\\awpy3-venv\\Scripts\\python.exe -m scripts.gera_malha [--cs2 "C:\\...\\Counter-Strike Global Offensive"] [--mapas de_mirage de_nuke ...] [--confere]

`--confere` não grava nada: diz, mapa a mapa, se o `.nav` do jogo mudou desde o arquivo derivado (a versão, o sha256, o número de áreas e de ligações), para quando uma atualização do jogo mexe num mapa;
o arquivo novo entra num commit à parte.

Formato de cada mapa:
  {"versao": 1, "mapa", "gerado_em", "origem": {"nav_versao", "nav_sub_versao", "sha256", "awpy"}, "credito",
   "areas": {"id": [ids na ordem], "poli": [[x, y, z, x, y, z, ...] por área, em unidades inteiras]},
   "lig": [de, para, ...] (índices das áreas, dirigidas, com as escadas de mão ligadas nos dois sentidos)}"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
PASTA = RAIZ / "data" / "caminhos" / "malha"
CS2_PADRAO = Path(r"C:\Program Files (x86)\Steam\steamapps\common\Counter-Strike Global Offensive")
CREDITO = "Derivado dos arquivos de navegação do CS2, da Valve (uso não comercial); o projeto não tem ligação com a Valve."
MAPAS = ["de_ancient", "de_anubis", "de_cache", "de_dust2", "de_inferno", "de_mirage", "de_nuke", "de_overpass", "de_train", "de_vertigo"]


def le_nav_do_jogo(mapa: str, cs2: Path) -> bytes:
    import vpk
    pacote = vpk.open(str(cs2 / "game" / "csgo" / "maps" / f"{mapa}.vpk"))
    return pacote.get_file(f"maps/{mapa}.nav").read()


def deriva(mapa: str, nav: bytes, pasta_tmp: Path) -> dict:
    from awpy import NavMesh
    import awpy
    pasta_tmp.mkdir(parents=True, exist_ok=True)
    arq = pasta_tmp / f"{mapa}.nav"
    arq.write_bytes(nav)
    n = NavMesh(arq)
    ids = [int(i) for i in n.areas["area_id"].to_list()]
    pos = {a: k for k, a in enumerate(ids)}
    poli, lig, embaixo, em_cima = [], set(), {}, {}
    for a in ids:
        d = n.area(a)
        poli.append([int(round(v)) for c in d["corners"] for v in c])
        for b in d["connections"]:
            if int(b) in pos:
                lig.add((pos[a], pos[int(b)]))
        for e in d["ladders_above"]:
            embaixo.setdefault(int(e), []).append(pos[a])
        for e in d["ladders_below"]:
            em_cima.setdefault(int(e), []).append(pos[a])
    for e, bs in embaixo.items():      # a área de baixo diz "escada acima: N" e a de cima "escada abaixo: N": o mesmo id as liga, nos dois sentidos
        for b in bs:
            for c in em_cima.get(e, []):
                lig.add((b, c))
                lig.add((c, b))
    achatado = [v for par in sorted(lig) for v in par]
    return {"versao": 1, "mapa": mapa, "gerado_em": datetime.date.today().isoformat(),
            "origem": {"nav_versao": n.version, "nav_sub_versao": n.sub_version, "sha256": hashlib.sha256(nav).hexdigest(), "awpy": awpy.__version__},
            "credito": CREDITO, "areas": {"id": ids, "poli": poli}, "lig": achatado}


def confere(mapa: str, novo: dict) -> str:
    arq = PASTA / f"{mapa}.json"
    if not arq.exists():
        return "sem arquivo derivado ainda"
    antigo = json.loads(arq.read_text(encoding="utf-8"))
    if antigo["origem"]["sha256"] == novo["origem"]["sha256"]:
        return "igual (mesmo sha256)"
    a, b = antigo["origem"], novo["origem"]
    return (f"MUDOU: versão {a['nav_versao']}.{a['nav_sub_versao']} -> {b['nav_versao']}.{b['nav_sub_versao']}; áreas {len(antigo['areas']['id'])} -> {len(novo['areas']['id'])}; "
            f"ligações {len(antigo['lig']) // 2} -> {len(novo['lig']) // 2}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--cs2", type=Path, default=CS2_PADRAO)
    ap.add_argument("--mapas", nargs="*", default=MAPAS)
    ap.add_argument("--confere", action="store_true")
    a = ap.parse_args()
    import tempfile
    tmp = Path(tempfile.mkdtemp(prefix="malha_"))
    PASTA.mkdir(parents=True, exist_ok=True)
    for mapa in a.mapas:
        novo = deriva(mapa, le_nav_do_jogo(mapa, a.cs2), tmp)
        if a.confere:
            print(f"{mapa}: {confere(mapa, novo)}")
            continue
        (PASTA / f"{mapa}.json").write_text(json.dumps(novo, separators=(",", ":")), encoding="utf-8")
        print(f"{mapa}: {len(novo['areas']['id'])} áreas, {len(novo['lig']) // 2} ligações, nav v{novo['origem']['nav_versao']}.{novo['origem']['nav_sub_versao']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
