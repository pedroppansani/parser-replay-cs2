"""SONDA temporária (não versionar): quem recebe o mouse no arrasto da alça de giro."""
from tests.test_tactics_browser import abre, arrasta_do_banco, interno, no_radar, navegador, pagina, contexto  # noqa: F401


def test_sonda_alca(contexto, pagina):
    pg = abre(contexto, pagina)
    arrasta_do_banco(pg, "t", "1", 0.5, 0.5)
    pid = interno(pg, "S.sel.id")
    ax, ay = interno(pg, f"I.alca('{pid}')")
    p = interno(pg, f"I.quadroDoPasso(S.estado, 0, I.centro()).pecas['{pid}']")
    cx, cy = interno(pg, f"I.jogoParaPixel({p['x']}, {p['y']})")
    pontos = [("inicio (alça)", no_radar(pg, ax, ay))]
    for i in range(1, 9):
        pontos.append((f"passo {i}", no_radar(pg, ax + (cx - ax) * i / 8, ay + (cy - 60 - ay) * i / 8)))
    pontos.append(("fim", no_radar(pg, cx, cy - 60)))
    linhas = []
    for nome, (x, y) in pontos:
        r = pg.evaluate("""([x, y]) => { const e = document.elementFromPoint(x, y); if (!e) return null;
            const nav = document.querySelector('.site-topo, .site-nav'); const nb = nav ? nav.getBoundingClientRect() : null;
            return {tag: e.tagName, id: e.id, cls: String(e.className).slice(0, 40), navBottom: nb ? Math.round(nb.bottom) : null}; }""", [x, y])
        linhas.append(f"{nome}: ({x:.0f},{y:.0f}) -> {r}")
    print("\n".join(linhas))
    assert True
