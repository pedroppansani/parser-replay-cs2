"""
Identidade de TIME: um nome canônico por time, num lugar só.

A demo grava o nome do time como estava no servidor, e o mesmo time aparece no
corpus escrito de mais de um jeito ("Vitality" e "Team Vitality", "Falcons" e
"Team Falcons"). Qualquer agregado por time quebra nisso: a contagem de times
do corpus saía 11 em vez de 9, e cinco scripts tinham cada um a sua cópia de
"tira o prefixo Team".

É o mesmo espírito da decisão 25 para jogadores (identidade é o steamid; o nome
é rótulo): aqui a tabela é explícita (`data/reference/times_conhecidos.json`),
porque time não tem identificador na demo. Nome que não está na tabela é o
próprio canônico; um teste acusa quando dois nomes do corpus parecem o mesmo
time sem que a tabela diga isso.
"""
from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path

ARQUIVO = Path(__file__).resolve().parent.parent / "data" / "reference" / "times_conhecidos.json"


@lru_cache(maxsize=1)
def _alias() -> dict[str, str]:
    if not ARQUIVO.exists():
        return {}
    return dict(json.loads(ARQUIVO.read_text(encoding="utf-8")).get("alias", {}))


def nome_canonico(nome: str | None) -> str:
    """O nome canônico do time. Sem nome, devolve "" (nunca inventa)."""
    n = (nome or "").strip()
    return _alias().get(n, n)


def chave_de_semelhanca(nome: str) -> str:
    """Forma reduzida do nome, só para DETECTAR variantes ainda não registradas:
    sem caixa, sem o prefixo "team", sem espaço nem pontuação. Não é usada para
    agregar -- quem agrega é a tabela."""
    n = re.sub(r"^team\s+", "", (nome or "").strip().casefold())
    return re.sub(r"[^a-z0-9]", "", n)


def nome_do_lado_faceit(nicks: list[str]) -> str:
    """"Time de <nick>" para um lado da FACEIT, onde o "time" da demo é um nome gerado (`team_<nick>`).

    O nick escolhido é o PRIMEIRO em ordem alfabética (`casefold`, depois a ordem do código) entre os
    jogadores que começaram a partida naquele lado: não depende de desempenho nem da ordem em que os
    dados chegam, então o mesmo lado tem o mesmo nome em qualquer execução (decisão 28). É só nome de
    exibição; o identificador interno do time (A/B) não muda.
    """
    if not nicks:
        return ""
    return "Time de " + min(nicks, key=lambda n: (n.casefold(), n))
