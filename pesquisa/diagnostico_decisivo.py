"""Diagnóstico do piso do round decisivo nas partidas do corpus (fase 6, passo 6.1).

Não muda nada. Lê a curva da chance de vitória já gravada em cada insights.json
(metrics/win_probability.py, modelo neutro de placar) e responde:

  1. por partida: formato, placar final, maior diferença de placar durante o jogo,
     virada (o vencedor esteve abaixo de 50% de chance em algum momento), os três
     maiores |ΔP|, quantos rounds passam do piso e se há round decisivo hoje;
  2. quanto da decisão "tem ou não tem round decisivo" a diferença FINAL de placar
     sozinha já explica (tabela de contingência e o melhor corte só pelo placar);
  3. o empate no topo: em quantas partidas o 1º e o 2º ficam a menos de
     LIMIAR_EMPATE_WPA, e a distribuição dessa diferença.

Uso:
    py -3.12 -m pesquisa.diagnostico_decisivo
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

import numpy as np

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))
from metrics.win_probability import LIMIAR_EMPATE_WPA  # noqa: E402

PROCESSED = RAIZ / "data" / "processed"


def partidas() -> list[dict]:
    """Uma linha por partida, só com o que já está gravado."""
    linhas = []
    for f in sorted(PROCESSED.glob("match_*/insights.json")):
        d = json.loads(f.read_text(encoding="utf-8"))
        wp, m = d["win_probability"], d["match"]
        curva = sorted(wp["curve"], key=lambda r: r["round"])
        a, b = m["score_a"], m["score_b"]
        vencedor = "A" if a > b else "B"
        chance_do_vencedor = [r["wp_a_antes"] if vencedor == "A" else 1 - r["wp_a_antes"] for r in curva]
        dif_placar = [r["score_a"] - r["score_b"] for r in curva]
        absolutos = sorted((r["wpa_abs"] for r in curva), reverse=True)
        minimo = wp["minimo_exigido"]
        linhas.append({
            "partida": f.parent.name, "formato": m.get("formato"), "placar": f"{a}-{b}",
            "rounds": len(curva), "diferenca_final": abs(a - b),
            "maior_diferenca": max(abs(x) for x in dif_placar),
            "virada": min(chance_do_vencedor) < 0.5,
            "menor_chance_do_vencedor": min(chance_do_vencedor),
            "top": absolutos[:3], "acima_do_piso": sum(x >= minimo for x in absolutos),
            "piso": minimo, "tem_decisivo": wp["top"] and wp["maior_wpa"] is not None
            and d.get("decisive_round") is not None and absolutos[0] >= minimo,
            "dif_1_2": absolutos[0] - absolutos[1] if len(absolutos) > 1 else None,
            "mediana_abs": float(np.median(absolutos)),
        })
    return linhas


def melhor_corte_so_pelo_placar(linhas: list[dict]) -> tuple[int, int]:
    """O corte de diferença final que mais acerta "tem decisivo" (tem se dif <= corte)."""
    melhor = (0, -1)
    for corte in range(0, 14):
        acertos = sum((l["diferenca_final"] <= corte) == l["tem_decisivo"] for l in linhas)
        if acertos > melhor[1]:
            melhor = (corte, acertos)
    return melhor


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    linhas = partidas()
    print(f"## 1. Por partida ({len(linhas)} partidas; piso {linhas[0]['piso']:.3f} no MR12)\n")
    print("| partida | formato | placar | maior dif. no jogo | virada | |ΔP| 1º / 2º / 3º | acima do piso | tem decisivo |")
    print("|---|---|---|---|---|---|---|---|")
    for l in sorted(linhas, key=lambda l: (l["diferenca_final"], l["partida"])):
        t = " / ".join(f"{x:.3f}" for x in l["top"])
        print(f"| {l['partida']} | {l['formato']} | {l['placar']} | {l['maior_diferenca']} | "
              f"{'sim' if l['virada'] else 'não'} | {t} | {l['acima_do_piso']} | {'sim' if l['tem_decisivo'] else 'não'} |")

    print("\n## 2. A diferença final de placar explica 'tem decisivo'?\n")
    tab = Counter((l["diferenca_final"], l["tem_decisivo"]) for l in linhas)
    print("| diferença final | com decisivo | sem decisivo |")
    print("|---|---|---|")
    for dif in sorted({l["diferenca_final"] for l in linhas}):
        print(f"| {dif} | {tab[(dif, True)]} | {tab[(dif, False)]} |")
    corte, acertos = melhor_corte_so_pelo_placar(linhas)
    print(f"\nMelhor regra só pelo placar: 'tem decisivo se a diferença final <= {corte}' acerta "
          f"{acertos} de {len(linhas)} ({acertos / len(linhas):.0%}).")
    viradas = [l for l in linhas if l["virada"]]
    print(f"Partidas com virada: {len(viradas)}; com decisivo entre elas: {sum(l['tem_decisivo'] for l in viradas)}.")

    print(f"\n## 3. Empate no topo (limiar atual {LIMIAR_EMPATE_WPA})\n")
    difs = np.array([l["dif_1_2"] for l in linhas if l["dif_1_2"] is not None])
    print(f"1º e 2º a menos de {LIMIAR_EMPATE_WPA}: {(difs < LIMIAR_EMPATE_WPA).sum()} de {len(difs)}")
    print(f"diferença 1º-2º: mín {difs.min():.4f}, p25 {np.percentile(difs, 25):.4f}, mediana {np.median(difs):.4f}, "
          f"p75 {np.percentile(difs, 75):.4f}, máx {difs.max():.4f}")
    exatos = (difs < 1e-9).sum()
    print(f"empates exatos (mesmo |ΔP| no 1º e no 2º): {exatos}")


if __name__ == "__main__":
    main()
