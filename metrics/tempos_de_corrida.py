"""O tempo que jogadores de verdade levaram para ir de um ponto (ou de uma área) a outro, medido no corpus (C3, decisão 64).

A aba Comandos da prancheta mostra "chega entre 1:14 e 1:11 (tempo real: 41 casos em 9 partidas)" no lugar de uma estimativa em linha reta.
Aqui só há a conta, pura e sem arquivo: o leitor das partidas fica em `scripts/build_tempos.py`.

Um RASTRO é um jogador vivo em um round valendo (do fim do freeze ao fim do round), uma amostra a cada 8 ticks:
`{"partida", "tick", "x", "y", "z", "walk", "duck", "tr", "passo"}` (arrays do numpy; `walk` e `duck` valem 0 ou 1 por tick).
Um NÓ é um alvo possível: `{"chave", "x", "y", "membros": [(x, y), ...], "andar"}` (ponto do Pedro, já agrupado como o leitor agrupa, ou área da demo).

A regra, em uma frase (o teste a recalcula por outro caminho): cada tick recebe o nó mais perto, se estiver a no máximo RAIO dele (o nó com mais de um membro
conta pelo membro mais perto; um nó de um andar só vale para ticks daquele andar); uma VISITA são ticks seguidos do mesmo nó; a viagem de A a B vai do tick de
MAIOR APROXIMAÇÃO de A, na última visita a A antes de B, ao tick de maior aproximação da primeira visita a B; descarta o que parou mais de 1 s, tem buraco
no rastro (morte, troca de round), passou de 25 s ou andou mais de 1,8 vezes a reta (quem volta a A conta da última saída). Só "correndo" entra na tabela: no máximo 10% dos ticks
andando (shift) e nenhum agachado.
"""
from __future__ import annotations

from collections import defaultdict

import numpy as np

RAIO_PONTOS = 200.0     # u em volta de um ponto do Pedro (um ponto é um canto; ±1 s de ruído em cada ponta)
RAIO_AREAS = 250.0      # u em volta da âncora de uma área da demo
RAIO_ORIGEM = 150.0     # u: a peça "está" num ponto se estiver a no máximo isto dele (a aba usa para achar o ponto de partida)
MIN_CASOS = 20
MIN_PARTIDAS = 3
MIN_PARES_DO_FATOR = 15
RETA_MIN_DO_FATOR = 300.0   # pares mais curtos que isto não entram no fator: o ruído do raio pesa mais que o desvio
LIMITE_S = 25.0
PARADO_U_S = 40.0
PARADA_MAX_S = 1.0
DESVIO_MAX = 1.8
ANDANDO_MAX = 0.10


def _parada_ou_buraco(r: dict, i: int, j: int) -> tuple[bool, float]:
    """(a viagem tem buraco ou parada longa, caminho andado) entre os índices i e j do rastro."""
    tk, passo, tr = r["tick"][i:j + 1], r["passo"], r["tr"]
    if np.any(np.diff(tk) > 4 * passo):
        return True, 0.0
    p = np.hypot(np.diff(r["x"][i:j + 1]), np.diff(r["y"][i:j + 1]))
    dt = np.maximum(np.diff(tk) / tr, passo / tr)
    return bool(np.sum((p / dt) < PARADO_U_S) * passo / tr > PARADA_MAX_S), float(p.sum())


def viagens(rastros: list[dict], nos: list[dict], raio: float, corte_z: float | None = None) -> dict[tuple[int, int], list[tuple[str, float, float, float]]]:
    """{(i, j): [(partida, duração em s, fração andando, agachado 0/1), ...]} para todo par de nós, em todos os rastros."""
    saida: dict[tuple[int, int], list] = defaultdict(list)
    n = len(nos)
    for r in rastros:
        d = np.full((len(r["x"]), n), np.inf)
        for k, no in enumerate(nos):
            for (mx, my) in no["membros"]:
                d[:, k] = np.minimum(d[:, k], np.hypot(r["x"] - mx, r["y"] - my))
            if corte_z is not None and no.get("andar") in ("cima", "baixo"):
                baixo = r["z"] < corte_z
                d[:, k] = np.where(baixo == (no["andar"] == "baixo"), d[:, k], np.inf)
        rotulo = np.where(d.min(1) <= raio, d.argmin(1), -1)
        visitas, i0 = [], 0                        # (nó, tick de maior aproximação)
        for i in range(1, len(rotulo) + 1):
            if i == len(rotulo) or rotulo[i] != rotulo[i0]:
                if rotulo[i0] >= 0:
                    visitas.append((int(rotulo[i0]), i0 + int(np.argmin(d[i0:i, rotulo[i0]]))))
                i0 = i
        for vi, (a, ia) in enumerate(visitas):
            vistos = {a}
            for b, ib in visitas[vi + 1:]:
                if b == a:
                    break                          # voltou a A no meio
                if b in vistos:
                    continue
                vistos.add(b)
                dur = (r["tick"][ib] - r["tick"][ia]) / r["tr"]
                if dur > LIMITE_S:
                    break
                ruim, andado = _parada_ou_buraco(r, ia, ib)
                reta = float(np.hypot(r["x"][ib] - r["x"][ia], r["y"][ib] - r["y"][ia]))
                if ruim or reta < 1 or andado > DESVIO_MAX * reta:
                    continue
                saida[(a, b)].append((r["partida"], dur, float(r["walk"][ia:ib + 1].mean()), float(r["duck"][ia:ib + 1].max())))
    return saida


def so_correndo(casos: list[tuple]) -> list[tuple]:
    return [c for c in casos if c[2] <= ANDANDO_MAX and c[3] == 0]


def resumo(casos: list[tuple]) -> dict | None:
    """p25, mediana e p75 (em s, duas casas), casos e partidas; None abaixo do mínimo (20 casos em 3 partidas)."""
    c = so_correndo(casos)
    partidas = {x[0] for x in c}
    if len(c) < MIN_CASOS or len(partidas) < MIN_PARTIDAS:
        return None
    d = np.array([x[1] for x in c])
    return {"p25": round(float(np.percentile(d, 25)), 2), "mediana": round(float(np.median(d)), 2), "p75": round(float(np.percentile(d, 75)), 2),
            "casos": len(c), "partidas": len(partidas)}


def pares(rastros: list[dict], nos: list[dict], raio: float, corte_z: float | None = None) -> dict[tuple[int, int], dict]:
    return {k: r for k, v in viagens(rastros, nos, raio, corte_z).items() if (r := resumo(v)) is not None}


def fator_do_mapa(tabelas: list[tuple[str, dict[tuple[int, int], dict], list[dict]]], velocidade: float) -> dict:
    """O fator de desvio do mapa: a mediana de (tempo real ÷ tempo em linha reta) nos pares com amostra, sem troca de andar e com reta de pelo menos 300 u.

    `tabelas` = [(fonte, pares, nós)] em ordem de preferência; vale a primeira com pelo menos MIN_PARES_DO_FATOR pares. Devolve também quanto o tempo em
    linha reta e o corrigido erram em relação à mediana real (mediana do erro absoluto, em s), o segundo também com cada par deixado de fora ("validação")."""
    for fonte, pr, nos in tabelas:
        linhas = []
        for (a, b), r in pr.items():
            na, nb = nos[a], nos[b]
            if na.get("andar") in ("cima", "baixo") and nb.get("andar") in ("cima", "baixo") and na["andar"] != nb["andar"]:
                continue                                            # troca de andar: a reta não diz nada
            reta = float(np.hypot(na["x"] - nb["x"], na["y"] - nb["y"]))
            if reta >= RETA_MIN_DO_FATOR:
                linhas.append((reta / velocidade, r["mediana"]))
        if len(linhas) < MIN_PARES_DO_FATOR:
            continue
        reta_s = np.array([x[0] for x in linhas]); real = np.array([x[1] for x in linhas]); razao = real / reta_s
        f = float(np.median(razao))
        fora = np.array([float(np.median(np.delete(razao, i))) for i in range(len(razao))])
        return {"valor": round(f, 3), "fonte": fonte, "pares": len(linhas),
                "erro_reta_s": round(float(np.median(np.abs(real - reta_s))), 2), "erro_corrigido_s": round(float(np.median(np.abs(real - f * reta_s))), 2),
                "erro_validado_s": round(float(np.median(np.abs(real - fora * reta_s))), 2)}
    return {"valor": None, "fonte": None, "pares": 0}
