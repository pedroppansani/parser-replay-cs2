"""SONDA temporária (não versionar): reproduz a sequência do test_desfazer_e_refazer até o move_peca, medindo tudo."""
import json
from tests.test_tactics_browser import abre, arrasta_do_banco, interno, no_mapa, caixa, solta_foco, navegador, pagina, contexto  # noqa: F401

MEDE = """() => { const c = document.getElementById('pr-mapa'), b = c.getBoundingClientRect(), L = document.getElementById('pr-linha'),
  I = Prancheta._interno, S = I.S, q = I.quadroDoPasso(S.estado, 0, I.centro()), W = I.radar().width, d = Object.keys(q.pecas).map(k => { const m = I.jogoParaPixel(q.pecas[k].x, q.pecas[k].y); return [Math.round(b.x + m[0] * b.width / W), Math.round(b.y + m[1] * b.height / W)]; });
  return {t_ms: Math.round(performance.now()), mapa: [Math.round(b.x), Math.round(b.y), Math.round(b.width), Math.round(b.height)], canvasPx: [c.width, c.height],
    linha_h: L ? L.offsetHeight : null, reprojecoes: S.reprojecoes, fontes: document.fonts.status, pecas_desenhadas_na_tela: d,
    pecas_no_estado: Object.keys(S.estado.pecas).length, reproducao: !!S.reproducao, sel: S.sel, arrasto: S.arrasto && S.arrasto.tipo}; }"""


def p(rotulo, valor):
    print("SONDA " + rotulo + " " + json.dumps(valor, ensure_ascii=False))


def test_sonda(contexto, pagina):
    pg = abre(contexto, pagina)
    p("A carregamento", pg.evaluate(MEDE))
    solta_foco(pg); antes = interno(pg, "S.estado")
    arrasta_do_banco(pg, "ct", "2", 0.5, 0.5); solta_foco(pg)
    p("B apos criar a peca", pg.evaluate(MEDE))
    pg.keyboard.press("Control+z"); p("C logo apos Ctrl+Z", pg.evaluate(MEDE))
    pg.keyboard.press("Control+y"); p("D logo apos Ctrl+Y", pg.evaluate(MEDE))
    pg.keyboard.press("Control+z"); pg.keyboard.press("Control+Shift+z")
    p("E logo apos Ctrl+Z e Ctrl+Shift+Z", pg.evaluate(MEDE))
    pid = interno(pg, "Object.keys(S.estado.pecas)[0]")
    interno(pg, f"(S.sel = {{tipo: 'peca', id: '{pid}'}}, 0)")
    solta_foco(pg); antes = interno(pg, "S.estado")
    ini = no_mapa(pg, 0.5, 0.5)
    p("F antes do move_peca (inicio do arrasto)", {"inicio": [round(ini[0]), round(ini[1])], **pg.evaluate(MEDE)})
    pg.mouse.move(*ini); pg.mouse.down()
    p("G apos mouse.down", pg.evaluate(MEDE))
    pg.mouse.move(*no_mapa(pg, 0.55, 0.45), steps=5); pg.mouse.up()
    p("H fim do arrasto", pg.evaluate(MEDE))
    solta_foco(pg)
    p("I estado mudou?", interno(pg, "S.estado") != antes)
