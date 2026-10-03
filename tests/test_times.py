"""Nenhum time aparece com dois nomes no corpus (metrics/times.py)."""
from __future__ import annotations

import json
import re
from pathlib import Path

from metrics.times import chave_de_semelhanca, nome_canonico

RAIZ = Path(__file__).resolve().parent.parent


def _nomes_profissionais() -> set[str]:
    partidas = json.loads((RAIZ / "data" / "manifest.json").read_text(encoding="utf-8"))["partidas"]
    return {t["nome"] for p in partidas.values() if p.get("origem") == "profissional"
            for t in (p.get("times") or {}).values() if t.get("nome")}


def test_nome_canonico_junta_as_variantes_conhecidas():
    assert nome_canonico("Team Vitality") == nome_canonico("Vitality") == "Vitality"
    assert nome_canonico("Team Falcons") == nome_canonico("Falcons") == "Falcons"
    assert nome_canonico("MOUZ") == "MOUZ" and nome_canonico(None) == ""
    # só o que está na tabela muda: "Team Liquid" não vira "Liquid" por adivinhação
    assert nome_canonico("Team Liquid") == "Team Liquid"


def test_nenhum_time_aparece_com_dois_nomes_no_corpus():
    """Dois nomes canônicos que se reduzem à mesma chave são o mesmo time
    escrito de dois jeitos, ainda fora da tabela."""
    por_chave: dict[str, set[str]] = {}
    for nome in _nomes_profissionais():
        por_chave.setdefault(chave_de_semelhanca(nome_canonico(nome)), set()).add(nome_canonico(nome))
    duplicados = {k: sorted(v) for k, v in por_chave.items() if len(v) > 1}
    assert not duplicados, f"registre em data/reference/times_conhecidos.json: {duplicados}"


def test_a_contagem_de_times_citada_usa_o_nome_canonico():
    from scripts.numeros_citaveis import corpus
    assert corpus()["times_profissionais"] == len({nome_canonico(n) for n in _nomes_profissionais()})


def test_ninguem_normaliza_nome_de_time_por_conta_propria():
    """A regra mora em metrics/times.py; cópias divergem na primeira correção."""
    padrao = re.compile(r"removeprefix\(.Team .\)|startswith\(.team .\)")
    achados = []
    for pasta in ("metrics", "scripts", "parsing", "clustering"):
        for f in sorted((RAIZ / pasta).rglob("*.py")):
            if f.name != "times.py" and padrao.search(f.read_text(encoding="utf-8")):
                achados.append(f.relative_to(RAIZ).as_posix())
    assert not achados, achados
