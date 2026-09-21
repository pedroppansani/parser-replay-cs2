"""
Candidatos a IGL por time, ranqueados por PROXIES -- material para o Pedro
decidir, NUNCA atribuição (decisão 7g do CLAUDE.md).

    py -3.12 -m scripts.igl_candidatos

CONFIANÇA BAIXA, e por construção: quem chama o time não deixa rastro direto no
demo. O áudio existe nas demos de FACEIT, mas as profissionais foram apagadas e
tempo de fala já se mostrou enganoso (o astro falava mais que o capitão). O
que sobra são comportamentos que a definição de IGL sugere -- "controla a
economia do time", "passa as calls" (e portanto joga onde enxerga o round) --
e nenhum deles é exclusivo do IGL: o suporte também dropa, também joga atrás.

Proxies, cada um comparado DENTRO do time (posto 1 = o mais IGL do time):
  doa_arma        rounds em que gastou pelo menos DROP_MIN a mais do que ganhou
                  em equipamento (comprou para outro), por round
  compra_menos    rounds jogados com equipamento bem abaixo do time, por round
  contato_tardio  mediana do tempo até o primeiro contato (joga atrás)
  utility         granadas por round
  impacto_baixo   rating do time (o menor fica em 1): folclore do cenário,
                  incluído para ser testado, não por ser confiável

O time é o mesmo elenco em várias partidas: a média dos postos junta as
partidas, e é essa média que ranqueia. Este script NÃO escreve em
roles_manual.json nem em arquivo nenhum -- há teste travando.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import polars as pl

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from metrics.identidade import com_nome_de_exibicao  # noqa: E402

PROCESSED = PROJECT_ROOT / "data" / "processed"
INTERIM = PROJECT_ROOT / "data" / "interim"
MANIFESTO = PROJECT_ROOT / "data" / "manifest.json"

# Gasto acima do próprio ganho de equipamento que caracteriza drop. 1.500 é o
# preço das armas que se dropa (SMG de 1.050-1.500, rifles de 1.800 para
# cima); abaixo disso a diferença é recompra de colete e granada.
DROP_MIN = 1500

# Com menos partidas que isto, o time aparece, mas marcado: um posto médio de
# uma partida só é uma partida só.
MIN_PARTIDAS_TIME = 3

PROXIES = {
    # proxy: (coluna, True se valor ALTO é o lado IGL, descrição)
    "doa_arma": ("doa_por_round", True, "rounds doando arma, por round"),
    "compra_menos": ("compra_menos_share", True, "rounds com bem menos equipamento que o time"),
    "contato_tardio": ("mediana_contato_s", True, "mediana do tempo até o 1º contato (s)"),
    "utility": ("granadas_por_round", True, "granadas por round"),
    "impacto_baixo": ("rating", False, "rating na partida"),
}


def _time_normalizado(nome: str) -> str:
    """"Team Vitality" e "Vitality" são o mesmo time no manifesto."""
    n = (nome or "").strip()
    return n[5:] if n.lower().startswith("team ") else n


def drops_da_partida(match_id: str) -> pl.DataFrame:
    """(jogador) -> rounds em que comprou para outro (gasto - ganho >= DROP_MIN)."""
    compra = pl.read_parquet(INTERIM / match_id / "compra.parquet")
    rounds = pl.read_parquet(PROCESSED / match_id / "rounds.parquet")
    ticks = pl.read_parquet(INTERIM / match_id / "ticks.parquet",
                            columns=["tick", "round_num", "steamid", "is_alive", "current_equip_value"])
    # o que ele levou do round anterior: o equipamento no fim, se estava vivo
    fim = (ticks.join(rounds.select("round_num", "end"), on="round_num")
           .filter(pl.col("tick") <= pl.col("end")).sort("tick").group_by("round_num", "steamid", maintain_order=True).last()
           .select((pl.col("round_num") + 1).cast(compra.schema["round_num"]).alias("round_num"), "steamid",
                   pl.when(pl.col("is_alive")).then(pl.col("current_equip_value")).otherwise(0).alias("guardado")))
    x = (compra.join(fim, on=["round_num", "steamid"], how="left")
         .with_columns(pl.col("guardado").fill_null(0))
         .with_columns((pl.col("cash_spent_this_round").cast(pl.Int64)
                        - (pl.col("current_equip_value").cast(pl.Int64) - pl.col("guardado").cast(pl.Int64))).alias("doado")))
    return x.group_by("steamid", maintain_order=True).agg(
        pl.len().alias("rounds_compra"), (pl.col("doado") >= DROP_MIN).sum().alias("rounds_doando"))


def sinais() -> pl.DataFrame:
    """Uma linha por (partida, jogador) com os proxies em unidade crua."""
    man = json.loads(MANIFESTO.read_text(encoding="utf-8"))["partidas"]
    linhas = []
    for d in sorted(PROCESSED.glob("match_*")):
        mid = d.name
        info = man.get(mid, {})
        if info.get("origem") != "profissional" or not (INTERIM / mid / "compra.parquet").exists():
            continue
        time_de = {n: _time_normalizado(info["times"][t]["nome"]) for t in ("A", "B") for n in info["times"][t]["jogadores"]}
        funcoes = pl.read_parquet(d / "player_roles.parquet")
        papeis = pl.read_parquet(d / "archetypes_summary.parquet")
        ins = json.loads((d / "insights.json").read_text(encoding="utf-8"))
        rating = {p["steamid"]: p.get("rating") for p in ins["players"]}
        drops = dict((r["steamid"], r) for r in drops_da_partida(mid).iter_rows(named=True))
        eco = {r["steamid"]: r for r in papeis.iter_rows(named=True)}
        for f in funcoes.iter_rows(named=True):
            sid = f["steamid"]
            dr, pa = drops.get(sid, {}), eco.get(sid, {})
            linhas.append({
                "match_id": mid, "time": time_de.get(f["name"]), "nome": f["name"], "steamid": sid,
                "doa_por_round": (dr.get("rounds_doando", 0) / dr["rounds_compra"]) if dr.get("rounds_compra") else None,
                "rounds_doando": dr.get("rounds_doando"),
                "compra_menos_share": (pa.get("eco_sacrifice_rounds", 0) / pa["rounds_played"]) if pa.get("rounds_played") else None,
                "mediana_contato_s": f.get("median_first_contact_s"),
                "granadas_por_round": f.get("nades_per_round"),
                "rating": rating.get(sid),
            })
    df = pl.DataFrame(linhas, infer_schema_length=None).drop_nulls("time")
    # identidade é o steamid (metrics/identidade.py): o nick muda entre partidas
    return com_nome_de_exibicao(df.rename({"nome": "name"})).rename({"name": "nome"})


def postos(s: pl.DataFrame) -> pl.DataFrame:
    """Posto de cada proxy dentro do (partida, time), em fração: 0 = o mais IGL, 1 = o menos."""
    out = s
    for nome, (col, alto, _) in PROXIES.items():
        out = out.with_columns(
            ((pl.col(col).rank("average", descending=alto).over(["match_id", "time"]) - 1)
             / (pl.len().over(["match_id", "time"]) - 1)).alias(f"posto_{nome}"))
    cols = [f"posto_{n}" for n in PROXIES]
    return out.with_columns(pl.mean_horizontal(cols).alias("posto_medio"))


def ranking(s: pl.DataFrame) -> pl.DataFrame:
    """Por (time, jogador): média de cada posto e dos valores crus nas partidas."""
    p = postos(s)
    ag = [pl.len().alias("partidas"), pl.col("posto_medio").mean()]
    ag += [pl.col(f"posto_{n}").mean() for n in PROXIES]
    ag += [pl.col(PROXIES[n][0]).mean() for n in PROXIES]
    return (p.group_by("time", "steamid", maintain_order=True).agg(pl.col("nome").last().alias("nome"), *ag)
            .drop("steamid").sort(["time", "posto_medio"]))


def main() -> None:
    r = ranking(sinais())
    print("CANDIDATOS A IGL -- CONFIANÇA BAIXA. Proxies de comportamento, não evidência de quem chama.")
    print("Posto 0,00 = o mais IGL do time naquele proxy; 1,00 = o menos. Nada foi gravado.\n")
    for (time,), g in r.group_by("time", maintain_order=True):
        n_part = int(g["partidas"].max())
        aviso = "" if n_part >= MIN_PARTIDAS_TIME else f"  (só {n_part} partida(s) -- amostra fraca)"
        print(f"== {time} -- {n_part} partidas{aviso}")
        for i, row in enumerate(g.head(3).iter_rows(named=True), 1):
            partes = ", ".join(
                f"{PROXIES[n][2]} {row[PROXIES[n][0]]:.2f} (posto {row[f'posto_{n}']:.2f})"
                for n in PROXIES if row[PROXIES[n][0]] is not None)
            print(f"  {i}. {row['nome']:<12} posto médio {row['posto_medio']:.2f} -- {partes}")
        print()


if __name__ == "__main__":
    main()
