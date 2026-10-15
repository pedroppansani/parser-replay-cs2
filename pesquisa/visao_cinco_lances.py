"""Fase 18 (18.1): cinco lances conferidos, um de cada situação, com o dado de cada fonte.

    py -3.12 -m pesquisa.visao_cinco_lances <pasta_do_spotted> [partida]

Lê o `approximate_spotted_by` gravado por `pesquisa.visao_contra_demo` (rascunho, fora do interim) e,
para as mortes da partida, escolhe o primeiro lance de cada situação:
1. as duas fontes dizem visível e houve troca de dano entre os dois na janela;
2. as duas dizem não visível;
3. só a nossa diz visível, e houve troca de dano (a demo deixou de marcar);
4. só a nossa diz visível, sem troca de dano;
5. a smoke fechou a linha (sem a smoke, a linha estaria livre).
Imprime lugar, distância, ângulo do olhar, linha de visão, spotted da demo e dano, com o link do replay.
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import polars as pl

from metrics import visao
from metrics.constantes import JANELA_DE_TRADE_S

RAIZ = Path(__file__).resolve().parents[1]


def main(argv: list[str]) -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    from leitura.insights import resolve_teams
    from parsing.parser import load_interim
    pasta, m = Path(argv[0]), (argv[1] if len(argv) > 1 else "match_15")
    tab = load_interim(RAIZ / "data" / "interim", m)
    ticks, kills = tab["ticks"], tab["kills"]
    meta = json.loads((RAIZ / "data" / "processed" / m / "match_meta.json").read_text(encoding="utf-8"))
    vis = visao.visao_da_partida(ticks, meta["map_name"], tab.get("smokes"), tab.get("player_blind"))
    sem_smoke = visao.Visao(ticks, vis.malha, [], cegueira=vis.cegueira)
    team_of, _ = resolve_teams(ticks)
    nome = dict(ticks.select("steamid", "name").unique(subset=["steamid"], keep="first", maintain_order=True).iter_rows())
    lugar = {(int(r), int(t), int(s)): p for r, t, s, p in ticks.select("round_num", "tick", "steamid", "place").iter_rows()}
    rounds = {int(r["round_num"]): r for r in tab["rounds"].iter_rows(named=True)}
    sp = pl.read_parquet(pasta / f"{m}_spotted.parquet")
    por_alvo: dict = {}
    for tk, alvo, obs in sp.iter_rows():
        por_alvo.setdefault(int(alvo), {})[int(tk)] = {int(o) for o in obs}
    danos = {}
    for r in tab["damages"].iter_rows(named=True):
        if r["attacker_steamid"] and r["victim_steamid"] and (r["dmg_health_real"] or 0) > 0:
            danos.setdefault((int(r["attacker_steamid"]), int(r["victim_steamid"])), []).append(int(r["tick"]))
    mortes = {}
    for r in kills.sort("tick").iter_rows(named=True):
        if r["victim_steamid"] is not None:
            mortes.setdefault((int(r["round_num"]), int(r["victim_steamid"])), int(r["tick"]))
    achados: dict = {}
    janela = int(JANELA_DE_TRADE_S * 64)
    for k in kills.sort("tick").iter_rows(named=True):
        a, v = k["attacker_steamid"], k["victim_steamid"]
        if a is None or v is None or team_of.get(a) is None or team_of.get(a) == team_of.get(v):
            continue
        rn, t = int(k["round_num"]), int(k["tick"])
        for j in sorted(s for s, tm in team_of.items() if tm == team_of.get(v) and s != v):
            if mortes.get((rn, int(j)), 10**12) <= t:
                continue
            fim = min(t + janela, mortes.get((rn, int(j)), 10**12) - 1, mortes.get((rn, int(a)), 10**12) - 1)
            if fim <= t:
                continue
            am = vis.amostras(t, fim)
            nossa = [s for s in am if vis.visivel(rn, s, int(j), int(a))]
            demo = [tk for tk, obs in por_alvo.get(int(a), {}).items() if t <= tk <= fim and int(j) in obs]
            dano = any(t <= s <= fim for s in danos.get((int(j), int(a)), []) + danos.get((int(a), int(j)), []))
            fumaca = [s for s in am if not vis.visivel(rn, s, int(j), int(a)) and sem_smoke.visivel(rn, s, int(j), int(a))]
            caso = (1 if nossa and demo and dano else 2 if not nossa and not demo else 3 if nossa and not demo and dano
                    else 4 if nossa and not demo else None)
            if fumaca and 5 not in achados:
                caso = 5
            if caso is None or caso in achados:
                continue
            s = (nossa or fumaca or am)[0]
            eo, ea = vis.estado(rn, int(j), s), vis.estado(rn, int(a), s)
            fe = rounds[rn]["freeze_end"]
            achados[caso] = {
                "partida": m, "round": rn, "relogio_s": round((s - fe) / 64, 1), "tick": s,
                "jogador": nome[j], "lugar_jogador": lugar.get((rn, s, int(j))), "matador": nome[a],
                "lugar_matador": lugar.get((rn, s, int(a))), "vitima": nome[v],
                "dist": round(math.hypot(eo[0] - ea[0], eo[1] - ea[1])), "dz": round(ea[2] - eo[2]),
                "angulo": round(visao.angulo_horizontal(eo[3], eo, ea), 1),
                "linha_de_visao": vis.linha_de_visao(rn, s, int(j), int(a)),
                "amostras_visiveis_nossa": f"{len(nossa)} de {len(am)}", "ticks_spotted_demo": len(demo),
                "troca_de_dano": dano, "smoke_fechou": bool(fumaca),
                "replay": f"docs/{m}.html#replay?round={rn}&t={round((s - fe) / 64, 1)}"}
        if len(achados) == 5:
            break
    for c in sorted(achados):
        print(c, achados[c])
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
