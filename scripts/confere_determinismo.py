"""Roda o cálculo de UMA partida e da tabela de economia numa pasta isolada.

É o executável do teste de determinismo em dois processos
(tests/test_determinismo_em_processos.py): o teste o chama duas vezes, cada uma
num processo próprio e com um PYTHONHASHSEED diferente, e compara os arquivos
byte a byte. Rodar duas vezes NO MESMO processo não prova nada -- a ordem de
hash das strings é fixa dentro de um processo.

A partida é lida de `<raiz>/data/interim/<partida>` e gravada em
`<raiz>/data/processed/<partida>`: nada do projeto é tocado.

Uso (pelo teste):
    py -3.12 -m scripts.confere_determinismo <raiz> <partida>
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))


def roda(raiz: Path, partida: str) -> None:
    import leitura.insights as insights
    import scripts.process_demo as processo
    from metrics.economia import ajusta_tabela
    from scripts.fit_economia import confrontos_do_corpus

    # a partida inteira: métricas (parquet) e a leitura da partida (insights.json)
    processo.PROJECT_ROOT = raiz
    insights.PROJECT_ROOT = raiz
    processo.process(Path(f"{partida}.dem"), partida, from_interim=True)
    insights.build(partida)
    # a tabela de economia do corpus (lê o interim de verdade)
    (raiz / "economia.json").write_text(
        json.dumps(ajusta_tabela(confrontos_do_corpus()), ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    roda(Path(sys.argv[1]), sys.argv[2])
