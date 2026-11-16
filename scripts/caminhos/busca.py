"""A busca do caminho (referência em Python; `dashboard/web/comandos/caminho.js` faz o mesmo no navegador). Decisão 70.

O grafo de um mapa (`data/caminhos/<mapa>.json`) tem NÓS de dois tipos: as células do corpus (índices 0 a nc-1) e as áreas da malha do jogo (nc a nc+na-1), e ligações dirigidas entre eles:
células com células (alguém passou), áreas com áreas (a malha liga) e PONTES célula <-> área (o centro da célula está dentro da área, na mesma altura).

A regra da fonte (decisão 70): o corpus primeiro, a malha onde o corpus não passou. Na prática, o custo de uma ligação área -> área é a distância vezes `PENALIDADE_DA_MALHA`
(a malha dos bots faz volta e não tem os pulos de gente: a mesma rota pelo corpus custa menos); a ligação célula -> célula custa a distância. ENTRE ANDARES a malha vem primeiro: as ligações do corpus
que cruzam o andar não entram no grafo, e as da malha que cruzam custam a distância (sem a penalidade).

O caminho é a linha dos centros; nos trechos de áreas da malha o fio é PUXADO: de cada ponto vai direto ao mais longe que a reta ainda cabe nas áreas do trecho (amostrada a cada `PASSO_DO_FIO_U`)."""
from __future__ import annotations

import heapq
import math

PENALIDADE_DA_MALHA = 1.25
RAIO_DA_CELULA_U = 120.0
RAIO_DA_AREA_U = 200.0
PESO_DO_Z = 0.7
GRADE_U = 128      # a quadrícula do índice espacial (u)
PASSO_DO_FIO_U = 16.0
JANELA_DO_FIO = 16      # quantos pontos adiante o fio olha de cada vez (a conta do fio cresce com o quadrado do trecho; 16 mantém o erro e a consulta abaixo de 50 ms com a CPU 4x mais lenta)
QUEDA_U = 40.0
VELOCIDADE_U_S = 250.0


class Caminhos:
    def __init__(self, d: dict):
        self.nc, self.na = d["nc"], d["na"]
        p = d["p"]
        self.n = self.nc + self.na
        self.px = [p[3 * i] for i in range(self.n)]
        self.py = [p[3 * i + 1] for i in range(self.n)]
        self.pz = [p[3 * i + 2] for i in range(self.n)]
        self.split = d.get("andar_z")
        self.poli = [[(q[3 * k], q[3 * k + 1]) for k in range(len(q) // 3)] for q in d["poli"]]
        self.adj: list[list[int]] = [[] for _ in range(self.n)]
        ant = 0
        e = d["e"]
        for k in range(0, len(e), 2):
            ant += e[k]
            self.adj[ant].append(e[k + 1])
        self._grade_c: dict = {}
        self._grade_a: dict = {}
        for i in range(self.nc):
            self._grade_c.setdefault((int(self.px[i] // GRADE_U), int(self.py[i] // GRADE_U)), []).append(i)
        for a in range(self.na):
            xs = [c[0] for c in self.poli[a]]
            ys = [c[1] for c in self.poli[a]]
            for gx in range(int(min(xs) // GRADE_U), int(max(xs) // GRADE_U) + 1):
                for gy in range(int(min(ys) // GRADE_U), int(max(ys) // GRADE_U) + 1):
                    self._grade_a.setdefault((gx, gy), []).append(a)

    def _cruza(self, u: int, v: int) -> bool:
        return self.split is not None and (self.pz[u] < self.split) != (self.pz[v] < self.split)

    def _dist(self, u: int, v: int) -> float:
        return math.sqrt((self.px[u] - self.px[v]) ** 2 + (self.py[u] - self.py[v]) ** 2 + (self.pz[u] - self.pz[v]) ** 2)

    def _peso(self, u: int, v: int) -> float:
        d = self._dist(u, v)
        return d * PENALIDADE_DA_MALHA if u >= self.nc and v >= self.nc and not self._cruza(u, v) else d

    def _contem(self, a: int, x: float, y: float) -> bool:
        poli = self.poli[a]
        pos = neg = False
        for k in range(len(poli)):
            ax, ay = poli[k]
            bx, by = poli[(k + 1) % len(poli)]
            s = (bx - ax) * (y - ay) - (by - ay) * (x - ax)
            if s > 1e-6:
                pos = True
            elif s < -1e-6:
                neg = True
        return not (pos and neg)

    def no_do_ponto(self, x: float, y: float, z: float | None) -> int | None:
        """A célula do corpus mais perto (até `RAIO_DA_CELULA_U`); sem ela, a área da malha que contém o ponto (a de altura mais perto); sem ela, a área de centro mais perto (até `RAIO_DA_AREA_U`)."""
        melhor, dm = None, RAIO_DA_CELULA_U
        gx, gy = int(x // GRADE_U), int(y // GRADE_U)
        for ax in range(gx - 1, gx + 2):
            for ay in range(gy - 1, gy + 2):
                for i in self._grade_c.get((ax, ay), []):
                    d = math.hypot(self.px[i] - x, self.py[i] - y) + (0 if z is None else abs(self.pz[i] - z) * PESO_DO_Z)
                    if d < dm:
                        melhor, dm = i, d
        if melhor is not None:
            return melhor
        cand = [a for a in self._grade_a.get((gx, gy), []) if self._contem(a, x, y)]
        if cand:
            return self.nc + (cand[0] if z is None else min(cand, key=lambda a: abs(self.pz[self.nc + a] - z)))
        dm = RAIO_DA_AREA_U
        for ax in range(gx - 2, gx + 3):
            for ay in range(gy - 2, gy + 3):
                for a in self._grade_a.get((ax, ay), []):
                    i = self.nc + a
                    d = math.hypot(self.px[i] - x, self.py[i] - y) + (0 if z is None else abs(self.pz[i] - z) * PESO_DO_Z)
                    if d < dm:
                        melhor, dm = i, d
        return melhor

    def _rota(self, a: int, b: int) -> list[int] | None:
        g = {a: 0.0}
        pai: dict[int, int] = {}
        fila = [(self._dist(a, b), 0.0, a)]
        fechado: set[int] = set()
        while fila:
            _, d, u = heapq.heappop(fila)
            if u in fechado:
                continue
            fechado.add(u)
            if u == b:
                r = [b]
                while r[-1] != a:
                    r.append(pai[r[-1]])
                return r[::-1]
            for v in self.adj[u]:
                nd = d + self._peso(u, v)
                if nd < g.get(v, math.inf):
                    g[v] = nd
                    pai[v] = u
                    heapq.heappush(fila, (nd + self._dist(v, b), nd, v))
        return None

    def _visivel(self, areas: set[int], p: tuple, q: tuple) -> bool:
        n = max(1, int(math.hypot(q[0] - p[0], q[1] - p[1]) // PASSO_DO_FIO_U))
        for k in range(n + 1):
            x = p[0] + (q[0] - p[0]) * k / n
            y = p[1] + (q[1] - p[1]) * k / n
            if not any(a in areas and self._contem(a, x, y) for a in self._grade_a.get((int(x // GRADE_U), int(y // GRADE_U)), [])):      # só as áreas do trecho que passam por esta quadrícula
                return False
        return True

    def _puxa_o_fio(self, pts: list[tuple], areas: set[int]) -> list[tuple]:
        fora, i = [pts[0]], 0
        while i < len(pts) - 1:
            j = min(len(pts) - 1, i + JANELA_DO_FIO)
            while j > i + 1 and not self._visivel(areas, pts[i], pts[j]):
                j -= 1
            fora.append(pts[j])
            i = j
        return fora

    def caminho(self, p: tuple, q: tuple, fio: bool = True) -> dict | None:
        """`p` e `q` = (x, y, z ou None). Devolve {"pontos", "comprimento" (u), "fonte" ("corpus", "malha" ou "mista"), "nos" (os índices dos nós da rota), "quedas" (índices dos trechos que descem {QUEDA_U} u ou mais)} ou None."""
        a, b = self.no_do_ponto(*p), self.no_do_ponto(*q)
        if a is None or b is None:
            return None
        rota = self._rota(a, b)
        if rota is None:
            return None
        centros = [(self.px[i], self.py[i], self.pz[i]) for i in rota]
        pts = [(p[0], p[1], p[2] if p[2] is not None else centros[0][2])] + centros + [(q[0], q[1], q[2] if q[2] is not None else centros[-1][2])]
        # o fio é puxado em cada trecho SEGUIDO de pontos de áreas da malha (a ponta do caminho conta como o tipo do nó vizinho)
        n = len(pts)
        nos_de = [rota[0]] + rota + [rota[-1]]      # o nó de cada ponto (as pontas usam o vizinho)
        eh_nav = [i >= self.nc for i in nos_de]
        saida: list[tuple] = []
        k = 0
        while k < n:
            if not eh_nav[k]:
                saida.append(pts[k])
                k += 1
                continue
            m = k
            while m + 1 < n and eh_nav[m + 1]:
                m += 1
            trecho = pts[k:m + 1]
            areas = {nos_de[j] - self.nc for j in range(k, m + 1)}
            saida.extend(self._puxa_o_fio(trecho, areas) if fio and len(trecho) > 2 else trecho)
            k = m + 1
        comp = sum(math.dist(saida[i], saida[i + 1]) for i in range(len(saida) - 1))
        tem_c, tem_a = any(i < self.nc for i in rota), any(i >= self.nc for i in rota)
        return {"pontos": [list(x) for x in saida], "comprimento": comp, "fonte": "mista" if tem_c and tem_a else "corpus" if tem_c else "malha", "nos": rota,
                "quedas": [i for i in range(len(saida) - 1) if saida[i + 1][2] - saida[i][2] <= -QUEDA_U]}
