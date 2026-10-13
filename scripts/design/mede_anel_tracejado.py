"""
O anel duplo TRACEJADO da granada desenhada (fase 11) contra os radares, como o A13/A14 fazem para a peça.

    py -3.12 -m scripts.design.mede_anel_tracejado

Critério (prompt da fase 11, regra 2): um dos dois anéis passa de 3:1 em qualquer pixel do radar.

Como o map_core.js desenha (anelDoGlifo com `tracejado`): o halo claro (token tinta) e o contorno escuro (token
contorno) são tracejados NO MESMO PASSO, como o fantasma (§4.1). Onde há traço há os dois anéis; no vão não há
anel nenhum (o radar aparece). Então, nos pixels do anel, a conta é a mesma do anel duplo cheio: o pior pixel do
MAIOR dos dois contrastes, com o radar já processado pelo par do mapa (RADAR_AJUSTE).

A tabela mostra também a alternativa "só o halo tracejado, contorno contínuo": no vão do halo sobra só o contorno
escuro, que some sobre o radar escuro. É o motivo de os dois anéis seguirem o mesmo tracejado.

Amostragem: até 120.000 pixels por andar, semente fixa 28 (decisão 28), como o gera_radar_ajuste.
"""
from __future__ import annotations

import glob
import json
import os
import sys

sys.dont_write_bytecode = True
import numpy as np  # noqa: E402

from scripts.design import mede_radar as mr  # noqa: E402
from scripts.design._comum import DESIGN, extrai_radares  # noqa: E402
from scripts.design.gera_radar_ajuste import L_hex, TOKENS, contr  # noqa: E402

# O mínimo do critério (prompt da fase 11, regra 2; o mesmo 3:1 do A14 para elemento gráfico, WCAG 1.4.11).
MINIMO = 3.0
AMOSTRA = 120000
SEMENTE = 28


def mede(pasta: str | None = None) -> list[dict]:
    """Uma linha por andar: o pior pixel do anel duplo tracejado (os dois anéis no mesmo passo) e o da alternativa
    com só o halo tracejado (no vão, só o contorno)."""
    pasta = pasta or str(extrai_radares())
    ajuste = json.loads((DESIGN / "radar_ajuste.json").read_text(encoding="utf-8"))
    linhas = []
    for arq in sorted(glob.glob(os.path.join(pasta, "*.png"))):
        nome = os.path.basename(arq)[:-4]
        mapa = nome.rsplit("_", 1)[0]
        s, b = ajuste["ajuste"].get(mapa, ajuste["padrao"])
        rgb = mr.carrega(arq)
        if len(rgb) > AMOSTRA:
            rgb = rgb[np.random.default_rng(SEMENTE).choice(len(rgb), AMOSTRA, replace=False)]
        Lpx = mr.lum_wcag(mr.processa(rgb, s, b))
        contorno, halo = contr(L_hex(TOKENS["contorno"]), Lpx), contr(L_hex(TOKENS["halo"]), Lpx)
        linhas.append({"andar": nome, "s": s, "b": b,
                       "mesmo_passo": float(np.maximum(contorno, halo).min()),
                       "so_o_halo": float(contorno.min())})
    return linhas


def main() -> int:
    linhas = mede(sys.argv[1] if len(sys.argv) > 1 else None)
    print("== Anel duplo tracejado da granada desenhada x radares (pior pixel, radar com o par do mapa) ==\n")
    print(f"{'andar':<11} {'s':>5} {'b':>5}  {'halo+contorno no mesmo passo':>28}  {'só o halo tracejado (vão)':>26}")
    for l in linhas:
        print(f"{l['andar']:<11} {l['s']:5.2f} {l['b']:5.2f}  {l['mesmo_passo']:28.2f}  {l['so_o_halo']:26.2f}")
    falha = [l["andar"] for l in linhas if l["mesmo_passo"] < MINIMO]
    print(f"\npior de todos (mesmo passo): {min(l['mesmo_passo'] for l in linhas):.2f}:1 (mínimo {MINIMO:.0f}:1)")
    if falha:
        print("PARAR: abaixo de 3:1 em", ", ".join(falha))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
