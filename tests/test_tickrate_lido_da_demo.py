"""Nenhuma conversão de tick para segundo usa um tickrate literal (cartão 12, nota 22j).

Regra dura da raiz: "O demo é 64 tick; nunca assuma (`metrics/timing.py` detecta)". O padrão
`tickrate: int = 128` de `metrics/grenades.py`, que o `scripts/process_demo.py` usava sem passar
o tickrate, gravou a janela da flash com o dobro da cegueira real. Este teste lê o código de
`metrics/`, `scripts/`, `parsing/`, `clustering/` e `leitura/` (AST, sem importar nada) e falha em qualquer destas formas:

- parâmetro `tickrate`/`tick_rate` com padrão numérico (`tickrate: int = 64`);
- constante de módulo com o tickrate escrito (`TICKRATE = 64`, `TR = 64`) ou em ticks com 64/128
  (`..._TICKS = 64`);
- conta com 64 ou 128 como operando de `*`, `/` ou `//` (`/ 64`, `* 64`, `800 / 128`);
- 64 ou 128 passado como argumento de chamada (`rating(..., 64)`, `.get("tickrate", 64)`) ou
  como queda de um `or` (`... or 64`).

O valor tem de vir de `metrics.timing.detect_tickrate` (ou do `tickrate` que o build grava a partir
dele). As exceções ficam em `EXCECOES` (definitivas, justificadas). `PENDENTES` está VAZIA (as funções
não têm padrão e os scripts leem o tickrate da partida); qualquer linha nova que caia numa das
formas acima e não esteja em `EXCECOES` quebra o teste. A prova de que cada função corrigida
funciona a 128 tick está em `tests/test_tickrate_128.py`.
"""
from __future__ import annotations

import ast
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
PASTAS = ("metrics", "scripts", "parsing", "clustering", "leitura")
LITERAIS = {64, 128}
NOMES_DE_TICKRATE = {"tickrate", "tick_rate"}

# (arquivo, trecho do código como o ast.unparse escreve): o porquê ao lado.
EXCECOES = {
    # A própria detecção: os candidatos e a queda quando a demo não tem âncora nenhuma.
    ("metrics/timing.py", "DEFAULT_TICKRATE = 64"): "a queda da detecção, único lugar do padrão",
    # Constantes em ticks sem conversão para segundo: o 64 é uma contagem de quadros, não um tickrate.
    ("metrics/grenade_throws.py", "TICKRATE_DA_MEDICAO = 64"):
        "o tickrate em que o gabarito foi medido (tolerância da 2ª diferença e janelas do jump-throw "
        "em ticks); a conta escala por (64 / tickrate), o tickrate da demo é o argumento",
    ("metrics/grenade_throws.py", "JANELA_DECOLAGEM_TICKS = 64"):
        "janela de posições (64 ticks de dados) com que o gabarito do jogo foi medido; a conta usa o "
        "tickrate recebido, a janela é só quantos pontos olhar",
    ("metrics/positioning.py", "POSITION_SAMPLE_EVERY_N_TICKS = 64"):
        "passo de amostragem da posição em ticks (1 s a 64 tick); não converte tick em segundo, só "
        "decide quantas amostras guardar para o mapa de calor",
}

# Esvaziada (cartão 12, 2026-10-21): todo tickrate vem da demo e é passado para baixo; as funções
# não têm padrão. Linha nova que caia numa das formas acima quebra o teste.
PENDENTES: dict[tuple[str, str], str] = {}


def _e_literal(no: ast.AST) -> bool:
    return (isinstance(no, ast.Constant) and not isinstance(no.value, bool)
            and isinstance(no.value, (int, float)) and no.value in LITERAIS)


def _trecho(no: ast.AST) -> str:
    """O trecho normalizado; chamada longa vira `f(... , x)` a partir do sétimo argumento."""
    if isinstance(no, ast.Call) and len(no.args) + len(no.keywords) > 7:
        curto = ast.Call(func=no.func, args=no.args, keywords=no.keywords[:2] + [
            ast.keyword(arg=None, value=ast.Name(id="x"))])
        return ast.unparse(curto).replace("**x", "x")
    return ast.unparse(no)


def achados() -> list[tuple[str, int, str]]:
    """(arquivo, linha, trecho) de cada tickrate literal em `metrics/` e `scripts/`."""
    saida = []
    for pasta in PASTAS:
        for f in sorted((RAIZ / pasta).rglob("*.py")):
            rel = f.relative_to(RAIZ).as_posix()
            arvore = ast.parse(f.read_text(encoding="utf-8"))
            for no in ast.walk(arvore):
                achou = None
                if isinstance(no, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    a = no.args
                    posicionais = a.posonlyargs + a.args
                    pares = list(zip(posicionais[len(posicionais) - len(a.defaults):], a.defaults))
                    pares += [(k, d) for k, d in zip(a.kwonlyargs, a.kw_defaults) if d is not None]
                    for arg, d in pares:
                        if arg.arg in NOMES_DE_TICKRATE and isinstance(d, ast.Constant) and d.value is not None:
                            anot = f": {ast.unparse(arg.annotation)}" if arg.annotation else ""
                            saida.append((rel, d.lineno, f"{arg.arg}{anot} = {d.value!r}"))
                    continue
                if isinstance(no, (ast.Assign, ast.AnnAssign)) and _e_literal(no.value):
                    alvos = no.targets if isinstance(no, ast.Assign) else [no.target]
                    nomes = [t.id for t in alvos if isinstance(t, ast.Name)]
                    if any("TICKRATE" in n.upper() or "TICK_RATE" in n.upper() or n == "TR" or "TICKS" in n
                           for n in nomes):
                        achou = no
                elif isinstance(no, ast.BinOp) and isinstance(no.op, (ast.Mult, ast.Div, ast.FloorDiv)):
                    if _e_literal(no.left) or _e_literal(no.right):
                        achou = no
                elif isinstance(no, ast.Call):
                    if any(_e_literal(x) for x in no.args) or any(_e_literal(k.value) for k in no.keywords):
                        achou = no
                elif isinstance(no, ast.BoolOp) and isinstance(no.op, ast.Or):
                    if any(_e_literal(v) for v in no.values):
                        achou = no
                if achou is not None:
                    saida.append((rel, achou.lineno, _trecho(achou)))
    return saida


def test_nenhuma_conversao_de_tick_usa_tickrate_literal():
    novos = [f"{a}:{n}: {t}" for a, n, t in achados() if (a, t) not in EXCECOES and (a, t) not in PENDENTES]
    assert not novos, ("tickrate escrito no código (leia de metrics.timing.detect_tickrate):\n"
                       + "\n".join(novos))


def test_as_listas_de_excecao_nao_tem_sobra():
    """Linha corrigida sai da lista: exceção que não acha mais nada é lixo."""
    vistos = {(a, t) for a, _, t in achados()}
    sobra = [k for k in list(EXCECOES) + list(PENDENTES) if k not in vistos]
    assert not sobra, f"exceções que não aparecem mais no código: {sobra}"


def test_a_metrica_de_flash_nao_tem_tickrate_padrao():
    """O caso do cartão 12: as funções de `metrics/grenades.py` exigem o tickrate, e o
    `process_demo` o lê da demo antes de chamá-las."""
    assert not [x for x in achados() if x[0] == "metrics/grenades.py"]
    arvore = ast.parse((RAIZ / "scripts" / "process_demo.py").read_text(encoding="utf-8"))
    chamadas = [n for n in ast.walk(arvore) if isinstance(n, ast.Call)
                and getattr(n.func, "id", None) == "compute_grenade_metrics"]
    assert chamadas and all(len(c.args) + len(c.keywords) >= 3 for c in chamadas)
    assert "detect_tickrate" in {getattr(n.func, "id", None) for n in ast.walk(arvore) if isinstance(n, ast.Call)}


def test_o_controle_acha_os_literais():
    """Controle: as formas proibidas são achadas (se não achasse nada, não mediria nada)."""
    codigo = ("def f(ticks, tickrate: int = 128):\n    return ticks / 64\n"
              "TICKRATE = 64\ng(1, 64)\nx = meta.get('tickrate') or 128\n")
    arvore = ast.parse(codigo)
    n_formas = sum(
        1 for no in ast.walk(arvore)
        if (isinstance(no, ast.BinOp) and (_e_literal(no.left) or _e_literal(no.right)))
        or (isinstance(no, ast.Call) and any(_e_literal(x) for x in no.args))
        or (isinstance(no, ast.BoolOp) and any(_e_literal(v) for v in no.values))
        or (isinstance(no, ast.Assign) and _e_literal(no.value))
        or (isinstance(no, ast.FunctionDef) and any(_e_literal(d) for d in no.args.defaults))
    )
    assert n_formas == 5
