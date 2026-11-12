"""RS0 (só leitura): um round real passo a passo -- a chance antes e depois de cada evento e o crédito de cada jogador.

    py -3.12 -m scripts.calibracao.rs0_round_real MATCH_ID [ROUND]      # sem ROUND, procura um com flash, troca e plant
"""
from __future__ import annotations

import inspect
import sys
import textwrap
from pathlib import Path

import polars as pl

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ))
import metrics.rating as R  # noqa: E402
from scripts.fit_rating import carrega_partida, tickrate_da_partida  # noqa: E402


def swing_cru():
    """A mesma `swing_por_evento`, sem a soma final por (round, jogador): as linhas de cada evento."""
    src = textwrap.dedent(inspect.getsource(R.swing_por_evento)).replace("def swing_por_evento(", "def swing_cru_(")
    fim = src.index("    swing = pl.DataFrame(linhas)")
    src = src[:fim] + "    return pl.DataFrame(linhas)\n"
    ns = R.__dict__
    exec(src, ns)
    return ns["swing_cru_"]


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    mid = sys.argv[1]
    rn_pedido = int(sys.argv[2]) if len(sys.argv) > 2 else None
    ref = R.carrega_referencia()
    modelo = R.ModeloDeRound.da_referencia((ref or {}).get("modelo_de_round"))
    tabelas, team_of, vencedor, kast = carrega_partida(mid)
    tickrate = tickrate_da_partida(tabelas)
    rounds, ticks = tabelas["rounds"], tabelas["ticks"]
    grupos = R.grupo_do_round(ticks, rounds)
    nome = dict(ticks.group_by("steamid", maintain_order=True).agg(pl.col("name").last()).iter_rows())
    log = []
    orig = R._delta_da_kill

    def espia(modelo_, antes, vivos, ben, adv, dif, bomba, ct, tempos):
        p0 = float(modelo_.prob(R.np.array([R._estado_completo(antes[ben], antes[adv], dif, bomba, ct, *tempos)]))[0])
        d = orig(modelo_, antes, vivos, ben, adv, dif, bomba, ct, tempos)
        log.append({"ben": ben, "antes": dict(antes), "depois": dict(vivos), "p0": p0, "p1": p0 + d, "bomba": bomba})
        return d

    R._delta_da_kill = espia
    cru = swing_cru()
    try:
        candidatos = [rn_pedido] if rn_pedido else sorted(int(x) for x in kills_rounds(tabelas))
        for rn in candidatos:
            log.clear()
            k = tabelas["kills"].filter(pl.col("round_num") == rn)
            kk = {**tabelas, "kills": k}
            linhas = cru(k, tabelas["damages"].filter(pl.col("round_num") == rn),
                         None if tabelas["player_blind"] is None else tabelas["player_blind"].filter(pl.col("round_num") == rn),
                         rounds, grupos, modelo, team_of, vencedor, tickrate)
            papeis = set(linhas["papel"].to_list())
            if rn_pedido or ({"flash", "trade", "dano"} <= papeis and "fim_do_round" in papeis and any(l["bomba"] for l in log) and k.height >= 6):
                imprime(mid, rn, k, linhas, list(log), rounds, nome, team_of, vencedor, tickrate)
                return
    finally:
        R._delta_da_kill = orig
    print("nenhum round com todos os papéis")


def kills_rounds(t):
    return t["kills"]["round_num"].unique(maintain_order=True).to_list()


def imprime(mid, rn, k, linhas, log, rounds, nome, team_of, vencedor, tickrate):
    info = rounds.filter(pl.col("round_num") == rn).row(0, named=True)
    inicio, plant = info["freeze_end"], info["bomb_plant"]
    def rel(tick):
        return max(0, 115 - int((tick - inicio) / tickrate))
    def nm(s):
        return nome.get(s, str(s))
    print(f"# {mid}, round {rn}: vencedor time {vencedor[rn]}; plant {'às ' + str(rel(plant) // 60) + ':' + format(rel(plant) % 60, '02d') if plant else 'não houve'}\n")
    ev = []
    atual = None
    for r in linhas.iter_rows(named=True):
        if r["papel"] == "morreu":
            atual = {"morreu": r, "outros": []}
            ev.append(atual)
        elif r["papel"] == "fim_do_round":
            ev.append({"fim": r}) if not (ev and "fim_lista" in ev[-1]) else None
            ev[-1].setdefault("fim_lista", []).append(r)
        elif atual is not None:
            atual["outros"].append(r)
    ks = [e for e in k.sort("tick").iter_rows(named=True) if e.get("weapon") != "planted_c4"]
    total = {}
    i = 0
    for e in ev:
        if "morreu" not in e:
            continue
        kk, lg = ks[i], log[i]; i += 1
        quem = nm(kk["attacker_steamid"]); vit = nm(kk["victim_steamid"])
        print(f"\n**{rel(kk['tick']) // 60}:{rel(kk['tick']) % 60:02d}  {quem} mata {vit} ({kk.get('weapon')})**")
        print(f"- vivos {lg['antes']['A']}v{lg['antes']['B']} (A×B) → {lg['depois']['A']}v{lg['depois']['B']}; chance do time que matou (time {lg['ben']}): {lg['p0'] * 100:.1f}% → {lg['p1'] * 100:.1f}% (variação {100 * (lg['p1'] - lg['p0']):+.1f} p.p.){'; bomba plantada' if lg['bomba'] else ''}")
        por = [("morreu", e["morreu"])] + [(r["papel"], r) for r in e["outros"]]
        for papel, r in por:
            print(f"  - {nm(r['steamid'])} ({papel}): {100 * r['swing']:+.2f} p.p.")
            total[r["steamid"]] = total.get(r["steamid"], 0) + r["swing"]
    fim = [e for e in ev if "fim_lista" in e]
    if fim:
        print("\n**Fim do round**")
        for r in fim[0]["fim_lista"]:
            print(f"  - {nm(r['steamid'])}: {100 * r['swing']:+.2f} p.p.")
            total[r["steamid"]] = total.get(r["steamid"], 0) + r["swing"]
    print("\n**Total do round por jogador (soma zero entre os dez):**")
    for s, v in sorted(total.items(), key=lambda x: -x[1]):
        print(f"  - {nm(s)} (time {team_of.get(s)}): {100 * v:+.2f} p.p.")
    print(f"\nSoma: {100 * sum(total.values()):+.4f} p.p.")


if __name__ == "__main__":
    main()
