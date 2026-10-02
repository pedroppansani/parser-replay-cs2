"""Determinismo ENTRE PROCESSOS (decisão 28), com a ordem de hash trocada.

POR QUE EXISTE (2026-10-02): a tabela de economia do rating foi gravada com um
desempate ao acaso e ficou duas semanas no repositório sem nenhum teste acusar.
Os testes de `test_determinismo.py` travam a causa no CÓDIGO-FONTE (group_by e
unique com ordem, mode com sort) e rodam tudo no mesmo processo, onde a ordem
de hash é fixa; e nenhum conferia que um arquivo de referência gravado é o que
o código produz.

Aqui o cálculo de uma partida inteira e o da tabela de economia rodam em DOIS
processos, com PYTHONHASHSEED diferente, e os arquivos são comparados byte a
byte. Pulado sem `data/interim/`.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
PARTIDA = "match_23"
SEMENTES = ("1", "20261002")
# o que muda de propósito entre duas execuções: o carimbo de quando rodou
CAMPOS_VOLATEIS = ("processado_em",)


@pytest.fixture(scope="module")
def execucoes(tmp_path_factory):
    interim = RAIZ / "data" / "interim" / PARTIDA
    if not (interim / "ticks.parquet").exists():
        pytest.skip("sem o interim da match_23")
    pastas = []
    for semente in SEMENTES:
        raiz = tmp_path_factory.mktemp(f"hash_{semente}")
        shutil.copytree(interim, raiz / "data" / "interim" / PARTIDA)
        # o match_meta existente carrega campos que o processamento preserva
        (raiz / "data" / "processed" / PARTIDA).mkdir(parents=True)
        r = subprocess.run([sys.executable, "-m", "scripts.confere_determinismo", str(raiz), PARTIDA],
                           cwd=RAIZ, capture_output=True, text=True, encoding="utf-8", errors="replace",
                           env={**os.environ, "PYTHONHASHSEED": semente, "PYTHONIOENCODING": "utf-8"})
        assert r.returncode == 0, r.stderr[-2000:]
        pastas.append(raiz)
    return pastas


def _arquivos(raiz: Path) -> dict[str, Path]:
    saida = raiz / "data" / "processed" / PARTIDA
    out = {f.name: f for f in sorted(saida.iterdir()) if f.is_file()}
    out["economia.json"] = raiz / "economia.json"
    return out


def _bytes(arq: Path) -> bytes:
    if arq.name == "match_meta.json":
        d = json.loads(arq.read_text(encoding="utf-8"))
        for c in CAMPOS_VOLATEIS:
            d.pop(c, None)
        return json.dumps(d, sort_keys=True, ensure_ascii=False).encode("utf-8")
    return arq.read_bytes()


def test_dois_processos_com_hash_diferente_dao_os_mesmos_arquivos(execucoes):
    a, b = (_arquivos(r) for r in execucoes)
    assert set(a) == set(b)
    assert len(a) > 30, f"só {len(a)} arquivos: o cálculo da partida não rodou inteiro"
    assert "insights.json" in a and "economia.json" in a
    diferentes = [nome for nome in a if _bytes(a[nome]) != _bytes(b[nome])]
    assert not diferentes, f"arquivos que mudam com a ordem de hash: {diferentes}"
