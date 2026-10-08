"""Favicon e Open Graph das páginas do site (auditoria, item 5.4; favicon novo na decisão 44). Um lugar só,
usado pela landing, pelas páginas de partida e pela prancheta.

O favicon é um SVG embutido (data URI): as páginas continuam autocontidas e
abrem como arquivo local. A imagem do Open Graph é a captura do replay que o
site já publica (`replay.png`); ela só existe no site, então sem URL do site a
página sai sem `og:image`.
"""
from __future__ import annotations

import html
from urllib.parse import quote

# Duas bolinhas, CT e TR, no fundo do tema (entrega-sala-de-demo §10): as cores são os tokens
# --fundo, --ct e --tr de dashboard/web/tokens.css (o favicon é um SVG embutido e não lê CSS).
_FAVICON_SVG = (
    "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'>"
    "<rect width='32' height='32' rx='6' fill='#0b0f14'/>"
    "<circle cx='11' cy='16' r='6' fill='#4a90e8'/><circle cx='21' cy='16' r='6' fill='#e0a23a'/></svg>"
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
