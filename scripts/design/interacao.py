"""Roteiro de interação contra `docs/`: erros de JS em todas as páginas, abas por teclado
(A9) e o replay tocando. Adaptado do roteiro do protótipo (entrega §15).

    py -3.12 -m scripts.design.interacao

A10 (prancheta, design-E): clique na régua move o relógio; Home volta a 1:55; Reproduzir corre o
relógio; Cache mostra o aviso e desliga "Buscar arremesso real". O "clique traçando acrescenta
ponto" é conferido pelos testes de comportamento (tests/test_prancheta_fluida.py, traçar caminho).
"""
import sys
sys.dont_write_bytecode = True
from playwright.sync_api import sync_playwright

from scripts.design._comum import chrome, url_de

PAGINAS = ["index.html", "match_02.html", "prancheta_de_mirage.html", "jogadores.html"]


def a10(pg) -> int:
    """A10 na prancheta da Mirage: régua, Home e Reproduzir. Devolve quantas verificações falharam."""
    relogio = lambda: pg.inner_text("#pr-relogio-grande").split(chr(10))[0].strip()  # noqa: E731
    falhas = 0
    inicio = relogio()
    r = pg.locator("#pr-regua").bounding_box()
    pg.mouse.click(r["x"] + r["width"] * 0.5, r["y"] + r["height"] / 2); pg.wait_for_timeout(200)
    meio = relogio()
    ok = inicio == "1:55" and meio != inicio
    print(f"A10: clique na régua move o relógio: {inicio} -> {meio}  {'PASSA' if ok else 'FALHA'}"); falhas += not ok
    pg.focus("#pr-cabecote"); pg.keyboard.press("Home"); pg.wait_for_timeout(200)
    ok = relogio() == "1:55"
    print(f"A10: Home volta a 1:55 ({relogio()})  {'PASSA' if ok else 'FALHA'}"); falhas += not ok
    # o relógio corre na reprodução "no relógio" (tática no tempo, modelo 3): a mesma tática dos testes
    from tests.test_prancheta_tempo_browser import _tatica_no_tempo
    _tatica_no_tempo(pg); pg.wait_for_timeout(200)
    antes = relogio()
    pg.click("#pr-reproduzir"); pg.wait_for_timeout(4000); depois = relogio(); pg.keyboard.press("Escape")
    ok = depois != antes
    print(f"A10: Reproduzir corre o relógio: {antes} -> {depois}  {'PASSA' if ok else 'FALHA'}"); falhas += not ok
    return falhas


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
        if pag == "prancheta_de_mirage.html":
            falhas += a10(pg)
        pg.close()
    pg = b.new_page(viewport={"width": 1440, "height": 900})
    pg.on("pageerror", lambda e: erros.append(f"prancheta_de_cache.html: {e}"))
    pg.goto(url_de("prancheta_de_cache.html")); pg.wait_for_timeout(800)
    aviso = pg.is_visible("#pr-aviso-mapa") and "não tem partidas no corpus" in pg.inner_text("#pr-aviso-mapa")
    desligado = pg.locator('aside [data-ferramenta="buscar"]').is_disabled()
    print(f"A10: Cache mostra o aviso ({aviso}) e desliga \"Buscar arremesso real\" ({desligado})  {'PASSA' if aviso and desligado else 'FALHA'}")
    falhas += not (aviso and desligado)
    pg.close()
    print("erros de JS:", erros or "nenhum")
    b.close(); p.stop()
    return 1 if (erros or falhas) else 0


if __name__ == "__main__":
    raise SystemExit(main())
