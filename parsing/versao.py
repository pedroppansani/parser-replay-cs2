"""
Versão do que PRODUZIU cada partida processada -- para saber o que está velho.

POR QUE EXISTE
--------------
Métrica muda. Quando muda, `data/processed/` fica com partidas calculadas por
versões diferentes do código, e a comparação entre elas passa a misturar
mudança de jogo com mudança de código -- em silêncio, que é o pior jeito. Já
aconteceu de verdade: a correção do `dmg_health_real` (decisão 8j) mudou o ADR
de 22 partidas, e não havia nada no repositório dizendo quais tinham sido
recalculadas depois.

SÃO DUAS VERSÕES, E A DIFERENÇA É CARA
--------------------------------------
- `VERSAO_DO_PARSER` cobre o que vira `data/interim/`: o parse da demo. Subir
  esta versão significa que o interim está velho, e refazê-lo **exige o arquivo
  .dem**. Como as demos são apagadas depois do processamento
  (`scripts/clean_match.py`), há partidas que NÃO PODEM ser reparseadas: o
  manifesto precisa dizer isso em voz alta, não descobrir na hora.
- `VERSAO_DAS_METRICAS` cobre o que vira `data/processed/`: o cálculo em cima do
  interim. Refazer custa `--from-interim`, não precisa da demo.

QUANDO SUBIR
------------
Sobe quem muda NÚMERO, não quem mexe em texto, teste ou comentário. Na dúvida,
suba: o custo de reprocessar é minutos, o custo de comparar duas versões
achando que são a mesma é uma conclusão errada sobre jogo.

A versão declarada à mão não pega mudança que alguém esqueceu de anotar -- por
isso o registro guarda também o COMMIT do git, que não depende de memória. A
versão serve para decidir o que reprocessar; o commit serve para auditar depois.
"""
from __future__ import annotations

import subprocess
from functools import lru_cache
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent

# HISTÓRICO -- uma linha por mudança que alterou número, a mais nova em cima.
#
# 1 (2026-09-20) primeira versão declarada. NÃO é "o parser nasceu aqui": é o
#   ponto em que o projeto passou a registrar isso. Partida processada antes
#   disto fica com versão desconhecida no manifesto, e é assim que tem que ser
#   -- afirmar retroativamente que ela rodou na versão 1 seria inventar.
VERSAO_DO_PARSER = 1

# 4 (2026-09-24) lurker medido sem os rounds com AWP, relativo à função
#   estrutural (piso 1,5x o esperado) e com amostra mínima de 8 rounds sem AWP.
# 3 (2026-09-22) empate na função dominante (structural_roles.
#   MARGEM_EMPATE_FUNCAO_ROUNDS = 0): quem tem duas ou mais funções com a mesma
#   contagem de rounds num lado fica "sem função dominante", com as empatadas.
# 2 (2026-09-21) processamento determinístico (decisão 28 do CLAUDE.md): empate
#   no corte do card de estilo entra inteiro, mode() desempata pelo menor valor
#   (inclui a classe de economia do jogador no rating), unique com subset fica
#   com a primeira linha. Antes, esses três casos dependiam da ordem de hash.
# 1 (2026-09-20) primeira versão declarada, mesmo raciocínio acima.
VERSAO_DAS_METRICAS = 4

# Pastas cujo estado define o NÚMERO. `sujo` olha só estas: olhar o repositório
# inteiro marcava todo reprocessamento como sujo, porque o próprio
# data/processed recém-escrito aparece como mudança não commitada.
PASTAS_DE_CODIGO = ("parsing", "metrics", "clustering", "scripts")


@lru_cache(maxsize=1)
def _commit() -> dict[str, str | bool | None]:
    """Commit atual, quando dá. Fora de um clone git, devolve None sem reclamar."""
    def git(*args: str) -> str | None:
        try:
            r = subprocess.run(["git", "-C", str(RAIZ), *args],
                               capture_output=True, text=True, timeout=10)
        except (OSError, subprocess.SubprocessError):
            return None
        return r.stdout.strip() if r.returncode == 0 else None

    sha = git("rev-parse", "HEAD")
    if sha is None:
        return {"commit": None, "sujo": None}
    # "sujo" = havia mudança não commitada no momento do processamento. É o
    # aviso de que o commit registrado NÃO descreve inteiramente este número.
    status = git("status", "--porcelain", "--", *PASTAS_DE_CODIGO)
    return {"commit": sha[:12], "sujo": bool(status)}


def _versao_da_lib(nome: str) -> str | None:
    try:
        from importlib.metadata import PackageNotFoundError, version

        return version(nome)
    except Exception:  # PackageNotFoundError e o que mais vier
        return None


def versoes() -> dict:
    """O bloco que vai para `match_meta.json` e daí para o manifesto."""
    return {
        "parser": VERSAO_DO_PARSER,
        "metricas": VERSAO_DAS_METRICAS,
        **_commit(),
        "awpy": _versao_da_lib("awpy"),
        "demoparser2": _versao_da_lib("demoparser2"),
    }


def situacao(registrado: dict | None) -> dict:
    """Compara o que rodou numa partida com o código de agora.

    `registrado` é o bloco `versao` do `match_meta.json` -- None quando a
    partida foi processada antes deste módulo existir.
    """
    if not registrado:
        return {
            "parser_velho": True, "metricas_velhas": True, "desconhecida": True,
            "motivo": "processada antes de o projeto registrar versão",
        }
    p = registrado.get("parser")
    m = registrado.get("metricas")
    partes = []
    if p != VERSAO_DO_PARSER:
        partes.append(f"parser {p} -> {VERSAO_DO_PARSER}")
    if m != VERSAO_DAS_METRICAS:
        partes.append(f"métricas {m} -> {VERSAO_DAS_METRICAS}")
    return {
        "parser_velho": p != VERSAO_DO_PARSER,
        "metricas_velhas": m != VERSAO_DAS_METRICAS,
        "desconhecida": False,
        "motivo": "; ".join(partes) or None,
    }
