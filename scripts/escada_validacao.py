"""
Escada de validação do rating contra os números OFICIAIS da HLTV.

    py -3.12 -m scripts.escada_validacao            # todos os degraus
    py -3.12 -m scripts.escada_validacao --rapido   # sem o Round Swing (o mais lento)

Valida-se de baixo para cima, e um degrau só vale se o de baixo estiver exato:
rating final próximo com contagem errada é coincidência, e coincidência quebra
na partida seguinte.

    1. rounds, kills e mortes      -- contagem: tem que bater EXATO
    2. ADR                         -- exato no arredondamento da HLTV (0,1)
    3. KAST                        -- rounds inteiros: exato
    4. aberturas, multi-kills, HS  -- contagem por SÉRIE (Detailed stats): exato
    5. Round Swing                 -- aqui começa a aproximação: correlação e erro
    6. rating                      -- por último

Fontes oficiais, todas transcritas dos prints da HLTV:
  data/reference/hltv_placar.json      K, D, ADR (410 jogadores, 41 partidas)
  data/reference/hltv_componentes.json KAST e Swing (310 jogadores, 31 partidas)
  data/reference/hltv_ratings.json     rating (430 jogadores, 43 partidas)
  data/reference/hltv_detalhado.json   Detailed stats por série (50 jogadores, 5 séries)
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import polars as pl

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from parsing.parser import kills_do_round_jogado  # noqa: E402

REF = PROJECT_ROOT / "data" / "reference"
PROCESSED = PROJECT_ROOT / "data" / "processed"
INTERIM = PROJECT_ROOT / "data" / "interim"

# A HLTV mostra o ADR com uma casa: a diferença que o arredondamento explica é
# metade do último dígito.
TOLERANCIA_ADR = 0.05

# Grafia da HLTV -> grafia gravada na demo, onde diferem.
APELIDOS = {"sh1ro": "SH1R0", "mzinho": "Mzinho", "Techno": "Techno4K"}


def _ler(nome: str) -> dict:
    return json.loads((REF / nome).read_text(encoding="utf-8"))["partidas"]


def _nome(n: str, conhecidos) -> str:
    return n if n in conhecidos else APELIDOS.get(n, n)


def contagens() -> pl.DataFrame:
    """Degraus 1 a 3: uma linha por jogador com o oficial e o nosso lado a lado."""
    placar = _ler("hltv_placar.json")
    comp = _ler("hltv_componentes.json")
    linhas = []
    for mid, v in placar.items():
        rounds = pl.read_parquet(PROCESSED / mid / "rounds.parquet")
        k = kills_do_round_jogado(pl.read_parquet(INTERIM / mid / "kills.parquet"), rounds)
        kills = dict(k.filter(pl.col("attacker_side") != pl.col("victim_side")).group_by("attacker_name").len().iter_rows())
        mortes = dict(k.group_by("victim_name").len().iter_rows())
        adr = dict(pl.read_parquet(PROCESSED / mid / "adr_summary.parquet").select("name", "adr").iter_rows())
        kast = dict(pl.read_parquet(PROCESSED / mid / "kast_summary.parquet").select("name", "kast_rounds").iter_rows())
        of_comp = (comp.get(mid) or {}).get("jogadores", {})
        for nome, o in v["jogadores"].items():
            oc = of_comp.get(nome) or of_comp.get({b: a for a, b in APELIDOS.items()}.get(nome, "")) or {}
            linhas.append({
                "match_id": mid, "nome": nome,
                "rounds_oficial": v["rounds"], "rounds": rounds.height,
                "kills_oficial": o["kills"], "kills": kills.get(nome, 0),
                "mortes_oficial": o["mortes"], "mortes": mortes.get(nome, 0),
                "adr_oficial": o["adr"], "adr": adr.get(nome),
                "kast_oficial": oc.get("kast_rounds"), "kast": kast.get(nome),
            })
    return pl.DataFrame(linhas, infer_schema_length=None)


def detalhado() -> pl.DataFrame:
    """Degrau 4: contagens da página 'Detailed stats' da HLTV, que é por SÉRIE --
    os nossos mapas de cada série são somados antes de comparar. Série que não
    está inteira no corpus fica de fora."""
    arq = REF / "hltv_detalhado.json"
    if not arq.exists():
        return pl.DataFrame()
    ref = json.loads(arq.read_text(encoding="utf-8"))
    apelidos = ref.get("apelidos", {})
    linhas = []
    for serie, v in ref["series"].items():
        if not v.get("serie_completa_no_corpus"):
            continue
        soma: dict[str, dict] = {}
        for mid in v["mapas"]:
            rounds = pl.read_parquet(PROCESSED / mid / "rounds.parquet")
            k = kills_do_round_jogado(pl.read_parquet(INTERIM / mid / "kills.parquet"), rounds)
            inim = k.filter(pl.col("attacker_steamid").is_not_null() & (pl.col("attacker_side") != pl.col("victim_side")))
            # abertura = a primeira kill em inimigo do round (fogo amigo e bomba não abrem)
            primeira = inim.sort("tick").group_by("round_num").first()
            # clutch: a definição única do projeto (metrics/clutch.py, 1vX com X >= 1)
            from metrics.clutch import clutch_situations
            from metrics.player_roles import resolve_teams
            from metrics.sides import side_of_team

            ticks = pl.read_parquet(INTERIM / mid / "ticks.parquet", columns=["tick", "round_num", "steamid", "name", "side"])
            team_of, _ = resolve_teams(ticks)
            venc = {int(r["round_num"]): ("A" if r["winner"] == side_of_team("A", int(r["round_num"])) else "B")
                    for r in rounds.iter_rows(named=True)}
            cl, _ = clutch_situations(k, rounds, team_of, venc)
            nome_de = dict(ticks.group_by("steamid").agg(pl.col("name").last()).iter_rows())
            ganhos = {}
            for r in cl.filter(pl.col("won")).iter_rows(named=True):
                ganhos[nome_de.get(r["steamid"])] = ganhos.get(nome_de.get(r["steamid"]), 0) + 1
            for nome in set(inim["attacker_name"].drop_nulls()) | set(k["victim_name"].drop_nulls()):
                meu = inim.filter(pl.col("attacker_name") == nome)
                s = soma.setdefault(nome, {"op_kills": 0, "op_mortes": 0, "mk_rounds": 0, "hs": 0, "clutches": 0})
                s["clutches"] += ganhos.get(nome, 0)
                s["op_kills"] += primeira.filter(pl.col("attacker_name") == nome).height
                s["op_mortes"] += primeira.filter(pl.col("victim_name") == nome).height
                s["mk_rounds"] += meu.group_by("round_num").len().filter(pl.col("len") >= 2).height
                s["hs"] += meu.filter(pl.col("headshot")).height
        for nome, o in v["jogadores"].items():
            x = soma.get(apelidos.get(nome, nome)) or soma.get(nome) or {}
            for campo in ("op_kills", "op_mortes", "mk_rounds", "hs", "clutches"):
                linhas.append({"serie": serie, "nome": nome, "campo": campo,
                               "oficial": o[campo], "nosso": x.get(campo, 0)})
    return pl.DataFrame(linhas)


def swing() -> pl.DataFrame:
    """Degrau 5: o Round Swing deste projeto, em pontos percentuais, contra o oficial."""
    from metrics.rating import ModeloDeRound, carrega_referencia, rating
    from scripts.fit_rating import carrega_partida

    referencia = carrega_referencia()
    modelo = ModeloDeRound.da_referencia((referencia or {}).get("modelo_de_round"))
    linhas = []
    for mid, v in _ler("hltv_componentes.json").items():
        tabelas, team_of, vencedor, kast = carrega_partida(mid)
        _, resumo = rating(tabelas, team_of, vencedor, kast, 64, referencia=referencia, modelo=modelo)
        nick = dict(tabelas["ticks"].group_by("steamid").agg(pl.col("name").last()).iter_rows())
        nosso = {nick.get(j["steamid"]): 100 * j["sub_round_swing"] for j in resumo["jogadores"]}
        for nome, o in v["jogadores"].items():
            linhas.append({"match_id": mid, "nome": nome, "swing_oficial": o["swing_pct"],
                           "swing": nosso.get(_nome(nome, nosso))})
    return pl.DataFrame(linhas)


def rating_do_site() -> pl.DataFrame:
    """Degrau 6: o rating que a PÁGINA mostra (insights.json) contra o oficial."""
    linhas = []
    for mid, v in _ler("hltv_ratings.json").items():
        if not v.get("usar_na_calibracao"):
            continue
        ins = PROCESSED / mid / "insights.json"
        if not ins.exists():
            continue
        nosso = {p["name"]: p.get("rating") for p in json.loads(ins.read_text(encoding="utf-8"))["players"]}
        for nome, oficial in (v.get("jogadores") or {}).items():
            if oficial is not None:
                linhas.append({"match_id": mid, "nome": nome, "rating_oficial": oficial,
                               "rating": nosso.get(_nome(nome, nosso))})
    return pl.DataFrame(linhas).drop_nulls()


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--rapido", action="store_true", help="pula o degrau 5 (Round Swing), o mais lento")
    args = ap.parse_args()

    c = contagens()
    n = c.height
    por_partida = c.unique("match_id")
    print(f"ESCADA DE VALIDAÇÃO -- {n} jogadores em {por_partida.height} partidas com K-D-ADR oficial\n")

    r_ok = int((por_partida["rounds"] == por_partida["rounds_oficial"]).sum())
    k_ok = c["kills"] == c["kills_oficial"]
    d_ok = c["mortes"] == c["mortes_oficial"]
    print(f"1. rounds   {r_ok}/{por_partida.height} partidas exatas")
    print(f"   kills    {int(k_ok.sum())}/{n} exatos | mortes {int(d_ok.sum())}/{n} exatos")
    ruins = c.filter(~(k_ok & d_ok))
    if ruins.height:
        print("   DEGRAU 1 NÃO ESTÁ EXATO -- os de cima são coincidência até isto ser explicado:")
        print(ruins.select("match_id", "nome", "kills_oficial", "kills", "mortes_oficial", "mortes"))

    dif = (c["adr"] - c["adr_oficial"])
    print(f"\n2. ADR      {int((dif.abs() <= TOLERANCIA_ADR).sum())}/{n} exatos no arredondamento | "
          f"maior diferença {dif.abs().max():.2f} | viés {dif.mean():+.3f}")
    fora = c.with_columns(dif.alias("dif")).filter(pl.col("dif").abs() > TOLERANCIA_ADR)
    if fora.height:
        print(fora.select("match_id", "nome", "adr_oficial", "adr", "dif").sort("dif"))

    ck = c.drop_nulls("kast_oficial")
    dk = ck["kast"] - ck["kast_oficial"]
    print(f"\n3. KAST     {int((dk == 0).sum())}/{ck.height} exatos | acima {int((dk > 0).sum())} "
          f"({int(dk.filter(dk > 0).sum()):+d} rounds) | abaixo {int((dk < 0).sum())} ({int(dk.filter(dk < 0).sum()):+d} rounds)")

    dt = detalhado()
    if dt.height:
        print(f"\n4. contagens da 'Detailed stats' (por série, {dt['serie'].n_unique()} séries):")
        for campo, g in dt.group_by("campo", maintain_order=True):
            print(f"   {campo[0]:<10} {int((g['nosso'] == g['oficial']).sum())}/{g.height} exatos")
        print("   (assistência de flash e morte trocada: ver CLAUDE.md 22j -- ainda não batem)")
    else:
        print("\n4. multi-kills e aberturas: sem data/reference/hltv_detalhado.json")

    if not args.rapido:
        s = swing().drop_nulls()
        x, y = s["swing"].to_numpy(), s["swing_oficial"].to_numpy()
        print(f"\n5. Swing    {s.height} jogadores | correlação {np.corrcoef(x, y)[0, 1]:.3f} | erro médio {np.mean(np.abs(x - y)):.2f} p.p. "
              f"| média {x.mean():+.2f} (oficial {y.mean():+.2f}) | inclinação {np.polyfit(y, x, 1)[0]:.2f}")

    rt = rating_do_site()
    x, y = rt["rating"].to_numpy(), rt["rating_oficial"].to_numpy()
    print(f"\n6. rating   {rt.height} jogadores | erro médio {np.mean(np.abs(x - y)):.3f} | viés {np.mean(x - y):+.3f} "
          f"| correlação {np.corrcoef(x, y)[0, 1]:.3f}   (o número da página, dentro da amostra)")


if __name__ == "__main__":
    main()
