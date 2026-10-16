"""Os `CLAUDE.md` cabem no orçamento e toda decisão em vigor está em algum deles (fase 14).

A raiz é lida inteira em toda sessão; o `CLAUDE.md` de uma pasta só quando a sessão mexe em
arquivos dali. Por isso cada um tem limite próprio, e a regra de uma decisão pode morar na raiz
ou na pasta onde ela pode ser quebrada. O que este teste garante:

- a raiz cabe em 15.000 bytes e cada `CLAUDE.md` de pasta em 5.000 (`metrics/` em 12.000 e
  `scripts/` em 6.000, decisões do Pedro nas fases 14, 17a e 18, para caber as regras copiadas),
  contados em UTF-8 com fim de linha LF;
- todo número de decisão citado no fim de uma regra ("... (21a)") tem nota em `notas/decisoes/`;
- toda decisão vigente é citada em algum `CLAUDE.md`, e a substituída ou revogada em nenhum;
- todo link relativo resolve;
- todo `CLAUDE.md` de pasta diz que complementa a raiz.

Substitui `test_o_claude_md_e_curto_e_os_links_resolvem` e
`test_regra_vigente_aparece_no_claude_md_e_a_superada_nao` de `test_referencias_a_decisoes.py`.
"""
from __future__ import annotations

import re
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
NOTAS = RAIZ / "notas" / "decisoes"
LIMITE_DA_RAIZ = 15_000              # bytes, com fim de linha LF (o limite que já existia)
LIMITE_DA_PASTA = 5_000              # bytes, idem
LIMITE_POR_PASTA = {"metrics/CLAUDE.md": 12_000,  # exceções decididas pelo Pedro (fase 14; fase 17a:
                    "scripts/CLAUDE.md": 6_000}   # as regras copiadas entre pastas; fase 18: as regras dos erros)
FORA = {".git", ".claude", ".venv", "venv", "node_modules", ".pytest_cache", "docs", "preview"}
# "(21a)" ou "(22a, 22b, 22k)" no fim de um item de lista
CITACAO = re.compile(r"\((\d+[a-z]?(?:,\s*\d+[a-z]?)*)\)\s*$")
LINK = re.compile(r"\]\(([^)#]+)\)")


def _texto(f: Path) -> str:
    return f.read_text(encoding="utf-8").replace("\r\n", "\n")


def _claude_mds() -> list[Path]:
    """A raiz e os `CLAUDE.md` de pasta do projeto (fora worktrees, .git e saídas)."""
    achados = []
    for f in sorted(RAIZ.rglob("CLAUDE.md")):
        partes = f.relative_to(RAIZ).parts
        if any(p in FORA for p in partes[:-1]):
            continue
        achados.append(f)
    return achados


def _itens(texto: str) -> list[str]:
    """Os itens de lista ("- ..." com as linhas de continuação), com o espaço normalizado."""
    itens, atual = [], None
    for linha in texto.split("\n"):
        if linha.startswith("- "):
            if atual is not None:
                itens.append(atual)
            atual = linha[2:]
        elif atual is not None and linha.startswith("  ") and linha.strip():
            atual += " " + linha.strip()
        else:
            if atual is not None:
                itens.append(atual)
            atual = None
    if atual is not None:
        itens.append(atual)
    return [re.sub(r"\s+", " ", i).strip() for i in itens]


def _citadas() -> dict[str, set[str]]:
    """ID da decisão -> os `CLAUDE.md` que a citam no fim de uma regra."""
    out: dict[str, set[str]] = {}
    for f in _claude_mds():
        for item in _itens(_texto(f)):
            m = CITACAO.search(item)
            if m:
                for ident in re.split(r",\s*", m.group(1)):
                    out.setdefault(ident, set()).add(f.relative_to(RAIZ).as_posix())
    return out


def _status() -> dict[str, str]:
    out = {}
    for f in NOTAS.glob("*-*.md"):
        status = re.search(r"- \*\*Status:\*\* (.+)", f.read_text(encoding="utf-8"))
        out[f.name.split("-")[0]] = status.group(1).strip() if status else ""
    return out


def test_a_raiz_cabe_no_limite():
    raiz = RAIZ / "CLAUDE.md"
    tamanho = len(_texto(raiz).encode("utf-8"))
    assert tamanho <= LIMITE_DA_RAIZ, f"CLAUDE.md da raiz com {tamanho} bytes (limite {LIMITE_DA_RAIZ})"


def test_cada_claude_md_de_pasta_cabe_no_limite():
    pastas = [f for f in _claude_mds() if f.parent != RAIZ]
    assert pastas, "nenhum CLAUDE.md de pasta encontrado: a varredura quebrou?"
    estourados = []
    for f in pastas:
        nome = f.relative_to(RAIZ).as_posix()
        limite = LIMITE_POR_PASTA.get(nome, LIMITE_DA_PASTA)
        tamanho = len(_texto(f).encode("utf-8"))
        if tamanho > limite:
            estourados.append(f"{nome}: {tamanho} bytes (limite {limite})")
    assert not estourados, estourados


def test_todo_claude_md_de_pasta_diz_que_complementa_a_raiz():
    for f in _claude_mds():
        if f.parent == RAIZ:
            continue
        inicio = _texto(f)[:400]
        assert "Complementa o `CLAUDE.md` da raiz" in inicio, f.relative_to(RAIZ).as_posix()


def test_toda_decisao_citada_num_claude_md_tem_nota():
    ids = set(_status())
    citadas = _citadas()
    assert len(citadas) > 80, "a varredura não achou as citações: o padrão quebrou?"
    orfas = [f"{i} em {sorted(arqs)}" for i, arqs in citadas.items() if i not in ids]
    assert not orfas, "decisão citada sem nota em notas/decisoes/:\n" + "\n".join(orfas)


def test_toda_vigente_esta_em_algum_claude_md_e_a_superada_em_nenhum():
    citadas = _citadas()
    faltando, sobrando = [], []
    for ident, status in sorted(_status().items()):
        if status == "vigente" and ident not in citadas:
            faltando.append(ident)
        if status != "vigente" and ident in citadas:
            sobrando.append(f"{ident} ({status}) em {sorted(citadas[ident])}")
    assert not faltando, f"decisão vigente fora de todos os CLAUDE.md: {faltando}"
    assert not sobrando, f"decisão superada ainda citada: {sobrando}"


def test_os_links_dos_claude_md_resolvem():
    for f in _claude_mds():
        for alvo in LINK.findall(_texto(f)):
            if not alvo.startswith("http"):
                assert (f.parent / alvo).exists(), f"{f.relative_to(RAIZ).as_posix()}: {alvo}"
