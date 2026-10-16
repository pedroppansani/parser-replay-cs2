"""Bloco copiado entre `CLAUDE.md` de pasta é igual ao da origem (fase 17a, item 6).

O `CLAUDE.md` de uma pasta só é lido quando a sessão mexe ali, e um ponteiro para outra pasta
depende de a sessão decidir abrir o outro arquivo. Por isso a regra que vale em duas pastas é
COPIADA, não apontada (decisão do Pedro na fase 17a). Para a cópia não divergir:

- na origem, o bloco fica entre `<!-- bloco NOME: inicio -->` e `<!-- bloco NOME: fim -->`;
- na cópia, entre `<!-- copia de ORIGEM#NOME: inicio -->` e `<!-- copia de ORIGEM#NOME: fim -->`,
  com ORIGEM o caminho do `CLAUDE.md` de origem a partir da raiz;
- o texto dos dois é o mesmo, ignorando espaços de borda e CRLF/LF.
"""
from __future__ import annotations

import re
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
FORA = {".git", ".claude", ".venv", "venv", "node_modules", ".pytest_cache", "docs", "preview"}
ORIGEM = re.compile(r"<!-- bloco ([a-z0-9-]+): inicio -->\n(.*?)\n<!-- bloco \1: fim -->", re.S)
COPIA = re.compile(r"<!-- copia de ([^#\s]+)#([a-z0-9-]+): inicio -->\n(.*?)\n<!-- copia de \1#\2: fim -->",
                   re.S)
MARCA = re.compile(r"<!-- (?:bloco [a-z0-9-]+|copia de [^#\s]+#[a-z0-9-]+): (?:inicio|fim) -->")
# Os blocos decididos na fase 17a: (origem, nome) -> onde está a cópia.
ESPERADOS = {
    ("dashboard/web/CLAUDE.md", "prancheta-espelho"): "metrics/CLAUDE.md",
    ("dashboard/web/CLAUDE.md", "anotacao-unidade-de-jogo"): "metrics/CLAUDE.md",
    ("metrics/CLAUDE.md", "regras-fit-metricas"): "scripts/CLAUDE.md",
    ("clustering/CLAUDE.md", "regras-clustering"): "scripts/CLAUDE.md",
}


def _texto(f: Path) -> str:
    return f.read_text(encoding="utf-8").replace("\r\n", "\n")


def _claude_mds() -> dict[str, str]:
    out = {}
    for f in sorted(RAIZ.rglob("CLAUDE.md")):
        rel = f.relative_to(RAIZ)
        if not any(p in FORA for p in rel.parts[:-1]):
            out[rel.as_posix()] = _texto(f)
    return out


def _origens() -> dict[tuple[str, str], str]:
    out = {}
    for nome, texto in _claude_mds().items():
        for bloco, corpo in ORIGEM.findall(texto):
            assert (nome, bloco) not in out, f"bloco {bloco} marcado duas vezes em {nome}"
            out[(nome, bloco)] = corpo.strip()
    return out


def _copias() -> list[tuple[str, str, str, str]]:
    """(arquivo da cópia, origem, nome do bloco, texto)."""
    return [(nome, origem, bloco, corpo.strip())
            for nome, texto in _claude_mds().items()
            for origem, bloco, corpo in COPIA.findall(texto)]


def test_toda_copia_e_igual_ao_bloco_da_origem():
    origens = _origens()
    divergentes = []
    for arquivo, origem, bloco, corpo in _copias():
        assert (origem, bloco) in origens, f"{arquivo}: cópia de {origem}#{bloco} sem bloco marcado na origem"
        if corpo != origens[(origem, bloco)]:
            divergentes.append(f"{arquivo}: cópia de {origem}#{bloco} difere da origem")
    assert not divergentes, divergentes


def test_os_blocos_decididos_existem_na_origem_e_na_copia():
    origens = _origens()
    copias = {(origem, bloco): arquivo for arquivo, origem, bloco, _ in _copias()}
    for (origem, bloco), destino in ESPERADOS.items():
        assert (origem, bloco) in origens, f"falta o bloco {bloco} marcado em {origem}"
        assert copias.get((origem, bloco)) == destino, f"falta a cópia de {origem}#{bloco} em {destino}"
    for chave in origens:
        assert chave in copias, f"bloco {chave[1]} de {chave[0]} marcado sem cópia em lugar nenhum"


def test_toda_marca_fecha():
    """Marca de início sem fim (ou com nome trocado) não casa com os padrões e passaria em silêncio."""
    for nome, texto in _claude_mds().items():
        marcas = MARCA.findall(texto)
        casadas = 2 * (len(ORIGEM.findall(texto)) + len(COPIA.findall(texto)))
        assert len(marcas) == casadas, f"{nome}: {len(marcas)} marcas, {casadas} casadas"
