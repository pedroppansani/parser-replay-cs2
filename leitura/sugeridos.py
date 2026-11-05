"""Reescrever (R0): o índice pequeno dos rounds sugeridos de cada partida, para a página de escolha.

Os páginas das partidas têm de 2,4 a 5,2 MB; a escolha não pode baixar todas só para listar alguns rounds. Este módulo junta, do que
já foi calculado (nada novo é medido), os rounds que merecem ser reescritos e o MOTIVO de cada um:

- `decisivo`: o round decisivo do payload (`decisive_round`), com a frase do card ("Levou o Time A de 50% para 75%...");
- `momento`: os momentos do bloco "Por que perdeu" (`breakdown.json`) que têm jogador, no máximo `MAX_MOMENTOS`, um por round,
  na ordem de `PRIORIDADE_DO_MOMENTO` (a abertura perdida primeiro) e depois do round;
- `erro`: os erros do Perfil de tipo VALIDADO (`TIPOS_DE_ERRO_VALIDADOS`, decisão 46), no máximo `MAX_ERROS`, os de maior perda de
  chance de vitória (`dwpa`) primeiro. Tipo não validado nunca entra.

O instante (`tick`) e o relógio do round (`relogio`, o mesmo que o Replay mostra) vão junto, para o Reescrever abrir naquele instante.
"""
from __future__ import annotations

from metrics.erros import ROTULO_DO_NIVEL, TIPOS_DE_ERRO_VALIDADOS, TITULOS
from metrics.tactics import relogio as relogio_do_jogo

FORMATO_SUGERIDOS = 1
MAX_MOMENTOS = 3          # por partida: a escolha é uma lista curta, não o bloco inteiro (decisão do R0, 2026-11-04)
MAX_ERROS = 2
# o momento sem jogador (sem_plant, pos_plant) não tem quem selecionar; os outros, na ordem do bloco "Por que perdeu"
PRIORIDADE_DO_MOMENTO = {"abertura_perdida": 0, "morte_isolada": 1, "virada_numerica": 2}


def _relogio(tick: int, rd: dict, tickrate: int) -> str | None:
    """O relógio do round no tick (o do Replay): desce de 1:55 e, depois do plant, os 40 s da bomba."""
    fe = rd.get("freeze_end")
    if fe is None:
        return None

    def seg(x):
        return None if x is None else (int(x) - int(fe)) / tickrate
    return relogio_do_jogo(seg(tick), seg(rd.get("bomb_plant")), seg(rd.get("end")))


def sugeridos_da_partida(decisivo: dict | None, frase_decisiva: str | None, breakdown: list[dict], erros: list[dict],
                         rounds: dict[int, dict], tickrate: int) -> list[dict]:
    """A lista de sugeridos da partida. `rounds` = {round: {freeze_end, bomb_plant, end}} (rounds.parquet); `erros` = linhas de
    erros_do_jogador (todas; só as de tipo validado entram)."""
    saida: list[dict] = []
    if decisivo and decisivo.get("round") is not None:
        saida.append({"round": int(decisivo["round"]), "motivo": "decisivo", "texto": frase_decisiva or "", "jogador": None,
                      "tick": None, "relogio": None, "tipo": None})

    melhores: dict[int, tuple] = {}
    for b in breakdown:
        for m in b.get("moments", []):
            if m.get("who") is None or m.get("kind") not in PRIORIDADE_DO_MOMENTO:
                continue
            chave = (PRIORIDADE_DO_MOMENTO[m["kind"]], int(b["round"]), int(m["tick"]))
            if b["round"] not in melhores or chave < melhores[b["round"]][0]:
                melhores[b["round"]] = (chave, b["round"], m)
    for _, rn, m in sorted(melhores.values(), key=lambda x: x[0])[:MAX_MOMENTOS]:
        saida.append({"round": int(rn), "motivo": "momento", "texto": m.get("text") or "", "jogador": m["who"], "tick": int(m["tick"]),
                      "relogio": _relogio(m["tick"], rounds.get(rn, {}), tickrate), "tipo": m["kind"]})

    validos = [e for e in erros if e["tipo"] in TIPOS_DE_ERRO_VALIDADOS and e.get("tick") is not None]
    validos.sort(key=lambda e: (e["dwpa"] if e.get("dwpa") is not None else 0.0, int(e["round_num"]), int(e["tick"]), e["name"]))
    vistos = set()
    for e in validos:
        if len(vistos) >= MAX_ERROS:
            break
        if int(e["round_num"]) in vistos:
            continue
        vistos.add(int(e["round_num"]))
        nivel = ROTULO_DO_NIVEL.get(e.get("nivel") or "", "")
        saida.append({"round": int(e["round_num"]), "motivo": "erro", "jogador": e["name"], "tick": int(e["tick"]),
                      "relogio": e.get("relogio") or _relogio(e["tick"], rounds.get(int(e["round_num"]), {}), tickrate), "tipo": e["tipo"],
                      "texto": f"{TITULOS.get(e['tipo'], e['tipo'])}" + (f" · erro validado, {nivel}" if nivel else " · erro validado")})
    return saida
