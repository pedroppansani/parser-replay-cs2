"""
O processamento é DETERMINÍSTICO: a mesma entrada dá a mesma saída, valor a
valor e na mesma ordem, em qualquer execução e em qualquer número de processos.

POR QUE ISTO É TESTE E NÃO CUIDADO
----------------------------------
Medido em 2026-09-21, antes da correção: duas execuções SEQUENCIAIS das mesmas
3 partidas diferiam em 38 arquivos. A causa era a ordem de hash do Polars --
`group_by` e `unique` devolvem os grupos numa ordem que muda a cada processo --,
e ela não ficava só na ordem das linhas: vazava para número de verdade sempre
que alguém cortava ou desempatava depois (`head`, `first`, `mode`,
`unique(subset=)`). Caso real: o card de estilo mostrava PerdYYY numa execução e
chiefkeef19 na outra. A mesma fonte faz a semente fixa do KMeans deixar de
garantir resultado, porque a semente só vale para a mesma ordem de linhas.

Depois da correção: seq x seq, paralelo x paralelo e seq x paralelo idênticos,
sem tolerância, nas 52 partidas (decisão 28 do CLAUDE.md).

Os testes daqui travam a CAUSA no código-fonte -- um `group_by` novo sem ordem
reabre o problema em silêncio, e o número continua plausível.
"""
from __future__ import annotations

import random
import re
from pathlib import Path

import polars as pl
import pytest

from metrics.player_profile import cards_de_estilo

RAIZ = Path(__file__).resolve().parent.parent
PASTAS = ["metrics", "scripts", "clustering", "parsing"]


def _fecha(texto: str, i: int) -> int:
    """Índice do ')' que fecha o '(' em texto[i], pulando strings e comentários."""
    prof, j = 0, i
    while j < len(texto):
        c = texto[j]
        if c in "\"'":
            q3 = texto[j:j + 3]
            if q3 in ('"""', "'''"):
                j = texto.index(q3, j + 3) + 3
                continue
            k = j + 1
            while texto[k] != c:
                k += 2 if texto[k] == "\\" else 1
            j = k + 1
            continue
        if c == "#":
            j = texto.index("\n", j)
            continue
        if c == "(":
            prof += 1
        elif c == ")":
            prof -= 1
            if prof == 0:
                return j
        j += 1
    raise ValueError("parêntese sem fechamento")


def _chamadas(nome: str):
    """(arquivo, linha, argumentos) de toda chamada `.nome(...)` do código do projeto."""
    padrao = re.compile(r"\." + nome + r"\(")
    for pasta in PASTAS:
        for arq in sorted((RAIZ / pasta).rglob("*.py")):
            texto = arq.read_text(encoding="utf-8")
            for m in padrao.finditer(texto):
                abre = m.end() - 1
                args = texto[abre + 1:_fecha(texto, abre)]
                linha = texto.count("\n", 0, m.start()) + 1
                yield f"{arq.relative_to(RAIZ).as_posix()}:{linha}", args


def test_todo_group_by_declara_a_ordem():
    """`group_by` sem `maintain_order=True` devolve os grupos em ordem de hash,
    diferente a cada processo. Reabriria as 38 diferenças entre execuções."""
    sem = [onde for onde, args in _chamadas("group_by") if "maintain_order" not in args]
    assert not sem, f"group_by sem maintain_order=True: {sem}"


def test_todo_unique_declara_a_ordem_e_qual_linha_fica():
    """`unique` tem os dois defeitos: ordem de hash e, com subset, `keep="any"`
    -- que não garante QUAL das linhas duplicadas sobra. Em site_roles isso
    escolhia a área do jogador; em grenades, qual linha de kill ficava."""
    sem_ordem = [onde for onde, args in _chamadas("unique") if "maintain_order" not in args]
    assert not sem_ordem, f"unique sem maintain_order=True: {sem_ordem}"
    # com argumento posicional ou subset, a linha que fica tem de ser declarada
    sem_keep = [onde for onde, args in _chamadas("unique")
                if args.replace("maintain_order=True", "").strip(" ,") and "keep=" not in args]
    assert not sem_keep, f"unique com subset e sem keep=: {sem_keep}"


def test_mode_nunca_desempata_ao_acaso():
    """`mode()` devolve TODAS as modas empatadas, em ordem não garantida, e
    `.first()` pegava uma qualquer. Uma delas era a classe de economia do
    jogador no rating (metrics/rating.py)."""
    ruins = []
    for pasta in PASTAS:
        for arq in sorted((RAIZ / pasta).rglob("*.py")):
            for n, linha in enumerate(arq.read_text(encoding="utf-8").splitlines(), 1):
                if ".mode().first()" in linha:
                    ruins.append(f"{arq.relative_to(RAIZ).as_posix()}:{n}")
    assert not ruins, f"mode().first() sem desempate (use .mode().sort().first()): {ruins}"


def test_o_detector_de_group_by_sem_ordem_funciona():
    """Controle: se o varredor não enxergasse chamada nenhuma, os testes acima
    passariam sem medir nada."""
    achadas = list(_chamadas("group_by"))
    assert len(achadas) > 100, len(achadas)


# --- o caso que tornou isso visível -----------------------------------------

def _atribuicoes(contagens: dict[tuple[int, str], int]) -> pl.DataFrame:
    """Uma linha por (jogador, round) no cluster, a partir de {(steamid, nome): n}."""
    linhas = []
    for (sid, nome), n_no_grupo in contagens.items():
        linhas += [{"steamid": sid, "name": nome, "round_num": r, "cluster": 0}
                   for r in range(n_no_grupo)]
        linhas += [{"steamid": sid, "name": nome, "round_num": 100 + r, "cluster": 1}
                   for r in range(17 - n_no_grupo)]
    return pl.DataFrame(linhas)


def test_empate_no_terceiro_lugar_do_card_entra_inteiro_e_nao_depende_da_ordem():
    """REGRESSÃO (match_05): PerdYYY e chiefkeef19 com 7 de 17 no mesmo grupo.
    Com `.head(3)` puro, quem aparecia dependia da ordem das linhas -- e ela
    mudava a cada execução. Empatado no corte entra; e a saída é a mesma para
    qualquer ordem de entrada."""
    contagens = {(1, "donk"): 12, (2, "sh1ro"): 9, (3, "PerdYYY"): 7, (4, "chiefkeef19"): 7, (5, "PR--"): 5}
    base = _atribuicoes(contagens)

    saidas = set()
    for semente in range(8):
        embaralhado = base.sample(fraction=1.0, shuffle=True, seed=semente)
        grupo0 = next(g for g in cards_de_estilo(embaralhado)["grupos"] if g["cluster"] == 0)
        saidas.add(tuple(j["name"] for j in grupo0["jogadores"]))
    assert len(saidas) == 1, f"a ordem da entrada mudou o card: {saidas}"
    (nomes,) = saidas
    assert nomes == ("donk", "sh1ro", "PerdYYY", "chiefkeef19"), nomes
    assert "PR--" not in nomes


def test_sem_empate_o_card_continua_com_tres():
    contagens = {(1, "a"): 12, (2, "b"): 9, (3, "c"): 7, (4, "d"): 6, (5, "e"): 5}
    grupo0 = next(g for g in cards_de_estilo(_atribuicoes(contagens))["grupos"] if g["cluster"] == 0)
    assert [j["name"] for j in grupo0["jogadores"]] == ["a", "b", "c"]


# --- o orquestrador ---------------------------------------------------------

def test_passo_de_corpus_nao_deixa_o_script_chamado_ler_os_argumentos_do_orquestrador(monkeypatch):
    """fit_global_clusters e fit_archetype_reference têm argparse no main().
    Chamados de dentro do reprocessa, leriam `--processos 4` e parariam."""
    from scripts import reprocessa

    monkeypatch.setattr(reprocessa, "LOGS_DIR", RAIZ / "logs" / "reprocessa-teste")
    monkeypatch.setattr("sys.argv", ["reprocessa", "--processos", "4"])
    visto = {}
    reprocessa._passo_de_corpus("sonda", lambda: visto.setdefault("argv", list(__import__("sys").argv)))
    assert visto["argv"] == ["sonda"]
    assert __import__("sys").argv == ["reprocessa", "--processos", "4"], "argv não foi restaurado"


def test_numero_de_processos_respeita_teto_e_minimo():
    from scripts import reprocessa

    n = reprocessa.processos_padrao()
    assert 1 <= n <= reprocessa.MAX_PROCESSOS
