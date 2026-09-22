"""
Perfil estatístico dos 4 grupos de estilo -- a base para o Pedro nomeá-los.

    py -3.12 -m scripts.proposta_grupos

Nada é gravado. O KMeans não nomeia grupos (decisão 8): este script só mostra
o que DEFINE cada grupo, para que o nome saia de um perfil e não de uma lista
em branco.

ANTES DO PERFIL, A ESTABILIDADE. O modelo em clustering/global_model.json foi
ajustado em 1.870 jogador-rounds (as 9 partidas de FACEIT) e é aplicado ao
corpus inteiro. O número de um grupo no KMeans é arbitrário (decisão 11): se o
modelo for reajustado, "grupo 2" pode passar a ser outra coisa, e o nome dado
hoje apontaria para o grupo errado. Por isso o script reajusta o modelo no
corpus inteiro (sem gravar) e mede:
  - concordância entre as duas atribuições (índice de Rand ajustado: 1 =
    idênticas, 0 = o que o acaso daria);
  - o casamento grupo a grupo (qual grupo novo corresponde a qual antigo, e
    quantos rounds mudam de grupo).
Nome dado a um modelo instável é nome dado a um acidente.

O PERFIL: para cada grupo e cada feature, a média do grupo, a média geral e a
distância em desvios-padrão (z). |z| grande é o que distingue o grupo.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import polars as pl
from scipy.optimize import linear_sum_assignment
from sklearn.metrics import adjusted_rand_score

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from clustering.playstyle import assign_with_model, fit_global_model, load_global_model  # noqa: E402
from scripts.fit_global_clusters import load_pool  # noqa: E402

# |z| a partir do qual uma feature entra na descrição do grupo. Meio desvio é o
# menor afastamento que ainda se enxerga no histograma sem procurar.
Z_DISTINGUE = 0.5

LEGENDA = {
    "avg_distance_from_team": ("distância média do time", "u"),
    "max_distance_from_team": ("maior distância do time no round", "u"),
    "distinct_places": ("regiões diferentes visitadas", ""),
    "crosshair_score": ("placement da mira (0-100)", ""),
    "height_score": ("mira na altura da cabeça (0-1)", ""),
    "frac_entering_fight": ("fração do tempo entrando em briga", ""),
    "time_of_first_contact_s": ("tempo até o 1º contato", "s"),
}


def perfil(pool: pl.DataFrame, rotulos: np.ndarray, features: list[str]) -> list[dict]:
    df = pool.with_columns(pl.Series("grupo", rotulos))
    geral = {f: (df[f].drop_nulls().mean(), df[f].drop_nulls().std()) for f in features}
    out = []
    for g in sorted(df["grupo"].unique(maintain_order=True).to_list()):
        sub = df.filter(pl.col("grupo") == g)
        linhas = []
        for f in features:
            m = sub[f].drop_nulls().mean()
            media, desvio = geral[f]
            linhas.append({"feature": f, "grupo": m, "geral": media, "z": (m - media) / desvio if desvio else 0.0})
        out.append({
            "grupo": g, "n": sub.height, "frac": sub.height / df.height,
            "ct": sub.filter(pl.col("side") == "ct").height, "tr": sub.filter(pl.col("side") == "t").height,
            "features": sorted(linhas, key=lambda x: -abs(x["z"])),
            "partidas": sub["match_id"].n_unique(),
        })
    return out


def main() -> None:
    pool, _ = load_pool()
    atual = load_global_model()
    novo = fit_global_model(pool)
    feats = atual["feature_columns"]
    a = assign_with_model(pool, atual)["cluster"].to_numpy()
    b = assign_with_model(pool, novo)["cluster"].to_numpy()

    ari = adjusted_rand_score(a, b)
    k = atual["n_clusters"]
    tabela = np.zeros((k, k), dtype=int)
    for x, y in zip(a, b):
        tabela[x, y] += 1
    linhas, colunas = linear_sum_assignment(-tabela)
    mantidos = tabela[linhas, colunas].sum()
    print("## Estabilidade: modelo atual x reajustado no corpus inteiro\n")
    print(f"- modelo atual: ajustado em {atual['n_player_rounds']} jogador-rounds, silhueta {atual['silhouette']:.3f}")
    print(f"- reajustado:   {novo['n_player_rounds']} jogador-rounds, silhueta {novo['silhouette']:.3f}")
    print(f"- índice de Rand ajustado entre as duas atribuições: **{ari:.3f}**")
    print(f"- com o melhor casamento de grupos, {mantidos} de {len(a)} rounds ({100 * mantidos / len(a):.1f}%) ficam no mesmo grupo")
    print("\n| grupo atual | vira o grupo novo | rounds do atual que ficam juntos |\n|---|---|---|")
    for x, y in zip(linhas, colunas):
        print(f"| {x} | {y} | {tabela[x, y]} de {tabela[x].sum()} ({100 * tabela[x, y] / tabela[x].sum():.0f}%) |")

    for titulo, rot in (("modelo ATUAL (o que está no site hoje)", a), ("modelo REAJUSTADO no corpus inteiro", b)):
        print(f"\n## Perfil -- {titulo}\n")
        for p in perfil(pool, rot, feats):
            print(f"### Grupo {p['grupo']}: {p['n']} jogador-rounds ({100 * p['frac']:.0f}%), CT {p['ct']} / TR {p['tr']}, "
                  f"em {p['partidas']} partidas\n")
            print("| feature | média do grupo | média geral | z |\n|---|---|---|---|")
            for f in p["features"]:
                nome, un = LEGENDA.get(f["feature"], (f["feature"], ""))
                marca = " **" if abs(f["z"]) >= Z_DISTINGUE else ""
                print(f"| {nome}{marca and ' (distingue)'} | {f['grupo']:.2f}{un} | {f['geral']:.2f}{un} | {f['z']:+.2f} |")
            print()


# ---------------------------------------------------------------------------
# Nomes candidatos, presos ao PERFIL e não ao número do grupo
# ---------------------------------------------------------------------------
# O número do grupo muda quando o modelo é reajustado (decisão 11); a assinatura
# de features não. Cada perfil é reconhecido pelo que o distingue, e os nomes
# citam os números que os justificam. Nenhum repete nome de função ESTRUTURAL
# (âncora, lurker, entry, trader, rotativo, coringa, suporte, AWPer): as duas
# camadas não se misturam (decisão 7d), e "âncora" como estilo colidiria com
# "âncora" como função.
PERFIS = [
    {"chave": "longe",
     "reconhece": lambda z: z["avg_distance_from_team"] >= 0.8,
     "candidatos": [
         ("Joga isolado", "distância média do time {avg_distance_from_team:.0f}u contra "
                          "{g_avg_distance_from_team:.0f}u ({z_avg_distance_from_team:+.2f} desvio)"),
         ("Segura longe do time", "maior distância no round {max_distance_from_team:.0f}u "
                                  "({z_max_distance_from_team:+.2f}) com poucas regiões visitadas "
                                  "({z_distinct_places:+.2f}): fica parado, longe"),
         ("Posição solitária", "{ct_pct:.0f}% dos rounds deste grupo são de CT: é o jeito de "
                               "defender um ponto sozinho"),
     ]},
    {"chave": "mira",
     "reconhece": lambda z: z["height_score"] <= -1.5,
     "candidatos": [
         ("Mira fora da altura", "mira na altura da cabeça {height_score:.2f} contra {g_height_score:.2f} "
                                 "({z_height_score:+.2f} desvio) -- o traço mais forte de todos os grupos"),
         ("Crosshair baixo", "placement {crosshair_score:.0f} contra {g_crosshair_score:.0f} "
                             "({z_crosshair_score:+.2f}); o resto do perfil fica perto da média"),
         ("Mira desajustada", "o grupo é definido só pela mira: posição, tempo e movimento são os da média"),
     ]},
    {"chave": "roda",
     "reconhece": lambda z: z["distinct_places"] >= 0.5 and z["time_of_first_contact_s"] >= 0.4,
     "candidatos": [
         ("Roda o mapa", "{distinct_places:.1f} regiões por round contra {g_distinct_places:.1f} "
                         "({z_distinct_places:+.2f} desvio)"),
         ("Contato tardio", "primeiro contato aos {time_of_first_contact_s:.0f}s contra "
                            "{g_time_of_first_contact_s:.0f}s ({z_time_of_first_contact_s:+.2f})"),
         ("Joga o relógio", "chega tarde e evita briga (tempo entrando em briga "
                            "{z_frac_entering_fight:+.2f} desvio)"),
     ]},
    {"chave": "junto",
     "reconhece": lambda z: z["time_of_first_contact_s"] <= -0.5 and z["max_distance_from_team"] <= -0.5,
     "candidatos": [
         ("Junto e rápido", "maior distância do time {max_distance_from_team:.0f}u contra "
                            "{g_max_distance_from_team:.0f}u ({z_max_distance_from_team:+.2f}) e contato aos "
                            "{time_of_first_contact_s:.0f}s ({z_time_of_first_contact_s:+.2f})"),
         ("Entra em bloco", "entra em briga {z_frac_entering_fight:+.2f} desvio acima da média, colado no "
                            "time ({z_avg_distance_from_team:+.2f})"),
         ("Execução em grupo", "{tr_pct:.0f}% dos rounds deste grupo são de TR: é o jeito de executar "
                               "um bomb junto"),
     ]},
]

# Um mapa com esta fração do grupo acima da fatia dele no corpus acende o aviso
# de "parte do grupo pode ser efeito do mapa". 1,8x: o dobro com folga para o
# ruído de um corpus onde o mapa mais raro tem 3% dos rounds.
RAZAO_MAPA_SUSPEITO = 1.8


def reconhece(z: dict) -> dict | None:
    """O perfil cuja assinatura bate -- só se bater UM. Ambíguo não recebe nome."""
    achados = [p for p in PERFIS if p["reconhece"](z)]
    return achados[0] if len(achados) == 1 else None


def proposta_md() -> list[str]:
    """As linhas da seção 2 do MATERIAL_DE_CALIBRACAO.md."""
    import json

    pool, _ = load_pool()
    atual, novo = load_global_model(), fit_global_model(pool)
    feats = atual["feature_columns"]
    a = assign_with_model(pool, atual)["cluster"].to_numpy()
    b = assign_with_model(pool, novo)["cluster"].to_numpy()
    k = atual["n_clusters"]
    tabela = np.zeros((k, k), dtype=int)
    for x, y in zip(a, b):
        tabela[x, y] += 1
    lin, col = linear_sum_assignment(-tabela)
    casa = dict(zip(lin, col))
    ari = adjusted_rand_score(a, b)
    man = json.loads((PROJECT_ROOT / "data" / "manifest.json").read_text(encoding="utf-8"))["partidas"]
    mapa_de = {m: v["mapa"].replace("de_", "") for m, v in man.items()}
    df = pool.with_columns(pl.Series("grupo", a), pl.col("match_id").replace_strict(mapa_de).alias("mapa"))
    mapas_corpus = df.group_by("mapa", maintain_order=True).len().with_columns((pl.col("len") / df.height).alias("fc"))
    geral = {f: (df[f].drop_nulls().mean(), df[f].drop_nulls().std()) for f in feats}

    out = ["## 2. Nomes dos quatro grupos de estilo", "",
           "Gerado por `py -3.12 -m scripts.proposta_grupos`. O KMeans não nomeia (decisão 8): abaixo está o que "
           "DEFINE cada grupo e, para cada um, três nomes que se justificam pelos números mostrados. Você escolhe, "
           "ajusta ou recusa; o nome vai para `clustering/cluster_names.json`.", "",
           "### Antes de nomear: o modelo ainda não foi ajustado no corpus inteiro", "",
           f"O modelo em uso foi ajustado em **{atual['n_player_rounds']} jogador-rounds (as 9 partidas de FACEIT)** "
           f"e aplicado às 52. Reajustado nas 52 ({novo['n_player_rounds']} jogador-rounds, sem gravar): índice de "
           f"Rand ajustado **{ari:.2f}**, e {100 * tabela[lin, col].sum() / len(a):.0f}% dos rounds ficam no mesmo "
           "grupo. **Os quatro perfis reaparecem** -- são os mesmos quatro jeitos --, mas os NÚMEROS dos grupos "
           "trocam, e o maior deles perde parte dos rounds para outro. Por isso os nomes abaixo estão presos ao "
           "perfil, não ao número: se o modelo for reajustado, cada nome segue o seu perfil. Reajustar é decisão "
           "sua (`py -3.12 -m scripts.fit_global_clusters`); recomendo antes de gravar os nomes.", "",
           "| perfil | grupo hoje | vira no reajuste | rounds que ficam juntos |", "|---|---|---|---|"]
    perfis = []
    for g in range(k):
        sub = df.filter(pl.col("grupo") == g)
        med = {f: sub[f].drop_nulls().mean() for f in feats}
        z = {f: (med[f] - geral[f][0]) / geral[f][1] for f in feats}
        p = reconhece(z)
        perfis.append((g, sub, med, z, p))
        out.append(f"| {p['chave'] if p else '?'} | {g} | {casa[g]} | {tabela[g, casa[g]]} de {tabela[g].sum()} "
                   f"({100 * tabela[g, casa[g]] / tabela[g].sum():.0f}%) |")
    for g, sub, med, z, p in perfis:
        ct = sub.filter(pl.col("side") == "ct").height
        vals = {**med, **{f"g_{f}": geral[f][0] for f in feats}, **{f"z_{f}": z[f] for f in feats},
                "ct_pct": 100 * ct / sub.height, "tr_pct": 100 * (sub.height - ct) / sub.height}
        chave = p["chave"] if p else "?"
        out += ["", f"### Perfil \"{chave}\" -- grupo {g} hoje ({sub.height} jogador-rounds, "
                    f"{100 * sub.height / df.height:.0f}% do corpus; CT {ct}, TR {sub.height - ct})", "",
                "| feature | média do grupo | média geral | desvio (z) |", "|---|---|---|---|"]
        for f in sorted(feats, key=lambda f: -abs(z[f])):
            nome, un = LEGENDA.get(f, (f, ""))
            destaque = " **(distingue)**" if abs(z[f]) >= Z_DISTINGUE else ""
            out.append(f"| {nome}{destaque} | {med[f]:.2f}{un} | {geral[f][0]:.2f}{un} | {z[f]:+.2f} |")
        mp = (sub.group_by("mapa", maintain_order=True).len()
              .with_columns((pl.col("len") / sub.height).alias("fg"))
              .join(mapas_corpus.select("mapa", "fc"), on="mapa")
              .with_columns((pl.col("fg") / pl.col("fc")).alias("r"))
              .sort("r", descending=True).row(0, named=True))
        aviso = ""
        if mp["r"] >= RAZAO_MAPA_SUSPEITO:
            aviso = (f" **Atenção:** {100 * mp['fg']:.0f}% dos rounds deste grupo são em {mp['mapa']} (o corpus "
                     f"tem {100 * mp['fc']:.0f}%, {mp['r']:.1f}x) -- parte do grupo pode ser efeito do mapa, "
                     "não estilo.")
        out += ["", f"Mapa mais super-representado: {mp['mapa']} ({mp['r']:.1f}x a fatia do corpus).{aviso}", ""]
        if p:
            out.append("**Nomes candidatos:**")
            for nome, just in p["candidatos"]:
                out.append(f"- **{nome}** -- {just.format(**vals)}")
        out += ["", f"**Sua resposta:** perfil \"{chave}\" = ____"]
    return out


if __name__ == "__main__":
    main()
