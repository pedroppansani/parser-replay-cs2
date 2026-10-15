"""Fase 18 (18.1): a linha de visão pelo mapa + campo de visão bate com a visibilidade gravada na demo?

    py -3.12 -m pesquisa.visao_contra_demo <pasta_de_saida> [partida ...]

Para cada partida com UMA demo no disco (a de várias partes tem os ticks recomeçando a cada parte),
lê `approximate_spotted_by` (m_bSpottedByMask) com o demoparser2 do projeto e grava em
`<pasta_de_saida>/<partida>_spotted.parquet` (nunca no interim). Depois, para cada morte por inimigo e
cada aliado vivo da vítima, compara na janela de troca:

- demo: o matador esteve no `spotted_by` do aliado em algum tick da janela;
- nossa: o matador esteve visível (linha de visão pelo mapa + campo de visão) em alguma amostra;
- só linha de visão (sem campo de visão), para saber se o `spotted` da demo já inclui o olhar.

Também mede de quantos em quantos ticks o `spotted_by` muda. Só imprime e grava o rascunho.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import numpy as np
import polars as pl

from metrics import visao
from metrics.constantes import JANELA_DE_TRADE_S

RAIZ = Path(__file__).resolve().parents[1]


def demos_de_uma_parte() -> dict[str, Path]:
    man = json.loads((RAIZ / "data" / "manifest.json").read_text(encoding="utf-8"))["partidas"]
    out = {}
    for m, v in sorted(man.items()):
        ds = v["demos"]
        if len(ds) == 1 and (RAIZ / ds[0]["caminho"]).exists() and os.path.getsize(RAIZ / ds[0]["caminho"]) == ds[0]["bytes"]:
            out[m] = RAIZ / ds[0]["caminho"]
    return out


def spotted(dem: Path, saida: Path) -> pl.DataFrame:
    if saida.exists():
        return pl.read_parquet(saida)
    from demoparser2 import DemoParser
    df = pl.from_pandas(DemoParser(str(dem)).parse_ticks(["approximate_spotted_by"]))
    df = df.filter(pl.col("approximate_spotted_by").list.len() > 0).select("tick", "steamid", "approximate_spotted_by")
    df.write_parquet(saida)
    return df


def compara(m: str, sp: pl.DataFrame) -> dict:
    from leitura.insights import resolve_teams
    from parsing.parser import load_interim

    tab = load_interim(RAIZ / "data" / "interim", m)
    ticks, kills = tab["ticks"], tab["kills"]
    meta = json.loads((RAIZ / "data" / "processed" / m / "match_meta.json").read_text(encoding="utf-8"))
    vis = visao.visao_da_partida(ticks, meta["map_name"], tab.get("smokes"), tab.get("player_blind"))
    team_of, _ = resolve_teams(ticks)
    janela = int(JANELA_DE_TRADE_S * 64)
    # visto pela demo: (alvo) -> {tick: {observadores}}
    por_alvo: dict = {}
    for tk, alvo, obs in sp.iter_rows():
        por_alvo.setdefault(int(alvo), {})[int(tk)] = {int(o) for o in obs}
    mortes = {}
    for r in kills.sort("tick").iter_rows(named=True):
        if r["victim_steamid"] is not None:
            mortes.setdefault((int(r["round_num"]), int(r["victim_steamid"])), int(r["tick"]))
    vivos = ticks.select("round_num", "tick", "steamid", "is_alive")
    alive = {(int(a), int(b), int(c)): bool(d) for a, b, c, d in vivos.filter(
        pl.col("tick").is_in(kills["tick"].unique().implode())).iter_rows()}
    danos = {}
    for r in tab["damages"].iter_rows(named=True):
        if r["attacker_steamid"] is not None and r["victim_steamid"] is not None and (r["dmg_health_real"] or 0) > 0:
            danos.setdefault((int(r["attacker_steamid"]), int(r["victim_steamid"])), []).append(int(r["tick"]))

    def trocaram_dano(x, y, t0, t1):
        return any(t0 < s <= t1 for s in danos.get((x, y), []) + danos.get((y, x), []))

    conta = {"dano_nossa_sem_demo": 0, "dano_demo_e_nossa": 0, "dano_nenhuma": 0, "nenhuma": 0, "pares": 0, "demo": 0, "nossa": 0, "so_linha": 0, "iguais": 0, "iguais_so_linha": 0,
             "demo_e_nossa": 0, "demo_sem_nossa": 0, "nossa_sem_demo": 0, "amostras": 0, "amostras_iguais": 0}
    exemplos = []
    for k in kills.sort("tick").iter_rows(named=True):
        a, v = k["attacker_steamid"], k["victim_steamid"]
        if a is None or v is None or team_of.get(a) is None or team_of.get(a) == team_of.get(v):
            continue
        rn, t = int(k["round_num"]), int(k["tick"])
        for j in [s for s, tm in team_of.items() if tm == team_of.get(v) and s != v]:
            if not alive.get((rn, t, int(j)), False) or mortes.get((rn, int(j)), 10**12) <= t:
                continue
            fim = min(t + janela, mortes.get((rn, int(j)), 10**12) - 1, mortes.get((rn, int(a)), 10**12) - 1)
            if fim <= t:
                continue
            visto_demo = any(int(j) in obs for tk, obs in por_alvo.get(int(a), {}).items() if t < tk <= fim)
            amostras = vis.amostras(t + 1, fim)
            nossa_amostra = [vis.visivel(rn, s, int(j), int(a)) for s in amostras]
            linha = any(vis.linha_de_visao(rn, s, int(j), int(a)) for s in amostras)
            nossa = any(nossa_amostra)
            # amostra a amostra: o spotted mais recente até o tick (é atualizado de 33 em 33)
            dic = por_alvo.get(int(a), {})
            tks = sorted(x for x in dic if x <= fim)
            for s, nv in zip(amostras, nossa_amostra):
                i = np.searchsorted(tks, s, side="right") - 1
                dv = i >= 0 and (s - tks[i]) <= 33 and int(j) in dic[tks[i]]
                conta["amostras"] += 1
                conta["amostras_iguais"] += int(dv == nv)
            conta["pares"] += 1
            conta["demo"] += visto_demo
            conta["nossa"] += nossa
            conta["so_linha"] += linha
            conta["iguais"] += visto_demo == nossa
            conta["iguais_so_linha"] += visto_demo == linha
            conta["demo_e_nossa"] += visto_demo and nossa
            conta["demo_sem_nossa"] += visto_demo and not nossa
            conta["nossa_sem_demo"] += nossa and not visto_demo
            dano = trocaram_dano(int(j), int(a), t, fim)
            conta["dano_nossa_sem_demo"] += nossa and not visto_demo and dano
            conta["dano_demo_e_nossa"] += nossa and visto_demo and dano
            conta["nenhuma"] += not nossa and not visto_demo
            conta["dano_nenhuma"] += not nossa and not visto_demo and dano
            if visto_demo != nossa and len(exemplos) < 6:
                exemplos.append((rn, t, int(j), int(a), visto_demo, nossa, linha))
    conta["exemplos"] = exemplos
    return conta


def intervalo_de_atualizacao(sp: pl.DataFrame) -> dict:
    d = (sp.with_columns(pl.col("approximate_spotted_by").cast(pl.List(pl.String)).list.join(",").alias("m"))
         .sort(["steamid", "tick"]))
    tk = d["tick"].to_numpy()
    passos = np.diff(np.unique(tk))
    return {"passo_mais_comum": int(np.bincount(passos).argmax()) if passos.size else None}


def main(argv: list[str]) -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    saida = Path(argv[0])
    saida.mkdir(parents=True, exist_ok=True)
    demos = demos_de_uma_parte()
    alvo = argv[1:] or list(demos)
    tot = {}
    for m in alvo:
        sp = spotted(demos[m], saida / f"{m}_spotted.parquet")
        c = compara(m, sp)
        passo = intervalo_de_atualizacao(sp)
        print(m, passo, {k: v for k, v in c.items() if k != "exemplos"})
        for e in c["exemplos"]:
            print("   diverge", e)
        for k, v in c.items():
            if k != "exemplos":
                tot[k] = tot.get(k, 0) + v
    print("TOTAL", tot)
    if tot.get("pares"):
        print(f"concordância por janela: {tot['iguais'] / tot['pares']:.3f} (só linha de visão: "
              f"{tot['iguais_so_linha'] / tot['pares']:.3f}); por amostra: {tot['amostras_iguais'] / tot['amostras']:.3f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
