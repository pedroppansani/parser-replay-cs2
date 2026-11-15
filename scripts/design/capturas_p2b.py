"""P2b: capturas de antes e depois da prancheta e do Reescrever, do site GERADO (`docs/`), para provar que tirar o leitor e a seção Comandos do HTML não muda nada do que se vê.

    py -3.12 -m scripts.design.capturas_p2b PASTA_DOCS SAIDA     # roda uma vez em cada site (antes e depois) e compara os arquivos com `compara`
    py -3.12 -m scripts.design.capturas_p2b compara SAIDA_ANTES SAIDA_DEPOIS

Prancheta da Mirage: uma ficha no mapa, a aba Comandos aberta e a frase "tr 2 corre pro meio aos 1:30" entendida. Reescrever: round 23 da match_43 no quadro 140, a seção Comandos aberta e
"ropz corre pro meio aos 1:10" entendida. 3 tamanhos x 2 temas, com o relógio simulado do Playwright; as páginas abrem como arquivo local, como no site."""
from __future__ import annotations

import hashlib
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

TAMANHOS = [("375", 375, 812), ("1366", 1366, 657), ("1440", 1440, 900)]
T_INICIAL = 1_700_000_000_000


def prancheta(nav, docs: Path, saida: Path, rotulo, w, h, tema):
    ctx = nav.new_context(viewport={"width": w, "height": h})
    ctx.add_init_script(f"try {{ localStorage.setItem('goatdemo:tema', '{tema}'); }} catch (e) {{}}")
    pg = ctx.new_page(); pg.clock.install(time=T_INICIAL)
    pg.goto((docs / "prancheta_de_mirage.html").as_uri())
    pg.wait_for_function("() => Prancheta._interno.S.estado !== null")
    pg.wait_for_timeout(500)
    pg.evaluate("""() => { const I = Prancheta._interno, S = I.S; I.emiteLote([["cria_peca", { peca: "demo-t2", lado: "t", rotulo: "2", passo: S.estado.passos[0].passo, x: -1100, y: -250, nivel: 0 }]]); }""")
    pg.evaluate("() => Prancheta._interno.abaDoPainel('comandos')")
    pg.fill("#pr-cmd-texto", "tr 2 corre pro meio aos 1:30")
    pg.click("#pr-cmd-entender")
    pg.wait_for_function("() => document.querySelectorAll('#pr-cmd-entendi li').length === 1 && !document.getElementById('pr-cmd-carregando-plano')")
    pg.wait_for_timeout(400)
    pg.locator("#pr-cmd-resultado").scroll_into_view_if_needed()
    pg.screenshot(path=str(saida / f"prancheta-{rotulo}-{tema}.png"))
    ctx.close()


def reescrever(nav, docs: Path, saida: Path, rotulo, w, h, tema):
    ctx = nav.new_context(viewport={"width": w, "height": h})
    ctx.add_init_script(f"try {{ localStorage.setItem('goatdemo:tema', '{tema}'); }} catch (e) {{}}")
    pg = ctx.new_page(); pg.clock.install(time=T_INICIAL)
    pg.goto((docs / "match_43.html").as_uri() + "#replay")
    pg.wait_for_function("() => window.MapAnnotations && MapAnnotations._interno.S.reprojecoes > 0")
    pg.wait_for_timeout(500)
    pg.locator("#strip .rchip", has_text="23").first.click(); pg.wait_for_timeout(200)
    pg.evaluate("f => { const s = document.getElementById('scrub'); s.value = f; s.dispatchEvent(new Event('input')); }", 140)
    pg.wait_for_timeout(300)
    if w < 1024:
        pg.evaluate("document.getElementById('map').scrollIntoView({block: 'center'})")
    pg.click("#rw-entrar")
    pg.click("#rw-cmd-abre")
    pg.wait_for_function("() => window.ComandosNoReescrever && document.querySelector('#rw-cmd-cartao .rw-cmd-vazio')")
    pg.fill("#rw-cmd-texto", "ropz corre pro meio aos 1:10")
    pg.click("#rw-cmd-entender")
    pg.wait_for_function("() => document.querySelectorAll('#rw-cmd-entendi li').length === 1")
    pg.wait_for_timeout(500)
    if w < 1024:
        pg.locator("#rw-comandos").scroll_into_view_if_needed()
    pg.screenshot(path=str(saida / f"reescrever-{rotulo}-{tema}.png"))
    ctx.close()


def compara(a: Path, b: Path) -> int:
    fa, fb = sorted(p.name for p in a.glob("*.png")), sorted(p.name for p in b.glob("*.png"))
    h = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    iguais = [n for n in fa if n in fb and h(a / n) == h(b / n)]
    dif = [n for n in fa if n not in iguais]
    print(f"{len(fa)} capturas antes, {len(fb)} depois; idênticas byte a byte: {len(iguais)}; diferentes ou faltando: {len(dif)}")
    for n in dif:
        print("  ", n)
    return 0 if not dif and fa == fb else 1


def main() -> int:
    if len(sys.argv) == 4 and sys.argv[1] == "compara":
        return compara(Path(sys.argv[2]), Path(sys.argv[3]))
    docs, saida = Path(sys.argv[1]).resolve(), Path(sys.argv[2])
    saida.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        nav = p.chromium.launch(channel="chrome")
        for tema in ("escuro", "claro"):
            for rotulo, w, h in TAMANHOS:
                prancheta(nav, docs, saida, rotulo, w, h, tema)
                reescrever(nav, docs, saida, rotulo, w, h, tema)
        nav.close()
    print(f"{len(list(saida.glob('*.png')))} capturas em {saida}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
