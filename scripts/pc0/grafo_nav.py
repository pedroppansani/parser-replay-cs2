"""PC0: o grafo dirigido dos `.nav` exportados (ver `exporta_nav.py`): achar a área de um ponto e o comprimento do caminho entre dois pontos."""
from __future__ import annotations

import heapq
import json
import math
from pathlib import Path

import numpy as np


GRADE_U = 128      # a quadrícula do índice espacial (u)


class Grafo:
    def __init__(self, caminho: Path):
        d = json.loads(caminho.read_text(encoding="utf-8"))
        self.areas = {int(k): v for k, v in d["areas"].items()}
        self.ids = list(self.areas)
        self.cent = {i: tuple(np.mean(a["c"], axis=0)) for i, a in self.areas.items()}
        self.poly = {i: np.array(a["c"], dtype=float) for i, a in self.areas.items()}
        self.lig = {i: [j for j in a["lig"] if j in self.areas] for i, a in self.areas.items()}
        # as ESCADAS (ladders): o `.nav` as guarda à parte; a área de baixo diz "escada acima: id" e a de cima "escada abaixo: id": o mesmo id liga as duas, nos dois sentidos
        embaixo: dict[int, list[int]] = {}
        em_cima: dict[int, list[int]] = {}
        for i, a in self.areas.items():
            for e in a["esc_cima"]:
                embaixo.setdefault(int(e), []).append(i)
            for e in a["esc_baixo"]:
                em_cima.setdefault(int(e), []).append(i)
        self.escadas = 0
        for e, bs in embaixo.items():
            for b in bs:
                for c in em_cima.get(e, []):
                    self.lig[b].append(c)
                    self.lig[c].append(b)
                    self.escadas += 1
        # índice em grade de 128 u das caixas das áreas
        self._g: dict[tuple[int, int], list[int]] = {}
        for i, p in self.poly.items():
            x0, y0 = p[:, 0].min(), p[:, 1].min()
            x1, y1 = p[:, 0].max(), p[:, 1].max()
            for gx in range(int(x0 // GRADE_U), int(x1 // GRADE_U) + 1):
                for gy in range(int(y0 // GRADE_U), int(y1 // GRADE_U) + 1):
                    self._g.setdefault((gx, gy), []).append(i)

    def contem(self, i: int, x: float, y: float) -> bool:
        p = self.poly[i][:, :2]
        n = len(p)
        sinais = []
        for k in range(n):
            ax, ay = p[k]
            bx, by = p[(k + 1) % n]
            sinais.append((bx - ax) * (y - ay) - (by - ay) * (x - ax))
        return all(s >= -1e-6 for s in sinais) or all(s <= 1e-6 for s in sinais)

    def area_do_ponto(self, x: float, y: float, z: float | None, tol_xy: float = 200.0) -> int | None:
        """A área que contém (x, y) e está mais perto de `z` (andares sobrepostos); sem nenhuma, a de centro mais perto num raio de `tol_xy` u."""
        cand = [i for i in self._g.get((int(x // GRADE_U), int(y // GRADE_U)), []) if self.contem(i, x, y)]
        if cand:
            if z is None:
                return cand[0]
            return min(cand, key=lambda i: abs(self.cent[i][2] - z))
        melhor, dm = None, tol_xy
        for gx in range(int(x // GRADE_U) - 2, int(x // GRADE_U) + 3):
            for gy in range(int(y // GRADE_U) - 2, int(y // GRADE_U) + 3):
                for i in self._g.get((gx, gy), []):
                    c = self.cent[i]
                    d = math.hypot(c[0] - x, c[1] - y) + (0 if z is None else abs(c[2] - z) * 0.5)
                    if d < dm:
                        melhor, dm = i, d
        return melhor

    def caminho(self, a: int, b: int) -> tuple[list[int], float] | None:
        """Dijkstra pela distância entre centros (3D); devolve (áreas, comprimento) ou None."""
        dist = {a: 0.0}
        pai: dict[int, int] = {}
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
            cu = self.cent[u]
            for v in self.lig[u]:
                cv = self.cent[v]
                nd = d + math.dist(cu, cv)
                if nd < dist.get(v, math.inf):
                    dist[v] = nd
                    pai[v] = u
                    heapq.heappush(fila, (nd, v))
        return None

    def visivel(self, rota: list[int], p: tuple, q: tuple, passo: float = 16.0) -> bool:
        """A reta de p a q fica toda sobre áreas da `rota` (nenhuma parede no meio)? Amostra a cada `passo` u."""
        n = max(1, int(math.hypot(q[0] - p[0], q[1] - p[1]) // passo))
        for k in range(n + 1):
            x = p[0] + (q[0] - p[0]) * k / n
            y = p[1] + (q[1] - p[1]) * k / n
            if not any(self.contem(i, x, y) for i in rota):
                return False
        return True

    def comprimento_entre_pontos(self, p: tuple, q: tuple, suave: bool = True):
        a, b = self.area_do_ponto(*p), self.area_do_ponto(*q)
        if a is None or b is None:
            return None
        r = self.caminho(a, b)
        if r is None:
            return None
        rota, _ = r
        pts = [(p[0], p[1], self.cent[a][2])] + [self.cent[i] for i in rota[1:-1]] + [(q[0], q[1], self.cent[b][2])]
        if suave and len(pts) > 2:      # "puxa o fio": de cada ponto vai direto ao mais longe que a reta ainda cabe nas áreas da rota
            fora, i = [pts[0]], 0
            while i < len(pts) - 1:
                j = len(pts) - 1
                while j > i + 1 and not self.visivel(rota, pts[i], pts[j]):
                    j -= 1
                fora.append(pts[j])
                i = j
            pts = fora
        return rota, sum(math.dist(pts[k], pts[k + 1]) for k in range(len(pts) - 1))
