"""
LCP e CLS (A12) do site gerado, 375x667, rede "Fast 4G" e CPU 4x mais lenta (Chrome via Playwright + CDP).

`docs/` é servido por HTTP local (python -m http.server, só leitura): em file:// a limitação de
rede não se aplica. As fontes vêm do Google Fonts, pela rede limitada.

Perfil "Fast 4G" (o do DevTools): 9 Mbit/s de descida, 1,5 Mbit/s de subida, latência 60 ms x 2,75 = 165 ms.
Cada página é medida 5 vezes, com cache limpo; o relatório dá a mediana e o pior.

    py -3.12 -m scripts.design.mede_lcp_cls

Critérios do site real: landing LCP < 2,5 s e CLS < 0,1; partida só CLS < 0,1 (o LCP da
partida depende dos megabytes de dados embutidos, engenharia de build).
"""
import statistics, subprocess, sys, time, os
sys.dont_write_bytecode = True
from playwright.sync_api import sync_playwright

from scripts.design._comum import DOCS, chrome

PASTA = str(DOCS)
PORTA = 8765
PAGINAS = ["index.html", "match_02.html"]
LIMITES = {"index.html": (2.5, 0.1), "match_02.html": (None, 0.1)}   # (LCP em s, CLS)
REDE = {"offline": False, "latency": 165, "downloadThroughput": 9_000_000 / 8, "uploadThroughput": 1_500_000 / 8}
JS_OBS = """
window.__lcp = 0; window.__lcpEl = ""; window.__cls = 0;
new PerformanceObserver(l => { for (const e of l.getEntries()) { window.__lcp = e.startTime; window.__lcpEl = (e.element && (e.element.tagName + "." + e.element.className)) || e.url || ""; } })
  .observe({type: "largest-contentful-paint", buffered: true});
new PerformanceObserver(l => { for (const e of l.getEntries()) if (!e.hadRecentInput) window.__cls += e.value; })
  .observe({type: "layout-shift", buffered: true});
"""

def main() -> int:
    srv = subprocess.Popen([sys.executable, "-B", "-m", "http.server", str(PORTA), "--bind", "127.0.0.1"], cwd=PASTA,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(1.5)
    falhou = False
    try:
        p = sync_playwright().start(); b = chrome(p)
        print("375x667 · Fast 4G (9/1,5 Mbit/s, 165 ms) · CPU 4x · 5 medidas por página, cache limpo\n")
        for pag in PAGINAS:
            lcps, clss, els = [], [], []
            for _ in range(5):
                ctx = b.new_context(viewport={"width": 375, "height": 667}, device_scale_factor=2)
                pg = ctx.new_page(); cdp = ctx.new_cdp_session(pg)
                cdp.send("Network.enable"); cdp.send("Network.setCacheDisabled", {"cacheDisabled": True})
                cdp.send("Network.emulateNetworkConditions", REDE)
                cdp.send("Emulation.setCPUThrottlingRate", {"rate": 4})
                pg.add_init_script(JS_OBS)
                pg.goto(f"http://127.0.0.1:{PORTA}/{pag}", wait_until="load", timeout=120000)
                pg.wait_for_timeout(4000)
                r = pg.evaluate("({lcp: window.__lcp, el: window.__lcpEl, cls: window.__cls})")
                lcps.append(r["lcp"]); clss.append(r["cls"]); els.append(r["el"])
                ctx.close()
            lim_lcp, lim_cls = LIMITES[pag]
            ok = (lim_lcp is None or statistics.median(lcps) / 1000 < lim_lcp) and statistics.median(clss) < lim_cls
            falhou = falhou or not ok
            print(f"{pag:<14} LCP mediana {statistics.median(lcps)/1000:5.2f} s (pior {max(lcps)/1000:5.2f} s)   "
                  f"CLS mediana {statistics.median(clss):.3f} (pior {max(clss):.3f})   elemento do LCP: {max(set(els), key=els.count)}   "
                  f"{'PASSA' if ok else 'FALHA'}")
        b.close(); p.stop()
    finally:
        srv.terminate()
    return 1 if falhou else 0

if __name__ == "__main__":
    raise SystemExit(main())
