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


def topo_do_site(atual: str, prancheta: str | None, repo: str) -> str:
    """O topo do site (entrega-sala-de-demo §7): marca e quatro links -- Partidas, Jogadores, Prancheta, GitHub.
    `atual` é "partidas", "jogadores" ou "prancheta" (recebe aria-current). O CSS fica em cada página."""
    from html import escape as e
    links = [("partidas", "index.html", "Partidas"), ("jogadores", "jogadores.html", "Jogadores")]
    if prancheta:
        links.append(("prancheta", prancheta, "Prancheta"))
    nav = "".join(f'<a href="{e(h)}"{" aria-current=\"page\"" if k == atual else ""}>{t}</a>' for k, h, t in links)
    return (f'<header class="site-topo">\n'
            f'    <a class="marca" href="index.html" aria-label="Parser de Replay CS2, início">'
            f'<span class="marca-longa">Parser de Replay</span><b>CS2</b></a>\n'
            f'    <nav class="site-nav" aria-label="Principal">{nav}<a href="{e(repo)}">GitHub</a></nav>\n'
            f'  </header>')
