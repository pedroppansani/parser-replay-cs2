"""CR1b: o Reescrever de antes e de depois da trilha com horário, nos mesmos passos, no round 23 da match_43 (o do protótipo).

    py -3.12 -m scripts.design.capturas_reescrever_cr1b <pasta_de_saida>

Roda no código da pasta onde está (rode uma vez no `main` e uma vez na branch, em duas pastas, e compare com `compara`). Os passos, em cada tamanho (375, 1366x657, 1440x900):
  1-entrou      "Reescrever este round" no instante (35 % do round)
  2-arrastou    KSCERATO arrastado 70 px para a direita e 50 para cima (o arrastar de hoje)
  3-tocou       ▶ por 2 s, pausa: a sua versão no meio do caminho, com o fantasma do real ligado
  4-sem-fantasma  o interruptor "Fantasma do real" desligado (no celular, o alternador na vista Real)
  5-o-que-mudou   a lista "O que mudou" à vista (com o fantasma ligado de novo)
Tema escuro nos 5 passos e tema claro no 3. O tempo é o relógio simulado do Playwright (`page.clock`): o mesmo quadro nas duas rodadas, sem depender do tempo real.
Também grava `estado.json` (o `window.__reescrever()` de cada passo, sem os campos que só o código novo tem).

    py -3.12 -m scripts.design.capturas_reescrever_cr1b compara PASTA_ANTES PASTA_DEPOIS   # diz quais PNGs e quais estados são idênticos
"""
from __future__ import annotations

import hashlib
import json
import sys
import tempfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ))

PARTIDA, ROUND = "match_43", 23
TELAS = [("375", 375, 812), ("1366", 1366, 657), ("1440", 1440, 900)]
T_INICIAL = 1_700_000_000_000      # o relógio simulado começa aqui, e a página para num instante fixo: o tempo da reprodução é o mesmo em toda rodada
NOVOS = {"trilha", "partida", "trechos"}        # campos do estado que só o código novo tem


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
    pg.evaluate("f => { const s = document.getElementById('scrub'); s.value = Math.floor(s.max * f); s.dispatchEvent(new Event('input')); }", 0.35)
    pg.wait_for_timeout(300)
    if w < 1024:
        pg.evaluate("document.getElementById('map').scrollIntoView({block: 'center'})")
    return ctx, pg, erros


def _estado(pg) -> dict:
    est = pg.evaluate("window.__reescrever()")
    for p in est["pecas"]:
        for k in NOVOS:
            p.pop(k, None)
    return est


def roda(saida: Path) -> None:
    from playwright.sync_api import sync_playwright
    from scripts.build_web_page import build_html
    saida.mkdir(parents=True, exist_ok=True)
    pagina = Path(tempfile.mkdtemp(prefix="rw_cr1b_")) / f"{PARTIDA}.html"
    pagina.write_text(build_html(PARTIDA), encoding="utf-8")
    estados: dict = {}
    with sync_playwright() as p:
        nav = p.chromium.launch(channel="chrome")
        for tema in ("escuro", "claro"):
            for rotulo, w, h in TELAS:
                ctx, pg, erros = _abre(nav, pagina, w, h, tema)
                chave = f"{rotulo}-{tema}"

                def foto(passo: str) -> None:
                    pg.wait_for_timeout(200)
                    pg.screenshot(path=str(saida / f"{passo}-{rotulo}-{tema}.png"))
                    estados[f"{passo}-{chave}"] = _estado(pg)

                pg.click("#rw-entrar")
                if tema == "escuro":
                    foto("1-entrou")
                tela = next(q for q in pg.evaluate("window.__reescrever()")["pecas"] if q["nome"] == "KSCERATO")["tela"]
                pg.mouse.move(*tela); pg.mouse.down(); pg.mouse.move(tela[0] + 70, tela[1] - 50, steps=5); pg.mouse.up()
                if tema == "escuro":
                    foto("2-arrastou")
                pg.clock.pause_at(T_INICIAL + 120_000)      # o relógio da página para: daqui em diante o tempo só passa por `run_for`
                pg.click("#play"); pg.clock.run_for(2000); pg.click("#play")
                foto("3-tocou")
                if tema == "escuro":
                    desktop = pg.locator("#rw-fantasma").is_visible()      # no celular não há o interruptor: o real tem a sua vez no alternador Real | Sua versão
                    pg.click("#rw-fantasma" if desktop else "#rw-ver [data-ver=real]")
                    foto("4-sem-fantasma")
                    pg.click("#rw-fantasma" if desktop else "#rw-ver [data-ver=sua]")
                    pg.locator("#rw-mudou").scroll_into_view_if_needed()
                    foto("5-o-que-mudou")
                assert erros == [], erros
                ctx.close()
        nav.close()
    (saida / "estado.json").write_text(json.dumps(estados, ensure_ascii=False, indent=1, sort_keys=True), encoding="utf-8")
    print(f"{len(list(saida.glob('*.png')))} capturas em {saida}")


def compara(a: Path, b: Path) -> int:
    ha = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in a.glob("*.png")}
    hb = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in b.glob("*.png")}
    dif = sorted(k for k in set(ha) & set(hb) if ha[k] != hb[k])
    print(f"PNGs: {len(ha)} antes, {len(hb)} depois; iguais byte a byte {len(set(ha) & set(hb)) - len(dif)}; diferentes {len(dif)}; só num lado {len(set(ha) ^ set(hb))}")
    for k in dif:
        print("   diferente:", k)
    ea = json.loads((a / "estado.json").read_text(encoding="utf-8")); eb = json.loads((b / "estado.json").read_text(encoding="utf-8"))
    edif = sorted(k for k in set(ea) | set(eb) if ea.get(k) != eb.get(k))
    print(f"estados (window.__reescrever, sem os campos novos): {len(ea)} antes, {len(eb)} depois; diferentes {len(edif)}")
    for k in edif[:6]:
        print("   estado diferente:", k)
    return 0 if not dif and not edif and set(ha) == set(hb) else 1


if __name__ == "__main__":
    if len(sys.argv) == 4 and sys.argv[1] == "compara":
        sys.exit(compara(Path(sys.argv[2]), Path(sys.argv[3])))
    if len(sys.argv) == 2:
        roda(Path(sys.argv[1]))
        sys.exit(0)
    print(__doc__)
    sys.exit(2)
