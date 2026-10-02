"""Injeção de JSON dentro de um <script>: UM lugar, usado pelos dois builds.

O HTML fecha o <script> no primeiro `</script` que encontrar, esteja ele onde
estiver -- inclusive no meio de uma string do JSON (um nome de jogador). E
U+2028/U+2029 são quebras de linha para o JavaScript antigo, dentro de string.
Por isso todo dado que vai para dentro de <script> passa por aqui.
"""
from __future__ import annotations

import json

BARRA = chr(92)                      # a barra invertida, sem depender de escape no fonte
SEPARADOR_DE_LINHA = chr(0x2028)
SEPARADOR_DE_PARAGRAFO = chr(0x2029)


def texto_seguro(texto_json: str) -> str:
    """Um JSON JÁ serializado, pronto para ir dentro de <script>.

    `<` só aparece dentro de string num JSON, então escapar a barra de `</` e a
    exclamação de `<!--` não muda valor nenhum (são escapes de identidade).
    """
    return (texto_json.replace("</", "<" + BARRA + "/").replace("<!--", "<" + BARRA + "!--")
            .replace(SEPARADOR_DE_LINHA, BARRA + "u2028").replace(SEPARADOR_DE_PARAGRAFO, BARRA + "u2029"))


def js(valor, compacto: bool = True) -> str:
    """Um valor Python como literal JavaScript seguro dentro de <script>."""
    sep = (",", ":") if compacto else None
    return texto_seguro(json.dumps(valor, ensure_ascii=False, separators=sep))
