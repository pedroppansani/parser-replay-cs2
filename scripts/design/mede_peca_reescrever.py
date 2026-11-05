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
  return { pior, abaixo, n, halo, contorno, fundo };
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
    print(f"{'mapa':<12}{'pior pixel':>12}{'abaixo de 3:1':>18}")
    for mapa, arq in sorted(mapas.items()):
        pg = b.new_page(viewport={"width": 1440, "height": 900})
        pg.goto(url_de(arq + "#replay"))
        pg.wait_for_timeout(900)
        r = pg.evaluate(JS)
        pg.close()
        if not r:
            print(f"{mapa:<12}{'sem radar':>12}")
            continue
        ok = r["pior"] >= MINIMO
        falhou += not ok
        print(f"{mapa:<12}{r['pior']:>11.2f}:1{r['abaixo']:>11} de {r['n']}  {'PASSA' if ok else 'FALHA'}")
    b.close()
    p.stop()
    return 1 if falhou else 0


if __name__ == "__main__":
    raise SystemExit(main())
