"""Contraste da peça da "Sua versão" contra o radar de cada mapa (Reescrever R2, condição do Pedro: no mínimo 3:1, nos mapas com radar).

A peça é o disco do lado com o anel duplo (halo claro `--tinta` por fora do contorno escuro `--contorno`, entrega-sala-de-demo §4.1): onde
o radar é claro o contorno separa, onde é escuro o halo separa. Para cada pixel do radar PROCESSADO (o que o canvas desenha: dessaturado,
sobre o fundo `--radar`) vale o melhor dos dois contrastes; o número do mapa é o PIOR pixel. Mede `docs/` (uma partida de cada mapa) em Chrome.

    py -3.12 -m scripts.design.mede_peca_reescrever            # imprime a tabela e devolve 1 se algum mapa ficar abaixo de 3:1
"""
import sys

sys.dont_write_bytecode = True
from playwright.sync_api import sync_playwright

from scripts.design._comum import DOCS, chrome, url_de

MINIMO = 3.0
JS = """async () => {
  const R = window.__RADAR__;
  if (!R || !R.image) return null;
  const css = n => getComputedStyle(document.documentElement).getPropertyValue(n).trim();
  const rgb = h => { const c = document.createElement('canvas').getContext('2d'); c.fillStyle = h; c.fillRect(0, 0, 1, 1); return Array.from(c.getImageData(0, 0, 1, 1).data).slice(0, 3); };
  const lum = c => { const f = v => { v /= 255; return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4); }; return 0.2126 * f(c[0]) + 0.7152 * f(c[1]) + 0.0722 * f(c[2]); };
  const cr = (a, b) => { const x = lum(a), y = lum(b); return (Math.max(x, y) + 0.05) / (Math.min(x, y) + 0.05); };
  const halo = rgb(css('--tinta-mapa') || css('--tinta')), contorno = rgb(css('--contorno')), fundo = rgb(css('--radar'));
  const im = new Image(); im.src = R.image; await im.decode();
  const proc = MapCore.radarProcessado(im, R.map);
  const W = 256, H = Math.round(256 * proc.height / proc.width);
  const c = document.createElement('canvas'); c.width = W; c.height = H; const x = c.getContext('2d');
  x.fillStyle = css('--radar'); x.fillRect(0, 0, W, H); x.drawImage(proc, 0, 0, W, H);
  const d = x.getImageData(0, 0, W, H).data; let pior = 99, abaixo = 0, n = 0;
  for (let i = 0; i < d.length; i += 4) { const p = [d[i], d[i + 1], d[i + 2]]; const v = Math.max(cr(p, halo), cr(p, contorno)); n++; if (v < pior) pior = v; if (v < 3) abaixo++; }
  // o FANTASMA (R3): o anel tracejado de raio 12, desenhado de verdade pelo MapCore sobre o radar processado, em 400 posições; em cada tracinho
  // compara o pixel do halo (fora) e o do contorno (dentro) com o pixel do radar no mesmo lugar, e vale o melhor dos dois
  const g = document.createElement('canvas'); g.width = proc.width; g.height = proc.height;
  const gx = g.getContext('2d'); gx.drawImage(proc, 0, 0);
  const base = gx.getImageData(0, 0, g.width, g.height), RF = 12, tracos = [];
  const lado = css('--ct-mapa');
  for (let i = 0; i < 20; i++) for (let j = 0; j < 20; j++) {
    const X = Math.round(proc.width * (0.1 + 0.8 * i / 19)), Y = Math.round(proc.height * (0.1 + 0.8 * j / 19));
    const c = document.createElement('canvas'); c.width = 80; c.height = 80;
    const cx = c.getContext('2d'); cx.drawImage(proc, X - 40, Y - 40, 80, 80, 0, 0, 80, 80);
    const antes = cx.getImageData(0, 0, 80, 80);
    MapCore.desenhaJogador(cx, 40, 40, { cor: lado, estado: 'fantasma', escala: 1.5, raio: RF, nome: null });
    const depois = cx.getImageData(0, 0, 80, 80);
    // 12 tracinhos: a cada 2π/ (perímetro / 9) rad; a metade "ligada" de cada passo 5/4 começa em 0 e vai a 5/9 do passo
    const passo = 9 / RF, k = Math.floor(2 * Math.PI * RF / 9);
    for (let t = 0; t < k; t++) {
      const ang = (t + 2.5 / 9) * passo;
      const pix = (r) => { const px = Math.round(40 + Math.cos(ang) * r), py = Math.round(40 + Math.sin(ang) * r), o = (py * 80 + px) * 4; return [[depois.data[o], depois.data[o + 1], depois.data[o + 2]], [antes.data[o], antes.data[o + 1], antes.data[o + 2]]]; };
      let cc = 0;                                  // o melhor contraste do tracinho (halo ou contorno) contra o radar no mesmo pixel, ao longo do raio
      for (let r = RF - 4; r <= RF + 4.01; r += 0.5) { const q = pix(r); cc = Math.max(cc, cr(q[0], q[1])); }
      tracos.push(cc);
    }
  }
  const piorG = Math.min.apply(null, tracos), abaixoG = tracos.filter(v => v < 3).length;
  return { pior, abaixo, n, halo, contorno, fundo, piorG, abaixoG, nG: tracos.length };
}"""


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    from scripts.build_site import match_summary
    mapas: dict[str, str] = {}
    for d in sorted((DOCS.parent / "data" / "processed").glob("match_*")):
        m = match_summary(d.name)
        if m and m["has_radar"] and m["map"] not in mapas:
            mapas[m["map"]] = m["file"]
    falhou = 0
    p = sync_playwright().start()
    b = chrome(p)
    print(f"{'mapa':<12}{'peça':>10}{'fantasma':>12}{'tracinhos abaixo de 3:1':>28}")
    for mapa, arq in sorted(mapas.items()):
        pg = b.new_page(viewport={"width": 1440, "height": 900})
        pg.goto(url_de(arq + "#replay"))
        pg.wait_for_timeout(900)
        r = pg.evaluate(JS)
        pg.close()
        if not r:
            print(f"{mapa:<12}{'sem radar':>12}")
            continue
        ok = r["pior"] >= MINIMO and r["piorG"] >= MINIMO
        falhou += not ok
        print(f"{mapa:<12}{r['pior']:>9.2f}:1{r['piorG']:>10.2f}:1{r['abaixoG']:>14} de {r['nG']}  {'PASSA' if ok else 'FALHA'}")
    b.close()
    p.stop()
    return 1 if falhou else 0


if __name__ == "__main__":
    raise SystemExit(main())
