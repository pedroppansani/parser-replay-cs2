"""RS0 (só leitura): duas opções de modelo de chance de vitória do round, fora da dobra (agrupado por partida), com o mapa como candidato.

    py -3.12 -m scripts.calibracao.rs0_modelos
Compara: logística atual (estado completo + tempo), logística + mapa (lado x mapa), tabela suavizada (vivos x vivos x bomba x lado, encolhida para a taxa do lado).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import polars as pl

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ))
from scripts.calibracao.valida_modelo_de_round import DOBRAS, amostras, atributos, mede  # noqa: E402
from scripts.fit_rating import partidas_disponiveis  # noqa: E402


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    from sklearn.linear_model import LogisticRegression
    from sklearn.model_selection import GroupKFold

    ids = partidas_disponiveis()
    df = pl.concat([amostras(m) for m in ids])
    mapa = {m: json.loads((RAIZ / "data/processed" / m / "match_meta.json").read_text(encoding="utf-8"))["map_name"] for m in ids}
    df = df.with_columns(pl.col("partida").replace_strict(mapa, return_dtype=pl.String).alias("mapa"))
    um = df.filter(pl.col("lado_a"))
    print(f"{len(ids)} partidas; {int(df['lado_a'].sum())} estados (um por kill); rounds distintos: {df.select('partida', 'round').unique().height}")
    por_mapa = um.group_by("mapa").agg(pl.col("partida").n_unique().alias("partidas"), pl.len().alias("estados"), pl.struct("partida", "round").n_unique().alias("rounds")).sort("mapa")
    print(por_mapa)
    X0 = atributos(df, "tempo")
    y, g = df["venceu"].to_numpy(), df["partida"].to_numpy()
    ct = df["ct"].to_numpy()
    mapas = sorted(set(mapa.values()))
    M = np.column_stack([(df["mapa"] == m).to_numpy().astype(float) * (2 * ct - 1) for m in mapas])   # efeito do mapa a favor do CT (sinal troca no TR)
    modelos = {"logística atual (tempo)": X0, "logística + lado×mapa": np.column_stack([X0, M])}
    previsoes = {}
    for nome, X in modelos.items():
        p = np.zeros(len(y))
        for tr, te in GroupKFold(n_splits=DOBRAS).split(X, y, g):
            p[te] = LogisticRegression(max_iter=3000).fit(X[tr], y[tr]).predict_proba(X[te])[:, 1]
        previsoes[nome] = p
    # tabela suavizada: (vivos_meu, vivos_dele, bomba, ct) encolhida para a taxa do lado (K = 20)
    K = 20.0
    chave = list(zip(df["vivos_meu"].to_list(), df["vivos_dele"].to_list(), df["bomba"].to_list(), df["ct"].to_list()))
    p = np.zeros(len(y))
    for tr, te in GroupKFold(n_splits=DOBRAS).split(X0, y, g):
        soma, n = {}, {}
        base = {c: y[tr][ct[tr] == c].mean() for c in (0.0, 1.0)}
        for i in tr:
            soma[chave[i]] = soma.get(chave[i], 0) + y[i]; n[chave[i]] = n.get(chave[i], 0) + 1
        for i in te:
            b = base[chave[i][3]]; ni = n.get(chave[i], 0)
            p[i] = (soma.get(chave[i], 0) + K * b) / (ni + K)
    previsoes["tabela suavizada (vivos×vivos×bomba×lado, K=20)"] = p
    print("\n| modelo | Brier | log-loss | AUC |\n|---|---|---|---|")
    for nome, pr in previsoes.items():
        r = mede(df, pr)
        print(f"| {nome} | {r['brier']} | {r['log_loss']} | {r['auc']} |")
    print("\nconfiabilidade (previsto médio → observado) da logística atual: " + "; ".join(f"{a} n={n}: {b}→{c}" for a, n, b, c in mede(df, previsoes['logística atual (tempo)'])['confiabilidade']))
    # o mapa: taxa de vitória do CT por mapa (de todo kill-estado seria ruído: usa a taxa de rounds)
    rr = um.group_by(["mapa", "partida", "round"]).agg(pl.col("venceu").first(), pl.col("ct").first()).with_columns(((pl.col("venceu") == 1) == (pl.col("ct") == 1)).alias("ct_venceu"))
    print("\nrounds com kill e taxa de vitória do CT por mapa (aprox.; o time A pode ser CT ou TR, ver `ct` do lado A):")
    print(rr.group_by("mapa").agg(pl.len().alias("rounds"), pl.col("ct_venceu").mean().round(3).alias("ct")).sort("mapa"))


if __name__ == "__main__":
    main()
