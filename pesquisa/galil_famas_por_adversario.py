"""Galil ou FAMAS com colete (rifle_t2|colete, grupo "força" da decisão 8i): a vitória separada pelo grupo de
compra do ADVERSÁRIO naquele round (eco, pistola, força ou compra cheia), com os rounds em cada célula.

Pergunta do Pedro (fase 17): os 61% dessa linha vêm da força da compra ou de ela costumar enfrentar o eco do
outro time (o time que ganhou a pistola e joga contra o eco)? Só mede; não muda classificação nem número
publicado, e não vira página. A fonte é a mesma da tabela da 8i: `scripts.fit_economia.confrontos_do_corpus`
(um registro por round, time, classe dele e classe do adversário, com o peso do EMPATE DIVIDIDO da 8i) e o
grupo de compra de `metrics.economia.grupo_de_compra`. Rounds são time-rounds com o peso do empate (por isso
há frações). Nota: `notas/investigacoes/2026-10-15-galil-famas-por-adversario.md`.

SAÍDA FIXADA: `pesquisa/galil_famas_por_adversario.json`, gravada com a versão das métricas abaixo.
`--confere` refaz a tabela a partir do interim e falha se ela não bater com a gravada.

Uso:
    py -3.12 -m pesquisa.galil_famas_por_adversario            # imprime
    py -3.12 -m pesquisa.galil_famas_por_adversario --grava    # regrava a saída fixada
    py -3.12 -m pesquisa.galil_famas_por_adversario --confere  # confere contra a saída fixada
"""
from __future__ import annotations

# Versão das métricas (parsing/versao.py) com que a saída fixada foi gravada.
VERSAO_DAS_METRICAS_DA_SAIDA = 24

import json  # noqa: E402
import sys  # noqa: E402
from pathlib import Path  # noqa: E402

import polars as pl  # noqa: E402

from metrics.economia import grupo_de_compra  # noqa: E402

SAIDA_FIXADA = Path(__file__).with_suffix(".json")
ROTULO = {"eco": "eco", "pistola": "pistola", "forca": "força", "cheia": "compra cheia"}
ORDEM = ("eco", "pistola", "forca", "cheia")
# classe da 8i (com colete) -> nome na saída
CLASSES = {"rifle_t2": "Galil ou FAMAS com colete (rifle_t2, força)",
           "rifle_t1": "rifle de primeira linha com colete (rifle_t1, compra cheia), para comparar"}
CASAS = 4  # arredondamento gravado (rounds com o peso do empate e taxa)


def tabela(conf: pl.DataFrame, grupo: str = "rifle_t2") -> list[dict]:
    """Vitória da classe `grupo` com colete por grupo do adversário (os quatro, mesmo vazios) e o total:
    rounds (soma dos pesos), vitórias (soma ponderada) e taxa."""
    gal = conf.filter((pl.col("grupo") == grupo) & pl.col("colete")).with_columns(
        pl.struct(["grupo_dele", "colete_dele"]).map_elements(
            lambda r: grupo_de_compra(r["grupo_dele"], r["colete_dele"]), return_dtype=pl.Utf8).alias("adversario"))
    soma = {g: [0.0, 0.0] for g in ORDEM}
    for r in gal.iter_rows(named=True):
        soma[r["adversario"]][0] += r["peso"]
        soma[r["adversario"]][1] += r["peso"] * float(r["venceu"])
    linhas = [{"adversario": g, "rounds": n, "vitorias": v} for g, (n, v) in soma.items()]
    linhas.append({"adversario": "total", "rounds": sum(n for n, _ in soma.values()),
                   "vitorias": sum(v for _, v in soma.values())})
    return [{"adversario": x["adversario"], "rounds": round(x["rounds"], CASAS), "vitorias": round(x["vitorias"], CASAS),
             "vitoria": round(x["vitorias"] / x["rounds"], CASAS) if x["rounds"] else None} for x in linhas]


def calcula() -> dict:
    from scripts.fit_economia import confrontos_do_corpus
    conf = confrontos_do_corpus()
    return {"versao_das_metricas": VERSAO_DAS_METRICAS_DA_SAIDA, "partidas": conf["match_id"].n_unique(),
            "tabelas": {g: tabela(conf, g) for g in CLASSES}}


def _br(x: float) -> str:
    return f"{x:.1f}".replace(".", ",")


def imprime(saida: dict) -> None:
    print(f"{saida['partidas']} partidas; versão das métricas {saida['versao_das_metricas']}")
    for g, linhas in saida["tabelas"].items():
        total = linhas[-1]["rounds"]
        print(f"\n{CLASSES[g]}, por grupo do adversário\n")
        print("| grupo do adversário | rounds | vitórias | fração dos rounds | vitória |")
        print("|---|---|---|---|---|")
        for r in linhas:
            nome = "**total**" if r["adversario"] == "total" else ROTULO[r["adversario"]]
            taxa = f"{r['vitoria']:.0%}" if r["vitoria"] is not None else "sem rounds"
            print(f"| {nome} | {_br(r['rounds'])} | {_br(r['vitorias'])} | {r['rounds'] / total:.0%} | {taxa} |")


def main(argv: list[str]) -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    from parsing.versao import VERSAO_DAS_METRICAS
    if VERSAO_DAS_METRICAS != VERSAO_DAS_METRICAS_DA_SAIDA:
        print(f"AVISO: o código está na versão das métricas {VERSAO_DAS_METRICAS}; a saída fixada é da "
              f"{VERSAO_DAS_METRICAS_DA_SAIDA}.")
    saida = calcula()
    imprime(saida)
    if "--grava" in argv:
        SAIDA_FIXADA.write_text(json.dumps(saida, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        print(f"\nsaída fixada gravada em {SAIDA_FIXADA}")
    elif "--confere" in argv:
        gravada = json.loads(SAIDA_FIXADA.read_text(encoding="utf-8"))
        if gravada != saida:
            print(f"\nDIFERENTE da saída fixada em {SAIDA_FIXADA}")
            return 1
        print(f"\nidêntica à saída fixada em {SAIDA_FIXADA}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
