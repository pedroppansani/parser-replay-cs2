"""
O anel duplo TRACEJADO da granada desenhada (fase 11) contra os radares, como o A13/A14 fazem para a peça.

    py -3.12 -m scripts.design.mede_anel_tracejado

Critério (prompt da fase 11, regra 2): um dos dois anéis passa de 3:1 em qualquer pixel do radar.

Fase 15 (V3 da §19.7): o tracejado passou a ser em px de TELA (3,5 on / 3 off) e a granada desenhada ganhou o
carimbo (quadrado de 4 px de --tinta com 1 px de --contorno por fora). O critério de "mesmo passo" deixou de ser só
a leitura do código: `passo_de_tela` abre o `map_core.js` no navegador (1440 e 375 px, 1x e 2x), grava cada `stroke()`
do anel e confere que o halo e o contorno saem com o MESMO passo e que ele vale 3,5/3 px de tela em toda largura e
densidade. A conta de contraste (o pior pixel do MAIOR dos dois) vale nos pixels do anel e do carimbo: o carimbo é
--tinta por dentro e --contorno por fora, os mesmos dois tokens, então o pior pixel dele é o mesmo número.

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


PASSO_DE_TELA = (3.5, 3.0)       # §19.7 (V1/V3) e decisão do Pedro na §19.1
TOLERANCIA_DO_PASSO = 0.01


def passo_de_tela() -> list[dict]:
    """Por largura e densidade: o passo em px de tela do halo e do contorno do anel da granada desenhada (chama o
    `map_core.js` de verdade) e se os dois são iguais entre si e ao 3,5/3 px de tela."""
    from scripts.design.mede_granada_real import confere_tracejado
    out = []
    for l in confere_tracejado():
        aneis = [s for s in l["strokes"] if s["passo"]]            # os tracejados: halo e contorno (o corpo não é)
        iguais = len(aneis) == 2 and aneis[0]["passo"] == aneis[1]["passo"]
        de_tela = bool(aneis) and all(abs(a - b) <= TOLERANCIA_DO_PASSO
                                      for s in aneis for a, b in zip(s["passo"], PASSO_DE_TELA))
        out.append({"largura": l["largura"], "densidade": l["densidade"], "aneis": aneis,
                    "mesmo_passo": iguais, "passo_de_tela": de_tela})
    return out


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    linhas = mede(sys.argv[1] if len(sys.argv) > 1 else None)
    print("== Anel duplo tracejado da granada desenhada x radares (pior pixel, radar com o par do mapa) ==\n")
    print(f"{'andar':<11} {'s':>5} {'b':>5}  {'halo+contorno no mesmo passo':>28}  {'só o halo tracejado (vão)':>26}")
    for l in linhas:
        print(f"{l['andar']:<11} {l['s']:5.2f} {l['b']:5.2f}  {l['mesmo_passo']:28.2f}  {l['so_o_halo']:26.2f}")
    falha = [l["andar"] for l in linhas if l["mesmo_passo"] < MINIMO]
    pior = min(l["mesmo_passo"] for l in linhas)
    print(f"\npior de todos (mesmo passo; vale também para o carimbo): {pior:.2f}:1 (mínimo {MINIMO:.0f}:1)")
    print("\n== passo em px de tela, no map_core.js (halo e contorno) ==")
    passos = passo_de_tela()
    for p in passos:
        print(f"{p['largura']:>5} px {p['densidade']}x: " + " | ".join(f"{s['passo'][0]:.2f}/{s['passo'][1]:.2f}" for s in p["aneis"])
              + f"   mesmo passo: {p['mesmo_passo']}   3,5/3 px de tela: {p['passo_de_tela']}")
    if falha:
        print("PARAR: abaixo de 3:1 em", ", ".join(falha))
        return 1
    if not all(p["mesmo_passo"] and p["passo_de_tela"] for p in passos):
        print("PARAR: o passo do anel não é o 3,5/3 px de tela nos dois anéis")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
