"""A referência de escala do rating se reproduz (cartão 13).

O `metrics/rating_reference.json` versionado tinha vindo de um estado que não dava
mais para refazer: rodar o `fit_rating` dava outro arquivo, diferente no último bit.
Estes testes prendem o gerador ao arquivo (regra 28 do CLAUDE.md).

- No Windows (a máquina do Pedro, onde a referência é gerada) a comparação é byte a
  byte. No CI (Linux) o modelo de round sai diferente no último bit (álgebra linear
  do sistema; medido em 2026-10-24: diferença relativa máxima de 6,8e-14 na
  fixture), e a comparação usa `TOLERANCIA_RELATIVA_NO_CI`.
- No CI não há o interim inteiro: o teste roda sobre a fixture de duas partidas e
  compara com `tests/fixtures/rating_reference_fixture_ci.json`.
- Com o interim na máquina, o teste compara o corpus inteiro com o versionado.

Para regravar depois de uma mudança deliberada, no Windows: `py -3.12 -m
scripts.fit_rating` (o do corpus) e `texto_da_referencia(PARTIDAS, DESTINO)` (o da fixture).
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import pytest

from metrics.rating import REFERENCIA_FILE
from scripts.fit_rating import partidas_disponiveis, texto_da_referencia
from scripts.gera_fixture_ci import DESTINO, PARTIDAS

RAIZ = Path(__file__).resolve().parent.parent
INTERIM_REAL = RAIZ / "data" / "interim"
ESPERADO_NA_FIXTURE = RAIZ / "tests" / "fixtures" / "rating_reference_fixture_ci.json"
# Cartão 13, resposta do Pedro: fora do Windows, tolerância relativa bem pequena (medido: 6,8e-14).
TOLERANCIA_RELATIVA_NO_CI = 1e-12


def _folhas(x, caminho=""):
    if isinstance(x, dict):
        for k, v in x.items():
            yield from _folhas(v, f"{caminho}/{k}")
    elif isinstance(x, list):
        for i, v in enumerate(x):
            yield from _folhas(v, f"{caminho}[{i}]")
    else:
        yield caminho, x


def _confere(gerado: str, esperado: str) -> None:
    if sys.platform == "win32":
        assert gerado == esperado
        return
    a, b = dict(_folhas(json.loads(esperado))), dict(_folhas(json.loads(gerado)))
    assert a.keys() == b.keys()
    fora = [
        (k, a[k], b[k]) for k in a
        if not (a[k] == b[k] or (isinstance(a[k], float) and isinstance(b[k], float)
                                 and math.isclose(a[k], b[k], rel_tol=TOLERANCIA_RELATIVA_NO_CI)))
    ]
    assert not fora, fora


def test_a_referencia_da_fixture_se_reproduz():
    _confere(texto_da_referencia(sorted(PARTIDAS), DESTINO) + "\n",
             ESPERADO_NA_FIXTURE.read_text(encoding="utf-8"))


# sem partida nenhuma (o CI não tem o interim) o all() daria True: a lista vazia também pula
_PARTIDAS_DO_CORPUS = partidas_disponiveis()


@pytest.mark.skipif(
    not _PARTIDAS_DO_CORPUS or not all((INTERIM_REAL / m).is_dir() for m in _PARTIDAS_DO_CORPUS),
    reason="sem o interim do corpus inteiro (o CI usa a fixture)",
)
def test_a_referencia_do_corpus_se_reproduz():
    _confere(texto_da_referencia(_PARTIDAS_DO_CORPUS), REFERENCIA_FILE.read_text(encoding="utf-8"))


def test_a_tolerancia_do_ci_aceita_o_ultimo_bit_e_pega_mudanca_de_verdade(monkeypatch):
    """Controle: sem ele, uma tolerância larga demais passaria calada."""
    monkeypatch.setattr(sys, "platform", "linux")
    base = {"medias": {"kast": 0.7191349025535313}, "n_partidas": 52}
    texto = json.dumps(base)
    _confere(json.dumps({**base, "medias": {"kast": 0.7191349025535313 * (1 + 7e-14)}}), texto)
    with pytest.raises(AssertionError):
        _confere(json.dumps({**base, "medias": {"kast": 0.7191349025535313 * (1 + 1e-9)}}), texto)
    with pytest.raises(AssertionError):
        _confere(json.dumps({**base, "n_partidas": 51}), texto)
