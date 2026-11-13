"""CR1b: o tempo de um quadro do Reescrever tocando a sua versão, de antes e de depois da trilha com horário.

    py -3.12 -m scripts.design.mede_quadro_reescrever PASTA_ANTES PASTA_DEPOIS [rodadas]

Cada pasta é uma cópia do projeto (o `main` e a branch). Na página da match_43, round 23, em 1440x900: entra no Reescrever, arrasta 5 peças (KSCERATO, FalleN, mezii,
ropz, ZywOo), toca a sua versão e mede, durante 4 s, quanto leva cada chamada do laço de animação (`requestAnimationFrame`: é o desenho do quadro inteiro, com as 5 peças,
o fantasma e "O que mudou"). Normal e com o processador 4 vezes mais lento (um celular fraco). As rodadas alternam antes e depois para o ruído do computador cair igual nos dois.
"""
from __future__ import annotations

import importlib.util
import json
import statistics
import subprocess
import sys
import tempfile
from pathlib import Path

PECAS = [("KSCERATO", 80, -40), ("FalleN", 60, 50), ("mezii", -70, 40), ("ropz", 70, 50), ("ZywOo", -60, -60)]
INICIO = """() => { const o = window.requestAnimationFrame.bind(window); window.__dur = []; window.__medindo = false;
  window.requestAnimationFrame = cb => o(t => { const a = performance.now(); cb(t); if (window.__medindo) window.__dur.push(performance.now() - a); }); }"""


def pagina_de(raiz: Path) -> Path:
    """Gera a página da partida com o código DA PASTA (num subprocesso, para não misturar os dois projetos no mesmo Python)."""
    saida = Path(tempfile.mkdtemp(prefix="rw_quadro_")) / "match_43.html"
    codigo = "import sys; sys.path.insert(0, sys.argv[1]); from scripts.build_web_page import build_html; open(sys.argv[2], 'w', encoding='utf-8').write(build_html('match_43'))"
    subprocess.run([sys.executable, "-c", codigo, str(raiz), str(saida)], cwd=str(raiz), check=True)
    return saida


def mede(nav, pagina: Path, lento: bool) -> list[float]:
    ctx = nav.new_context(viewport={"width": 1440, "height": 900})
    ctx.add_init_script(f"({INICIO})()")
    pg = ctx.new_page()
    if lento:
        ctx.new_cdp_session(pg).send("Emulation.setCPUThrottlingRate", {"rate": 4})
    pg.goto(pagina.as_uri() + "#replay")
    pg.wait_for_function("() => window.MapAnnotations && MapAnnotations._interno.S.reprojecoes > 0")
    pg.wait_for_timeout(500)
    pg.locator("#strip .rchip", has_text="23").first.click()
    pg.wait_for_timeout(200)
    pg.evaluate("f => { const s = document.getElementById('scrub'); s.value = Math.floor(s.max * f); s.dispatchEvent(new Event('input')); }", 0.35)
    pg.wait_for_timeout(300)
    pg.click("#rw-entrar")
    for nome, dx, dy in PECAS:
        tela = next(q for q in pg.evaluate("window.__reescrever()")["pecas"] if q["nome"] == nome)["tela"]
        pg.mouse.move(*tela); pg.mouse.down(); pg.mouse.move(tela[0] + dx, tela[1] + dy, steps=4); pg.mouse.up()
    pg.click("#play")
    pg.wait_for_timeout(300)
    pg.evaluate("() => { window.__dur = []; window.__medindo = true; }")
    pg.wait_for_timeout(4000)
    dur = pg.evaluate("() => { window.__medindo = false; return window.__dur; }")
    ctx.close()
    return dur


def resumo(v: list[float]) -> str:
    v = sorted(v)
    return f"mediana {statistics.median(v):5.2f} ms, média {statistics.fmean(v):5.2f}, p95 {v[int(0.95 * (len(v) - 1))]:5.2f}, p99 {v[int(0.99 * (len(v) - 1))]:5.2f}, máx {v[-1]:5.2f} ({len(v)} quadros)"


def main() -> int:
    from playwright.sync_api import sync_playwright
    antes, depois = Path(sys.argv[1]), Path(sys.argv[2])
    n = int(sys.argv[3]) if len(sys.argv) > 3 else 5
    paginas = {"antes": pagina_de(antes), "depois": pagina_de(depois)}
    with sync_playwright() as p:
        nav = p.chromium.launch(channel="chrome")
        for lento in (False, True):
            todos: dict[str, list[float]] = {"antes": [], "depois": []}
            medianas: dict[str, list[float]] = {"antes": [], "depois": []}
            for i in range(n):
                for quem in (("antes", "depois") if i % 2 == 0 else ("depois", "antes")):
                    d = mede(nav, paginas[quem], lento)
                    todos[quem] += d
                    medianas[quem].append(statistics.median(d))
            print(f"CPU {'4x mais lenta' if lento else 'normal'} ({n} rodadas de 4 s, alternando):")
            for quem in ("antes", "depois"):
                print(f"  {quem:6} {resumo(todos[quem])}; mediana por rodada: {[round(m, 2) for m in medianas[quem]]}")
        nav.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
