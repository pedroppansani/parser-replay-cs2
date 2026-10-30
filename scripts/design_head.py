"""O <head> da direção visual: tokens e fontes (decisões 44 e 48).

Um lugar só, usado pela página da partida, pela prancheta, pela página de jogadores e pela
landing. Os tokens (cores, fontes, espaços, raios) moram em `dashboard/web/tokens.css`; as fontes
são duas famílias, Geist e Geist Mono, hospedadas no próprio site (entrega-v2-goatdemo §3.1): os
woff2 ficam em `dashboard/web/fontes/` e o build os copia para `fontes/`, ao lado das páginas.
Nenhum pedido ao Google Fonts. O `preload` das duas fontes entra por um script mínimo no <head>, SÓ quando a página vem
por HTTP (o Pages): em `file://` o preload com crossorigin é bloqueado por CORS e vira erro no console (medido no
protótipo), e a página continua abrindo como arquivo local sem ele (v2-7, medido no Pages).
"""
from __future__ import annotations

import re
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


# `fallback` (e não `swap`): o texto espera até ~100 ms pela fonte antes de usar o substituto; com o preload a fonte
# costuma já estar baixada nessa hora e o texto não troca de fonte na frente de quem lê (CLS). Medido na v2-7 (Fast 4G,
# CPU 4x, Linux sem Arial): a landing a 375 px foi de CLS 0,085 para 0. `optional` foi descartado: na partida e na
# prancheta a página ficava a visita inteira no substituto.
FONT_DISPLAY = "fallback"


def fontes_html() -> str:
    """O preload das duas fontes (só por HTTP) e os dois @font-face: eixo wght de 400 a 600 (o que o gera_fontes
    deixou). Os fallbacks medidos estão no tokens.css."""
    arquivos = ",".join(f'"{arquivo}"' for _, arquivo in FONTES)
    preload = ('<script>if (location.protocol !== "file:") [' + arquivos + '].forEach(function (a) { '
               'var l = document.createElement("link"); l.rel = "preload"; l.as = "font"; l.type = "font/woff2"; '
               'l.crossOrigin = "anonymous"; l.href = "fontes/" + a; document.head.appendChild(l); });</script>')
    faces = "\n".join(f'@font-face {{ font-family: "{familia}"; src: url(fontes/{arquivo}) format("woff2"); '
                      f'font-weight: 400 600; font-display: {FONT_DISPLAY}; }}' for familia, arquivo in FONTES)
    return f"{preload}\n<style>\n{faces}\n</style>"


def copia_fontes(saida: Path) -> None:
    """Os woff2 e a licença (OFL.txt) em `<saida>/fontes/`, ao lado das páginas (docs/ e preview/)."""
    shutil.copytree(FONTES_DIR, saida / "fontes", dirs_exist_ok=True)


def v2_css() -> str:
    return (WEB / "v2.css").read_text(encoding="utf-8")


def v2_js() -> str:
    """O comportamento comum da v2 (--nav-h, foco abaixo da navbar, diálogo), para ir inline na página."""
    return (WEB / "v2.js").read_text(encoding="utf-8")


# O tema escolhido na landing (Fase T): um arquivo pequeno, ao lado das páginas, carregado no <head> antes de qualquer
# pintura (sem script inline: a CSP não muda). A prancheta é sempre violeta e não o carrega.
TEMA_JS = "tema.js"


def tema_html(html: str) -> str:
    """A tag do tema.js; vazia na página violeta (a prancheta), lida só na tag <html>."""
    return "" if re.search(r'<html[^>]*\sdata-tema="violeta"', html) else f'<script src="{TEMA_JS}"></script>\n'


def copia_tema(saida: Path) -> None:
    """O `tema.js` em `<saida>/`, ao lado das páginas (docs/ e preview/)."""
    shutil.copyfile(WEB / TEMA_JS, saida / TEMA_JS)


def aplica(html: str) -> str:
    """Troca os marcadores pelos tokens, pelo tema, pelas fontes e pelo CSS da v2."""
    # o tema.js depois do preload das fontes: o pedido dele não atrasa a descoberta das fontes
    return (html.replace(MARCADOR_TOKENS, tokens_css()).replace(MARCADOR_FONTES, fontes_html() + "\n" + tema_html(html))
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


# O botão de tema (Fase T), só na navbar da landing: o nome é "Escuro" e o aria-pressed diz se o escuro está ligado
TEXTO_DO_TEMA = "Escuro"
_LUA = ('<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" '
        'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false">'
        '<path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z"/></svg>')


def botao_do_tema() -> str:
    return (f'<button class="tema-botao" type="button" aria-pressed="false">{_LUA}'
            f'<span>{TEXTO_DO_TEMA}</span></button>')


def topo_do_site(atual: str, prancheta: str | None, repo: str) -> str:
    """A navbar do site (entrega-v2-goatdemo §5.1): a marca (cabra C + wordmark, leva à landing) e três links --
    Partidas, Jogadores, Prancheta --, sem GitHub nem botão de ação (o GitHub fica no rodapé da landing, dúvida 1
    do plano). `atual` é "partidas", "jogadores" ou "prancheta" (recebe aria-current); na landing ("partidas") entra o
    botão de tema (Fase T). Com o `v2.css` (marcador
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
            f'    <nav class="site-nav" aria-label="Principal">{nav}</nav>{botao_do_tema() if atual == "partidas" else ""}\n'
            f'  </header>')
