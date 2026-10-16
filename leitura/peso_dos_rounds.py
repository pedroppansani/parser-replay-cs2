"""Textos da seção "Quanto cada round pesou" (aba Placar da página da partida).

A seção troca a curva da chance de vitória, que repetia o desenho de "A virada em dois atos" (a chance
depende quase só do placar), por barras: quanto CADA round mudou a chance de vitória do lado A (o mesmo
time de referência do gráfico de cima). A barra é `wp_a_depois - wp_a_antes` da curva que o payload já
publica (`metrics/win_probability.curva_da_partida`); nenhum número novo é calculado, e o round
decisivo é o que o payload já traz (`decisive_round`), nunca eleito de novo aqui.

Tudo que sai daqui é TEXTO pronto (decisão 18): o título, a abertura com dois rounds da própria
partida, a frase que liga a maior barra ao round decisivo, o rótulo de cada barra e as linhas dos três
cartões. Nenhum número entra como número no bloco, então a impressão dos números
(`scripts/design/impressao_numeros.py`) não muda. Quem desenha (o JS do template) lê a altura da barra
da curva do payload; daqui só vem como ela é escrita.
"""
from __future__ import annotations

import math

from metrics.formatting import format_pp
from metrics.win_probability import FATOR_MINIMO_DECISIVO, LIMIAR_EMPATE_WPA

TITULO = "Quanto cada round pesou"


def variacao(linha: dict) -> float:
    """A altura da barra: depois menos antes, na chance do lado A (positivo = a favor do A)."""
    return float(linha["wp_a_depois"]) - float(linha["wp_a_antes"])


# U+2060 (word joiner) dos dois lados do traço: "6–2" não quebra no meio da linha em 375 px.
_SEM_QUEBRA = chr(0x2060)


def _placar(a: int, b: int) -> str:
    return f"{a}{_SEM_QUEBRA}–{_SEM_QUEBRA}{b}"


def placar_antes_e_depois(linha: dict) -> tuple[str, str]:
    """("11–11", "12–11"): o placar (lado A primeiro) antes e depois do round, sem quebra no traço."""
    a, b = int(linha["score_a"]), int(linha["score_b"])
    antes = (a - 1, b) if linha["winner_team"] == "A" else (a, b - 1)
    return _placar(*antes), _placar(a, b)


def _pp_par(a: float, b: float) -> tuple[str, str]:
    """Dois valores (sem sinal) que a frase COMPARA: inteiros, ou com uma casa se o arredondamento os
    iguala (a regra de `metrics.formatting.format_pct_par`, em pontos percentuais)."""
    if round(a * 100) != round(b * 100):
        return format_pp(a).lstrip("+"), format_pp(b).lstrip("+")
    def uma_casa(x: float) -> str:
        return f"{x * 100:.1f}".replace(".", ",") + " pp"
    return uma_casa(a), uma_casa(b)


def _fator(x: float) -> str:
    return f"{x:g}".replace(".", ",")


def _abertura(curva: list[dict], nomes: dict[str, str]) -> str:
    base = (f"Cada barra é o quanto o round mudou a chance de vitória de {nomes['A']}: para cima, a favor "
            f"de {nomes['A']}; para baixo, a favor de {nomes['B']}. A chance depende do placar: com a "
            "partida encaminhada, um round quase não mexe; com o placar apertado perto do fim, um round "
            "mexe muito.")
    if len(curva) >= 2:
        # os dois exemplos saem da partida: o round que menos mexeu e o que mais mexeu (no empate, o primeiro)
        menor = min(curva, key=lambda c: (abs(variacao(c)), c["round"]))
        maior = min(curva, key=lambda c: (-abs(variacao(c)), c["round"]))
        if abs(variacao(maior)) > abs(variacao(menor)):
            base += (f" Nesta partida, o round {menor['round']}, no {placar_antes_e_depois(menor)[0]}, mexeu "
                     f"{format_pp(abs(variacao(menor))).lstrip('+')}; o round {maior['round']}, no "
                     f"{placar_antes_e_depois(maior)[0]}, mexeu {format_pp(abs(variacao(maior))).lstrip('+')}.")
    return base + " Passe o mouse numa barra para ver o que pesou no round, e clique para assistir."


def _nota_do_decisivo(wp: dict, decisivo: dict | None) -> str:
    """Liga a maior barra ao round decisivo publicado, pela definição de `metrics.win_probability`."""
    top = wp.get("top") or []
    if not top:
        return ""
    if decisivo is None:
        minimo = wp.get("minimo_exigido")
        if minimo is None:
            return ""
        maior = top[0]
        de_maior, de_minimo = _pp_par(abs(variacao(maior)), float(minimo))
        return (f"A maior barra, a do round {int(maior['round'])}, mexeu {de_maior}, abaixo do mínimo de "
                f"{de_minimo} para um round ser decisivo ({_fator(FATOR_MINIMO_DECISIVO)} vez o que mexe o "
                "primeiro round, no 0–0): esta partida não tem round decisivo.")
    rd = int(decisivo["round"])
    linha_dec = next((t for t in top if int(t["round"]) == rd), None)
    if linha_dec is None:
        return ""
    v_dec = abs(variacao(linha_dec))
    iguais = [t for t in top if int(t["round"]) != rd and math.isclose(abs(variacao(t)), v_dec, abs_tol=1e-9)]
    if iguais:
        rounds = [str(rd)] + [str(int(t["round"])) for t in iguais]
        lista = ", ".join(rounds[:-1]) + " e " + rounds[-1]
        return (f"Os rounds {lista} mexeram o mesmo tanto ({format_pp(v_dec).lstrip('+')}). Com barras "
                f"iguais, o decisivo é o que veio primeiro: o round {rd}.")
    vice = next((t for t in top if int(t["round"]) != rd), None)
    de_dec = _pp_par(v_dec, abs(variacao(vice)))[0] if wp.get("empate_no_topo") and vice else format_pp(v_dec).lstrip("+")
    texto = f"A barra mais alta é a do round decisivo, o {rd}: ele mexeu {de_dec} na chance de vitória."
    if wp.get("empate_no_topo") and vice:
        de_vice, _ = _pp_par(abs(variacao(vice)), v_dec)
        texto += (f" A do round {int(vice['round'])} ({de_vice}) fica a menos de "
                  f"{format_pp(LIMIAR_EMPATE_WPA).lstrip('+')}: os dois pesaram praticamente o mesmo.")
    return texto


def bloco(payload: dict, nomes: dict[str, str]) -> dict | None:
    """O bloco de texto da seção, pronto para a página (PAGINA.peso_dos_rounds).

    `nomes` é o nome de cada lado ({"A": ..., "B": ...}), o mesmo do cabeçalho. `rotulos` e `frases` vêm
    na ordem da curva (um por round); `cartoes`, na ordem de `win_probability.top` (os três maiores).
    """
    wp = payload.get("win_probability") or {}
    curva = wp.get("curve") or []
    if not curva:
        return None
    decisivo = payload.get("decisive_round")

    def frase(linha: dict) -> str:
        return f"{format_pp(variacao(linha))} na chance de {nomes['A']}"

    cartoes = []
    for t in wp.get("top") or []:
        antes, depois = placar_antes_e_depois(t)
        cartoes.append({
            "cabecalho": f"Round {int(t['round'])} · {antes} → {depois}",
            "variacao": f"{frase(t)} · {nomes[t['winner_team']]} venceu o round",
        })
    return {
        "titulo": TITULO,
        "abertura": _abertura(curva, nomes),
        "nota": _nota_do_decisivo(wp, decisivo),
        "rotulos": [format_pp(variacao(c)) for c in curva],
        "frases": [frase(c) for c in curva],
        "placares": [" → ".join(placar_antes_e_depois(c)) for c in curva],
        "cartoes": cartoes,
    }
