"""CR3: as capturas da granada por comando no Reescrever, no round 23 da match_43 com "Reescrever daqui" em 1:20 (o quadro 140), nos 3 tamanhos (375, 1366x657, 1440x900) e nos dois temas.

    py -3.12 -m scripts.design.capturas_reescrever_cr3 <pasta_de_saida>

Os estados, todos com a seção Comandos ABERTA e a biblioteca de arremessos ao lado da página, como no site:
   1-troca-aplicada   "FalleN joga smoke no janelão aos 0:57" com [Levar o FalleN até lá] aplicado: a linha da troca em "O que mudou" e a granada real tracejada no mapa
   2-qual-granada     "mezii joga flash no meio aos 1:10": o mezii jogou duas flash depois de 1:20; um botão por granada, com o horário e o lugar reais
   3-nao-jogou        "YEKINDAR joga smoke no janelão aos 1:10": ele não jogou smoke neste round
   4-antes-do-instante "ropz joga smoke no meio aos 1:05": a smoke dele saiu às 1:55, antes de 1:20 (já faz parte do real)
   5-saida-longe      "FalleN joga smoke no janelão aos 0:57": o lugar de saída é longe, com [Levar o FalleN até lá] e [Usar outro arremesso]
   6-chegada-tardia   "FalleN joga smoke no janelão aos 1:19" + [Levar]: ele só chega às 1:12, "Jogar às 1:12?"
   7-frase-mista      "apEX corre pro meio aos 1:10 e depois joga flash no meio" aplicada (a corrida e a troca; um item do Desfazer)
   8-so-a-corrida    "ropz joga flash no meio aos 1:10 e corre pro B": o ropz não jogou flash; o cartão recusa a granada e oferece [Aplicar só a corrida]
O tempo é o relógio simulado do Playwright (`page.clock`). Também mede, por tamanho, o retângulo do mapa em cada estado e o CLS.
"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ))

PARTIDA, ROUND, QUADRO, MAPA = "match_43", 23, 140, "de_mirage"
TELAS = [("375", 375, 812), ("1366", 1366, 657), ("1440", 1440, 900)]
T_INICIAL = 1_700_000_000_000
RECT = "() => { const r = document.getElementById('map').getBoundingClientRect(); return [r.x, r.y + scrollY, r.width, r.height].map(v => Math.round(v * 10) / 10); }"
CLS = "window.__cls_total = 0; new PerformanceObserver(l => { for (const e of l.getEntries()) window.__cls_total += e.value; }).observe({type: 'layout-shift'});"
PRONTA = "() => window.__reescrever().trocas.biblioteca === 'pronta'"


def _pagina(pasta: Path) -> Path:
    from scripts.build_reescrever_comandos import escreve
    from scripts.build_site import match_summary, times_das_partidas
    from scripts.build_tactics_page import arquivo_da_biblioteca, biblioteca_js
    from scripts.build_web_page import build_html
    arq = pasta / f"{PARTIDA}.html"
    arq.write_text(build_html(PARTIDA), encoding="utf-8")
    escreve(pasta, [MAPA])
    ids = {a["partida"] for a in json.loads((RAIZ / "data" / "lineups" / f"{MAPA}.json").read_text(encoding="utf-8"))["arremessos"]}
    bib = biblioteca_js(MAPA, times_das_partidas([s for s in (match_summary(i) for i in sorted(ids)) if s]))
    destino = pasta / arquivo_da_biblioteca(MAPA)
    destino.parent.mkdir(exist_ok=True)
    destino.write_text(bib, encoding="utf-8")
    return arq


def _abre(nav, pagina: Path, w: int, h: int, tema: str):
    ctx = nav.new_context(viewport={"width": w, "height": h})
    ctx.add_init_script(f"try {{ localStorage.setItem('goatdemo:tema', '{tema}'); }} catch (e) {{}}")
    pg = ctx.new_page()
    pg.clock.install(time=T_INICIAL)
    erros: list[str] = []
    pg.on("pageerror", lambda e: erros.append(str(e)))
    pg.goto(pagina.as_uri() + "#replay")
    pg.wait_for_function("() => window.MapAnnotations && MapAnnotations._interno.S.reprojecoes > 0")
    pg.wait_for_timeout(500)
    pg.locator("#strip .rchip", has_text=str(ROUND)).first.click()
    pg.wait_for_timeout(200)
    pg.evaluate("f => { const s = document.getElementById('scrub'); s.value = f; s.dispatchEvent(new Event('input')); }", QUADRO)
    pg.wait_for_timeout(300)
    if w < 1024:
        pg.evaluate("document.getElementById('map').scrollIntoView({block: 'center'})")
    pg.click("#rw-entrar")
    pg.click("#rw-cmd-abre")
    pg.wait_for_function("() => window.ComandosNoReescrever && document.querySelector('#rw-cmd-cartao .rw-cmd-vazio')")
    pg.evaluate(CLS)
    return ctx, pg, erros


def roda(saida: Path) -> None:
    from playwright.sync_api import sync_playwright
    saida.mkdir(parents=True, exist_ok=True)
    pagina = _pagina(Path(tempfile.mkdtemp(prefix="rw_cr3_")))
    medidas: dict = {}
    with sync_playwright() as p:
        nav = p.chromium.launch(channel="chrome")
        for tema in ("escuro", "claro"):
            for rotulo, w, h in TELAS:
                ctx, pg, erros = _abre(nav, pagina, w, h, tema)
                chave = f"{rotulo}-{tema}"
                rects: dict = {}

                def vai(frase: str, *cliques: str) -> None:
                    pg.fill("#rw-cmd-texto", frase)
                    pg.click("#rw-cmd-entender")
                    pg.wait_for_function(PRONTA)
                    pg.wait_for_timeout(350)
                    for c in cliques:
                        pg.locator("#rw-cmd-cartao button", has_text=c).first.click()
                        pg.wait_for_timeout(200)

                def foto(passo: str, alvo: str = "rw-comandos") -> None:
                    pg.wait_for_timeout(250)
                    if w < 1024:
                        pg.locator("#" + alvo).scroll_into_view_if_needed()
                    elif alvo != "rw-comandos":      # só o "O que mudou" (estados 1 e 7) é levado à vista à mão; os estados do cartão aparecem como a pessoa os veria: a coluna rola sozinha
                        pg.evaluate("a => { const c = document.getElementById('squad-t'); const s = document.getElementById(a); c.scrollTop = s.offsetTop - c.offsetTop - 8; }", alvo)
                    pg.wait_for_timeout(100)
                    if w < 1024:      # no celular: da moldura do mapa (com o alternador) até o fim da seção (ou de "O que mudou"), para ler
                        caixa = pg.evaluate("a => { const p = document.getElementById('palco').getBoundingClientRect(), s = document.getElementById(a).getBoundingClientRect(); return [p.top + scrollY, s.bottom + scrollY]; }", alvo if alvo != "rw-comandos" else "rw-cmd-corpo")
                        pg.screenshot(path=str(saida / f"{passo}-{rotulo}-{tema}.png"), full_page=True, clip={"x": 0, "y": max(0, caixa[0] - 8), "width": w, "height": caixa[1] - caixa[0] + 56})
                    else:
                        pg.screenshot(path=str(saida / f"{passo}-{rotulo}-{tema}.png"))
                    rects[passo] = pg.evaluate(RECT)

                vai("YEKINDAR joga smoke no janelão aos 1:10"); foto("3-nao-jogou")
                vai("ropz joga smoke no meio aos 1:05"); foto("4-antes-do-instante")
                vai("mezii joga flash no meio aos 1:10"); foto("2-qual-granada")
                vai("FalleN joga smoke no janelão aos 1:19", "Levar o"); foto("6-chegada-tardia")
                vai("FalleN joga smoke no janelão aos 0:57"); foto("5-saida-longe")
                pg.click("#rw-cmd-cartao button:has-text('Levar o')"); pg.click("#rw-cmd-aplicar"); pg.wait_for_timeout(200)
                foto("1-troca-aplicada", "rw-mudou")
                pg.click("#rw-desfazer"); pg.wait_for_timeout(200)
                vai("apEX corre pro meio aos 1:10 e depois joga flash no meio", "Levar o", "Jogar às")
                pg.click("#rw-cmd-aplicar"); pg.wait_for_timeout(200)
                foto("7-frase-mista", "rw-mudou")
                pg.click("#rw-desfazer"); pg.wait_for_timeout(200)
                vai("ropz joga flash no meio aos 1:10 e corre pro B"); foto("8-so-a-corrida")
                medidas[chave] = {"mapa": rects, "cls_ate_aplicar": pg.evaluate("window.__cls_total")}
                assert erros == [], erros
                ctx.close()
        nav.close()
    (saida / "medidas.json").write_text(json.dumps(medidas, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{len(list(saida.glob('*.png')))} capturas em {saida}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(2)
    roda(Path(sys.argv[1]))
