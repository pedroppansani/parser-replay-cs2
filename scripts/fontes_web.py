"""
O texto de uma fonte do site, com as partes incluídas (cartão 9, decisão 50).

Uma fonte grande (o `tactics.js`, o script do `template.html`) pode ser dividida em partes: no lugar de cada parte fica
uma linha `//@inclui <caminho>` (relativo à pasta da fonte, sozinha na linha, a partir da primeira coluna), e
`le_fonte` devolve o texto com cada uma dessas linhas trocada pelo conteúdo da parte, tal como está no arquivo. O build,
os testes e as ferramentas leem as duas fontes por aqui, nunca pelo `read_text` do arquivo: o que sai é o texto de antes
da divisão, byte a byte (`scripts.design.prova_refatoracao`). Uma parte não inclui outra.
"""
from __future__ import annotations

import re
from pathlib import Path

INCLUI = re.compile(r"^//@inclui ([\w./-]+)\n", re.M)


def le_fonte(caminho: Path | str) -> str:
    caminho = Path(caminho)

    def parte(m: re.Match) -> str:
        arquivo = caminho.parent / m.group(1)
        texto = arquivo.read_text(encoding="utf-8")
        if INCLUI.search(texto):
            raise ValueError(f"{arquivo}: uma parte não inclui outra")
        return texto

    return INCLUI.sub(parte, caminho.read_text(encoding="utf-8"))
