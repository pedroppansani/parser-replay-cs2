/* O caminho das peças pelo mapa (PC1, decisão 70): o mesmo cálculo de `scripts/caminhos/busca.py`, no navegador.
   Puro (sem DOM, rede nem armazenamento), como o leitor e o plano; no navegador vem pelo arquivo `caminhos/<mapa>.js` (que entrega o dado) e, em PC2, é usado pelo plano da prancheta e do Reescrever.

   O grafo de um mapa tem NÓS de dois tipos, as células do corpus (0 a nc-1) e as áreas da malha do jogo (nc a nc+na-1), e ligações dirigidas entre eles. O corpus vem primeiro (a ligação área -> área custa a
   distância vezes PENALIDADE); entre andares a malha vem primeiro (o dado já não traz as ligações do corpus que cruzam o andar; as da malha que cruzam custam a distância). O caminho é a linha dos centros; nos
   trechos de áreas da malha o fio é PUXADO (de cada ponto vai direto ao mais longe que a reta ainda cabe nas áreas do trecho).

   `CaminhoDosMapas.cria(dados).caminho([x, y, z|null], [x, y, z|null], fio)` devolve {pontos, comprimento (u), fonte: "corpus" | "malha" | "mista", nos (os índices dos nós da rota), quedas (índices dos trechos que descem 40 u ou mais)} ou null. */
(function (global) {
  "use strict";
  var PENALIDADE = 1.25, RAIO_CELULA = 120, RAIO_AREA = 200, PESO_Z = 0.7, PASSO_FIO = 16, QUEDA = 40, JANELA_FIO = 16;

  function cria(d) {
    var nc = d.nc, na = d.na, n = nc + na, px = new Float64Array(n), py = new Float64Array(n), pz = new Float64Array(n), split = d.andar_z === undefined ? null : d.andar_z;
    var i, k;
    for (i = 0; i < n; i++) { px[i] = d.p[3 * i]; py[i] = d.p[3 * i + 1]; pz[i] = d.p[3 * i + 2]; }
    var poli = d.poli.map(function (q) { var c = []; for (var j = 0; j < q.length; j += 3) c.push([q[j], q[j + 1]]); return c; });
    var adj = new Array(n);
    for (i = 0; i < n; i++) adj[i] = [];
    var ant = 0;
    for (k = 0; k < d.e.length; k += 2) { ant += d.e[k]; adj[ant].push(d.e[k + 1]); }
    var gradeC = {}, gradeA = {};
    function chave(gx, gy) { return gx + "," + gy; }
    for (i = 0; i < nc; i++) { var kc = chave(Math.floor(px[i] / 128), Math.floor(py[i] / 128)); (gradeC[kc] || (gradeC[kc] = [])).push(i); }
    for (var a = 0; a < na; a++) {
      var xs = poli[a].map(function (c) { return c[0]; }), ys = poli[a].map(function (c) { return c[1]; });
      var x0 = Math.floor(Math.min.apply(null, xs) / 128), x1 = Math.floor(Math.max.apply(null, xs) / 128), y0 = Math.floor(Math.min.apply(null, ys) / 128), y1 = Math.floor(Math.max.apply(null, ys) / 128);
      for (var gx = x0; gx <= x1; gx++) for (var gy = y0; gy <= y1; gy++) { var ka = chave(gx, gy); (gradeA[ka] || (gradeA[ka] = [])).push(a); }
    }

    function dist(u, v) { var dx = px[u] - px[v], dy = py[u] - py[v], dz = pz[u] - pz[v]; return Math.sqrt(dx * dx + dy * dy + dz * dz); }
    function cruza(u, v) { return split !== null && (pz[u] < split) !== (pz[v] < split); }
    function peso(u, v) { var m = dist(u, v); return u >= nc && v >= nc && !cruza(u, v) ? m * PENALIDADE : m; }
    function contem(a, x, y) {
      var c = poli[a], pos = false, neg = false;
      for (var j = 0; j < c.length; j++) {
        var A = c[j], B = c[(j + 1) % c.length], s = (B[0] - A[0]) * (y - A[1]) - (B[1] - A[1]) * (x - A[0]);
        if (s > 1e-6) pos = true; else if (s < -1e-6) neg = true;
      }
      return !(pos && neg);
    }

    function noDoPonto(x, y, z) {
      var melhor = null, dm = RAIO_CELULA, gx = Math.floor(x / 128), gy = Math.floor(y / 128), ax, ay, l, j, m;
      for (ax = gx - 1; ax <= gx + 1; ax++) for (ay = gy - 1; ay <= gy + 1; ay++) {
        l = gradeC[chave(ax, ay)] || [];
        for (j = 0; j < l.length; j++) { m = l[j]; var dd = Math.hypot(px[m] - x, py[m] - y) + (z === null ? 0 : Math.abs(pz[m] - z) * PESO_Z); if (dd < dm) { melhor = m; dm = dd; } }
      }
      if (melhor !== null) return melhor;
      var cand = (gradeA[chave(gx, gy)] || []).filter(function (aa) { return contem(aa, x, y); });
      if (cand.length) {
        if (z === null) return nc + cand[0];
        var b = cand[0];
        for (j = 1; j < cand.length; j++) if (Math.abs(pz[nc + cand[j]] - z) < Math.abs(pz[nc + b] - z)) b = cand[j];
        return nc + b;
      }
      dm = RAIO_AREA;
      for (ax = gx - 2; ax <= gx + 2; ax++) for (ay = gy - 2; ay <= gy + 2; ay++) {
        l = gradeA[chave(ax, ay)] || [];
        for (j = 0; j < l.length; j++) { m = nc + l[j]; var d2 = Math.hypot(px[m] - x, py[m] - y) + (z === null ? 0 : Math.abs(pz[m] - z) * PESO_Z); if (d2 < dm) { melhor = m; dm = d2; } }
      }
      return melhor;
    }

    // o A*: heap binário de (f, g, nó), na mesma ordem de desempate da referência em Python
    function rota(a, b) {
      var g = new Float64Array(n).fill(Infinity), pai = new Int32Array(n).fill(-1), fechado = new Uint8Array(n);
      var hf = [], hg = [], hn = [];
      function menor(i1, i2) { return hf[i1] < hf[i2] || (hf[i1] === hf[i2] && (hg[i1] < hg[i2] || (hg[i1] === hg[i2] && hn[i1] < hn[i2]))); }
      function troca(i1, i2) { var f = hf[i1], gg = hg[i1], nn = hn[i1]; hf[i1] = hf[i2]; hg[i1] = hg[i2]; hn[i1] = hn[i2]; hf[i2] = f; hg[i2] = gg; hn[i2] = nn; }
      function empurra(f, gg, nn) { hf.push(f); hg.push(gg); hn.push(nn); var c = hf.length - 1; while (c > 0) { var p = (c - 1) >> 1; if (!menor(c, p)) break; troca(c, p); c = p; } }
      function tira() {
        var f = hf[0], gg = hg[0], nn = hn[0], ult = hf.length - 1;
        hf[0] = hf[ult]; hg[0] = hg[ult]; hn[0] = hn[ult]; hf.pop(); hg.pop(); hn.pop();
        var c = 0, tam = hf.length;
        for (;;) { var l = 2 * c + 1, r = l + 1, m = c; if (l < tam && menor(l, m)) m = l; if (r < tam && menor(r, m)) m = r; if (m === c) break; troca(c, m); c = m; }
        return [f, gg, nn];
      }
      g[a] = 0;
      empurra(dist(a, b), 0, a);
      while (hf.length) {
        var t = tira(), u = t[2], d0 = t[1];
        if (fechado[u]) continue;
        fechado[u] = 1;
        if (u === b) { var r = [b]; while (r[r.length - 1] !== a) r.push(pai[r[r.length - 1]]); return r.reverse(); }
        for (var j = 0; j < adj[u].length; j++) {
          var v = adj[u][j], nd = d0 + peso(u, v);
          if (nd < g[v]) { g[v] = nd; pai[v] = u; empurra(nd + dist(v, b), nd, v); }
        }
      }
      return null;
    }

    function visivel(areas, p, q) {      // `areas`: {id: 1} das áreas do trecho; só as que passam pela quadrícula do ponto são testadas
      var m = Math.max(1, Math.floor(Math.hypot(q[0] - p[0], q[1] - p[1]) / PASSO_FIO));
      for (var j = 0; j <= m; j++) {
        var x = p[0] + (q[0] - p[0]) * j / m, y = p[1] + (q[1] - p[1]) * j / m, ok = false, l = gradeA[chave(Math.floor(x / 128), Math.floor(y / 128))] || [];
        for (var t = 0; t < l.length; t++) if (areas[l[t]] === 1 && contem(l[t], x, y)) { ok = true; break; }
        if (!ok) return false;
      }
      return true;
    }
    function puxaOFio(pts, areas) {
      var fora = [pts[0]], i0 = 0;
      while (i0 < pts.length - 1) {
        var j = Math.min(pts.length - 1, i0 + JANELA_FIO);
        while (j > i0 + 1 && !visivel(areas, pts[i0], pts[j])) j--;
        fora.push(pts[j]);
        i0 = j;
      }
      return fora;
    }

    function caminho(p, q, fio) {
      if (fio === undefined) fio = true;
      var za = p[2] === undefined ? null : p[2], zb = q[2] === undefined ? null : q[2];
      var a = noDoPonto(p[0], p[1], za), b = noDoPonto(q[0], q[1], zb);
      if (a === null || b === null) return null;
      var r = rota(a, b);
      if (r === null) return null;
      var pts = [[p[0], p[1], za !== null ? za : pz[r[0]]]], j;
      for (j = 0; j < r.length; j++) pts.push([px[r[j]], py[r[j]], pz[r[j]]]);
      pts.push([q[0], q[1], zb !== null ? zb : pz[r[r.length - 1]]]);
      var np = pts.length, nosDe = [r[0]].concat(r, [r[r.length - 1]]), ehNav = nosDe.map(function (x) { return x >= nc; });
      var saida = [], k = 0;
      while (k < np) {
        if (!ehNav[k]) { saida.push(pts[k]); k++; continue; }
        var m = k;
        while (m + 1 < np && ehNav[m + 1]) m++;
        var trecho = pts.slice(k, m + 1), areas = {};
        for (j = k; j <= m; j++) areas[nosDe[j] - nc] = 1;
        saida = saida.concat(fio && trecho.length > 2 ? puxaOFio(trecho, areas) : trecho);
        k = m + 1;
      }
      var comp = 0, quedas = [];
      for (j = 0; j < saida.length - 1; j++) {
        comp += Math.sqrt(Math.pow(saida[j][0] - saida[j + 1][0], 2) + Math.pow(saida[j][1] - saida[j + 1][1], 2) + Math.pow(saida[j][2] - saida[j + 1][2], 2));
        if (saida[j + 1][2] - saida[j][2] <= -QUEDA) quedas.push(j);
      }
      var temC = r.some(function (x) { return x < nc; }), temA = r.some(function (x) { return x >= nc; });
      return { pontos: saida, comprimento: comp, fonte: temC && temA ? "mista" : temC ? "corpus" : "malha", nos: r, quedas: quedas };
    }
    return { caminho: caminho, noDoPonto: noDoPonto, nos: n, celulas: nc, areas: na };
  }

  global.CaminhoDosMapas = { cria: cria };
  if (typeof module !== "undefined" && module.exports) module.exports = global.CaminhoDosMapas;
})(typeof window !== "undefined" ? window : this);
