"""Quem estava vendo quem (fase 18, item 18.1): linha de visão pelo mapa mais o campo de visão.

JUSTIFICATIVA DE JOGO. "Não trocou", "possível bait", "perdeu a troca" e "morreu sozinho" só fazem
sentido sabendo se o matador ficou EXPOSTO para o jogador: se o inimigo abriu pela lateral, matou e
recuou sem nunca aparecer na tela de quem estava perto, ninguém deixou de trocar (definição do Pedro,
fase 18). "Visível para o jogador" é a combinação de duas coisas:

1. **Linha de visão pelo mapa**: o segmento dos olhos do jogador até o alvo não atravessa nenhum
   triângulo da colisão do mapa nem uma smoke ativa;
2. **Campo de visão**: o alvo está a menos de `MEIO_FOV_GRAUS` da direção horizontal do olhar;
3. e quem olha **não está cego** por flash (a mesma cegueira efetiva de `metrics.grenades`, acima de
   `EFFECTIVE_BLIND_SECONDS`): cego, não vê ninguém.

Por que a linha de visão pelo mapa e não a visibilidade gravada na demo (`m_bSpottedByMask`, que o
demoparser2 0.42 lê como `approximate_spotted_by`): a demo só existe no disco para parte do corpus (a
maioria das partidas só tem o interim), e a régua do Perfil compara jogadores entre partidas; misturar
duas fontes de visão faria a régua comparar coisas medidas de jeitos diferentes. A visibilidade da demo
fica como CONFERÊNCIA da linha de visão (nota `notas/investigacoes/2026-10-15-fonte-de-visao.md`).

A malha é a colisão de cada mapa publicada pelo `awpy-data` (o projeto de dados do awpy), convertida
para o formato `.tri` do awpy 2.0.2 por `scripts/visao_malhas.py`, que confere o sha256 de cada arquivo
(`metrics/visao_malhas.json`). O verificador do awpy 2.0.2 (`awpy.visibility.VisibilityChecker`) dá a
mesma resposta que `Malha.linha_livre` (o mesmo teste de Möller–Trumbore, com as mesmas tolerâncias:
`tests/test_visao.py` compara os dois), mas é Python puro numa árvore de objetos: construir a árvore da
Inferno (548 mil triângulos) leva minutos e cada consulta leva milissegundos. Aqui a mesma conta é feita
numa grade do plano com numpy.

Função pura e determinística: as mesmas posições e a mesma malha dão sempre a mesma resposta.
"""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

import numpy as np
import polars as pl

from metrics.constantes import RAIO_SMOKE_UNIDADES
from metrics.geometry import EYE_HEIGHT_CROUCHED, EYE_HEIGHT_STANDING

# --- Constantes (fase 18). Cada uma está no material de calibração, seção 7 ------------------------

# Metade do campo de visão HORIZONTAL do CS2 em 16:9. O jogo fixa o campo de visão em 90 graus na
# horizontal de uma tela 4:3 (fov_cs_debug 90) e alarga a horizontal nas telas largas mantendo a
# vertical (o "Hor+" do motor Source): em 16:9, tan(h/2) = tan(45°) x (16/9) / (4/3) = 4/3, então
# h = 106,26 graus e a metade é 53,13. Quem joga em 4:3 esticado vê menos (45 graus de cada lado);
# 16:9 é o pedido do Pedro (18.1, item 3).
MEIO_FOV_GRAUS = round(math.degrees(math.atan(math.tan(math.radians(45.0)) * (16 / 9) / (4 / 3))), 2)

# De quantos em quantos ticks a visão é conferida dentro de uma janela. 8 ticks = 1/8 s a 64 ticks.
# Origem: a visibilidade gravada na demo é atualizada de 33 em 33 ticks (medido na match_23, ver a
# nota da fonte de visão); 8 ticks é quatro vezes mais fino e fica abaixo do tempo de reação humano
# (~0,2 s = 13 ticks): um inimigo que aparece por menos que isso não dava para trocar.
AMOSTRA_VISAO_TICKS = 8

# Pontos do alvo conferidos: a linha dos olhos (a cabeça) e o meio do corpo. Basta um estar livre.
FRACAO_DO_CORPO = 0.5

# Onde ficam os .tri (o mesmo diretório do awpy 2.0.2: awpy.data.TRIS_DIR) e o registro dos sha256.
TRIS_DIR = Path.home() / ".awpy" / "tris"
REGISTRO_DAS_MALHAS = Path(__file__).resolve().parent.parent / "visao_malhas.json"

# Tamanho da célula da grade do plano (unidades). Só muda o tempo da consulta, nunca a resposta:
# cada triângulo entra em toda célula que a caixa dele toca, e o segmento percorre todas as células
# por onde passa (Amanatides e Woo).
CELULA = 128.0
_EPS = 1e-6            # as mesmas tolerâncias do awpy 2.0.2 (VisibilityChecker._ray_triangle_intersection)


class MalhaAusente(FileNotFoundError):
    """A malha do mapa não está em TRIS_DIR (rode `py -3.12 -m scripts.visao_malhas`)."""


def le_tri(caminho: Path) -> np.ndarray:
    """Triângulos de um .tri do awpy 2.0.2: 9 float32 por triângulo (p1, p2, p3). Devolve (n, 3, 3)."""
    dados = np.fromfile(caminho, dtype="<f4")
    if dados.size % 9:
        raise ValueError(f"{caminho}: tamanho não é múltiplo de 9 floats")
    return dados.reshape(-1, 3, 3)


def sha256(caminho: Path) -> str:
    h = hashlib.sha256()
    with open(caminho, "rb") as f:
        for bloco in iter(lambda: f.read(1 << 20), b""):
            h.update(bloco)
    return h.hexdigest()


def registro() -> dict:
    return json.loads(REGISTRO_DAS_MALHAS.read_text(encoding="utf-8")) if REGISTRO_DAS_MALHAS.exists() else {}


class Malha:
    """A colisão de um mapa, com a grade do plano para achar os triângulos perto de um segmento."""

    def __init__(self, triangulos: np.ndarray, celula: float = CELULA):
        t = np.asarray(triangulos, dtype=np.float64).reshape(-1, 3, 3)
        self.n = int(t.shape[0])
        self.p1 = t[:, 0, :]
        self.e1 = t[:, 1, :] - t[:, 0, :]
        self.e2 = t[:, 2, :] - t[:, 0, :]
        self.zmin = t[:, :, 2].min(axis=1)
        self.zmax = t[:, :, 2].max(axis=1)
        self.celula = float(celula)
        if self.n == 0:
            self.x0 = self.y0 = 0.0
            self.nx = self.ny = 1
            self.inicio = np.zeros(2, dtype=np.int64)
            self.indices = np.zeros(0, dtype=np.int64)
            return
        xmin, xmax = t[:, :, 0].min(axis=1), t[:, :, 0].max(axis=1)
        ymin, ymax = t[:, :, 1].min(axis=1), t[:, :, 1].max(axis=1)
        self.x0, self.y0 = float(xmin.min()), float(ymin.min())
        self.nx = int((xmax.max() - self.x0) // self.celula) + 1
        self.ny = int((ymax.max() - self.y0) // self.celula) + 1
        i0 = ((xmin - self.x0) // self.celula).astype(np.int64)
        i1 = ((xmax - self.x0) // self.celula).astype(np.int64)
        j0 = ((ymin - self.y0) // self.celula).astype(np.int64)
        j1 = ((ymax - self.y0) // self.celula).astype(np.int64)
        # cada triângulo em toda célula da caixa dele (ordem estável: célula, depois o índice do triângulo)
        nxs, nys = i1 - i0 + 1, j1 - j0 + 1
        cont = nxs * nys
        tri = np.repeat(np.arange(self.n, dtype=np.int64), cont)
        desloc = np.arange(int(cont.sum()), dtype=np.int64) - np.repeat(np.cumsum(cont) - cont, cont)
        nx_rep = np.repeat(nxs, cont)
        ci = np.repeat(i0, cont) + desloc % nx_rep
        cj = np.repeat(j0, cont) + desloc // nx_rep
        cel = cj * self.nx + ci
        ordem = np.lexsort((tri, cel))
        self.indices = tri[ordem]
        self.inicio = np.searchsorted(cel[ordem], np.arange(self.nx * self.ny + 1), side="left").astype(np.int64)

    def _celulas(self, ax: float, ay: float, bx: float, by: float) -> list[int]:
        """As células da grade por onde o segmento passa no plano (Amanatides e Woo)."""
        c = self.celula
        fx0, fy0 = (ax - self.x0) / c, (ay - self.y0) / c
        fx1, fy1 = (bx - self.x0) / c, (by - self.y0) / c
        i, j = int(math.floor(fx0)), int(math.floor(fy0))
        i1, j1 = int(math.floor(fx1)), int(math.floor(fy1))
        dx, dy = fx1 - fx0, fy1 - fy0
        passo_i = 1 if dx > 0 else -1
        passo_j = 1 if dy > 0 else -1
        t_max_x = ((i + (passo_i > 0)) - fx0) / dx if dx != 0 else math.inf
        t_max_y = ((j + (passo_j > 0)) - fy0) / dy if dy != 0 else math.inf
        t_delta_x = abs(1.0 / dx) if dx != 0 else math.inf
        t_delta_y = abs(1.0 / dy) if dy != 0 else math.inf
        out = []
        n_max = abs(i1 - i) + abs(j1 - j) + 2
        for _ in range(n_max):
            if 0 <= i < self.nx and 0 <= j < self.ny:
                out.append(j * self.nx + i)
            if i == i1 and j == j1:
                break
            # no canto exato, as duas vizinhas entram (conservador: nunca perde um triângulo)
            if t_max_x < t_max_y:
                i += passo_i
                t_max_x += t_delta_x
            elif t_max_y < t_max_x:
                j += passo_j
                t_max_y += t_delta_y
            else:
                if 0 <= i + passo_i < self.nx and 0 <= j < self.ny:
                    out.append(j * self.nx + i + passo_i)
                if 0 <= i < self.nx and 0 <= j + passo_j < self.ny:
                    out.append((j + passo_j) * self.nx + i)
                i += passo_i
                j += passo_j
                t_max_x += t_delta_x
                t_max_y += t_delta_y
        return out

    def linha_livre(self, a, b) -> bool:
        """O segmento de `a` a `b` (x, y, z) não atravessa nenhum triângulo? O mesmo teste do awpy 2.0.2
        (`VisibilityChecker.is_visible`): direção normalizada, acerto com 1e-6 < t <= comprimento."""
        ax, ay, az = float(a[0]), float(a[1]), float(a[2])
        bx, by, bz = float(b[0]), float(b[1]), float(b[2])
        d = np.array([bx - ax, by - ay, bz - az])
        dist = float(np.sqrt(d @ d))
        if dist < _EPS or self.n == 0:
            return True
        d = d / dist
        cels = self._celulas(ax, ay, bx, by)
        if not cels:
            return True
        cand = np.concatenate([self.indices[self.inicio[c]:self.inicio[c + 1]] for c in cels])
        if cand.size == 0:
            return True
        zlo, zhi = min(az, bz), max(az, bz)
        cand = cand[(self.zmax[cand] >= zlo - _EPS) & (self.zmin[cand] <= zhi + _EPS)]
        if cand.size == 0:
            return True
        e1, e2, p1 = self.e1[cand], self.e2[cand], self.p1[cand]
        dx, dy, dz = d
        # h = d x e2, a = e1 . h (produto vetorial por componente: o mesmo número de np.cross, mais rápido)
        hx = dy * e2[:, 2] - dz * e2[:, 1]
        hy = dz * e2[:, 0] - dx * e2[:, 2]
        hz = dx * e2[:, 1] - dy * e2[:, 0]
        a_ = e1[:, 0] * hx + e1[:, 1] * hy + e1[:, 2] * hz
        ok = np.abs(a_) >= _EPS
        if not ok.any():
            return True
        f = np.zeros_like(a_)
        f[ok] = 1.0 / a_[ok]
        sx, sy, sz = ax - p1[:, 0], ay - p1[:, 1], az - p1[:, 2]
        u = f * (sx * hx + sy * hy + sz * hz)
        # q = s x e1
        qx = sy * e1[:, 2] - sz * e1[:, 1]
        qy = sz * e1[:, 0] - sx * e1[:, 2]
        qz = sx * e1[:, 1] - sy * e1[:, 0]
        v = f * (qx * dx + qy * dy + qz * dz)
        t = f * (e2[:, 0] * qx + e2[:, 1] * qy + e2[:, 2] * qz)
        acerto = ok & (u >= 0.0) & (u <= 1.0) & (v >= 0.0) & (u + v <= 1.0) & (t > _EPS) & (t <= dist)
        return not bool(acerto.any())


_MALHAS: dict[str, Malha] = {}


def carrega_malha(mapa: str, tris_dir: Path | None = None, confere: bool = True) -> Malha:
    """A malha do mapa, lida do .tri e conferida pelo sha256 gravado em `visao_malhas.json`. Guardada em
    memória no processo (a mesma partida e o material leem a mesma malha muitas vezes)."""
    chave = f"{tris_dir or TRIS_DIR}|{mapa}"
    if chave in _MALHAS:
        return _MALHAS[chave]
    caminho = (tris_dir or TRIS_DIR) / f"{mapa}.tri"
    if not caminho.exists():
        raise MalhaAusente(f"sem a malha de {mapa} em {caminho}: rode `py -3.12 -m scripts.visao_malhas`")
    if confere:
        esperado = (registro().get("mapas") or {}).get(mapa, {}).get("sha256_tri")
        if esperado is None or sha256(caminho) != esperado:
            raise ValueError(f"{caminho}: sha256 não confere com {REGISTRO_DAS_MALHAS.name}")
    m = Malha(le_tri(caminho))
    _MALHAS[chave] = m
    return m


def malha_disponivel(mapa: str, tris_dir: Path | None = None) -> bool:
    return ((tris_dir or TRIS_DIR) / f"{mapa}.tri").exists()


# --- Quem vê quem, numa partida ------------------------------------------------------------------

def angulo_horizontal(yaw: float, de, para) -> float:
    """Ângulo (0 a 180) entre o olhar horizontal `yaw` e a direção de `de` até `para` no plano."""
    alvo = math.degrees(math.atan2(float(para[1]) - float(de[1]), float(para[0]) - float(de[0])))
    dif = abs(float(yaw) - alvo) % 360.0
    return 360.0 - dif if dif > 180.0 else dif


def _olhos(x: float, y: float, z: float, agachado: bool) -> tuple[float, float, float]:
    return (x, y, z + (EYE_HEIGHT_CROUCHED if agachado else EYE_HEIGHT_STANDING))


def _segmento_cruza_esfera(a, b, c, raio: float) -> bool:
    """O segmento de a a b passa a menos de `raio` do centro c?"""
    ab = np.array([b[0] - a[0], b[1] - a[1], b[2] - a[2]], dtype=float)
    ac = np.array([c[0] - a[0], c[1] - a[1], c[2] - a[2]], dtype=float)
    n2 = float(ab @ ab)
    s = 0.0 if n2 == 0 else min(1.0, max(0.0, float(ac @ ab) / n2))
    p = ac - s * ab
    return float(p @ p) < raio * raio


class Visao:
    """As perguntas de visão de uma partida: onde cada jogador está e para onde olha em cada tick, e se
    um vê o outro. `ticks` precisa de round_num, tick, steamid, X, Y, Z, yaw e (opcional) ducking;
    `malha` None = mapa sem paredes (os testes sintéticos montam a própria malha); `smokes` são
    (round, tick de início, tick de fim, X, Y, Z); `cegueira` é {(round, steamid): [(tick de início, tick
    de fim)]} das flashes efetivas."""

    def __init__(self, ticks: pl.DataFrame, malha: Malha | None, smokes: list[tuple] | None = None,
                 meio_fov: float = MEIO_FOV_GRAUS, amostra: int = AMOSTRA_VISAO_TICKS, cegueira: dict | None = None):
        self.malha = malha
        self.cegueira = cegueira or {}
        self.meio_fov = float(meio_fov)
        self.amostra = int(amostra)
        cols = ["round_num", "tick", "steamid", "X", "Y", "Z", "yaw"]
        t = ticks.select(cols + (["ducking"] if "ducking" in ticks.columns else [])).drop_nulls(["X", "Y", "Z"])
        t = t.sort(["round_num", "steamid", "tick"], maintain_order=True)
        self._serie: dict = {}
        rn = t["round_num"].cast(pl.Int64).to_numpy()
        sid = t["steamid"].cast(pl.UInt64).to_numpy()
        tk = t["tick"].cast(pl.Int64).to_numpy()
        x, y, z = (t[c].cast(pl.Float64).to_numpy() for c in ("X", "Y", "Z"))
        yaw = t["yaw"].cast(pl.Float64).fill_null(0.0).to_numpy()
        duck = (t["ducking"].fill_null(False).to_numpy() if "ducking" in t.columns
                else np.zeros(t.height, dtype=bool))
        if t.height:
            quebra = np.flatnonzero((np.diff(rn) != 0) | (np.diff(sid.astype(np.int64)) != 0)) + 1
            limites = np.concatenate([[0], quebra, [t.height]])
            for a, b in zip(limites[:-1], limites[1:]):
                self._serie[(int(rn[a]), int(sid[a]))] = (tk[a:b], x[a:b], y[a:b], z[a:b], yaw[a:b], duck[a:b])
        self.smokes: dict = {}
        for s in smokes or []:
            self.smokes.setdefault(int(s[0]), []).append((int(s[1]), int(s[2]), (float(s[3]), float(s[4]), float(s[5]))))
        self._cache: dict = {}

    def estado(self, rn: int, sid: int, tick: int):
        """(x, y, z, yaw, agachado) no tick mais próximo ANTES ou NO instante; None sem dado."""
        s = self._serie.get((int(rn), int(sid)))
        if s is None:
            return None
        i = int(np.searchsorted(s[0], int(tick), side="right")) - 1
        if i < 0:
            return None
        return float(s[1][i]), float(s[2][i]), float(s[3][i]), float(s[4][i]), bool(s[5][i])

    def posicao(self, rn: int, sid: int, tick: int):
        e = self.estado(rn, sid, tick)
        return None if e is None else {"X": e[0], "Y": e[1], "Z": e[2]}

    def amostras(self, t0: int, t1: int) -> list[int]:
        """Os ticks conferidos de t0 a t1 (os dois inclusive): de `amostra` em `amostra`, e o t1."""
        if t1 < t0:
            return []
        out = list(range(int(t0), int(t1) + 1, self.amostra))
        if out[-1] != int(t1):
            out.append(int(t1))
        return out

    def linha_livre(self, rn: int, tick: int, a, b) -> bool:
        """Sem parede do mapa e sem smoke ativa entre a e b."""
        for ini, fim, centro in self.smokes.get(int(rn), []):
            if ini <= tick <= fim and _segmento_cruza_esfera(a, b, centro, RAIO_SMOKE_UNIDADES):
                return False
        return self.malha is None or self.malha.linha_livre(a, b)

    def linha_de_visao(self, rn: int, tick: int, obs: int, alvo: int, pos_obs=None, pos_alvo=None) -> bool:
        """Linha de visão dos olhos de `obs` até a cabeça OU o meio do corpo de `alvo` (sem olhar o campo de
        visão). `pos_obs` / `pos_alvo` trocam a posição (x, y, z, agachado) do tick: é o que responde "e se
        o outro tivesse ficado parado?" no recuo do bait."""
        eo = pos_obs or self.estado(rn, obs, tick)
        ea = pos_alvo or self.estado(rn, alvo, tick)
        if eo is None or ea is None:
            return False
        olho = _olhos(eo[0], eo[1], eo[2], eo[-1])
        altura = EYE_HEIGHT_CROUCHED if ea[-1] else EYE_HEIGHT_STANDING
        for h in (altura, altura * FRACAO_DO_CORPO):
            if self.linha_livre(rn, tick, olho, (ea[0], ea[1], ea[2] + h)):
                return True
        return False

    def no_campo_de_visao(self, rn: int, tick: int, obs: int, alvo: int) -> bool:
        eo, ea = self.estado(rn, obs, tick), self.estado(rn, alvo, tick)
        if eo is None or ea is None:
            return False
        return angulo_horizontal(eo[3], eo, ea) < self.meio_fov

    def cego(self, rn: int, sid: int, tick: int) -> bool:
        return any(a <= tick <= b for a, b in self.cegueira.get((int(rn), int(sid)), ()))

    def visivel(self, rn: int, tick: int, obs: int, alvo: int) -> bool:
        """`alvo` visível para `obs` no tick: `obs` não está cego, `alvo` está dentro do campo de visão E com
        linha de visão livre."""
        chave = (int(rn), int(tick), int(obs), int(alvo))
        r = self._cache.get(chave)
        if r is None:
            r = (not self.cego(rn, obs, tick) and self.no_campo_de_visao(rn, tick, obs, alvo)
                 and self.linha_de_visao(rn, tick, obs, alvo))
            self._cache[chave] = r
        return r


def cegueira_efetiva(blinds: pl.DataFrame | None, tickrate: int) -> dict:
    """{(round, steamid): [(início, fim)]} das flashes acima de `EFFECTIVE_BLIND_SECONDS` (metrics.grenades)."""
    from metrics.grenades import EFFECTIVE_BLIND_SECONDS
    out: dict = {}
    if blinds is None or blinds.height == 0:
        return out
    for r in blinds.sort(["round_num", "tick"], maintain_order=True).iter_rows(named=True):
        if r["user_steamid"] is None or (r["blind_duration"] or 0) < EFFECTIVE_BLIND_SECONDS:
            continue
        out.setdefault((int(r["round_num"]), int(r["user_steamid"])), []).append(
            (int(r["tick"]), int(r["tick"]) + float(r["blind_duration"]) * tickrate))
    return out


def visao_da_partida(ticks: pl.DataFrame, mapa: str, smokes_df: pl.DataFrame | None,
                     blinds: pl.DataFrame | None = None, tickrate: int = 64, tris_dir: Path | None = None) -> Visao:
    """A visão de uma partida do interim: a malha do mapa, as smokes (início e fim pelo interim) e a cegueira."""
    from metrics.constantes import DURACAO_SMOKE_S
    smokes = []
    if smokes_df is not None and smokes_df.height:
        # o interim não grava o fim da smoke (end_tick vazio em todas as partidas): o fim é o início mais a
        # duração da smoke no jogo (DURACAO_SMOKE_S, a mesma do replay e da prancheta)
        dur = int(round(DURACAO_SMOKE_S * tickrate))
        for rn, ini, fim, x, y, z in smokes_df.select("round_num", "start_tick", "end_tick", "X", "Y", "Z").iter_rows():
            if None in (rn, ini, x, y, z):
                continue
            smokes.append((rn, ini, int(fim) if fim is not None else int(ini) + dur, x, y, z))
    return Visao(ticks, carrega_malha(mapa, tris_dir), smokes, cegueira=cegueira_efetiva(blinds, tickrate))


__all__ = ["MEIO_FOV_GRAUS", "AMOSTRA_VISAO_TICKS", "Malha", "Visao", "MalhaAusente", "carrega_malha",
           "visao_da_partida", "angulo_horizontal", "le_tri"]
