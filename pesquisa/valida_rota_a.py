"""Validação da rota A FORA DA AMOSTRA: as metas por partida do gabarito.

As regras e as constantes da rota A saíram da match_23. Este script roda as
metas em cada partida com gabarito (tests/fixtures/gabarito_arremessos_*),
com as constantes EXATAMENTE como estão no código (nada é recalculado aqui),
e responde às três perguntas da validação:
  1. solturas nas janelas neutras (0-5 e 14-18 ticks depois da decolagem):
     o que o jogo usou, a vz fixa do pulo ou a vz real;
  2. a faixa neutra de postura na match_11 (Anubis): quem estava agachado;
  3. pés em t contra pés do evento (t-1): erro do ponto de saída, parado e em
     movimento.

Uso:
    py -3.12 -m pesquisa.valida_rota_a
"""
from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

import numpy as np

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))
from metrics import grenade_throws as gt  # noqa: E402
from metrics.gabarito import (_entradas, botao_gravado, carrega_gabarito,  # noqa: E402,F401
                              limite_da_invariante, metas_da_partida, pes_da_saida)

META = 0.99


def pergunta_janelas(todos: list[dict]) -> None:
    print("\n== 1. solturas nas janelas neutras: o que o jogo usou")
    casos = Counter()
    for a in todos:
        z, xy, vp, zs, t = _entradas(a)
        ev = gt.estado_vertical(z, xy, t)
        if not ev["regra"].startswith("janela"):
            continue
        e, d = a["entrada"], a["demo"]
        u = gt.direcao_do_lancamento(e["pitch"], e["yaw"])
        usada = (np.array(d["v0"]) - gt.VELOCIDADE_BOTAO[botao_gravado(d["forca"])] * u) / gt.FATOR_HERANCA
        fixa = d["vz_decolagem"] - gt.GRAVIDADE * gt.TEMPO_FIXO_DO_PULO
        real = ev["vz_derivada"]
        qual = "vz fixa" if abs(usada[2] - fixa) < abs(usada[2] - real) else "vz real"
        gravado = None if d["tick_do_pulo"] is None else e["tick_soltura"] - d["tick_do_pulo"]
        casos[(ev["regra"], qual)] += 1
        print(f"   {a['id']:18s} {ev['regra']:28s} decolagem estimada {ev['ticks_desde_decolagem']:6.2f} "
              f"gravada {gravado} | vz usada {usada[2]:7.1f} fixa {fixa:7.1f} real {real:7.1f} -> {qual}")
    print("   resumo:", dict(casos))


def pergunta_anubis(todos: list[dict]) -> None:
    print("\n== 2. faixa neutra de postura na match_11 (Anubis)")
    lo, hi = gt.FAIXA_POSTURA_NEUTRA
    na_faixa, dist = [], {"em pé": [], "agachado": []}
    for a in todos:
        if not a["id"].startswith("match_11:"):
            continue
        z, xy, vp, zs, t = _entradas(a)
        e, d = a["entrada"], a["demo"]
        r = gt.rotina_do_jogo(z, xy, vp, zs, e["pitch"], e["yaw"], t, faixa_postura=(0.0, 0.0))
        if r["altura_saida"] is None:
            continue
        dd = r["altura_saida"] - gt.CORTE_POSTURA
        if d["no_chao"] and d["duck_amount"] in (0.0, 1.0):
            dist["agachado" if d["duck_amount"] == 1.0 else "em pé"].append(dd)
        if lo <= dd <= hi:
            na_faixa.append((a["id"], round(dd, 2), d["duck_amount"], d["no_chao"]))
    print(f"   na faixa [{lo}, {hi}]: {len(na_faixa)}; duck_amount deles: {Counter(x[2] for x in na_faixa)}")
    for x in na_faixa:
        print("     ", x)
    for k, v in dist.items():
        v = np.array(v)
        if v.size:
            print(f"   {k}: n={v.size} altura - corte mín {v.min():.2f} p1 {np.percentile(v, 1):.2f} mediana {np.median(v):.2f} máx {v.max():.2f}")
    if dist["em pé"] and dist["agachado"]:
        print(f"   separa? menor em pé {min(dist['em pé']):.2f} x maior agachado {max(dist['agachado']):.2f}")


def pergunta_pes(por_partida: dict[str, list[dict]]) -> None:
    print("\n== 3. pés em t x pés do evento (t-1): erro do ponto de saída no chão (u)")
    total = {("parado", "t-1"): [], ("parado", "t"): [], ("em movimento", "t-1"): [], ("em movimento", "t"): []}
    for partida, arr in por_partida.items():
        for a in arr:
            e, d = a["entrada"], a["demo"]
            if not d["no_chao"] or d["duck_amount"] not in (0.0, 1.0):
                continue
            b = botao_gravado(d["forca"])
            h = (gt.ALTURA_SAIDA_AGACHADO if d["duck_amount"] == 1.0 else gt.ALTURA_SAIDA_EM_PE) + gt.ALTURA_SAIDA_POR_BOTAO * (b - 1)
            u = gt.direcao_do_lancamento(e["pitch"], e["yaw"])
            pv = np.array(e["pos_vizinhos"])
            mov = "parado" if np.linalg.norm((pv[1] - pv[0])[:2]) * a["tickrate"] / 2 < 5 else "em movimento"
            for nome, pes in (("t-1", np.array(e["pes"])), ("t", np.array([*e["xy_janela"][-2], e["z_janela"][-2]]))):
                total[(mov, nome)].append(float(np.linalg.norm(pes + np.array([0, 0, h]) + gt.AVANCO_SAIDA * u - np.array(d["p0"]))))
    for (mov, nome), v in total.items():
        v = np.array(v)
        print(f"   {mov:13s} pés {nome:3s}: n={v.size} mediana {np.median(v):.3f} p95 {np.percentile(v, 95):.3f} < 1u {np.mean(v < 1):.1%}")


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    todos, partidas = carrega_gabarito()
    por_partida: dict[str, list[dict]] = {}
    for a in todos:
        por_partida.setdefault(a["id"].split(":")[0], []).append(a)
    print(f"constantes CONGELADAS: tolerância {gt.TOLERANCIA_BOTAO}, faixa de postura {gt.FAIXA_POSTURA_NEUTRA}, "
          f"janela {gt.JANELA_REGRA_FIXA} / real >= {gt.JANELA_VZ_REAL_MIN}, 2ª diferença {gt.TOL_SEGUNDA_DIFERENCA}")
    print("\npartida   n    botão         cobertura  no ar(determ.)  indeterm.  postura(fora da faixa)  guarda  invariante      vel<5  vel p99  vel máx  pos<1  pos p95  pos máx")
    falhas, erros_postura = [], []
    for p in sorted(por_partida):
        m = metas_da_partida(por_partida[p])
        fr = lambda x: f"{x[0]}/{x[1]} {x[0] / x[1]:.1%}" if x[1] else "-"
        print(f"{p}  {m['n']:4d}  {fr(m['botao']):13s} {m['cobertura']:6.1%}    {fr(m['no_ar']):14s} {m['indeterminados']:6.1%}    "
              f"{fr(m['postura']):22s} {m['guarda']:4d}   "
              f"{m['invariante_max']:5.1f}<{m['invariante_limite']:.1f}  {m['vel_menos_5']:6.1%} {m['vel_p99']:7.2f} {m['vel_max']:8.1f}  "
              f"{m['pos_menos_1']:5.1%} {m['pos_p95']:7.2f} {m['pos_max']:7.1f}")
        erros_postura += m["erros_postura"]
        if m["indeterminados"] > 0.02:
            falhas.append((p, "indeterminados acima de 2%", round(m["indeterminados"], 4), None))
        for nome in ("botao", "no_ar", "postura"):
            ok, n = m[nome]
            if n and ok / n < (0.995 if nome == "postura" else META):
                falhas.append((p, nome, ok, n))
    print("\nerros de postura no chão (id, rotulado, duck_amount, altura - corte, subida dos pés em 64 ticks):")
    for x in erros_postura:
        print("   ", x)
        if m["invariante_max"] >= m["invariante_limite"]:
            falhas.append((p, "invariante", m["invariante_max"], m["invariante_limite"]))
    print("\nMETAS ABAIXO:", falhas or "nenhuma")
    pergunta_janelas(todos)
    pergunta_anubis(todos)
    pergunta_pes(por_partida)


if __name__ == "__main__":
    main()
