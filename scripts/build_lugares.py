"""
Tabela de NOMES DE LUGAR por mapa, para o roteiro da prancheta (fase 8, 8.5).

Mesma lógica de scripts/build_lineups.py: a tabela sai dos ticks de
`data/interim/` (que não vai para o git), então é gerada AQUI e gravada em
`data/lugares/<mapa>.json`; o build da prancheta só lê o arquivo. A regra está
em metrics/lugares.py.

Uso:
    py -3.12 -m scripts.build_lugares            # grava
    py -3.12 -m scripts.build_lugares --tabela   # só a medição, em markdown
"""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from metrics.lugares import (  # noqa: E402
    LADOS_DA_CELULA, LIMITE_BYTES, MIN_PARTIDAS, PASSO_TICKS, acerto, amostras, grade, tabela_compacta,
)

INTERIM = PROJECT_ROOT / "data" / "interim"
MANIFESTO = PROJECT_ROOT / "data" / "manifest.json"
RADARS = PROJECT_ROOT / "assets" / "radars"
SAIDA = PROJECT_ROOT / "data" / "lugares"


def compacto(obj) -> str:
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":"))


def medicao(partidas: list[str], mapa: str) -> list[dict]:
    """Por lado da célula: células, peso e acerto fora da amostra (as partidas
    de índice par montam a tabela, as de índice ímpar conferem)."""
    radar = json.loads((RADARS / f"{mapa}.json").read_text(encoding="utf-8"))
    por = {p: amostras(INTERIM / p / "ticks.parquet", radar, mapa) for p in partidas}
    treino = [a for i, p in enumerate(partidas) if i % 2 == 0 for a in por[p]]
    teste = [a for i, p in enumerate(partidas) if i % 2 == 1 for a in por[p]]
    out = []
    for lado in LADOS_DA_CELULA:
        tab = tabela_compacta(grade(treino + teste, lado), lado)
        out.append({"lado": lado, "bytes": len(compacto(tab).encode("utf-8")),
                    "acerto": acerto(treino, teste, lado) if teste else None,
                    "amostras_teste": len(teste), "tabela": tab})
    return out


def escolhe(linhas: list[dict]) -> dict | None:
    """O lado de maior acerto fora da amostra entre os que cabem no limite
    (acerto arredondado a 3 casas; empate: a célula maior, a tabela menor)."""
    cabem = [l for l in linhas if l["bytes"] <= LIMITE_BYTES and l["acerto"] is not None]
    return max(cabem, key=lambda l: (round(l["acerto"], 3), l["lado"])) if cabem else None


def partidas_por_mapa() -> dict[str, list[str]]:
    man = json.loads(MANIFESTO.read_text(encoding="utf-8"))["partidas"]
    por = defaultdict(list)
    for m, v in sorted(man.items()):
        if (INTERIM / m / "ticks.parquet").exists():
            por[v["mapa"]].append(m)
    return dict(por)


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    so_tabela = "--tabela" in sys.argv
    SAIDA.mkdir(parents=True, exist_ok=True)
    if so_tabela:
        print("| mapa | partidas | lado (px) | peso (KB) | acerto fora da amostra | escolhido |")
        print("|---|---|---|---|---|---|")
    for mapa, partidas in sorted(partidas_por_mapa().items()):
        destino = SAIDA / f"{mapa}.json"
        if len(partidas) < MIN_PARTIDAS:
            if so_tabela:
                print(f"| {mapa} | {len(partidas)} | — | — | sem medida | sem tabela |")
            else:
                print(f"{mapa}: {len(partidas)} partida(s), sem medida fora da amostra -- sem tabela")
            continue
        linhas = medicao(partidas, mapa)
        esc = escolhe(linhas)
        if so_tabela:
            for l in linhas:
                print(f"| {mapa} | {len(partidas)} | {l['lado']} | {l['bytes'] / 1024:.1f} | {l['acerto']:.3f} | "
                      f"{'sim' if esc is l else ''} |")
            continue
        if esc is None:
            print(f"{mapa}: nenhum lado cabe em {LIMITE_BYTES} bytes -- sem tabela")
            continue
        doc = dict(esc["tabela"], origem={
            "fonte": "campo place dos ticks do corpus", "partidas": len(partidas),
            "acerto_fora_da_amostra": round(esc["acerto"], 4), "amostras_teste": esc["amostras_teste"],
            "passo_ticks": PASSO_TICKS, "regra": "metrics/lugares.py"})
        destino.write_text(compacto(doc) + "\n", encoding="utf-8")
        print(f"{mapa}: lado {esc['lado']} px, {esc['bytes'] / 1024:.1f} KB, acerto {esc['acerto']:.3f} "
              f"({len(partidas)} partidas)")


if __name__ == "__main__":
    main()
