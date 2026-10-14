"""
Capturas da granada desenhada V3 (fase 15) nas páginas reais de `docs/` (rode `py -3.12 -m scripts.build_site` antes).

    py -3.12 -m scripts.design.captura_granada <pasta de saída>

Por página (replay = match_02.html#replay, prancheta = prancheta_de_mirage.html) e por largura (1440 e 375 px):
as quatro granadas REAIS numa linha e as quatro DESENHADAS na linha de baixo, desenhadas pelo `MapCore.nadeGlyph` da
própria página sobre uma camada transparente posta em cima do canvas do mapa (mesma escala em px de tela); a
legenda do replay; e um recorte ampliado (3x) do par smoke real e desenhada. Nomes `granada-*`.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.dont_write_bytecode = True

from scripts.design._comum import DOCS, chrome  # noqa: E402

PAGINAS = {"replay": ("match_02.html#replay", "#map"), "prancheta": ("prancheta_de_mirage.html", "#pr-mapa")}
LARGURAS = {"1440": (1440, 900), "375": (375, 812)}
TIPOS = ["smoke", "flash", "he", "molotov"]

DESENHA = r"""
([seletor, tipos]) => {
  const cv = document.querySelector(seletor);
  cv.scrollIntoView({block: "center"});
  const r = cv.getBoundingClientRect(), dpr = window.devicePixelRatio || 1;
  const o = document.createElement("canvas");
  o.id = "camada-granada";
  o.width = Math.round(r.width * dpr); o.height = Math.round(r.height * dpr);
  o.style.cssText = "position:fixed;pointer-events:none;z-index:99;left:" + r.left + "px;top:" + r.top + "px;width:" + r.width + "px;height:" + r.height + "px";
  document.body.appendChild(o);
  const ctx = o.getContext("2d"), k = r.width / 1024, s = k * dpr;      // px de tela por px do radar (zoom 1)
  MapCore.defineAnelDuplo(true);
  const centros = [];
  tipos.forEach((t, i) => {
    const px = (0.34 + i * 0.1) * r.width, ox = px / k;
    [["real", 0.46], ["desenhada", 0.54]].forEach(([modo, fy]) => {
      const oy = fy * r.height / k;
      ctx.setTransform(s, 0, 0, s, ox * s, oy * s);
      MapCore.nadeGlyph(ctx, t, 0, 0, modo === "real" ? 5.5 : 7, MapCore.NADE_COLOR[t], -Math.PI / 2, modo === "desenhada");
      centros.push([modo, t, r.left + px, r.top + fy * r.height]);
    });
  });
  return {caixa: [r.left, r.top, r.width, r.height], centros};
}
"""


def main(saida: Path) -> None:
    from playwright.sync_api import sync_playwright
    saida.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        nav = chrome(p)
        for pagina, (arq, seletor) in PAGINAS.items():
            for nome, (w, h) in LARGURAS.items():
                ctx = nav.new_context(viewport={"width": w, "height": h}, device_scale_factor=2)
                pg = ctx.new_page()
                pg.goto((DOCS / arq.split("#")[0]).as_uri() + ("#" + arq.split("#")[1] if "#" in arq else ""))
                pg.wait_for_timeout(1500)
                if pagina == "replay":
                    pg.click('[data-tab="replay"]') if pg.locator('[data-tab="replay"]').count() else None
                    pg.wait_for_timeout(800)
                info = pg.evaluate(DESENHA, [seletor, TIPOS])
                pg.wait_for_timeout(200)
                x, y, cw, ch = info["caixa"]
                pg.screenshot(path=str(saida / f"granada-{pagina}-{nome}.png"),
                              clip={"x": max(x, 0), "y": max(y, 0), "width": min(cw, w), "height": min(ch, h)})
                # recorte ampliado: a smoke real e a desenhada lado a lado (e as demais), 3x
                cs = info["centros"]
                x0 = min(c[2] for c in cs) - 30; x1 = max(c[2] for c in cs) + 30
                y0 = min(c[3] for c in cs) - 34; y1 = max(c[3] for c in cs) + 30
                ctx.close()
                ctx2 = nav.new_context(viewport={"width": w, "height": h}, device_scale_factor=4)
                pg2 = ctx2.new_page()
                pg2.goto((DOCS / arq.split("#")[0]).as_uri() + ("#" + arq.split("#")[1] if "#" in arq else ""))
                pg2.wait_for_timeout(1500)
                if pagina == "replay" and pg2.locator('[data-tab="replay"]').count():
                    pg2.click('[data-tab="replay"]'); pg2.wait_for_timeout(800)
                info2 = pg2.evaluate(DESENHA, [seletor, TIPOS])
                pg2.wait_for_timeout(200)
                pg2.screenshot(path=str(saida / f"granada-{pagina}-{nome}-recorte.png"),
                               clip={"x": max(x0, 0), "y": max(y0, 0), "width": min(x1 - x0, w), "height": min(y1 - y0, h)})
                if pagina == "replay":
                    pg2.locator("#maplegend").screenshot(path=str(saida / f"granada-legenda-{nome}.png"))
                ctx2.close()
        nav.close()


if __name__ == "__main__":
    main(Path(sys.argv[1]))
