"""As decisões vivem em `notas/decisoes/`; o código as cita por ID.

Toda menção a "decisão N" num comentário tem de apontar para uma nota que
existe, e o `CLAUDE.md` tem de continuar curto e com os links de pé.
"""
from __future__ import annotations

import re
import subprocess
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
NOTAS = RAIZ / "notas" / "decisoes"
PASTAS = ("parsing", "metrics", "clustering", "scripts", "pesquisa", "tests", "dashboard")
EXTENSOES = {".py", ".js", ".html", ".css"}
LIMITE_DO_CLAUDE_MD = 15_000          # bytes, com fim de linha LF
MENCAO = re.compile(r"decis(?:ão|ao|ões|oes)\s+(\d+[a-z]?)\b", re.I)


def _ids_com_nota() -> set[str]:
    return {f.name.split("-")[0] for f in NOTAS.glob("*-*.md")}


def _mencoes() -> list[tuple[str, int, str]]:
    out = []
    for pasta in PASTAS:
        for f in sorted((RAIZ / pasta).rglob("*")):
            if f.suffix not in EXTENSOES or not f.is_file() or "__pycache__" in f.parts:
                continue
            if f.name == Path(__file__).name:
                continue
            for n, linha in enumerate(f.read_text(encoding="utf-8", errors="replace").splitlines(), start=1):
                for m in MENCAO.finditer(linha):
                    out.append((f.relative_to(RAIZ).as_posix(), n, m.group(1)))
    return out


def test_toda_decisao_citada_no_codigo_tem_nota():
    ids = _ids_com_nota()
    mencoes = _mencoes()
    assert len(mencoes) > 50, "a varredura não achou as menções: o padrão quebrou?"
    orfas = [f"{arq}:{n} cita a decisão {i}" for arq, n, i in mencoes if i not in ids]
    assert not orfas, "decisão citada sem nota em notas/decisoes/:\n" + "\n".join(orfas)


def test_cada_nota_tem_o_cabecalho_e_um_status_valido():
    notas = sorted(NOTAS.glob("*-*.md"))
    assert len(notas) >= 84
    for f in notas:
        texto = f.read_text(encoding="utf-8")
        ident = f.name.split("-")[0]
        assert f"- **ID:** {ident}\n" in texto, f.name
        status = re.search(r"- \*\*Status:\*\* (.+)", texto)
        assert status, f.name
        assert re.fullmatch(r"vigente|revogada|substituída por \d+[a-z]?", status.group(1).strip()), (f.name, status.group(1))
        assert "- **Data:**" in texto and "- **Resumo:**" in texto, f.name


def test_o_claude_md_e_curto_e_os_links_resolvem():
    texto = (RAIZ / "CLAUDE.md").read_text(encoding="utf-8").replace("\r\n", "\n")
    assert len(texto.encode("utf-8")) <= LIMITE_DO_CLAUDE_MD
    links = re.findall(r"\]\(([^)#]+)\)", texto)
    assert len(links) > 80
    for alvo in links:
        if not alvo.startswith("http"):
            assert (RAIZ / alvo).exists(), alvo


def test_regra_vigente_aparece_no_claude_md_e_a_superada_nao():
    texto = (RAIZ / "CLAUDE.md").read_text(encoding="utf-8")
    regras = texto[texto.index("## Regras vigentes"):texto.index("## Números citáveis")]
    for f in sorted(NOTAS.glob("*-*.md")):
        ident = f.name.split("-")[0]
        status = re.search(r"- \*\*Status:\*\* (.+)", f.read_text(encoding="utf-8")).group(1).strip()
        citada = f"](notas/decisoes/{f.name})" in regras
        assert citada == (status == "vigente"), (ident, status)


def test_a_reestruturacao_nao_perdeu_nada():
    """A conferência de 2026-10-02: todo ID e todo trecho do CLAUDE.md antigo
    está em alguma nota. Precisa da revisão antiga no git (pulado num clone raso)."""
    from scripts.confere_claude_md import confere
    from scripts.divide_claude_md import ANTIGO
    if subprocess.run(["git", "cat-file", "-e", f"{ANTIGO}:CLAUDE.md"], cwd=RAIZ, capture_output=True).returncode != 0:
        pytest.skip("a revisão antiga do CLAUDE.md não está neste clone")
    r = confere()
    assert not r["ids_sem_nota"] and not r["ids_sem_cabecalho"]
    assert not r["trechos_perdidos"], r["trechos_perdidos"][:5]
