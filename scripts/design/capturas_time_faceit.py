"""P1c: a lista de Partidas (landing) e o cabeçalho de uma partida da FACEIT com o nome do time que a demo grava (decisão 65).

    py -3.12 -m scripts.build_site
    py -3.12 -m scripts.design.capturas_time_faceit <pasta_de_saida> [match_01]

375 e 1440 x claro e escuro; a janela (a lista depois de clicar em FACEIT; o topo do cabeçalho). Escreve também o texto dos nomes que a página mostra.
"""
from __future__ import annotations

import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

RAIZ = Path(__file__).resolve().parents[2]
TAMANHOS = [("375", 375, 812), ("1440", 1440, 900)]


def main() -> None:
    saida = Path(sys.argv[1]); saida.mkdir(parents=True, exist_ok=True)
    partida = sys.argv[2] if len(sys.argv) > 2 else "match_01"
    with sync_playwright() as p:
        nav = p.chromium.launch(channel="chrome")
        for tema in ("claro", "escuro"):
            for rotulo, w, h in TAMANHOS:
                ctx = nav.new_context(viewport={"width": w, "height": h})
                ctx.add_init_script(f"try {{ localStorage.setItem('goatdemo:tema', '{tema}'); }} catch (e) {{}}")
                for nome, arq in (("lista-de-partidas", "index.html"), (f"cabecalho-{partida}", f"{partida}.html")):
                    pg = ctx.new_page(); pg.goto((RAIZ / "docs" / arq).as_uri()); pg.wait_for_timeout(600)
                    if nome == "lista-de-partidas":
                        pg.get_by_role("button", name="FACEIT").first.click(); pg.wait_for_timeout(300)      # a landing abre só nas profissionais
                        pg.get_by_role("heading", name="Partidas").first.evaluate("e => { e.scrollIntoView(true); window.scrollBy(0, -90); }")      # a lista no topo da janela
                        pg.wait_for_timeout(200)
                    linhas = [x.strip() for x in pg.inner_text("body").splitlines() if "Time de" in x]
                    print(f"{rotulo} {tema} {nome}: {len(linhas)} linhas com 'Time de'", linhas[:6])
                    pg.screenshot(path=str(saida / f"{nome}-{rotulo}-{tema}.png")); pg.close()      # a janela, legível; a página inteira a 375 passa de 11.000 px
                ctx.close()
        nav.close()


if __name__ == "__main__":
    main()
