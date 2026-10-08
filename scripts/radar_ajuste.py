"""
A tabela RADAR_AJUSTE (dessaturação do radar por mapa) vista do build: ela mora no map_core.js
(entrega-sala-de-demo §4.1) e o build avisa quando um mapa com radar não tem entrada nela.

Mapa sem entrada usa RADAR_AJUSTE_PADRAO (0,10/0,70) na página; o aviso diz isso e manda rodar o
gerador, porque o par certo de um mapa novo sai da medição, não de chute.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

MAP_CORE = Path(__file__).resolve().parent.parent / "dashboard" / "web" / "map_core.js"


def tabela() -> dict[str, tuple[float, float]]:
    """{mapa sem "de_": (saturação, brilho)}, lido da constante do map_core.js."""
    texto = MAP_CORE.read_text(encoding="utf-8")
    bloco = re.search(r"var RADAR_AJUSTE = \{(.*?)\};", texto, re.S).group(1)
    return {m: (float(s), float(b)) for m, s, b in re.findall(r"(\w+):\s*\[([\d.]+),\s*([\d.]+)\]", bloco)}


def padrao() -> tuple[float, float]:
    s, b = re.search(r"var RADAR_AJUSTE_PADRAO = \[([\d.]+),\s*([\d.]+)\];", MAP_CORE.read_text(encoding="utf-8")).groups()
    return float(s), float(b)


def aviso(mapa: str) -> str | None:
    """O texto do aviso para um mapa sem entrada, ou None quando ele tem a sua."""
    chave = mapa.removeprefix("de_")
    if chave in tabela():
        return None
    s, b = (f"{x:.2f}".replace(".", ",") for x in padrao())
    return (f"aviso: radar de {mapa} sem entrada em RADAR_AJUSTE; usando o par padrão {s}/{b}; "
            "rode py -3.12 -m scripts.design.gera_radar_ajuste")


def avisa(mapa: str) -> None:
    texto = aviso(mapa)
    if texto:
        print(texto, file=sys.stderr)
