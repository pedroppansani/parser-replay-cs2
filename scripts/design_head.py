"""O <head> da direção visual "Sala de demo": tokens e fontes (decisão 44).

Um lugar só, usado pela página da partida, pela prancheta, pela página de jogadores e pela
landing. Os tokens (cores, fontes, espaços, raios) moram em `dashboard/web/tokens.css`; as fontes
são duas famílias (entrega-sala-de-demo §5), com a MESMA URL em todas as páginas.
"""
from __future__ import annotations

from pathlib import Path

WEB = Path(__file__).resolve().parent.parent / "dashboard" / "web"

# Archivo (eixo wdth 75-100, pesos 400-700) e JetBrains Mono (400 e 600), display=swap.
# Fonte: entrega-sala-de-demo §5.
FONTES_URL = ("https://fonts.googleapis.com/css2?family=Archivo:wdth,wght@75..100,400..700"
              "&family=JetBrains+Mono:wght@400;600&display=swap")

MARCADOR_TOKENS = "/*__TOKENS__*/"
MARCADOR_FONTES = "<!--__FONTES__-->"


def tokens_css() -> str:
    return (WEB / "tokens.css").read_text(encoding="utf-8")


def fontes_html() -> str:
    return ('<link rel="preconnect" href="https://fonts.googleapis.com">\n'
            '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>\n'
            f'<link rel="stylesheet" href="{FONTES_URL}">')


def aplica(html: str) -> str:
    """Troca os dois marcadores pelos tokens e pelas fontes."""
    return html.replace(MARCADOR_TOKENS, tokens_css()).replace(MARCADOR_FONTES, fontes_html())
