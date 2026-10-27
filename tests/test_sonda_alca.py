"""SONDA temporária (não versionar): geometria da prancheta e quem recebe o mouse nos arrastes."""
import json
from tests.test_tactics_browser import abre, arrasta_do_banco, interno, no_radar, no_mapa, caixa, navegador, pagina, contexto  # noqa: F401

MEDE = """() => { const r = e => { if (!e) return null; const b = e.getBoundingClientRect(); return [Math.round(b.x), Math.round(b.y), Math.round(b.width), Math.round(b.height)]; };
  const c = document.getElementById('pr-mapa');
  return {viewport: [innerWidth, innerHeight], scrollY: Math.round(scrollY), mapa: r(c), canvasPx: [c.width, c.height],
    navbar: r(document.querySelector('.site-topo, .site-nav, header')), cab: r(document.querySelector('.pr-cab')),
    fontes: [document.fonts.status, [...document.fonts].filter(f => f.status === 'loaded').map(f => f.family)],
    bodyFont: getComputedStyle(document.body).fontFamily.slice(0, 40)}; }"""
QUEM = """([x, y]) => { const e = document.elementFromPoint(x, y); return e ? e.tagName + '#' + e.id + '.' + String(e.className).slice(0, 30) : null; }"""


def p(rotulo, valor):
    print("SONDA " + rotulo + " " + json.dumps(valor, ensure_ascii=False))


def test_sonda(contexto, pagina):
    pg = abre(contexto, pagina)
    p("1 apos abrir", pg.evaluate(MEDE))
    arrasta_do_banco(pg, "ct", "2", 0.5, 0.5)
    p("2 apos criar peca (move_peca)", pg.evaluate(MEDE))
    pid = interno(pg, "Object.keys(S.estado.pecas)[0]")
    interno(pg, f"(S.sel = {{tipo: 'peca', id: '{pid}'}}, I.reprojeta(), 0)")
    pc = interno(pg, f"I.quadroDoPasso(S.estado, 0, I.centro()).pecas['{pid}']")
    cx, cy = interno(pg, f"I.jogoParaPixel({pc['x']}, {pc['y']})")
    peca_tela = no_radar(pg, cx, cy); inicio_move = no_mapa(pg, 0.5, 0.5)
    ax, ay = interno(pg, f"I.alca('{pid}')"); alca_tela = no_radar(pg, ax, ay)
    p("3 peca_na_tela", [round(peca_tela[0]), round(peca_tela[1])])
    p("3 inicio_do_arrasto_move_peca (no_mapa .5 .5)", [round(inicio_move[0]), round(inicio_move[1])])
    p("3 distancia_peca_inicio_px", round(((peca_tela[0] - inicio_move[0]) ** 2 + (peca_tela[1] - inicio_move[1]) ** 2) ** 0.5, 1))
    p("3 alca_na_tela", [round(alca_tela[0]), round(alca_tela[1])])
    p("3 quem_recebe_no_inicio_do_move", pg.evaluate(QUEM, list(inicio_move)))
    p("3 quem_recebe_na_alca", pg.evaluate(QUEM, list(alca_tela)))
    pg.wait_for_timeout(1000)
    p("4 mapa 1s depois", pg.evaluate(MEDE)["mapa"])
    c2 = caixa(pg); p("4 caixa_playwright", [round(c2["x"]), round(c2["y"]), round(c2["width"]), round(c2["height"])])
    alca2 = no_radar(pg, ax, ay); p("4 alca_na_tela_1s_depois", [round(alca2[0]), round(alca2[1])])
