"""P1b: o nome da peça ("TR 2") perto do relógio grande e da borda de cima do mapa na prancheta.

    py -3.12 -m scripts.design.capturas_nome_da_peca <pasta_de_saida> [raiz_do_codigo]

`raiz_do_codigo` (opcional) é outra cópia do projeto (um `git worktree` de antes de uma fase): serve para mostrar como era antes. Sem ele, usa este.
Para cada mapa e tamanho (375, 1366x657, 1440x900) a peça fica na borda de cima (3 posições), no meio e na borda de baixo (e, na Nuke, também com o andar de baixo aberto); o relógio aparece
(o formato 3 tem horário). Escreve também, por captura, se a caixa do nome cobre o relógio ou sai do mapa (medida pela camada de rótulos).
A prancheta é sempre violeta: o tema claro e o escuro saem iguais.
"""
from __future__ import annotations

import importlib
import sys
import tempfile
from pathlib import Path

from playwright.sync_api import sync_playwright

TAMANHOS = [("375", 375, 812), ("1366", 1366, 657), ("1440", 1440, 900)]
MAPAS = ["de_mirage", "de_nuke"]
# (nome, fração x do mapa, fração y do mapa) da área visível do mapa (a tela, já com o zoom da Nuke); "sob-o-relogio" = no centro do relógio
POSICOES = [("topo-esq", 0.12, 0.03), ("topo-meio", 0.5, 0.03), ("topo-dir", 0.88, 0.03), ("meio", 0.5, 0.5), ("baixo", 0.5, 0.97), ("sob-o-relogio", None, None)]


def main() -> None:
    saida = Path(sys.argv[1]); saida.mkdir(parents=True, exist_ok=True)
    raiz = Path(sys.argv[2]).resolve() if len(sys.argv) > 2 else Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(raiz))
    build_html = importlib.import_module("scripts.build_tactics_page").build_html
    assert Path(importlib.import_module("scripts.build_tactics_page").__file__).resolve().is_relative_to(raiz), "importou o código de outra pasta"
    with sync_playwright() as p:
        nav = p.chromium.launch(channel="chrome")
        for mapa in MAPAS:
            pagina = Path(tempfile.mkdtemp(prefix="nome_peca_")) / f"{mapa}.html"
            pagina.write_text(build_html(mapa), encoding="utf-8")
            for rotulo, w, h in TAMANHOS:
                ctx = nav.new_context(viewport={"width": w, "height": h}, device_scale_factor=1)
                for nome, fx, fy, andar in [(n, x, y, 0) for n, x, y in POSICOES] + ([(n + "-andar-de-baixo", x, y, 1) for n, x, y in POSICOES if n != "meio"] if mapa == "de_nuke" and w > 640 else []):
                    pg = ctx.new_page(); pg.goto(pagina.as_uri()); pg.wait_for_function("() => Prancheta._interno.S.estado !== null")
                    if andar:
                        pg.click('[data-andar="1"]', timeout=3000)
                    pg.evaluate("""([fx, fy, nivel]) => { const I = Prancheta._interno, S = I.S;
                        const cv = document.getElementById('pr-mapa'), v = S.view || { zoom: 1, panX: 0, panY: 0 };
                        const cr = cv.getBoundingClientRect(), rr = document.getElementById('pr-relogio-grande').getBoundingClientRect(), kk = 1024 / cr.width;
                        const sx = fx === null ? rr.left - cr.left + rr.width / 2 : fx * cr.width, sy = fy === null ? rr.top - cr.top + rr.height / 2 : fy * cr.height;
                        const rpx = [(sx * kk - v.panX) / v.zoom, (sy * kk - v.panY) / v.zoom]; const g = I.pixelParaJogo(rpx[0], rpx[1]);
                        I.emiteLote([["cria_peca", { peca: "demo-tr2", lado: "t", rotulo: "2", passo: S.estado.passos[0].passo, x: g[0], y: g[1], nivel: nivel }]]); }""", [fx, fy, andar])
                    pg.wait_for_timeout(250); pg.mouse.move(2, 2)
                    # a caixa do nome (px de tela, relativa ao canvas) contra o relógio grande
                    med = pg.evaluate("""() => { const cv = document.getElementById('pr-mapa'), rc = cv.getBoundingClientRect();
                        const rel = document.getElementById('pr-relogio-grande'), rr = rel && !rel.hidden ? rel.getBoundingClientRect() : null;
                        return { canvas: [rc.left, rc.top, rc.width, rc.height], relogio: rr ? [rr.left, rr.top, rr.width, rr.height] : null,
                                 caixas: window.__medicaoRotulos.caixas() }; }""")
                    cx = med["caixas"]
                    cobre = ""
                    if med["relogio"] and cx:
                        rl, rt, rw, rh = med["relogio"]; cl, ct, _, _ = med["canvas"]
                        for c in cx:
                            if c.get("txt", "").strip() and c["x"] + cl < rl + rw and c["x"] + cl + c["w"] > rl and c["y"] + ct < rt + rh and c["y"] + ct + c["h"] > rt:
                                cobre = f" COBRE O RELÓGIO ({c['txt']})"
                    print(f"{mapa} {rotulo} {nome}: relógio={'sim' if med['relogio'] else 'não'}, caixas={[c.get('txt') for c in cx]}{cobre}")
                    pg.screenshot(path=str(saida / f"{mapa}-{rotulo}-{nome}.png"), full_page=True)
                    pg.close()
                ctx.close()
        nav.close()


if __name__ == "__main__":
    main()
