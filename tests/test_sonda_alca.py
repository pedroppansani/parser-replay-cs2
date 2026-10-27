"""SONDA temporária (não versionar): o mapa muda de tamanho? quando e por quê."""
import json
from tests.test_tactics_browser import abre, arrasta_do_banco, interno, no_radar, no_mapa, caixa, navegador, pagina, contexto  # noqa: F401

MEDE = """() => { const c = document.getElementById('pr-mapa'), b = c.getBoundingClientRect(), L = document.getElementById('pr-linha'),
  T = document.getElementById('pr-tela'), tb = T.getBoundingClientRect();
  return {t_ms: Math.round(performance.now()), mapa: [Math.round(b.x), Math.round(b.y), Math.round(b.width), Math.round(b.height)],
    tela_topo: Math.round(tb.top + scrollY), linha: L ? [L.hidden, L.offsetHeight] : null,
    reprojecoes: Prancheta._interno.S.reprojecoes, fontes_status: document.fonts.status, scrollY: Math.round(scrollY),
    navbar_cab: [Math.round(document.querySelector('.pr-cab').getBoundingClientRect().bottom)]}; }"""
DOIS_QUADROS = "() => new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)))"


def p(rotulo, valor):
    print("SONDA " + rotulo + " " + json.dumps(valor, ensure_ascii=False))


def test_sonda(contexto, pagina):
    pg = abre(contexto, pagina)
    p("M1 carregamento", pg.evaluate(MEDE))
    # início do arrasto do banco (a ficha pega o mouse)
    f = pg.locator('.pr-ficha.t[data-rotulo="1"]').bounding_box()
    pg.mouse.move(f["x"] + f["width"] / 2, f["y"] + f["height"] / 2); pg.mouse.down()
    p("M2 inicio do arrasto do banco", pg.evaluate(MEDE))
    pg.mouse.move(*no_mapa(pg, 0.5, 0.5), steps=6)
    pg.mouse.up()
    p("M3 logo apos soltar (sincrono)", pg.evaluate(MEDE))
    c_sync = caixa(pg); p("M3 caixa_playwright_logo_apos", [round(c_sync["x"]), round(c_sync["y"]), round(c_sync["width"]), round(c_sync["height"])])
    pg.evaluate(DOIS_QUADROS)
    p("M4 dois quadros depois", pg.evaluate(MEDE))
    pg.wait_for_timeout(1000)
    p("M5 1 s depois (fim)", pg.evaluate(MEDE))
