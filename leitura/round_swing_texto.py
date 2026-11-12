"""Textos do Round swing na página da partida (RS2): a coluna da tabela de jogadores e a linha do Perfil.

Tudo que sai daqui é TEXTO pronto (decisão 18): o número já escrito ("+5,8", "−2,1"), o texto para o leitor de tela e as frases. A página só desenha; nenhum número
entra no bloco como número, então a impressão dos números não muda.

Os números vêm da RS1: `round_swing` de cada jogador no `web_payload.json` (a partida) e `data/player_profiles/round_swing.json` (o corpus). Implementação própria da
metodologia do Rating 3.0 da HLTV: o número pode diferir do deles, e o site nunca o apresenta como o da HLTV.

Regras do Pedro (RS2): menos de 30 rounds no corpus -> sem número, com o motivo ("poucos rounds para um número confiável (24 de 30)"); de 30 a 99 -> número com "±";
100 ou mais -> número com "±" e a marca "estável". Sinal sempre escrito, com o menos tipográfico (U+2212); o leitor de tela lê "mais"/"menos" por extenso.
"""
from __future__ import annotations

import json
from pathlib import Path

from metrics.round_swing_jogador import MIN_ROUNDS_PARA_MOSTRAR, ROUNDS_ESTAVEL

RAIZ = Path(__file__).resolve().parent.parent
ARQUIVO_DO_CORPUS = RAIZ / "data" / "player_profiles" / "round_swing.json"

MENOS = "−"          # o sinal de menos tipográfico

TEXTOS = {
    "coluna": "Round swing (p.p.)",
    "selo": "implementação própria",
    "frase": "Round swing: quanto o jogador mexeu, por round, na chance de o time vencer o round; implementação própria, o número pode diferir do da HLTV.",
    "p_p": "p.p. = pontos percentuais.",
    "aviso_partida": "Numa partida, o round swing varia cerca de ±4 p.p. só por acaso: ele conta o que aconteceu, não quem é melhor.",
    "titulo_do_perfil": "Round swing no corpus",
    "unidade": "p.p. por round",
    "estavel": "estável",
    "poucos": "poucos rounds para um número confiável ({n} de {minimo})",
}


def _decimal(x: float) -> str:
    return f"{abs(x):.1f}".replace(".", ",")


def numero(x: float) -> str:
    """"+5,8", "−2,1" ou "0,0": o sinal sempre escrito (menos tipográfico). O que arredonda para 0,0 não tem sinal."""
    t = _decimal(x)
    if t == "0,0":
        return t
    return ("+" if x > 0 else MENOS) + t


def leitor(x: float, erro: float | None = None) -> str:
    """O número por extenso para o leitor de tela: "mais 5,8 pontos percentuais por round, mais ou menos 1,2"."""
    t = _decimal(x)
    base = "zero pontos percentuais por round" if t == "0,0" else f"{'mais' if x > 0 else 'menos'} {t} pontos percentuais por round"
    return base if erro is None else f"{base}, mais ou menos {_decimal(erro)}"


def da_partida(bloco: dict | None) -> dict | None:
    """A célula da tabela da partida: {"t": "+5,8", "l": "mais 5,8 pontos percentuais por round"}; None sem o campo."""
    if not bloco or bloco.get("pp_por_round") is None:
        return None
    return {"t": numero(bloco["pp_por_round"]), "l": leitor(bloco["pp_por_round"])}


def estado(rounds: int) -> str:
    return "poucos" if rounds < MIN_ROUNDS_PARA_MOSTRAR else "estavel" if rounds >= ROUNDS_ESTAVEL else "intermediario"


def do_corpus(b: dict | None) -> dict | None:
    """A linha do Perfil: {"estado", "numero" ("+5,8 ± 1,2"), "contagem" ("21 partidas, 447 rounds"), "motivo" (só em "poucos"), "l" (leitor)}."""
    if not b:
        return None
    n, partidas = int(b["rounds"]), int(b.get("partidas") or 0)
    est = estado(n)
    contagem = f"{partidas} {'partida' if partidas == 1 else 'partidas'}, {n} rounds"
    if est == "poucos":
        motivo = TEXTOS["poucos"].format(n=n, minimo=MIN_ROUNDS_PARA_MOSTRAR)
        return {"estado": est, "numero": "", "contagem": contagem, "motivo": motivo, "l": f"{TEXTOS['titulo_do_perfil']}: {motivo}"}
    erro = b.get("erro_padrao_pp")
    txt = numero(b["pp_por_round"]) + ("" if erro is None else f" ± {_decimal(erro)}")
    leit = f"{TEXTOS['titulo_do_perfil']}: {leitor(b['pp_por_round'], erro)}; {contagem}" + ("; estável" if est == "estavel" else "")
    return {"estado": est, "numero": txt, "contagem": contagem, "motivo": "", "l": leit}


def bloco(payload: dict, corpus: dict | None = None) -> dict:
    """O bloco da página: os textos e, por NOME de jogador da partida, a célula da tabela e a linha do Perfil."""
    if corpus is None:
        corpus = json.loads(ARQUIVO_DO_CORPUS.read_text(encoding="utf-8"))["jogadores"] if ARQUIVO_DO_CORPUS.exists() else {}
    partida, perfil = {}, {}
    for p in payload.get("players") or []:
        c = da_partida(p.get("round_swing"))
        if c:
            partida[p["name"]] = c
        l = do_corpus(corpus.get(str(p["steamid"])))
        if l:
            perfil[p["name"]] = l
    return {"textos": TEXTOS, "partida": partida, "corpus": perfil}
