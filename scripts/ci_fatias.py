"""P1d: reparte os arquivos de teste em fatias, uma por máquina do CI (o job `test` roda em paralelo, uma fatia em cada).

    python -m scripts.ci_fatias 1 2          # imprime os arquivos da fatia 1 de 2 (o workflow passa isso ao pytest)
    python -m scripts.ci_fatias --atualiza LOG_DO_CI [LOG ...]   # regrava as durações a partir de `pytest --durations=0` de um run do CI

A divisão é por ARQUIVO de teste (a ordem dentro de cada arquivo não muda) e sem dependência nova (nada de xdist nem pytest-split).
Os arquivos são os mesmos que o pytest acharia: `tests/**/test_*.py`. A união das fatias é SEMPRE exatamente essa lista: as durações só pesam
a divisão (em `.github/duracoes-dos-testes.json`, medidas no CI, que é onde o tempo importa); uma duração velha deixa as fatias tortas, mas nunca
tira um teste. Arquivo novo, sem duração, pesa a mediana das conhecidas e vai para a fatia com menos carga; arquivo que sumiu é ignorado.
`tests/test_ci_fatias.py` prova a partição.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from statistics import median

RAIZ = Path(__file__).resolve().parent.parent
ARQUIVO_DE_DURACOES = RAIZ / ".github" / "duracoes-dos-testes.json"
# uma linha de `pytest --durations=0`: "12.34s call     tests/test_x.py::test_y[param]"
_LINHA = re.compile(r"(\d+(?:\.\d+)?)s\s+(?:setup|call|teardown)\s+(tests/\S+?\.py)::")


def arquivos_de_teste(raiz: Path = RAIZ) -> list[str]:
    """Os arquivos que o pytest roda, com `/` e relativos à raiz, em ordem alfabética."""
    return sorted(p.relative_to(raiz).as_posix() for p in (raiz / "tests").rglob("test_*.py"))


def carrega_duracoes(arquivo: Path = ARQUIVO_DE_DURACOES) -> dict[str, float]:
    """Segundos por arquivo de teste. Sem arquivo ou com lixo: vazio (a divisão cai para pesos iguais, mas continua exata)."""
    try:
        dados = json.loads(arquivo.read_text(encoding="utf-8")).get("segundos", {})
    except (OSError, ValueError, AttributeError):
        return {}
    return {a: float(s) for a, s in dados.items() if isinstance(s, (int, float)) and not isinstance(s, bool) and s >= 0}


def reparte(arquivos: list[str], duracoes: dict[str, float], n: int) -> list[list[str]]:
    """As `n` fatias (listas ordenadas de arquivos). Cada arquivo cai em UMA fatia, e a união é a lista inteira, sempre.

    Guloso pelo mais pesado: os arquivos com duração, do maior para o menor, vão para a fatia mais leve; depois os sem duração (pesando a
    mediana das conhecidas), também para a mais leve. Empate: a fatia de menor índice. Não depende da ordem de `arquivos`."""
    if n < 1:
        raise ValueError("n precisa ser pelo menos 1")
    unicos = sorted(set(arquivos))
    conhecidos = {a: duracoes[a] for a in unicos if a in duracoes}
    peso_do_novo = median(conhecidos.values()) if conhecidos else 1.0
    fatias: list[list[str]] = [[] for _ in range(n)]
    carga = [0.0] * n

    def poe(arquivo: str, peso: float) -> None:
        i = min(range(n), key=lambda k: (carga[k], k))
        fatias[i].append(arquivo); carga[i] += peso

    for a in sorted(conhecidos, key=lambda a: (-conhecidos[a], a)):
        poe(a, conhecidos[a])
    for a in unicos:
        if a not in conhecidos:
            poe(a, peso_do_novo)
    return [sorted(f) for f in fatias]


def duracoes_do_log(texto: str) -> dict[str, float]:
    """Soma, por arquivo, o setup + call + teardown de um `pytest --durations=0`."""
    soma: dict[str, float] = {}
    for segundos, arquivo in _LINHA.findall(texto):
        soma[arquivo] = soma.get(arquivo, 0.0) + float(segundos)
    return {a: round(s, 2) for a, s in sorted(soma.items())}


def atualiza(logs: list[Path], arquivo: Path = ARQUIVO_DE_DURACOES) -> int:
    medidas: dict[str, float] = {}
    for log in logs:
        for a, s in duracoes_do_log(log.read_text(encoding="utf-8", errors="replace")).items():
            medidas[a] = round(medidas.get(a, 0.0) + s, 2)
    if not medidas:
        print("nenhuma linha de duração achada (rode o pytest com --durations=0)", file=sys.stderr)
        return 1
    arquivo.write_text(json.dumps({
        "_leia_isto": "Segundos por arquivo de teste, medidos no CI (pytest --durations=0), para scripts/ci_fatias.py repartir os arquivos entre as máquinas. "
                      "Só pesam a divisão: arquivo novo ou sumido não quebra nada. Para atualizar: baixe o log do job `test` de um run (gh run view ID --log) e rode "
                      "`python -m scripts.ci_fatias --atualiza LOG`.",
        "segundos": medidas}, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"{len(medidas)} arquivos, {sum(medidas.values()):.0f} s no total, em {arquivo}")
    return 0


def main(argv: list[str]) -> int:
    if argv and argv[0] == "--atualiza":
        return atualiza([Path(a) for a in argv[1:]])
    if len(argv) != 2 or not all(a.isdigit() for a in argv):
        print(__doc__, file=sys.stderr)
        return 2
    i, n = int(argv[0]), int(argv[1])
    if not 1 <= i <= n:
        print(f"fatia {i} fora de 1..{n}", file=sys.stderr)
        return 2
    fatia = reparte(arquivos_de_teste(), carrega_duracoes(), n)[i - 1]
    if not fatia:   # pytest sem arquivo nenhum rodaria a suíte inteira: melhor parar
        print(f"a fatia {i} de {n} ficou vazia", file=sys.stderr)
        return 1
    print(" ".join(fatia))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
