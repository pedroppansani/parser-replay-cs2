"""O grafo de passagens montado das trajetórias do corpus (PC0, decisão 70).

Uma CÉLULA é um quadrado de `CELULA_U` u por uma faixa de `FAIXA_Z_U` u de altura que alguém pisou (em pelo menos `MIN_VISITAS` rastros). Uma LIGAÇÃO dirigida A -> B existe quando um jogador de verdade passou
de A para B em amostras seguidas (0,125 s) em pelo menos `MIN_LIGACOES` rastros: uma queda só existe no sentido em que foi feita, e nenhuma parede é atravessada (ninguém atravessa). O centro de
cada célula é a média das amostras que caíram nela."""
from __future__ import annotations

from collections import defaultdict

import numpy as np

CELULA_U = 64.0         # decisão do Pedro (PC0): 47 KB por mapa e erro de 9,8% na Mirage
FAIXA_Z_U = 48.0        # a altura da faixa: separa um andar do outro sem partir uma rampa
MIN_VISITAS = 3
MIN_LIGACOES = 2
SALTO_MAX_U = 160.0     # o máximo que um jogador anda entre duas amostras seguidas (250 u/s x 0,125 s = 31 u; folga para queda e erro)


def celulas_e_ligacoes(rastros: list[dict]) -> tuple[list[tuple], dict[tuple, tuple[float, float, float]], set[tuple]]:
    """(células em ordem, centro de cada uma, ligações (a, b)) dos rastros (`scripts.build_tempos.rastros`)."""
    visitas: dict[tuple, set] = defaultdict(set)
    soma: dict[tuple, list] = defaultdict(lambda: [0.0, 0.0, 0.0, 0])
    lig: dict[tuple, set] = defaultdict(set)
    for ri, r in enumerate(rastros):
        x, y, z = r["x"], r["y"], r["z"]
        gx, gy, gz = np.floor(x / CELULA_U).astype(int), np.floor(y / CELULA_U).astype(int), np.floor(z / FAIXA_Z_U).astype(int)
        chave = list(zip(gx.tolist(), gy.tolist(), gz.tolist()))
        ok = (np.diff(r["tick"]) <= 2 * r["passo"]) & (np.hypot(np.diff(x), np.diff(y)) < SALTO_MAX_U) & (np.abs(np.diff(z)) < 400)
        for k, c in enumerate(chave):
            visitas[c].add(ri)
            s = soma[c]
            s[0] += x[k]
            s[1] += y[k]
            s[2] += z[k]
            s[3] += 1
            if k + 1 < len(chave) and ok[k] and chave[k + 1] != c:
                lig[(c, chave[k + 1])].add(ri)
    celulas = sorted(c for c, v in visitas.items() if len(v) >= MIN_VISITAS)
    centro = {c: (soma[c][0] / soma[c][3], soma[c][1] / soma[c][3], soma[c][2] / soma[c][3]) for c in celulas}
    ligacoes = {(a, b) for (a, b), rs in lig.items() if len(rs) >= MIN_LIGACOES and a in centro and b in centro}
    return celulas, centro, ligacoes


def z_dos_nos(nos: list, mapa: str, rastros: list[dict] | None = None) -> dict:
    """O z de cada nó da C3 (`[chave, x, y, andar]`): a mediana do z dos rastros a até 120 u dele (e, em mapa de dois andares, só do andar do nó)."""
    from metrics.map_areas import floor_split_z
    from scripts.build_tempos import rastros as le_rastros
    rs = rastros if rastros is not None else le_rastros(mapa)
    x = np.concatenate([r["x"] for r in rs])
    y = np.concatenate([r["y"] for r in rs])
    z = np.concatenate([r["z"] for r in rs])
    corte = floor_split_z(mapa)
    saida = {}
    for chave, nx_, ny_, andar in nos:
        m = np.hypot(x - nx_, y - ny_) < 120
        if corte is not None and andar in ("cima", "baixo"):
            m &= (z >= corte) if andar == "cima" else (z < corte)
        saida[chave] = float(np.median(z[m])) if m.sum() >= 5 else None
    return saida
