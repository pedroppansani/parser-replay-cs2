"""Roteiro de interação contra `docs/`: erros de JS em todas as páginas, abas por teclado
(A9) e o replay tocando. Adaptado do roteiro do protótipo (entrega §15).

    py -3.12 -m scripts.design.interacao

A prancheta tem testes de comportamento próprios (tests/test_prancheta_*.py); aqui só
se confere que a página abre sem erro.
"""
import sys
sys.dont_write_bytecode = True
from playwright.sync_api import sync_playwright

from scripts.design._comum import chrome, url_de

PAGINAS = ["index.html", "match_02.html", "prancheta_de_mirage.html", "jogadores.html"]


def main() -> int:
    p = sync_playwright().start(); b = chrome(p)
    erros, falhas = [], 0
    for pag in PAGINAS:
        pg = b.new_page(viewport={"width": 1440, "height": 900})
        pg.on("pageerror", lambda e, pag=pag: erros.append(f"{pag}: {e}"))
        pg.goto(url_de(pag)); pg.wait_for_timeout(800)
        if pag == "match_02.html":
            # A9: foco na primeira aba, seta para a direita vai para a próxima e mostra o painel; End vai para a última
            abas = pg.eval_on_selector_all("[role=tab]", "ts => ts.map(t => t.dataset.tab)")
            pg.focus('[role=tab][data-tab="%s"]' % abas[0]); pg.keyboard.press("ArrowRight"); pg.wait_for_timeout(200)
            foco = pg.evaluate("document.activeElement.dataset.tab")
            painel = pg.evaluate("(a) => { const p = document.querySelector('[data-panel=\"' + a + '\"]'); return !!p && !p.hidden; }", foco)
            ok1 = foco == abas[1] and painel
            pg.keyboard.press("End"); ultima = pg.evaluate("document.activeElement.dataset.tab"); ok2 = ultima == abas[-1]
            print(f"A9: seta leva a {foco!r} (painel visível: {painel}); End leva a {ultima!r}  {'PASSA' if ok1 and ok2 else 'FALHA'}")
            falhas += not (ok1 and ok2)
            pg.click('[data-tab="replay"]'); pg.wait_for_timeout(200)
            antes = pg.eval_on_selector("#scrub", "e => +e.value")
            pg.click("#play"); pg.wait_for_timeout(900); depois = pg.eval_on_selector("#scrub", "e => +e.value"); pg.click("#play")
            print(f"tocar avança o trilho: {antes} -> {depois}  {'PASSA' if depois > antes else 'FALHA'}")
            falhas += not (depois > antes)
        pg.close()
    print("erros de JS:", erros or "nenhum")
    b.close(); p.stop()
    return 1 if (erros or falhas) else 0


if __name__ == "__main__":
    raise SystemExit(main())
