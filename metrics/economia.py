"""
Ajuste de economia do rating: taxa de vitória de cada confronto de equipamento,
estimada NO CORPUS INTEIRO.

POR QUE MUDOU
-------------
A versão anterior estimava as taxas dentro de cada partida: ~20 rounds
espalhados por dezenas de células, quase todas vazias ou com 1 a 3 casos, e o
encolhimento puxava tudo para a média -- na prática o ajuste de economia mal
agia. No corpus (52 partidas, 2.304 lados-round) as células principais têm
centenas de casos.

A CLASSE DE EQUIPAMENTO: arma mais cara + colete
------------------------------------------------
Como a HLTV define ("colete + arma mais cara"), lida da COMPRA no fim do freeze
time (`compra.parquet`), e não da arma na mão num tick qualquer. O colete não é
detalhe: medido no corpus, time de pistola inicial SEM colete vence 4% (CT) e
10% (TR) dos rounds; COM colete, 51% e 49% -- sem separar, eco total e round de
pistola caem no mesmo grupo.

O grupo de um TIME no round é a moda dos cinco (é assim que se fala de
economia: "eles estão de rifle"); o colete do time é o da maioria.

ENCOLHIMENTO EM DOIS NÍVEIS
---------------------------
Célula (lado, classe minha, classe dele) com poucos casos encolhe na direção da
mesma célula SEM o colete (lado, grupo meu, grupo dele), que por sua vez encolhe
na direção da taxa do lado. `n` casos pesam n / (n + K) contra o nível de cima.
Assim uma célula vista 3 vezes não vira "100% de vitória", e a informação do
colete só entra onde há amostra para ela.
"""
from __future__ import annotations

import json
from pathlib import Path

import polars as pl

from metrics.sides import side_of_team

REFERENCIA_ECONOMIA = Path(__file__).resolve().parent / "economia_reference.json"

# Casos que uma célula precisa para valer METADE do próprio peso contra o nível
# de cima. O mesmo K = 20 da versão por partida: abaixo disso a frequência de
# uma célula é mais ruído que sinal (um confronto visto 5 vezes com 4 vitórias
# não diz que a taxa é 80%).
K_ENCOLHIMENTO = 20.0

# Células com menos casos que isto aparecem marcadas como amostra fraca no
# relatório -- a taxa delas é quase só a do nível de cima.
MIN_AMOSTRA_CELULA = 20


def classe(grupo: str, colete: bool) -> str:
    return f"{grupo}|{'colete' if colete else 'sem_colete'}"


def compra_por_jogador(compra: pl.DataFrame) -> pl.DataFrame:
    """(round, jogador) -> grupo da arma mais cara do inventário e colete."""
    from metrics.rating import ARMA_PARA_GRUPO, FORCA_DO_GRUPO

    linhas = []
    for r in compra.iter_rows(named=True):
        grupos = [ARMA_PARA_GRUPO[a] for a in (r["inventory"] or []) if a in ARMA_PARA_GRUPO]
        if not grupos:
            continue
        g = max(grupos, key=lambda x: FORCA_DO_GRUPO[x])
        linhas.append({"round_num": int(r["round_num"]), "steamid": int(r["steamid"]), "grupo": g,
                       "colete": bool((r["armor_value"] or 0) > 0)})
    if not linhas:
        return pl.DataFrame(schema={"round_num": pl.Int64, "steamid": pl.UInt64, "grupo": pl.Utf8, "colete": pl.Boolean})
    return pl.DataFrame(linhas).with_columns(pl.col("steamid").cast(pl.UInt64))


def confrontos_da_partida(compra: pl.DataFrame, team_of: dict[int, str],
                          vencedor_por_round: dict[int, str]) -> pl.DataFrame:
    """Um registro por (round, time): lado, classe dele, classe do adversário, venceu."""
    j = compra_por_jogador(compra).with_columns(
        pl.col("steamid").map_elements(lambda s: team_of.get(int(s)), return_dtype=pl.Utf8).alias("time")
    ).drop_nulls("time")
    por_time = j.group_by(["round_num", "time"]).agg(
        pl.col("grupo").mode().first(), (pl.col("colete").mean() >= 0.5).alias("colete"))
    linhas = []
    for (rn,), g in por_time.group_by("round_num"):
        if g.height != 2:
            continue
        a, b = g.row(0, named=True), g.row(1, named=True)
        for eu, ele in ((a, b), (b, a)):
            linhas.append({
                "round_num": int(rn), "lado": side_of_team(eu["time"], int(rn)),
                "grupo": eu["grupo"], "colete": eu["colete"],
                "grupo_dele": ele["grupo"], "colete_dele": ele["colete"],
                "venceu": vencedor_por_round.get(int(rn)) == eu["time"],
            })
    return pl.DataFrame(linhas) if linhas else pl.DataFrame()


def ajusta_tabela(confrontos: pl.DataFrame) -> dict:
    """Taxas encolhidas por célula, a partir dos confrontos do corpus inteiro."""
    base = {lado: float(t) for lado, t in confrontos.group_by("lado").agg(pl.col("venceu").mean()).iter_rows()}

    pai = {}
    for r in confrontos.group_by(["lado", "grupo", "grupo_dele"]).agg(
            pl.len().alias("n"), pl.col("venceu").mean().alias("taxa")).iter_rows(named=True):
        w = r["n"] / (r["n"] + K_ENCOLHIMENTO)
        pai[(r["lado"], r["grupo"], r["grupo_dele"])] = {
            "n": int(r["n"]), "taxa_crua": float(r["taxa"]),
            "taxa": w * float(r["taxa"]) + (1 - w) * base[r["lado"]],
        }

    celulas = {}
    for r in confrontos.group_by(["lado", "grupo", "colete", "grupo_dele", "colete_dele"]).agg(
            pl.len().alias("n"), pl.col("venceu").mean().alias("taxa")).iter_rows(named=True):
        acima = pai[(r["lado"], r["grupo"], r["grupo_dele"])]["taxa"]
        w = r["n"] / (r["n"] + K_ENCOLHIMENTO)
        chave = "||".join([r["lado"], classe(r["grupo"], r["colete"]), classe(r["grupo_dele"], r["colete_dele"])])
        celulas[chave] = {"n": int(r["n"]), "taxa_crua": round(float(r["taxa"]), 4),
                          "taxa": round(w * float(r["taxa"]) + (1 - w) * acima, 4),
                          "amostra_fraca": int(r["n"]) < MIN_AMOSTRA_CELULA}
    return {
        "taxa_base_por_lado": base,
        "celulas_sem_colete": {"||".join(k): {**v, "taxa": round(v["taxa"], 4), "taxa_crua": round(v["taxa_crua"], 4)}
                               for k, v in pai.items()},
        "celulas": celulas,
        "lados_round": confrontos.height,
        "k_encolhimento": K_ENCOLHIMENTO,
    }


def carrega_tabela() -> dict | None:
    if not REFERENCIA_ECONOMIA.exists():
        return None
    return json.loads(REFERENCIA_ECONOMIA.read_text(encoding="utf-8"))


def celulas_para_o_rating(tabela: dict) -> dict:
    """No formato que o rating consulta: (lado, classe minha, classe dele) -> {taxa, n}.

    Classe ausente na tabela com colete cai na célula sem colete, que cai na
    taxa do lado -- nunca num peso inventado.
    """
    out = {}
    for chave, v in tabela["celulas"].items():
        lado, meu, dele = chave.split("||")
        out[(lado, meu, dele)] = v
    for chave, v in tabela["celulas_sem_colete"].items():
        lado, meu, dele = chave.split("||")
        out.setdefault((lado, meu, dele), v)
    return out
