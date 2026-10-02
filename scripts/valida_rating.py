"""Validação HONESTA do rating: tudo reajustado sem o que é avaliado.

O "deixa uma partida fora" de `fit_rating --fit-pesos` reajusta SÓ os pesos: o
modelo de chance de round, a referência de escala e a tabela de economia viram
todas as partidas, inclusive a avaliada. Aqui, para cada dobra, os QUATRO são
refeitos sem as partidas de fora, e o rating delas é previsto com o que sobrou:

  1. modelo de round    treinado nas amostras das partidas de dentro;
  2. tabela de economia taxas por confronto das partidas de dentro;
  3. referência de escala  médias e desvios dos sub-ratings de dentro;
  4. pesos              regressão não-negativa contra o oficial, só de dentro.

Duas divisões:
  - por PARTIDA: uma de fora por vez;
  - por TIME: todas as partidas de um time de fora (o corpus é de poucos times;
    se o modelo aprendeu o estilo de um deles, é aqui que aparece).

Junto vai o método antigo (só os pesos), medido do mesmo jeito, para comparar.

Uso:
    py -3.12 -m scripts.valida_rating              # mede e imprime
    py -3.12 -m scripts.valida_rating --gravar     # grava metrics/rating_validacao.json
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np
import polars as pl

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))
from metrics.economia import ajusta_tabela, confrontos_da_partida  # noqa: E402
from metrics.rating import PESOS_PROVISORIOS, ModeloDeRound, amostras_de_round, grupo_do_round, rating  # noqa: E402
from scripts.fit_rating import (  # noqa: E402
    _linhas_com_alvo, _times_dos_jogadores, carrega_partida, partidas_disponiveis, referencia_de,
)

SAIDA = RAIZ / "metrics" / "rating_validacao.json"
# o que o rating lê da tabela de ticks (grupo_do_round); o resto pesaria 3x na memória
COLUNAS_DE_TICKS = ["round_num", "tick", "steamid", "name", "side", "active_weapon_name", "current_equip_value"]
NOMES = list(PESOS_PROVISORIOS)
COLUNAS = [f"norm_{n}" for n in NOMES]


class Corpus:
    """As partidas em memória, com o que não depende da dobra já calculado."""

    def __init__(self, ids: list[str]):
        self.ids = ids
        self.partida, self.amostras, self.confrontos, self.nick = {}, {}, {}, {}
        for mid in ids:
            tabelas, team_of, vencedor, kast = carrega_partida(mid)
            ticks = tabelas["ticks"]
            self.nick[mid] = dict(ticks.group_by("steamid", maintain_order=True).agg(pl.col("name").last()).iter_rows())
            tabelas = {**tabelas, "ticks": ticks.select([c for c in COLUNAS_DE_TICKS if c in ticks.columns])}
            self.partida[mid] = (tabelas, team_of, vencedor, kast)
            grupos = grupo_do_round(tabelas["ticks"], tabelas["rounds"])
            self.amostras[mid] = amostras_de_round(tabelas["kills"], tabelas["rounds"], grupos, team_of, vencedor)
            compra = tabelas.get("compra")
            self.confrontos[mid] = (confrontos_da_partida(compra, team_of, vencedor)
                                    if compra is not None and compra.height else pl.DataFrame())

    def modelo(self, dentro: list[str]) -> ModeloDeRound:
        Xs = [self.amostras[m][0] for m in dentro if self.amostras[m][0].shape[0]]
        ys = [self.amostras[m][1] for m in dentro if self.amostras[m][0].shape[0]]
        return ModeloDeRound().treina(np.vstack(Xs), np.concatenate(ys))

    def economia(self, dentro: list[str]) -> dict:
        return ajusta_tabela(pl.concat([self.confrontos[m] for m in dentro if self.confrontos[m].height]))

    def componentes(self, modelo: ModeloDeRound, economia: dict, referencia: dict | None, ids: list[str]) -> pl.DataFrame:
        linhas = []
        for mid in ids:
            tabelas, team_of, vencedor, kast = self.partida[mid]
            _, resumo = rating(tabelas, team_of, vencedor, kast, 64, referencia=referencia, modelo=modelo,
                               tabela_economia=economia)
            for j in resumo["jogadores"]:
                linhas.append({**j, "name": self.nick[mid].get(j["steamid"]), "match_id": mid})
        return pl.DataFrame(linhas, infer_schema_length=None)


def _pesos(X: np.ndarray, y: np.ndarray) -> np.ndarray:
    """Pesos >= 0 com intercepto livre (o mesmo ajuste de fit_rating)."""
    from scipy.optimize import nnls
    uns = np.ones((len(X), 1))
    w, _ = nnls(np.hstack([X, uns, -uns]), y)
    return np.append(w[:-2], w[-2] - w[-1])


def _erro(prev: np.ndarray, real: np.ndarray) -> dict:
    return {"erro_medio": round(float(np.mean(np.abs(prev - real))), 4),
            "correlacao": round(float(np.corrcoef(prev, real)[0, 1]), 4),
            "vies": round(float(np.mean(prev - real)), 4), "n": int(len(real))}


def dobra(corpus: Corpus, fora: list[str]) -> pl.DataFrame:
    """Previsão do rating das partidas `fora`, com tudo ajustado sem elas."""
    dentro = [m for m in corpus.ids if m not in fora]
    modelo, economia = corpus.modelo(dentro), corpus.economia(dentro)
    bruto = corpus.componentes(modelo, economia, None, dentro)                 # sub_* não dependem da referência
    referencia = referencia_de(bruto, modelo, dentro)
    treino = _linhas_com_alvo(corpus.componentes(modelo, economia, referencia, dentro))
    teste = _linhas_com_alvo(corpus.componentes(modelo, economia, referencia, fora))
    w = _pesos(treino.select(COLUNAS).to_numpy(), treino["rating_oficial"].to_numpy())
    return teste.select("match_id", "name", "rating_oficial").with_columns(
        pl.Series("previsto", teste.select(COLUNAS).to_numpy() @ w[:-1] + w[-1]))


def valida(avisa=print) -> dict:
    ids = partidas_disponiveis()
    t0 = time.time()
    corpus = Corpus(ids)
    avisa(f"corpus em memória: {len(ids)} partidas, {time.time() - t0:.0f}s")

    # método antigo (só os pesos), com tudo o mais ajustado no corpus inteiro
    modelo, economia = corpus.modelo(ids), corpus.economia(ids)
    referencia = referencia_de(corpus.componentes(modelo, economia, None, ids), modelo, ids)
    dados = _linhas_com_alvo(corpus.componentes(modelo, economia, referencia, ids))
    real = dados["rating_oficial"].to_numpy()
    com_alvo = sorted(set(dados["match_id"].to_list()))
    X = dados.select(COLUNAS).to_numpy()
    prev = np.zeros(dados.height)
    for mid in com_alvo:
        t = (dados["match_id"] == mid).to_numpy()
        w = _pesos(X[~t], real[~t])
        prev[t] = X[t] @ w[:-1] + w[-1]
    so_pesos = _erro(prev, real)
    avisa(f"só os pesos (método antigo): {so_pesos}")

    # por partida, completo
    partes = []
    for k, mid in enumerate(com_alvo, start=1):
        partes.append(dobra(corpus, [mid]))
        if k % 5 == 0:
            avisa(f"  partida {k}/{len(com_alvo)} ({time.time() - t0:.0f}s)")
    por_partida = pl.concat(partes)
    completo = _erro(por_partida["previsto"].to_numpy(), por_partida["rating_oficial"].to_numpy())
    avisa(f"deixa uma partida fora, completo: {completo}")

    # por time, completo
    time_de = _times_dos_jogadores()
    times_da_partida: dict[str, set] = {}
    for (mid, _nome), t in time_de.items():
        if t:
            times_da_partida.setdefault(mid, set()).add(t)
    times = sorted({t for mid in com_alvo for t in times_da_partida.get(mid, ())})
    por_time, partes = {}, []
    for t in times:
        fora = [m for m in com_alvo if t in times_da_partida.get(m, ())]
        d = dobra(corpus, fora)
        # só os jogadores do TIME de fora: os adversários dele continuam no treino por outras partidas
        d = d.filter(pl.struct(["match_id", "name"]).map_elements(
            lambda r: time_de.get((r["match_id"], r["name"])) == t, return_dtype=pl.Boolean))
        if d.height:
            por_time[t] = {**_erro(d["previsto"].to_numpy(), d["rating_oficial"].to_numpy()), "partidas_de_fora": len(fora)}
            partes.append(d)
            avisa(f"  time {t}: {por_time[t]} ({time.time() - t0:.0f}s)")
    todos = pl.concat(partes)
    time_fora = _erro(todos["previsto"].to_numpy(), todos["rating_oficial"].to_numpy())
    avisa(f"deixa um time fora, completo: {time_fora}")

    return {
        "_leia_isto": ("Gerado por py -3.12 -m scripts.valida_rating --gravar. Erro do rating contra o oficial "
                       "da HLTV com o modelo de round, a economia, a referência e os pesos reajustados SEM o "
                       "que é avaliado."),
        "partidas_com_rating_oficial": len(com_alvo), "jogador_partidas": int(len(real)),
        "so_os_pesos": {**so_pesos, "metodo": "deixa uma partida fora reajustando só os pesos (o método antigo)"},
        "deixa_uma_partida_fora": {**completo, "metodo": "modelo de round, economia, referência e pesos sem a partida avaliada"},
        "deixa_um_time_fora": {**time_fora, "metodo": ("idem, sem NENHUMA partida do time avaliado; o erro é o dos "
                                                       "jogadores desse time"), "por_time": por_time},
    }


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
    # --modelo completo|atual mede com o outro modelo de round sem mexer no código
    import metrics.rating as r
    if "--modelo" in sys.argv:
        r.MODELO_DE_ROUND_COMPLETO = sys.argv[sys.argv.index("--modelo") + 1] == "completo"
    saida = Path(sys.argv[sys.argv.index("--saida") + 1]) if "--saida" in sys.argv else SAIDA
    doc = valida()
    doc["modelo_de_round"] = "completo" if r.MODELO_DE_ROUND_COMPLETO else "quatro entradas"
    if "--gravar" in sys.argv:
        saida.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print("gravado em", saida)
    print(json.dumps({k: v for k, v in doc.items() if k != "_leia_isto"}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
