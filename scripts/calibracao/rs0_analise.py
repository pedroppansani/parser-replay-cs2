"""RS0 (só leitura): o Round Swing por jogador contra o oficial da HLTV (os prints do Pedro) e a estabilidade pelo número de rounds.

    py -3.12 -m scripts.calibracao.rs0_analise ARQUIVO_DO_rs0_swing_por_round.parquet
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import polars as pl

RAIZ = Path(__file__).resolve().parents[2]


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    d = pl.read_parquet(sys.argv[1])
    ref = json.loads((RAIZ / "data/reference/hltv_componentes.json").read_text(encoding="utf-8"))["partidas"]
    # (1) por partida e jogador: média por round em pontos percentuais (round sem linha = 0)
    pj = (d.group_by(["partida", "steamid", "nome", "rounds_da_partida"]).agg(pl.col("swing").sum().alias("soma"))
          .with_columns((100 * pl.col("soma") / pl.col("rounds_da_partida")).alias("pp")))
    lin = []
    for mid, v in ref.items():
        nos = {r["nome"]: r["pp"] for r in pj.filter(pl.col("partida") == mid).iter_rows(named=True)}
        baixo = {k.lower(): x for k, x in nos.items() if k}
        for nome, o in v["jogadores"].items():
            x = nos.get(nome, baixo.get((nome or "").lower()))
            if x is not None:
                lin.append((mid, nome, o["swing_pct"], x, v["rounds"]))
    of, nosso = np.array([l[2] for l in lin]), np.array([l[3] for l in lin])
    print(f"(1) {len(lin)} jogador-partidas em {len(ref)} partidas com o Swing oficial")
    print(f"    correlação {np.corrcoef(of, nosso)[0, 1]:.3f}; erro médio absoluto {np.abs(of - nosso).mean():.2f} p.p.; viés (nosso - oficial) {np.mean(nosso - of):+.2f}; "
          f"inclinação da reta nosso~oficial {np.polyfit(of, nosso, 1)[0]:.2f}; desvio do oficial {of.std():.2f}, do nosso {nosso.std():.2f}")
    rank = lambda a: np.argsort(np.argsort(a))
    print(f"    Spearman {np.corrcoef(rank(of), rank(nosso))[0, 1]:.3f}; erro quadrático médio {np.sqrt(np.mean((of - nosso) ** 2)):.2f} p.p.")
    por_m = {}
    for mid, nome, o, x, r in lin:
        por_m.setdefault(mid, []).append((o, x))
    cm = [np.corrcoef(*zip(*v))[0, 1] for v in por_m.values() if len(v) > 3]
    print(f"    correlação DENTRO de cada partida: mediana {np.median(cm):.2f}, pior {min(cm):.2f}, melhor {max(cm):.2f}")
    for lo, hi in ((0, 22), (22, 26), (26, 31), (31, 99)):
        s = [(o, x) for _, _, o, x, r in lin if lo <= r < hi]
        if len(s) > 5:
            a, b = np.array(s).T
            print(f"    partidas de {lo}-{hi - 1} rounds: {len(s)} jogadores, erro médio {np.abs(a - b).mean():.2f} p.p.")
    # maiores erros
    ordem = sorted(lin, key=lambda l: -abs(l[2] - l[3]))[:5]
    print("    maiores erros:", "; ".join(f"{m} {n} oficial {o:+.2f} nosso {x:+.2f}" for m, n, o, x, r in ordem))

    # (2) estabilidade: a média por round de cada jogador (steamid) em n rounds sorteados, duas metades disjuntas
    por_jog = {}
    for (sid, nome), g in d.group_by(["steamid", "nome"]):
        pass
    todos = d.group_by(["partida", "steamid"]).agg(pl.col("round_num").n_unique().alias("r_com_linha"))
    # série completa por jogador: um valor por round jogado (0 onde não há linha)
    rounds_por_partida = d.select("partida", "rounds_da_partida").unique().to_dicts()
    series: dict[int, list[float]] = {}
    for mid, ng in d.group_by("partida"):
        mid = mid[0]
        nr = int(ng["rounds_da_partida"][0])
        for sid, g in ng.group_by("steamid"):
            sid = sid[0]
            v = np.zeros(nr)
            for r, s in zip(g["round_num"].to_list(), g["swing"].to_list()):
                if 1 <= r <= nr:
                    v[r - 1] = s
            series.setdefault(sid, []).extend((100 * v).tolist())
    tam = np.array([len(v) for v in series.values()])
    print(f"\n(2) {len(series)} jogadores; rounds por jogador: mediana {int(np.median(tam))}, mínimo {tam.min()}, máximo {tam.max()}; com 100+ rounds: {(tam >= 100).sum()}, com 200+: {(tam >= 200).sum()}")
    sd = np.sqrt(np.mean([np.var(v) for v in series.values()]))
    print(f"    desvio do swing de UM round (p.p.): {sd:.1f}; erro padrão da média: " + ", ".join(f"{n} rounds ±{sd / np.sqrt(n):.1f}" for n in (10, 20, 30, 60, 100, 200)))
    rng = np.random.default_rng(1)
    print("    confiabilidade (correlação entre duas amostras disjuntas de n rounds, jogadores com 2n+ rounds):")
    for n in (10, 20, 30, 50, 80, 120):
        ok = [np.array(v) for v in series.values() if len(v) >= 2 * n]
        if len(ok) < 12:
            print(f"      n={n}: só {len(ok)} jogadores, sem estimativa")
            continue
        rs = []
        for _ in range(200):
            a, b = [], []
            for v in ok:
                i = rng.permutation(len(v))
                a.append(v[i[:n]].mean()); b.append(v[i[n:2 * n]].mean())
            rs.append(np.corrcoef(a, b)[0, 1])
        print(f"      n={n}: {len(ok)} jogadores, r = {np.mean(rs):.2f}")
    # distribuição do número entre jogadores (média por round de cada um, todos os rounds)
    medias = np.array([np.mean(v) for v in series.values() if len(v) >= 100])
    print(f"    média por round dos jogadores com 100+ rounds: de {medias.min():+.2f} a {medias.max():+.2f}; desvio entre jogadores {medias.std():.2f}")


if __name__ == "__main__":
    main()
