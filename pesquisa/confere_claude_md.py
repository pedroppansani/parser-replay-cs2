"""Prova que a reestruturação do CLAUDE.md não perdeu nada.

Compara o CLAUDE.md da revisão `ANTIGO` com o que existe hoje em `notas/` e no
CLAUDE.md novo:

1. todo ID de decisão do antigo tem uma nota em `notas/decisoes/<ID>-*.md`,
   com o cabeçalho completo (ID, Status, Data, Resumo);
2. todo TRECHO do antigo aparece em alguma nota, investigação ou no CLAUDE.md
   novo. Trecho = frase (ou item de lista, ou linha de tabela ou de código) com
   o espaço em branco normalizado, para a quebra de linha não contar.

Uso:
    py -3.12 -m pesquisa.confere_claude_md
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))
from pesquisa.divide_claude_md import antigo, blocos  # noqa: E402

NOTAS = RAIZ / "notas"
MIN_CARACTERES = 25            # trecho menor que isto não identifica nada ("Medido:", "```")
CAMPOS = ("**ID:**", "**Status:**", "**Data:**", "**Resumo:**")


def normaliza(t: str) -> str:
    return re.sub(r"\s+", " ", t).strip()


def trechos(texto: str) -> list[str]:
    """As frases do texto, com o espaço normalizado."""
    out = []
    for paragrafo in re.split(r"\n\s*\n", texto):
        p = normaliza(paragrafo)
        # corta em fim de frase seguido de maiúscula, abre-parêntese, aspas ou marcador
        for frase in re.split(r"(?<=[.!?:;])\s+(?=[A-ZÀ-Ú0-9(\"“`*\-|])", p):
            f = frase.strip()
            if len(f) >= MIN_CARACTERES:
                out.append(f)
    return out


def destino() -> str:
    partes = [(RAIZ / "CLAUDE.md").read_text(encoding="utf-8")]
    partes += [f.read_text(encoding="utf-8") for f in sorted(NOTAS.rglob("*.md"))]
    return normaliza("\n".join(partes))


def confere() -> dict:
    velho = antigo()
    decs, _ = blocos(velho)
    sem_nota, sem_campo = [], []
    for ident in decs:
        arquivos = list((NOTAS / "decisoes").glob(f"{ident}-*.md"))
        if len(arquivos) != 1:
            sem_nota.append(ident)
            continue
        texto = arquivos[0].read_text(encoding="utf-8")
        if not all(c in texto for c in CAMPOS) or f"**ID:** {ident}\n" not in texto:
            sem_campo.append(ident)
    alvo = destino()
    todos = trechos(velho)
    perdidos = [t for t in todos if t not in alvo]
    return {"ids": len(decs), "ids_sem_nota": sem_nota, "ids_sem_cabecalho": sem_campo,
            "trechos": len(todos), "trechos_perdidos": perdidos,
            "bytes_antigo": len(velho.encode("utf-8")),
            "bytes_novo": len((RAIZ / "CLAUDE.md").read_text(encoding="utf-8").encode("utf-8"))}


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    r = confere()
    com_nota = r["ids"] - len(r["ids_sem_nota"])
    achados = r["trechos"] - len(r["trechos_perdidos"])
    print(f"IDs do CLAUDE.md antigo com nota: {com_nota} de {r['ids']} ({com_nota / r['ids']:.1%})")
    print(f"notas com o cabeçalho completo:   {r['ids'] - len(r['ids_sem_cabecalho'])} de {r['ids']}")
    print(f"trechos do antigo preservados:    {achados} de {r['trechos']} ({achados / r['trechos']:.1%})")
    print(f"CLAUDE.md: {r['bytes_antigo']} bytes -> {r['bytes_novo']} bytes")
    for nome in ("ids_sem_nota", "ids_sem_cabecalho"):
        if r[nome]:
            print(f"  {nome}: {r[nome]}")
    for t in r["trechos_perdidos"][:20]:
        print("  PERDIDO:", t[:160])
    if r["ids_sem_nota"] or r["ids_sem_cabecalho"] or r["trechos_perdidos"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
