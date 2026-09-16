"""
Processa em lote todos os .dem da pasta `demos/` e gera a cadeia completa de
cada partida (métricas + insights + replay + payload).

Existe porque o site de demonstração mostra várias partidas, e rodar os cinco
comandos à mão pra cada uma é onde se erra a ordem e se publica número velho.

O match_id sai do nome do arquivo do FACEIT, que é um GUID — ilegível. Então as
partidas são numeradas por ordem de processamento (match_01, match_02, ...) e o
mapeamento fica registrado em `data/processed/<match_id>/match_meta.json`.

Uso:
    python -m scripts.process_all_demos              # todas as demos ainda não processadas
    python -m scripts.process_all_demos --force      # reprocessa tudo
"""
from __future__ import annotations

import argparse
import json
import time
import traceback
from pathlib import Path

from scripts import build_breakdown, build_insights, export_replay, export_web_payload
from scripts.process_demo import process

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEMOS_DIR = PROJECT_ROOT / "demos"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"


def find_demos() -> list[Path]:
    """Caminhos dos .dem em `demos/`.

    O FACEIT entrega cada demo dentro de uma pasta com o mesmo nome do arquivo,
    então aceitamos as duas formas (arquivo solto e arquivo dentro da pasta).
    """
    if not DEMOS_DIR.exists():
        return []
    found: list[Path] = []
    for entry in sorted(DEMOS_DIR.iterdir()):
        if entry.is_file() and entry.suffix == ".dem":
            found.append(entry)
        elif entry.is_dir():
            inner = entry / entry.name
            if inner.exists():
                found.append(inner)
            else:
                found.extend(sorted(entry.glob("*.dem")))
    return found


def already_processed() -> dict[str, str]:
    """match_id -> nome do .dem de origem, pras partidas já processadas."""
    out: dict[str, str] = {}
    if not PROCESSED_DIR.exists():
        return out
    for match_dir in sorted(PROCESSED_DIR.iterdir()):
        meta_path = match_dir / "match_meta.json"
        if meta_path.exists():
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            out[match_dir.name] = Path(meta.get("source_dem", "")).name
    return out


def build_chain(match_id: str) -> None:
    """Os passos que transformam métricas em página: ordem importa."""
    build_insights.build(match_id)
    build_breakdown.build(match_id)
    export_replay.build(match_id)
    export_web_payload.build(match_id)


def main() -> None:
    parser = argparse.ArgumentParser(description="Processa todas as demos da pasta demos/.")
    parser.add_argument("--force", action="store_true", help="reprocessa demos já processadas")
    args = parser.parse_args()

    demos = find_demos()
    if not demos:
        print(f"Nenhuma demo encontrada em {DEMOS_DIR}")
        return

    done = already_processed()
    by_source = {v: k for k, v in done.items()}
    next_index = len(done) + 1

    print(f"{len(demos)} demo(s) em demos/ · {len(done)} já processada(s)\n")

    for dem in demos:
        existing = by_source.get(dem.name)
        if existing and not args.force:
            print(f"[pular] {dem.name[:20]}... já processada como {existing}")
            continue

        match_id = existing or f"match_{next_index:02d}"
        if not existing:
            next_index += 1

        print(f"[{match_id}] {dem.name[:20]}...")
        t0 = time.time()
        try:
            process(dem, match_id, from_interim=False)
            build_chain(match_id)
            print(f"[{match_id}] ok em {time.time() - t0:.0f}s\n")
        except Exception:
            # uma demo corrompida não pode derrubar o lote inteiro
            print(f"[{match_id}] FALHOU:\n{traceback.format_exc()}\n")


if __name__ == "__main__":
    main()
