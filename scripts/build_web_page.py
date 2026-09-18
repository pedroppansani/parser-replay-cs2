"""
Injeta o payload da partida no template e gera a página final, autocontida.

Uso:
    python -m scripts.build_web_page match_01
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
TEMPLATE = PROJECT_ROOT / "dashboard" / "web" / "template.html"


def build_html(match_id: str, site: dict | None = None) -> str:
    """Devolve o HTML final da partida, com os dados já embutidos.

    `site` é a lista de partidas do site multi-demo (ver scripts/build_site.py).
    Sem ele, a barra de troca de partida fica escondida e o arquivo é um HTML
    solto que funciona offline — que é o modo original da página.
    """
    base = PROJECT_ROOT / "data" / "processed" / match_id
    payload = (base / "web_payload.json").read_text(encoding="utf-8")
    replay = (base / "replay.json").read_text(encoding="utf-8")
    breakdown_path = base / "breakdown.json"
    breakdown = breakdown_path.read_text(encoding="utf-8") if breakdown_path.exists() else "[]"
    # A camada de desenho vive em arquivo separado no repositorio (o template ja
    # esta grande demais) e e injetada aqui, para a pagina continuar sendo um
    # arquivo unico que abre offline.
    annotations = (TEMPLATE.parent / "annotations.js").read_text(encoding="utf-8")

    html = (
        TEMPLATE.read_text(encoding="utf-8")
        .replace("/*__DATA__*/", payload)
        .replace("/*__REPLAY__*/", replay)
        .replace("/*__BREAKDOWN__*/", breakdown)
        .replace("/*__ANNOTATIONS__*/", annotations)
    )

    map_name = json.loads((base / "match_meta.json").read_text(encoding="utf-8"))["map_name"]
    radar_path = PROJECT_ROOT / "assets" / "radars" / f"{map_name}.json"
    # o `||` mantém o `null` do template como fallback quando o mapa não tem radar
    html = html.replace(
        "/*__RADAR__*/",
        radar_path.read_text(encoding="utf-8") + " ||" if radar_path.exists() else "",
    )
    html = html.replace("/*__SITE__*/", json.dumps(site, ensure_ascii=False) + " ||" if site else "")
    return html


def build(match_id: str) -> Path:
    out = PROJECT_ROOT / "dashboard" / "web" / f"{match_id}.html"
    out.write_text(build_html(match_id), encoding="utf-8")
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description="Gera a página web autocontida da partida.")
    parser.add_argument("match_id", type=str)
    args = parser.parse_args()
    out = build(args.match_id)
    print(f"{out}  ({out.stat().st_size / 1024:.0f} KB)")


if __name__ == "__main__":
    main()
