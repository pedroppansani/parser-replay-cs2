"""P2b: o LCP da prancheta e da página da partida, antes e depois de o leitor (prancheta) e a seção Comandos (partida) saírem do HTML.

    py -3.12 -m scripts.design.mede_lcp_p2b PASTA_DOCS_ANTES PASTA_DOCS_DEPOIS [medidas_por_celula]

Cada pasta é um site gerado (`docs/`), servido por HTTP local. Cada medida usa um contexto novo (sem cache), alternando antes e depois; células: as duas páginas (a prancheta da Mirage e a
partida match_43) nos 3 tamanhos (375x812, 1366x657, 1440x900) com a CPU normal e, a 375, também com a CPU 4 vezes mais lenta. Sai a mediana e o p75 de cada lado, a diferença das medianas e o
tamanho do HTML; uma célula que piora mais de 30 ms na mediana é marcada."""
from __future__ import annotations

import statistics
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

from scripts.design.mede_lcp_da_prancheta import LCP_JS, serve

PAGINAS = [("prancheta", "prancheta_de_mirage.html"), ("partida", "match_43.html")]
CELULAS = [("375", 375, 812, False), ("1366", 1366, 657, False), ("1440", 1440, 900, False), ("375", 375, 812, True)]
LIMITE_MS = 30


def mede(nav, porta: int, arquivo: str, w: int, h: int, lento: bool):
    ctx = nav.new_context(viewport={"width": w, "height": h})
    pg = ctx.new_page()
    if lento:
        ctx.new_cdp_session(pg).send("Emulation.setCPUThrottlingRate", {"rate": 4})
    pg.goto(f"http://127.0.0.1:{porta}/{arquivo}", wait_until="load")
    v = pg.evaluate(LCP_JS)
    kb = len(pg.content()) // 1024
    ctx.close()
    return v, kb


def main() -> int:
    antes, depois = Path(sys.argv[1]), Path(sys.argv[2])
    n = int(sys.argv[3]) if len(sys.argv) > 3 else 40
    so = sys.argv[4] if len(sys.argv) > 4 else None      # só uma das páginas ("prancheta" ou "partida"), para repetir uma célula com mais medidas
    sa, pa = serve(antes)
    sd, pd = serve(depois)
    ruim = 0
    with sync_playwright() as p:
        nav = p.chromium.launch(channel="chrome")
        print(f"{n} medidas por célula, contexto novo, sem cache, alternando antes e depois")
        print(f"{'página':10} {'janela':7} {'CPU':4} {'antes (mediana / p75)':24} {'depois (mediana / p75)':24} {'diferença':10} {'HTML antes':11} {'HTML depois':11}")
        for nome, arquivo in [x for x in PAGINAS if so in (None, x[0])]:
            for rotulo, w, h, lento in CELULAS:
                la, ld, ka, kd = [], [], 0, 0
                for i in range(n):
                    for quem in (("a", "d") if i % 2 == 0 else ("d", "a")):
                        v, k = mede(nav, pa if quem == "a" else pd, arquivo, w, h, lento)
                        if quem == "a":
                            la.append(v); ka = k
                        else:
                            ld.append(v); kd = k
                q = lambda v: sorted(v)[int(0.75 * (len(v) - 1))]
                dif = statistics.median(ld) - statistics.median(la)
                marca = "  <-- PIOR" if dif > LIMITE_MS else ""
                ruim += dif > LIMITE_MS
                print(f"{nome:10} {rotulo:7} {'4x' if lento else '1x':4} {statistics.median(la):7.0f} / {q(la):6.0f} ms   {statistics.median(ld):7.0f} / {q(ld):6.0f} ms   {dif:+7.0f} ms  {ka:7} KB   {kd:7} KB{marca}", flush=True)
        nav.close()
    sa.shutdown(); sd.shutdown()
    print("células que pioram mais de %d ms: %d" % (LIMITE_MS, ruim))
    return 0


if __name__ == "__main__":
    sys.exit(main())
