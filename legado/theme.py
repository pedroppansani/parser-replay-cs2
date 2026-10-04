"""
Tokens visuais do dashboard.

As cores não foram escolhidas no olho: a paleta categórica foi validada com o
validador de paletas (checagem de banda de luminosidade, piso de croma,
separação para daltonismo e contraste contra a superfície) nos dois modos.

Achado dessa validação, que explica uma decisão do dashboard: com três séries a
paleta passa em todos os pares nos dois modos, mas NENHUMA quarta cor passa no
modo escuro junto das três primeiras (o melhor candidato fica em ΔE 7,1 de
separação em visão normal, abaixo do piso de 15). Como o clustering usa 4 grupos
num scatter -- forma que compara todos os pares de cor ao mesmo tempo --, a
saída foi facetar: um painel por cluster, cada um destacado numa cor só sobre os
demais pontos em cinza. Além de resolver a acessibilidade, lê melhor pro que
esse gráfico serve (olhar um cluster de cada vez pra dar nome a ele).
"""
from __future__ import annotations

# Série categórica (até 3 em um mesmo gráfico; acima disso, facetar)
SERIES = ["#2a78d6", "#eb6834", "#1baf7a"]
SERIES_DARK = ["#3987e5", "#d95926", "#199e70"]

# Rampa sequencial de uma cor só (magnitude: heatmap de posições)
SEQUENTIAL_BLUE = [
    [0.0, "#cde2fb"],
    [0.25, "#86b6ef"],
    [0.5, "#3987e5"],
    [0.75, "#256abf"],
    [1.0, "#0d366b"],
]

# Tinta e cromo do gráfico
INK_PRIMARY = "#e9e9e6"
INK_SECONDARY = "#c3c2b7"
INK_MUTED = "#898781"
GRID = "#2c2c2a"
AXIS = "#383835"
SURFACE = "rgba(0,0,0,0)"  # deixa o fundo do Streamlit aparecer
CONTEXT_POINT = "#4a4a47"  # pontos de contexto (fora do cluster em foco)

FONT_FAMILY = 'system-ui, -apple-system, "Segoe UI", sans-serif'


def base_layout(height: int = 360, show_legend: bool = False) -> dict:
    """Layout comum: grid discreto, sem moldura, fonte do sistema, hover ligado."""
    return {
        "height": height,
        "showlegend": show_legend,
        "paper_bgcolor": SURFACE,
        "plot_bgcolor": SURFACE,
        "font": {"family": FONT_FAMILY, "color": INK_SECONDARY, "size": 12},
        "margin": {"l": 56, "r": 16, "t": 16, "b": 40},
        "xaxis": {
            "gridcolor": GRID,
            "linecolor": AXIS,
            "zerolinecolor": AXIS,
            "tickfont": {"color": INK_MUTED},
        },
        "yaxis": {
            "gridcolor": GRID,
            "linecolor": AXIS,
            "zerolinecolor": AXIS,
            "tickfont": {"color": INK_MUTED},
        },
        "hoverlabel": {"font": {"family": FONT_FAMILY, "size": 12}},
    }
