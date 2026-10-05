"""O round inteiro no hash da prancheta (fase 9, item 9.3). Não muda nada.

A prancheta recebe o round como recebe o instante hoje: na URL (#round=...),
para funcionar igual no arquivo local e no Pages, sem servidor. O documento da
fase 9 põe o limite em 150 KB no hash e manda medir o MAIOR round do corpus
depois da simplificação, compactado (deflate, como o CompressionStream do
navegador, que usa o formato zlib) e em base64url.

Para cada tolerância do Douglas-Peucker (unidades do jogo), mede:
  - o erro de posição contra o replay: em cada amostra (4 por segundo) de
    jogador vivo, a distância entre a posição gravada e a do caminho
    simplificado no mesmo horário (interpolação linear entre os pontos que
    ficaram);
  - o tamanho do round no hash: JSON compacto -> zlib (nível 6, o padrão) ->
    base64url sem preenchimento.

Uso:
    py -3.12 -m pesquisa.round_no_hash
"""
from __future__ import annotations

import json
import math
import sys
import zlib
from pathlib import Path

import numpy as np

from metrics.round_na_prancheta import TOLERANCIAS_U, payload_do_round, posicao_no_caminho

RAIZ = Path(__file__).resolve().parents[1]
PROCESSED = RAIZ / "data" / "processed"
LIMITE_HASH_BYTES = 150 * 1024


def tamanho_no_hash(payload: dict) -> int:
    bruto = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return math.ceil(len(zlib.compress(bruto, 6)) * 4 / 3)


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    replays = sorted(PROCESSED.glob("*/replay.json"))
    print(f"{len(replays)} partidas\n")
    print("| tolerância (u) | erro p50 (u) | erro p95 (u) | erro máx (u) | pontos por jogador (mediana / máx) | maior round no hash (KB) | mediana (KB) | qual |")
    print("|---|---|---|---|---|---|---|---|")
    for tol in TOLERANCIAS_U:
        erros, tamanhos, npts = [], [], []
        for f in replays:
            rep = json.loads(f.read_text(encoding="utf-8"))
            for rd in rep["rounds"]:
                pl = payload_do_round(rep, rd, tol, f.parent.name)
                tamanhos.append((tamanho_no_hash(pl), f"{f.parent.name} r{rd['round']}"))
                for j, p in zip(pl["jogadores"], rd["players"]):
                    npts.append(len(j["pontos"]))
                    for i, (x, y, v) in enumerate(zip(p["x"], p["y"], p["alive"])):
                        if not v:
                            continue
                        q = posicao_no_caminho(j["pontos"], i)
                        if q is not None:
                            erros.append(math.hypot(q[0] - x, q[1] - y))
        e = np.array(erros)
        maior = max(tamanhos)
        med = float(np.median([t for t, _ in tamanhos]))
        print(f"| {tol} | {np.percentile(e, 50):.1f} | {np.percentile(e, 95):.1f} | {e.max():.1f} | "
              f"{np.median(npts):.0f} / {max(npts)} | "
              f"{maior[0] / 1024:.1f} | {med / 1024:.1f} | {maior[1]} |")
    print(f"\nlimite do documento: {LIMITE_HASH_BYTES / 1024:.0f} KB")


if __name__ == "__main__":
    main()
