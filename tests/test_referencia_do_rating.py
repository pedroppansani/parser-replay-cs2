"""A referência de escala do rating se reproduz (cartão 13).

O `metrics/rating_reference.json` versionado tinha vindo de um estado que não dava
mais para refazer: rodar o `fit_rating` dava outro arquivo, diferente no último bit.
Estes testes prendem o gerador ao arquivo: qualquer diferença, inclusive no último
bit, quebra (regra 28 do CLAUDE.md).

- No CI não há o interim inteiro: o teste roda sobre a fixture de duas partidas e
  compara com `tests/fixtures/rating_reference_fixture_ci.json`.
- Com o interim na máquina, o teste compara o corpus inteiro com o versionado.

Para regravar depois de uma mudança deliberada: `py -3.12 -m scripts.fit_rating`
(o do corpus) e o `texto_da_referencia(PARTIDAS, DESTINO)` (o da fixture).
"""
from __future__ import annotations

from pathlib import Path

import pytest

from metrics.rating import REFERENCIA_FILE
from scripts.fit_rating import partidas_disponiveis, texto_da_referencia
from scripts.gera_fixture_ci import DESTINO, PARTIDAS

RAIZ = Path(__file__).resolve().parent.parent
INTERIM_REAL = RAIZ / "data" / "interim"
ESPERADO_NA_FIXTURE = RAIZ / "tests" / "fixtures" / "rating_reference_fixture_ci.json"


def test_a_referencia_da_fixture_se_reproduz_byte_a_byte():
    esperado = ESPERADO_NA_FIXTURE.read_text(encoding="utf-8")
    assert texto_da_referencia(sorted(PARTIDAS), DESTINO) + "\n" == esperado

