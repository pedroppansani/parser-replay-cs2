"""P1d: a divisão do job `test` do CI em fatias (scripts/ci_fatias.py). A soma das fatias tem que ser EXATAMENTE a suíte inteira: nenhum arquivo de teste
fica de fora e nenhum roda duas vezes, inclusive com arquivo novo sem duração medida, duração velha ou arquivo de durações ausente."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from scripts.ci_fatias import RAIZ, arquivos_de_teste, carrega_duracoes, duracoes_do_log, reparte

TOTAL = 2          # quantas máquinas o workflow usa


def _confere(fatias, arquivos):
    todos = [a for f in fatias for a in f]
    assert sorted(todos) == sorted(set(arquivos)), "a união das fatias não é a lista de arquivos"
    assert len(todos) == len(set(todos)), "um arquivo caiu em duas fatias"


def _coletados_pelo_pytest() -> list[str]:
    """Os arquivos que o PRÓPRIO pytest coleta (`--collect-only -q`: uma linha `arquivo::teste` por teste), com a configuração do projeto."""
    r = subprocess.run([sys.executable, "-m", "pytest", "--collect-only", "-q", "-p", "no:cacheprovider"], cwd=RAIZ, capture_output=True, text=True, timeout=300)
    assert r.returncode == 0, r.stdout[-800:] + r.stderr[-800:]
    return sorted({linha.split("::")[0].removeprefix("./").replace("\\", "/") for linha in r.stdout.splitlines() if "::" in linha})


def test_a_lista_de_arquivos_e_a_que_o_pytest_coleta():
    """Se alguém criar `pytest.ini`/`testpaths`/`python_files` ou um teste fora de `tests/`, a divisão deixaria de rodar arquivos: este teste acusa."""
    coletados, nossa = _coletados_pelo_pytest(), arquivos_de_teste()
    assert [a for a in coletados if a not in nossa] == [], "o pytest coleta arquivos que a divisão não vê (ficariam de fora do CI)"
    assert [a for a in nossa if a not in coletados] == [], "a divisão lista arquivos de onde o pytest não coleta nenhum teste"


def test_a_uniao_das_fatias_e_exatamente_a_suite_inteira():
    arquivos = arquivos_de_teste()
    assert len(arquivos) > 100 and "tests/test_ci_fatias.py" in arquivos
    fatias = reparte(arquivos, carrega_duracoes(), TOTAL)
    _confere(fatias, arquivos)
    _confere(fatias, _coletados_pelo_pytest())             # e é a coleta do pytest, não só o padrão tests/**/test_*.py
    assert all(fatias), "uma fatia ficou vazia"


@pytest.mark.parametrize("n", [1, 2, 3, 5])
def test_qualquer_numero_de_fatias_cobre_a_suite_sem_repetir(n):
    arquivos = arquivos_de_teste()
    _confere(reparte(arquivos, carrega_duracoes(), n), arquivos)


def test_arquivo_novo_sem_duracao_vai_para_a_fatia_com_menos_carga_e_nao_some():
    duracoes = {"tests/a.py": 100.0, "tests/b.py": 10.0, "tests/c.py": 10.0}
    fatias = reparte(["tests/a.py", "tests/b.py", "tests/c.py", "tests/novo.py"], duracoes, 2)
    _confere(fatias, ["tests/a.py", "tests/b.py", "tests/c.py", "tests/novo.py"])
    assert fatias[0] == ["tests/a.py"]                                    # a mais pesada sozinha
    assert fatias[1] == ["tests/b.py", "tests/c.py", "tests/novo.py"]     # a mais leve recebe o novo
    # e no corpus de verdade, com um arquivo inventado
    arquivos = arquivos_de_teste() + ["tests/test_um_arquivo_novo_sem_duracao.py"]
    fatias = reparte(arquivos, carrega_duracoes(), TOTAL)
    _confere(fatias, arquivos)
    assert sum("tests/test_um_arquivo_novo_sem_duracao.py" in f for f in fatias) == 1


def test_varios_arquivos_novos_se_espalham_pela_mediana_em_vez_de_cair_todos_na_mesma_fatia():
    duracoes = {"tests/a.py": 10.0, "tests/b.py": 10.0}
    novos = [f"tests/novo{i}.py" for i in range(6)]
    fatias = reparte(["tests/a.py", "tests/b.py"] + novos, duracoes, 2)
    _confere(fatias, ["tests/a.py", "tests/b.py"] + novos)
    assert abs(len(fatias[0]) - len(fatias[1])) <= 1


def test_duracao_velha_ou_de_arquivo_que_sumiu_nao_tira_nem_poe_teste():
    arquivos = ["tests/a.py", "tests/b.py"]
    duracoes = {"tests/a.py": 5.0, "tests/b.py": 1.0, "tests/apagado.py": 9999.0}      # o apagado nao existe mais
    fatias = reparte(arquivos, duracoes, 2)
    _confere(fatias, arquivos)
    assert "tests/apagado.py" not in [a for f in fatias for a in f]


def test_sem_arquivo_de_duracoes_ou_com_lixo_a_divisao_continua_exata(tmp_path):
    assert carrega_duracoes(tmp_path / "nao_existe.json") == {}
    ruim = tmp_path / "ruim.json"
    ruim.write_text("isto não é json", encoding="utf-8")
    assert carrega_duracoes(ruim) == {}
    estranho = tmp_path / "estranho.json"
    estranho.write_text(json.dumps({"segundos": {"tests/a.py": "muito", "tests/b.py": -3, "tests/c.py": 4, "tests/d.py": True}}), encoding="utf-8")
    assert carrega_duracoes(estranho) == {"tests/c.py": 4.0}                 # só número não negativo vale
    arquivos = arquivos_de_teste()
    _confere(reparte(arquivos, {}, TOTAL), arquivos)


def test_a_divisao_e_deterministica_e_nao_depende_da_ordem_da_lista():
    arquivos = arquivos_de_teste()
    d = carrega_duracoes()
    assert reparte(arquivos, d, TOTAL) == reparte(list(reversed(arquivos)), d, TOTAL) == reparte(arquivos, d, TOTAL)


def test_as_fatias_do_corpus_ficam_equilibradas():
    d = carrega_duracoes()
    if not d:
        pytest.skip("sem durações medidas")
    arquivos = arquivos_de_teste()
    cargas = [sum(d.get(a, 0.0) for a in f) for f in reparte(arquivos, d, TOTAL)]
    assert max(cargas) <= 1.25 * min(cargas), f"fatias tortas: {cargas}"


def test_a_linha_de_comando_imprime_as_fatias_e_recusa_pedido_torto():
    def roda(*args):
        return subprocess.run([sys.executable, "-m", "scripts.ci_fatias", *args], cwd=RAIZ, capture_output=True, text=True, timeout=120)
    partes = [roda(str(i), str(TOTAL)) for i in range(1, TOTAL + 1)]
    assert all(p.returncode == 0 for p in partes), [p.stderr for p in partes]
    todos = [a for p in partes for a in p.stdout.split()]
    _confere([p.stdout.split() for p in partes], arquivos_de_teste())
    assert len(todos) == len(set(todos))
    assert roda("3", "2").returncode == 2 and roda("0", "2").returncode == 2 and roda("x", "2").returncode == 2 and roda().returncode == 2


def test_as_duracoes_saem_do_log_do_pytest_somando_setup_call_e_teardown():
    log = ("============ slowest durations ============\n"
           "10.50s call     tests/test_a.py::test_um\n"
           "2.25s setup    tests/test_a.py::test_um\n"
           "1.00s call     tests/test_b.py::test_x[1366x657]\n"
           "0.50s teardown tests/test_b.py::test_x[1366x657]\n"
           "linha qualquer sem duração\n")
    assert duracoes_do_log(log) == {"tests/test_a.py": 12.75, "tests/test_b.py": 1.5}


def test_o_workflow_usa_o_script_com_o_mesmo_numero_de_fatias_e_o_deploy_espera_todas():
    yml = (RAIZ / ".github" / "workflows" / "pages.yml").read_text(encoding="utf-8")
    assert f"fatia: [{', '.join(str(i) for i in range(1, TOTAL + 1))}]" in yml, "a matriz do workflow não bate com TOTAL"
    assert f"scripts.ci_fatias ${{{{ matrix.fatia }}}} {TOTAL}" in yml
    assert "needs: [test, build]" in yml                 # `test` é a matriz inteira: o deploy só sai com todas as fatias verdes
    assert "runs-on: ubuntu-24.04" in yml and "fail-fast: false" in yml
