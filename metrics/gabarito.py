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
    py -3.12 -m metrics.gabarito
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np

RAIZ = Path(__file__).resolve().parents[1]
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
        "_leia_isto": ("Gerado por py -3.12 -m metrics.gabarito a partir de "
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


# --- Metas por partida (rota A fora da amostra) -------------------------------
# Saíram de pesquisa/valida_rota_a.py (auditoria 5.6): o teste da rotina e o
# numeros_citaveis usam estas funções, e lógica usada por teste não mora em
# script de pesquisa. O script continua lá, com as perguntas da validação.

def botao_gravado(f: float) -> float:
    return round(f * 2) / 2


def limite_da_invariante() -> float:
    from metrics import grenade_throws as gt
    c = sorted(gt.VELOCIDADE_BOTAO.values())
    return min(b - a for a, b in zip(c, c[1:])) - gt.TOLERANCIA_BOTAO


def pes_da_saida(a: dict, ev: dict) -> np.ndarray:
    """Pés de referência do ponto de saída: tabela em t; no pulo, decolagem + 0,1 s."""
    from metrics import grenade_throws as gt
    e = a["entrada"]
    pes = np.array([*e["xy_janela"][-2], e["z_janela"][-2] + ev["z_ref"]])
    if ev["regra"] == "regra fixa 6-13":
        t01 = -ev["ticks_desde_decolagem"] / a["tickrate"] + gt.TEMPO_FIXO_DO_PULO
        J = np.array(e["xy_janela"])
        k = (len(J) - 2) + t01 * a["tickrate"] - 0.5
        i0 = int(np.floor(k))
        f = k - i0
        pes[:2] = J[i0] * (1 - f) + J[i0 + 1] * f
    return pes


def metas_da_partida(arr: list[dict]) -> dict:
    from metrics import grenade_throws as gt
    lim = limite_da_invariante()
    rot, ar, post, erros_vel, erros_pos, max_rot = [], [], [], [], [], 0.0
    indet, guarda, erros_postura = 0, 0, []
    for a in arr:
        z, xy, vp, zs, t = _entradas(a)
        e, d = a["entrada"], a["demo"]
        ev = gt.estado_vertical(z, xy, t)
        r = gt.rotina_do_jogo(z, xy, vp, zs, e["pitch"], e["yaw"], t)
        u = gt.direcao_do_lancamento(e["pitch"], e["yaw"])
        b_rec = botao_gravado(d["forca"])
        if r["botao"] is not None:
            rot.append(r["botao"] == b_rec)
            vj = np.array([*ev["vh"], ev["vz"]])
            erro = float(np.linalg.norm(gt.VELOCIDADE_BOTAO[r["botao"]] * u + gt.FATOR_HERANCA * vj - np.array(d["v0"])))
            max_rot = max(max_rot, erro)
        if r["no_ar"] is not None:
            ar.append(r["no_ar"] == (not d["no_chao"]))
        else:
            indet += 1
        if r["estado_vertical"] == "vetor incoerente com o voo":
            guarda += 1
        if r["postura"] is not None and d["no_chao"] and d["duck_amount"] in (0.0, 1.0):
            post.append((r["postura"] == "agachado") == (d["duck_amount"] == 1.0))
            if not post[-1]:
                erros_postura.append((a["id"], r["postura"], d["duck_amount"], round(r["altura_saida"] - gt.CORTE_POSTURA, 2),
                                      round(float(np.ptp(np.array(e["z_janela"])[:-1])), 1)))
        if ev["vz"] is not None:
            vj = np.array([*ev["vh"], ev["vz"]])
            erros_vel.append(float(np.linalg.norm(gt.VELOCIDADE_BOTAO[b_rec] * u + gt.FATOR_HERANCA * vj - np.array(d["v0"]))))
        if r["botao"] is not None and r["postura"] is not None:
            h = (gt.ALTURA_SAIDA_AGACHADO if r["postura"] == "agachado" else gt.ALTURA_SAIDA_EM_PE) \
                + gt.ALTURA_SAIDA_POR_BOTAO * (r["botao"] - 1)
            calc = pes_da_saida(a, ev) + np.array([0, 0, h]) + gt.AVANCO_SAIDA * u
            erros_pos.append(float(np.linalg.norm(calc - np.array(d["p0"]))))
    ev_, ep_ = np.array(erros_vel), np.array(erros_pos)
    return {
        "n": len(arr),
        "botao": (sum(rot), len(rot)), "cobertura": len(rot) / len(arr),
        "no_ar": (sum(ar), len(ar)), "postura": (sum(post), len(post)),
        "invariante_max": max_rot, "invariante_limite": lim,
        "vel_menos_5": float(np.mean(ev_ < 5)), "vel_p99": float(np.percentile(ev_, 99)), "vel_max": float(ev_.max()),
        "pos_menos_1": float(np.mean(ep_ < 1)), "pos_p95": float(np.percentile(ep_, 95)), "pos_max": float(ep_.max()),
        "indeterminados": indet / len(arr), "guarda": guarda, "erros_postura": erros_postura,
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
