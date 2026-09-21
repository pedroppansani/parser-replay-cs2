"""
Gera MATERIAL_DE_CALIBRACAO.md: tudo que depende de julgamento do Pedro, junto,
no formato "olhar e confirmar".

    py -3.12 -m scripts.material_calibracao

Quatro seções:
  1. PISOS de função: distribuição, cortes candidatos e os NOMES de cada lado;
  2. GRUPOS de estilo: perfil, quem concentra, 5 rounds representativos e
     sugestões de nome (a escolha continua do Pedro, em cluster_names.json);
  3. FORÇA das granadas: distribuição com os rótulos aplicados e um exemplo de cada;
  4. CONSOLE: um comando pronto de um arremesso específico, para testar no jogo.

O arquivo é saída GERADA (decisão 24), mas é pequeno e vive no repositório de
propósito: é o documento que o Pedro responde, e o histórico dele é o registro
de quando cada limiar foi decidido.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import polars as pl

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from clustering.playstyle import describe_clusters  # noqa: E402
from metrics.identidade import com_nome_de_exibicao  # noqa: E402
from metrics.grenade_throws import grenade_throws, grupos_de_forca, rotula_forca, trajetorias  # noqa: E402
from metrics.player_roles import TRAIT_SPECS  # noqa: E402
from parsing.parser import load_interim  # noqa: E402
from scripts.calibration_report import carrega, cortes_com_nomes  # noqa: E402

PROCESSED = PROJECT_ROOT / "data" / "processed"
INTERIM = PROJECT_ROOT / "data" / "interim"
SAIDA = PROJECT_ROOT / "MATERIAL_DE_CALIBRACAO.md"

# Partidas usadas na amostra de força de arremesso (o módulo é caro: ~1 min por
# partida). Seis bastam: 2.268 arremessos, e os três grupos já aparecem.
PARTIDAS_FORCA = ("match_01", "match_05", "match_38", "match_43", "match_47", "match_52")
# O arremesso do roteiro de console. Escolhido por ser smoke de CT clássica, em
# pé, parado e com a menor ancoragem residual da partida.
CONSOLE = ("match_38", 2, "jL")

# Sugestões de nome para cada grupo. São SUGESTÕES, não rótulos: a nomeação é do
# Pedro (decisão 8) e mora em clustering/cluster_names.json.
SUGESTOES = {
    "longe do time": ("Segura sozinho", "Âncora isolado", "Posição fixa"),
    "joga por baixo": ("Mira fora da altura", "Crosshair baixo", "—"),
    "passa por muitas regiões": ("Joga o round inteiro", "Rodando com o time", "Default paciente"),
    "encosta no adversário cedo": ("Pressão cedo", "Entrada em bloco", "Executa junto"),
}
FEATURES = ["avg_distance_from_team", "max_distance_from_team", "distinct_places",
            "time_of_first_contact_s", "frac_entering_fight", "crosshair_score", "height_score"]


def secao_pisos() -> list[str]:
    funcoes = carrega("player_roles")
    man = json.loads((PROJECT_ROOT / "data" / "manifest.json").read_text(encoding="utf-8"))["partidas"]
    time_de = {(m, n): (v["times"][t]["nome"] or "").removeprefix("Team ")
               for m, v in man.items() for t in ("A", "B") for n in v["times"][t]["jogadores"]}
    funcoes = funcoes.with_columns(pl.struct(["match_id", "name"]).map_elements(
        lambda r: time_de.get((r["match_id"], r["name"])), return_dtype=pl.Utf8).alias("time_real"))
    out = ["## 1. Pisos de função",
           "",
           "O rótulo exige **liderar o próprio time** naquela métrica E passar do piso. "
           "Por isso a tabela é dos líderes: para cada jogador, em quantas partidas ele liderou o time "
           "e em quantas levaria o rótulo com cada corte candidato. Os pisos continuam ABSOLUTOS -- "
           "percentil faria uma fração fixa sempre receber rótulo, e \"nenhum suporte nesta partida\" "
           "deixaria de poder acontecer.", ""]
    for t in TRAIT_SPECS:
        bloco = cortes_com_nomes(funcoes, t)
        out.append(f"### {t.label} — hoje `{t.column} >= {t.floor}`")
        out.append("```")
        out += [b.replace("=== ", "").replace(" ===", "") for b in bloco]
        out.append("```")
        out.append(f"**Sua resposta:** piso de {t.label} = ____")
        out.append("")
    return out


def secao_grupos() -> list[str]:
    man = json.loads((PROJECT_ROOT / "data" / "manifest.json").read_text(encoding="utf-8"))["partidas"]
    partes = [pl.read_parquet(d / "cluster_assignments.parquet").with_columns(
        pl.lit(d.name).alias("match_id"), pl.lit(man[d.name]["mapa"].replace("de_", "")).alias("mapa"))
        for d in sorted(PROCESSED.glob("match_*")) if (d / "cluster_assignments.parquet").exists()]
    c = com_nome_de_exibicao(pl.concat(partes, how="diagonal_relaxed"))
    perfil_global = PROJECT_ROOT / "data" / "global_clusters" / "cluster_profiles.parquet"
    desc = {r["cluster"]: r["titulo"] for r in describe_clusters(pl.read_parquet(perfil_global)).to_dicts()}
    geral = {f: (c[f].mean(), c[f].std()) for f in FEATURES}
    tot = c.group_by("steamid", maintain_order=True).agg(pl.col("name").last().alias("name"), pl.len().alias("d"))
    out = ["## 2. Nomes dos quatro grupos de estilo", "",
           "A descrição automática é releitura das médias, não nome de função (decisão 8). "
           "As sugestões abaixo são só sugestões: quem nomeia é você, em `clustering/cluster_names.json`.", ""]
    for k in sorted(c["cluster"].unique(maintain_order=True)):
        g = c.filter(pl.col("cluster") == k)
        titulo = desc.get(k, f"grupo {k}")
        z = sorted(((f, (g[f].mean() - geral[f][0]) / geral[f][1], g[f].mean(), geral[f][0]) for f in FEATURES),
                   key=lambda x: -abs(x[1]))[:4]
        top = (g.group_by("steamid", maintain_order=True).len().join(tot, on="steamid").filter(pl.col("d") >= 150)
               .with_columns((pl.col("len") / pl.col("d")).alias("fr")).sort("fr", descending=True).head(5))
        cx, cy = g["pca_1"].mean(), g["pca_2"].mean()
        ex = (g.with_columns(((pl.col("pca_1") - cx) ** 2 + (pl.col("pca_2") - cy) ** 2).alias("dist"))
              .sort("dist").unique(["match_id"], keep="first", maintain_order=True).head(5))
        out += [f"### Grupo {k} — descrição automática: \"{titulo}\"",
                f"- **{g.height} rounds** ({g.height / c.height:.0%} do corpus); CT {g.filter(pl.col('side') == 'ct').height}, TR {g.filter(pl.col('side') == 't').height}",
                "- **O que distingue** (desvios da média geral): " + "; ".join(
                    f"{f} {m:.1f} contra {mg:.1f} ({zz:+.2f})" for f, zz, m, mg in z),
                "- **Quem mais concentra** (fração dos próprios rounds, mínimo de 150 rounds no corpus): " + ", ".join(
                    f"{r['name']} {r['len']} de {r['d']} ({r['fr']:.0%})" for r in top.iter_rows(named=True)),
                "- **Rounds representativos** (mais perto do centro do grupo):"]
        for r in ex.iter_rows(named=True):
            contato = "-" if r["time_of_first_contact_s"] is None else f"{r['time_of_first_contact_s']:.0f}s"
            out.append(f"  - {r['match_id']} ({r['mapa']}) round {r['round_num']}, {r['name']} ({r['side']}): "
                       f"{r['avg_distance_from_team']:.0f}u do time, {r['distinct_places']} regiões, contato {contato}, "
                       f"{r['damage']} de dano, {r['kills']} kills")
        s = SUGESTOES.get(titulo, ("—", "—", "—"))
        out += [f"- **Sugestões:** {s[0]} · {s[1]} · {s[2]}", "", f"**Sua resposta:** grupo {k} = ____", ""]
    return out


def secao_forca() -> list[str]:
    partes = []
    for mid in PARTIDAS_FORCA:
        if not (INTERIM / mid / "ticks.parquet").exists():
            continue
        t = load_interim(INTERIM, mid)
        pr, _ = grenade_throws(t, 64)
        if pr.height:
            fr = pl.read_parquet(PROCESSED / mid / "rounds.parquet").select("round_num", "freeze_end")
            partes.append(pr.join(fr.with_columns(pl.col("round_num").cast(pr.schema["round_num"])),
                                  on="round_num", how="left").with_columns(pl.lit(mid).alias("match_id")))
    d = pl.concat(partes, how="diagonal_relaxed").drop_nulls("velocidade_arremesso")
    v = d["velocidade_arremesso"].to_numpy()
    g = grupos_de_forca(v)
    d = d.with_columns(pl.col("velocidade_arremesso").map_elements(
        lambda x: rotula_forca(x, g), return_dtype=pl.Utf8).alias("forca"))
    out = ["## 3. Rótulos de força do arremesso", "",
           f"{d.height} arremessos em {d['match_id'].n_unique()} partidas. Os grupos saem por moda "
           "(decisão 5); os rótulos foram aplicados PELA ORDEM (mais lento = curto) e estão marcados "
           "\"(a confirmar)\" no código até você responder.", "",
           "| Grupo | Centro | Arremessos | Exemplo |", "|---|---|---|---|"]
    for (rot,), grp in d.group_by("forca", maintain_order=True):
        e = grp.filter(pl.col("reproducao_exata") & (pl.col("movimento") == "parado"))
        e = (e if e.height else grp).sort("velocidade_arremesso").row(min(1, max(0, (e.height or 1) - 1)), named=True)
        seg = (e["tick_soltura"] - e["freeze_end"]) / 64
        out.append(f"| {rot} | {grp['velocidade_arremesso'].mean():.0f} u/s | {grp.height} | "
                   f"{e['thrower']}, {e['kind']}, {e['match_id']} round {e['round_num']} "
                   f"({int(seg // 60)}:{int(seg % 60):02d}), {e['postura']}, {e['movimento']} |")
    bordas = np.arange(0, 900, 50)
    cont, _ = np.histogram(v, bins=bordas)
    out += ["", "```"]
    for i, n in enumerate(cont):
        out.append(f"{bordas[i]:>4}-{bordas[i + 1]:<4} u/s | {'#' * int(50 * n / max(cont.max(), 1)):<50} {n:>4}"
                   f"  {rotula_forca(float(bordas[i] + 25), g)}")
    out += ["```", "", "**Sua resposta:** curto/médio/longo pela ordem está certo? ____", ""]
    return out


def secao_console() -> list[str]:
    mid, rn, jogador = CONSOLE
    t = load_interim(INTERIM, mid)
    pr, _ = grenade_throws(t, 64)
    c = pr.filter((pl.col("round_num") == rn) & (pl.col("thrower") == jogador) & (pl.col("kind") == "smoke"))
    if c.height == 0:
        return ["## 4. Teste do comando de console", "", "arremesso de referência não encontrado", ""]
    r = c.sort("residuo").row(0, named=True)
    traj = trajetorias(t["grenades"], t["rounds"]).filter(
        (pl.col("entity_id") == r["entity_id"]) & (pl.col("round_num") == rn)).sort("tick")
    fim = traj.row(-1, named=True)
    fr = dict(t["rounds"].select("round_num", "freeze_end").iter_rows())
    seg = (r["tick_soltura"] - fr[rn]) / 64
    mapa = json.loads((PROCESSED / mid / "match_meta.json").read_text(encoding="utf-8"))["map_name"]
    return ["## 4. Teste do comando de console", "",
            f"Arremesso: **{jogador}**, smoke, **{mid}** ({mapa}) round {rn}, "
            f"{int(seg // 60)}:{int(seg % 60):02d} do round (tick {r['tick_soltura']}). "
            f"Ancoragem com resíduo de {r['residuo']:.2f}u, em pé, parado.", "",
            "1. Servidor local no mapa, com:", "",
            "```",
            "sv_cheats 1; mp_warmup_end; mp_freezetime 0; sv_infinite_ammo 1; sv_grenade_trajectory_prac_pipreview 1",
            "```", "",
            "2. Com a smoke na mão, sem se mover:", "",
            "```",
            f"setpos {r['x']:.2f} {r['y']:.2f} {r['z']:.2f}; setang {r['pitch']:.2f} {r['yaw']:.2f} 0",
            "```", "",
            "3. Solte com o **botão esquerdo** (arremesso cheio), em pé, parado.", "",
            f"**Certo:** a smoke para em ({fim['X']:.0f}, {fim['Y']:.0f}, {fim['Z']:.0f}). "
            "O preview da trajetória mostra o ponto antes de você soltar.", "",
            "**Se errar, me mande:** a saída do `getpos` logo depois do `setpos`; onde a smoke caiu "
            "(nome do lugar); e se o erro foi de DISTÂNCIA (curta ou longa demais -> altura ou pitch) "
            "ou de LADO (esquerda ou direita -> yaw).", "",
            "**Sua resposta:** funcionou? ____", ""]


def main() -> None:
    partes = ["# Material de calibração", "",
              "Gerado por `py -3.12 -m scripts.material_calibracao`. Cada seção termina com a "
              "pergunta que só você responde; as respostas viram constante com data e tamanho de "
              "corpus no CLAUDE.md.", ""]
    partes += secao_pisos() + secao_grupos() + secao_forca() + secao_console()
    SAIDA.write_text("\n".join(partes), encoding="utf-8")
    print(f"Gravado em {SAIDA.relative_to(PROJECT_ROOT)} ({SAIDA.stat().st_size / 1024:.0f} KB)")


if __name__ == "__main__":
    main()
