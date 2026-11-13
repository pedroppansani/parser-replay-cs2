"""CR1a: o LCP da prancheta de antes e de depois, e o que a página pede de rede (o `comandos/plano.js` só pode ser pedido quando a aba Comandos abre).

    py -3.12 -m scripts.design.mede_lcp_da_prancheta PASTA_DOCS_ANTES PASTA_DOCS_DEPOIS [rodadas] [mapa]

Cada pasta é um site gerado (`docs/`), servido por HTTP local (como em produção; a política de segurança vale). Cada medida usa um contexto novo (sem cache), a
janela de cada um dos 3 tamanhos (375x812, 1366x657, 1440x900) e, além do normal, o processador 4 vezes mais lento (um celular fraco). O LCP é o da própria
página (`largest-contentful-paint`); também sai o tamanho do HTML e a lista de arquivos de script pedidos antes e depois de abrir a aba.
"""
from __future__ import annotations

import functools
import http.server
import socketserver
import statistics
import sys
import threading
from pathlib import Path

from playwright.sync_api import sync_playwright

TAMANHOS = [("375", 375, 812), ("1366", 1366, 657), ("1440", 1440, 900)]
LCP_JS = """() => new Promise(res => { let v = null; new PerformanceObserver(l => { for (const e of l.getEntries()) v = e.startTime; }).observe({ type: 'largest-contentful-paint', buffered: true });
  setTimeout(() => res(v), 1500); })"""


def serve(pasta: Path):
    h = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(pasta))
    h.log_message = lambda *a, **k: None
    class Q(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *a, **k):
            pass
    srv = socketserver.TCPServer(("127.0.0.1", 0), functools.partial(Q, directory=str(pasta)))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, srv.server_address[1]


def mede(nav, porta: int, mapa: str, w: int, h: int, lento: bool, n: int):
    lcps, html_kb = [], 0
    for _ in range(n):
        ctx = nav.new_context(viewport={"width": w, "height": h})
        pg = ctx.new_page()
        if lento:
            cdp = ctx.new_cdp_session(pg)
            cdp.send("Emulation.setCPUThrottlingRate", {"rate": 4})
        pg.goto(f"http://127.0.0.1:{porta}/prancheta_{mapa}.html", wait_until="load")
        lcps.append(pg.evaluate(LCP_JS))
        html_kb = len(pg.content()) // 1024
        ctx.close()
    return lcps, html_kb


def rede(nav, porta: int, mapa: str):
    """Os scripts pedidos antes e depois de abrir a aba Comandos."""
    ctx = nav.new_context(viewport={"width": 1366, "height": 657})
    pg = ctx.new_page()
    pedidos: list[str] = []
    pg.on("request", lambda r: pedidos.append(r.url.rsplit("/", 2)[-2] + "/" + r.url.rsplit("/", 1)[-1]) if r.url.endswith(".js") else None)
    pg.goto(f"http://127.0.0.1:{porta}/prancheta_{mapa}.html", wait_until="load")
    pg.wait_for_function("() => Prancheta._interno.S.estado !== null")
    pg.wait_for_timeout(1500)
    antes = sorted(set(pedidos)); pedidos.clear()
    pg.evaluate("() => Prancheta._interno.abaDoPainel('comandos')")
    pg.wait_for_timeout(1500)
    depois = sorted(set(pedidos))
    ok = pg.evaluate("() => typeof PlanoDeComandos !== 'undefined'")
    ctx.close()
    return antes, depois, ok


def main() -> int:
    antes_dir, depois_dir = Path(sys.argv[1]), Path(sys.argv[2])
    n = int(sys.argv[3]) if len(sys.argv) > 3 else 15
    mapa = sys.argv[4] if len(sys.argv) > 4 else "de_mirage"
    sa, pa = serve(antes_dir)
    sd, pd = serve(depois_dir)
    with sync_playwright() as p:
        nav = p.chromium.launch(channel="chrome")
        print(f"{mapa}, {n} medidas por célula, contexto novo, sem cache")
        print(f"{'janela':8} {'CPU':6} {'LCP antes (mediana / p75)':30} {'LCP depois (mediana / p75)':30} {'HTML antes':11} {'HTML depois':11}")
        for rotulo, w, h in TAMANHOS:
            for lento in (False, True):
                la, ka = mede(nav, pa, mapa, w, h, lento, n)
                ld, kd = mede(nav, pd, mapa, w, h, lento, n)
                q = lambda v: sorted(v)[int(0.75 * (len(v) - 1))]
                print(f"{rotulo:8} {'4x' if lento else '1x':6} {statistics.median(la):8.0f} / {q(la):6.0f} ms{'':8} {statistics.median(ld):8.0f} / {q(ld):6.0f} ms{'':8} {ka:7} KB   {kd:7} KB")
        for nome, porta in (("antes ", pa), ("depois", pd)):
            a, d, ok = rede(nav, porta, mapa)
            print(f"rede {nome}: scripts pedidos ao carregar = {a}; ao abrir a aba Comandos = {d}; PlanoDeComandos existe depois = {ok}")
        nav.close()
    sa.shutdown(); sd.shutdown()
    return 0


if __name__ == "__main__":
    sys.exit(main())
