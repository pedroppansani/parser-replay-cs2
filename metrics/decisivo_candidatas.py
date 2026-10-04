"""Regras CANDIDATAS para o round decisivo (fase 6, passo 6.2). Nenhuma está ligada.

A regra em produção é a de `metrics/win_probability.round_decisivo`: o round de
maior |ΔP| da chance de vencer a partida, se passar de 1,5x o round mais barato
do formato. O diagnóstico do 6.1 (notas/investigacoes/2026-10-04-piso-do-decisivo.md)
mostrou que, com o modelo neutro de placar, esse piso quase só repete a diferença
final do placar (48 de 52 partidas), e que o empate no topo é a regra (36 de 52
com |ΔP| idêntico no 1º e no 2º). As candidatas abaixo respondem a perguntas de
jogo diferentes; quem escolhe é o Pedro, com as respostas do material de
calibração (passo 6.3), e o parâmetro de B sai de deixa-uma-partida-fora (6.4).

Todas são funções PURAS da curva (`win_probability.curva_da_partida`) e do time
vencedor, e devolvem o mesmo formato: {"round": int | None, "empate": bool,
"porque": str}.

- A, piso absoluto (o controle): a regra de hoje, com o mesmo fator 1,5. O fator
  não tem nada a re-ancorar no corpus sem um alvo -- o alvo são as respostas do
  Pedro, e é no 6.4 que ele é medido contra elas.
- B, proeminência: o maior |ΔP| precisa se destacar dos rounds da MESMA partida,
  >= k x a mediana dos |ΔP| dela. Não depende da escala do placar, só do contorno.
- C, virada definitiva: o round depois do qual o vencedor nunca mais teve menos
  de 50% de chance, desde que antes dele tenha estado abaixo. "Quando a partida
  virou de vez." Sem virada, não há round decisivo por esta regra.
- D, combinação: C quando houve virada; senão, B.

EMPATE NO TOPO (para A, B e D-sem-virada): dois rounds empatam quando a frase da
página mostra a MESMA porcentagem para os dois. A frase escreve o |ΔP| em
porcentagem inteira (`metrics/formatting.format_pct`), e duas variações que o
leitor lê iguais não podem ser apresentadas como uma escolha. A origem do limiar
é a precisão do que se mostra, não um número escolhido pelo resultado. Na regra
C não há "topo": o round é definido pelo cruzamento dos 50%, e não há empate.
"""
from __future__ import annotations

from statistics import median

from metrics.formatting import format_pct
from metrics.win_probability import MR12, Formato, wpa_minimo

# k da regra B usado SÓ no material do 6.3: a mediana, nas 52 partidas, da razão
# entre o maior |ΔP| e a mediana dos |ΔP| da partida (1,68; mín 1,18, máx 4,11;
# pesquisa/diagnostico_decisivo.py). O k que vale é escolhido no 6.4, por
# deixa-uma-partida-fora contra as respostas do Pedro.
K_PROEMINENCIA_DO_MATERIAL = 1.68


def _ordenados(curva: list[dict]) -> list[dict]:
    return sorted(curva, key=lambda r: (-r["wpa_abs"], r["round"]))


def empate_por_frase(primeiro: float, segundo: float | None) -> bool:
    """Empate quando a página escreveria a mesma porcentagem para os dois."""
    return segundo is not None and format_pct(primeiro) == format_pct(segundo)


def _empate_do_topo(curva: list[dict]) -> bool:
    o = _ordenados(curva)
    return len(o) > 1 and empate_por_frase(o[0]["wpa_abs"], o[1]["wpa_abs"])


def regra_a(curva: list[dict], formato: Formato = MR12) -> dict:
    """A: o maior |ΔP| se passar do piso absoluto do formato (a regra de hoje)."""
    if not curva:
        return {"round": None, "empate": False, "porque": "partida sem rounds"}
    o, piso = _ordenados(curva), wpa_minimo(formato)
    if o[0]["wpa_abs"] < piso:
        return {"round": None, "empate": False,
                "porque": f"o maior salto ({format_pct(o[0]['wpa_abs'])}) não passa do piso de {format_pct(piso)}"}
    return {"round": int(o[0]["round"]), "empate": _empate_do_topo(curva),
            "porque": f"maior salto da partida, {format_pct(o[0]['wpa_abs'])}, acima do piso de {format_pct(piso)}"}


def regra_b(curva: list[dict], k: float = K_PROEMINENCIA_DO_MATERIAL) -> dict:
    """B: o maior |ΔP| precisa ser >= k x a mediana dos |ΔP| da própria partida."""
    if not curva:
        return {"round": None, "empate": False, "porque": "partida sem rounds"}
    o = _ordenados(curva)
    med = median(r["wpa_abs"] for r in curva)
    razao = o[0]["wpa_abs"] / med if med > 0 else float("inf")
    texto = f"o maior salto vale {razao:.2f}x o round típico da partida (exigido {k:.2f}x)".replace(".", ",")
    if razao < k:
        return {"round": None, "empate": False, "porque": f"nenhum round se destaca: {texto}"}
    return {"round": int(o[0]["round"]), "empate": _empate_do_topo(curva), "porque": texto}


def chance_do_vencedor(curva: list[dict], vencedor: str) -> list[tuple[int, float, float]]:
    """(round, chance do vencedor ANTES, chance DEPOIS), em ordem de round."""
    saida = []
    for r in sorted(curva, key=lambda r: r["round"]):
        antes, depois = r["wp_a_antes"], r["wp_a_depois"]
        if vencedor == "B":
            antes, depois = 1 - antes, 1 - depois
        saida.append((int(r["round"]), float(antes), float(depois)))
    return saida


def regra_c(curva: list[dict], vencedor: str) -> dict:
    """C: o round depois do qual o vencedor nunca mais esteve abaixo de 50%,
    se antes dele esteve. Sem virada, nenhum round."""
    serie = chance_do_vencedor(curva, vencedor)
    abaixo = [i for i, (_, antes, depois) in enumerate(serie) if depois < 0.5]
    if not abaixo:
        return {"round": None, "empate": False,
                "porque": "sem virada: o vencedor nunca esteve abaixo de 50% de chance"}
    i = abaixo[-1] + 1
    if i >= len(serie):
        return {"round": None, "empate": False, "porque": "o vencedor terminou abaixo de 50% (curva incoerente)"}
    rn, antes, depois = serie[i]
    return {"round": rn, "empate": False,
            "porque": f"virada definitiva: o vencedor passou de {format_pct(antes)} para {format_pct(depois)} "
                      f"e não ficou mais abaixo de 50%"}


def regra_d(curva: list[dict], vencedor: str, k: float = K_PROEMINENCIA_DO_MATERIAL) -> dict:
    """D: C quando houve virada; senão, B."""
    c = regra_c(curva, vencedor)
    if c["round"] is not None:
        return {**c, "porque": "houve virada (regra C): " + c["porque"]}
    b = regra_b(curva, k)
    return {**b, "porque": "sem virada (regra B): " + b["porque"]}


def todas(curva: list[dict], vencedor: str, formato: Formato = MR12,
          k: float = K_PROEMINENCIA_DO_MATERIAL) -> dict[str, dict]:
    return {"A": regra_a(curva, formato), "B": regra_b(curva, k),
            "C": regra_c(curva, vencedor), "D": regra_d(curva, vencedor, k)}
