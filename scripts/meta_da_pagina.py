"""Favicon e Open Graph das páginas do site (auditoria, item 5.4; favicon da marca GOAT.demo na decisão 48). Um
lugar só, usado pela landing, pelas páginas de partida e pela prancheta.

O favicon é um SVG embutido (data URI): as páginas continuam autocontidas e
abrem como arquivo local. A imagem do Open Graph é a captura do replay que o
site já publica (`replay.png`); ela só existe no site, então sem URL do site a
página sai sem `og:image`.
"""
from __future__ import annotations

import html
from pathlib import Path
from urllib.parse import quote

from scripts.csp import meta_csp

# A cabra C da marca em #0a0a0a (entrega-v2-goatdemo §1); o SVG versionado usa currentColor, que num favicon
# embutido não tem de onde herdar cor.
_FAVICON_SVG = " ".join((Path(__file__).resolve().parents[1] / "dashboard" / "web" / "marca" / "cabra-c.svg")
                        .read_text(encoding="utf-8").replace("currentColor", "#0a0a0a").split())
FAVICON = "data:image/svg+xml," + quote(_FAVICON_SVG, safe="/:=' ")
IMAGEM_OG = "replay.png"
# o nome do site no fim de todo <title> e og:title (entrega-v2-goatdemo §1: nunca "GOAT" sozinho)
MARCA = "GOAT.demo · Replay de CS2"


def url_do_site(repo_url: str | None) -> str | None:
    """https://github.com/<dono>/<repo> -> https://<dono>.github.io/<repo>/ (GitHub Pages)."""
    if not repo_url:
        return None
    partes = repo_url.rstrip("/").split("/")
    if len(partes) < 5 or partes[2] != "github.com":
        return None
    return f"https://{partes[3].lower()}.github.io/{partes[4]}/"


def meta_tags(titulo: str, descricao: str, site: str | None = None, pagina: str = "",
              hosts_de_conexao: list[str] | None = None) -> str:
    """As linhas do <head>: a CSP (primeiro: só vale para o que vem depois dela), favicon, descrição e Open Graph
    (com imagem só no site). `hosts_de_conexao`: origens extras do `connect-src`, só da prancheta com grupo
    (scripts/csp.py)."""
    e = lambda s: html.escape(s, quote=True)  # noqa: E731
    linhas = [
        meta_csp(hosts_de_conexao),
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
