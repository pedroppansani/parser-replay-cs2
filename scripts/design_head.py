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
# O CSS novo da v2 (navbar flutuante) mora em dashboard/web/v2.css, nunca no template.html (plano v2-0 §4.12);
# entra só na página que tem o marcador (desde a v2-5, todas: landing, partida, jogadores e prancheta)
MARCADOR_V2 = "/*__V2__*/"


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


def v2_css() -> str:
    return (WEB / "v2.css").read_text(encoding="utf-8")


def v2_js() -> str:
    """O comportamento comum da v2 (--nav-h, foco abaixo da navbar, diálogo), para ir inline na página."""
    return (WEB / "v2.js").read_text(encoding="utf-8")


def aplica(html: str) -> str:
    """Troca os marcadores pelos tokens, pelas fontes e pelo CSS da v2."""
    return (html.replace(MARCADOR_TOKENS, tokens_css()).replace(MARCADOR_FONTES, fontes_html())
            .replace(MARCADOR_V2, v2_css()))


def _wordmark_liso() -> str:
    """O wordmark liso da marca a 17 px de altura (entrega-v2-goatdemo §1: abaixo de 24 px, sem a mira), na cor
    do texto (currentColor); o nome acessível fica no link."""
    svg = (WEB / "marca" / "goatdemo-liso.svg").read_text(encoding="utf-8").strip()
    return svg.replace(' role="img" aria-label="GOAT.demo"', ' width="123" height="17" aria-hidden="true" focusable="false"')


def _cabra() -> str:
    """A cabra C da marca a 30 px (entrega-v2-goatdemo §5.1), na cor do texto; o nome acessível fica no link."""
    svg = (WEB / "marca" / "cabra-c.svg").read_text(encoding="utf-8").strip()
    return svg.replace(' role="img" aria-label="Cabra Pico"', ' width="30" height="30" aria-hidden="true" focusable="false"')


def topo_do_site(atual: str, prancheta: str | None, repo: str) -> str:
    """A navbar do site (entrega-v2-goatdemo §5.1): a marca (cabra C + wordmark, leva à landing) e três links --
    Partidas, Jogadores, Prancheta --, sem GitHub nem botão de ação (o GitHub fica no rodapé da landing, dúvida 1
    do plano). `atual` é "partidas", "jogadores" ou "prancheta" (recebe aria-current). Com o `v2.css` (marcador
    /*__V2__*/) ela flutua em pílula; sem ele, cada página a desenha com o CSS dela. `repo` fica na assinatura
    para as páginas que chamam."""
    from html import escape as e
    # fora da landing, "Partidas" desce direto para a grade (index.html#partidas)
    links = [("partidas", "index.html" if atual == "partidas" else "index.html#partidas", "Partidas"),
             ("jogadores", "jogadores.html", "Jogadores")]
    if prancheta:
        links.append(("prancheta", prancheta, "Prancheta"))
    nav = "".join(f'<a href="{e(h)}"{" aria-current=\"page\"" if k == atual else ""}>{t}</a>' for k, h, t in links)
    return (f'<header class="site-topo">\n'
            f'    <a class="marca" href="index.html" aria-label="GOAT.demo, início">{_cabra()}{_wordmark_liso()}</a>\n'
            f'    <nav class="site-nav" aria-label="Principal">{nav}</nav>\n'
            f'  </header>')
