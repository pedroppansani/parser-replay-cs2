"""CR2: as capturas da seção "Comandos" do Reescrever, no round 23 da match_43 com "Reescrever daqui" em 1:20 (o quadro 140), nos 3 tamanhos (375, 1366x657, 1440x900) e nos dois temas.

    py -3.12 -m scripts.design.capturas_reescrever_cr2 <pasta_de_saida>

Os estados, todos com a seção ABERTA:
   1-vazia          a seção sem frase
   2-entendido      "ropz corre pro meio aos 1:10", antes de aplicar
   3-pergunta       "o 4 joga smoke no janelão aos 1:05" (o 4 sem lado: os botões de nick e vida)
   4-recusado       "ZywOo roda pra B aos 0:50" (começa depois da morte real)
   5-termina        "tr 5 segura o meio até 0:50" aplicado, a sua versão tocada até a peça esmaecer na hora da morte real
   6-antes          "YEKINDAR corre pro meio aos 1:30" (antes do instante, com [Começar em 1:20])
   7-bomba-ou-round "KSCERATO corre pro meio aos 0:30"
   8-aplicado       "ropz corre pro meio aos 1:10" aplicado, com a linha em "O que mudou" e o fantasma do real
   9-desfeito       depois do Desfazer
  10-granada        "FalleN joga smoke no janelão aos 0:57" (não aplicado; o aviso da CR3)
  11-alternador     (só no celular) o alternador Real | Sua versão com a seção aberta, na vista Real
O tempo é o relógio simulado do Playwright (`page.clock`): o mesmo quadro em toda rodada. Também mede, por tamanho, o retângulo do mapa em cada estado e o CLS.
"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ))

PARTIDA, ROUND, QUADRO = "match_43", 23, 140
TELAS = [("375", 375, 812), ("1366", 1366, 657), ("1440", 1440, 900)]
T_INICIAL = 1_700_000_000_000
RECT = "() => { const r = document.getElementById('map').getBoundingClientRect(); return [r.x, r.y + scrollY, r.width, r.height].map(v => Math.round(v * 10) / 10); }"
CLS = "window.__cls_total = 0; new PerformanceObserver(l => { for (const e of l.getEntries()) window.__cls_total += e.value; }).observe({type: 'layout-shift'});"


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
    return ctx, pg, erros


def roda(saida: Path) -> None:
    from playwright.sync_api import sync_playwright
    from scripts.build_reescrever_comandos import escreve
    from scripts.build_web_page import build_html
    saida.mkdir(parents=True, exist_ok=True)
    pasta = Path(tempfile.mkdtemp(prefix="rw_cr2_"))
    pagina = pasta / f"{PARTIDA}.html"
    pagina.write_text(build_html(PARTIDA), encoding="utf-8")
    escreve(pasta, ["de_mirage"])
    medidas: dict = {}
    with sync_playwright() as p:
        nav = p.chromium.launch(channel="chrome")
        for tema in ("escuro", "claro"):
            for rotulo, w, h in TELAS:
                ctx, pg, erros = _abre(nav, pagina, w, h, tema)
                chave = f"{rotulo}-{tema}"
                rects: dict = {}
                pg.click("#rw-entrar")
                pg.click("#rw-cmd-abre")
                pg.wait_for_function("() => window.ComandosNoReescrever && document.querySelector('#rw-cmd-cartao .rw-cmd-vazio')")
                pg.evaluate(CLS)

                def vai(frase: str) -> None:
                    pg.fill("#rw-cmd-texto", frase)
                    pg.click("#rw-cmd-entender")

                def foto(passo: str, alvo: str = "rw-comandos") -> None:
                    pg.wait_for_timeout(250)
                    pg.locator("#" + alvo).scroll_into_view_if_needed()
                    if w >= 1024:      # no computador a coluna rola por dentro: o alvo no alto dela
                        pg.evaluate("a => { const c = document.getElementById('squad-t'); const s = document.getElementById(a); c.scrollTop = s.offsetTop - c.offsetTop - 8; }", alvo)
                    pg.wait_for_timeout(100)
                    if w < 1024:      # no celular: da moldura do mapa (com o alternador) até o fim da seção, para ler
                        caixa = pg.evaluate("a => { const p = document.getElementById('palco').getBoundingClientRect(), s = document.getElementById(a).getBoundingClientRect(); return [p.top + scrollY, s.bottom + scrollY]; }", alvo if alvo != "rw-comandos" else "rw-cmd-corpo")
                        pg.screenshot(path=str(saida / f"{passo}-{rotulo}-{tema}.png"), full_page=True, clip={"x": 0, "y": max(0, caixa[0] - 8), "width": w, "height": caixa[1] - caixa[0] + 56})
                    else:
                        pg.screenshot(path=str(saida / f"{passo}-{rotulo}-{tema}.png"))
                    rects[passo] = pg.evaluate(RECT)

                foto("1-vazia")
                vai("ropz corre pro meio aos 1:10"); foto("2-entendido")
                vai("o 4 joga smoke no janelão aos 1:05"); foto("3-pergunta")
                vai("ZywOo roda pra B aos 0:50"); foto("4-recusado")
                vai("YEKINDAR corre pro meio aos 1:30"); foto("6-antes")
                vai("KSCERATO corre pro meio aos 0:30"); foto("7-bomba-ou-round")
                vai("FalleN joga smoke no janelão aos 0:57"); foto("10-granada")
                # 8 e 9: aplicar ropz, tocar 2 s (o fantasma do real onde difere) e desfazer
                vai("ropz corre pro meio aos 1:10"); pg.click("#rw-cmd-aplicar")
                pg.clock.pause_at(T_INICIAL + 120_000)
                pg.click("#play"); pg.clock.run_for(2000); pg.click("#play")
                foto("8-aplicado", "rw-mudou")
                if w < 1024:
                    pg.click("#rw-ver [data-ver=real]"); foto("11-alternador"); pg.click("#rw-ver [data-ver=sua]")
                pg.click("#rw-editar")
                pg.click("#rw-desfazer"); foto("9-desfeito")
                medidas[chave] = {"mapa": rects, "cls_ate_aplicar": pg.evaluate("window.__cls_total")}
                assert erros == [], erros
                ctx.close()
                # 5: termina depois da morte (uma página só para ele)
                ctx, pg, erros = _abre(nav, pagina, w, h, tema)
                pg.click("#rw-entrar"); pg.click("#rw-cmd-abre")
                pg.wait_for_function("() => window.ComandosNoReescrever && document.querySelector('#rw-cmd-cartao .rw-cmd-vazio')")
                pg.fill("#rw-cmd-texto", "tr 5 segura o meio até 0:50"); pg.click("#rw-cmd-entender"); pg.click("#rw-cmd-aplicar")
                pg.clock.pause_at(T_INICIAL + 120_000)
                pg.click("#play"); pg.clock.run_for(29_000); pg.click("#play")      # 29 s depois de 1:20: passa de 0:52, a morte real do ZywOo
                medidas[chave]["esmaecidas"] = pg.evaluate("window.__reescrever().esmaecidas")
                pg.locator("#rw-mudou").scroll_into_view_if_needed()
                pg.wait_for_timeout(250)
                pg.screenshot(path=str(saida / f"5-termina-{rotulo}-{tema}.png"), full_page=w < 1024, clip=None)
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
