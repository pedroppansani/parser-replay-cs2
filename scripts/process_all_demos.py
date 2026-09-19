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
import re
import shutil
import time
import traceback
from pathlib import Path

from parsing.parser import merge_interim, parse_demo, save_interim
from scripts import build_breakdown, build_insights, export_replay, export_web_payload, manifest
from scripts.process_demo import process

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEMOS_DIR = PROJECT_ROOT / "demos"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
INTERIM_DIR = PROJECT_ROOT / "data" / "interim"


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


# Demo dividida pelo GOTV quando o servidor reinicia no meio do mapa: o mesmo
# mapa vira "...-p1.dem" e "...-p2.dem". Na prática as partes podem nem estar na
# mesma pasta -- extrair a série do zip para "X", "X - Copia" e "X - Copia (2)"
# é comum no Windows, e foi exatamente assim que o Overpass de FURIA x Vitality
# chegou (p2 numa pasta, p1 na cópia). Por isso a chave de agrupamento ignora o
# sufixo de cópia da pasta.
_SUFIXO_COPIA = re.compile(r"\s+-\s+(copia|cópia|copy)(\s*\(\d+\))?$|\s+\(\d+\)$", re.IGNORECASE)
_PARTE = re.compile(r"-p(\d+)\.dem$", re.IGNORECASE)


def group_demos(demos: list[Path]) -> list[list[Path]]:
    """Agrupa as partes de uma demo dividida; demo inteira vira grupo de um.

    A ordem do grupo é a ordem das partes (p1, p2...), que é a ordem em que a
    fusão empilha os rounds.
    """
    grupos: dict[tuple, list[tuple[int, Path]]] = {}
    ordem: list[tuple] = []
    for dem in demos:
        parte = _PARTE.search(dem.name)
        if parte is None:
            chave = ("inteira", str(dem))
            numero = 0
        else:
            pasta = _SUFIXO_COPIA.sub("", dem.parent.name)
            chave = ("dividida", pasta, dem.name[: parte.start()])
            numero = int(parte.group(1))
        if chave not in grupos:
            grupos[chave] = []
            ordem.append(chave)
        grupos[chave].append((numero, dem))
    return [[d for _, d in sorted(grupos[c], key=lambda x: x[0])] for c in ordem]


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
        # partida fundida: cada parte conta como já processada
        for fp_parte in meta.get("source_fingerprints") or []:
            out.setdefault(fp_parte, match_dir.name)
        fp = meta.get("source_fingerprint")
        if not fp:
            src = Path(meta.get("source_dem", ""))
            if src.is_file():
                fp = fingerprint(src)
        if fp and fp not in out:
            out[fp] = match_dir.name
    return out


def next_match_index() -> int:
    """Próximo número livre, a partir do MAIOR id existente -- não da contagem.

    Pela contagem, remover uma partida (a duplicata, uma metade fundida) fazia o
    próximo id cair num que já existe, e a demo nova SOBRESCREVIA outra partida.
    """
    numeros = [
        int(p.name.split("_")[1])
        for p in (PROCESSED_DIR.glob("match_*") if PROCESSED_DIR.exists() else [])
        if p.is_dir() and p.name.split("_")[1].isdigit()
    ]
    return max(numeros, default=0) + 1


def record_fingerprint(match_id: str, fp: str, parts: list[Path] | None = None,
                       part_fps: list[str] | None = None) -> None:
    meta_path = PROCESSED_DIR / match_id / "match_meta.json"
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    meta["source_fingerprint"] = fp
    if parts and len(parts) > 1:
        meta["source_parts"] = [str(p) for p in parts]
        meta["source_fingerprints"] = part_fps
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")


def process_split(parts: list[Path], match_id: str) -> None:
    """Parseia cada parte num interim temporário, funde e processa o resultado."""
    temporarios = []
    for i, parte in enumerate(parts, start=1):
        tmp = f"{match_id}__parte{i}"
        save_interim(parse_demo(parte), INTERIM_DIR, tmp)
        temporarios.append(tmp)
    merge_interim(INTERIM_DIR, temporarios, match_id)
    for tmp in temporarios:
        shutil.rmtree(INTERIM_DIR / tmp)
    process(parts[0], match_id, from_interim=True)


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
    next_index = next_match_index()

    print(f"{len(demos)} demo(s) em demos/ · {len(set(by_fp.values()))} partida(s) já processada(s)\n")

    seen_this_run: set[str] = set()
    for grupo in group_demos(demos):
        # duplicata real (mesmo conteúdo) sai antes de qualquer outra decisão;
        # dentro de uma demo dividida, também descarta a mesma parte repetida
        partes, fps = [], []
        for dem in grupo:
            fp_dem = fingerprint(dem)
            if fp_dem in seen_this_run:
                print(f"[duplicada] {dem.parent.name[:40]}... mesmo conteúdo de outra demo deste lote, pulando")
                continue
            seen_this_run.add(fp_dem)
            partes.append(dem)
            fps.append(fp_dem)
        if not partes:
            continue

        # identidade da partida fundida = as partes, em ordem
        fp = fps[0] if len(fps) == 1 else hashlib.sha256("|".join(fps).encode()).hexdigest()[:20]
        existing = by_fp.get(fp) or next((by_fp[f] for f in fps if f in by_fp), None)
        if existing and not args.force:
            print(f"[pular] {partes[0].name[:20]}... já processada como {existing}")
            continue

        match_id = existing or f"match_{next_index:02d}"
        if not existing:
            next_index += 1

        rotulo = partes[0].name[:20] + (f"... ({len(partes)} partes fundidas)" if len(partes) > 1 else "...")
        print(f"[{match_id}] {rotulo}")
        t0 = time.time()
        try:
            if len(partes) > 1:
                process_split(partes, match_id)
            else:
                process(partes[0], match_id, from_interim=False)
            record_fingerprint(match_id, fp, partes, fps)
            by_fp[fp] = match_id
            for f in fps:
                by_fp[f] = match_id
            build_chain(match_id)
            # Registro de origem ANTES de a demo poder ser apagada: times,
            # evento, hash do arquivo inteiro (scripts/manifest.py).
            manifest.atualiza([match_id])
            print(f"[{match_id}] ok em {time.time() - t0:.0f}s\n")
        except Exception:
            # uma demo corrompida não pode derrubar o lote inteiro
            print(f"[{match_id}] FALHOU:\n{traceback.format_exc()}\n")


if __name__ == "__main__":
    main()
