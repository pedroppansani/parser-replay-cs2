"""O round inteiro do replay como dado para a prancheta (fase 9).

O replay grava 4 amostras por segundo de cada jogador (x, y, direção, andar,
vivo). A prancheta recebe o round pela URL, então o caminho de cada jogador é
simplificado com Douglas-Peucker: ficam os pontos que mudam a forma do caminho
mais do que a tolerância, e o horário de cada ponto que ficou é o da amostra.
Entre dois pontos, a prancheta interpola linear -- o mesmo que ela já faz entre
pontos-chave (formato 3).

A tolerância escolhida e o erro que ela causa estão medidos em
pesquisa/round_no_hash.py (notas/investigacoes/2026-10-05-round-no-hash.md).
"""
from __future__ import annotations

import math

# Tolerâncias medidas (unidades do jogo); a escolhida fica em TOLERANCIA_U.
TOLERANCIAS_U = (0, 2, 4, 8, 16, 32)
# A escolhida: a maior medida cujo erro máximo (= a tolerância, com a distância
# sincronizada no tempo) fica abaixo do que o próprio replay já não vê entre duas
# amostras -- um jogador correndo de rifle anda 210,6 u/s (VELOCIDADE_U_S, medida
# no corpus) / 4 amostras por segundo = 52,6 u. Com 32 u: maior round do corpus
# com 11,5 KB no hash (limite 150 KB) e 46 pontos por jogador na mediana (contra
# 288 sem simplificar). Tabela em notas/investigacoes/2026-10-05-round-no-hash.md.
TOLERANCIA_U = 32


def douglas_peucker(pontos: list[tuple[float, float, float]], tol: float) -> list[int]:
    """Índices dos pontos (t, x, y) que ficam -- o primeiro e o último sempre.

    Douglas-Peucker com a distância SINCRONIZADA no tempo: o desvio de um ponto
    é a distância até onde o trecho simplificado estaria NO MESMO HORÁRIO
    (interpolação linear no tempo entre os extremos), não até a reta. Assim o
    erro de posição no horário fica limitado pela tolerância; a versão só
    espacial deixaria cair o vaivém (ir e voltar na mesma reta) e o tempo
    parado. Iterativo, para não estourar a pilha num round longo."""
    n = len(pontos)
    if n <= 2 or tol <= 0:
        return list(range(n))
    fica = [False] * n
    fica[0] = fica[-1] = True
    pilha = [(0, n - 1)]
    while pilha:
        a, b = pilha.pop()
        ta, ax, ay = pontos[a]
        tb, bx, by = pontos[b]
        pior, ip = -1.0, -1
        for i in range(a + 1, b):
            ti, px, py = pontos[i]
            f = (ti - ta) / (tb - ta) if tb > ta else 0.0
            d = math.hypot(px - (ax + (bx - ax) * f), py - (ay + (by - ay) * f))
            if d > pior:
                pior, ip = d, i
        if ip >= 0 and pior > tol:
            fica[ip] = True
            pilha.append((a, ip))
            pilha.append((ip, b))
    return [i for i in range(n) if fica[i]]


def caminho_do_jogador(p: dict, tol: float, fixos: tuple[int, ...] = ()) -> tuple[list[list], int | None]:
    """Pontos [quadro, x, y, direção, andar] do trecho vivo e o quadro da morte
    (None se terminou vivo). Ficam sempre: o primeiro e o último quadro vivo, os
    dois lados de cada troca de andar (a prancheta não interpola entre andares)
    e os quadros `fixos` -- o instante de onde a prancheta veio, para que ali a
    posição e a direção sejam as gravadas, sem o erro da simplificação. Entre
    dois pontos que sempre ficam, Douglas-Peucker sincronizado no tempo."""
    vivos = [i for i, v in enumerate(p["alive"]) if v]
    if not vivos:
        return [], None
    ini, fim = vivos[0], vivos[-1]
    lv = p.get("lv") or [0] * len(p["x"])
    marcos = {ini, fim}
    for k in range(ini + 1, fim + 1):
        if lv[k] != lv[k - 1]:
            marcos.update((k - 1, k))
    marcos.update(q for q in fixos if ini <= q <= fim)
    marcos = sorted(marcos)
    ficam = set(marcos)
    for a, b in zip(marcos, marcos[1:]):
        trecho = list(range(a, b + 1))
        sel = douglas_peucker([(i, p["x"][i], p["y"][i]) for i in trecho], tol)
        ficam.update(trecho[s] for s in sel)
    pontos = [[i, p["x"][i], p["y"][i], p["d"][i], lv[i]] for i in sorted(ficam)]
    morte = fim + 1 if fim + 1 < len(p["alive"]) else None
    return pontos, morte


def posicao_no_caminho(pontos: list[list], quadro: float) -> tuple[float, float] | None:
    """(x, y) do caminho simplificado no quadro, ou None fora do trecho vivo."""
    if not pontos or quadro < pontos[0][0] or quadro > pontos[-1][0]:
        return None
    for a, b in zip(pontos, pontos[1:]):
        if a[0] <= quadro <= b[0]:
            f = (quadro - a[0]) / (b[0] - a[0]) if b[0] > a[0] else 0.0
            return a[1] + (b[1] - a[1]) * f, a[2] + (b[2] - a[2]) * f
    return pontos[-1][1], pontos[-1][2]


def payload_do_round(rep: dict, rd: dict, tol: float, partida: str, quadro: int | None = None) -> dict:
    """O round no formato que viaja na URL (quadros, não segundos). `quadro` é o
    instante de onde a prancheta veio (fica como ponto de todo jogador vivo).

    Granada: k, by, f (quadro do arremesso), o e d (começo e fim da trajetória),
    l (id do arremesso real), lo (posição da soltura gravada pelo export), v (voo
    em quadros: até o efeito ligado, para smoke e molotov; senão até o fim da
    trajetória) e e (duração do efeito ligado, em quadros, ou None)."""
    fixos = () if quadro is None else (quadro,)
    jogadores = []
    for p in rd["players"]:
        pontos, morte = caminho_do_jogador(p, tol, fixos)
        jogadores.append({"nome": p["name"], "lado": p["side"], "pontos": pontos, "morte": morte})
    efeitos = {}
    for z in rd.get("smokes", []) + rd.get("fires", []):
        if z.get("l"):
            efeitos.setdefault(z["l"]["id"], z)
    granadas = []
    for g in rd.get("nades", []):
        if not g.get("x"):
            continue
        lance = g.get("l") or {}
        z = efeitos.get(lance.get("id")) if g["k"] in ("smoke", "molotov") else None
        granadas.append({"k": g["k"], "by": g.get("by"), "f": g["f0"],
                         "o": [g["x"][0], g["y"][0]], "d": [g["x"][-1], g["y"][-1]],
                         "l": lance.get("id"), "lo": lance["o"][:2] if lance.get("o") else None,
                         "v": (z["f0"] - g["f0"]) if z else len(g["x"]) - 1,
                         "e": (z["f1"] - z["f0"]) if z else None})
    plant = next((e for e in rd.get("events", []) if e["type"] == "plant"), None)
    return {"partida": partida, "round": rd["round"], "hz": rep["sample_hz"], "jogadores": jogadores,
            "granadas": granadas,
            "bomba": {"f": plant["f"], "x": plant["x"], "y": plant["y"], "por": plant.get("player")} if plant else None}
