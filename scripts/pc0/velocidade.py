"""PC0: o tempo de calcular um caminho NO NAVEGADOR com a CPU 4 vezes mais lenta (a meta é menos de 50 ms).

    py -3.12 -m scripts.pc0.velocidade de_mirage PASTA_DOS_NAV_JSON

Monta o pacote (como em `pesa.py`) do grafo do corpus (células de 64 u e de 96 u) e do `.nav` (centros), manda para o Chrome (Playwright), liga `Emulation.setCPUThrottlingRate = 4` e mede:
  - montar o grafo (uma vez, ao carregar o arquivo) e
  - 300 consultas entre pontos sorteados dos nós da tabela da C3: achar a célula mais perto de cada ponta + A* (heap binário, heurística em linha reta). Sai a mediana, o p95 e o máximo."""
from __future__ import annotations

import json
import random
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

from scripts.build_tempos import rastros
from scripts.pc0.compara_tempos import z_dos_nos
from scripts.pc0.grafo_corpus import GrafoCorpus
from scripts.pc0.grafo_nav import Grafo
from scripts.pc0.pesa import pacote

JS = r"""
({ pacote, consultas, repete }) => {
  const t0 = performance.now();
  const n = pacote.p.length / 3, px = new Float32Array(n), py = new Float32Array(n), pz = new Float32Array(n);
  for (let i = 0; i < n; i++) { px[i] = pacote.p[3 * i]; py[i] = pacote.p[3 * i + 1]; pz[i] = pacote.p[3 * i + 2]; }
  const m = pacote.e.length / 2, de = new Int32Array(m), para = new Int32Array(m);
  let ant = 0;
  for (let k = 0; k < m; k++) { ant += pacote.e[2 * k]; de[k] = ant; para[k] = pacote.e[2 * k + 1]; }
  const ini = new Int32Array(n + 1);
  for (let k = 0; k < m; k++) ini[de[k] + 1]++;
  for (let i = 0; i < n; i++) ini[i + 1] += ini[i];
  const viz = new Int32Array(m), fim = ini.slice(0, n);
  for (let k = 0; k < m; k++) viz[fim[de[k]]++] = para[k];
  const grade = new Map();      // célula de 120 u -> índices
  for (let i = 0; i < n; i++) { const k = Math.floor(px[i] / 120) * 100003 + Math.floor(py[i] / 120); (grade.get(k) || grade.set(k, []).get(k)).push(i); }
  const montou = performance.now() - t0;
  function perto(x, y, z) {
    let melhor = -1, dm = 150;
    const gx = Math.floor(x / 120), gy = Math.floor(y / 120);
    for (let ax = gx - 2; ax <= gx + 2; ax++) for (let ay = gy - 2; ay <= gy + 2; ay++) { const l = grade.get(ax * 100003 + ay); if (!l) continue;
      for (const i of l) { const d = Math.hypot(px[i] - x, py[i] - y) + Math.abs(pz[i] - z) * 0.7; if (d < dm) { dm = d; melhor = i; } } }
    return melhor;
  }
  const g = new Float64Array(n), vis = new Uint8Array(n), heap = new Int32Array(m + n + 8), hk = new Float64Array(m + n + 8);
  function astar(a, b) {
    g.fill(Infinity); vis.fill(0); let hn = 0;
    const push = (i, k) => { let c = hn++; while (c > 0) { const p = (c - 1) >> 1; if (hk[p] <= k) break; heap[c] = heap[p]; hk[c] = hk[p]; c = p; } heap[c] = i; hk[c] = k; };
    const pop = () => { const r = heap[0]; const i = heap[--hn], k = hk[hn]; let c = 0; for (;;) { let l = 2 * c + 1; if (l >= hn) break; if (l + 1 < hn && hk[l + 1] < hk[l]) l++; if (hk[l] >= k) break; heap[c] = heap[l]; hk[c] = hk[l]; c = l; } heap[c] = i; hk[c] = k; return r; };
    g[a] = 0; push(a, Math.hypot(px[a] - px[b], py[a] - py[b], pz[a] - pz[b]));
    while (hn) {
      const u = pop(); if (vis[u]) continue; vis[u] = 1; if (u === b) return g[b];
      for (let k = ini[u]; k < ini[u + 1]; k++) { const v = viz[k], nd = g[u] + Math.hypot(px[u] - px[v], py[u] - py[v], pz[u] - pz[v]);
        if (nd < g[v]) { g[v] = nd; push(v, nd + Math.hypot(px[v] - px[b], py[v] - py[b], pz[v] - pz[b])); } }
    }
    return Infinity;
  }
  const tempos = [], achou = [];
  for (let r = 0; r < repete; r++) for (const [x1, y1, z1, x2, y2, z2] of consultas) {
    const t = performance.now();
    const a = perto(x1, y1, z1), b = perto(x2, y2, z2);
    const d = a < 0 || b < 0 ? Infinity : astar(a, b);
    tempos.push(performance.now() - t); achou.push(d < Infinity);
  }
  tempos.sort((x, y) => x - y);
  return { montou, mediana: tempos[Math.floor(tempos.length / 2)], p95: tempos[Math.floor(tempos.length * 0.95)], maximo: tempos[tempos.length - 1], consultas: tempos.length, achou: achou.filter(Boolean).length };
}
"""


def main(mapa: str, pasta: Path) -> None:
    t = json.loads(Path(f"data/tempos/{mapa}.json").read_text(encoding="utf-8"))
    lista_nos = t["nos"]
    zn = z_dos_nos(lista_nos, mapa)
    pts = [(n[1], n[2], zn[n[0]]) for n in lista_nos if zn[n[0]] is not None]
    rnd = random.Random(1)
    consultas = [list(rnd.choice(pts)) + list(rnd.choice(pts)) for _ in range(300)]
    rs = rastros(mapa)
    g = Grafo(pasta / f"{mapa}.json")
    ids = list(g.areas)
    pos = {i: k for k, i in enumerate(ids)}
    pacotes = {"nav (centros)": pacote([g.cent[i] for i in ids], [(pos[a], pos[b]) for a in ids for b in g.lig[a] if b in pos])}
    for s in (64, 96):
        gc = GrafoCorpus(rs, s=s, zs=48, min_visitas=3, min_ligacoes=2)
        cel = sorted(gc.celulas)
        idx = {c: k for k, c in enumerate(cel)}
        pacotes[f"corpus {s} u"] = pacote([gc.centro[c] for c in cel], [(idx[a], idx[b]) for a, bs in gc.adj.items() for b in bs])
    with sync_playwright() as p:
        nav = p.chromium.launch(channel="chrome")
        for lento in (1, 4):
            pg = nav.new_page()
            pg.goto("about:blank")
            cdp = pg.context.new_cdp_session(pg)
            cdp.send("Emulation.setCPUThrottlingRate", {"rate": lento})
            for nome, pk in pacotes.items():
                r = pg.evaluate(JS, {"pacote": pk, "consultas": consultas, "repete": 1})
                print(f"CPU {lento}x  {nome:14s} montar {r['montou']:6.1f} ms; consulta mediana {r['mediana']:.2f} ms, p95 {r['p95']:.2f} ms, máximo {r['maximo']:.1f} ms ({r['achou']}/{r['consultas']} com caminho)")
            pg.close()
        nav.close()


if __name__ == "__main__":
    main(sys.argv[1], Path(sys.argv[2]))
