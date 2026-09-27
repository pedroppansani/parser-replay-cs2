"""Constantes da rota A que saem do GABARITO, calculadas (nunca digitadas).

Grava `metrics/gabarito_constantes.json`, que `metrics/grenade_throws.py` lê:
  - tolerancia_botao: ceil(2 × p99) do erro da velocidade calculada contra
    m_vInitialVelocity, nos arremessos em que o modelo se aplica;
  - faixa_postura_neutra: (margem do agachado correto mais alto, margem do em
    pé correto mais baixo) em relação ao corte, entre os arremessos com botão
    e altura de saída.
Com gabarito novo (mais partidas em tests/fixtures/gabarito_arremessos_*.json),
rodar de novo recalcula as duas pela mesma função.

Uso:
    py -3.12 -m scripts.constantes_do_gabarito
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))
FIXTURES = RAIZ / "tests" / "fixtures"
SAIDA = RAIZ / "metrics" / "gabarito_constantes.json"


def carrega_gabarito() -> tuple[list[dict], list[str]]:
    arremessos, partidas = [], []
    for f in sorted(FIXTURES.glob("gabarito_arremessos_*.json")):
        doc = json.loads(f.read_text(encoding="utf-8"))
        partidas.append(doc["partida"])
        arremessos += [{**a, "tickrate": doc["tickrate"]} for a in doc["arremessos"]]
    return arremessos, partidas


def _entradas(a: dict) -> tuple:
    e = a["entrada"]
    t = a["tickrate"]
    pp = np.array(e["proj_pontos"])
    pt = e["proj_ticks"]
    vp = (pp[1] - pp[0]) / ((pt[1] - pt[0]) / t)
    z_saida = pp[0][2] - vp[2] * (pt[0] - e["tick_soltura"]) / t
    return np.array(e["z_janela"]), np.array(e["xy_janela"]), vp, z_saida, t


def calcula(arremessos: list[dict]) -> dict:
    from metrics import grenade_throws as gt

    # 1. tolerância: erro do modelo onde ele se aplica
    erros = []
    for a in arremessos:
        z, xy, vp, _, t = _entradas(a)
        ev = gt.estado_vertical(z, xy, t)
        if ev["vz"] is None:
            continue
        botao = round(a["demo"]["forca"] * 2) / 2
        u = gt.direcao_do_lancamento(a["entrada"]["pitch"], a["entrada"]["yaw"])
        calc = gt.VELOCIDADE_BOTAO[botao] * u + gt.FATOR_HERANCA * np.array([*ev["vh"], ev["vz"]])
        erros.append(float(np.linalg.norm(calc - np.array(a["demo"]["v0"]))))
    p99 = float(np.percentile(erros, 99))
    tolerancia = float(math.ceil(2 * p99))

    # 2. faixa de postura: o caso correto mais próximo do corte, de cada lado
    acima, abaixo = [], []
    for a in arremessos:
        z, xy, vp, z_saida, t = _entradas(a)
        r = gt.rotina_do_jogo(z, xy, vp, z_saida, a["entrada"]["pitch"], a["entrada"]["yaw"], t,
                              tolerancia=tolerancia, faixa_postura=(0.0, 0.0))
        if r["altura_saida"] is None:
            continue
        d = r["altura_saida"] - gt.CORTE_POSTURA
        duck = a["demo"]["duck_amount"]
        if duck == 0.0 and d > 0:
            acima.append(d)
        elif duck == 1.0 and d < 0:
            abaixo.append(d)
    return {
        "_leia_isto": ("Gerado por py -3.12 -m scripts.constantes_do_gabarito a partir de "
                       "tests/fixtures/gabarito_arremessos_*.json. Não editar à mão."),
        "tolerancia_botao": tolerancia,
        "tolerancia_origem": {"p99_erro_velocidade": round(p99, 4), "n": len(erros)},
        "faixa_postura_neutra": [round(max(abaixo), 4), round(min(acima), 4)],
        "faixa_postura_origem": {"n_agachados_corretos": len(abaixo), "n_em_pe_corretos": len(acima)},
    }


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    arremessos, partidas = carrega_gabarito()
    doc = calcula(arremessos)
    doc["partidas"] = partidas
    doc["n_arremessos"] = len(arremessos)
    SAIDA.write_text(json.dumps(doc, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(json.dumps(doc, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
