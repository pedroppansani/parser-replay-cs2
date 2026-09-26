"""
Gera a página da prancheta tática de um mapa, autocontida (abre offline).

Uma página por mapa, com o radar e a biblioteca de arremessos reais daquele
mapa embutidos -- a mesma razão de o site ter uma página por partida (ver
scripts/build_site.py): sem servidor, sem fetch, e o arquivo salvo continua
funcionando. Só entra mapa que tem as duas coisas: radar calibrado e biblioteca
(`data/lineups/`, gerada por scripts/build_lineups.py).

Uso:
    py -3.12 -m scripts.build_tactics_page de_mirage
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from metrics.annotations import impressao_da_calibracao

PROJECT_ROOT = Path(__file__).resolve().parent.parent
WEB = PROJECT_ROOT / "dashboard" / "web"
LINEUPS_DIR = PROJECT_ROOT / "data" / "lineups"
RADARS_DIR = PROJECT_ROOT / "assets" / "radars"


def arquivo_da_pagina(mapa: str) -> str:
    return f"prancheta_{mapa}.html"


def mapas_disponiveis() -> list[str]:
    return sorted(p.stem for p in LINEUPS_DIR.glob("de_*.json") if (RADARS_DIR / p.name).exists())


def _js(valor) -> str:
    # `</` fechando o <script> no meio de um nome de jogador quebraria a página
    return json.dumps(valor, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")


def build_html(mapa: str, rotulos: dict[str, str] | None = None) -> str:
    radar = json.loads((RADARS_DIR / f"{mapa}.json").read_text(encoding="utf-8"))
    # a mesma impressão que as anotações usam: tática feita sobre outra
    # calibração do radar é recusada na importação
    radar["calibracao"] = impressao_da_calibracao(radar)
    biblioteca = json.loads((LINEUPS_DIR / f"{mapa}.json").read_text(encoding="utf-8"))
    rotulos = rotulos or {}
    mapas = [{"mapa": m, "nome": rotulos.get(m, m), "arquivo": arquivo_da_pagina(m)} for m in mapas_disponiveis()]
    return (
        (WEB / "tactics.html").read_text(encoding="utf-8")
        .replace("/*__MAP_CORE__*/", (WEB / "map_core.js").read_text(encoding="utf-8"))
        .replace("/*__TACTICS_JS__*/", (WEB / "tactics.js").read_text(encoding="utf-8"))
        .replace("/*__MAPA__*/null", _js(mapa))
        .replace("/*__RADAR__*/null", _js(radar))
        .replace("/*__LINEUPS__*/null", _js(biblioteca))
        .replace("/*__MAPAS__*/[]", _js(mapas))
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Gera a página da prancheta de um mapa.")
    parser.add_argument("mapa", type=str)
    args = parser.parse_args()
    saida = WEB / arquivo_da_pagina(args.mapa)
    saida.write_text(build_html(args.mapa), encoding="utf-8")
    print(f"{saida.relative_to(PROJECT_ROOT)} ({saida.stat().st_size / 1024:.0f} KB)")


if __name__ == "__main__":
    main()
