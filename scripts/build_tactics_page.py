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
LUGARES_DIR = PROJECT_ROOT / "data" / "lugares"
RADARS_DIR = PROJECT_ROOT / "assets" / "radars"


def arquivo_da_pagina(mapa: str) -> str:
    return f"prancheta_{mapa}.html"


# Variantes de radar que não são o mapa competitivo (radar noturno, versão
# antiga, imagem crua de antes da calibração).
SUFIXOS_NAO_COMPETITIVOS = ("_night", "_v1", "_raw")


def mapas_disponiveis() -> list[str]:
    """Mapas com prancheta: todo radar CALIBRADO de mapa competitivo (de_*). A
    biblioteca de arremessos é opcional -- mapa sem partida no corpus ganha a
    prancheta sem a busca de arremesso real, e a página diz por quê."""
    return sorted(p.stem for p in RADARS_DIR.glob("de_*.json")
                  if not p.stem.endswith(SUFIXOS_NAO_COMPETITIVOS))


from scripts.meta_da_pagina import meta_tags  # noqa: E402
from metrics.tactics import modelo3_para_a_pagina  # noqa: E402


def _js(valor) -> str:
    # `</` fechando o <script> no meio de um nome de jogador quebraria a página:
    # a injeção segura é uma função só, usada também pela página da partida
    from scripts.json_em_script import js
    return js(valor)


def build_html(mapa: str, rotulos: dict[str, str] | None = None, site: str | None = None) -> str:
    radar = json.loads((RADARS_DIR / f"{mapa}.json").read_text(encoding="utf-8"))
    # a mesma impressão que as anotações usam: tática feita sobre outra
    # calibração do radar é recusada na importação
    radar["calibracao"] = impressao_da_calibracao(radar)
    caminho_bib = LINEUPS_DIR / f"{mapa}.json"
    biblioteca = json.loads(caminho_bib.read_text(encoding="utf-8")) if caminho_bib.exists() else None
    # nomes de lugar do roteiro (scripts/build_lugares.py); sem tabela, sem nome
    caminho_lug = LUGARES_DIR / f"{mapa}.json"
    lugares = json.loads(caminho_lug.read_text(encoding="utf-8")) if caminho_lug.exists() else None
    if rotulos is None:
        from metrics.constantes import NOME_DO_MAPA
        rotulos = NOME_DO_MAPA
    mapas = [{"mapa": m, "nome": rotulos.get(m, m), "arquivo": arquivo_da_pagina(m)} for m in mapas_disponiveis()]
    return (
        (WEB / "tactics.html").read_text(encoding="utf-8")
        .replace("/*__ANNOTATIONS_CSS__*/", (WEB / "annotations.css").read_text(encoding="utf-8"))
        .replace("/*__TACTICS_CSS__*/", (WEB / "tactics.css").read_text(encoding="utf-8"))
        .replace("/*__MAP_CORE__*/", (WEB / "map_core.js").read_text(encoding="utf-8"))
        .replace("/*__TACTICS_JS__*/", (WEB / "tactics.js").read_text(encoding="utf-8"))
        .replace("/*__MAPA__*/null", _js(mapa))
        .replace("/*__RADAR__*/null", _js(radar))
        .replace("/*__LINEUPS__*/null", _js(biblioteca))
        .replace("/*__MAPAS__*/[]", _js(mapas))
        .replace("/*__MODELO3__*/null", _js(modelo3_para_a_pagina()))
        .replace("/*__LUGARES__*/null", _js(lugares))
        .replace("<!--__META__-->", meta_tags(
            f"Prancheta tática · {rotulos.get(mapa, mapa)}",
            f"Monte uma tática na {rotulos.get(mapa, mapa)}: jogadores, granadas reais do corpus e passos.",
            site, arquivo_da_pagina(mapa)))
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
