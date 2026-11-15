"""PC0: um grafo de passagens montado SÓ das trajetórias do corpus.

Uma CÉLULA é um quadrado de `S` u por uma faixa de `ZS` u de altura que alguém pisou (em pelo menos `MIN_VISITAS` rastros). Uma LIGAÇÃO dirigida A -> B existe quando um jogador de verdade passou
de A para B em amostras seguidas (0,125 s) em pelo menos `MIN_LIGACOES` rastros: uma queda só existe no sentido em que foi feita, e nenhuma parede é atravessada (ninguém atravessa).
O peso da ligação é a distância entre os centros das duas células (a média das amostras que caíram nelas)."""
from __future__ import annotations

import heapq
import math
from collections import defaultdict

import numpy as np

S = 40.0           # u: lado da célula
ZS = 48.0          # u: altura da faixa (a do degrau do jogo é 18; 48 separa um andar do outro sem partir uma rampa)
MIN_VISITAS = 3
MIN_LIGACOES = 2
SALTO_MAX = 160.0  # u: o máximo que um jogador anda entre duas amostras seguidas (250 u/s x 0,125 s = 31 u; folga para queda e erro)


class GrafoCorpus:
    def __init__(self, rastros: list[dict], s: float = S, zs: float = ZS, min_visitas: int = MIN_VISITAS, min_ligacoes: int = MIN_LIGACOES):
        S_, ZS_ = s, zs
        visitas: dict[tuple, set] = defaultdict(set)
        soma: dict[tuple, list] = defaultdict(lambda: [0.0, 0.0, 0.0, 0])
        lig: dict[tuple, set] = defaultdict(set)
        for ri, r in enumerate(rastros):
            x, y, z = r["x"], r["y"], r["z"]
            gx, gy, gz = np.floor(x / S_).astype(int), np.floor(y / S_).astype(int), np.floor(z / ZS_).astype(int)
            chave = list(zip(gx.tolist(), gy.tolist(), gz.tolist()))
            ok = (np.diff(r["tick"]) <= 2 * r["passo"]) & (np.hypot(np.diff(x), np.diff(y)) < SALTO_MAX) & (np.abs(np.diff(z)) < 400)
            for k, c in enumerate(chave):
                visitas[c].add(ri)
                s = soma[c]
                s[0] += x[k]
                s[1] += y[k]
                s[2] += z[k]
                s[3] += 1
                if k + 1 < len(chave) and ok[k] and chave[k + 1] != c:
                    lig[(c, chave[k + 1])].add(ri)
        self.celulas = {c for c, v in visitas.items() if len(v) >= min_visitas}
        self.centro = {c: (soma[c][0] / soma[c][3], soma[c][1] / soma[c][3], soma[c][2] / soma[c][3]) for c in self.celulas}
        self.adj: dict[tuple, list[tuple]] = defaultdict(list)
        self.ligacoes = 0
        self.n_lig: dict[tuple, int] = {}      # quantos rastros fizeram cada ligação
        self.visitas = {c: len(v) for c, v in visitas.items() if c in self.celulas}
        for (a, b), rs in lig.items():
            if len(rs) >= min_ligacoes and a in self.celulas and b in self.celulas:
                self.adj[a].append(b)
                self.n_lig[(a, b)] = len(rs)
                self.ligacoes += 1
        self.s = S_
        self._idx: dict[tuple[int, int], list] = defaultdict(list)
        for c in self.celulas:
            self._idx[(int(self.centro[c][0] // 120), int(self.centro[c][1] // 120))].append(c)

    def celula_do_ponto(self, x: float, y: float, z: float | None, raio: float = 120.0):
        melhor, dm = None, raio
        g0x, g0y = int(x // 120), int(y // 120)
        for ax in range(g0x - 2, g0x + 3):
            for ay in range(g0y - 2, g0y + 3):
                for c in self._idx.get((ax, ay), []):
                    cx, cy, cz = self.centro[c]
                    d = math.hypot(cx - x, cy - y) + (0 if z is None else abs(cz - z) * 0.7)
                    if d < dm:
                        melhor, dm = c, d
        return melhor

    def caminho(self, a, b):
        dist = {a: 0.0}
        pai: dict = {}
        fila = [(0.0, a)]
        while fila:
            d, u = heapq.heappop(fila)
            if u == b:
                rota = [b]
                while rota[-1] != a:
                    rota.append(pai[rota[-1]])
                return rota[::-1], d
            if d > dist.get(u, math.inf):
                continue
            cu = self.centro[u]
            for v in self.adj.get(u, []):
                nd = d + math.dist(cu, self.centro[v])
                if nd < dist.get(v, math.inf):
                    dist[v] = nd
                    pai[v] = u
                    heapq.heappush(fila, (nd, v))
        return None

    def comprimento_entre_pontos(self, p, q):
        a, b = self.celula_do_ponto(*p), self.celula_do_ponto(*q)
        if a is None or b is None:
            return None
        r = self.caminho(a, b)
        if r is None:
            return None
        rota, comp = r
        return rota, comp
