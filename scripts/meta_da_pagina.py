"""Favicon e Open Graph das páginas do site (auditoria, item 5.4). Um lugar só,
usado pela landing, pelas páginas de partida e pela prancheta.

O favicon é um SVG embutido (data URI): as páginas continuam autocontidas e
abrem como arquivo local. A imagem do Open Graph é a captura do replay que o
site já publica (`replay.png`); ela só existe no site, então sem URL do site a
página sai sem `og:image`.
"""
from __future__ import annotations

import html
from urllib.parse import quote

# Uma mira (anel e cruz) na tinta da página, com o ponto no azul do Time A.
_FAVICON_SVG = (
    "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'>"
    "<circle cx='16' cy='16' r='11' fill='none' stroke='#0f1620' stroke-width='3'/>"
    "<path d='M16 1v8M16 23v8M1 16h8M23 16h8' stroke='#0f1620' stroke-width='3'/>"
    "<circle cx='16' cy='16' r='3.5' fill='#2a78d6'/></svg>"
)
FAVICON = "data:image/svg+xml," + quote(_FAVICON_SVG, safe="/:=' ")
IMAGEM_OG = "replay.png"


def url_do_site(repo_url: str | None) -> str | None:
    """https://github.com/<dono>/<repo> -> https://<dono>.github.io/<repo>/ (GitHub Pages)."""
    if not repo_url:
        return None
    partes = repo_url.rstrip("/").split("/")
    if len(partes) < 5 or partes[2] != "github.com":
        return None
    return f"https://{partes[3].lower()}.github.io/{partes[4]}/"


def meta_tags(titulo: str, descricao: str, site: str | None = None, pagina: str = "") -> str:
    """As linhas do <head>: favicon, descrição e Open Graph (com imagem só no site)."""
    e = lambda s: html.escape(s, quote=True)  # noqa: E731
    linhas = [
        f'<link rel="icon" href="{e(FAVICON)}">',
        f'<meta name="description" content="{e(descricao)}">',
        '<meta property="og:type" content="website">',
        f'<meta property="og:title" content="{e(titulo)}">',
        f'<meta property="og:description" content="{e(descricao)}">',
    ]
    if site:
        linhas += [f'<meta property="og:url" content="{e(site + pagina)}">',
                   f'<meta property="og:image" content="{e(site + IMAGEM_OG)}">',
                   '<meta name="twitter:card" content="summary_large_image">']
    return "\n".join(linhas)
