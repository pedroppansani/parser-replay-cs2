"""O modelo de chance de round do Round Swing, medido FORA DA DOBRA.

O AUC e o Brier gravados em `rating_reference.json` são medidos no TREINO, com
duas linhas por evento (uma por lado, espelhadas e correlacionadas). Aqui a
medida é por validação cruzada AGRUPADA POR PARTIDA (GroupKFold): nenhuma
partida aparece dos dois lados da divisão, e cada evento conta uma vez (o lado
A; o lado B é o complemento).

Compara o modelo atual com candidatos mais ricos, do mesmo jeito:
  atual      diferença de vivos, diferença de equipamento, bomba, lado
  vivos      + os vivos de cada lado (5v4, 2v1 e 1v0 deixam de ser o mesmo estado)
  tempo      + o tempo restante (do round antes do plant, da bomba depois)

Uso:
    py -3.12 -m scripts.valida_modelo_de_round
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import polars as pl

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))
from metrics.rating import grupo_do_round  # noqa: E402
from scripts.fit_rating import carrega_partida, partidas_disponiveis  # noqa: E402

TICKRATE = 64
TEMPO_DO_ROUND_S = 115.0          # relógio do round no competitivo (1:55)
TEMPO_DA_BOMBA_S = 40.0           # a mesma constante que metrics/timing.py usa para achar o tickrate
DOBRAS = 10


def amostras(mid: str) -> pl.DataFrame:
    """Uma linha por (kill, lado): o estado DEPOIS da kill e se aquele lado venceu o round."""
    tabelas, team_of, vencedor, _ = carrega_partida(mid)
    rounds, kills = tabelas["rounds"], tabelas["kills"]
    grupos = grupo_do_round(tabelas["ticks"], rounds)
    eq = (grupos.with_columns(pl.col("steamid").map_elements(lambda s: team_of.get(s), return_dtype=pl.String).alias("time"))
          .drop_nulls("time").group_by(["round_num", "time"], maintain_order=True)
          .agg(pl.col("equip").sum().alias("equip"), pl.col("side").mode().sort().first()))
    equip = {(int(r["round_num"]), r["time"]): (float(r["equip"]), r["side"]) for r in eq.iter_rows(named=True)}
    info = {int(r["round_num"]): r for r in rounds.iter_rows(named=True)}
    linhas = []
    for rn_t, rk in kills.sort("tick").group_by("round_num", maintain_order=True):
        rn = int(rn_t[0])
        venc = vencedor.get(rn)
        if venc is None or rn not in info:
            continue
        vivos = {"A": 5, "B": 5}
        plant, inicio = info[rn]["bomb_plant"], info[rn]["freeze_end"]
        for k in rk.iter_rows(named=True):
            tv = team_of.get(k["victim_steamid"])
            if tv is None:
                continue
            vivos[tv] -= 1
            plantada = plant is not None and k["tick"] >= int(plant)
            decorrido = max(0.0, (k["tick"] - int(inicio)) / TICKRATE)
            da_bomba = max(0.0, (k["tick"] - int(plant)) / TICKRATE) if plantada else 0.0
            for time in ("A", "B"):
                outro = "B" if time == "A" else "A"
                if (rn, time) not in equip or (rn, outro) not in equip:
                    continue
                meu, lado = equip[(rn, time)]
                dele, _ = equip[(rn, outro)]
                ct = lado == "ct"
                linhas.append({
                    "partida": mid, "round": rn, "lado_a": time == "A",
                    "vivos_meu": vivos[time], "vivos_dele": vivos[outro],
                    "dif_vivos": vivos[time] - vivos[outro], "dif_equip": (meu - dele) / 1000.0,
                    "bomba": (0.0 if not plantada else (-1.0 if ct else 1.0)), "ct": 1.0 if ct else 0.0,
                    # o tempo joga a favor do CT antes do plant e a favor do TR depois
                    "tempo_do_round": 0.0 if plantada else min(1.0, decorrido / TEMPO_DO_ROUND_S) * (1.0 if ct else -1.0),
                    "tempo_da_bomba": min(1.0, da_bomba / TEMPO_DA_BOMBA_S) * (-1.0 if ct else 1.0) if plantada else 0.0,
                    "venceu": int(venc == time),
                })
    return pl.DataFrame(linhas)


def atributos(df: pl.DataFrame, modelo: str) -> np.ndarray:
    base = ["dif_vivos", "dif_equip", "bomba", "ct"]
    if modelo == "atual":
        return df.select(base).to_numpy()
    total = (df["vivos_meu"] + df["vivos_dele"]).to_numpy().astype(float)
    razao = np.where(total > 0, df["dif_vivos"].to_numpy() / np.maximum(total, 1.0), 0.0)
    extra = [razao, (df["vivos_meu"] == 0).to_numpy().astype(float) - (df["vivos_dele"] == 0).to_numpy().astype(float)]
    if modelo == "tempo":
        extra += [df["tempo_do_round"].to_numpy(), df["tempo_da_bomba"].to_numpy()]
    return np.column_stack([df.select(base).to_numpy()] + extra)


def fora_da_dobra(df: pl.DataFrame, modelo: str) -> np.ndarray:
    from sklearn.linear_model import LogisticRegression
    from sklearn.model_selection import GroupKFold

    X, y, g = atributos(df, modelo), df["venceu"].to_numpy(), df["partida"].to_numpy()
    p = np.zeros(len(y))
    for treino, teste in GroupKFold(n_splits=DOBRAS).split(X, y, g):
        p[teste] = LogisticRegression(max_iter=2000).fit(X[treino], y[treino]).predict_proba(X[teste])[:, 1]
    return p


def mede(df: pl.DataFrame, p: np.ndarray) -> dict:
    from sklearn.metrics import brier_score_loss, log_loss, roc_auc_score
    um = df["lado_a"].to_numpy()                       # um lado por evento: o outro é o complemento
    y, q = df["venceu"].to_numpy()[um], np.clip(p[um], 1e-6, 1 - 1e-6)
    faixas = np.minimum((q * 10).astype(int), 9)
    confiabilidade = [(f"{k / 10:.1f}-{(k + 1) / 10:.1f}", int((faixas == k).sum()),
                       round(float(q[faixas == k].mean()), 3), round(float(y[faixas == k].mean()), 3))
                      for k in range(10) if (faixas == k).any()]
    return {"eventos": int(um.sum()), "brier": round(float(brier_score_loss(y, q)), 4),
            "log_loss": round(float(log_loss(y, q)), 4), "auc": round(float(roc_auc_score(y, q)), 4),
            "confiabilidade": confiabilidade}


def por_estado(df: pl.DataFrame, previsoes: dict[str, np.ndarray]) -> pl.DataFrame:
    """Por estado de vivos (do lado A): n, taxa observada e a prevista por cada modelo."""
    d = df.with_columns(*[pl.Series(f"p_{m}", p) for m, p in previsoes.items()]).filter(pl.col("lado_a"))
    return (d.group_by(["vivos_meu", "vivos_dele"], maintain_order=True)
            .agg(pl.len().alias("n"), pl.col("venceu").mean().round(3).alias("observado"),
                 *[pl.col(f"p_{m}").mean().round(3).alias(m) for m in previsoes])
            .sort(["vivos_meu", "vivos_dele"], descending=True))


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    df = pl.concat([amostras(m) for m in partidas_disponiveis()])
    print(f"{df['partida'].n_unique()} partidas, {int(df['lado_a'].sum())} eventos (kills com round decidível), "
          f"validação cruzada agrupada por partida em {DOBRAS} dobras\n")
    previsoes, medidas = {}, {}
    for m in ("atual", "vivos", "tempo"):
        previsoes[m] = fora_da_dobra(df, m)
        medidas[m] = mede(df, previsoes[m])
    print("| modelo | Brier | log-loss | AUC |\n|---|---|---|---|")
    for m, r in medidas.items():
        print(f"| {m} | {r['brier']} | {r['log_loss']} | {r['auc']} |")
    for m, r in medidas.items():
        print(f"\nconfiabilidade fora da dobra, modelo {m} (faixa prevista, n, previsto médio, observado):")
        for linha in r["confiabilidade"]:
            print("  ", linha)
    with pl.Config(tbl_rows=40):
        print("\npor estado de vivos (meu x dele): n, observado e previsto por modelo")
        print(por_estado(df, previsoes))


if __name__ == "__main__":
    main()
