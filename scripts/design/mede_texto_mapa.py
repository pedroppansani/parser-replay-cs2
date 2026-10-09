"""A11 (entrega-sala-de-demo §15): contraste do texto desenhado no mapa, medido no CANVAS real
do replay e da prancheta (docs/), sobre os radares dessaturados de cada mapa.

    py -3.12 -m scripts.design.mede_texto_mapa [rótulo-da-rodada]

O texto do canvas não está no DOM, então a medição depende de um gancho que o `map_core.js`
expõe (implementado na design-B2): `window.__medicaoRotulos`, um objeto com

    modo        "normal" | "sem_preenchimento" | "sem_texto"  (o modo atual)
    define(m)   troca o modo e redesenha: "sem_preenchimento" pinta só o contorno do rótulo
                (a placa e o contorno ficam; o preenchimento da letra fica transparente) e
                "sem_texto" não desenha rótulo nenhum (sobra só o fundo)
    caixas()    os rótulos desenhados no quadro atual: [{x, y, w, h, txt, cor, peso, alt}],
                em pixels de tela relativos ao canto do canvas; `alt` é a altura da letra em
                px de tela; `cor` é "#rrggbb"; os escondidos por colisão NÃO entram

Método (o do design, §15): três capturas do canvas -- A normal, B sem preenchimento, C sem
texto --; o glifo é onde A e B diferem; o fundo local "considerando o contorno" são os pixels a
até 2 px do glifo, fora dele, lidos em B; mede-se o MAIS CLARO deles contra a cor declarada do
texto. Critério: 4,5:1 (3:1 se a letra tem >= 18,66 px de altura ou é negrito >= 14 px).
Também imprime o pior caso sem contorno (informativo) e a altura mínima do rótulo.

Roda no replay de todos os mapas com partida no corpus e na prancheta da Mirage com a tática da
fixture (a tática exportada é presa à calibração de um mapa; a fixture do projeto é da Mirage). Sem o gancho na página, avisa e devolve 2.
"""
from __future__ import annotations

import io
import json
import sys

sys.dont_write_bytecode = True
import numpy as np
from PIL import Image
from playwright.sync_api import sync_playwright

from scripts.design._comum import DOCS, MAPAS, RAIZ, chrome, url_de

TELAS = ((1440, 900), (375, 667))
FRACAO_DO_ROUND = 0.45          # onde parar no round (como o compara_capturas)


def lum(rgb: np.ndarray) -> np.ndarray:
    c = rgb / 255.0
    lin = np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
    return lin @ np.array([0.2126, 0.7152, 0.0722])


def dilata(m: np.ndarray, r: int) -> np.ndarray:
    """Dilatação SEM dar a volta na borda. Com `np.roll`, a borda de baixo do glifo (a perna do "g")
    reaparecia na primeira linha do recorte, fora da placa, e o "fundo local" virava o radar acima dela."""
    h, w = m.shape
    pad = np.pad(m, r)
    out = np.zeros_like(m)
    for dy in range(-r, r + 1):
        for dx in range(-r, r + 1):
            out |= pad[r + dy:r + dy + h, r + dx:r + dx + w]
    return out


def captura(pg, seletor: str) -> np.ndarray:
    return np.asarray(Image.open(io.BytesIO(pg.locator(seletor).screenshot())).convert("RGB")).astype(float)


def mede(pg, seletor: str, modo_inicial: str = "normal") -> list[tuple[float, float, float, str, float]]:
    """[(razão com contorno, razão sem contorno, altura, texto, limite)] de cada rótulo desenhado."""
    pg.evaluate("m => window.__medicaoRotulos.define(m)", "normal")
    pg.wait_for_timeout(120)
    caixas = pg.evaluate("window.__medicaoRotulos.caixas()")
    a = captura(pg, seletor)
    pg.evaluate("m => window.__medicaoRotulos.define(m)", "sem_preenchimento"); pg.wait_for_timeout(120)
    b = captura(pg, seletor)
    pg.evaluate("m => window.__medicaoRotulos.define(m)", "sem_texto"); pg.wait_for_timeout(120)
    c = captura(pg, seletor)
    pg.evaluate("m => window.__medicaoRotulos.define(m)", "normal")
    res = []
    for cx in caixas:
        x0, y0 = max(0, int(cx["x"]) - 3), max(0, int(cx["y"]) - 3)
        x1, y1 = int(cx["x"] + cx["w"]) + 3, int(cx["y"] + cx["h"]) + 3
        ra, rb, rc = a[y0:y1, x0:x1], b[y0:y1, x0:x1], c[y0:y1, x0:x1]
        if ra.size == 0:
            continue
        la, lb = lum(ra), lum(rb)
        glifo = np.abs(la - lb) > 0.02           # o que o preenchimento pinta, borda suavizada incluída
        if glifo.sum() < 3:
            continue
        viz = dilata(glifo, 2) & ~glifo
        h = cx["cor"].lstrip("#")
        lt = lum(np.array([[int(h[i:i + 2], 16) for i in (0, 2, 4)]], float))[0]
        lviz = lb[viz].max() if viz.any() else 0.0
        lsem = lum(rc.reshape(-1, 3)).max()
        r_com = (max(lt, lviz) + 0.05) / (min(lt, lviz) + 0.05)
        r_sem = (max(lt, lsem) + 0.05) / (min(lt, lsem) + 0.05)
        alt = cx["alt"]
        lim = 3.0 if (alt >= 18.66 or (int(cx["peso"]) >= 700 and alt >= 14)) else 4.5
        res.append((r_com, r_sem, alt, cx["txt"], lim))
    return res


def tatica_do_mapa(mapa: str) -> dict:
    """O que muda no documento da prancheta: uma tática no tempo no centro do radar do mapa (duas peças com função, um
    caminho e uma smoke). O resto do documento (mapa, calibração) é o que a própria página criou."""
    radar = json.loads((RAIZ / "assets" / "radars" / f"{mapa}.json").read_text(encoding="utf-8"))
    cx = radar["origin_x"] + radar["width"] / 2 / radar["scale_px_per_unit"]
    cy = radar["origin_y"] - radar["height"] / 2 / radar["scale_px_per_unit"]

    def op(seq, tipo, **d):
        return {"id": f"m{seq:04d}", "seq": seq, "autor": "medicao", "em": "2026-10-09T00:00:00Z", "tipo": tipo, **d}
    ops = [op(1, "renomeia", titulo="Medição"), op(2, "cria_passo", passo="p1", titulo="saída"),
           op(3, "cria_peca", peca="a", lado="t", rotulo="1", passo="p1", x=cx - 300, y=cy + 100, yaw=0.0),
           op(4, "cria_peca", peca="b", lado="ct", rotulo="1", passo="p1", x=cx + 250, y=cy - 150, yaw=180.0),
           op(5, "cria_caminho", peca="a", pontos=[{"t": 5.0, "x": cx - 150, "y": cy + 20}, {"t": 12.0, "x": cx, "y": cy - 60}]),
           op(6, "cria_granada", granada="s", arma="smoke", passo="p1", t=8.0, jogador="a",
              origem=[cx - 200, cy + 60], destino=[cx + 100, cy - 100]),
           op(7, "planta_bomba", t=30.0, x=cx + 50, y=cy - 200),
           op(8, "define_funcao", peca="a", funcao="Entry fragger"), op(9, "define_funcao", peca="b", funcao="AWPer")]
    return {"id": "medicao00001", "versao": 3, "contador": 9, "operacoes": ops}


def partidas_por_mapa() -> dict[str, str]:
    """A primeira partida de cada mapa com partida no corpus, na ordem do manifesto."""
    man = json.loads((RAIZ / "data" / "manifest.json").read_text(encoding="utf-8"))["partidas"]
    achado: dict[str, str] = {}
    for mid, v in sorted(man.items()):
        achado.setdefault(v["mapa"], mid)
    return achado


def main() -> int:
    rodada = sys.argv[1] if len(sys.argv) > 1 else ""
    p = sync_playwright().start()
    b = chrome(p)
    linhas, piores = [], []
    for w, h in TELAS:
        for mapa, mid in sorted(partidas_por_mapa().items()):
            pg = b.new_page(viewport={"width": w, "height": h}, device_scale_factor=1)
            pg.goto(url_de(f"{mid}.html")); pg.wait_for_timeout(700)
            if not pg.evaluate("!!window.__medicaoRotulos"):
                print("A página não expõe window.__medicaoRotulos (gancho da design-B2, ver a docstring).")
                b.close(); p.stop()
                return 2
            pg.click('[data-tab="replay"]'); pg.wait_for_timeout(300)
            pg.evaluate("""(f) => { const s = document.getElementById('scrub'); s.value = Math.round(+s.max * f);
                                    s.dispatchEvent(new Event('input')); }""", FRACAO_DO_ROUND)
            res = mede(pg, "#map")                 # o canvas do replay (template.html)
            if res:
                pior = min(res)
                linhas.append((w, h, f"replay {mapa}", len(res), pior, sum(1 for r in res if r[0] < r[4]), min(r[2] for r in res)))
                piores.append((pior[0], f"replay {mapa} {w}", pior[3]))
            pg.close()
        # prancheta, em CADA mapa (design-E2): uma tática sintética no centro do radar do mapa -- dois jogadores com
        # nome e função, um caminho com horários e uma smoke --, que dá a mesma mistura de rótulos de uma tática real
        for mapa in sorted(MAPAS):
            pg = b.new_page(viewport={"width": w, "height": h}, device_scale_factor=1)
            pg.goto(url_de(f"prancheta_de_{mapa}.html"))
            pg.wait_for_function("() => Prancheta._interno.S.estado !== null")
            doc = pg.evaluate("Prancheta._interno.S.doc")
            doc.update(tatica_do_mapa(f"de_{mapa}"))
            if not pg.evaluate("(t) => Prancheta._interno.importaTexto(t)", json.dumps(doc)):
                print(f"a prancheta de {mapa} recusou a tática sintética"); pg.close(); continue
            pg.wait_for_timeout(300); pg.mouse.move(2, 2)
            pg.locator("#pr-mapa").evaluate("e => e.scrollIntoView({block: 'start'})"); pg.wait_for_timeout(200)
            res = mede(pg, "#pr-mapa")
            if res:
                pior = min(res)
                linhas.append((w, h, f"prancheta {mapa}", len(res), pior, sum(1 for r in res if r[0] < r[4]), min(r[2] for r in res)))
                piores.append((pior[0], f"prancheta {mapa} {w}", pior[3]))
            pg.close()
    b.close(); p.stop()
    for w, h, onde, n, pior, falhas, alt_min in linhas:
        print(f"{rodada:<7} {w}x{h} {onde:<22} rótulos {n:>3}  altura mín {alt_min:4.1f} px  "
              f"pior com contorno {pior[0]:5.2f}:1 ('{pior[3]}')  pior sem contorno {pior[1]:5.2f}:1  abaixo do critério: {falhas}")
    pior_geral = min(piores) if piores else (0.0, "-", "-")
    print(f"{rodada:<7} PIOR GERAL com contorno: {pior_geral[0]:.2f}:1 ({pior_geral[1]}, '{pior_geral[2]}')")
    return 0 if all(l[5] == 0 for l in linhas) else 1


if __name__ == "__main__":
    raise SystemExit(main())
