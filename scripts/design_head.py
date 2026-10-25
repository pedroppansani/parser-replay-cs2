"""O <head> da direção visual: tokens e fontes (decisões 44 e 48).

Um lugar só, usado pela página da partida, pela prancheta, pela página de jogadores e pela
landing. Os tokens (cores, fontes, espaços, raios) moram em `dashboard/web/tokens.css`; as fontes
são duas famílias, Geist e Geist Mono, hospedadas no próprio site (entrega-v2-goatdemo §3.1): os
woff2 ficam em `dashboard/web/fontes/` e o build os copia para `fontes/`, ao lado das páginas.
Nenhum pedido ao Google Fonts. Sem `<link rel=preload crossorigin>`: em `file://` o preload com
crossorigin é bloqueado por CORS (medido no protótipo).
"""
from __future__ import annotations

import shutil
from pathlib import Path

WEB = Path(__file__).resolve().parent.parent / "dashboard" / "web"

# As duas famílias carregadas (A6) e os arquivos, relativos à página (o build copia FONTES_DIR para fontes/).
FONTES_DIR = WEB / "fontes"
FONTES = (("Geist", "geist-latin.woff2"), ("Geist Mono", "geist-mono-latin.woff2"))

MARCADOR_TOKENS = "/*__TOKENS__*/"
MARCADOR_FONTES = "<!--__FONTES__-->"


def tokens_css() -> str:
    return (WEB / "tokens.css").read_text(encoding="utf-8")


def fontes_html() -> str:
    """Os dois @font-face: eixo wght de 400 a 600 (o que o gera_fontes deixou), display=swap. Os fallbacks
    medidos estão no tokens.css."""
    faces = "\n".join(f'@font-face {{ font-family: "{familia}"; src: url(fontes/{arquivo}) format("woff2"); '
                      f'font-weight: 400 600; font-display: swap; }}' for familia, arquivo in FONTES)
    return f"<style>\n{faces}\n</style>"


def copia_fontes(saida: Path) -> None:
    """Os woff2 e a licença (OFL.txt) em `<saida>/fontes/`, ao lado das páginas (docs/ e preview/)."""
    shutil.copytree(FONTES_DIR, saida / "fontes", dirs_exist_ok=True)


def aplica(html: str) -> str:
    """Troca os dois marcadores pelos tokens e pelas fontes."""
    return html.replace(MARCADOR_TOKENS, tokens_css()).replace(MARCADOR_FONTES, fontes_html())


def _wordmark_liso() -> str:
    """O wordmark liso da marca a 17 px de altura (entrega-v2-goatdemo §1: abaixo de 24 px, sem a mira), na cor
    do texto (currentColor); o nome acessível fica no link."""
    svg = (WEB / "marca" / "goatdemo-liso.svg").read_text(encoding="utf-8").strip()
    return svg.replace(' role="img" aria-label="GOAT.demo"', ' width="123" height="17" aria-hidden="true" focusable="false"')


def topo_do_site(atual: str, prancheta: str | None, repo: str) -> str:
    """O topo do site (entrega-sala-de-demo §7): marca e quatro links -- Partidas, Jogadores, Prancheta, GitHub.
    `atual` é "partidas", "jogadores" ou "prancheta" (recebe aria-current). O CSS fica em cada página."""
    from html import escape as e
    # fora da landing, "Partidas" desce direto para a grade (index.html#partidas)
    links = [("partidas", "index.html" if atual == "partidas" else "index.html#partidas", "Partidas"),
             ("jogadores", "jogadores.html", "Jogadores")]
    if prancheta:
        links.append(("prancheta", prancheta, "Prancheta"))
    nav = "".join(f'<a href="{e(h)}"{" aria-current=\"page\"" if k == atual else ""}>{t}</a>' for k, h, t in links)
    return (f'<header class="site-topo">\n'
            f'    <a class="marca" href="index.html" aria-label="GOAT.demo, início">{_wordmark_liso()}</a>\n'
            f'    <nav class="site-nav" aria-label="Principal">{nav}<a href="{e(repo)}">GitHub</a></nav>\n'
            f'  </header>')
