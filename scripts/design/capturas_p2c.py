"""P2c: capturas dos cinco itens, do site GERADO (`docs/`), em 3 tamanhos (375, 1366x657, 1440x900) e nos dois temas.

    py -3.12 -m scripts.design.capturas_p2c PASTA_DOCS SAIDA

1a-navbar-landing    a navbar com Partidas · Jogadores · Reescrever · Prancheta (landing)
1b-tatica-links      o bloco "Monte uma tática do zero" com os 10 mapas como links
1c-navbar-prancheta  a prancheta, com o link dela marcado
2-arrastar-varias-vezes  Reescrever: três arrastos em instantes diferentes (o caminho com três paradas e as linhas de "O que mudou")
3a-ver-no-mapa-botao / 3b-ver-no-mapa-depois  Reescrever: o botão depois do Aplicar e o mapa à vista depois do toque (a prancheta: 3c / 3d)
4a-time-faceit / 4b-time-profissional  o cabeçalho de uma partida da FACEIT ("Time de t1ltedbot") e de uma profissional
5-relogio-translucido  a prancheta com uma peça sob o relógio grande
O relógio simulado do Playwright; as páginas abrem como arquivo local, como no site."""
from __future__ import annotations

import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

TAMANHOS = [("375", 375, 812), ("1366", 1366, 657), ("1440", 1440, 900)]
T_INICIAL = 1_700_000_000_000
PRONTA = "() => window.ComandosNoReescrever && document.querySelector('#rw-cmd-cartao .rw-cmd-vazio')"
PECA = """() => { const I = Prancheta._interno, S = I.S; I.emiteLote([["cria_peca", { peca: "demo-t2", lado: "t", rotulo: "2", passo: S.estado.passos[0].passo, x: -1100, y: -250, nivel: 0 }]]); I.abaDoPainel('comandos'); }"""
SOB_O_RELOGIO = """() => { const I = Prancheta._interno, S = I.S, cv = document.getElementById('pr-mapa'), r = document.getElementById('pr-relogio-grande').getBoundingClientRect(), c = cv.getBoundingClientRect();
  const p = S.ultimoDesenho.find(d => d.tipo === 'peca'), k = cv.width / c.width, a = cv.getContext('2d').getTransform().a / S.view.zoom;
  S.view.zoom = 1; S.view.panX = ((r.left + r.width / 2 - c.left) * k) / a - p.x; S.view.panY = ((r.top + r.height / 2 - c.top) * k) / a - p.y; I.atualizaTudo(); }"""


def abre(nav, w, h, tema):
    ctx = nav.new_context(viewport={"width": w, "height": h})
    ctx.add_init_script(f"try {{ localStorage.setItem('goatdemo:tema', '{tema}'); }} catch (e) {{}}")
    pg = ctx.new_page()
    pg.clock.install(time=T_INICIAL)
    return ctx, pg


def partida(pg, docs: Path, w):
    pg.goto((docs / "match_43.html").as_uri() + "#replay")
    pg.wait_for_function("() => window.MapAnnotations && MapAnnotations._interno.S.reprojecoes > 0")
    pg.wait_for_timeout(500)
    pg.locator("#strip .rchip", has_text="23").first.click()
    pg.wait_for_timeout(200)
    pg.evaluate("f => { const s = document.getElementById('scrub'); s.value = f; s.dispatchEvent(new Event('input')); }", 140)
    pg.wait_for_timeout(300)
    if w < 1024:
        pg.evaluate("document.getElementById('map').scrollIntoView({block: 'center'})")


def arrasta(pg, nome, dx, dy):
    xy = pg.evaluate("n => window.__reescrever().pecas.find(p => p.nome === n).tela", nome)
    pg.mouse.move(*xy)
    pg.mouse.down()
    pg.mouse.move(xy[0] + dx, xy[1] + dy, steps=6)
    pg.mouse.up()
    pg.wait_for_timeout(200)


def avanca(pg, quadros):
    alvo = int(pg.evaluate("window.__reescrever().quadro")) + quadros
    pg.click("#play")
    pg.wait_for_function("q => window.__reescrever().quadro >= q", arg=alvo, timeout=20000)
    pg.click("#play")
    pg.wait_for_timeout(150)


def foto(pg, saida, nome, rotulo, tema, w, alvo=None):
    pg.wait_for_timeout(250)
    if alvo and w < 1024:
        pg.locator(alvo).first.scroll_into_view_if_needed()
    elif alvo == "#rw-mudou":      # no computador a coluna do painel rola por dentro: leva "O que mudou" à vista
        pg.evaluate("a => { const c = document.getElementById('squad-t'), s = document.getElementById(a); c.scrollTop = s.offsetTop - c.offsetTop - 8; }", "rw-mudou")
    pg.screenshot(path=str(saida / f"{nome}-{rotulo}-{tema}.png"))


def so_a_captura_2(docs: Path, saida: Path) -> None:
    """Refaz só a captura 2 (arrastar várias vezes), nos 3 tamanhos e nos 2 temas."""
    saida.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        nav = p.chromium.launch(channel="chrome")
        for tema in ("escuro", "claro"):
            for rotulo, w, h in TAMANHOS:
                ctx, pg = abre(nav, w, h, tema)
                partida(pg, docs, w)
                pg.click("#rw-entrar")
                arrasta(pg, "ropz", 60, -40)
                avanca(pg, 12)
                arrasta(pg, "ropz", -50, 60)
                avanca(pg, 12)
                arrasta(pg, "ropz", 40, 40)
                foto(pg, saida, "2-arrastar-varias-vezes", rotulo, tema, w, "#rw-mudou")
                ctx.close()
        nav.close()
    print(f"captura 2 refeita em {saida}")


def roda(docs: Path, saida: Path) -> None:
    saida.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        nav = p.chromium.launch(channel="chrome")
        for tema in ("escuro", "claro"):
            for rotulo, w, h in TAMANHOS:
                ctx, pg = abre(nav, w, h, tema)                                    # 1: navbar e landing
                pg.goto((docs / "index.html").as_uri())
                pg.wait_for_timeout(600)
                foto(pg, saida, "1a-navbar-landing", rotulo, tema, w)
                pg.locator("#h-tatica").scroll_into_view_if_needed()
                pg.evaluate("window.scrollBy(0, -80)")
                pg.wait_for_timeout(200)
                foto(pg, saida, "1b-tatica-links", rotulo, tema, w)
                pg.goto((docs / "prancheta_de_mirage.html").as_uri())
                pg.wait_for_function("() => Prancheta._interno.S.estado !== null")
                pg.wait_for_timeout(500)
                foto(pg, saida, "1c-navbar-prancheta", rotulo, tema, w)
                ctx.close()

                ctx, pg = abre(nav, w, h, tema)                                    # 2: arrastar várias vezes
                partida(pg, docs, w)
                pg.click("#rw-entrar")
                arrasta(pg, "ropz", 60, -40)
                avanca(pg, 12)
                arrasta(pg, "ropz", -50, 60)
                avanca(pg, 12)
                arrasta(pg, "ropz", 40, 40)
                foto(pg, saida, "2-arrastar-varias-vezes", rotulo, tema, w, "#rw-mudou")
                ctx.close()

                ctx, pg = abre(nav, w, h, tema)                                    # 3: Ver no mapa (Reescrever)
                partida(pg, docs, w)
                pg.click("#rw-entrar")
                pg.click("#rw-cmd-abre")
                pg.wait_for_function(PRONTA)
                pg.fill("#rw-cmd-texto", "ropz corre pro meio aos 1:10")
                pg.click("#rw-cmd-entender")
                pg.wait_for_timeout(400)
                pg.click("#rw-cmd-aplicar")
                pg.wait_for_timeout(300)
                foto(pg, saida, "3a-ver-no-mapa-botao", rotulo, tema, w, "#rw-cmd-cartao")
                if pg.locator("#rw-cmd-ver-mapa").is_visible():
                    pg.click("#rw-cmd-ver-mapa")
                    pg.wait_for_timeout(300)
                foto(pg, saida, "3b-ver-no-mapa-depois", rotulo, tema, w)
                ctx.close()

                ctx, pg = abre(nav, w, h, tema)                                    # 3 (prancheta) e 5 (o relógio)
                pg.goto((docs / "prancheta_de_mirage.html").as_uri())
                pg.wait_for_function("() => Prancheta._interno.S.estado !== null")
                pg.wait_for_timeout(500)
                pg.evaluate(PECA)
                pg.fill("#pr-cmd-texto", "tr 2 corre pro meio aos 1:30")
                pg.click("#pr-cmd-entender")
                pg.wait_for_function("() => document.querySelectorAll('#pr-cmd-entendi li').length === 1")
                pg.click("#pr-cmd-aplicar")
                pg.wait_for_timeout(300)
                foto(pg, saida, "3c-prancheta-ver-no-mapa-botao", rotulo, tema, w, "#pr-cmd-resultado")
                if pg.locator("#pr-cmd-ver-mapa").is_visible():
                    pg.click("#pr-cmd-ver-mapa")
                    pg.wait_for_timeout(300)
                foto(pg, saida, "3d-prancheta-ver-no-mapa-depois", rotulo, tema, w)
                pg.evaluate(SOB_O_RELOGIO)
                pg.evaluate("document.getElementById('pr-palco').scrollIntoView({block: 'start'})")
                pg.wait_for_timeout(250)
                foto(pg, saida, "5-relogio-translucido", rotulo, tema, w)
                ctx.close()

                for nome, partida_id in (("4a-time-faceit", "match_01"), ("4b-time-profissional", "match_43")):      # 4: o nome do time
                    ctx, pg = abre(nav, w, h, tema)
                    pg.goto((docs / f"{partida_id}.html").as_uri())
                    pg.wait_for_timeout(700)
                    foto(pg, saida, nome, rotulo, tema, w)
                    ctx.close()
        nav.close()
    print(f"{len(list(saida.glob('*.png')))} capturas em {saida}")


if __name__ == "__main__":
    if len(sys.argv) == 4 and sys.argv[3] == "2":
        so_a_captura_2(Path(sys.argv[1]).resolve(), Path(sys.argv[2]))
        sys.exit(0)
    if len(sys.argv) != 3:
        print(__doc__)
        sys.exit(2)
    roda(Path(sys.argv[1]).resolve(), Path(sys.argv[2]))
