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
    import gzip
    arquivos = sorted(list(FIXTURES.glob("gabarito_arremessos_*.json")) + list(FIXTURES.glob("gabarito_arremessos_*.json.gz")))
    for f in arquivos:
        texto = gzip.decompress(f.read_bytes()).decode("utf-8") if f.suffix == ".gz" else f.read_text(encoding="utf-8")
        doc = json.loads(texto)
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


QUANTIS_POSTURA = (0.0, 0.25, 0.5, 1.0, 2.0, 3.0, 5.0)   # candidatos da faixa (%)
META_POSTURA = 0.995                                    # acerto fora da faixa, por partida


def calcula(arremessos: list[dict]) -> dict:
    """As constantes da rota A a partir do gabarito, nesta ordem:

    1. deslocamento do primeiro segmento do projétil (vp - v0, mediana);
    2. tolerância ANTES da guarda: ceil(2 × p99) do erro do vetor onde o modelo
       se aplica (com o botão gravado);
    3. limiar da guarda do voo: meio do vão entre o maior resíduo dos vetores
       certos (erro < 5 u/s) e o menor dos grosseiramente errados (erro acima
       da tolerância antes da guarda);
    4. tolerância final: ceil(2 × p99) do erro, sem os que a guarda neutraliza;
    5. faixa de postura por QUANTIL: o menor quantil q em que, fora da faixa
       [p(100-q) dos agachados, p(q) dos em pé] (medida a partir do corte),
       o acerto passa de META_POSTURA em TODAS as partidas.
    """
    from metrics import grenade_throws as gt

    # 1. deslocamento do primeiro segmento
    dif = []
    for a in arremessos:
        z, xy, vp, _, t = _entradas(a)
        pt = a["entrada"]["proj_ticks"]
        if pt[1] - pt[0] == 1:
            dif.append(vp - np.array(a["demo"]["v0"]))
    desloc_z = float(np.median(np.array(dif)[:, 2]))
    off = np.array([0.0, 0.0, desloc_z])

    # 2-4. erro do vetor e resíduo do voo, com o botão GRAVADO
    # voo limpo: o primeiro segmento observado bate com a velocidade inicial
    # gravada (sem quique no primeiro tick); ceil(2 x p99) da distância
    sujo = np.linalg.norm(np.array(dif) - off, axis=1)
    limite_voo_limpo = float(math.ceil(2 * np.percentile(sujo, 99)))
    casos = []
    for a in arremessos:
        z, xy, vp, _, t = _entradas(a)
        ev = gt.estado_vertical(z, xy, t)
        if ev["vz"] is None:
            continue
        b = round(a["demo"]["forca"] * 2) / 2
        u = gt.direcao_do_lancamento(a["entrada"]["pitch"], a["entrada"]["yaw"])
        prev = gt.VELOCIDADE_BOTAO[b] * u + gt.FATOR_HERANCA * np.array([*ev["vh"], ev["vz"]])
        limpo = float(np.linalg.norm(vp - np.array(a["demo"]["v0"]) - off)) <= limite_voo_limpo
        casos.append((float(np.linalg.norm(prev - np.array(a["demo"]["v0"]))), float(np.linalg.norm(vp - prev - off)), limpo))
    erro = np.array([x[0] for x in casos])
    res = np.array([x[1] for x in casos])
    limpo = np.array([x[2] for x in casos])
    tol_antes = float(math.ceil(2 * np.percentile(erro, 99)))
    certo_max = float(res[(erro < 5) & limpo].max())
    grosso_min = float(res[erro > tol_antes].min()) if (erro > tol_antes).any() else float("inf")
    limiar = (certo_max + grosso_min) / 2 if np.isfinite(grosso_min) else 2 * certo_max
    fica = res <= limiar
    tol = float(math.ceil(2 * np.percentile(erro[fica], 99)))

    # 5. faixa de postura por quantil
    alturas = []   # (partida, altura - corte, agachado?)
    for a in arremessos:
        z, xy, vp, zs, t = _entradas(a)
        d = a["demo"]
        if d["duck_amount"] not in (0.0, 1.0):
            continue
        r = gt.rotina_do_jogo(z, xy, vp, zs, a["entrada"]["pitch"], a["entrada"]["yaw"], t,
                              tolerancia=tol, faixa_postura=(0.0, 0.0), limiar_voo=limiar)
        if r["altura_saida"] is None:
            continue
        alturas.append((a["id"].split(":")[0], r["altura_saida"] - gt.CORTE_POSTURA, d["duck_amount"] == 1.0))
    ag = np.array([h for _, h, x in alturas if x])
    pe = np.array([h for _, h, x in alturas if not x])
    curva, escolhido = [], None
    for q in QUANTIS_POSTURA:
        lo, hi = sorted((float(np.percentile(ag, 100 - q)), float(np.percentile(pe, q))))
        por: dict[str, list[int]] = {}
        for partida, h, agachado in alturas:
            if lo <= h <= hi:
                continue
            por.setdefault(partida, [0, 0])
            por[partida][0] += int((h < 0) == agachado)
            por[partida][1] += 1
        pior = min(ok / n for ok, n in por.values())
        cobertura = sum(n for _, n in por.values()) / len(alturas)
        curva.append({"quantil": q, "faixa": [round(lo, 4), round(hi, 4)], "pior_acerto": round(pior, 5),
                      "cobertura": round(cobertura, 5)})
        if escolhido is None and pior >= META_POSTURA:
            escolhido = curva[-1]
    if escolhido is None:
        escolhido = curva[-1]
    return {
        "_leia_isto": ("Gerado por py -3.12 -m scripts.constantes_do_gabarito a partir de "
                       "tests/fixtures/gabarito_arremessos_*. Não editar à mão."),
        "deslocamento_primeiro_segmento_z": round(desloc_z, 4),
        "tolerancia_antes_da_guarda": tol_antes,
        "limiar_guarda_voo": round(limiar, 4),
        "limiar_guarda_origem": {"maior_residuo_vetor_certo": round(certo_max, 4),
                                 "menor_residuo_vetor_grosseiro": round(grosso_min, 4),
                                 "n": len(casos), "neutralizados_no_gabarito": int((~fica).sum()),
                                 "voo_sujo_no_primeiro_tick": int((~limpo).sum()),
                                 "limite_voo_limpo": limite_voo_limpo},
        "tolerancia_botao": tol,
        "tolerancia_origem": {"p99_erro_velocidade": round(float(np.percentile(erro[fica], 99)), 4),
                              "p99_antes_da_guarda": round(float(np.percentile(erro, 99)), 4),
                              "n": int(fica.sum())},
        "faixa_postura_neutra": escolhido["faixa"],
        "faixa_postura_origem": {"quantil": escolhido["quantil"], "curva": curva,
                                 "n_agachados": int(ag.size), "n_em_pe": int(pe.size)},
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
