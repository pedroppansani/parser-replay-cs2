"""
Ajusta a tabela de economia do rating no corpus inteiro (metrics/economia.py).

Mesmo padrão das outras referências (decisão 16): refaça sempre que processar
demo nova. Imprime a comparação com os dois pontos que a HLTV publicou.

Uso:
    py -3.12 -m scripts.fit_economia
"""
from __future__ import annotations

import json
from pathlib import Path

import polars as pl

from metrics.economia import (
    MIN_AMOSTRA_CELULA, REFERENCIA_ECONOMIA, ajusta_tabela, confrontos_da_partida,
)
from metrics.sides import side_of_team
from scripts.build_insights import resolve_teams

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Os dois pontos publicados pela HLTV, no lado TR (ver metrics/rating.py).
PONTOS_HLTV = {"rifle x rifle": 0.48, "matar pistola inicial": 0.75}


def confrontos_do_corpus() -> pl.DataFrame:
    partes = []
    for d in sorted((PROJECT_ROOT / "data" / "interim").glob("match_*")):
        if "__" in d.name or not (d / "compra.parquet").exists():
            continue
        rounds = pl.read_parquet(PROJECT_ROOT / "data" / "processed" / d.name / "rounds.parquet")
        ticks = pl.read_parquet(d / "ticks.parquet", columns=["round_num", "tick", "steamid", "name", "side"])
        team_of, _ = resolve_teams(ticks)
        venc = {int(r["round_num"]): ("A" if r["winner"] == side_of_team("A", int(r["round_num"])) else "B")
                for r in rounds.iter_rows(named=True)}
        c = confrontos_da_partida(pl.read_parquet(d / "compra.parquet"), team_of, venc)
        if c.height:
            partes.append(c.with_columns(pl.lit(d.name).alias("match_id")))
    return pl.concat(partes)


def main() -> None:
    conf = confrontos_do_corpus()
    tabela = ajusta_tabela(conf)
    # o arquivo diz de que código saiu: é o que permite conferir depois que ele
    # é reprodutível (tests/test_economia_reprodutivel.py)
    from parsing.versao import versoes
    v = versoes()
    tabela["gerada_por"] = {"comando": "py -3.12 -m scripts.fit_economia", "commit": v["commit"], "sujo": v["sujo"],
                            "partidas": conf["match_id"].n_unique()}
    REFERENCIA_ECONOMIA.write_text(json.dumps(tabela, ensure_ascii=False, indent=2), encoding="utf-8")
    cel = tabela["celulas"]
    fracas = sum(1 for v in cel.values() if v["amostra_fraca"])
    print(f"{tabela['lados_round']} lados-round; {len(cel)} células com colete, "
          f"{fracas} com menos de {MIN_AMOSTRA_CELULA} casos (encolhidas para o nível de cima)")
    print("taxa base por lado:", {k: round(v, 3) for k, v in tabela["taxa_base_por_lado"].items()})
    t = conf.filter(pl.col("lado") == "t")

    def taxa(x: pl.DataFrame) -> tuple[float, float]:
        """(taxa de vitória ponderada pelo peso do empate, casos = soma dos pesos)."""
        n = float(x["peso"].sum())
        return (float((x["venceu"].cast(pl.Float64) * x["peso"]).sum() / n) if n else 0.0), n

    rr = t.filter(pl.col("grupo").is_in(["rifle_t1", "rifle_t2"]) & pl.col("grupo_dele").is_in(["rifle_t1", "rifle_t2"]))
    print(f"\nHLTV rifle x rifle (TR) {PONTOS_HLTV['rifle x rifle']:.0%}  | corpus {taxa(rr)[0]:.1%} ({taxa(rr)[1]:.1f} casos)")
    for rot, filtro in (("pistola inicial sem colete", (pl.col("grupo_dele") == "pistola_inicial") & ~pl.col("colete_dele")),
                        ("pistola inicial (qualquer)", pl.col("grupo_dele") == "pistola_inicial"),
                        ("qualquer pistola", pl.col("grupo_dele").is_in(["pistola_inicial", "pistola_melhorada"]))):
        x = t.filter(pl.col("grupo").is_in(["rifle_t1", "rifle_t2"]) & filtro)
        print(f"HLTV matar pistola inicial (TR) {PONTOS_HLTV['matar pistola inicial']:.0%}  | corpus, TR de rifle contra "
              f"{rot}: {taxa(x)[0]:.1%} ({taxa(x)[1]:.1f} casos)")
    print(f"\nTabela gravada em {REFERENCIA_ECONOMIA}")


if __name__ == "__main__":
    main()
