"""PC0: exporta os `.nav` do CS2 instalado (extraídos do .vpk de cada mapa) para JSON, lendo com o awpy 3.3.0 (o do projeto, o 2.0.2, só lê a versão 30 a 35 e o jogo hoje grava a 36).

Roda com o Python de um venv À PARTE que tenha o `awpy==3.3.0` (o do projeto NÃO muda):
    <venv>/Scripts/python.exe -m scripts.pc0.exporta_nav PASTA_DOS_NAV PASTA_DE_SAIDA

Cada mapa vira `<mapa>.json` com {"areas": {id: {"c": [[x, y, z], ...], "lig": [ids], "esc_cima": [...], "esc_baixo": [...]}}}. O que sai daqui é do jogo (Valve): fica FORA do repositório."""
from __future__ import annotations

import json
import sys
from pathlib import Path

from awpy import NavMesh


def exporta(nav: Path, saida: Path) -> dict:
    n = NavMesh(nav)
    areas = {}
    for aid in n.areas["area_id"].to_list():
        a = n.area(int(aid))
        areas[int(aid)] = {"c": [[round(v, 1) for v in p] for p in a["corners"]], "lig": [int(x) for x in a["connections"]],
                           "esc_cima": list(a["ladders_above"]), "esc_baixo": list(a["ladders_below"]), "flags": a["dynamic_attribute_flags"]}
    (saida / f"{nav.stem}.json").write_text(json.dumps({"versao": n.version, "sub": n.sub_version, "areas": areas}, separators=(",", ":")), encoding="utf-8")
    return {"areas": len(areas), "ligacoes": sum(len(a["lig"]) for a in areas.values()), "escadas": sum(len(a["esc_cima"]) + len(a["esc_baixo"]) for a in areas.values())}


if __name__ == "__main__":
    pasta, saida = Path(sys.argv[1]), Path(sys.argv[2])
    saida.mkdir(parents=True, exist_ok=True)
    for nav in sorted(pasta.glob("*.nav")):
        print(nav.stem, exporta(nav, saida))
