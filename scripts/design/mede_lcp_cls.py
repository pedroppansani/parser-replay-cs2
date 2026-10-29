"""
LCP e CLS do site (A12, A26), a 375 e a 1440 px, rede "Fast 4G" e CPU 4x mais lenta (Chrome via Playwright + CDP).

Mede o site PUBLICADO (`MEDE_URL=https://pedroppansani.github.io/parser-replay-cs2`) ou, sem `MEDE_URL`, a pasta
`docs/` (ou `MEDE_PASTA`) servida por HTTP local (python -m http.server, só leitura): em file:// a limitação de rede
não se aplica.

Perfil "Fast 4G" (o do DevTools): 9 Mbit/s de descida, 1,5 Mbit/s de subida, latência 60 ms x 2,75 = 165 ms.
Cada página é medida 5 vezes por largura, com cache limpo; o relatório dá a mediana e o pior do LCP e do CLS, o
elemento do LCP e quando cada fonte (Geist, Geist Mono) terminou de chegar, que é o que o `preload` muda (v2-7).

    py -3.12 -m scripts.design.mede_lcp_cls
    MEDE_URL=https://pedroppansani.github.io/parser-replay-cs2 py -3.12 -m scripts.design.mede_lcp_cls

Critérios (v2-7, pedido do Pedro): CLS 0 em todas; LCP da landing < 2,5 s. A landing é medida com `?agente=tr`
(o sorteio do agente é aleatório e deixaria a medida instável; plano v2-0 §4.8).
"""
import os
import statistics
import subprocess
import sys
import time

sys.dont_write_bytecode = True
from playwright.sync_api import sync_playwright

from scripts.design._comum import DOCS, chrome

PASTA = os.environ.get("MEDE_PASTA") or str(DOCS)
BASE = (os.environ.get("MEDE_URL") or "").rstrip("/")
PORTA = 8765
MEDIDAS = 5
LARGURAS = [(375, 667), (1440, 900)]
PAGINAS = ["index.html?agente=tr", "match_02.html", "match_02.html#perfil", "prancheta_de_mirage.html"]
LCP_MAXIMO_S = {"index.html?agente=tr": 2.5}   # o LCP da partida depende dos megabytes de dado embutidos
CLS_MAXIMO = 0.0                                 # a meta do Pedro na v2-7
REDE = {"offline": False, "latency": 165, "downloadThroughput": 9_000_000 / 8, "uploadThroughput": 1_500_000 / 8}
JS_OBS = """
window.__lcp = 0; window.__lcpEl = ""; window.__cls = 0;
new PerformanceObserver(l => { for (const e of l.getEntries()) { window.__lcp = e.startTime; window.__lcpEl = (e.element && (e.element.tagName + "." + e.element.className)) || e.url || ""; } })
  .observe({type: "largest-contentful-paint", buffered: true});
new PerformanceObserver(l => { for (const e of l.getEntries()) if (!e.hadRecentInput) window.__cls += e.value; })
  .observe({type: "layout-shift", buffered: true});
"""
FONTES_JS = """() => Object.fromEntries(performance.getEntriesByType("resource").filter(r => r.name.endsWith(".woff2"))
  .map(r => [r.name.split("/").pop(), Math.round(r.responseEnd)]))"""


def mede(b, url: str, largura: int, altura: int) -> dict:
    ctx = b.new_context(viewport={"width": largura, "height": altura}, device_scale_factor=2 if largura < 641 else 1)
    pg = ctx.new_page(); cdp = ctx.new_cdp_session(pg)
    cdp.send("Network.enable"); cdp.send("Network.setCacheDisabled", {"cacheDisabled": True})
    cdp.send("Network.emulateNetworkConditions", REDE)
    cdp.send("Emulation.setCPUThrottlingRate", {"rate": 4})
    pg.add_init_script(JS_OBS)
    pg.goto(url, wait_until="load", timeout=180000)
    pg.wait_for_timeout(4000)
    r = pg.evaluate("({lcp: window.__lcp, el: window.__lcpEl, cls: window.__cls})")
    r["fontes"] = pg.evaluate(FONTES_JS)
    ctx.close()
    return r


def main(paginas: list[str] | None = None) -> int:
    srv = None
    if not BASE:
        srv = subprocess.Popen([sys.executable, "-B", "-m", "http.server", str(PORTA), "--bind", "127.0.0.1"], cwd=PASTA,
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(1.5)
    base = BASE or f"http://127.0.0.1:{PORTA}"
    falhou = False
    try:
        p = sync_playwright().start(); b = chrome(p)
        print(f"{base} · Fast 4G (9/1,5 Mbit/s, 165 ms) · CPU 4x · {MEDIDAS} medidas por página e largura, cache limpo\n")
        print("| página | largura | LCP mediana (pior) | CLS mediana (pior) | elemento do LCP | fontes prontas (mediana, ms) | |")
        print("|---|---|---|---|---|---|---|")
        for pag in (paginas or PAGINAS):
            for largura, altura in LARGURAS:
                rs = [mede(b, f"{base}/{pag}", largura, altura) for _ in range(MEDIDAS)]
                lcps, clss = [r["lcp"] / 1000 for r in rs], [r["cls"] for r in rs]
                els = [r["el"] for r in rs]
                fontes = {f: int(statistics.median(r["fontes"].get(f, 0) for r in rs)) for f in sorted({f for r in rs for f in r["fontes"]})}
                lim = LCP_MAXIMO_S.get(pag)
                ok = max(clss) <= CLS_MAXIMO and (lim is None or statistics.median(lcps) < lim)
                falhou = falhou or not ok
                print(f"| {pag} | {largura} | {statistics.median(lcps):.2f} s ({max(lcps):.2f}) | "
                      f"{statistics.median(clss):.3f} ({max(clss):.3f}) | {max(set(els), key=els.count)} | "
                      f"{', '.join(f'{f} {ms}' for f, ms in fontes.items()) or '-'} | {'PASSA' if ok else 'FALHA'} |", flush=True)
        b.close(); p.stop()
    finally:
        if srv:
            srv.terminate()
    return 1 if falhou else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:] or None))
