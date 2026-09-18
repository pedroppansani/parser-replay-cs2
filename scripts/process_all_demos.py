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
import hashlib
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


# A identidade de uma demo é o CONTEÚDO, não o nome do arquivo. Uma cópia do
# Windows ("... - Copia") tem o mesmo nome em outra pasta; uma demo renomeada tem
# outro nome e o mesmo conteúdo. Pelo nome, as duas viravam partidas diferentes
# -- foi assim que match_24 nasceu como réplica exata de match_23.
#
# Hashear 300MB inteiros a cada execução é desperdício: tamanho + começo + fim
# já distingue qualquer par real de demos (o cabeçalho traz servidor e mapa, e o
# final traz o placar). Colisão exigiria duas partidas diferentes com o mesmo
# tamanho exato em bytes e os mesmos 8MB nas pontas.
FINGERPRINT_EDGE_BYTES = 4 * 1024 * 1024


def fingerprint(dem: Path) -> str:
    size = dem.stat().st_size
    h = hashlib.sha256(str(size).encode())
    with dem.open("rb") as f:
        h.update(f.read(FINGERPRINT_EDGE_BYTES))
        if size > 2 * FINGERPRINT_EDGE_BYTES:
            f.seek(-FINGERPRINT_EDGE_BYTES, 2)
            h.update(f.read(FINGERPRINT_EDGE_BYTES))
    return h.hexdigest()[:20]


def already_processed() -> dict[str, str]:
    """impressão digital da demo -> match_id, pras partidas já processadas.

    Partidas antigas não têm a impressão gravada no meta; nesse caso ela é
    calculada a partir do `source_dem`, se o arquivo ainda existir.
    """
    out: dict[str, str] = {}
    if not PROCESSED_DIR.exists():
        return out
    for match_dir in sorted(PROCESSED_DIR.iterdir()):
        meta_path = match_dir / "match_meta.json"
        if not meta_path.exists():
            continue
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        fp = meta.get("source_fingerprint")
        if not fp:
            src = Path(meta.get("source_dem", ""))
            if src.is_file():
                fp = fingerprint(src)
        if fp and fp not in out:
            out[fp] = match_dir.name
    return out


def record_fingerprint(match_id: str, fp: str) -> None:
    meta_path = PROCESSED_DIR / match_id / "match_meta.json"
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    meta["source_fingerprint"] = fp
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")


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

    by_fp = already_processed()
    existing_ids = {p.name for p in PROCESSED_DIR.iterdir() if p.is_dir()} if PROCESSED_DIR.exists() else set()
    next_index = len(existing_ids) + 1

    print(f"{len(demos)} demo(s) em demos/ · {len(by_fp)} já processada(s)\n")

    seen_this_run: set[str] = set()
    for dem in demos:
        fp = fingerprint(dem)
        if fp in seen_this_run:
            print(f"[duplicada] {dem.parent.name[:40]}... mesmo conteúdo de outra demo deste lote, pulando")
            continue
        seen_this_run.add(fp)

        existing = by_fp.get(fp)
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
            record_fingerprint(match_id, fp)
            by_fp[fp] = match_id
            build_chain(match_id)
            print(f"[{match_id}] ok em {time.time() - t0:.0f}s\n")
        except Exception:
            # uma demo corrompida não pode derrubar o lote inteiro
            print(f"[{match_id}] FALHOU:\n{traceback.format_exc()}\n")


if __name__ == "__main__":
    main()
